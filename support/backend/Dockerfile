# Synap Support - Backend (Django)
# Python 3.11+
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput --settings=config.settings.local 2>/dev/null || true

EXPOSE 8250

# Arranque: migrate + gunicorn (puerto 8250 por defecto para Support)
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear && cd /tmp && exec gunicorn config.wsgi:application --bind 0.0.0.0:8250 --workers 2 --worker-tmp-dir /tmp --chdir /app"]
