FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8050 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=4 \
    GUNICORN_TIMEOUT=120 \
    APP_CONFIG_DIR=/app/runtime/config \
    APP_CONFIG_FILE=/app/runtime/config/kis_devlp.yaml \
    APP_ENV_FILE=/app/runtime/config/.env \
    KIS_TOKEN_DIR=/app/runtime/tokens \
    OHLCV_DIR=/app/runtime/ohlcv

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8050

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8050} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} stock_dashboard:app"]
