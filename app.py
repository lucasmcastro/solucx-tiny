import os
from datetime import datetime
from flask import Flask, session, redirect, url_for, request, render_template
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
import requests

# Load environment variables from .env file
load_dotenv()

TINY_CLIENT_ID = os.getenv('TINY_CLIENT_ID')
TINY_CLIENT_SECRET = os.getenv('TINY_CLIENT_SECRET')
TINY_REDIRECT_URI = os.getenv('TINY_REDIRECT_URI')
TINY_AUTHORIZATION_URL = os.getenv('TINY_AUTHORIZATION_URL') # e.g., 'https://erp.tiny.com.br/authorize'
TINY_TOKEN_URL = os.getenv('TINY_TOKEN_URL')           # e.g., 'https://api.tiny.com.br/api2/token'
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
TINY_API_BASE_URL = os.getenv('TINY_API_BASE_URL')
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # disable SSL verification

# --- Verify essential configuration is present ---
if not all([TINY_CLIENT_ID, TINY_CLIENT_SECRET, TINY_REDIRECT_URI,TINY_AUTHORIZATION_URL, TINY_TOKEN_URL, FLASK_SECRET_KEY]):
    raise ValueError("Essential Tiny ERP or Flask configuration is missing in .env file.")

# Define the scope required by Tiny ERP API (Adjust if needed)
TINY_SCOPE = ['Pedidos'] # Example scope, check Tiny docs

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

@app.route('/')
def index():
    """Home page: Shows login status and actions."""
    logged_in = 'access_token' in session
    return render_template('index.html', logged_in=logged_in)

@app.route('/login')
def login():
    """Redirects the user to Tiny ERP's authorization page."""
    tiny_session = OAuth2Session(TINY_CLIENT_ID, redirect_uri=TINY_REDIRECT_URI) #, scope=TINY_SCOPE)
    authorization_url, state = tiny_session.authorization_url(TINY_AUTHORIZATION_URL)

    # Store the state in the session for later validation
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    """Handles the callback from Tiny ERP after authorization."""
    # Verify state to prevent CSRF attacks
    if request.args.get('state') != session.get('oauth_state'):
        return 'Invalid state parameter', 400

    tiny_session = OAuth2Session(TINY_CLIENT_ID, redirect_uri=TINY_REDIRECT_URI, state=session['oauth_state'])

    try:
        token = tiny_session.fetch_token(
            TINY_TOKEN_URL,
            client_secret=TINY_CLIENT_SECRET,
            authorization_response=request.url # Provides the full callback URL including the code
        )
        # Store the token in the session
        session['access_token'] = token['access_token']
        session['token_type'] = token.get('token_type', 'Bearer') # Usually Bearer
        # Optionally store refresh token, expiry time etc. if needed
        # session['refresh_token'] = token.get('refresh_token')
        # session['expires_at'] = time.time() + token.get('expires_in', 3600)

    except Exception as e:
        print(f"Error fetching token: {e}") # Log the error
        return f'Error fetching token: {e}', 500

    # Clear the state now that we've used it
    session.pop('oauth_state', None)

    return redirect(url_for('index'))

@app.route('/fetch_orders')
def fetch_orders():
    """Fetches orders from Tiny ERP API using the stored access token."""
    if 'access_token' not in session:
        return redirect(url_for('login'))

    access_token = session['access_token']
    token_type = session.get('token_type', 'Bearer')

    # Prepare OAuth2 session with the token
    # Note: requests-oauthlib automatically adds the Authorization header
    # However, for direct requests usage, you'd format it like:
    headers = {
        'Authorization': f'{token_type} {access_token}',
        'Accept': 'application/json' # Good practice to specify accept header
    }

    # Calculate dataAtualizacao (today's date in YYYY-MM-DD format)
    # today_date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Construct the API URL
    orders_url = f"{TINY_API_BASE_URL}/pedidos"
    params = {'dataAtualizacao': '2025-04-16', 'formato': 'json'} # Add formato=json if required by API

    try:
        response = requests.get(orders_url, headers=headers, params=params)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        orders_data = response.json()
        # Assuming the structure is {'status': 'OK', 'registros': [...]} based on some API patterns
        # Adjust parsing based on actual Tiny ERP API response structure
        if orders_data.get('paginacao').get('total') > 0:
             # Check if 'registros' key exists and contains a list
            if 'itens' in orders_data and isinstance(orders_data['itens'], list):
                # Drill down if orders are nested, e.g., under 'pedido' key
                orders = orders_data['itens']
                return render_template('orders.html', orders=orders)
            else:
                 # Handle case where status is OK but data format is unexpected
                 return render_template('orders.html', error="API returned OK but data format is unexpected.")
        elif orders_data.get('status') == 'Erro':
             error_msg = orders_data.get('erros', ['Unknown error'])[0]
             return render_template('orders.html', error=f"API Error: {error_msg}")
        else:
             # Handle unexpected status values
             return render_template('orders.html', error=f"Unexpected API status: {orders_data.get('status')}")


    except requests.exceptions.RequestException as e:
        print(f"Error calling Tiny API: {e}") # Log the error
        error_message = f"Error contacting Tiny API: {e}"
        # Try to get more details from response if available
        if e.response is not None:
             try:
                 error_details = e.response.json()
                 error_message += f" - {error_details}"
             except ValueError: # If response is not JSON
                 error_message += f" - {e.response.text}"
        return render_template('orders.html', error=error_message)
    except Exception as e: # Catch other potential errors during processing
        print(f"An unexpected error occurred: {e}") # Log the error
        return render_template('orders.html', error=f"An unexpected error occurred: {e}")


@app.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Ensure templates directory exists (optional, Flask usually finds it)
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # Run in debug mode for development, listening on port 5000
    app.run(host='0.0.0.0', port=8000, debug=True)

