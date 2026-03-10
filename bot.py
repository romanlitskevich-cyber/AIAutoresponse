import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from aiohttp import web

# --- 1. СЕРВЕР ДЛЯ RENDER (Health Check) ---
async def handle_render_check(request):
    return web.Response(text="Bot is healthy and running")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_render_check)
    runner = web.AppRunner(app)
    await runner.setup()

    # Render передает номер порта в переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Веб-сервер запущен на порту {port}. Render должен быть доволен!")

# --- 2. ЛОГИКА БОТА ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_KEY = os.environ.get('GEMINI_API_KEY')

# Ограничиваем чтение истории, чтобы не превысить лимит 512MB RAM на Render
def get_context():
    try:
        with open('optimized_history.txt', 'r', encoding='utf-8') as f:
            # Читаем последние 200к символов (этого более чем достаточно для стиля)
            content = f.read()
            return content[-200000:]
    except:
        return "Отвечай кратко."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    try:
        client = genai.Client(api_key=API_KEY)
        context_data = get_context()

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            config={'system_instruction': f"Ты мой цифровой клон. Стиль:\n{context_data}"},
            contents=update.message.text
        )
        if response.text:
            await update.message.reply_text(response.text)
    except Exception as e:
        print(f"❌ Ошибка Gemini: {e}")

async def main():
    # ШАГ 1: Сначала запускаем веб-сервер, чтобы Render не выдал Timed Out
    await start_web_server()

    # ШАГ 2: Запускаем бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Бот запущен и готов к работе в Telegram!")

    async with app:
        await app.updater.start_polling()
        await app.start()
        # Бесконечный цикл, чтобы программа не завершалась
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass