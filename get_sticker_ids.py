import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def get_sticker_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe un sticker y devuelve su file_id"""
    if update.message.sticker:
        sticker = update.message.sticker
        file_id = sticker.file_id
        emoji = sticker.emoji or "sin emoji"
        await update.message.reply_text(
            "Sticker recibido!\n"
            "Emoji: " + emoji + "\n"
            "file_id: " + file_id
        )
    else:
        await update.message.reply_text("Mandame un sticker para obtener su file_id")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Sticker.ALL, get_sticker_id))
    print("Bot listo para recibir stickers...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
