import os
import asyncio
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
from parser.pumpfun import fetch_latest_tokens, fetch_token_info, pump_minutes
from parser.raylaunch import fetch_raylaunch_tokens, ray_minutes

TOKEN = "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE"
CHANNEL_ID = -1002379895969

# Логирование
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user = update.effective_user.id
    print(f"[MESSAGE] From {user}: {msg}")
    await update.message.reply_text("Принято")

# Упрощённый фильтр: пропускаем все токены с marketCap > 0
def is_promising(token_info):
    try:
        return token_info.get("marketCap", 0) > 0
    except Exception:
        return False

seen = set()

async def send_signal(token, source, app):
    name = token.get("name", "Unknown")
    symbol = token.get("symbol", "???")
    market_cap = token.get("marketCap", 0)
    holders = token.get("holders", 0)
    dev_percent = token.get("devTokenPercentage", 0)
    link = token.get("url", "https://pump.fun")

    msg = f"🚨 Новый токен ({source})\n\n"
    msg += f"🪙 {name} ({symbol})\n"
    msg += f"💰 MC: ${market_cap:,.0f}\n👥 Холд.: {holders}\n🛠 Dev: {dev_percent:.1f}%\n🔗 {link}"

    print(f"[SIGNAL] Sending token: {name}")
    await app.bot.send_message(chat_id=CHANNEL_ID, text=msg)

async def check_tokens_loop(app):
    try:
        while True:
            now_str = datetime.now().strftime('%H:%M:%S')
            print(f"[{now_str}] [LOOP] Checking tokens...")

            # Тестовое сообщение каждые 10 сек
            await app.bot.send_message(chat_id=CHANNEL_ID, text=f"[{now_str}] ✅ Тестовое сообщение от бота")

            # Pump.fun
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
                    await send_signal(info, "pumpfun", app)

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
                if ray_minutes(token.get("created_at", 0)) > 30:
                    continue
                if is_promising(token):
                    await send_signal(token, "raylaunch", app)

            await asyncio.sleep(10)

    except asyncio.CancelledError:
        print("[LOOP] Token checker cancelled.")
    except Exception as e:
        print(f"[ERROR] Token loop crashed: {e}")

# Flask server to keep alive
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running!"

# Главный старт
async def main():
    from nest_asyncio import apply
    apply()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    asyncio.create_task(check_tokens_loop(application))

    print("[INIT] Starting token loop...")
    await application.run_polling()

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=10000)).start()
    asyncio.run(main())
