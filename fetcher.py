import sqlite3
import time
import requests
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_FILE = 'prices.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def fetch_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum",
        "vs_currencies": "usd"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        # Raise an HTTPError if the HTTP request returned an unsuccessful status code
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            logging.error("Rate limited by CoinGecko API.")
        else:
            logging.error(f"HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching prices: {e}")
        return None

def save_prices(data):
    if not data:
        return
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    
    try:
        if 'bitcoin' in data and 'usd' in data['bitcoin']:
            cursor.execute('INSERT INTO prices (symbol, price, timestamp) VALUES (?, ?, ?)', 
                           ('BTC', data['bitcoin']['usd'], timestamp))
        if 'ethereum' in data and 'usd' in data['ethereum']:
            cursor.execute('INSERT INTO prices (symbol, price, timestamp) VALUES (?, ?, ?)', 
                           ('ETH', data['ethereum']['usd'], timestamp))
        conn.commit()
        logging.info("Prices saved to database.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        conn.close()

def main():
    init_db()
    logging.info("Starting RippleAlert price fetcher...")
    
    backoff = 10
    
    while True:
        data = fetch_prices()
        if data:
            save_prices(data)
            backoff = 10 # reset backoff on success
            time.sleep(10)
        else:
            logging.warning(f"Retrying in {backoff} seconds...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300) # exponential backoff up to 5 mins

if __name__ == "__main__":
    main()
