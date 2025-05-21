"""
Main Flask server for our cryptocurrency dashboard with watchlist feature
"""
import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db, Watchlist

def create_app():
    """Create and configure the Flask app with database"""
    app = Flask(__name__)
    CORS(app)
    
    # Configure database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Set secret key for cookies
    app.secret_key = os.environ.get("SESSION_SECRET", "crypt0_dashboard_secret")
    
    # Initialize the database
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        logger.info("Database tables created (if they didn't exist already)")
        
    return app

def add_watchlist_routes(app, rate_limit_decorator=None):
    """
    Add watchlist routes to Flask app
    """
    
    # Dummy decorator if none provided (for standalone testing)
    if rate_limit_decorator is None:
        def rate_limit_decorator(api_name):
            def decorator(func):
                return func
            return decorator
    
    @app.route('/api/watchlist', methods=['GET'])
    @rate_limit_decorator('watchlist')
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
    @rate_limit_decorator('watchlist')
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
    @rate_limit_decorator('watchlist')
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

    logger.info("Watchlist routes added successfully")
    return app

# For standalone testing
if __name__ == "__main__":
    app = create_app()
    app = add_watchlist_routes(app)
    app.run(host='0.0.0.0', port=5002, debug=True)