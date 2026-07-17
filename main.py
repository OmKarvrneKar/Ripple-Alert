from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import sqlite3
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
USERS_DB = "users.db"
PRICES_DB = "prices.db"

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
        r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
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

def get_db_connection(db_name):
    conn = sqlite3.connect(db_name, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_users_db():
    conn = get_db_connection(USERS_DB)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            UNIQUE(user_id, symbol),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            condition TEXT NOT NULL,
            threshold REAL NOT NULL,
            window_minutes REAL,
            is_currently_triggered BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            rule_description TEXT NOT NULL,
            triggered_price REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_users_db()

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
        
    conn = get_db_connection(USERS_DB)
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

@app.post("/signup")
def signup(user: UserCreate):
    conn = get_db_connection(USERS_DB)
    existing = conn.execute("SELECT * FROM users WHERE email = ?", (user.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
        
    pwd_hash = get_password_hash(user.password)
    conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (user.email, pwd_hash))
    conn.commit()
    conn.close()
    return {"message": "User created successfully"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection(USERS_DB)
    user = conn.execute("SELECT * FROM users WHERE email = ?", (form_data.username,)).fetchone()
    conn.close()
    
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": user['email']})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/watchlist")
def add_to_watchlist(item: WatchlistItem, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection(USERS_DB)
    try:
        conn.execute("INSERT INTO watchlist (user_id, symbol) VALUES (?, ?)", (current_user['id'], item.symbol.upper()))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Symbol already in watchlist")
    conn.close()
    return {"message": f"{item.symbol.upper()} added to watchlist"}

@app.post("/rules")
def create_rule(rule: RuleCreate, current_user: dict = Depends(get_current_user)):
    if rule.condition not in ["below", "above", "percent_change_in_window"]:
        raise HTTPException(status_code=400, detail="Invalid condition")
    if rule.condition == "percent_change_in_window" and not rule.window_minutes:
        raise HTTPException(status_code=400, detail="window_minutes is required for percent_change_in_window")
        
    conn = get_db_connection(USERS_DB)
    conn.execute('''
        INSERT INTO rules (user_id, symbol, condition, threshold, window_minutes, is_currently_triggered) 
        VALUES (?, ?, ?, ?, ?, 0)
    ''', (current_user['id'], rule.symbol.upper(), rule.condition, rule.threshold, rule.window_minutes))
    conn.commit()
    conn.close()
    return {"message": f"Rule created: Alert when {rule.symbol.upper()} is {rule.condition} {rule.threshold}"}

@app.get("/alert-history")
def get_alert_history(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection(USERS_DB)
    items = conn.execute("SELECT symbol, rule_description, triggered_price, timestamp FROM alert_history WHERE user_id = ? ORDER BY timestamp DESC", (current_user['id'],)).fetchall()
    conn.close()
    return {"history": [dict(item) for item in items]}

@app.get("/watchlist")
def get_watchlist(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection(USERS_DB)
    items = conn.execute("SELECT symbol FROM watchlist WHERE user_id = ?", (current_user['id'],)).fetchall()
    conn.close()
    return {"watchlist": [item['symbol'] for item in items]}

@app.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):
    conn = get_db_connection(PRICES_DB)
    try:
        price_row = conn.execute("SELECT price, timestamp FROM prices WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1", (symbol.upper(),)).fetchone()
        conn.close()
        if price_row:
            return {"symbol": symbol.upper(), "price": price_row['price'], "timestamp": price_row['timestamp']}
        else:
            raise HTTPException(status_code=404, detail="Price not found")
    except sqlite3.OperationalError:
        conn.close()
        raise HTTPException(status_code=404, detail="Database not initialized or price not found")
