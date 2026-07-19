import os
from unittest.mock import MagicMock
from alert_engine import check_rules

# Mock the get_db_connection function in alert_engine
import alert_engine
import datetime

def test_composite_rules():
    # Setup mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    alert_engine.get_db_connection = lambda: mock_conn

    # 1. Test AND Rule
    # "BTC below 60,000 AND ETH below 3,000"
    mock_cursor.fetchall.return_value = [
        # Parent Rule
        {'id': 1, 'user_id': 1, 'symbol': None, 'condition': None, 'threshold': None, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': 'AND', 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'email': 'test@test.com'},
        # Child 1
        {'id': 2, 'user_id': 1, 'symbol': 'BTC', 'condition': 'below', 'threshold': 60000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 1, 'cooldown_minutes': 0, 'last_triggered_at': None, 'email': 'test@test.com'},
        # Child 2
        {'id': 3, 'user_id': 1, 'symbol': 'ETH', 'condition': 'below', 'threshold': 3000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 1, 'cooldown_minutes': 0, 'last_triggered_at': None, 'email': 'test@test.com'},
    ]
    
    redis_client = MagicMock()
    ts_str = "2026-07-19T22:00:00"

    print("--- Testing AND Rule ---")
    print("Test 1: Only BTC is below 60,000 (ETH is 3500)")
    recent_prices = {"BTC": 59000}
    global_prices = {"BTC": 59000, "ETH": 3500}
    check_rules(redis_client, recent_prices, global_prices, ts_str)
    # Shouldn't trigger (execute count on UPDATE should be 0)
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET" in call[0][0]]
    assert len(update_calls) == 0
    print("Result: Did not fire. (Correct)")
    
    print("\nTest 2: Both BTC and ETH are below thresholds")
    mock_cursor.execute.reset_mock()
    recent_prices = {"ETH": 2900}
    global_prices = {"BTC": 59000, "ETH": 2900}
    check_rules(redis_client, recent_prices, global_prices, ts_str)
    # Should trigger
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 1
    print("Result: Fired successfully! (Correct)")
    
    # 2. Test OR Rule
    mock_cursor.reset_mock()
    mock_cursor.fetchall.return_value = [
        # Parent Rule
        {'id': 4, 'user_id': 1, 'symbol': None, 'condition': None, 'threshold': None, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': 'OR', 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'email': 'test@test.com'},
        # Child 1
        {'id': 5, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 70000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 4, 'cooldown_minutes': 0, 'last_triggered_at': None, 'email': 'test@test.com'},
        # Child 2
        {'id': 6, 'user_id': 1, 'symbol': 'ETH', 'condition': 'below', 'threshold': 2000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 4, 'cooldown_minutes': 0, 'last_triggered_at': None, 'email': 'test@test.com'},
    ]
    
    print("\n--- Testing OR Rule ---")
    print("Test 3: Neither condition met")
    mock_cursor.execute.reset_mock()
    recent_prices = {"BTC": 65000}
    global_prices = {"BTC": 65000, "ETH": 2500}
    check_rules(redis_client, recent_prices, global_prices, ts_str)
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET" in call[0][0]]
    assert len(update_calls) == 0
    print("Result: Did not fire. (Correct)")
    
    print("\nTest 4: One condition met (BTC > 70k)")
    mock_cursor.execute.reset_mock()
    recent_prices = {"BTC": 71000}
    global_prices = {"BTC": 71000, "ETH": 2500}
    check_rules(redis_client, recent_prices, global_prices, ts_str)
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 1
    print("Result: Fired successfully! (Correct)")

    # 3. Test Cooldown Rule
    mock_cursor.reset_mock()
    ts_now = 1672531200 # Jan 1 2023, 00:00:00
    ts_triggered = 1672531000 # 200 seconds ago (3.33 mins)
    
    mock_cursor.fetchall.return_value = [
        # Parent Rule (Single condition rule with 5 min cooldown)
        {'id': 7, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 10000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 5, 'last_triggered_at': datetime.datetime.fromtimestamp(ts_triggered), 'email': 'test@test.com'}
    ]
    
    print("\n--- Testing Cooldown Rule ---")
    print("Test 5: Condition met but inside 5m cooldown (200s elapsed)")
    ts_str_5 = datetime.datetime.fromtimestamp(ts_now).isoformat()
    recent_prices = {"BTC": 11000}
    global_prices = {"BTC": 11000}
    check_rules(redis_client, recent_prices, global_prices, ts_str_5)
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 0
    print("Result: Did not fire, in cooldown. (Correct)")
    
    print("\nTest 6: Condition met and outside 5m cooldown (400s elapsed)")
    mock_cursor.execute.reset_mock()
    ts_now_later = ts_triggered + 400
    ts_str_6 = datetime.datetime.fromtimestamp(ts_now_later).isoformat()
    check_rules(redis_client, recent_prices, global_prices, ts_str_6)
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 1
    print("Result: Fired successfully after cooldown! (Correct)")

if __name__ == "__main__":
    test_composite_rules()
    print("\nALL COMPOSITE RULE & COOLDOWN TESTS PASSED!")
