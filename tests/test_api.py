import pytest

pytestmark = pytest.mark.asyncio

async def test_signup(async_client, test_user):
    response = await async_client.post("/signup", json=test_user)
    assert response.status_code == 200
    assert response.json() == {"message": "User created successfully"}

async def test_signup_duplicate(async_client, test_user):
    # Setup - user is already created from previous test, but tests might run out of order
    # so we create again just in case (if it fails with 400, it's expected)
    await async_client.post("/signup", json=test_user)
    
    response = await async_client.post("/signup", json=test_user)
    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"}

async def test_login(async_client, test_user):
    response = await async_client.post("/login", data={"username": test_user["email"], "password": test_user["password"]})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_invalid_password(async_client, test_user):
    response = await async_client.post("/login", data={"username": test_user["email"], "password": "wrongpassword"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Incorrect email or password"}

async def test_protected_routes_unauthorized(async_client):
    response = await async_client.get("/watchlist")
    assert response.status_code == 401

@pytest.fixture
async def auth_token(async_client, test_user):
    # Ensure user exists
    await async_client.post("/signup", json=test_user)
    response = await async_client.post("/login", data={"username": test_user["email"], "password": test_user["password"]})
    return response.json()["access_token"]

async def test_add_watchlist(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await async_client.post("/watchlist", json={"symbol": "BTC"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "BTC added to watchlist"}
    
    # Test getting watchlist
    response = await async_client.get("/watchlist", headers=headers)
    assert response.status_code == 200
    assert "BTC" in response.json()["watchlist"]

async def test_create_rule(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    rule_data = {
        "symbol": "ETH",
        "condition": "above",
        "threshold": 3000.0
    }
    response = await async_client.post("/rules", json=rule_data, headers=headers)
    assert response.status_code == 200
    assert "Alert when ETH is above 3000.0" in response.json()["message"]

async def test_create_rule_invalid_condition(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    rule_data = {
        "symbol": "ETH",
        "condition": "invalid_cond",
        "threshold": 3000.0
    }
    response = await async_client.post("/rules", json=rule_data, headers=headers)
    assert response.status_code == 400

async def test_get_alert_history(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await async_client.get("/alert-history", headers=headers)
    assert response.status_code == 200
    assert "history" in response.json()

async def test_get_latest_price_not_found(async_client):
    # In the test schema, prices table doesn't even exist because main.py doesn't initialize it!
    # Wait, fetcher.py initializes it. Let's just verify it returns 404
    response = await async_client.get("/latest-price/UNKNOWN")
    assert response.status_code == 404
