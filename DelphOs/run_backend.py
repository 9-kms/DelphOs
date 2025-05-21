import os
import sys

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Run the Flask server directly
from backend.flask_server import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)