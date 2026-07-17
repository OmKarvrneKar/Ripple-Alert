import sqlite3
import redis
import json
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ALERT ENGINE - %(message)s')

USERS_DB = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(USERS_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def log_alert_history(conn, user_id, symbol, rule_description, triggered_price, timestamp):
    conn.execute('''
        INSERT INTO alert_history (user_id, symbol, rule_description, triggered_price, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, symbol, rule_description, triggered_price, timestamp))

def check_rules(redis_client, prices_data, timestamp_str):
    conn = get_db_connection()
    try:
        rules = conn.execute('''
            SELECT r.id, r.user_id, r.symbol, r.condition, r.threshold, r.window_minutes, r.is_currently_triggered, u.email 
            FROM rules r
            JOIN users u ON r.user_id = u.id
        ''').fetchall()
        
        # Update Redis sorted sets for percent change
        current_ts = datetime.fromisoformat(timestamp_str).timestamp()
        
        for symbol, current_price in prices_data.items():
            # Add to sorted set (value must be unique, so price_timestamp)
            redis_client.zadd(f"history:{symbol}", {f"{current_price}_{current_ts}": current_ts})
        
        for rule in rules:
            symbol = rule['symbol']
            if symbol not in prices_data:
                continue
                
            current_price = prices_data[symbol]
            threshold = rule['threshold']
            condition = rule['condition']
            is_triggered = bool(rule['is_currently_triggered'])
            window_minutes = rule['window_minutes']
            rule_id = rule['id']
            user_id = rule['user_id']
            email = rule['email']
            
            condition_met = False
            rule_description = ""
            
            if condition == "below" and current_price < threshold:
                condition_met = True
                rule_description = f"{symbol} below {threshold}"
            elif condition == "above" and current_price > threshold:
                condition_met = True
                rule_description = f"{symbol} above {threshold}"
            elif condition == "percent_change_in_window" and window_minutes:
                # Get historical prices in window
                start_ts = current_ts - (window_minutes * 60)
                history = redis_client.zrangebyscore(f"history:{symbol}", start_ts, current_ts)
                
                for entry in history:
                    old_price = float(entry.split('_')[0])
                    pct_change = abs(current_price - old_price) / old_price * 100
                    if pct_change >= threshold:
                        condition_met = True
                        rule_description = f"{symbol} moved {pct_change:.2f}% (>= {threshold}%) in {window_minutes} mins"
                        break
                
            if condition_met and not is_triggered:
                # Trigger alert
                logging.info(f"🚨 ALERT SENT 🚨 To: {email} | {rule_description} (Current: ${current_price})")
                conn.execute("UPDATE rules SET is_currently_triggered = 1 WHERE id = ?", (rule_id,))
                log_alert_history(conn, user_id, symbol, rule_description, current_price, timestamp_str)
                
            elif not condition_met and is_triggered:
                # Reset alert
                logging.info(f"🔄 ALERT RESET 🔄 {symbol} condition no longer met. Alert re-armed.")
                conn.execute("UPDATE rules SET is_currently_triggered = 0 WHERE id = ?", (rule_id,))
                log_alert_history(conn, user_id, symbol, f"RESET: {symbol} condition no longer met", current_price, timestamp_str)
                
        # Clean up old data from redis (keep last 24h max)
        for symbol in prices_data.keys():
            redis_client.zremrangebyscore(f"history:{symbol}", "-inf", current_ts - 86400)
            
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
            timestamp_str = data.get("timestamp")
            if prices and timestamp_str:
                check_rules(r, prices, timestamp_str)

if __name__ == "__main__":
    while True:
        try:
            main()
        except redis.ConnectionError:
            logging.error("Redis connection lost. Retrying in 5 seconds...")
            time.sleep(5)
