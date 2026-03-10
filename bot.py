import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Читаем ключи из переменных окружения Render
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_KEY = os.getenv('GEMINI_API_KEY')

# Проверка, что ключи загрузились
if not TOKEN or not API_KEY:
    raise ValueError("ОШИБКА: Ключи не найдены в Environment Variables на Render!")

# Инициализация Gemini
client = genai.Client(api_key=API_KEY)

# Загружаем вашу историю
try:
    with open('optimized_history.txt', 'r', encoding='utf-8') as f:
        context_data = f.read()
except FileNotFoundError:
    context_data = "История не найдена. Отвечай просто как обычный человек."

SYSTEM_PROMPT = f"Ты мой цифровой клон. Твой стиль общения основан на этой истории:\n{context_data}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    try:
        # Запрос к Gemini
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            config={'system_instruction': SYSTEM_PROMPT},
            contents=update.message.text
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Ошибка Gemini: {e}")

async def main():
    # Настройка бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот на Render запущен и готов к работе!")

    async with app:
        await app.updater.start_polling()
        await app.start()
        # Поддерживаем жизнь процесса
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())