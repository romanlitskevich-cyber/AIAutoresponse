import os
import asyncio
import logging
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from aiohttp import web

# Настройка логирования в консоль Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 1. HEALTH CHECK СЕРВЕР ---
async def handle_hc(request):
    return web.Response(text="Бот живой!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"✅ Веб-сервер запущен на порту {port}")

# --- 2. ДАННЫЕ И КОНТЕКСТ ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_KEY = os.environ.get('GEMINI_API_KEY')

def get_context_safe():
    try:
        if os.path.exists('optimized_history.txt'):
            with open('optimized_history.txt', 'r', encoding='utf-8') as f:
                # Берем только последние 15к символов для гарантии работы на Free Tier
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - 15000))
                return f.read()
    except Exception as e:
        logger.error(f"Ошибка чтения истории: {e}")
    return "Стиль: общайся как человек."

# --- 3. ОБРАБОТКА СООБЩЕНИЙ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если это не текстовое сообщение — игнорируем
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    logger.info(f"📩 НОВОЕ СООБЩЕНИЕ: {user_text}")

    try:
        client = genai.Client(api_key=API_KEY)
        history_snippet = get_context_safe()

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            config={
                'system_instruction': f"Ты мой цифровой клон. Твой стиль:\n{history_snippet}"
            },
            contents=user_text
        )

        if response and response.text:
            logger.info(f"🤖 ОТВЕТ GEMINI: {response.text[:50]}...")
            await update.message.reply_text(response.text)
        else:
            logger.warning("⚠️ Gemini вернул пустой результат")

    except Exception as e:
        logger.error(f"❌ ОШИБКА ОБРАБОТКИ: {e}")

# --- 4. ГЛАВНЫЙ ЗАПУСК ---
async def main():
    # Сначала запускаем сервер, чтобы Render не убил деплой
    await start_web_server()

    if not TOKEN or not API_KEY:
        logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: Токены не заданы в Environment Variables!")
        return

    # Инициализация приложения
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()

    # КЛЮЧЕВОЙ МОМЕНТ: Удаляем старые вебхуки и чистим очередь
    logger.info("♻️ Сброс старых соединений Telegram...")
    await app.bot.delete_webhook(drop_pending_updates=True)

    await app.start()
    await app.updater.start_polling()

    logger.info("🚀 БОТ ПОЛНОСТЬЮ ЗАПУЩЕН И СЛУШАЕТ TELEGRAM")

    # Держим процесс активным
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")