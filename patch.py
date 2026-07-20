import sys

with open('e:/Application/RippleAlert/alert_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace 1
old1 = """        cursor.execute('''
            SELECT r.id, r.user_id, r.symbol, r.condition, r.threshold, r.window_minutes, r.is_currently_triggered, r.logic_operator, r.parent_rule_id, r.cooldown_minutes, r.last_triggered_at, r.snoozed_until, u.email 
            FROM rules r
            JOIN users u ON r.user_id = u.id
        ''')
        rules = cursor.fetchall()
        
        # Update Redis sorted sets for percent change
        current_ts = datetime.fromisoformat(timestamp_str).timestamp()"""

new1 = """        cursor.execute('''
            SELECT r.id, r.user_id, r.symbol, r.condition, r.threshold, r.window_minutes, r.is_currently_triggered, r.logic_operator, r.parent_rule_id, r.cooldown_minutes, r.last_triggered_at, r.snoozed_until, r.rule_type, u.email 
            FROM rules r
            JOIN users u ON r.user_id = u.id
        ''')
        rules = cursor.fetchall()
        
        cursor.execute("SELECT user_id, symbol, amount_held FROM portfolio_holdings")
        holdings_data = cursor.fetchall()
        
        portfolio_by_user = {}
        for h in holdings_data:
            uid = h['user_id']
            if uid not in portfolio_by_user:
                portfolio_by_user[uid] = {}
            portfolio_by_user[uid][h['symbol']] = h['amount_held']
            
        # Update Redis sorted sets for percent change
        current_ts = datetime.fromisoformat(timestamp_str).timestamp()"""

if old1 not in content:
    print('Failed to find old1')
    sys.exit(1)

content = content.replace(old1, new1)

old2 = """            if rule.get('rule_type') == 'portfolio_value':
                user_holdings = portfolio_by_user.get(user_id, {})
                affected = any(sym in recent_prices for sym in user_holdings.keys())
                if not affected:
                    continue
                    
                total_value = 0.0
                for sym, amt in user_holdings.items():
                    price = global_prices.get(sym, 0.0)
                    total_value += amt * price
                    
                condition_met = False
                if rule['condition'] == 'below' and total_value < rule['threshold']:
                    condition_met = True
                elif rule['condition'] == 'above' and total_value > rule['threshold']:
                    condition_met = True
                    
                rule_description = f"Portfolio value {rule['condition']} ${rule['threshold']} (Current: ${total_value:,.2f})" if condition_met else ""
                symbol_to_log = "PORTFOLIO"
                price_to_log = total_value
                
            elif rule['logic_operator']:"""

old2_alt = """            if rule['logic_operator']:"""

if old2_alt in content:
    content = content.replace(old2_alt, old2)
else:
    print('Failed to find old2_alt')
    sys.exit(1)

with open('e:/Application/RippleAlert/alert_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Successfully patched alert_engine.py')
