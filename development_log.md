# RippleAlert - Development Log

This document outlines the step-by-step process used to build, test, and deploy the RippleAlert project.

## Step 1: Core Script Creation
- **Action**: Created `fetcher.py`.
- **Details**: Built a Python script using the `requests` and `sqlite3` libraries to fetch Bitcoin and Ethereum prices every 10 seconds with an exponential backoff error-handling system.

## Step 2: FastAPI Backend & Authentication
- **Action**: Created `main.py`.
- **Details**: Built a robust backend supporting user authentication. Users are stored in a dedicated `users.db`. Secure signup/login endpoints were implemented utilizing **bcrypt** for robust password hashing, and generating JSON Web Tokens (JWT) for secure session tracking.

## Step 3: Frontend Interface
- **Action**: Created `frontend/index.html`.
- **Details**: Built a sleek, single-page application dashboard supporting signups, logins, and dynamic watchlists, instantly reacting to incoming price data.

## Step 4: WebSockets & Redis Pub/Sub Decoupling
- **Action**: Integrated WebSockets and Redis into the architecture.
- **Details**: 
  - `fetcher.py` was separated into an entirely independent background process. After fetching data, it stores it in SQLite and publishes the JSON payload to a Redis `prices` channel.
  - `main.py` runs a background task using `redis.asyncio` that subscribes to the Redis channel. 
  - When messages arrive from Redis, `main.py` instantly forwards them across open WebSockets to all connected browser clients.
  - This architecture ensures strict decoupling: the FastAPI server can be restarted safely without interrupting the independent `fetcher.py` process.

## Step 5: Alert Engine
- **Action**: Created `alert_engine.py` and `/rules` endpoint.
- **Details**: 
  - Added a `rules` table in the SQLite database to store user-defined alert thresholds.
  - Added a `POST /rules` endpoint in `main.py` allowing users to configure price alerts (e.g., BTC below $60k).
  - Created a new standalone process `alert_engine.py` that subscribes to the Redis `prices` channel.
  - The engine continuously compares incoming live prices against active user rules, triggering and logging clear alerts when thresholds are crossed, and resetting them when prices bounce back.

## Step 6: Extended Alert System & Rolling Windows
- **Action**: Added alert history logging and rolling percent change rule.
- **Details**: 
  - Added an `alert_history` table and a `GET /alert-history` endpoint to serve the log of fired alerts back to the user interface.
  - Expanded the rule logic to support a `percent_change_in_window` condition (e.g., BTC moved > 3% in 60 minutes).
  - Used Redis Sorted Sets (`ZADD` and `ZREMRANGEBYSCORE`) to efficiently track historical prices bounded by the rolling window on the fly.
  - Updated the frontend UI to fetch and render the user's alert history cleanly below the live prices section.

## Step 7: Finalization & Containerization
- **Action**: Migrated to PostgreSQL, orchestrated with Docker Compose, and prepared CI/CD.
- **Details**: 
  - **Database Migration**: Swapped SQLite for PostgreSQL (`psycopg2-binary`) to make the app production-ready. Unified the schema to use `DATABASE_URL` for the `users` and `prices` data.
  - **Container Orchestration**: Added a comprehensive `docker-compose.yml` to orchestrate 5 distinct services: `web`, `worker`, `alert-engine`, `db` (Postgres 15), and `redis` (Redis 7).
  - **Environment Context**: Updated all Python components to consume `DATABASE_URL`, `REDIS_HOST`, and `REDIS_PORT` dynamically from their container environment, falling back to localhost for local testing.
  - **CI/CD Actions**: Wrote `.github/workflows/deploy.yml` to automate Render deployment triggers upon pushed commits to `main`.

## Step 8: Live Deployment & Final Debugging
- **Action**: Hardened the Docker deployment and resolved critical production dependency issues.
- **Details**:
  - **Connection Strings**: Solved an edge-case where `DATABASE_URL` injections from cloud providers start with `postgres://` instead of `postgresql://` by safely parsing and substituting the prefix for `psycopg2`.
  - **Docker Compose Race Conditions**: Fixed intermittent startup failures where the `web`, `fetcher`, and `alert_engine` crashed trying to query Postgres before the database was ready. Addressed by wrapping initial connections in a 5-iteration exponential backoff loop.
  - **Dependency Pinning**: Diagnosed a 500 Internal Server Error in `/login`. Discovered `passlib` broke due to an API change in `bcrypt` v4.1+. Fixed by pinning `bcrypt==4.0.1`.
  - **Missing Dependencies**: Fixed a runtime crash due to missing `python-multipart` required by FastAPI's `OAuth2PasswordRequestForm`.
  - **End-to-End Testing**: Validated the fully containerized system using an automated `test_docker.py` script that tests signup, WebSockets, rule insertion, and Alert History population.