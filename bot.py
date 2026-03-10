import os
import logging
import asyncio
from aiohttp import web
from google import genai  # Библиотека нового поколения (2026)
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Чтение переменных из Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация клиента Gemini
client = genai.Client(api_key=GEMINI_KEY)

# --- ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"📩 НОВОЕ СООБЩЕНИЕ от {update.effective_user.first_name}: {user_text}")

    try:
        # Пробуем стандартную модель 1.5 Flash
        # В новом SDK 2026 года пишем просто название без префиксов
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_text
        )

        if response.text:
            await update.message.reply_text(response.text)
            logger.info("✅ ОТВЕТ УСПЕШНО ОТПРАВЛЕН")
        else:
            await update.message.reply_text("Бот получил пустой ответ. Попробуйте другой вопрос.")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ ОШИБКА GEMINI: {error_msg}")

        # ЕСЛИ ОШИБКА 404 — ЗАПУСКАЕМ ДИАГНОСТИКУ
        if "404" in error_msg:
            try:
                # Спрашиваем у Google, какие модели доступны этому ключу
                available_models = client.models.list()
                model_list = "\n".join([m.name for m in available_models])
                diag_message = (
                    "⚠️ Ошибка 404: Модель не найдена.\n\n"
                    f"Вашему ключу доступны эти модели:\n{model_list}\n\n"
                    "Пожалуйста, перешлите этот список разработчику."
                )
                await update.message.reply_text(diag_message)
            except Exception as diag_e:
                await update.message.reply_text(f"Критическая ошибка доступа к API: {diag_e}")
        else:
            await update.message.reply_text("Произошла ошибка в работе нейросети. Мы уже чиним!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Бот запущен! Напиши мне что-нибудь, и Gemini ответит.")

# --- СЕРВЕР ДЛЯ RENDER (Health Check) ---
async def handle_health_check(request):
    return web.Response(text="Бот онлайн", status=200)

async def run_bot():
    # Инициализация Telegram
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск мини-сервера для Render на порту 10000
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 10000).start()

    # Запуск процесса опроса Telegram (Polling)
    async with application:
        # Очищаем очередь старых сообщений, чтобы бот не спамил при включении
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.initialize()
        await application.start()
        logger.info("🤖 БОТ ПОДКЛЮЧЕН К TELEGRAM И ГОТОВ")
        await application.updater.start_polling()

        # Поддержка работы скрипта
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот выключен.")