FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 devlens
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY services ./services
COPY alembic.ini LICENSE ./
RUN pip install --no-cache-dir -c requirements.lock .
USER devlens
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn devlens.main:app --host 0.0.0.0 --port 8000 --workers 1"]
