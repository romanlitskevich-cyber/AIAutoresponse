import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from aiohttp import web

# --- 1. HEALTH CHECK ДЛЯ RENDER ---
async def handle_hc(request):
    return web.Response(text="Alive")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_hc)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web Port {port} opened")

# --- 2. НАСТРОЙКИ ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_KEY = os.environ.get('GEMINI_API_KEY')

def load_context():
    try:
        if os.path.exists('optimized_history.txt'):
            with open('optimized_history.txt', 'r', encoding='utf-8') as f:
                # Берем только последние 20 000 символов для стабильности
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 20000))
                return f.read()
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
    return "Стиль: кратко."

# --- 3. ОБРАБОТКА ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    print(f"📩 Получено сообщение: {user_text}") # Увидишь это в логах Render

    try:
        client = genai.Client(api_key=API_KEY)
        my_context = load_context()

        # Используем полный путь к модели, чтобы избежать 404
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            config={
                'system_instruction': f"Ты мой цифровой клон. База твоей личности:\n{my_context}"
            },
            contents=user_text
        )

        if response and response.text:
            print(f"🤖 Ответ Gemini: {response.text[:50]}...")
            await update.message.reply_text(response.text)
        else:
            print("⚠️ Gemini прислал пустой ответ")

    except Exception as e:
        print(f"❌ Ошибка при обработке: {e}")

# --- 4. ЗАПУСК ---
async def main():
    await start_web_server()

    if not TOKEN or not API_KEY:
        print("❌ Ключи не найдены в Environment Variables!")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()
    await app.start()
    # Чистим очередь, чтобы бот не завис на старых сообщениях
    await app.updater.start_polling(drop_pending_updates=True)

    print("🚀 БОТ ЗАПУЩЕН И ЖДЕТ СООБЩЕНИЙ")
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())