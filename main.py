import os
import time
import threading
from datetime import datetime
from flask import Flask
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from pumpfun_api import fetch_latest_tokens, fetch_token_info, minutes_since as pump_minutes
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as ray_minutes
from filter import is_promising

# --- Config ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE")
CHANNEL_ID = -1002379895969  # Замени на свой канал ID
PORT = int(os.environ.get("PORT", 10000))

# --- Globals ---
seen = set()
signals_sent = 0
start_time = datetime.now()

# --- Flask ---
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is alive", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

# --- Telegram Handlers ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - start_time
    msg = (
        f"✅ Bot is running\n"
        f"Signals sent: {signals_sent}\n"
        f"Uptime: {uptime.seconds // 60} min"
    )
    await update.message.reply_text(msg)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Got your message!")

async def send_signal(info, source, bot):
    global signals_sent
    link = f"https://pump.fun/{info.get('address')}" if source == "pumpfun" else info.get("url", "")
    msg = (
        f"[NEW] Token on {source.title()}\n"
        f"{info.get('name')} (${info.get('symbol')})\n"
        f"MC: ${int(info.get('marketCap', 0)):,}\n"
        f"Holders: {info.get('holders', 0)}\n"
        f"Dev Hold: {info.get('devTokenPercentage', 0):.2f}%\n"
        f"5m Vol: ${int(info.get('volume5m', 0)):,}\n"
        f"Netflow: ${int(info.get('netflow5m', 0)):,}\n\n"
        f"{link}"
    )
    print(f"[SIGNAL] {info.get('symbol')} - sending...")
    await bot.send_message(chat_id=CHANNEL_ID, text=msg)
    signals_sent += 1

async def check_tokens_loop(application):
    bot = application.bot
    while True:
        print("[LOOP] Checking tokens...")

        # PumpFun
        for token in fetch_latest_tokens():
            mint = token.get("address")
            if mint in seen:
                continue
            seen.add(mint)

            info = fetch_token_info(mint)
            if not info or pump_minutes(info.get("created_at", 0)) > 30:
                continue

            if is_promising(info):
                await send_signal(info, "pumpfun", bot)

        # RayLaunch
        for token in fetch_raylaunch_tokens():
            mint = token.get("address") or token.get("mint")
            if mint in seen:
                continue
            seen.add(mint)

            token["marketCap"] = token.get("market_cap", 0)
            token["name"] = token.get("name", "???")
            token["symbol"] = token.get("symbol", "???")
            token["holders"] = token.get("holders", 0)
            token["devTokenPercentage"] = token.get("dev_hold", 0)
            token["volume5m"] = token.get("volume", 0)
            token["netflow5m"] = token.get("inflow", 0)
            token["url"] = token.get("url", "")

            if ray_minutes(token.get("created_at", time.time())) > 30:
                continue
            if is_promising(token):
                await send_signal(token, "raylaunch", bot)

        await asyncio.sleep(10)

# --- Start bot ---
def start_bot():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запуск фоновой задачи
    asyncio.create_task(check_tokens_loop(application))

    print("[BOT] Polling started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# --- Main ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()

    try:
        asyncio.get_event_loop().run_until_complete(asyncio.to_thread(start_bot))
    except KeyboardInterrupt:
        print("Exiting...")
