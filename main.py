from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "ВАШ_ТОКЕН_ТУТ"

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Получена команда /status от {update.effective_user.id}")
    await update.message.reply_text("✅ Бот жив и работает!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Получено сообщение от {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Принял сообщение!")

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Запуск polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
