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

from pumpfun_api import fetch_latest_tokens, fetch_token_info, minutes_since as pump_minutes
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as ray_minutes
# from filter import is_promising  # убрали импорт фильтра

nest_asyncio.apply()

TELEGRAM_TOKEN = "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE"
CHANNEL_ID = -1002379895969

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

async def check_tokens_loop(application):
    try:
        while True:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [LOOP] Checking tokens...")

            for token in fetch_latest_tokens():
                mint = token.get("address")
                if mint in seen:
                    continue
                seen.add(mint)

                info = fetch_token_info(mint)
                if not info:
                    continue
                if pump_minutes(info.get("created_at", 0)) > 30:
                    continue
                # Убираем фильтр, отправляем всё подряд:
                await send_signal(info, "pumpfun", application)

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
                # Убираем фильтр:
                await send_signal(token, "raylaunch", application)

            await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("[LOOP] Token checker cancelled.")
    except Exception as e:
        print(f"[ERROR] Token loop crashed: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - start_time
    mins = uptime.seconds // 60
    msg = (
        f"✅ Bot is running\n"
        f"Sources: Pump.fun, RayLaunch\n"
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
        print("[INIT] Starting token loop...")
        app.token_task = asyncio.create_task(check_tokens_loop(app))

    async def shutdown(app):
        print("[SHUTDOWN] Cancelling token loop...")
        if hasattr(app, "token_task"):
            app.token_task.cancel()
            try:
                await app.token_task
            except asyncio.CancelledError:
                pass

    application.post_init = post_init
    application.post_shutdown = shutdown

    print("[BOT] Polling started")
    application.run_polling()

if __name__ == "__main__":
    run_all()
