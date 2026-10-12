FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY backend ./backend
COPY ml ./ml
COPY scripts ./scripts
COPY alembic.ini ./
RUN useradd --create-home playerworth && chown -R playerworth:playerworth /app
USER playerworth
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
