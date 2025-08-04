import os
import time
import threading
import asyncio
from datetime import datetime

from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

import nest_asyncio
nest_asyncio.apply()

from pumpfun_api import fetch_latest_tokens, fetch_token_info, minutes_since as pump_minutes
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as ray_minutes
from filter import is_promising

# Получаем токен из переменных окружения
TELEGRAM_TOKEN = os.getenv("8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002379895969"))

app = Flask(__name__)
seen = set()
signals_sent = 0
start_time = datetime.now()

@app.route("/")
def home():
    return "PumpFun + RayLaunch bot is running", 200

# Основной бот
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def send_signal(info, source):
    global signals_sent
    link = f"https://pump.fun/{info.get('address')}" if source == "pumpfun" else info.get("url", "")
    mc = info.get("marketCap", 0)
    holders = info.get("holders", 0)
    dev_hold = info.get("devTokenPercentage", 0)
    inflow = info.get("netflow5m", 0)
    vol = info.get("volume5m", 0)
    name = info.get("name", "")
    symbol = info.get("symbol", "")
    msg = (
        f"[NEW] Token on {source.title()}\n"
        f"{name} (${symbol})\n\n"
        f"MC: ${int(mc):,}\n"
        f"Holders: {holders}\n"
        f"Dev Hold: {dev_hold:.2f}%\n"
        f"5m Vol: ${int(vol):,}\n"
        f"Netflow: ${int(inflow):,}\n\n"
        f"{link}"
    )
    await application.bot.send_message(chat_id=CHANNEL_ID, text=msg)
    signals_sent += 1

async def check_tokens_loop():
    while True:
        print("[LOOP] Checking tokens...")

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
            if is_promising(info):
                await send_signal(info, source="pumpfun")

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
                await send_signal(token, source="raylaunch")

        await asyncio.sleep(10)

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
    print(f"[ECHO] Message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

def run_flask():
    app.run(host="0.0.0.0", port=10000)

def run_all():
    threading.Thread(target=run_flask, daemon=True).start()

    loop = asyncio.get_event_loop()

    # Добавляем обработчики
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем фоновую задачу
    loop.create_task(check_tokens_loop())

    print("[BOT] Polling started")
    loop.run_until_complete(application.run_polling())

if __name__ == "__main__":
    print("[BOT] Initializing Telegram bot...")
    run_all()


