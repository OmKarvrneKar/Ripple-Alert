import pytest
import main
import psycopg2.extras

@pytest.fixture
async def auth_token(async_client, test_user):
    # Ensure user exists and get token
    await async_client.post("/signup", json=test_user)
    response = await async_client.post("/login", data={"username": test_user["email"], "password": test_user["password"]})
    return response.json()["access_token"]

async def test_create_watchlist_entry(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    response = await async_client.post("/watchlist", json={"symbol": "SOL"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "SOL added to watchlist"}
    
    # Confirm it's in the DB
    response_get = await async_client.get("/watchlist", headers=headers)
    assert response_get.status_code == 200
    assert "SOL" in response_get.json()["watchlist"]

async def test_create_threshold_rule(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    rule_data = {
        "symbol": "BTC",
        "condition": "above",
        "threshold": 65000.0
    }
    response = await async_client.post("/rules", json=rule_data, headers=headers)
    assert response.status_code == 200
    
    # Query database to confirm is_currently_triggered is False
    conn = main.get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM rules WHERE symbol = 'BTC' AND condition = 'above' ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    assert row is not None
    assert row["threshold"] == 65000.0
    assert row["is_currently_triggered"] is False

async def test_create_percent_change_rule(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    rule_data = {
        "symbol": "ETH",
        "condition": "percent_change_in_window",
        "threshold": 5.0,
        "window_minutes": 60
    }
    response = await async_client.post("/rules", json=rule_data, headers=headers)
    assert response.status_code == 200
    assert "Alert when ETH is percent_change_in_window 5.0" in response.json()["message"]

async def test_create_rule_invalid_input(async_client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Invalid condition
    rule_data = {
        "symbol": "ETH",
        "condition": "magic_moon",
        "threshold": 3000.0
    }
    res1 = await async_client.post("/rules", json=rule_data, headers=headers)
    assert res1.status_code == 400
    assert "Invalid condition" in res1.json()["detail"]
    
    # Missing window_minutes for percent_change
    rule_data2 = {
        "symbol": "ETH",
        "condition": "percent_change_in_window",
        "threshold": 3.0
    }
    res2 = await async_client.post("/rules", json=rule_data2, headers=headers)
    assert res2.status_code == 400
    assert "window_minutes is required" in res2.json()["detail"]
    
    # Missing threshold entirely (FastAPI Pydantic Validation Error 422)
    rule_data3 = {
        "symbol": "ETH",
        "condition": "above"
    }
    res3 = await async_client.post("/rules", json=rule_data3, headers=headers)
    assert res3.status_code == 422
