import sys
import os
from flask import Flask, render_template, send_from_directory, request, redirect
import requests
import subprocess
import threading

# Add the current directory to path so we can import modules properly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create Flask app for serving frontend
app = Flask(__name__, static_folder='frontend/public')

# Serve the frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# Proxy API requests to the backend
@app.route('/api/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy_api(path):
    backend_url = 'http://localhost:5001/api/' + path
    
    # Forward the request to the backend
    if request.method == 'GET':
        response = requests.get(backend_url, params=request.args)
    elif request.method == 'POST':
        response = requests.post(backend_url, json=request.json)
    elif request.method == 'DELETE':
        response = requests.delete(backend_url, params=request.args)
    
    # Return the response from the backend
    return response.content, response.status_code, response.headers.items()

if __name__ == "__main__":
    # The Flask backend is started by the separate workflow
    print("Frontend and API proxy running at http://0.0.0.0:5000")
    print("Backend service running at http://localhost:5001/api")
    app.run(host='0.0.0.0', port=5000, debug=True)