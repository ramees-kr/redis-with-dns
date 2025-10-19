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
        record_type = request.form.get('record_type', 'A')

        if domain_name:
            # records will be a list of IPs or an {"error": ...} dict
            records, ttl, status, duration = get_dns_lookup(domain_name, record_type)
            
            context['domain'] = domain_name
            context['records'] = records # Pass the list or dict to the template
            context['ttl'] = ttl
            context['status'] = status
            context['duration'] = f"{duration:.2f}"
            
            # Check if the lookup was successful
            is_success = (status == "hit" or status == "miss")
            
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
    context = {
        'active_page': 'hashes'
    }

    if request.method == 'POST':
        domain_name = request.form.get('domain')
        
        if domain_name and r:
            hash_key = f"{META_KEY_PREFIX}{domain_name}"
            
            # HGETALL retrieves all fields and values from the hash
            # It returns a dictionary in python-redis
            metadata = r.hgetall(hash_key)
            
            context['domain'] = domain_name
            context['hash_key'] = hash_key
            context['metadata'] = metadata
            
    return render_template('feature_hashes.html', **context)

# This allows us to run the app directly with 'python app.py'
if __name__ == '__main__':
    # debug=True will auto-reload the server when you save files
    app.run(debug=True, port=5000)