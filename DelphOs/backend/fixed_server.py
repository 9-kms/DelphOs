from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import local ml_utils with fixed implementation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from ml_utils_fixed import generate_prediction
    logger.info("Using fixed ML prediction utilities")
except ImportError:
    from ml_utils import generate_prediction
    logger.warning("Using original ML prediction utilities")

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS specifically for API routes

# API base URLs
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex"

# ---------- CACHING SYSTEM ----------
# Simple in-memory cache
cache = {
    'data': {},
    'timestamps': {}
}

# Cache duration in seconds
CACHE_DURATION = {
    'coingecko_top': 60,          # Top coins - 1 minute
    'coingecko_search': 300,      # Search results - 5 minutes
    'dexscreener': 300,           # DexScreener data - 5 minutes
    'ml_prediction': 600          # ML predictions - 10 minutes
}

# Cache lock for thread safety
cache_lock = threading.Lock()

def get_cached_data(cache_key):
    """Get data from cache if not expired"""
    with cache_lock:
        if cache_key in cache['data'] and cache_key in cache['timestamps']:
            # Check if cache has expired
            cache_type = cache_key.split('_')[0]
            duration = CACHE_DURATION.get(cache_type, 60)
            
            if datetime.now() - cache['timestamps'][cache_key] < timedelta(seconds=duration):
                logger.debug(f"Cache hit for {cache_key}")
                return cache['data'][cache_key]
            else:
                logger.debug(f"Cache expired for {cache_key}")
    return None

def set_cache(cache_key, data):
    """Store data in cache with timestamp"""
    with cache_lock:
        cache['data'][cache_key] = data
        cache['timestamps'][cache_key] = datetime.now()
        logger.debug(f"Cached data for {cache_key}")

# ---------- RATE LIMITING ----------
# Rate limit tracker
rate_limit_data = {
    'coingecko': {
        'calls': [],
        'limit': 30,          # Conservative limit (real is 50/min)
        'period': 60          # 1 minute
    },
    'dexscreener': {
        'calls': [],
        'limit': 10,          # Conservative limit (real is ~12/hour)
        'period': 300         # 5 minutes
    }
}

rate_limit_lock = threading.Lock()

def check_rate_limit(api_name):
    """Check if we've hit the rate limit for an API"""
    now = time.time()
    with rate_limit_lock:
        # Remove expired timestamps
        rate_limit_data[api_name]['calls'] = [
            timestamp for timestamp in rate_limit_data[api_name]['calls']
            if timestamp > now - rate_limit_data[api_name]['period']
        ]
        
        # Check if we're over the limit
        if len(rate_limit_data[api_name]['calls']) >= rate_limit_data[api_name]['limit']:
            logger.warning(f"Rate limit exceeded for {api_name}")
            return False
        
        # Add this call
        rate_limit_data[api_name]['calls'].append(now)
        return True

