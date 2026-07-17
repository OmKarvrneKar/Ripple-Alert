import pytest
from passlib.context import CryptContext
from main import get_db_connection

# Re-use the hashing context to verify bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def test_signup_creates_bcrypt_user(async_client, test_user):
    # Register the user
    response = await async_client.post("/signup", json=test_user)
    assert response.status_code == 200
    
    # Query database to verify it is bcrypt hashed
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE email = %s", (test_user["email"],))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    assert row is not None
    password_hash = row[0]
    
    # Bcrypt hashes always start with $2a$, $2b$, or $2y$
    assert password_hash.startswith("$2b$")
    assert pwd_context.verify(test_user["password"], password_hash)

async def test_signup_duplicate(async_client, test_user):
    # Ensure user exists (test isolation may have cleaned it up if run out of order)
    await async_client.post("/signup", json=test_user)
    
    # Try again
    response = await async_client.post("/signup", json=test_user)
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}

async def test_login_success(async_client, test_user):
    # Ensure user exists
    await async_client.post("/signup", json=test_user)
    
    # Login
    response = await async_client.post("/login", data={"username": test_user["email"], "password": test_user["password"]})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Basic JWT check (3 parts separated by dots)
    assert len(data["access_token"].split(".")) == 3

async def test_login_invalid_password(async_client, test_user):
    # Ensure user exists
    await async_client.post("/signup", json=test_user)
    
    response = await async_client.post("/login", data={"username": test_user["email"], "password": "wrongpassword"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Incorrect email or password"}

async def test_protected_endpoints_unauthorized(async_client):
    # No token
    res1 = await async_client.get("/watchlist")
    assert res1.status_code == 401
    
    res2 = await async_client.post("/rules", json={"symbol": "BTC", "condition": "above", "threshold": 50000})
    assert res2.status_code == 401
    
    # Invalid token
    headers = {"Authorization": "Bearer not.a.real.token"}
    res3 = await async_client.get("/watchlist", headers=headers)
    assert res3.status_code == 401
