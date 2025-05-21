"""
Integrated Flask server with watchlist support for cryptocurrency dashboard
"""
import os
import sys
import time
import logging
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime, timedelta
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db, Watchlist

# Import feature modules
from flask_server_charts import add_chart_routes
from backtesting import add_backtest_routes
from easter_eggs import add_easter_egg_routes
from news_routes import add_news_routes

# Create Flask app with database
app = Flask(__name__)
CORS(app)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Set a secret key for cookies
app.secret_key = os.environ.get("SESSION_SECRET", "crypt0_dashboard_secret")

# Initialize the database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created (if they didn't exist already)")

# Cache configuration
CACHE_TTL = 300  # Cache time-to-live in seconds (5 minutes)
LONG_CACHE_TTL = 3600  # Longer cache TTL (1 hour)
cache = {}  # In-memory cache

# Rate limit configuration
RATE_LIMITS = {
    'default': {'limit': 10, 'window': 60},  # Default: 10 requests per minute
    'search': {'limit': 20, 'window': 60},   # Search: 20 requests per minute
    'prediction': {'limit': 5, 'window': 60}, # Prediction: 5 requests per minute
    'chart': {'limit': 15, 'window': 60},     # Chart data: 15 requests per minute
    'discover': {'limit': 3, 'window': 60},   # Discover: 3 requests per minute
    'backtest': {'limit': 2, 'window': 180},  # Backtest: 2 requests per 3 minutes (heavy operation)
    'oracle': {'limit': 1, 'window': 60},     # Oracle: 1 request per minute
    'demonic': {'limit': 2, 'window': 300},   # Easter egg: 2 requests per 5 minutes
    'watchlist': {'limit': 20, 'window': 60}, # Watchlist: 20 requests per minute
}

# Rate limit tracking
rate_limit_data = {}

def check_rate_limit(api_name, ip_address=None):
    """Check if we've hit the rate limit for an API"""
    if ip_address is None:
        ip_address = request.remote_addr or 'unknown'
    
    key = f"{api_name}:{ip_address}"
    now = time.time()
    
    # Get rate limit config for this API
    limit_config = RATE_LIMITS.get(api_name, RATE_LIMITS['default'])
    limit = limit_config['limit']
    window = limit_config['window']
    
    # Initialize or clean up old requests
    if key not in rate_limit_data:
        rate_limit_data[key] = []
    else:
        # Remove requests outside the window
        rate_limit_data[key] = [t for t in rate_limit_data[key] if now - t < window]
    
    # Check if we're at the limit
    if len(rate_limit_data[key]) >= limit:
        return False
    
    # Add current request
    rate_limit_data[key].append(now)
    return True

