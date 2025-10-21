from dotenv import load_dotenv
load_dotenv()

import json
from flask import Flask, render_template, request
from dns_cache import get_dns_lookup, r
import time

# Initialize the Flask app
app = Flask(__name__)

# keys for recent queries in Redis
RECENT_QUERIES_KEY = "dns:recent"
MAX_RECENT_QUERIES = 10
META_KEY_PREFIX = "dns:meta:"
POPULARITY_KEY = "dns:popularity"

@app.route('/', methods=['GET', 'POST'])
def home():
    """
    Renders the Home page and handles the form submission.
    """
    # This context dict will hold all variables for the template
    context = {}
    context['active_page'] = 'home' 
    
    if request.method == 'POST':
        # 1. Get the domain from the form
        domain_name = request.form.get('domain')
        record_type = request.form.get('record_type', 'A').strip()

        if domain_name:
            # records will be a list of IPs or an {"error": ...} dict
            records, ttl, status, duration = get_dns_lookup(domain_name, record_type)
            
            # 1. Broaden is_success check
            is_success = (status != "error")
            
            # 2. Create explicit booleans for the template
            is_negative = 'negative' in status
            from_cache = 'hit' in status

            context['domain'] = domain_name
            context['records'] = records # Pass the list or dict to the template
            context['ttl'] = ttl
            context['status'] = status
            context['duration'] = f"{duration:.2f}"
            context['record_type'] = record_type
            context['is_negative'] = is_negative
            context['from_cache'] = from_cache
            
            if r and is_success:
                log_entry = f"{domain_name} ({record_type})"
                r.lpush(RECENT_QUERIES_KEY, log_entry)
                r.ltrim(RECENT_QUERIES_KEY, 0, MAX_RECENT_QUERIES - 1)
                
                # Metadata and Popularity are still domain-based
                hash_key = f"{META_KEY_PREFIX}{domain_name}"
                r.hincrby(hash_key, 'hit_count', 1)
                current_timestamp = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
                r.hset(hash_key, 'last_fetched', current_timestamp)
                
                r.zincrby(POPULARITY_KEY, 1, domain_name)

    return render_template('home.html', **context)


@app.route('/feature/lists')
def feature_lists():
    """
    Renders the Feature Lists page, displaying recent DNS queries.
    Fetches the list of recent queries from Redis and passes them to the template.
    """
    # Fetch the list of recent queries from Redis
    recent_queries = []
    if r:
        # LRANGE fetches a "range" from the list. 0 to -1 means "all items".
        recent_queries = r.lrange(RECENT_QUERIES_KEY, 0, -1)
        
    context = {
        'active_page': 'lists', # For sidebar navigation
        'recent_queries': recent_queries
    }
    return render_template('feature_lists.html', **context)


@app.route('/feature/hashes', methods=['GET', 'POST'])
def feature_hashes():
    """
    Renders the Hashes page, including Metadata and Core Cache Inspector.
    Allows users to input a domain and view its metadata and cached DNS records.
    """
    context = {
        'active_page': 'hashes'
    }

    if request.method == 'POST':
        domain_name = request.form.get('domain')
        
        if domain_name and r:
            # --- 1. Metadata Logic ---
            meta_key = f"{META_KEY_PREFIX}{domain_name}"
            metadata = r.hgetall(meta_key)
            
            context['domain'] = domain_name
            context['meta_key'] = meta_key 
            context['metadata'] = metadata
            
            # --- 2. Core Cache Inspector Logic (Refactored) ---
            cached_records_data = []
            scan_pattern = f"dns:cache:{domain_name}:*"
            
            # Step 1: Get all matching keys from the iterator
            keys_found = list(r.scan_iter(match=scan_pattern))
            
            if keys_found:
                # Step 2: Create ONE pipeline outside the loop
                pipe = r.pipeline()
                for key in keys_found:
                    pipe.hgetall(key)
                    pipe.ttl(key)
                
                # Step 3: Execute ONCE to get all data
                results = pipe.execute()
                
                # Step 4: Process the results
                # 'results' is a flat list: [hgetall_res1, ttl_res1, hgetall_res2, ttl_res2, ...]
                
                for i, key in enumerate(keys_found):
                    data = results[i * 2]       # The HGETALL result
                    ttl = results[i * 2 + 1]    # The TTL result
                    
                    try:
                        # Ensure 'data' is a dict before a .get()
                        data = data if isinstance(data, dict) else {}
                        data['records_list'] = json.loads(data.get('records', '[]'))
                    except (json.JSONDecodeError, TypeError) as e:
                        data['records_list'] = [f"Error parsing JSON: {e}"]

                    cached_records_data.append({'key': key, 'data': data, 'ttl': ttl})
            
            context['cached_records_data'] = cached_records_data

    return render_template('feature_hashes.html', **context)

@app.route('/feature/zsets')
def feature_zsets():
    """
    Renders the Sorted Sets feature page, showing a leaderboard.
    """
    context = {
        'active_page': 'zsets'
    }
    
    leaderboard = []
    if r:
        # ZREVRANGE fetches a "reverse range" (highest score to lowest)
        # We ask for ranks 0-9 (top 10) and use WITHSCORES=True
        # This returns a list of tuples: [('google.com', 10.0), ('bing.com', 5.0)]
        leaderboard = r.zrevrange(POPULARITY_KEY, 0, 9, withscores=True)
        
    context['leaderboard'] = leaderboard
    context['leaderboard_key'] = POPULARITY_KEY
        
    return render_template('feature_zsets.html', **context)


# This allows us to run the app directly with 'python app.py'
if __name__ == '__main__':
    # debug=True will auto-reload the server when you save files
    app.run(debug=True, port=5000)