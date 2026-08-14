import sys

with open('e:/Application/RippleAlert/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Part 1: Add BacktestRequest
old_class = """class SnoozeRequest(BaseModel):
    duration_minutes: float"""

new_class = """class SnoozeRequest(BaseModel):
    duration_minutes: float

class BacktestRequest(BaseModel):
    rule: RuleCreate
    days: int = 7"""

if old_class in content:
    content = content.replace(old_class, new_class)
else:
    print("Could not find SnoozeRequest")
    sys.exit(1)

# Part 2: Add POST /rules/backtest
# Before @app.post("/rules")
old_route = """@app.post("/rules")
def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):"""

new_route = """@app.post("/rules/backtest")
def backtest_rule(req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    rule = req.rule
    days = req.days
    
    # We only support backtesting single price rules for now to keep it simple, 
    # but let's allow it to fetch data for the symbol
    if rule.rule_type != 'price' or not rule.symbol:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Backtesting currently supports single symbol price rules")
        
    symbol = rule.symbol.upper()
    
    cursor.execute('''
        SELECT price, timestamp FROM prices 
        WHERE symbol = %s AND timestamp >= NOW() - INTERVAL '%s days'
        ORDER BY timestamp ASC
    ''', (symbol, days))
    
    historical_prices = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not historical_prices:
        return {"triggers": [], "message": "No historical data found for backtest period."}
        
    triggers = []
    is_triggered = False
    last_trigger_ts = 0
    cooldown_seconds = (rule.cooldown_minutes or 0) * 60
    
    # We won't simulate percent_change_in_window perfectly without a rolling buffer, 
    # but we can do a naive evaluation for above/below
    
    for row in historical_prices:
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
            is_triggered = False
            
    return {
        "symbol": symbol,
        "days_analyzed": days,
        "data_points": len(historical_prices),
        "trigger_count": len(triggers),
        "triggers": triggers
    }

@app.post("/rules")
def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):"""

if old_route in content:
    content = content.replace(old_route, new_route)
else:
    print("Could not find @app.post('/rules')")
    sys.exit(1)

with open('e:/Application/RippleAlert/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done!")
