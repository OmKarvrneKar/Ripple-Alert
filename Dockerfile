FROM python:3.11-slim

WORKDIR /app

# Install dependencies required for psycopg2 compilation
RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables will be overridden by docker-compose
ENV PYTHONUNBUFFERED=1
