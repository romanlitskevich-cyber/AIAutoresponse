import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from aiohttp import web

# --- Health Check Server (чтобы HF открыл сеть) ---
async def health_check(request):
    return web.Response(text="Bot is running")

async def start_server():
    server = web.Application()
    server.add_routes([web.get('/', health_check)])
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 7860)
    await site.start()

# --- Логика Бота ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_KEY = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=API_KEY)

with open('optimized_history.txt', 'r', encoding='utf-8') as f:
    context_data = f.read()

SYSTEM_PROMPT = f"Ты мой цифровой клон. Пиши как я на основе истории:\n{context_data}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            config={'system_instruction': SYSTEM_PROMPT},
            contents=update.message.text
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Gemini Error: {e}")

async def main():
    # 1. Запускаем "заглушку" сервера для облака
    await start_server()

    # 2. Ждем чуть дольше, пока поднимется сеть
    print("Ожидание сети...")
    await asyncio.sleep(10)

    # 3. Запуск бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен!")
    async with app:
        await app.updater.start_polling()
        await app.start()
        # Держим цикл активным
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())