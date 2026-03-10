import os
import logging
import asyncio
from aiohttp import web
from google import genai  # Новый импорт
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация нового клиента Gemini (стандарт 2026)
client = genai.Client(api_key=GEMINI_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"📩 НОВОЕ СООБЩЕНИЕ от {update.effective_user.first_name}: {user_text}")

    try:
        # Новый способ вызова модели
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=user_text
        )
        await update.message.reply_text(response.text)
        logger.info(f"✅ ОТВЕТ ОТПРАВЛЕН")
    except Exception as e:
        logger.error(f"❌ ОШИБКА GEMINI: {e}")
        await update.message.reply_text("Нейросеть не смогла ответить. Проверь логи.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я обновленный бот на Gemini 1.5 Flash. Напиши мне!")

async def handle_health_check(request):
    return web.Response(text="OK", status=200)

async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 10000).start()

    async with application:
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run_bot())