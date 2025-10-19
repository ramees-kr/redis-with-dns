from flask import Flask, render_template, request
from dns_cache import get_dns_lookup

# Initialize the Flask app
app = Flask(__name__)

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

    # 4. Render the template, passing in all context variables
    # If it's a GET request, context is empty and the form is blank
    # If it's a POST, context is full and the results are shown
    return render_template('home.html', **context)

# This allows us to run the app directly with 'python app.py'
if __name__ == '__main__':
    # debug=True will auto-reload the server when you save files
    app.run(debug=True, port=5000)