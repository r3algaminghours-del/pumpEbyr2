import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8278714282:AAEM0iWo1J_CjSIW4oGZ588m0JTVPQv_AAE"
CHANNEL_ID = -1002379895969  # твой канал, пока не используется в этом тесте

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received /status from {update.effective_user.id}")
    await update.message.reply_text("✅ Bot is alive and responding!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received message from {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Got your message!")

async def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Starting polling...")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
