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
