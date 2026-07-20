import sys

with open('e:/Application/RippleAlert/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_loop = """    for row in historical_prices:
        current_price = row['price']
        # Depending on DB, timestamp might be string or datetime
        if isinstance(row['timestamp'], str):
            from datetime import datetime
            current_ts = datetime.fromisoformat(row['timestamp']).timestamp()
        else:
            current_ts = row['timestamp'].timestamp()
            
        condition_met = False
        
        if rule.condition == 'below' and current_price < rule.threshold:
            condition_met = True
        elif rule.condition == 'above' and current_price > rule.threshold:
            condition_met = True
            
        # We skip percent_change_in_window for backtest to avoid complexity for now
        
        in_cooldown = False
        if last_trigger_ts > 0 and (current_ts - last_trigger_ts) < cooldown_seconds:
            in_cooldown = True
            
        if condition_met and not is_triggered:
            if not in_cooldown:
                is_triggered = True
                last_trigger_ts = current_ts
                triggers.append({
                    "timestamp": row['timestamp'],
                    "price": current_price,
                    "description": f"{symbol} {rule.condition} {rule.threshold}"
                })
        elif not condition_met and is_triggered:
            is_triggered = False"""

new_loop = """    price_history = []
    
    for row in historical_prices:
        current_price = row['price']
        if isinstance(row['timestamp'], str):
            from datetime import datetime
            current_ts = datetime.fromisoformat(row['timestamp']).timestamp()
        else:
            current_ts = row['timestamp'].timestamp()
            
        condition_met = False
        rule_description = ''
        
        if rule.condition == 'below' and current_price < rule.threshold:
            condition_met = True
            rule_description = f"{symbol} below {rule.threshold}"
        elif rule.condition == 'above' and current_price > rule.threshold:
            condition_met = True
            rule_description = f"{symbol} above {rule.threshold}"
        elif rule.condition == 'percent_change_in_window' and rule.window_minutes:
            window_sec = rule.window_minutes * 60
            # Clean old prices outside window
            price_history = [p for p in price_history if p[0] >= current_ts - window_sec]
            
            for old_ts, old_price in price_history:
                pct_change = abs(current_price - old_price) / old_price * 100
                if pct_change >= rule.threshold:
                    condition_met = True
                    rule_description = f"{symbol} moved {pct_change:.2f}% (>= {rule.threshold}%) in {rule.window_minutes} mins"
                    break
        
        price_history.append((current_ts, current_price))
        
        in_cooldown = False
        if last_trigger_ts > 0 and (current_ts - last_trigger_ts) < cooldown_seconds:
            in_cooldown = True
            
        if condition_met and not is_triggered:
            if not in_cooldown:
                is_triggered = True
                last_trigger_ts = current_ts
                triggers.append({
                    "timestamp": row['timestamp'],
                    "price": current_price,
                    "description": rule_description
                })
        elif not condition_met and is_triggered:
            is_triggered = False"""

if old_loop in content:
    content = content.replace(old_loop, new_loop)
    with open('e:/Application/RippleAlert/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done!')
else:
    print('Target not found')
