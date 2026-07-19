import os
import time
import logging
import urllib.request
import xml.etree.ElementTree as ET
import psycopg2
from datetime import datetime
from email.utils import parsedate_to_datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SENTIMENT FETCHER - %(message)s')

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost/ripplealert")

def get_db_connection():
    db_url = DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(db_url)
    return conn

def fetch_and_store_news():
    url = 'https://cointelegraph.com/rss'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logging.info("Fetching latest crypto news from Cointelegraph...")
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        new_articles = 0
        
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            pubDate_str = item.find('pubDate').text
            
            # Filter for BTC or ETH keywords to be relevant
            title_upper = title.upper()
            if not ('BTC' in title_upper or 'BITCOIN' in title_upper or 'ETH' in title_upper or 'ETHEREUM' in title_upper or 'CRYPTO' in title_upper):
                continue
                
            try:
                # parsedate_to_datetime parses RFC 2822 dates commonly found in RSS
                pub_ts = parsedate_to_datetime(pubDate_str)
            except Exception:
                pub_ts = datetime.utcnow()
                
            try:
                cursor.execute('''
                    INSERT INTO news_headlines (headline, source, url, timestamp)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                ''', (title, 'Cointelegraph', link, pub_ts))
                
                # If rowcount is > 0, it means it was inserted (not conflicting)
                if cursor.rowcount > 0:
                    new_articles += 1
            except psycopg2.Error as e:
                logging.error(f"Error inserting headline: {e}")
                conn.rollback()
                continue
                
        conn.commit()
        logging.info(f"Stored {new_articles} new relevant headlines.")
        
    except Exception as e:
        logging.error(f"Failed to fetch news: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logging.info("Starting Sentiment Fetcher Service...")
    while True:
        fetch_and_store_news()
        # Poll every 20 minutes
        time.sleep(20 * 60)
