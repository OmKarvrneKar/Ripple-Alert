import os
import psycopg2
import psycopg2.extras
import redis
import json
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ALERT ENGINE - %(message)s')

# Environment variables with defaults
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/ripplealert")
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

def get_db_connection():
    db_url = DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(db_url)
    return conn

def log_alert_history(conn, user_id, symbol, rule_description, triggered_price, timestamp):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO alert_history (user_id, symbol, rule_description, triggered_price, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_id, symbol, rule_description, triggered_price, timestamp))
    cursor.close()

def evaluate_rule(rule, current_price, current_ts, redis_client):
    condition = rule['condition']
    threshold = rule['threshold']
    symbol = rule['symbol']
    window_minutes = rule.get('window_minutes')
    
    condition_met = False
    rule_description = ""
    
    if condition == "below" and current_price < threshold:
        condition_met = True
        rule_description = f"{symbol} below {threshold}"
    elif condition == "above" and current_price > threshold:
        condition_met = True
        rule_description = f"{symbol} above {threshold}"
    elif condition == "percent_change_in_window" and window_minutes:
        start_ts = current_ts - (window_minutes * 60)
        history = redis_client.zrangebyscore(f"history:{symbol}", start_ts, current_ts)
        
        for entry in history:
            old_price = float(entry.split('_')[0])
            pct_change = abs(current_price - old_price) / old_price * 100
            if pct_change >= threshold:
                condition_met = True
                rule_description = f"{symbol} moved {pct_change:.2f}% (>= {threshold}%) in {window_minutes} mins"
                break
                
    return condition_met, rule_description

def check_rules(redis_client, prices_data, timestamp_str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT r.id, r.user_id, r.symbol, r.condition, r.threshold, r.window_minutes, r.is_currently_triggered, r.logic_operator, r.parent_rule_id, u.email 
            FROM rules r
            JOIN users u ON r.user_id = u.id
        ''')
        rules = cursor.fetchall()
        
        # Update Redis sorted sets for percent change
        current_ts = datetime.fromisoformat(timestamp_str).timestamp()
        
        for symbol, current_price in prices_data.items():
            # Add to sorted set (value must be unique, so price_timestamp)
            redis_client.zadd(f"history:{symbol}", {f"{current_price}_{current_ts}": current_ts})
        
        parent_rules = [r for r in rules if r['parent_rule_id'] is None]
        child_rules = [r for r in rules if r['parent_rule_id'] is not None]
        
        children_by_parent = {}
        for c in child_rules:
            if c['parent_rule_id'] not in children_by_parent:
                children_by_parent[c['parent_rule_id']] = []
            children_by_parent[c['parent_rule_id']].append(c)
            
        for rule in parent_rules:
            is_triggered = bool(rule['is_currently_triggered'])
            rule_id = rule['id']
            user_id = rule['user_id']
            email = rule['email']
            
            if rule['logic_operator']:
                children = children_by_parent.get(rule_id, [])
                if not children:
                    continue
                    
                child_results = []
                for child in children:
                    if child['symbol'] not in prices_data:
                        child_results.append((False, ""))
                    else:
                        child_results.append(evaluate_rule(child, prices_data[child['symbol']], current_ts, redis_client))
                
                if rule['logic_operator'] == 'AND':
                    condition_met = all(res[0] for res in child_results)
                    rule_description = " AND ".join([res[1] for res in child_results if res[1]]) if condition_met else ""
                elif rule['logic_operator'] == 'OR':
                    condition_met = any(res[0] for res in child_results)
                    rule_description = " OR ".join([res[1] for res in child_results if res[0]]) if condition_met else ""
                else:
                    condition_met = False
                    rule_description = ""
                    
                symbol_to_log = "MULTI"
                price_to_log = 0.0
                
            else:
                symbol = rule['symbol']
                if symbol not in prices_data:
                    continue
                    
                current_price = prices_data[symbol]
                condition_met, rule_description = evaluate_rule(rule, current_price, current_ts, redis_client)
                symbol_to_log = symbol
                price_to_log = current_price
                
            if condition_met and not is_triggered:
                # Trigger alert
                logging.info(f"🚨 ALERT SENT 🚨 To: {email} | {rule_description}")
                cursor.execute("UPDATE rules SET is_currently_triggered = TRUE WHERE id = %s", (rule_id,))
                log_alert_history(conn, user_id, symbol_to_log, rule_description, price_to_log, timestamp_str)
                
            elif not condition_met and is_triggered:
                # Reset alert
                logging.info(f"🔄 ALERT RESET 🔄 {symbol_to_log} condition no longer met. Alert re-armed.")
                cursor.execute("UPDATE rules SET is_currently_triggered = FALSE WHERE id = %s", (rule_id,))
                log_alert_history(conn, user_id, symbol_to_log, f"RESET: condition no longer met", price_to_log, timestamp_str)
                
        # Clean up old data from redis (keep last 24h max)
        for symbol in prices_data.keys():
            redis_client.zremrangebyscore(f"history:{symbol}", "-inf", current_ts - 86400)
            
        conn.commit()
        cursor.close()
    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        conn.close()

def main():
    logging.info("Starting standalone RippleAlert Alert Engine...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
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