def rate_limit(api_name):
    """Decorator for rate limiting API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not check_rate_limit(api_name):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again later.'
                }), 429
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Add watchlist routes
@app.route('/api/watchlist', methods=['GET'])
@rate_limit('watchlist')
def get_watchlist():
    """
    Get user's watchlist
    
    Parameters:
    - user_id: User identifier (optional, will use session ID if not provided)
    """
    try:
        # Get user ID (from query param or generate session ID)
        user_id = request.args.get('user_id')
        if not user_id:
            # Generate a session ID if not provided
            session_id = request.cookies.get('session_id')
            if not session_id:
                # Generate a new one
                user_id = str(uuid.uuid4())
            else:
                user_id = session_id
        
        # Get all watchlist items for this user
        watchlist_items = Watchlist.query.filter_by(user_id=user_id).all()
        
        # Format the response
        result = {
            'user_id': user_id,
            'count': len(watchlist_items),
            'coins': [item.to_dict() for item in watchlist_items]
        }
        
        response = jsonify(result)
        
        # Set a cookie with the session_id if it's a new session
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', user_id, max_age=60*60*24*30)  # 30 days
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting watchlist: {str(e)}")
        return jsonify({'error': f"Failed to get watchlist: {str(e)}"}), 500

@app.route('/api/watchlist/<symbol>', methods=['POST'])
@rate_limit('watchlist')
def add_to_watchlist(symbol):
    """
    Add a coin to the watchlist
    
    Parameters:
    - user_id: User identifier (optional, will use session ID if not provided)
    - notes: Optional notes about this coin
    """
    try:
        data = request.get_json() or {}
        
        # Get user ID (from request body or session)
        user_id = data.get('user_id')
        if not user_id:
            # Get from cookie
            session_id = request.cookies.get('session_id')
            if not session_id:
                # Generate a new one
                user_id = str(uuid.uuid4())
            else:
                user_id = session_id
        
        # Check if already in watchlist
        existing = Watchlist.query.filter_by(
            user_id=user_id, 
            coin_symbol=symbol.upper()
        ).first()
        
        if existing:
            # Update notes if provided
            if 'notes' in data:
                existing.notes = data['notes']
                db.session.commit()
            return jsonify({
                'message': f"{symbol.upper()} is already in your watchlist",
                'coin': existing.to_dict()
            })
        
        # Create new watchlist entry
        watchlist_item = Watchlist(
            user_id=user_id,
            coin_symbol=symbol.upper(),
            notes=data.get('notes')
        )
        
        db.session.add(watchlist_item)
        db.session.commit()
        
        response = jsonify({
            'message': f"Added {symbol.upper()} to your watchlist",
            'coin': watchlist_item.to_dict()
        })
        
        # Set a cookie with the session_id if it's a new session
        if not request.cookies.get('session_id'):
            response.set_cookie('session_id', user_id, max_age=60*60*24*30)  # 30 days
            
        return response
        
    except Exception as e:
        logger.error(f"Error adding to watchlist: {str(e)}")
        return jsonify({'error': f"Failed to add to watchlist: {str(e)}"}), 500

@app.route('/api/watchlist/<symbol>', methods=['DELETE'])
@rate_limit('watchlist')
def remove_from_watchlist(symbol):
    """
    Remove a coin from the watchlist
    
    Parameters:
    - user_id: User identifier (optional, will use session ID if not provided)
    """
    try:
        # Get user ID (from query param or session)
        user_id = request.args.get('user_id')
        if not user_id:
            # Get from cookie
            session_id = request.cookies.get('session_id')
            if not session_id:
                return jsonify({'error': "User ID not provided"}), 400
            user_id = session_id
        
        # Find the watchlist item
        watchlist_item = Watchlist.query.filter_by(
            user_id=user_id, 
            coin_symbol=symbol.upper()
        ).first()
        
        if not watchlist_item:
            return jsonify({
                'message': f"{symbol.upper()} is not in your watchlist"
            }), 404
        
        # Remove from watchlist
        db.session.delete(watchlist_item)
        db.session.commit()
        
        return jsonify({
            'message': f"Removed {symbol.upper()} from your watchlist"
        })
        
    except Exception as e:
        logger.error(f"Error removing from watchlist: {str(e)}")
        return jsonify({'error': f"Failed to remove from watchlist: {str(e)}"}), 500

# Index route
@app.route('/api')
def index():
    return {
        'name': 'Crypto Dashboard API',
        'version': '1.0.0',
        'features': [
            'Watchlist for saving favorite coins',
            'Price charts with technical indicators',
            'Machine learning predictions',
            'Backtesting of prediction models',
            'News sentiment analysis',
            'Easter eggs'
        ]
    }

@app.route('/api/info')
def get_info():
    """
    Get general information including disclaimer
    """
    disclaimer_text = """
    This dashboard is for educational and entertainment purposes only.
    Cryptocurrency investments are high-risk. Always do your own research.
    Technical indicators and machine learning predictions are not financial advice.
    """
    
    return jsonify({
        'name': 'DelphOs Crypto Dashboard',
        'version': '1.0.0',
        'disclaimer': disclaimer_text.strip(),
        'rate_limits': RATE_LIMITS,
        'cache_duration': CACHE_TTL
    })

# Cache implementation for feature routes
def get_cached_data(cache_key):
    """Get data from cache if not expired"""
    if cache_key in cache:
        timestamp, data = cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    return None

def set_cache(cache_key, data, ttl=None):
    """Store data in cache with timestamp"""
    cache[cache_key] = (time.time(), data)

# Add feature routes
add_chart_routes(app, rate_limit, get_cached_data, set_cache)
add_backtest_routes(app, rate_limit)
add_easter_egg_routes(app, rate_limit)
add_news_routes(app, rate_limit, get_cached_data, set_cache)

# Set up the development server
if __name__ == "__main__":
    logger.info("Starting backend server with watchlist support")
    app.run(host='0.0.0.0', port=5001, debug=True)