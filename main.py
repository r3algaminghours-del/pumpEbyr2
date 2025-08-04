import os
import time
import asyncio
import threading
from flask import Flask
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from pumpfun_api import fetch_latest_tokens, fetch_token_info, minutes_since as pump_minutes
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as ray_minutes
from filter import is_promising

# --- Конфигурация ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1001234567890"))  # обязательно отрицательный ID

seen = set()
signals_sent = 0
start_time = datetime.now()

# --- Flask ---
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Bot is alive", 200

# --- Telegram обработчики ---
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
    print(f"[MSG] From {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

# --- Сигнал токена ---
async def send_signal(info, source, bot):
    global signals_sent
    link = f"https://pump.fun/{info.get('address')}" if source == "pumpfun" else info.get("url", "")
    msg = (
        f"[NEW] Token on {source.title()}\n"
        f"{info.get('name')} (${info.get('symbol')})\n\n"
        f"MC: ${int(info.get('marketCap', 0)):,}\n"
        f"Holders: {info.get('holders', 0)}\n"
        f"Dev Hold: {info.get('devTokenPercentage', 0):.2f}%\n"
        f"5m Vol: ${int(info.get('volume5m', 0)):,}\n"
        f"Netflow: ${int(info.get('netflow5m', 0)):,}\n\n"
        f"{link}"
    )
    print(f"[SIGNAL] Sending {info.get('symbol')} from {source}")
    await bot.send_message(chat_id=CHANNEL_ID, text=msg)
    signals_sent += 1

# --- Фоновый парсинг токенов ---
async def check_tokens_loop(bot):
    while True:
        print("[LOOP] Checking tokens...")

        # Pump.fun
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
                await send_signal(token, "raylaunch", bot)

        await asyncio.sleep(10)

# --- Основная логика бота ---
async def telegram_main():
    print("[BOT] Initializing Telegram bot...")

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем цикл парсинга в фоне
    asyncio.create_task(check_tokens_loop(application.bot))

    print("[BOT] Polling started")
    await application.run_polling()

# --- Запуск Flask и Telegram параллельно ---
def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

def run_all():
    # Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    # Telegram bot в основном asyncio event loop
    asyncio.run(telegram_main())

if __name__ == "__main__":
    try:
        run_all()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down...")
