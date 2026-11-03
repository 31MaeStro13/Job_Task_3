FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8001

WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependencies lock
COPY pyproject.toml uv.lock ./

# Install python dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Collect static files and apply migrations
RUN uv run python manage.py collectstatic --noinput && \
    uv run python manage.py migrate --noinput

EXPOSE 8001

CMD ["sh", "-c", "uv run gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8001} --workers 2 --threads 4"]
