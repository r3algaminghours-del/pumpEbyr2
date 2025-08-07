import os
import time
import asyncio
import threading
import logging
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

from pumpfun_api import listen_pumpfun_tokens, minutes_since
from filter import is_promising

# === Конфигурация ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 1758725762))

# === Логгирование ===
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("main")

# === Flask для Render Ping ===
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running!", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=10000)

# === Глобальные переменные ===
seen = set()
signals_sent = 0
start_time = datetime.now()

# === Telegram команды ===
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - start_time
    mins = uptime.seconds // 60
    msg = (
        f"✅ Bot is running\n"
        f"Source: Pump.fun WebSocket\n"
        f"Signals sent: {signals_sent}\n"
        f"Uptime: {mins} minutes"
    )
    await update.message.reply_text(msg)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"[MESSAGE] From {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

# === Отправка сигнала ===
async def send_signal(info, application):
    global signals_sent

    link = f"https://pump.fun/{info.get('address')}"
    msg = (
        f"[NEW] Token on Pump.fun\n"
        f"{info.get('name', '')} (${info.get('symbol', '')})\n\n"
        f"MC: ${int(info.get('marketCap', 0)):,}\n"
        f"Holders: {info.get('holders', 0)}\n"
        f"Dev Hold: {info.get('devTokenPercentage', 0):.2f}%\n"
        f"5m Vol: ${int(info.get('volume5m', 0)):,}\n"
        f"Netflow: ${int(info.get('netflow5m', 0)):,}\n\n"
        f"{link}"
    )

    try:
        await application.bot.send_message(chat_id=CHANNEL_ID, text=msg)
        signals_sent += 1
        logger.info(f"[SEND] Sent signal for {info.get('symbol')}")
    except Exception as e:
        logger.error(f"[SEND] Failed to send signal: {e}")

# === Callback при поступлении новых токенов ===
async def handle_pumpfun_tokens(tokens, application):
    for token in tokens:
        mint = token.get("address")
        if not mint or mint in seen:
            continue
        seen.add(mint)

        if minutes_since(token.get("created_at", 0)) > 30:
            continue
        if is_promising(token):
            await send_signal(token, application)

# === Основной цикл ===
async def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # запускаем WebSocket loop отдельно
    async def pump_ws_task():
        await listen_pumpfun_tokens(lambda tokens: handle_pumpfun_tokens(tokens, application))

    async def post_init(app):
        logger.info("[INIT] Starting Pump.fun WebSocket listener...")
        app.pump_ws = asyncio.create_task(pump_ws_task())

    async def shutdown(app):
        logger.info("[SHUTDOWN] Shutting down Pump.fun listener...")
        if hasattr(app, "pump_ws"):
            app.pump_ws.cancel()
            try:
                await app.pump_ws
            except asyncio.CancelledError:
                logger.info("[SHUTDOWN] Listener cancelled")

    application.post_init = post_init
    application.post_shutdown = shutdown

    logger.info("[BOT] Polling started")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
