import asyncio
import logging
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from pumpfun_api import fetch_latest_tokens, fetch_token_info, minutes_since as pf_minutes
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as rl_minutes

# === Конфигурация ===
BOT_TOKEN = "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE"
USER_CHAT_ID = 1758725762

# === Логирование ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот активен. Ожидаю токены...")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"[MESSAGE] From {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Принято!")

# === Основной цикл ===
async def check_tokens_loop(application):
    sent_tokens = set()
    logging.info("[INIT] Starting token loop...")

    while True:
        logging.info("[LOOP] Checking tokens...")

        try:
            pumpfun_tokens = fetch_latest_tokens()
            ray_tokens = fetch_raylaunch_tokens()

            logging.info(f"[DEBUG] PumpFun tokens fetched: {len(pumpfun_tokens)}")
            logging.info(f"[DEBUG] RayLaunch tokens fetched: {len(ray_tokens)}")

            if pumpfun_tokens:
                logging.info(f"[DEBUG] Sample PumpFun token: {pumpfun_tokens[0]}")
            if ray_tokens:
                logging.info(f"[DEBUG] Sample RayLaunch token: {ray_tokens[0]}")

            # Отправим тестовый токен PumpFun, если есть
            if pumpfun_tokens:
                token = pumpfun_tokens[0]
                msg = f"🧪 PumpFun Token: {token.get('name')} — {token.get('mint')}"
                await application.bot.send_message(chat_id=USER_CHAT_ID, text=msg)

            # Отправим тестовый токен RayLaunch, если есть
            if ray_tokens:
                token = ray_tokens[0]
                msg = f"🧪 RayLaunch Token: {token.get('name')} — {token.get('mint')}"
                await application.bot.send_message(chat_id=USER_CHAT_ID, text=msg)

        except Exception as e:
            logging.error(f"[ERROR] Loop failed: {e}")

        await asyncio.sleep(10)  # Интервал в секундах

# === Запуск бота ===
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    loop_task = asyncio.create_task(check_tokens_loop(application))

    logging.info("[BOT] Polling started")
    await application.run_polling()

    logging.info("[SHUTDOWN] Cancelling token loop...")
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        logging.info("[LOOP] Token checker cancelled.")

if __name__ == "__main__":
    asyncio.run(main())

