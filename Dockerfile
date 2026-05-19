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
# Render runtime o'zi PORT beradi; Dockerfile'da default qo'yib ketamiz
ENV PORT=5000

# Gunicorn orqali ishga tushirish (Render uchun ishonchliroq)
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile -"]
