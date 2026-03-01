import os
from dotenv import load_dotenv
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "🔮 Hoş geldin! Ben senin kişisel mistik falcınım.\n\n"
        "Bana burcunu, aklındaki bir soruyu veya sadece 'Bana bir fal bak' yaz, "
        "yıldızların senin için ne söylediğini anlatayım."
    )
    await update.message.reply_text(mesaj)

async def fal_bak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        prompt = f"Sen eğlenceli, biraz gizemli, hafif samimi ve bilge bir astroloji/fal botusun. Kullanıcının şu mesajına göre ona sanki kahve falı ya da tarot bakıyormuş gibi akıcı, etkileyici ve çok uzun olmayan bir yanıt ver: '{user_message}'"

        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt
        )
        await update.message.reply_text(response.text)
        
    except Exception as e:
        await update.message.reply_text("✨ Yıldızlar şu an biraz puslu, enerjiyi tam alamadım. Lütfen birazdan tekrar dene!")
        print(f"Hata Logu: {e}")

def main():
    # Botu başlatıyoruz
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Komutları ve mesajları dinleyen algılayıcılar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fal_bak))

    print("🔮 Fal Botu uyandı ve Telegram'da mesaj bekliyor...")
    app.run_polling()

if __name__ == '__main__':
    main()