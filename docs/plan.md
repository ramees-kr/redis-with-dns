# Redis DNS Tutorial: Development Plan

This plan outlines the steps to build a web-based application and tutorial. The primary goal is to learn and teach Redis data structures by building a practical DNS caching tool.

The application will be a "tutorial dashboard" with a uniform UI:

- A **sidebar** for navigating between features.
- A **main content area** that demonstrates the feature, explains the use case, and shows the code/commands used.

---

## Phase 1: The MVP (Core App & UI Shell)

**Goal:** Get a working Flask application with the basic UI shell and the core DNS lookup tool. This phase will demonstrate **Redis Strings** implicitly.

1.  **Setup (Local Environment)**

    - Start Redis using Docker: `docker run -d -p 6379:6379 --name redis-dns-cache redis/redis-stack:latest`
    - Create a Python virtual environment: `python -m venv venv` and activate it.
    - Install dependencies: `pip install flask redis dnspython` (and `gunicorn` for later).

```bash
redis-dns-tutorial/
├── venv/                 # Your Python virtual environment
├── app.py                # Your main Flask application
├── dns_cache.py          # Our module for all Redis & DNS logic
├── templates/
│   ├── layout.html       # The main UI shell (sidebar, content)
│   └── home.html         # The "Home / DNS Query" page
├── .gitignore            # (You've already provided this)
├── plan.md               # The plan we just created
└── requirements.txt      # (We will add to this)
```

2.  **Core DNS Cache Logic (`dns_cache.py`)**

    - Create a Python module that handles:
      - Connecting to the Redis instance.
      - A single function `get_dns_lookup(domain)` that:
        - Checks Redis for a key (e.g., `dns:google.com`).
        - **On cache hit:** Returns the IP and TTL from Redis.
        - **On cache miss:** Performs a real DNS lookup (using `dnspython`), saves it to Redis using `SETEX` (which sets a key and TTL), and returns the IP.

3.  **Flask App Setup (`app.py`)**

    - Create the main `app.py` file.
    - Import Flask and the `dns_cache` module.
    - Create a Redis connection instance.

4.  **Uniform UI Shell (Templates)**

    - Create `templates/layout.html` using a Bootstrap CDN.
    - This file will contain the main structure:
      - A persistent **sidebar** (left).
      - A **main content block** (right).
    - Add the first link to the sidebar: "Home (DNS Query)".

5.  **Page 1: "Home / DNS Query"**
    - Create a route `/` in `app.py`.
    - Create a template `templates/home.html` that `extends layout.html`.
    - This page will contain:
      - An HTML form to input a domain name.
      - A "result" area that, on submit, shows:
        - The domain queried.
        - The IP address found.
        - Cache Status: "Cache Hit" or "Cache Miss".
        - The key's remaining TTL in Redis.

---

## Phase 2: Tutorial Feature - Redis Lists

**Goal:** Implement a "Recent Queries" list to demonstrate the **List** data structure.

1.  **Update Core Logic**

    - In `app.py` (or `dns_cache.py`), modify the query function.
    - After _every_ lookup, `LPUSH` the domain name to a key `dns:recent`.
    - Immediately after, `LTRIM` the list to `0, 9` to keep only the 10 most recent items.

2.  **Create "Lists" Page**

    - Add a "Data Structure: Lists" link to the sidebar in `layout.html`.
    - Create a new route `/feature/lists` in `app.py`.
    - This route will fetch all items from the list using `LRANGE dns:recent 0 -1`.
    - Create a `templates/feature_lists.html` template.

3.  **Build 3-Box Layout (in `feature_lists.html`)**
    - **Box 1 (Demo):** "Live Feature: Recent Queries". Display the list of 10 recent queries. Users can go to the "Home" page, query a domain, and see this list update.
    - **Box 2 (Use Case):** "Why use a List?". Explain that Lists are perfect for capped logs or timelines. `LPUSH` is O(1) (very fast) for adding new items, and `LTRIM` efficiently trims the list to a fixed size.
    - **Box 3 (Commands):** "Code & Performance". Show the Python code (`r.lpush(...)`, `r.ltrim(...)`, `r.lrange(...)`) and the raw Redis commands (`LPUSH`, `LTRIM`, `LRANGE`) with their Big O performance.

