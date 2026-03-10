import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Читаем ключи напрямую из переменных окружения
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_KEY = os.environ.get('GEMINI_API_KEY')

if not TOKEN or not API_KEY:
    raise ValueError("КРИТИЧЕСКАЯ ОШИБКА: Переменные TELEGRAM_BOT_TOKEN или GEMINI_API_KEY не заданы в настройках Render!")

# Инициализация Gemini
client = genai.Client(api_key=API_KEY)

# Загружаем вашу историю (файл должен быть в репозитории на GitHub)
try:
    with open('optimized_history.txt', 'r', encoding='utf-8') as f:
        context_data = f.read()
except FileNotFoundError:
    context_data = "Инструкция: отвечай как живой человек в чате."

SYSTEM_PROMPT = f"Ты мой цифровой клон. Твой стиль общения полностью основан на этой истории:\n{context_data}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Игнорируем всё, кроме текста
    if not update.message or not update.message.text:
        return

    try:
        # Запрос к Gemini через актуальный SDK
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            config={'system_instruction': SYSTEM_PROMPT},
            contents=update.message.text
        )
        if response.text:
            await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Ошибка Gemini: {e}")

async def main():
    # Настройка Telegram бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот успешно запущен и использует переменные окружения!")

    async with app:
        await app.updater.start_polling()
        await app.start()
        # Поддерживаем жизнь процесса бесконечным циклом
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass