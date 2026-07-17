import pytest
from unittest.mock import MagicMock
from alert_engine import evaluate_rule, check_rules
import main
import datetime

def test_evaluate_rule_threshold():
    # Test above threshold (True)
    rule = {"condition": "above", "threshold": 50000, "symbol": "BTC"}
    met, desc = evaluate_rule(rule, current_price=51000, current_ts=1000, redis_client=None)
    assert met is True
    assert "BTC above 50000" in desc

    # Test above threshold (False)
    met, desc = evaluate_rule(rule, current_price=49000, current_ts=1000, redis_client=None)
    assert met is False

    # Test below threshold (True)
    rule2 = {"condition": "below", "threshold": 3000, "symbol": "ETH"}
    met, desc = evaluate_rule(rule2, current_price=2900, current_ts=1000, redis_client=None)
    assert met is True
    assert "ETH below 3000" in desc

def test_evaluate_rule_percent_change():
    rule = {
        "condition": "percent_change_in_window",
        "threshold": 5.0,
        "symbol": "SOL",
        "window_minutes": 60
    }
    mock_redis = MagicMock()
    
    # Mock redis returning a single historical entry from 30 mins ago
    # format is price_timestamp: 100.0_500
    mock_redis.zrangebyscore.return_value = ["100.0_500"]
    
    # 105.0 is exactly 5.0% increase from 100.0
    met, desc = evaluate_rule(rule, current_price=105.0, current_ts=1000, redis_client=mock_redis)
    assert met is True
    assert "SOL moved 5.00%" in desc

    # 104.0 is 4.0% increase (False)
    met, desc = evaluate_rule(rule, current_price=104.0, current_ts=1000, redis_client=mock_redis)
    assert met is False

@pytest.fixture
def mock_rule(setup_test_db):
    # Insert a dummy user and rule into the test DB
    conn = main.get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (email, password_hash) VALUES ('test_alert@example.com', 'hash') RETURNING id")
    user_id = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO rules (user_id, symbol, condition, threshold, is_currently_triggered)
        VALUES (%s, 'BTC', 'above', 50000, FALSE) RETURNING id
    """, (user_id,))
    rule_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return rule_id, user_id

def test_alert_engine_state_transitions(mock_rule):
    rule_id, user_id = mock_rule
    mock_redis = MagicMock()
    
    ts_str = datetime.datetime.now().isoformat()
    
    def get_is_triggered():
        conn = main.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT is_currently_triggered FROM rules WHERE id = %s", (rule_id,))
        val = cur.fetchone()[0]
        cur.close()
        conn.close()
        return val

    def get_alert_history_count():
        conn = main.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM alert_history WHERE user_id = %s", (user_id,))
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count

    # 1. Trigger the alert (price goes to 55000 > 50000)
    check_rules(mock_redis, {"BTC": 55000.0}, ts_str)
    assert get_is_triggered() is True
    assert get_alert_history_count() == 1
    
    # 2. Rule shouldn't re-fire (price stays above threshold at 56000)
    check_rules(mock_redis, {"BTC": 56000.0}, ts_str)
    assert get_is_triggered() is True
    assert get_alert_history_count() == 1  # Still 1, didn't re-fire
    
    # 3. Reset the alert (price drops below threshold to 49000)
    check_rules(mock_redis, {"BTC": 49000.0}, ts_str)
    assert get_is_triggered() is False
    assert get_alert_history_count() == 2  # Added a RESET entry in history
    
    # 4. Re-fire the alert (price goes back above to 51000)
    check_rules(mock_redis, {"BTC": 51000.0}, ts_str)
    assert get_is_triggered() is True
    assert get_alert_history_count() == 3  # Fired again
