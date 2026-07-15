import sqlite3
import redis
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ALERT ENGINE - %(message)s')

USERS_DB = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(USERS_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def check_rules(prices):
    conn = get_db_connection()
    try:
        rules = conn.execute('''
            SELECT r.id, r.user_id, r.symbol, r.condition, r.threshold, r.is_currently_triggered, u.email 
            FROM rules r
            JOIN users u ON r.user_id = u.id
        ''').fetchall()
        
        for rule in rules:
            symbol = rule['symbol']
            if symbol not in prices:
                continue
                
            current_price = prices[symbol]
            threshold = rule['threshold']
            condition = rule['condition']
            is_triggered = bool(rule['is_currently_triggered'])
            rule_id = rule['id']
            email = rule['email']
            
            condition_met = False
            if condition == "below" and current_price < threshold:
                condition_met = True
            elif condition == "above" and current_price > threshold:
                condition_met = True
                
            if condition_met and not is_triggered:
                # Trigger alert
                logging.info(f"🚨 ALERT SENT 🚨 To: {email} | {symbol} is {condition} {threshold} (Current: ${current_price})")
                conn.execute("UPDATE rules SET is_currently_triggered = 1 WHERE id = ?", (rule_id,))
                
            elif not condition_met and is_triggered:
                # Reset alert
                logging.info(f"🔄 ALERT RESET 🔄 {symbol} is no longer {condition} {threshold} (Current: ${current_price}). Alert re-armed.")
                conn.execute("UPDATE rules SET is_currently_triggered = 0 WHERE id = ?", (rule_id,))
                
        conn.commit()
    except sqlite3.OperationalError as e:
        logging.error(f"Database error: {e}")
    finally:
        conn.close()

def main():
    logging.info("Starting standalone RippleAlert Alert Engine...")
    r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe("prices")
    
    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            prices = data.get("data", {})
            if prices:
                check_rules(prices)

if __name__ == "__main__":
    while True:
        try:
            main()
        except redis.ConnectionError:
            logging.error("Redis connection lost. Retrying in 5 seconds...")
            time.sleep(5)
