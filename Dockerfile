FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .

COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY tests/ ./tests/

RUN pip install --no-cache-dir -e .

COPY . .

ENV PYTHONPATH=/app/src

RUN git config --global --add safe.directory /app

EXPOSE 8000

CMD ["python", "-m", "autonode.__main__"]