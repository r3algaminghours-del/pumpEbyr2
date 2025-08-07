import os
import time
import threading
import nest_asyncio
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from datetime import datetime

from pumpfun_api import listen_pumpfun_tokens
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as ray_minutes
from filter import is_promising

nest_asyncio.apply()

TELEGRAM_TOKEN = "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE"
CHANNEL_ID = 1758725762

seen = set()
signals_sent = 0
start_time = datetime.now()

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=10000)

async def send_signal(info, source, application):
    global signals_sent
    link = f"https://pump.fun/{info.get('address')}" if source == "pumpfun" else info.get("url", "")
    msg = (
        f"[NEW] Token on {source.title()}\n"
        f"{info.get('name', '')} (${info.get('symbol', '')})\n\n"
        f"MC: ${int(info.get('marketCap', 0)):,}\n"
        f"Holders: {info.get('holders', 0)}\n"
        f"Dev Hold: {info.get('devTokenPercentage', 0):.2f}%\n"
        f"5m Vol: ${int(info.get('volume5m', 0)):,}\n"
        f"Netflow: ${int(info.get('netflow5m', 0)):,}\n\n"
        f"{link}"
    )
    await application.bot.send_message(chat_id=CHANNEL_ID, text=msg)
    signals_sent += 1

async def handle_pump_tokens(tokens, application):
    for token in tokens:
        mint = token.get("address") or token.get("mint")
        if mint in seen:
            continue
        seen.add(mint)

        token["marketCap"] = token.get("market_cap", 0)
        token["name"] = token.get("name", "Unknown")
        token["symbol"] = token.get("symbol", "???")
        token["holders"] = token.get("holders", 0)
        token["devTokenPercentage"] = token.get("dev_hold", 0)
        token["volume5m"] = token.get("volume", 0)
        token["netflow5m"] = token.get("inflow", 0)

        if is_promising(token):
            await send_signal(token, "pumpfun", application)

async def raylaunch_loop(application):
    try:
        while True:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [RAYLAUNCH] Checking tokens...")

            for token in fetch_raylaunch_tokens():
                mint = token.get("address") or token.get("mint")
                if mint in seen:
                    continue
                seen.add(mint)

                token["marketCap"] = token.get("market_cap", 0)
                token["name"] = token.get("name", "Unknown")
                token["symbol"] = token.get("symbol", "???")
                token["holders"] = token.get("holders", 0)
                token["devTokenPercentage"] = token.get("dev_hold", 0)
                token["volume5m"] = token.get("volume", 0)
                token["netflow5m"] = token.get("inflow", 0)
                token["url"] = token.get("url", "")

                if ray_minutes(token.get("created_at", time.time())) > 30:
                    continue

                if is_promising(token):
                    await send_signal(token, "raylaunch", application)

            await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("[RAYLAUNCH] Loop cancelled.")
    except Exception as e:
        print(f"[RAYLAUNCH] Error: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - start_time
    mins = uptime.seconds // 60
    msg = (
        f"✅ Bot is running\n"
        f"Sources: Pump.fun (WebSocket), RayLaunch\n"
        f"Signals sent: {signals_sent}\n"
        f"Uptime: {mins} minutes"
    )
    await update.message.reply_text(msg)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[MESSAGE] From {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

def run_all():
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    async def post_init(app):
        print("[INIT] Starting token tasks...")
        app.pump_task = asyncio.create_task(listen_pumpfun_tokens(lambda tokens: handle_pump_tokens(tokens, app)))
        app.ray_task = asyncio.create_task(raylaunch_loop(app))

    async def shutdown(app):
        print("[SHUTDOWN] Cancelling tasks...")
        for task_name in ["pump_task", "ray_task"]:
            task = getattr(app, task_name, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    application.post_init = post_init
    application.post_shutdown = shutdown

    print("[BOT] Polling started")
    application.run_polling()

if __name__ == "__main__":
    run_all()
