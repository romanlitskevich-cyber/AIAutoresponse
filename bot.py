import os
import logging
import asyncio
from aiohttp import web
from google import genai  # Новый официальный клиент Google
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация клиента Gemini (версия 2026)
client = genai.Client(api_key=GEMINI_KEY)

# --- ЛОГИКА БОТА ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"📩 НОВОЕ СООБЩЕНИЕ от {update.effective_user.first_name}: {user_text}")

    try:
        # Пробуем отправить запрос в Gemini
        # Мы используем '-latest', чтобы избежать 404 ошибки на Render
        response = client.models.generate_content(
            model="gemini-1.5-flash-latest",
            contents=user_text
        )

        if response.text:
            await update.message.reply_text(response.text)
            logger.info("✅ ОТВЕТ УСПЕШНО ОТПРАВЛЕН")
        else:
            await update.message.reply_text("Бот получил пустой ответ от нейросети.")

    except Exception as e:
        logger.error(f"❌ ОШИБКА GEMINI: {e}")
        # Если ошибка 404, пробуем подсказать пользователю
        if "404" in str(e):
            await update.message.reply_text("Ошибка: Модель временно недоступна в этом регионе.")
        else:
            await update.message.reply_text("Произошла ошибка при обращении к нейросети.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот на базе Gemini 1.5 Flash. Напиши мне свой вопрос!")

# --- СЕРВЕР ДЛЯ RENDER (Health Check) ---
async def handle_health_check(request):
    return web.Response(text="Бот активен и работает", status=200)

async def run_bot():
    # Настройка Telegram приложения
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Настройка веб-сервера на порту 10000 для Render
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

    # Запуск Telegram бота
    async with application:
        # Сброс вебхуков, чтобы не было ошибки Conflict
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.initialize()
        await application.start()
        logger.info("🚀 СИСТЕМА ЗАПУЩЕНА: БОТ ГОТОВ ПРИНИМАТЬ СООБЩЕНИЯ")
        await application.updater.start_polling()

        # Бесконечный цикл работы
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную")