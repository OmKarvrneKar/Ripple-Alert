FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# We don't define a CMD or ENTRYPOINT here so that docker-compose can specify them for each service.
