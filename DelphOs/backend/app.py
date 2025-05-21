import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Add the parent directory to the path so we can import the models module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db

# Create the Flask app for database-backed features
def create_app():
    app = Flask(__name__)
    
    # Configure the database with environment variables
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Set a secret key for cookie encryption
    app.secret_key = os.environ.get("SESSION_SECRET", "crypt0_dashboard_secret")
    
    # Initialize the database
    db.init_app(app)
    
    return app