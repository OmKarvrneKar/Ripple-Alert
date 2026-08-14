import sys

with open('e:/Application/RippleAlert/scratch.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will replace the mock_cursor.fetchall.return_value with mock_cursor.fetchall.side_effect
old_test = '''    mock_cursor.fetchall.return_value = [
        # Parent Rule
        {'id': 1, 'user_id': 1, 'symbol': None, 'condition': None, 'threshold': None, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': 'AND', 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'email': 'test@test.com'},
        # Child 1
        {'id': 2, 'user_id': 1, 'symbol': 'BTC', 'condition': 'below', 'threshold': 60000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 1, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'email': 'test@test.com'},
        # Child 2
        {'id': 3, 'user_id': 1, 'symbol': 'ETH', 'condition': 'below', 'threshold': 3000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 1, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'email': 'test@test.com'},
    ]'''

new_test = '''    mock_cursor.fetchall.side_effect = [
        [
            # Parent Rule
            {'id': 1, 'user_id': 1, 'symbol': None, 'condition': None, 'threshold': None, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': 'AND', 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'price', 'email': 'test@test.com'},
            # Child 1
            {'id': 2, 'user_id': 1, 'symbol': 'BTC', 'condition': 'below', 'threshold': 60000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 1, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'price', 'email': 'test@test.com'},
            # Child 2
            {'id': 3, 'user_id': 1, 'symbol': 'ETH', 'condition': 'below', 'threshold': 3000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 1, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'price', 'email': 'test@test.com'},
        ],
        [] # Empty holdings
    ]'''

content = content.replace(old_test, new_test)

old_test_2 = '''    mock_cursor.fetchall.return_value = [
        # Parent Rule
        {'id': 4, 'user_id': 1, 'symbol': None, 'condition': None, 'threshold': None, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': 'OR', 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'email': 'test@test.com'},
        # Child 1
        {'id': 5, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 70000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 4, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'email': 'test@test.com'},
        # Child 2
        {'id': 6, 'user_id': 1, 'symbol': 'ETH', 'condition': 'below', 'threshold': 2000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 4, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'email': 'test@test.com'},
    ]'''

new_test_2 = '''    mock_cursor.fetchall.side_effect = [
        [
            # Parent Rule
            {'id': 4, 'user_id': 1, 'symbol': None, 'condition': None, 'threshold': None, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': 'OR', 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'price', 'email': 'test@test.com'},
            # Child 1
            {'id': 5, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 70000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 4, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'price', 'email': 'test@test.com'},
            # Child 2
            {'id': 6, 'user_id': 1, 'symbol': 'ETH', 'condition': 'below', 'threshold': 2000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': 4, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'price', 'email': 'test@test.com'},
        ],
        [] # Empty holdings
    ]'''

content = content.replace(old_test_2, new_test_2)

old_test_3 = '''    mock_cursor.fetchall.return_value = [
        # Parent Rule (Single condition rule with 5 min cooldown)
        {'id': 7, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 10000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 5, 'last_triggered_at': datetime.datetime.fromtimestamp(ts_triggered), 'snoozed_until': None, 'email': 'test@test.com'}
    ]'''

new_test_3 = '''    mock_cursor.fetchall.side_effect = [
        [
            # Parent Rule (Single condition rule with 5 min cooldown)
            {'id': 7, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 10000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 5, 'last_triggered_at': datetime.datetime.fromtimestamp(ts_triggered), 'snoozed_until': None, 'rule_type': 'price', 'email': 'test@test.com'}
        ],
        []
    ]'''

content = content.replace(old_test_3, new_test_3)

old_test_4 = '''    mock_cursor.fetchall.return_value = [
        {'id': 8, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 10000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': datetime.datetime.fromtimestamp(ts_snoozed_until), 'email': 'test@test.com'}
    ]'''

new_test_4 = '''    mock_cursor.fetchall.side_effect = [
        [
            {'id': 8, 'user_id': 1, 'symbol': 'BTC', 'condition': 'above', 'threshold': 10000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': datetime.datetime.fromtimestamp(ts_snoozed_until), 'rule_type': 'price', 'email': 'test@test.com'}
        ],
        []
    ]'''

content = content.replace(old_test_4, new_test_4)

portfolio_test = '''
    # 5. Test Portfolio Rule
    mock_cursor.reset_mock()
    mock_cursor.fetchall.side_effect = [
        [
            {'id': 9, 'user_id': 1, 'symbol': None, 'condition': 'below', 'threshold': 35000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'portfolio_value', 'email': 'test@test.com'}
        ],
        [
            {'user_id': 1, 'symbol': 'BTC', 'amount_held': 0.5},
            {'user_id': 1, 'symbol': 'ETH', 'amount_held': 2.0}
        ]
    ]
    
    print("\\n--- Testing Portfolio Rule ---")
    print("Test 8: Portfolio drops below 35,000 (0.5 * 65k + 2 * 3.5k = 39.5k)")
    # Ticks to BTC 65k, ETH 3.5k
    test_recent = {'BTC': 65000}
    test_global = {'BTC': 65000, 'ETH': 3500}
    check_rules(redis_client, test_recent, test_global, datetime.datetime.now().isoformat())
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 0
    print("Result: Did not fire. 39.5k is above 35k. (Correct)")
    
    mock_cursor.fetchall.side_effect = [
        [
            {'id': 9, 'user_id': 1, 'symbol': None, 'condition': 'below', 'threshold': 35000, 'window_minutes': None, 'is_currently_triggered': False, 'logic_operator': None, 'parent_rule_id': None, 'cooldown_minutes': 0, 'last_triggered_at': None, 'snoozed_until': None, 'rule_type': 'portfolio_value', 'email': 'test@test.com'}
        ],
        [
            {'user_id': 1, 'symbol': 'BTC', 'amount_held': 0.5},
            {'user_id': 1, 'symbol': 'ETH', 'amount_held': 2.0}
        ]
    ]
    print("Test 9: Portfolio drops to 31k (0.5 * 50k + 2 * 3k)")
    test_recent = {'BTC': 50000}
    test_global = {'BTC': 50000, 'ETH': 3000}
    check_rules(redis_client, test_recent, test_global, datetime.datetime.now().isoformat())
    update_calls = [call for call in mock_cursor.execute.call_args_list if "UPDATE rules SET is_currently_triggered = TRUE" in call[0][0]]
    assert len(update_calls) == 1
    print("Result: Fired successfully! (Correct)")
'''

content = content.replace('print("\\nALL COMPOSITE RULE, COOLDOWN, & SNOOZE TESTS PASSED!")', portfolio_test + '\n    print("\\nALL COMPOSITE RULE, COOLDOWN, SNOOZE, & PORTFOLIO TESTS PASSED!")')

with open('e:/Application/RippleAlert/scratch.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
