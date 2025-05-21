#!/usr/bin/env python3
"""
Run the fixed Flask backend server for crypto dashboard
This version uses the fixed server implementation
"""
from fixed_server import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)