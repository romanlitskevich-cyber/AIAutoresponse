import os
import logging
import asyncio
from aiohttp import web
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Инициализация клиента
client = genai.Client(api_key=GEMINI_KEY)

# СПИСОК МОДЕЛЕЙ ДЛЯ ПЕРЕБОРА (составлен на основе твоего списка доступных)
# Бот будет пробовать их строго по порядку сверху вниз
MODELS_TO_TRY = [
    "gemini-2.5-flash",       # Самая новая и сбалансированная
    "gemini-2.0-flash-lite",  # Самая легкая (обычно самые большие лимиты)
    "gemini-2.0-flash-001",   # Предыдущее стабильное поколение
    "gemini-2.5-pro",         # Мощная модель (на крайний случай)
    "gemma-3-27b-it"          # Открытая модель Google (если всё остальное лежит)
]

# --- ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"📩 НОВОЕ СООБЩЕНИЕ: {user_text}")

    response_text = None

    # Запускаем цикл перебора моделей
    for model_name in MODELS_TO_TRY:
        try:
            logger.info(f"🔄 Пробуем отправить запрос в {model_name}...")

            response = client.models.generate_content(
                model=model_name,
                contents=user_text
            )

            # Если ответ получен успешно, сохраняем его и ПРЕРЫВАЕМ цикл
            if response.text:
                response_text = response.text
                logger.info(f"✅ УСПЕХ! Ответила модель: {model_name}")
                break

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota" in error_msg:
                logger.warning(f"⚠️ Лимиты (429) для {model_name}. Иду к следующей...")
                continue # Переходим к следующей модели в списке
            else:
                logger.error(f"❌ Ошибка {model_name}: {error_msg}. Иду к следующей...")
                continue # При других ошибках тоже пробуем следующую

    # Проверяем, удалось ли хоть одной модели дать ответ
    if response_text:
        await update.message.reply_text(response_text)
    else:
        # Если цикл закончился, а ответа нет (все модели выдали ошибку)
        await update.message.reply_text(
            "Извини, сейчас все серверы нейросети перегружены или исчерпан лимит бесплатного тарифа (Ошибка 429). "
            "Пожалуйста, подожди немного или обнови API-ключ."
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот с умным переключением моделей. Напиши мне что-нибудь!")

# --- СЕРВЕР ДЛЯ RENDER (Health Check) ---
async def handle_health_check(request):
    return web.Response(text="Бот онлайн и готов перебирать модели!", status=200)

async def run_bot():
    # Настройка Telegram
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Настройка Web-сервера для Render
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 10000).start()

    # Запуск Telegram-бота с защитой от Conflict (409)
    async with application:
        logger.info("🧹 Очистка старых сессий (защита от Conflict)...")
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.initialize()
        await application.start()

        logger.info("🚀 СИСТЕМА ЗАПУЩЕНА")
        # Еще раз чистим очередь перед самым началом опроса
        await application.updater.start_polling(drop_pending_updates=True)

        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")