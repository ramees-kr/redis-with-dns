from flask import Flask, render_template, request
from dns_cache import get_dns_lookup, r

# Initialize the Flask app
app = Flask(__name__)

# keys for recent queries in Redis
RECENT_QUERIES_KEY = "dns:recent"
MAX_RECENT_QUERIES = 10

@app.route('/', methods=['GET', 'POST'])
def home():
    """
    Renders the Home page and handles the form submission.
    """
    # This context dict will hold all variables for the template
    context = {}
    
    if request.method == 'POST':
        # 1. Get the domain from the form
        domain_name = request.form.get('domain')
        
        if domain_name:
            # 2. Call our DNS/Redis logic
            ip, ttl, status, duration = get_dns_lookup(domain_name)
            
            # 3. Add all results to the context
            context['domain'] = domain_name
            context['ip'] = ip
            context['ttl'] = ttl
            context['status'] = status
            context['duration'] = f"{duration:.2f}"

            if r and status != "error":
                # LPUSH adds the new domain to the left (front) of the list
                r.lpush(RECENT_QUERIES_KEY, domain_name)
                # LTRIM trims the list to keep only the first 10 items (0-9)
                r.ltrim(RECENT_QUERIES_KEY, 0, MAX_RECENT_QUERIES - 1)

    # 4. Render the template, passing in all context variables
    # If it's a GET request, context is empty and the form is blank
    # If it's a POST, context is full and the results are shown
    return render_template('home.html', **context)


@app.route('/feature/lists')
def feature_lists():
    
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

# This allows us to run the app directly with 'python app.py'
if __name__ == '__main__':
    # debug=True will auto-reload the server when you save files
    app.run(debug=True, port=5000)