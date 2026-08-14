import sys

with open('e:/Application/RippleAlert/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """@app.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):"""

new_code = """@app.get("/market-mood/{symbol}")
def get_market_mood(symbol: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Fetch recent headlines containing symbol
    cursor.execute('''
        SELECT headline, source, url, timestamp, sentiment_score, sentiment_reason
        FROM news_headlines
        WHERE upper(headline) LIKE %s
        ORDER BY timestamp DESC LIMIT 20
    ''', (f"%{symbol.upper()}%",))
    headlines = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not headlines:
        return {"symbol": symbol.upper(), "overall_mood": "neutral", "score_breakdown": {"positive": 0, "negative": 0, "neutral": 0}, "headlines": []}
        
    pos = sum(1 for h in headlines if h['sentiment_score'] == 'positive')
    neg = sum(1 for h in headlines if h['sentiment_score'] == 'negative')
    neu = len(headlines) - pos - neg
    
    overall_mood = "neutral"
    if pos > neg:
        overall_mood = "bullish"
    elif neg > pos:
        overall_mood = "bearish"
        
    return {
        "symbol": symbol.upper(),
        "overall_mood": overall_mood,
        "score_breakdown": {"positive": pos, "negative": neg, "neutral": neu},
        "headlines": [dict(h) for h in headlines]
    }

@app.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('e:/Application/RippleAlert/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done!')
else:
    print('Target not found')
