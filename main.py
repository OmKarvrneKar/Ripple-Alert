from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import os
import psycopg2
import psycopg2.extras
import jwt
from datetime import datetime, timedelta
import asyncio
from typing import List
import json
import redis.asyncio as redis
from passlib.context import CryptContext

app = FastAPI(title="RippleAlert API")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

# Environment variables with defaults
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/ripplealert")
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())

async def redis_listener():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("prices")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await manager.broadcast(data)
    except Exception as e:
        print(f"Redis listener error: {e}")

@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def get_db_connection():
    db_url = DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(db_url)
    return conn

def init_users_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            UNIQUE(user_id, symbol),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            symbol TEXT,
            condition TEXT,
            threshold REAL,
            window_minutes REAL,
            is_currently_triggered BOOLEAN DEFAULT FALSE,
            logic_operator TEXT,
            parent_rule_id INTEGER REFERENCES rules(id) ON DELETE CASCADE,
            cooldown_minutes REAL DEFAULT 0,
            last_triggered_at TIMESTAMP,
            snoozed_until TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Run migrations for existing DBs
    try:
        conn.autocommit = True
        cursor.execute("ALTER TABLE rules ADD COLUMN logic_operator TEXT;")
        cursor.execute("ALTER TABLE rules ADD COLUMN parent_rule_id INTEGER REFERENCES rules(id) ON DELETE CASCADE;")
        cursor.execute("ALTER TABLE rules ALTER COLUMN symbol DROP NOT NULL;")
        cursor.execute("ALTER TABLE rules ALTER COLUMN condition DROP NOT NULL;")
        cursor.execute("ALTER TABLE rules ALTER COLUMN threshold DROP NOT NULL;")
        conn.autocommit = False
    except psycopg2.Error:
        pass # Columns probably already exist
        
    try:
        conn.autocommit = True
        cursor.execute("ALTER TABLE rules ADD COLUMN cooldown_minutes REAL DEFAULT 0;")
        cursor.execute("ALTER TABLE rules ADD COLUMN last_triggered_at TIMESTAMP;")
        conn.autocommit = False
    except psycopg2.Error:
        pass # Columns probably already exist
        
    try:
        conn.autocommit = True
        cursor.execute("ALTER TABLE rules ADD COLUMN snoozed_until TIMESTAMP;")
        conn.autocommit = False
    except psycopg2.Error:
        pass # Columns probably already exist
        
    try:
        conn.autocommit = True
        cursor.execute("ALTER TABLE rules ADD COLUMN rule_type TEXT DEFAULT 'price';")
        conn.autocommit = False
    except psycopg2.Error:
        pass # Columns probably already exist
        
    try:
        conn.autocommit = True
        cursor.execute("ALTER TABLE news_headlines ADD COLUMN sentiment_score TEXT DEFAULT 'neutral';")
        cursor.execute("ALTER TABLE news_headlines ADD COLUMN sentiment_reason TEXT;")
        conn.autocommit = False
    except psycopg2.Error:
        pass # Columns probably already exist
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            symbol TEXT,
            rule_description TEXT NOT NULL,
            triggered_price REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            amount_held REAL NOT NULL,
            UNIQUE(user_id, symbol),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_headlines (
            id SERIAL PRIMARY KEY,
            headline TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT UNIQUE,
            timestamp TIMESTAMP NOT NULL,
            sentiment_score TEXT DEFAULT 'neutral',
            sentiment_reason TEXT
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

import time
max_retries = 5
for i in range(max_retries):
    try:
        init_users_db()
        print("Database initialized successfully.")
        break
    except Exception as e:
        print(f"Could not initialize DB (attempt {i+1}/{max_retries}): {e}")
        time.sleep(3)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

from typing import List, Optional

class UserCreate(BaseModel):
    email: str
    password: str

class WatchlistItem(BaseModel):
    symbol: str

class RuleCondition(BaseModel):
    symbol: str
    condition: str
    threshold: float
    window_minutes: Optional[float] = None

class RuleCreate(BaseModel):
    # For single rules
    symbol: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    window_minutes: Optional[float] = None
    rule_type: Optional[str] = 'price'
    
    # For composite rules
    logic: Optional[str] = None
    conditions: Optional[List[RuleCondition]] = None
    
    # Common
    cooldown_minutes: Optional[float] = 0

class SnoozeRequest(BaseModel):
    duration_minutes: float

class BacktestRequest(BaseModel):
    rule: RuleCreate
    days: int = 7

class PortfolioItem(BaseModel):
    symbol: str
    amount: float

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid auth credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid auth credentials")
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

@app.post("/signup")
def signup(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
    existing = cursor.fetchone()
    if existing:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
        
    pwd_hash = get_password_hash(user.password)
    cursor.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (user.email, pwd_hash))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "User created successfully"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE email = %s", (form_data.username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": user['email']})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/watchlist")
