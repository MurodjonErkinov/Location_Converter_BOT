# Engil Python image
FROM python:3.10-slim

# Ishchi katalog
WORKDIR /app

# Kutubxonalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyihani ko‘chiramiz
COPY . .

# Render Flask app’ni port orqali ishga tushiradi
ENV PORT=5000

# Flask’ga environment sozlash
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=$PORT

# Flask serverni ishga tushirish
CMD ["flask", "run"]
