FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    bash \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir aider-chat

WORKDIR /workspace
