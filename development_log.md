# RippleAlert - Development Log

This document outlines the step-by-step process used to build, test, and deploy the RippleAlert project.

## Step 1: Core Script Creation
- **Action**: Created `fetcher.py`.
- **Details**: Built a Python script using the `requests` and `sqlite3` libraries to fetch Bitcoin (BTC) and Ethereum (ETH) prices in USD from the free CoinGecko API. 
- **Features Implemented**:
  - A polling mechanism that executes every 10 seconds.
  - An SQLite database initialization step that automatically builds the schema (`id`, `symbol`, `price`, `timestamp`).
  - An exponential backoff error-handling system to gracefully recover from API rate limiting (HTTP 429) and network interruptions without crashing.

## Step 2: Dependency Management
- **Action**: Created `requirements.txt`.
- **Details**: Generated a standard requirements file specifying the `requests` library (version `2.31.0`) so the environment can be easily replicated on any machine via `pip install -r requirements.txt`.

## Step 3: Initial Documentation
- **Action**: Created `README.md`.
- **Details**: Drafted a markdown guide explaining the project's purpose, prerequisites, installation steps, usage instructions, and the underlying SQLite database schema. Later, appended `# Ripple-Alert` to the end of the file.

## Step 4: Testing and Database Verification
- **Action**: Executed `fetcher.py` and validated database insertions.
- **Details**: Ran the fetching script in the background for approximately 30 seconds. Afterwards, the script was terminated and a SQL query was executed on `prices.db` to verify that real timestamped prices were accurately populated.

## Step 5: Version Control & Git Initialization
- **Action**: Initialized the Git repository and created `.gitignore`.
- **Details**: 
  - Ran `git init` to start tracking the workspace.
  - Created a `.gitignore` file specifically targeting `prices.db` and Python cache files (`__pycache__/`, `*.pyc`) to prevent pushing local database instances to GitHub.
  - Executed a sequence of Git commands to add all essential source files (`fetcher.py`, `requirements.txt`, `README.md`, `.gitignore`).
  - Removed `prices.db` from the git cache after it was momentarily staged.
  - Successfully committed the code and pushed the `main` branch to the remote repository at `https://github.com/OmKarvrneKar/Ripple-Alert.git`.
