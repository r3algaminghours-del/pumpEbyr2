import time
import threading
import os
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from datetime import datetime

from pumpfun_api import fetch_latest_tokens, fetch_token_info, minutes_since as pump_minutes
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as ray_minutes
from filter import is_promising

# Конфиг
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8180214699:AAEU79Dd8N_kCZZFXoqdifB3u0-B1BxiHgQ")
CHANNEL_ID = 1758725762  # ID канала или пользователя (нужен формат int)

seen = set()
signals_sent = 0
start_time = datetime.now()

# Flask для Render
app = Flask(__name__)
@app.route("/")
def home():
    return "PumpFun + RayLaunch bot is running", 200

# Telegram Application
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Команды и сообщения
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - start_time
    mins = uptime.seconds // 60
    msg = f"""✅ Bot is running
Sources: Pump.fun, RayLaunch
Signals sent: {signals_sent}
Uptime: {mins} minutes"""
    await update.message.reply_text(msg)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

application.add_handler(CommandHandler("status", status))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Отправка сигнала
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
    msg = f"""[NEW] Token on {source.title()}
{name} (${symbol})

MC: ${int(mc):,}
Holders: {holders}
Dev Hold: {dev_hold:.2f}%%
5m Vol: ${int(vol):,}
Netflow: ${int(inflow):,}

{link}
"""
    await application.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML")
    signals_sent += 1

# Цикл проверки токенов
async def check_tokens_loop():
    while True:
        print("Checking tokens...")

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

# Flask запускаем отдельно в потоке
def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Основной запуск
async def run():
    asyncio.create_task(check_tokens_loop())
    print("Starting Telegram bot...")
    await application.initialize()
    await application.start()
    print("Polling started...")
    await application.run_polling()
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down...")



