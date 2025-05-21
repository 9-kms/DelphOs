from flask import Flask, jsonify, request
from datetime import datetime

# This is a temporary file to help add the new routes
# You'll use this for reference when updating flask_server.py

def add_root_route(app, disclaimer_text, rate_limit_data, cache_duration):
    @app.route('/')
    def index():
        """
        API root - return version info
        """
        return jsonify({
            "name": "DelphOs Crypto API",
            "version": "1.1.0",
            "endpoints": [
                "/api/info",
                "/api/coins",
                "/api/ml_predictions?coin=BTC",
                "/api/prophecy/BTC", 
                "/api/search?q=bitcoin",
                "/api/discover/bullish",
                "/api/discover/bearish",
                "/api/ask_oracle"
            ],
            "disclaimer": disclaimer_text
        })

    @app.route('/api/info')
    def get_info():
        """
        Get general information including disclaimer
        """
        return jsonify({
            'name': 'DelphOs Crypto Prediction Dashboard',
            'version': '1.1.0',
            'disclaimer': disclaimer_text,
            'api_limits': {
                'coins': f"{rate_limit_data['api_coins']['limit']} requests per {rate_limit_data['api_coins']['period'] // 60} minutes",
                'predictions': f"{rate_limit_data['api_ml_predictions']['limit']} requests per {rate_limit_data['api_ml_predictions']['period'] // 60} minutes",
                'prophecy': f"{rate_limit_data['api_prophecy']['limit']} requests per {rate_limit_data['api_prophecy']['period'] // 60} minutes" 
            },
            'cache_duration': {
                'coin_data': f"{cache_duration['coingecko_top']} seconds",
                'predictions': f"{cache_duration['ml_prediction']} seconds",
                'dexscreener': f"{cache_duration['dexscreener']} seconds" 
            },
            'timestamp': datetime.now().isoformat()
        })