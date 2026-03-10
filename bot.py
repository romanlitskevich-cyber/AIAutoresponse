import os
import logging
import asyncio
from aiohttp import web
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Настройка логирования (чтобы видеть всё в Render)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. Настройка API ключей из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Функция обработки сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"📩 НОВОЕ СООБЩЕНИЕ от {update.effective_user.first_name}: {user_text}")

    try:
        # Отправляем запрос в Gemini
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
        logger.info(f"✅ ОТВЕТ ОТПРАВЛЕН пользователю {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ ОШИБКА GEMINI: {e}")
        await update.message.reply_text("Извини, нейросеть сейчас недоступна. Попробуй позже.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот на базе Gemini 1.5 Flash. Напиши мне что-нибудь!")

# 4. Веб-сервер для "здоровья" Render (Health Check)
async def handle_health_check(request):
    return web.Response(text="Бот работает!", status=200)

async def run_bot():
    # Создаем приложение Telegram
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Настройка веб-сервера для Render
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

    # Запуск бота
    async with application:
        # Сброс вебхуков и старых обновлений, чтобы избежать Conflict
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.initialize()
        await application.start()
        logger.info("🚀 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ")
        await application.updater.start_polling()

        # Держим бота запущенным
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")