import datetime
from unittest.mock import MagicMock
import json

from alert_engine import check_rules

def test_portfolio_rules():
    print("Testing Portfolio Rules")
    mock_cursor = MagicMock()
    # 2 calls to fetchall per check_rules
    mock_cursor.fetchall.side_effect = [
        # Call 1: rules
        [{'id': 10, 'user_id': 1, 'symbol': None, 'condition': 'below', 'threshold': 35000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'portfolio_value', 'email': 'test@test.com'}],
        # Call 2: portfolio
        [{'user_id': 1, 'symbol': 'BTC', 'amount_held': 0.5}, {'user_id': 1, 'symbol': 'ETH', 'amount_held': 2.0}],
        
        # Call 1 (second tick): rules
        [{'id': 10, 'user_id': 1, 'symbol': None, 'condition': 'below', 'threshold': 35000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'portfolio_value', 'email': 'test@test.com'}],
        # Call 2 (second tick): portfolio
        [{'user_id': 1, 'symbol': 'BTC', 'amount_held': 0.5}, {'user_id': 1, 'symbol': 'ETH', 'amount_held': 2.0}]
    ]
    import alert_engine
    alert_engine.get_db_connection = MagicMock()
    conn = alert_engine.get_db_connection.return_value
    conn.cursor.return_value = mock_cursor
    
    redis_client = MagicMock()
    
    print("\n--- Test 1: Portfolio drops below 35,000 (0.5 * 65k + 2 * 3.5k = 39.5k) ---")
    test_recent = {'BTC': 65000}
    test_global = {'BTC': 65000, 'ETH': 3500}
    check_rules(redis_client, test_recent, test_global, datetime.datetime.now().isoformat())
    
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 0
    print("Result: Did not fire. 39.5k is above 35k. (Correct)")
    
    print("\n--- Test 2: Portfolio drops to 31k (0.5 * 50k + 2 * 3k = 31k) ---")
    test_recent = {'BTC': 50000}
    test_global = {'BTC': 50000, 'ETH': 3000}
    check_rules(redis_client, test_recent, test_global, datetime.datetime.now().isoformat())
    
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 1
    print("Result: Fired successfully! (Correct)")

if __name__ == "__main__":
    test_portfolio_rules()
