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
        await update.message.reply_text(
            f"✅ Sticker recibido!\n"
            f"Emoji: {sticker.emoji}\n"
            f"file_id: `{sticker.file_id}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Mándame un sticker para obtener su file_id")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Sticker.ALL, get_sticker_id))
    print("🤖 Bot listo para recibir stickers...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
