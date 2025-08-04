import os
import time
import threading
import asyncio
from datetime import datetime
from flask import Flask
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

# === Настройки ===
TELEGRAM_TOKEN = "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE"
CHANNEL_ID = 1758725762  # Замени на ID своего канала

seen = set()
signals_sent = 0
start_time = datetime.now()

# === Flask-сервер для Render ===
app = Flask(__name__)
@app.route("/")
def index():
    return "Bot is running", 200

# === Telegram bot ===
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# === Обработка команды /status ===
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - start_time
    mins = uptime.seconds // 60
    msg = f"""✅ Bot is running
Sources: Pump.fun, RayLaunch
Signals sent: {signals_sent}
Uptime: {mins} minutes"""
    await update.message.reply_text(msg)

# === Обработка любых текстовых сообщений (эхо) ===
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[echo] From {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

# === Отправка сигнала в канал ===
async def send_signal(info, source):
    global signals_sent
    link = f"https://pump.fun/{info.get('address')}" if source == "pumpfun" else info.get("url", "")
    msg = f"""[NEW] Token on {source.title()}
{info.get("name")} (${info.get("symbol")})

MC: ${int(info.get("marketCap", 0)):,}
Holders: {info.get("holders", 0)}
Dev Hold: {info.get("devTokenPercentage", 0):.2f}%
5m Vol: ${int(info.get("volume5m", 0)):,}
Netflow: ${int(info.get("netflow5m", 0)):,}

{link}
"""
    await application.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="HTML")
    signals_sent += 1

# === Фоновая проверка токенов ===
async def check_tokens_loop():
    while True:
        print("🔄 Checking tokens...")

        # --- PumpFun ---
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

        # --- RayLaunch ---
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

# === Регистрируем хендлеры ===
application.add_handler(CommandHandler("status", status))
application.add_handler(MessageHandler(filters.TEXT & ~_

