import urllib.request
import xml.etree.ElementTree as ET
from sentiment_fetcher import analyze_sentiment
from email.utils import parsedate_to_datetime
import main
from fastapi.testclient import TestClient

def test_fetcher():
    url = 'https://cointelegraph.com/rss'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    items = root.findall('.//item')

    print('--- SENTIMENT FETCHER TEST ---')
    mock_db = []
    for item in items[:10]:
        title = item.find('title').text
        title_upper = title.upper()
        if not ('BTC' in title_upper or 'BITCOIN' in title_upper or 'ETH' in title_upper or 'ETHEREUM' in title_upper or 'CRYPTO' in title_upper):
            continue
        score, reason = analyze_sentiment(title)
        print(f"Headline: {title}")
        print(f"Score: {score} -> Reason: {reason}")
        print('-'*50)
        mock_db.append({'headline': title, 'sentiment_score': score, 'sentiment_reason': reason})
        
    print("\n--- MARKET MOOD API SIMULATION (BTC) ---")
    btc_news = [h for h in mock_db if 'BTC' in h['headline'].upper() or 'BITCOIN' in h['headline'].upper()]
    pos = sum(1 for h in btc_news if h['sentiment_score'] == 'positive')
    neg = sum(1 for h in btc_news if h['sentiment_score'] == 'negative')
    neu = len(btc_news) - pos - neg
    overall_mood = "neutral"
    if pos > neg:
        overall_mood = "bullish"
    elif neg > pos:
        overall_mood = "bearish"
    print(f"Overall Mood: {overall_mood}")
    print(f"Breakdown: Pos {pos}, Neg {neg}, Neu {neu}")

if __name__ == '__main__':
    test_fetcher()
