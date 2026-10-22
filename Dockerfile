FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATABASE_PATH=/data/cars.db

EXPOSE 5000

CMD ["sh", "-c", "python -c 'from database import init_db; init_db()' && exec gunicorn --bind 0.0.0.0:5000 --workers 2 --access-logfile - --error-logfile - app:app"]
 