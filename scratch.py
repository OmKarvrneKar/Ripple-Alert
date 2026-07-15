import requests
import time
import redis
import json
from datetime import datetime

API = "http://127.0.0.1:8000"

print("1. Signup and Login...")
requests.post(f"{API}/signup", json={"email": "test_final@test.com", "password": "pass"})
res = requests.post(f"{API}/login", data={"username": "test_final@test.com", "password": "pass"})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("2. Creating Window Rule: >= 5% in 60 mins...")
r2 = requests.post(f"{API}/rules", json={"symbol": "BTC", "condition": "percent_change_in_window", "threshold": 5.0, "window_minutes": 60}, headers=headers)
print("Rule:", r2.json())

print("3. Pushing fake price 64000 to establish baseline...")
r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
r.publish("prices", json.dumps({"data": {"BTC": 64000, "ETH": 2000}, "timestamp": datetime.utcnow().isoformat()}))

time.sleep(2)

print("4. Pushing fake price 64500 to simulate a 0.78% change (should NOT trigger)...")
r.publish("prices", json.dumps({"data": {"BTC": 64500, "ETH": 2000}, "timestamp": datetime.utcnow().isoformat()}))

time.sleep(2)

history = requests.get(f"{API}/alert-history", headers=headers).json()
print("History after small change (should be empty):", history.get('history'))

print("5. Pushing fake price 70000 to simulate a 9.37% change (SHOULD trigger)...")
r.publish("prices", json.dumps({"data": {"BTC": 70000, "ETH": 2000}, "timestamp": datetime.utcnow().isoformat()}))

time.sleep(2)

history = requests.get(f"{API}/alert-history", headers=headers).json()
print("History after large change:")
for h in history.get('history', []):
    print(" -", h['rule_description'])