---

## Phase 3: Tutorial Feature - Redis Hashes

**Goal:** Store and display metadata (hit count, last fetched) for domains using the **Hash** data structure.

1.  **Update Core Logic**

    - Modify the query function again.
    - On every lookup for a domain (e.g., `google.com`):
      - `HINCRBY` a key `dns:meta:google.com` and a field `hit_count` by 1.
      - `HSET` the same key with a field `last_fetched` to the current timestamp.

2.  **Create "Hashes" Page**

    - Add a "Data Structure: Hashes" link to the sidebar.
    - Create a new route `/feature/hashes` in `app.py`.
    - This route will include a form to look up metadata for a domain.
    - When submitted, it will use `HGETALL` on `dns:meta:<domain>` to get all fields.
    - Create a `templates/feature_hashes.html` template.

3.  **Build 3-Box Layout**
    - **Box 1 (Demo):** "Live Feature: Domain Metadata". Show the lookup form. When a user enters a domain, display its metadata (hit count, last fetched) in a table.
    - **Box 2 (Use Case):** "Why use a Hash?". Explain that Hashes are ideal for storing objects. They group related fields under a single key, which is much more memory-efficient than many top-level keys (e.g., `dns:google.com:hits`, `dns:google.com:last_fetched`).
    - **Box 3 (Commands):** "Code & Performance". Show Python (`r.hincrby(...)`, `r.hset(...)`, `r.hgetall(...)`) and raw Redis (`HINCRBY`, `HSET`, `HGETALL`) commands and performance.

---

## Phase 4: Tutorial Feature - Redis Sorted Sets (ZSETs)

**Goal:** Create a "Top Queried Domains" leaderboard using the **Sorted Set** data structure.

1.  **Update Core Logic**

    - In the query function, add one more command:
    - `ZINCRBY` a key `dns:popularity` by 1 for the queried domain. This command will add the member if it doesn't exist or increment its score if it does.

2.  **Create "Sorted Sets" Page**

    - Add a "Data Structure: Sorted Sets" link to the sidebar.
    - Create a new route `/feature/zsets` in `app.py`.
    - This route will fetch the top 10 domains using `ZREVRANGE dns:popularity 0 9 WITHSCORES`.
    - Create a `templates/feature_zsets.html` template.

3.  **Build 3-Box Layout**
    - **Box 1 (Demo):** "Live Feature: Top 10 Leaderboard". Display an ordered list of the top 10 most queried domains and their scores (query counts).
    - **Box 2 (Use Case):** "Why use a Sorted Set?". Explain that ZSETs are perfect for leaderboards. They maintain a sorted collection, and `ZINCRBY` provides an atomic, high-performance way to update scores.
    - **Box 3 (Commands):** "Code & Performance". Show Python (`r.zincrby(...)`, `r.zrevrangewithscores(...)`) and raw Redis (`ZINCRBY`, `ZREVRANGE ... WITHSCORES`) commands and performance.

---

## Phase 5: Future Features & Learning

**Goal:** Plan for subsequent learning modules based on the original project ideas.

- **Feature: Redis Streams**
  - **Use Case:** A detailed, immutable log of all query events.
  - **Demo:** Use `XADD` to log every single DNS query (domain, IP, timestamp) to a Stream. Build a "Log Viewer" page that uses `XRANGE` or `XREAD`.
- **Feature: Redis Pub/Sub**
  - **Use Case:** Real-time notifications.
  - **Demo:** `PUBLISH` a message on a channel (e.g., `queries`) every time a new domain is queried. Build a simple UI that uses JavaScript (WebSocket) to `SUBSCRIBE` to that channel and show a live-updating feed.
- **Feature: Negative Caching**
  - **Use Case:** Improve performance by caching _failures_ (e.g., `NXDOMAIN`).
  - **Demo:** Update the core logic to also cache "Not Found" results (with a short TTL) to prevent re-querying for non-existent domains.
