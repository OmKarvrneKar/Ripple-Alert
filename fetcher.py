import os
import psycopg2
import psycopg2.extras
import time
import requests
import logging
from datetime import datetime
import redis
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables with defaults
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/ripplealert")
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Connect to Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def get_db_connection():
    db_url = DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id SERIAL PRIMARY KEY,
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

def process_and_publish(data):
    if not data:
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    prices_update = {}
    
    try:
        if 'bitcoin' in data and 'usd' in data['bitcoin']:
            btc_price = data['bitcoin']['usd']
            cursor.execute('INSERT INTO prices (symbol, price, timestamp) VALUES (%s, %s, %s)', 
                           ('BTC', btc_price, timestamp))
            prices_update['BTC'] = btc_price
            
        if 'ethereum' in data and 'usd' in data['ethereum']:
            eth_price = data['ethereum']['usd']
            cursor.execute('INSERT INTO prices (symbol, price, timestamp) VALUES (%s, %s, %s)', 
                           ('ETH', eth_price, timestamp))
            prices_update['ETH'] = eth_price
            
        conn.commit()
        logging.info("Prices saved to database.")
        
        # Publish to Redis
        payload = {
            "type": "prices",
            "data": prices_update,
            "timestamp": timestamp
        }
        redis_client.publish("prices", json.dumps(payload))
        logging.info("Prices published to Redis channel 'prices'.")
        
    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
    except redis.RedisError as e:
        logging.error(f"Redis error: {e}")
    finally:
        conn.close()

def main():
    import time
    max_retries = 5
    for i in range(max_retries):
        try:
            init_db()
            break
        except Exception as e:
            logging.error(f"Could not init DB (attempt {i+1}/{max_retries}): {e}")
            time.sleep(3)
            
    logging.info("Starting standalone RippleAlert price fetcher...")
    
    backoff = 10
    
    while True:
        data = fetch_prices()
        if data:
            process_and_publish(data)
            backoff = 10 # reset backoff on success
            time.sleep(10)
        else:
            logging.warning(f"Retrying in {backoff} seconds...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300) # exponential backoff up to 5 mins

if __name__ == "__main__":
    main()
