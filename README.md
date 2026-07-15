# RippleAlert

RippleAlert is a full-stack Python application that fetches the current price of Bitcoin (BTC) and Ethereum (ETH) in USD every 10 seconds. 

## Features
- **Standalone Price Fetcher (`fetcher.py`)**: Fetches real-time crypto prices every 10 seconds, stores them in SQLite, and publishes them to a Redis channel.
- **FastAPI Backend (`main.py`)**: Subscribes to the Redis pub/sub channel, provides user authentication (JWT + Bcrypt), and forwards live prices to browsers via WebSockets.
- **Alert Engine (`alert_engine.py`)**: Subscribes to Redis and checks live prices against user-defined alert rules (including rolling window percent changes), triggering and resetting alert logs automatically.
- **Alert History**: A historical log of all fired alerts is saved to SQLite and securely accessible via a dedicated `/alert-history` endpoint.
- **Dynamic Frontend**: A lightweight HTML/JS interface that instantly flashes live updates as prices arrive over the WebSocket connection without polling, and displays a history of triggered alerts.

## Prerequisites
- Python 3.x
- `pip` package manager
- Redis (Running locally on port 6379, e.g., via `docker run -d -p 6379:6379 redis`)

## Installation

1. Clone or download the repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start Redis**:
   ```bash
   docker run -d -p 6379:6379 redis
   ```
2. **Start the Fetcher** (in a new terminal):
   ```bash
   python fetcher.py
   ```
3. **Start the API Server** (in a new terminal):
   ```bash
   python -m uvicorn main:app --port 8000
   ```
4. **Start the Alert Engine** (in a new terminal):
   ```bash
   python alert_engine.py
   ```
5. **Open the Frontend**:
   Open `frontend/index.html` in your web browser.

## Architecture
- **prices.db**: SQLite DB storing all historical price data.
- **users.db**: SQLite DB storing user accounts (secured with bcrypt) and watchlists safely.
- **Redis**: Acts as the message broker decoupling the fetcher and the API server.
