from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import DictCursor
import jwt
from datetime import datetime, timedelta
import asyncio
from typing import List
import json
import redis.asyncio as redis
from passlib.context import CryptContext
import os

app = FastAPI(title="RippleAlert API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ripplealert")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

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
    init_db()
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
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

def init_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    password_hash VARCHAR NOT NULL
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS watchlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    symbol VARCHAR NOT NULL,
                    UNIQUE(user_id, symbol)
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS rules (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    symbol VARCHAR NOT NULL,
                    condition VARCHAR NOT NULL,
                    threshold DOUBLE PRECISION NOT NULL,
                    window_minutes DOUBLE PRECISION,
                    is_currently_triggered BOOLEAN DEFAULT FALSE
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS alert_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    symbol VARCHAR NOT NULL,
                    rule_description VARCHAR NOT NULL,
                    triggered_price DOUBLE PRECISION NOT NULL,
                    timestamp VARCHAR NOT NULL
                )
            ''')
            # Initialize prices table here as well just in case fetcher hasn't run
            cur.execute('''
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
        print(f"Database initialization failed: {e}")

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
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
    conn.close()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

@app.post("/signup")
def signup(user: UserCreate):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (user.email,))
            existing = cur.fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Email already registered")
                
            pwd_hash = get_password_hash(user.password)
            cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (user.email, pwd_hash))
        conn.commit()
    finally:
        conn.close()
    return {"message": "User created successfully"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (form_data.username,))
        user = cur.fetchone()
    conn.close()
    
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": user['email']})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/watchlist")
def add_to_watchlist(item: WatchlistItem, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO watchlist (user_id, symbol) VALUES (%s, %s)", (current_user['id'], item.symbol.upper()))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Symbol already in watchlist")
    finally:
        if not conn.closed:
            conn.close()
    return {"message": f"{item.symbol.upper()} added to watchlist"}

@app.post("/rules")
def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):
    if rule.condition not in ["below", "above", "percent_change_in_window"]:
        raise HTTPException(status_code=400, detail="Invalid condition")
    if rule.condition == "percent_change_in_window" and not rule.window_minutes:
        raise HTTPException(status_code=400, detail="window_minutes is required for percent_change_in_window")
        
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO rules (user_id, symbol, condition, threshold, window_minutes, is_currently_triggered) 
            VALUES (%s, %s, %s, %s, %s, FALSE)
        ''', (current_user['id'], rule.symbol.upper(), rule.condition, rule.threshold, rule.window_minutes))
    conn.commit()
    conn.close()
    return {"message": f"Rule created: Alert when {rule.symbol.upper()} is {rule.condition} {rule.threshold}"}

@app.get("/alert-history")
def get_alert_history(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT symbol, rule_description, triggered_price, timestamp FROM alert_history WHERE user_id = %s ORDER BY timestamp DESC", (current_user['id'],))
        items = cur.fetchall()
    conn.close()
    return {"history": [dict(item) for item in items]}

@app.get("/watchlist")
def get_watchlist(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT symbol FROM watchlist WHERE user_id = %s", (current_user['id'],))
        items = cur.fetchall()
    conn.close()
    return {"watchlist": [item['symbol'] for item in items]}

@app.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT price, timestamp FROM prices WHERE symbol = %s ORDER BY timestamp DESC LIMIT 1", (symbol.upper(),))
            price_row = cur.fetchone()
        conn.close()
        if price_row:
            return {"symbol": symbol.upper(), "price": price_row['price'], "timestamp": price_row['timestamp']}
        else:
            raise HTTPException(status_code=404, detail="Price not found")
    except psycopg2.OperationalError:
        raise HTTPException(status_code=404, detail="Database not initialized or price not found")
