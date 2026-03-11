import os
import logging
import asyncio
from aiohttp import web
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ ЛОГИРОВАНИЯ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
HISTORY_FILE = "optimized_history.txt"  # Твой оптимизированный файл

client = genai.Client(api_key=GEMINI_KEY)

# --- ЗАГРУЗКА БАЗЫ ЗНАНИЙ ---
def load_personality():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"✅ База стиля загружена: {len(content)} символов")
                return content
        except Exception as e:
            logger.error(f"❌ Ошибка чтения файла: {e}")
    return "Примеры переписки отсутствуют. Отвечай вежливо и кратко."

MY_STYLE = load_personality()

# Системная инструкция, которая делает из нейронки тебя
SYSTEM_INSTRUCTION = f"""
Ты — цифровая копия владельца этого аккаунта. Твоя цель — отвечать на входящие сообщения в Telegram точно так же, как это сделал бы он.

ПРАВИЛА:
1. Изучи 'БАЗУ СТИЛЯ' ниже. Обрати внимание на: длину фраз, использование сленга, наличие или отсутствие заглавных букв, любимые эмодзи и манеру здороваться/прощаться.
2. Отвечай максимально похоже. Если владелец пишет кратко — отвечай кратко.
3. НИКОГДА не упоминай, что ты ИИ, бот или Gemini. Ты — это он.
4. Если вопрос слишком личный или сложный, ответь в своем стиле: "я ща занят, позже гляну" или что-то подобное.

БАЗА СТИЛЯ (ПРИМЕРЫ ТВОИХ ОТВЕТОВ):
---
{MY_STYLE}
---
"""

# --- ОБРАБОТКА СООБЩЕНИЙ ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"📩 Входящее от {update.effective_user.first_name}: {user_text}")

    # Список моделей: 2.5 Flash в приоритете
    models = ["gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash"]

    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.8, # Чуть выше для естественности
                    top_p=0.95,
                )
            )

            if response.text:
                await update.message.reply_text(response.text)
                logger.info(f"✅ Успешный ответ от {model_name}")
                return
        except Exception as e:
            logger.warning(f"⚠️ Модель {model_name} выдала ошибку: {e}")
            continue

    await update.message.reply_text("Я сейчас не на связи, отвечу как освобожусь!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Автоответчик в твоем стиле запущен и готов к работе.")

# --- СЕРВЕР ДЛЯ RENDER ---
async def handle_health_check(request):
    return web.Response(text="Bot is alive", status=200)

async def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 10000).start()

    async with application:
        # Защита от Conflict (409)
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.initialize()
        await application.start()
        logger.info("🚀 СИСТЕМА ПОЛНОСТЬЮ ЗАПУЩЕНА")
        await application.updater.start_polling(drop_pending_updates=True)

        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")