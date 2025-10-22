# Redis DNS Caching Tutorial & Dashboard

**Live Demo:** [https://redis-with-dns.onrender.com/](https://redis-with-dns.onrender.com/)

This project is a hands-on, interactive web application designed to teach core Redis data structures by building a practical, high-performance DNS caching system.

The application is a "tutorial dashboard" that not only performs real DNS lookups but also visualizes how different Redis data structures are used together to cache results, track analytics, and manage data efficiently.

![Redis DNS Dashboard Screenshot](docs/screenshots/001-dashboard.jpeg)

## Features

- **Live DNS Query Tool:** Performs DNS lookups for `A`, `MX`, `TXT`, and `NS` records.
- **Intelligent Caching:**
  - Caches successful lookups in a **Redis Hash** with the record's real TTL.
  - Caches failed lookups (`NXDOMAIN`, NoAnswer) in a **Redis String** (negative caching) to reduce load on upstream servers.
  - Clears stale negative cache entries upon successful lookup.
- **Central Dashboard:** The homepage provides a complete overview, showcasing multiple Redis data types working together:
  - Query results (Hash/String)
  - Domain metadata (Hash)
  - All cached records for the domain (Hash + `SCAN`)
  - Recent query log (List)
  - Popularity leaderboard (Sorted Set)
- **Deep-Dive Pages:** Each data structure has its own dedicated tutorial page explaining the "Why" (use case) and "How" (code and performance) with interactive examples.

## Tech Stack

- **Backend:** Python 3, Flask
- **Database:** Redis (connects to Redis Cloud or local instance)
- **DNS:** `dnspython` library
- **Frontend:** Bootswatch (Vapor Theme)
- **Deployment:** Render, Gunicorn

## How to Run Locally

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/ramees-kr/redis-with-dns.git
    cd redis-with-dns
    ```

2.  **Start Redis (Local):**
    The simplest way is with Docker:

    ```bash
    docker run -d -p 6379:6379 --name redis-dns-tutorial redis/redis-stack:latest
    ```

    _(Alternatively, set up a `.env` file with your Redis Cloud credentials as shown in Deployment Setup below)_

3.  **Set up Python environment:**

    ```bash
    python -m venv venv
    # Activate: source venv/bin/activate (macOS/Linux) or .\venv\Scripts\activate (Windows)
    pip install -r requirements.txt
    ```

4.  **Run the Flask application:**

    ```bash
    flask --app app run --debug
    ```

5.  Open your browser to `http://127.0.0.1:5000`.

---

## Deployment Setup (Render + Redis Cloud)

This app is designed for easy deployment on platforms like Render using a cloud Redis provider.

1.  **Create a free Redis Cloud database:**

    - Sign up at [Redis Cloud](https://redis.com/try-free/).
    - Create a new database and note down the **Host**, **Port**, and **Password**.

2.  **Deploy on Render:**
    - Create a new "Web Service" on Render and connect it to your GitHub repository.
    - Render will automatically detect `requirements.txt` and `Procfile`.
    - Go to the "Environment" tab and add the following environment variables using the credentials from Redis Cloud:
      - `REDIS_HOST`: (Your Redis Cloud host)
      - `REDIS_PORT`: (Your Redis Cloud port)
      - `REDIS_PASSWORD`: (Your Redis Cloud password)
      - `REDIS_USERNAME`: `default` (usually)
    - Render will build and deploy your application.

_(Optional: For local development using Redis Cloud, create a `.env` file in the root directory with the above variables and add `from dotenv import load_dotenv; load_dotenv()` at the top of `app.py`. Make sure `.env` is in your `.gitignore`!)_

---

## Learning Guide: Redis Data Structures

This project demonstrates practical uses for several core Redis data structures.

### 1. Redis Strings

- **Use Case:** Negative Caching.
- **Implementation:** `SETEX` stores "NXDOMAIN" status with a short TTL for failed lookups.

### 2. Redis Lists

- **Use Case:** Recent Query Log (capped list).
- **Implementation:** `LPUSH` adds queries, `LTRIM` keeps the list size fixed.

### 3. Redis Hashes

- **Use Cases:** Storing structured cache data and atomic counters.
- **Implementation:**
  - Core cache stores DNS results (`records`, `fetched_at`).
  - Metadata uses `HINCRBY` for hit counts.
  - `SCAN` iterates keys efficiently for the dashboard inspector.

### 4. Redis Sorted Sets (ZSETs)

- **Use Case:** Real-time popularity leaderboard.
- **Implementation:** `ZINCRBY` atomically updates domain scores on each query; `ZREVRANGE` retrieves the top N.
