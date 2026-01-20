
# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install deps from app/requirements.txt
COPY app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt



COPY app/ /app/


EXPOSE 8080

RUN useradd -r -u 10001 appuser && chown -R appuser:appuser /app
USER 10001

CMD ["python", "main.py"]
