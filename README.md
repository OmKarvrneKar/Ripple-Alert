# RippleAlert

RippleAlert is a full-stack Python application that fetches the current price of Bitcoin (BTC) and Ethereum (ETH) in USD every 10 seconds. 

## Features
- **Standalone Price Fetcher (`fetcher.py`)**: Fetches real-time crypto prices every 10 seconds, stores them in SQLite, and publishes them to a Redis channel.
- **FastAPI Backend (`main.py`)**: Subscribes to the Redis pub/sub channel, provides user authentication (JWT + Bcrypt), and forwards live prices to browsers via WebSockets.
- **Alert Engine (`alert_engine.py`)**: Subscribes to Redis and checks live prices against user-defined alert rules (including rolling window percent changes), triggering and resetting alert logs automatically.
- **Alert History**: A historical log of all fired alerts is saved to SQLite and securely accessible via a dedicated `/alert-history` endpoint.
- **Dynamic Frontend**: A lightweight HTML/JS interface that instantly flashes live updates as prices arrive over the WebSocket connection without polling, and displays a history of triggered alerts.

- **PostgreSQL Database**: Robust persistent storage replacing SQLite for production.
- **Docker Compose Orchestration**: Containerized deployment for all services and databases.

## Prerequisites
- Docker and Docker Compose
- *Alternative*: Python 3.x and local Redis/Postgres instances.

## Installation & Local Docker Deployment

1. Clone or download the repository.
2. In the project directory, start all services using Docker Compose:
   ```bash
   docker-compose up --build
   ```
3. The following services will be orchestrated:
   - `web` (FastAPI backend on port 8000)
   - `worker` (Standalone fetcher process)
   - `alert-engine` (Alert rule processor)
   - `db` (PostgreSQL on port 5432)
   - `redis` (Redis broker on port 6379)
4. Open `frontend/index.html` in your web browser.
## Manual Deployment (Without Docker)

1. Run `pip install -r requirements.txt`
2. Set `DATABASE_URL`, `REDIS_HOST`, and `REDIS_PORT` in your environment.
3. Start the Fetcher: `python fetcher.py`
4. Start the Alert Engine: `python alert_engine.py`
5. Start the FastAPI server: `uvicorn main:app --port 8000`

## Architecture
- **PostgreSQL Database**: Unified database storing all historical price data, user accounts, and rules.
- **Redis**: Acts as the message broker decoupling the fetcher and the API server, and stores high-performance rolling window price caches for alert rule processing.
