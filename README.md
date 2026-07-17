# RippleAlert

RippleAlert is a full-stack Python application that fetches the current price of Bitcoin (BTC) and Ethereum (ETH) in USD every 10 seconds. 

## Features
- **Standalone Price Fetcher (`fetcher.py`)**: Fetches real-time crypto prices every 10 seconds, stores them in PostgreSQL, and publishes them to a Redis channel.
- **FastAPI Backend (`main.py`)**: Subscribes to the Redis pub/sub channel, provides user authentication (JWT + Bcrypt), and forwards live prices to browsers via WebSockets.
- **Alert Engine (`alert_engine.py`)**: Subscribes to Redis and checks live prices against user-defined alert rules (including rolling window percent changes), triggering and resetting alert logs automatically.
- **Alert History**: A historical log of all fired alerts is saved to PostgreSQL and securely accessible via a dedicated `/alert-history` endpoint.
- **Dynamic Frontend**: A lightweight HTML/JS interface that instantly flashes live updates as prices arrive over the WebSocket connection without polling, and displays a history of triggered alerts.

## Tech Stack
- **Backend**: Python (FastAPI, Uvicorn, Requests, Psycopg2)
- **Database**: PostgreSQL
- **Message Broker & Time-Series Cache**: Redis
- **Security**: PyJWT, passlib[bcrypt]
- **Frontend**: Vanilla HTML/JS/CSS (WebSocket integrated)
- **Deployment**: Docker & Docker Compose, GitHub Actions for CI/CD

## Running the Application Locally (Docker Compose)
The easiest way to run the entire RippleAlert ecosystem is using Docker Compose.

1. Clone or download the repository.
2. Start all services:
   ```bash
   docker-compose up --build -d
   ```
   This will spin up:
   - PostgreSQL on port 5432
   - Redis on port 6379
   - FastAPI (`web`) on port 8000
   - The price fetcher background process (`worker`)
   - The rule evaluation system (`alert-engine`)

3. **Access the Dashboard**:
   Open `frontend/index.html` in your web browser. Or serve it via a simple HTTP server (e.g., `python -m http.server 8080 -d frontend`).

## Architecture
- **PostgreSQL**: Stores all historical price data, user accounts (secured with bcrypt), watchlists, and alert history.
- **Redis**: Acts as the message broker decoupling the fetcher and the API server, and provides time-series sorted sets for rolling window calculations.
