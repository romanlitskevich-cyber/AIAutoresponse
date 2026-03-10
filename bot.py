import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from aiohttp import web

# --- Health Check сервер для бесплатного тарифа Render ---
async def health_check(request):
    return web.Response(text="Bot is alive")

async def start_health_server():
    app = web.Application()
    app.add_routes([web.get('/', health_check)])
    runner = web.AppRunner(app)
    await runner.setup()
    # Render всегда дает порт в переменную PORT
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health server started on port {port}")

# --- Настройки ---
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_KEY = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=API_KEY)

# Читаем историю и берем только последние 500 000 символов (чтобы влезть в лимит)
try:
    with open('optimized_history.txt', 'r', encoding='utf-8') as f:
        full_context = f.read()
        context_data = full_context[-500000:] # Берем только хвост файла
except FileNotFoundError:
    context_data = "Пиши как обычный человек."

SYSTEM_PROMPT = f"Ты мой цифровой клон. Твой стиль общения основан на этой истории:\n{context_data}"

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
    await start_health_server() # Запуск "заглушки" порта

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен!")
    async with app:
        await app.updater.start_polling()
        await app.start()
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())