import asyncio
import logging
import os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from pumpfun_api import fetch_latest_tokens as fetch_pumpfun, fetch_token_info, minutes_since as pf_minutes
from raylaunch_api import fetch_raylaunch_tokens, minutes_since as rl_minutes

# === CONFIG ===
TOKEN = "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE"
USER_ID = 1758725762  # Личный Telegram ID
CHECK_INTERVAL = 10  # seconds

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S"
)

# === FLASK SERVER (RENDER workaround) ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# === TELEGRAM COMMANDS ===
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧠 Я получил ваше сообщение.")

# === TOKEN PARSING LOOP ===
sent_tokens = set()

async def check_tokens_loop(app):
    logging.info("[INIT] Starting token loop...")
    while True:
        logging.info("[LOOP] Checking tokens...")

        # Pump.fun
        for token in fetch_pumpfun():
            address = token.get("id")
            if address in sent_tokens:
                continue

            created = pf_minutes(token.get("created"))
            if created < 10 and token.get("tvl", 0) > 0.1:
                info = fetch_token_info(address)
                if info:
                    msg = f"🔥 Новый токен на Pump.fun\n\n" \
                          f"💠 Название: {info.get('name')}\n" \
                          f"📈 TVL: {round(info.get('tvl', 0), 2)} SOL\n" \
                          f"🕒 Минут с создания: {round(created, 1)}\n" \
                          f"https://pump.fun/{address}"
                    await app.bot.send_message(chat_id=USER_ID, text=msg)
                    sent_tokens.add(address)

        # RayLaunch
        for token in fetch_raylaunch_tokens():
            address = token.get("address")
            if address in sent_tokens:
                continue

            created = rl_minutes(token.get("created", 0))
            if created < 10 and token.get("liquidity", 0) > 0.1:
                msg = f"🚀 Новый токен на RayLaunch\n\n" \
                      f"💠 Название: {token.get('name')}\n" \
                      f"📈 Liquidity: {round(token.get('liquidity', 0), 2)} SOL\n" \
                      f"🕒 Минут с создания: {round(created, 1)}\n" \
                      f"https://raylaunch.app/token/{address}"
                await app.bot.send_message(chat_id=USER_ID, text=msg)
                sent_tokens.add(address)

        await asyncio.sleep(CHECK_INTERVAL)

# === TELEGRAM BOT ===
async def telegram_main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    loop_task = asyncio.create_task(check_tokens_loop(application))
    logging.info("[BOT] Polling started")

    await application.run_polling()
    loop_task.cancel()
    logging.info("[SHUTDOWN] Token loop cancelled.")

# === ENTRYPOINT ===
def run_all():
    Thread(target=run_flask).start()
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(telegram_main())

if __name__ == "__main__":
    run_all()
