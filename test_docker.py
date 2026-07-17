import requests
import asyncio
import websockets
import json
import time

API = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/prices"

async def test_websocket(token):
    print("Testing WebSocket connection...")
    try:
        async with websockets.connect(WS_URL) as ws:
            print("Connected to WebSocket. Waiting for a message...")
            # We just need to receive one price update to confirm it works
            # fetcher runs every 10 seconds
            message = await asyncio.wait_for(ws.recv(), timeout=15.0)
            data = json.loads(message)
            if data.get("type") == "prices" and "BTC" in data.get("data", {}):
                print(f"WebSocket test passed! Received live BTC price: {data['data']['BTC']}")
                return True
    except Exception as e:
        print(f"WebSocket test failed: {e}")
        return False

def run_tests():
    email = f"docker_{int(time.time())}@test.com"
    print(f"1. Signing up {email}...")
    r = requests.post(f"{API}/signup", json={"email": email, "password": "pass"})
    if r.status_code != 200:
        print("Signup failed:", r.text)
        return
        
    print("2. Logging in...")
    r = requests.post(f"{API}/login", data={"username": email, "password": "pass"})
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("3. Adding BTC and ETH to watchlist...")
    requests.post(f"{API}/watchlist", json={"symbol": "BTC"}, headers=headers)
    requests.post(f"{API}/watchlist", json={"symbol": "ETH"}, headers=headers)
    
    # 4. WebSocket test
    asyncio.run(test_websocket(token))
    
    print("5. Creating alert rule (BTC >= 0)...")
    requests.post(f"{API}/rules", json={"symbol": "BTC", "condition": "above", "threshold": 0}, headers=headers)
    
    print("6. Waiting 12 seconds for fetcher and alert engine to process...")
    time.sleep(12)
    
    print("7. Checking alert history...")
    r = requests.get(f"{API}/alert-history", headers=headers)
    history = r.json().get("history", [])
    if history:
        print("Alert History check passed! Fired alerts:")
        for h in history:
            print(f" - {h['rule_description']} at ${h['triggered_price']}")
    else:
        print("Alert History check failed! No alerts found.")

if __name__ == "__main__":
    run_tests()
