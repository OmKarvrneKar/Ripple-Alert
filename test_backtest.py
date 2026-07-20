import os
import sys
import datetime
from main import app
from fastapi.testclient import TestClient

def test_backtester():
    # Because we're in the same folder, we can mock the DB easily or just use TestClient
    client = TestClient(app)
    
    # We need a token or we can mock get_current_user
    # Actually, we can just call backtest_rule directly by mocking Depends
    from main import backtest_rule
    
    class MockRule:
        rule_type = 'price'
        symbol = 'BTC'
        condition = 'below'
        threshold = 60000.0
        window_minutes = None
        cooldown_minutes = 0

    class MockReq:
        rule = MockRule()
        days = 7

    # Since we need to connect to DB, let's see if we can connect
    try:
        res = backtest_rule(MockReq(), {"id": 1})
        print(f"Test 1 - Threshold Rule (BTC < 60k): {res['trigger_count']} triggers out of {res['data_points']} points")
    except Exception as e:
        print("Test 1 Failed:", e)
        
    class MockRulePct:
        rule_type = 'price'
        symbol = 'ETH'
        condition = 'percent_change_in_window'
        threshold = 2.0 # 2%
        window_minutes = 60
        cooldown_minutes = 0

    class MockReqPct:
        rule = MockRulePct()
        days = 7

    try:
        res = backtest_rule(MockReqPct(), {"id": 1})
        print(f"Test 2 - Percent Rule (ETH moved 2% in 60m): {res['trigger_count']} triggers out of {res['data_points']} points")
    except Exception as e:
        print("Test 2 Failed:", e)

if __name__ == "__main__":
    test_backtester()
