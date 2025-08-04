from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from datetime import datetime

TELEGRAM_TOKEN = "8180214699:AAEU79Dd8N_kCZZFXoqdifB3u0-B1BxiHgQ"

start_time = datetime.now()
signals_sent = 0  # заглушка для статуса

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.now() - start_time
    mins = uptime.seconds // 60
    msg = f"""✅ Bot is running
Signals sent: {signals_sent}
Uptime: {mins} minutes"""
    await update.message.reply_text(msg)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Starting polling...")
    application.run_polling()

if __name__ == "__main__":
    main()

