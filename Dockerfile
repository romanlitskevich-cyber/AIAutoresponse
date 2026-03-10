FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Мы НЕ копируем secrets.txt в образ, Render сам подложит его при запуске
CMD ["python", "bot.py"]