def add_to_watchlist(item: WatchlistItem, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO watchlist (user_id, symbol) VALUES (%s, %s)", (current_user['id'], item.symbol.upper()))
        conn.commit()
    except psycopg2.IntegrityError:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Symbol already in watchlist")
    cursor.close()
    conn.close()
    return {"message": f"{item.symbol.upper()} added to watchlist"}

@app.post("/rules/backtest")
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
    
    price_history = []
    
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
            is_triggered = False
            
    return {
        "symbol": symbol,
        "days_analyzed": days,
        "data_points": len(historical_prices),
        "trigger_count": len(triggers),
        "triggers": triggers
    }

@app.post("/rules")
def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if rule.logic:
            if rule.logic not in ["AND", "OR"]:
                raise HTTPException(status_code=400, detail="Invalid logic operator")
            if not rule.conditions or len(rule.conditions) < 2:
                raise HTTPException(status_code=400, detail="Composite rules need at least 2 conditions")
                
            cursor.execute('''
                INSERT INTO rules (user_id, is_currently_triggered, logic_operator, cooldown_minutes) 
                VALUES (%s, FALSE, %s, %s) RETURNING id
            ''', (current_user['id'], rule.logic, rule.cooldown_minutes))
            parent_id = cursor.fetchone()[0]
            
            for cond in rule.conditions:
                if cond.condition not in ["below", "above", "percent_change_in_window"]:
                    raise HTTPException(status_code=400, detail="Invalid condition")
                if cond.condition == "percent_change_in_window" and not cond.window_minutes:
                    raise HTTPException(status_code=400, detail="window_minutes is required for percent_change_in_window")
                
                cursor.execute('''
                    INSERT INTO rules (user_id, symbol, condition, threshold, window_minutes, parent_rule_id) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (current_user['id'], cond.symbol.upper(), cond.condition, cond.threshold, cond.window_minutes, parent_id))
                
            rule_desc = f"Composite Rule ({rule.logic})"
        elif rule.rule_type == 'portfolio_value':
            if not rule.condition or rule.threshold is None:
                raise HTTPException(status_code=400, detail="Missing fields for portfolio rule")
            cursor.execute('''
                INSERT INTO rules (user_id, rule_type, condition, threshold, is_currently_triggered, cooldown_minutes) 
                VALUES (%s, %s, %s, %s, FALSE, %s)
            ''', (current_user['id'], rule.rule_type, rule.condition, rule.threshold, rule.cooldown_minutes))
            rule_desc = f"Alert when Portfolio Value is {rule.condition} ${rule.threshold}"
        else:
            if not rule.symbol or not rule.condition or rule.threshold is None:
                raise HTTPException(status_code=400, detail="Missing fields for single rule")
            if rule.condition not in ["below", "above", "percent_change_in_window"]:
                raise HTTPException(status_code=400, detail="Invalid condition")
            if rule.condition == "percent_change_in_window" and not rule.window_minutes:
                raise HTTPException(status_code=400, detail="window_minutes is required for percent_change_in_window")
                
            cursor.execute('''
                INSERT INTO rules (user_id, symbol, condition, threshold, window_minutes, is_currently_triggered, cooldown_minutes) 
                VALUES (%s, %s, %s, %s, %s, FALSE, %s)
            ''', (current_user['id'], rule.symbol.upper(), rule.condition, rule.threshold, rule.window_minutes, rule.cooldown_minutes))
            rule_desc = f"Alert when {rule.symbol.upper()} is {rule.condition} {rule.threshold}"
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
        
    return {"message": f"Rule created: {rule_desc}"}

@app.get("/rules")
def get_rules(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cursor.execute("SELECT id, symbol, condition, threshold, window_minutes, is_currently_triggered, logic_operator, parent_rule_id, cooldown_minutes, last_triggered_at, snoozed_until, rule_type FROM rules WHERE user_id = %s ORDER BY id DESC", (current_user['id'],))
    all_rules = cursor.fetchall()
    
    processed_rules = []
    
    for r in all_rules:
        if r['parent_rule_id'] is not None:
            continue
            
        if r['logic_operator'] is not None:
            children = [dict(c) for c in all_rules if c['parent_rule_id'] == r['id']]
            processed_rules.append({
                "id": r['id'],
                "is_currently_triggered": r['is_currently_triggered'],
                "logic": r['logic_operator'],
                "cooldown_minutes": r['cooldown_minutes'],
                "last_triggered_at": r['last_triggered_at'],
                "snoozed_until": r['snoozed_until'],
                "conditions": children
            })
        else:
            processed_rules.append(dict(r))
            
    cursor.close()
    conn.close()
    return {"rules": processed_rules}

@app.post("/rules/{rule_id}/snooze")
def snooze_rule(rule_id: int, request: SnoozeRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM rules WHERE id = %s AND user_id = %s", (rule_id, current_user['id']))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Rule not found")
        
    snooze_until_ts = datetime.utcnow() + timedelta(minutes=request.duration_minutes)
    cursor.execute("UPDATE rules SET snoozed_until = %s WHERE id = %s", (snooze_until_ts, rule_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Rule {rule_id} snoozed for {request.duration_minutes} minutes"}

@app.delete("/rules/{rule_id}/snooze")
def cancel_snooze(rule_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM rules WHERE id = %s AND user_id = %s", (rule_id, current_user['id']))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Rule not found")
        
    cursor.execute("UPDATE rules SET snoozed_until = NULL WHERE id = %s", (rule_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Snooze cancelled for rule {rule_id}"}

@app.get("/alert-history")
def get_alert_history(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT symbol, rule_description, triggered_price, timestamp FROM alert_history WHERE user_id = %s ORDER BY timestamp DESC", (current_user['id'],))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"history": [dict(item) for item in items]}

@app.get("/watchlist")
def get_watchlist(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT symbol FROM watchlist WHERE user_id = %s", (current_user['id'],))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"watchlist": [item['symbol'] for item in items]}

@app.get("/portfolio")
def get_portfolio(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT symbol, amount_held FROM portfolio_holdings WHERE user_id = %s", (current_user['id'],))
    items = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"portfolio": [dict(item) for item in items]}

@app.post("/portfolio")
def set_portfolio_item(item: PortfolioItem, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO portfolio_holdings (user_id, symbol, amount_held) 
        VALUES (%s, %s, %s) 
        ON CONFLICT (user_id, symbol) 
        DO UPDATE SET amount_held = EXCLUDED.amount_held
    ''', (current_user['id'], item.symbol.upper(), item.amount))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Portfolio updated: {item.amount} {item.symbol.upper()}"}

@app.get("/market-mood/{symbol}")
def get_market_mood(symbol: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Fetch recent headlines containing symbol
    cursor.execute('''
        SELECT headline, source, url, timestamp, sentiment_score, sentiment_reason
        FROM news_headlines
        WHERE upper(headline) LIKE %s
        ORDER BY timestamp DESC LIMIT 20
    ''', (f"%{symbol.upper()}%",))
    headlines = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not headlines:
        return {"symbol": symbol.upper(), "overall_mood": "neutral", "score_breakdown": {"positive": 0, "negative": 0, "neutral": 0}, "headlines": []}
        
    pos = sum(1 for h in headlines if h['sentiment_score'] == 'positive')
    neg = sum(1 for h in headlines if h['sentiment_score'] == 'negative')
    neu = len(headlines) - pos - neg
    
    overall_mood = "neutral"
    if pos > neg:
        overall_mood = "bullish"
    elif neg > pos:
        overall_mood = "bearish"
        
    return {
        "symbol": symbol.upper(),
        "overall_mood": overall_mood,
        "score_breakdown": {"positive": pos, "negative": neg, "neutral": neu},
        "headlines": [dict(h) for h in headlines]
    }

@app.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT price, timestamp FROM prices WHERE symbol = %s ORDER BY timestamp DESC LIMIT 1", (symbol.upper(),))
        price_row = cursor.fetchone()
        cursor.close()
        conn.close()
        if price_row:
            return {"symbol": symbol.upper(), "price": price_row['price'], "timestamp": price_row['timestamp']}
        else:
            raise HTTPException(status_code=404, detail="Price not found")
    except psycopg2.OperationalError:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Database not initialized or price not found")

@app.get("/price-history/{symbol}")
def get_price_history(symbol: str, hours: float = 24.0):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Determine downsampling resolution
        if hours <= 24:
            trunc_unit = 'minute'
        else:
            trunc_unit = 'hour'
            
        # We cast the text timestamp to an actual timestamp for time manipulation
        query = f'''
            SELECT 
                date_trunc('{trunc_unit}', CAST(timestamp AS TIMESTAMP)) as time_bucket, 
                AVG(price) as avg_price 
            FROM prices 
            WHERE symbol = %s 
              AND CAST(timestamp AS TIMESTAMP) >= NOW() - INTERVAL '%s hours'
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
        '''
        cursor.execute(query, (symbol.upper(), hours))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format result to be easily consumable by Chart.js or similar
        return {
            "symbol": symbol.upper(),
            "hours": hours,
            "resolution": trunc_unit,
            "data": [
                {"timestamp": row['time_bucket'].isoformat(), "price": round(row['avg_price'], 2)}
                for row in rows
            ]
        }
    except psycopg2.Error as e:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

# Serve the React frontend (must be at the end to not override API routes)
if os.path.exists("frontend-v2/dist"):
    app.mount("/", StaticFiles(directory="frontend-v2/dist", html=True), name="static")
elif os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
