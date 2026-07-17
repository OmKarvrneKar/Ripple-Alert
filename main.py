from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
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
            symbol TEXT NOT NULL,
            condition TEXT NOT NULL,
            threshold REAL NOT NULL,
            window_minutes REAL,
            is_currently_triggered BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            rule_description TEXT NOT NULL,
            triggered_price REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
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

class UserCreate(BaseModel):
    email: str
    password: str

class WatchlistItem(BaseModel):
    symbol: str

class RuleCreate(BaseModel):
    symbol: str
    condition: str
    threshold: float
    window_minutes: float = None

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

@app.post("/rules")
def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):
    if rule.condition not in ["below", "above", "percent_change_in_window"]:
        raise HTTPException(status_code=400, detail="Invalid condition")
    if rule.condition == "percent_change_in_window" and not rule.window_minutes:
        raise HTTPException(status_code=400, detail="window_minutes is required for percent_change_in_window")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO rules (user_id, symbol, condition, threshold, window_minutes, is_currently_triggered) 
        VALUES (%s, %s, %s, %s, %s, FALSE)
    ''', (current_user['id'], rule.symbol.upper(), rule.condition, rule.threshold, rule.window_minutes))
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"Rule created: Alert when {rule.symbol.upper()} is {rule.condition} {rule.threshold}"}

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
