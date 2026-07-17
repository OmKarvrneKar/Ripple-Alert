import psycopg2
import time
import requests
import logging
from datetime import datetime
import redis
import json
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ripplealert")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Connect to Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                price DOUBLE PRECISION NOT NULL,
                timestamp VARCHAR NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        # Could sleep and retry here if DB is not up yet

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
        
    timestamp = datetime.utcnow().isoformat()
    prices_update = {}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        conn.close()
        
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

def main():
    while True:
        try:
            init_db()
            break
        except Exception:
            logging.error("Waiting for database...")
            time.sleep(5)
            
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
