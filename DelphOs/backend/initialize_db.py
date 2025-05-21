import sys
import os

# Add the current directory to path so we can import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from models import db

if __name__ == "__main__":
    print("Initializing database...")
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
    print("Database initialization complete!")