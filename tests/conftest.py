import pytest
from httpx import AsyncClient, ASGITransport
import psycopg2
from unittest.mock import patch
import os
import sys

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

test_db_url = "postgresql://ripple_user:ripple_pass@db:5432/ripplealert"

# Configure the test connection overriding schema
def get_test_db_connection():
    conn = psycopg2.connect(test_db_url)
    cur = conn.cursor()
    cur.execute("SET search_path TO test_schema")
    cur.close()
    return conn

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Setup test schema
    conn = psycopg2.connect(test_db_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP SCHEMA IF EXISTS test_schema CASCADE")
    cur.execute("CREATE SCHEMA test_schema")
    cur.close()
    conn.close()

    # Mock DB connection
    with patch("main.get_db_connection", side_effect=get_test_db_connection), \
         patch("alert_engine.get_db_connection", side_effect=get_test_db_connection):
        # We need to initialize the tables in the test schema
        from main import init_users_db
        init_users_db()
        
        # Also create prices table for tests
        conn = get_test_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()
        
        yield
    
    # Teardown
    conn = psycopg2.connect(test_db_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP SCHEMA IF EXISTS test_schema CASCADE")
    cur.close()
    conn.close()

@pytest.fixture
async def async_client():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.fixture
def test_user():
    return {"email": "test@example.com", "password": "testpassword123"}
