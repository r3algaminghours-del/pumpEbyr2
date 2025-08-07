import asyncio
import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from flask import Flask
import threading

from pumpfun_api import get_new_pumpfun_tokens
from raylaunch_api import get_new_raylaunch_tokens

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_ID = 1758725762
CHECK_INTERVAL = 10

logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO
)

app = Flask(__name__)

@app.route('/')
def index():
    return 'PumpFun + RayLaunch bot is running'

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is up and running!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"[MESSAGE] From {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("👋 Привет! Используй /status чтобы проверить статус бота.")

async def send_message_to_user(bot, user_id, text):
    try:
        await bot.send_message(chat_id=user_id, text=text)
        logging.info(f"[SEND] To {user_id}: {text}")
    except Exception as e:
        logging.error(f"[ERROR] Failed to send message: {e}")

async def token_checker(bot):
    logging.info("[INIT] Starting token loop...")
    sent_tokens = set()

    while True:
        logging.info("[LOOP] Checking tokens...")

        try:
            pumpfun_tokens = get_new_pumpfun_tokens()
            logging.info(f"[PUMPFUN] New: {pumpfun_tokens}")
            for token in pumpfun_tokens:
                if token not in sent_tokens:
                    await send_message_to_user(bot, USER_ID, f"🔥 PumpFun Token: {token}")
                    sent_tokens.add(token)

            raylaunch_tokens = get_new_raylaunch_tokens()
            logging.info(f"[RAYLAUNCH] New: {raylaunch_tokens}")
            for token in raylaunch_tokens:
                if token not in sent_tokens:
                    await send_message_to_user(bot, USER_ID, f"🚀 RayLaunch Token: {token}")
                    sent_tokens.add(token)

        except Exception as e:
            logging.error(f"[LOOP ERROR] {e}")

        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    asyncio.get_event_loop().create_task(token_checker(application.bot))

    logging.info("[BOT] Polling started")
    await application.run_polling()

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()

    # fix: don't call asyncio.run()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

