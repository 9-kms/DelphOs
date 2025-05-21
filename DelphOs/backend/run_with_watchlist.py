"""
Run the Flask backend server with watchlist support enabled
This version integrates all features including database-backed watchlist
"""
import os
import sys
import logging
from flask import Flask
from flask_cors import CORS

# Add the current directory to path so we can import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import feature modules
from backend.flask_server_charts import add_chart_routes
from backend.backtesting import add_backtest_routes
from backend.easter_eggs import add_easter_egg_routes
from backend.news_routes import add_news_routes
from backend.flask_server_watchlist import create_app, add_watchlist_routes

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rate_limit(api_name):
    """Decorator for rate limiting API calls"""
    def decorator(func):
        # For simplicity, we're not implementing actual rate limiting in this version
        return func
    return decorator

if __name__ == "__main__":
    # Create app with database support for watchlist
    app = create_app()
    CORS(app)
    
    # Add all feature routes
    add_watchlist_routes(app, rate_limit)
    add_chart_routes(app, rate_limit, None, None)  # Simplified for demo
    add_backtest_routes(app, rate_limit)
    add_easter_egg_routes(app, rate_limit)
    add_news_routes(app, rate_limit, None, None)   # Simplified for demo
    
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
    
    # Run the server
    logger.info("Starting backend server with watchlist support")
    app.run(host='0.0.0.0', port=5001, debug=True)