def rate_limit(api_name):
    """Decorator for rate limiting API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not check_rate_limit(api_name):
                return jsonify({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': f"{rate_limit_data[api_name]['period']} seconds"
                }), 429
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ---------- REQUEST HELPERS ----------
def make_api_request(url, params=None, headers=None, api_name='default', retry_count=3, backoff_factor=1.5):
    """Make API request with exponential backoff and rate limiting"""
    if not headers:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    if not check_rate_limit(api_name):
        raise Exception(f"Rate limit exceeded for {api_name}")
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            # If we got a rate limit error from the API, back off
            if response.status_code == 429:
                wait_time = backoff_factor ** attempt
                logger.warning(f"Rate limited by {api_name}, backing off for {wait_time}s")
                time.sleep(wait_time)
                continue
                
            return response
            
        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if attempt < retry_count - 1:
                wait_time = backoff_factor ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception(f"Failed after {retry_count} attempts")

@app.route('/api/coins', methods=['GET'])
@rate_limit('coingecko')
def get_coins():
    """
    Fetch top cryptocurrencies from CoinGecko API with caching
    """
    try:
        # Get optional parameters 
        page = request.args.get('page', '1')
        per_page = request.args.get('per_page', '50')
        vs_currency = request.args.get('currency', 'usd')
        order = request.args.get('order', 'market_cap_desc')
        
        # Check cache first
        cache_key = f"coingecko_top_{vs_currency}_{page}_{per_page}_{order}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # If not in cache, make API request with our helper that handles retries and backoff
        try:
            response = make_api_request(
                f"{COINGECKO_API_URL}/coins/markets",
                params={
                    "vs_currency": vs_currency,
                    "order": order,
                    "per_page": "100",  # Increased to get more coins
                    "page": page,
                    "sparkline": False,
                    "price_change_percentage": "24h"
                },
                api_name="coingecko"
            )
            
            if response.status_code != 200:
                logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                return jsonify({"error": "Failed to fetch coin data"}), 500
                
            coins = response.json()
            
            # Format the response
            formatted_coins = []
            for coin in coins:
                # Skip if any required field is missing
                if not all(key in coin for key in ["id", "symbol", "name", "current_price"]):
                    continue
                    
                formatted_coins.append({
                    "id": coin["id"],
                    "symbol": coin["symbol"].upper(),
                    "name": coin["name"],
                    "price": coin["current_price"] or 0,
                    "price_change_24h": coin["price_change_percentage_24h"] or 0,
                    "volume": coin["total_volume"] or 0,
                    "market_cap": coin["market_cap"] or 0,
                    "image": coin.get("image", ""),
                    "rank": coin.get("market_cap_rank", 999)
                })
            
            # Cache the formatted response
            set_cache(cache_key, formatted_coins)
            
            return jsonify(formatted_coins)
            
        except Exception as e:
            logger.error(f"CoinGecko API request error: {str(e)}")
            return jsonify({"error": f"Failed to fetch coin data: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Error in get_coins: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/ml_predictions', methods=['GET'])
def get_ml_predictions():
    """
    Get ML predictions for a specified cryptocurrency with caching
    """
    try:
        coin = request.args.get('coin', '')
        
        if not coin:
            return jsonify({"error": "Coin parameter is required"}), 400
        
        # Check cache first (predictions can be cached longer as they don't change often)
        cache_key = f"ml_prediction_{coin}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
            
        # Use yfinance to get historical data
        ticker = f"{coin}-USD" if "USD" not in coin else coin
        
        logger.info(f"Fetching data for {ticker}")
        
        try:
            data = yf.download(ticker, period="90d", interval="1d")
            
            # Check if data is empty or None
            if data is None or (hasattr(data, 'empty') and data.empty):
                logger.error(f"No data found for {coin}")
                return jsonify({"error": f"No data found for {coin}"}), 404
                
            # Calculate RSI manually (simpler implementation)
            try:
                # Make sure close is a Series
                close_series = data['Close']
                if not isinstance(close_series, pd.Series):
                    close_series = pd.Series(data['Close'].values)
                
                # Calculate RSI directly
                delta = close_series.diff().dropna()
                
                # Get gains and losses
                gains = delta.copy()
                gains[gains < 0] = 0
                
                losses = delta.copy()
                losses[losses > 0] = 0
                losses = -losses  # Make positive
                
                # Calculate average gains and losses
                window = 14
                avg_gain = gains.rolling(window=window).mean()
                avg_loss = losses.rolling(window=window).mean()
                
                # Avoid division by zero
                avg_loss = avg_loss.replace(0, 0.001)
                
                # Calculate RSI
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
                # Add to dataframe
                data['rsi'] = rsi
                
                logger.info(f"RSI calculation successful for {coin}")
                
            except Exception as rsi_err:
                logger.error(f"RSI calculation error: {str(rsi_err)}")
                # Create default RSI
                data['rsi'] = pd.Series(50, index=data.index)
            
            # Generate prediction using our ML utility
            prediction, confidence, reason = generate_prediction(data)
            
            # Create result with safe handling of all values
            result = {
                "symbol": coin,
                "prediction": prediction,
                "confidence": confidence,
                "reason": reason,
                "last_price": float(data['Close'].iloc[-1]),
                "timestamp": datetime.now().isoformat()
            }
            
            # Add RSI if available
            try:
                last_rsi = data['rsi'].iloc[-1]
                if not pd.isna(last_rsi):
                    result["current_rsi"] = float(last_rsi)
                else:
                    result["current_rsi"] = 50.0
            except:
                result["current_rsi"] = 50.0
            
            # Cache the prediction
            set_cache(cache_key, result)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error processing data for {coin}: {str(e)}")
            return jsonify({"error": f"Failed to process data for {coin}: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Error in ML prediction: {str(e)}")
        return jsonify({"error": f"Failed to generate prediction: {str(e)}"}), 500

@app.route('/api/search', methods=['GET'])
@rate_limit('coingecko')
def search_coins():
    """
    Search for coins by name or symbol with caching
    """
    try:
        query = request.args.get('q', '')
        
        if not query or len(query) < 2:
            return jsonify([])
        
        # Check cache first
        cache_key = f"coingecko_search_{query}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
            
        # If not in cache, make API request with our helper
        try:
            response = make_api_request(
                f"{COINGECKO_API_URL}/search",
                params={"query": query},
                api_name="coingecko"
            )
            
            if response.status_code != 200:
                logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                return jsonify({"error": "Failed to search coins"}), 500
                
            results = response.json()
            
            # Format the response to only include coins (not categories or exchanges)
            coins = results.get("coins", [])
            formatted_results = [
                {
                    "id": coin["id"],
                    "symbol": coin["symbol"].upper(),
                    "name": coin["name"],
                    "image": coin.get("large", ""),
                    "market_cap_rank": coin.get("market_cap_rank", 9999)
                }
                for coin in coins[:15]  # Limit to top 15 results
            ]
            
            # Cache the formatted results
            set_cache(cache_key, formatted_results)
                
            return jsonify(formatted_results)
            
        except Exception as e:
            logger.error(f"CoinGecko API request error: {str(e)}")
            return jsonify({"error": f"Failed to search coins: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Error in search_coins: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# ---------- DEXSCREENER API ROUTES ----------

@app.route('/api/dex/pairs/<pair_address>', methods=['GET'])
@rate_limit('dexscreener')
def get_dex_pair(pair_address):
    """
    Get DexScreener pair information
    """
    try:
        if not pair_address:
            return jsonify({"error": "Pair address is required"}), 400
        
        # Check cache first
        cache_key = f"dexscreener_pair_{pair_address}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # Request from DexScreener with retries and backoff
        try:
            response = make_api_request(
                f"{DEXSCREENER_API_URL}/pairs/{pair_address}",
                api_name="dexscreener"
            )
            
            if response.status_code != 200:
                logger.error(f"DexScreener API error: {response.status_code} - {response.text}")
                return jsonify({"error": "Failed to fetch pair data"}), 500
            
            data = response.json()
            
            # Cache the response
            set_cache(cache_key, data)
            
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"DexScreener API request error: {str(e)}")
            return jsonify({"error": f"Failed to fetch pair data: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error in get_dex_pair: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/dex/tokens/<token_address>', methods=['GET'])
@rate_limit('dexscreener')
def get_dex_token(token_address):
    """
    Get DexScreener token information across different pairs
    """
    try:
        if not token_address:
            return jsonify({"error": "Token address is required"}), 400
        
        # Check cache first
        cache_key = f"dexscreener_token_{token_address}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # Request from DexScreener with retries and backoff
        try:
            response = make_api_request(
                f"{DEXSCREENER_API_URL}/tokens/{token_address}",
                api_name="dexscreener"
            )
            
            if response.status_code != 200:
                logger.error(f"DexScreener API error: {response.status_code} - {response.text}")
                return jsonify({"error": "Failed to fetch token data"}), 500
            
            data = response.json()
            
            # Cache the response
            set_cache(cache_key, data)
            
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"DexScreener API request error: {str(e)}")
            return jsonify({"error": f"Failed to fetch token data: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error in get_dex_token: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/api/dex/search', methods=['GET'])
@rate_limit('dexscreener')
def search_dex(query):
    """
    Search for tokens on DexScreener
    """
    try:
        query = request.args.get('q', '')
        
        if not query or len(query) < 2:
            return jsonify([])
        
        # Check cache first
        cache_key = f"dexscreener_search_{query}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # Request from DexScreener with retries and backoff
        try:
            response = make_api_request(
                f"{DEXSCREENER_API_URL}/search",
                params={"query": query},
                api_name="dexscreener"
            )
            
            if response.status_code != 200:
                logger.error(f"DexScreener API error: {response.status_code} - {response.text}")
                return jsonify({"error": "Failed to search tokens"}), 500
            
            data = response.json()
            
            # Cache the response
            set_cache(cache_key, data)
            
            return jsonify(data)
            
        except Exception as e:
            logger.error(f"DexScreener API request error: {str(e)}")
            return jsonify({"error": f"Failed to search tokens: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error in search_dex: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# ---------- BACKGROUND CACHE REFRESH ----------
def background_cache_refresh():
    """Refresh popular cache entries in the background to prevent cache misses"""
    def refresh_worker():
        while True:
            try:
                logger.info("Background refresh: Updating top coins cache")
                
                # Refresh top coins in USD silently in the background
                make_api_request(
                    f"{COINGECKO_API_URL}/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "order": "market_cap_desc",
                        "per_page": "100",
                        "page": "1",
                        "sparkline": False,
                        "price_change_percentage": "24h"
                    },
                    api_name="coingecko"
                )
                
                # Sleep before next refresh
                time.sleep(45)  # Refresh slightly before cache expires
                
            except Exception as e:
                logger.error(f"Error in background refresh: {str(e)}")
                time.sleep(60)  # Wait a bit before retrying after error
    
    # Start the background thread
    refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
    refresh_thread.start()

# Start background refresh
background_cache_refresh()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)