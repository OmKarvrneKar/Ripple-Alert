import sys

with open('e:/Application/RippleAlert/sentiment_fetcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """            try:
                cursor.execute('''
                    INSERT INTO news_headlines (headline, source, url, timestamp)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                ''', (title, 'Cointelegraph', link, pub_ts))
                
                # If rowcount is > 0, it means it was inserted (not conflicting)
                if cursor.rowcount > 0:"""

new_code = """            sentiment_score, sentiment_reason = analyze_sentiment(title)
            try:
                cursor.execute('''
                    INSERT INTO news_headlines (headline, source, url, timestamp, sentiment_score, sentiment_reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                ''', (title, 'Cointelegraph', link, pub_ts, sentiment_score, sentiment_reason))
                
                # If rowcount is > 0, it means it was inserted (not conflicting)
                if cursor.rowcount > 0:"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('e:/Application/RippleAlert/sentiment_fetcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done!')
else:
    print('Target not found')
