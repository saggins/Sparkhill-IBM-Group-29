FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/opt/fastembed \
    SQLITE_PATH=/data/db.sqlite3 \
    DEBUG=False

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image so first request needs no download.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')"

COPY lib/ lib/
COPY backend/ backend/

WORKDIR /app/backend

# Settings demand these at import time; build-only placeholders.
RUN SECRET_KEY=build GOOGLE_OAUTH_CLIENT_ID=build python manage.py collectstatic --noinput

RUN useradd --create-home app && mkdir -p /data && chown app /data
USER app

VOLUME /data
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-2}"]
