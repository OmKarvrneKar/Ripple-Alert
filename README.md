# RippleAlert

RippleAlert is a simple Python script that fetches the current price of Bitcoin (BTC) and Ethereum (ETH) in USD from the free CoinGecko API every 10 seconds. The prices are stored in a local SQLite database (`prices.db`).

## Features
- Fetches real-time crypto prices every 10 seconds.
- Stores historical price data in a SQLite database.
- Gracefully handles API rate limiting and connection errors with exponential backoff.

## Prerequisites
- Python 3.x
- `pip` package manager

## Installation

1. Clone or download the repository (or navigate to the project folder).
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the fetcher script:
```bash
python fetcher.py
```

Press `Ctrl+C` to stop the script.

## Database Schema
The data is stored in `prices.db` with the following schema:
- `id`: Integer Primary Key
- `symbol`: Text (e.g., 'BTC', 'ETH')
- `price`: Real (e.g., 50000.0)
- `timestamp`: Text (ISO 8601 format)

# Ripple-Alert
