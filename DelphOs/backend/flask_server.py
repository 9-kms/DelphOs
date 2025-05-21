from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from functools import wraps

# Import our advanced technical indicators
from advanced_indicators import get_technical_analysis
from simple_rsi import calculate_rsi
from link_analyzer import analyze_link
from general_analyzer import analyze_any_coin

# Import multi-signal analysis modules
from multi_signal_routes import add_multi_signal_routes

# Import database functionality
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db

# Import ML prediction tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    # Try to import the enhanced prediction model first
    from enhanced_ml import enhanced_prediction as generate_prediction
    # Import the news scraper module
    from news_scraper import get_news_sentiment_for_symbol
    logger = logging.getLogger(__name__)
    logger.info("Using enhanced ML prediction utilities with multiple indicators")
except ImportError:
    try:
        # Try the fixed version next
        from ml_utils_fixed import generate_prediction
        logger = logging.getLogger(__name__)
        logger.info("Using fixed ML prediction utilities")
    except ImportError:
        # Fall back to original if needed
        from ml_utils import generate_prediction
        logger = logging.getLogger(__name__)
        logger.warning("Using original ML prediction utilities")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS specifically for API routes

# Application constants
DISCLAIMER_TEXT = "NOT FINANCIAL ADVICE: This dashboard provides cryptocurrency analysis and predictions based on historical data and technical indicators. All predictions are speculative and should not be considered financial advice. The creators of this tool are not registered investment advisors. Always do your own research before making investment decisions."

# Constants for AI-backed discovery
BULLISH_RSI_THRESHOLD = 30        # RSI below this is considered bullish (oversold)
BULLISH_TREND_THRESHOLD = 5.0     # 5-day trend percentage increase considered bullish
BEARISH_RSI_THRESHOLD = 70        # RSI above this is considered bearish (overbought)
BEARISH_TREND_THRESHOLD = -5.0    # 5-day trend percentage decrease considered bearish

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
            # Check if custom TTL is set for this key
            duration = None
            if 'ttl' in cache and cache_key in cache['ttl']:
                duration = cache['ttl'][cache_key]
            
            # If no custom TTL, use the standard cache duration
            if duration is None:
                cache_type = cache_key.split('_')[0]
                duration = CACHE_DURATION.get(cache_type, 60)
            
            if datetime.now() - cache['timestamps'][cache_key] < timedelta(seconds=duration):
                logger.debug(f"Cache hit for {cache_key}")
                return cache['data'][cache_key]
            else:
                logger.debug(f"Cache expired for {cache_key}")
    return None

def set_cache(cache_key, data, ttl=None):
    """Store data in cache with timestamp and optional TTL in seconds"""
    with cache_lock:
        cache['data'][cache_key] = data
        cache['timestamps'][cache_key] = datetime.now()
        
        # Store custom TTL if provided
        if ttl is not None:
            if 'ttl' not in cache:
                cache['ttl'] = {}
            cache['ttl'][cache_key] = ttl
            
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
    },
    'api_coins': {            # Rate limit for coins API
        'calls': {},          # Dict to track calls by IP
        'limit': 100,         # 100 calls per minute
        'period': 60          # 1 minute
    },
    'api_ml_predictions': {   # ML predictions are more resource-intensive
        'calls': {},          # Dict to track calls by IP
        'limit': 30,          # 30 calls per minute
        'period': 60          # 1 minute
    },
    'api_prophecy': {         # Prophecy endpoint for external integrations
        'calls': {},          # Dict to track calls by IP
        'limit': 30,          # 30 calls per minute
        'period': 60          # 1 minute
    },
    'api_charts': {           # Charts endpoint for historical data
        'calls': {},          # Dict to track calls by IP
        'limit': 50,          # 50 calls per minute
        'period': 60          # 1 minute
    },
    'api_backtest': {         # Backtesting feature is resource-intensive
        'calls': {},          # Dict to track calls by IP
        'limit': 10,          # 10 calls per minute
        'period': 60          # 1 minute
    },
    'api_news': {             # News sentiment scraping is resource-intensive
        'calls': {},          # Dict to track calls by IP
        'limit': 10,          # 10 calls per minute
        'period': 60          # 1 minute
    },
    'api_combined': {         # Combined analysis endpoint
        'calls': {},          # Dict to track calls by IP
        'limit': 15,          # 15 calls per minute
        'period': 60          # 1 minute
    }
}

rate_limit_lock = threading.Lock()

def check_rate_limit(api_name, ip_address=None):
    """Check if we've hit the rate limit for an API"""
    now = time.time()
    with rate_limit_lock:
        # Special handling for our API endpoints that require IP tracking
        if api_name.startswith('api_'):
            ip = ip_address or '127.0.0.1'  # Use local IP if none provided
            
            # Initialize if this API doesn't use a dict for tracking yet
            if not isinstance(rate_limit_data[api_name]['calls'], dict):
                rate_limit_data[api_name]['calls'] = {}
                
            # Initialize if this IP doesn't exist yet
            if ip not in rate_limit_data[api_name]['calls']:
                rate_limit_data[api_name]['calls'][ip] = []
            
            # Remove expired timestamps
            rate_limit_data[api_name]['calls'][ip] = [
                timestamp for timestamp in rate_limit_data[api_name]['calls'][ip]
                if timestamp > now - rate_limit_data[api_name]['period']
            ]
            
            # Check if this IP is over the limit
            if len(rate_limit_data[api_name]['calls'][ip]) >= rate_limit_data[api_name]['limit']:
                logger.warning(f"Rate limit exceeded for {api_name} from IP {ip}")
                return False
            
            # Add this call
            rate_limit_data[api_name]['calls'][ip].append(now)
            return True
        else:
            # Original implementation for non-IP tracked APIs
            if isinstance(rate_limit_data[api_name]['calls'], dict):
                # If we somehow got here with a dict-type calls tracker
                return True  # Skip for safety
            
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
            # For our API endpoints that need IP tracking
            if api_name.startswith('api_'):
                # Get client IP address
                ip_address = request.remote_addr
                if not check_rate_limit(api_name, ip_address):
                    return jsonify({
                        'error': 'Rate limit exceeded. Please try again later.',
                        'retry_after': f"{rate_limit_data[api_name]['period']} seconds",
                        'limit': rate_limit_data[api_name]['limit'],
                        'per': f"{rate_limit_data[api_name]['period'] // 60} minutes"
                    }), 429
            else:
                # For external APIs that don't need IP tracking
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
        "disclaimer": DISCLAIMER_TEXT
    })

@app.route('/api/info')
def get_info():
    """
    Get general information including disclaimer
    """
    return jsonify({
        'name': 'DelphOs Crypto Prediction Dashboard',
        'version': '1.1.0',
        'disclaimer': DISCLAIMER_TEXT,
        'api_limits': {
            'coins': f"{rate_limit_data['api_coins']['limit']} requests per {rate_limit_data['api_coins']['period'] // 60} minutes",
            'predictions': f"{rate_limit_data['api_ml_predictions']['limit']} requests per {rate_limit_data['api_ml_predictions']['period'] // 60} minutes",
            'prophecy': f"{rate_limit_data['api_prophecy']['limit']} requests per {rate_limit_data['api_prophecy']['period'] // 60} minutes" 
        },
        'cache_duration': {
            'coin_data': f"{CACHE_DURATION['coingecko_top']} seconds",
            'predictions': f"{CACHE_DURATION['ml_prediction']} seconds",
            'dexscreener': f"{CACHE_DURATION['dexscreener']} seconds" 
        },
        'timestamp': datetime.now().isoformat()
    })

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
                
            # Simplified, more reliable approach for calculating RSI
            try:
                # Extract close prices as simple list of values
                close_values = []
                
                if isinstance(data['Close'], pd.Series):
                    close_values = data['Close'].values
                elif hasattr(data['Close'], 'values'):
                    close_values = data['Close'].values
                else:
                    # Fallback for unknown format
                    close_values = [float(x) for x in data['Close']]
                
                # Create a clean pandas Series with these values
                clean_prices = pd.Series(close_values)
                logger.info(f"Extracted {len(clean_prices)} price points for {coin}")
                
                # Simple manual RSI calculation (most reliable approach)
                # Step 1: Calculate price changes
                delta = clean_prices.diff().dropna()
                
                # Step 2: Split into gains and losses
                gains = delta.copy()
                gains[gains < 0] = 0
                
                losses = delta.copy()
                losses[losses > 0] = 0
                losses = losses.abs()  # Make positive
                
                # Step 3: Calculate SMA of gains and losses
                window = 14  # Standard RSI period
                avg_gain = gains.rolling(window=window).mean()
                avg_loss = losses.rolling(window=window).mean()
                
                # Step 4: Calculate RS and RSI
                # Handle division by zero
                avg_loss = avg_loss.replace(0, 0.001)  # Safer approach without apply
                rs = avg_gain / avg_loss
                rsi_values = 100 - (100 / (1 + rs))
                
                # Add to original dataframe with matching index
                # Handle different array types safely
                if hasattr(rsi_values, 'values'):
                    rsi_vals = rsi_values.values
                else:
                    rsi_vals = rsi_values
                    
                # Make sure we have the right length
                if len(data.index) >= len(rsi_vals):
                    data['rsi'] = pd.Series(rsi_vals, index=data.index[-len(rsi_vals):])
                else:
                    # Handle case where we have more RSI values than data points
                    data['rsi'] = pd.Series(rsi_vals[-len(data.index):], index=data.index)
                
                # Check if we have valid RSI data
                if data['rsi'].isna().all():
                    logger.warning(f"RSI calculation failed for {coin}, using historical price action instead")
                    
                    # For LINK specifically, use a price-based approach since RSI fails
                    if coin.upper() == 'LINK':
                        # Calculate recent price action - 7 day trend
                        price_change_7d = (data['Close'].iloc[-1] / data['Close'].iloc[-8] - 1) * 100
                        if price_change_7d > 5:
                            data['rsi'] = pd.Series(70, index=data.index)  # Trending up - higher RSI
                        elif price_change_7d < -5:
                            data['rsi'] = pd.Series(30, index=data.index)  # Trending down - lower RSI
                        else:
                            data['rsi'] = pd.Series(45, index=data.index)  # Slight bias below neutral
                    else:
                        # For other coins with RSI issues, use a neutral value
                        data['rsi'] = pd.Series(50, index=data.index)
                        
                    logger.info(f"Using price-based RSI substitute for {coin}")
                else:
                    logger.info(f"RSI calculation successful for {coin}")
                    
            except Exception as e:
                logger.error(f"Error calculating RSI: {str(e)}")
                # Create neutral RSI values as fallback
                data['rsi'] = pd.Series(50, index=data.index)
            
            # Get comprehensive technical analysis that works with any data structure
            try:
                # Use our general analyzer for all coins for consistency
                tech_analysis = analyze_any_coin(data)
                logger.info(f"Generated robust technical analysis for {coin}")
                
                # Run ML model with proper error handling
                try:
                    ml_prediction, ml_confidence, ml_reason = generate_prediction(data)
                except Exception as ml_error:
                    logger.error(f"ML prediction error: {str(ml_error)}")
                    ml_prediction = "Neutral"
                    ml_confidence = 50
                    ml_reason = "Error in prediction algorithm"
                
                # Use the more detailed technical analysis
                result = {
                    "symbol": coin,
                    "prediction": tech_analysis["overall_signal"],  # Use the technical analysis result
                    "confidence": tech_analysis["confidence"],
                    "reason": tech_analysis["explanation"],
                    "last_price": float(data['Close'].iloc[-1]),
                    "timestamp": datetime.now().isoformat(),
                    
                    # Add advanced indicators
                    "current_rsi": float(tech_analysis["rsi"]),
                    "stochastic_rsi": float(tech_analysis["srsi_k"]),
                    "macd_signal": "Bullish" if tech_analysis["macd"] > tech_analysis["macd_signal"] else "Bearish",
                    "ema_position": tech_analysis["ema_status"]["position"],
                    
                    # Include ML model result for comparison
                    "ml_prediction": ml_prediction,
                    "ml_confidence": ml_confidence,
                    "ml_reason": ml_reason
                }
                
                logger.info(f"Enhanced prediction for {coin}: {result['prediction']} ({result['confidence']}%)")
                
            except Exception as e:
                logger.error(f"Error generating advanced analysis: {str(e)}")
                
                # Fall back to basic ML prediction
                prediction, confidence, reason = generate_prediction(data)
                
                result = {
                    "symbol": coin,
                    "prediction": prediction,
                    "confidence": confidence,
                    "reason": reason,
                    "last_price": float(data['Close'].iloc[-1]),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add RSI if available and valid
                try:
                    if 'rsi' in data.columns and not pd.isna(data['rsi'].iloc[-1]):
                        result["current_rsi"] = float(data['rsi'].iloc[-1])
                    else:
                        result["current_rsi"] = 50.0
                except Exception as e:
                    logger.warning(f"Could not include RSI in response: {str(e)}")
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
        # Get query parameter - support both 'q' and 'query'
        query = request.args.get('query', request.args.get('q', ''))
        
        # Check for special easter egg: 666
        if query == '666':
            logger.info("666 easter egg triggered in search!")
            # Use the demonic mode API
            return demonic_mode()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        # Check cache first
        cache_key = f"coingecko_search_{query}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
            
        # If we already have top coins data cached, filter it first as a fallback
        top_coins_cache_key = "coingecko_top_usd_1_50_market_cap_desc"
        top_coins = get_cached_data(top_coins_cache_key)
        
        if top_coins:
            filtered_coins = []
            query_lower = query.lower()
            
            for coin in top_coins:
                if (query_lower in coin.get('id', '').lower() or 
                    query_lower in coin.get('symbol', '').lower() or 
                    query_lower in coin.get('name', '').lower()):
                    filtered_coins.append({
                        "id": coin["id"],
                        "symbol": coin["symbol"].upper(),
                        "name": coin["name"],
                        "image": coin.get("image", ""),
                        "market_cap_rank": coin.get("rank", 9999)
                    })
            
            if filtered_coins:
                # Cache the filtered results
                set_cache(cache_key, filtered_coins)
                return jsonify(filtered_coins)
        
        # If not in cache, make API request with our helper
        try:
            response = make_api_request(
                f"{COINGECKO_API_URL}/search",
                params={"query": query},
                api_name="coingecko"
            )
            
            if response.status_code != 200:
                logger.error(f"CoinGecko API error: {response.status_code} - {response.text}")
                return jsonify([])  # Return empty array instead of error for better UI experience
                
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
            return jsonify([])  # Return empty array instead of error
    
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

@app.route('/api/dex/search/<query>', methods=['GET'])
@rate_limit('dexscreener')
def search_dex(query):
    """
    Search for tokens on DexScreener
    """
    try:
        if not query or len(query) < 2:
            return jsonify({"error": "Search query must be at least 2 characters"}), 400
        
        # Check cache first
        cache_key = f"dexscreener_search_{query}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # Request from DexScreener with retries and backoff
        try:
            response = make_api_request(
                f"{DEXSCREENER_API_URL}/search",
                params={"q": query},
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

@app.route('/api/dex/popular', methods=['GET'])
@rate_limit('dexscreener')
def get_popular_dex_tokens():
    """
    Get popular tokens from DexScreener including Cloudy Heart and other established tokens
    """
    try:
        # Check cache first to reduce API calls
        cache_key = "dexscreener_popular_tokens"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # Popular token addresses to fetch, including Cloudy Heart
        popular_tokens = [
            # Cloudy Heart (CLOUDY)
            "0x0d111e482712f9405e2304d59b7f302e50d15fea", 
            # Pepe (PEPE)
            "0x6982508145454ce325ddbe47a25d4ec3d2311933",
            # Shiba Inu (SHIB)
            "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce",
            # Dogwifhat (WIF)
            "0xD1D4a9164a7df24495d49C6aCd1F95c4F20B715E"
        ]
        
        # For tokens we know might have special data requirements or not be available via normal APIs
        special_tokens = [
            {
                "symbol": "CLOUDY",
                "name": "Cloudy Heart",
                "address": "0x0d111e482712f9405e2304d59b7f302e50d15fea",
                "chain": "ethereum",
                "logo": "https://assets.coingecko.com/coins/images/33258/small/cloudy.png",
                "description": "Cloudy Heart (CLOUDY) is a community-driven token focused on building a sustainable ecosystem.",
                "is_special": True
            }
        ]
        
        all_token_data = {
            "pairs": [],
            "special_tokens": special_tokens
        }
        
        # Fetch each token's data from DexScreener
        for token_address in popular_tokens:
            try:
                logger.info(f"Fetching DexScreener data for token: {token_address}")
                response = make_api_request(
                    f"{DEXSCREENER_API_URL}/tokens/{token_address}",
                    api_name="dexscreener"
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Add pairs to the main result
                    if "pairs" in token_data and token_data["pairs"]:
                        # Clean and enhance pair data
                        for pair in token_data["pairs"]:
                            # Add source information
                            pair["source"] = "dexscreener"
                            
                            # Ensure we have a token symbol
                            if "baseToken" in pair and "symbol" in pair["baseToken"]:
                                pair["symbol"] = pair["baseToken"]["symbol"]
                                
                            # Add special handling for CloudyHeart
                            if pair.get("symbol") == "CLOUDY" or (
                                "baseToken" in pair and 
                                pair["baseToken"].get("address") == "0x0d111e482712f9405e2304d59b7f302e50d15fea"
                            ):
                                pair["is_cloudy_heart"] = True
                                
                        all_token_data["pairs"].extend(token_data["pairs"])
                        logger.info(f"Added {len(token_data['pairs'])} pairs for token {token_address}")
                
                # Sleep briefly to avoid hitting rate limits
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error fetching token {token_address}: {str(e)}")
                # Continue with other tokens even if one fails
                continue
        
        # Format the results to be consistent with our API
        formatted_results = {
            "tokens": [],
            "count": 0,
            "timestamp": datetime.now().isoformat()
        }

        # Combine DexScreener pair data with special tokens
        seen_symbols = set()
        
        # Add special tokens first (they take priority)
        for token in special_tokens:
            formatted_token = {
                "symbol": token["symbol"],
                "name": token["name"],
                "address": token["address"],
                "chain": token["chain"],
                "logo": token.get("logo", ""),
                "price": None,  # Will be filled from pair data if available
                "price_change_24h": None,
                "market_cap": None,
                "volume_24h": None,
                "source": "special",
                "description": token.get("description", ""),
                "is_special": True
            }
            
            formatted_results["tokens"].append(formatted_token)
            seen_symbols.add(token["symbol"])
        
        # Process pair data from DexScreener
        for pair in all_token_data["pairs"]:
            if "baseToken" not in pair:
                continue
                
            base_token = pair["baseToken"]
            symbol = base_token.get("symbol", "").upper()
            
            # Skip if we've already added this token
            if symbol in seen_symbols:
                # For special tokens like CloudyHeart, update price information
                for token in formatted_results["tokens"]:
                    if token["symbol"] == symbol and token.get("is_special"):
                        # Update with latest price data
                        token["price"] = pair.get("priceUsd")
                        token["price_change_24h"] = pair.get("priceChange", {}).get("h24")
                        token["volume_24h"] = pair.get("volume", {}).get("h24")
                        # Add detail link
                        token["dexscreener_url"] = f"https://dexscreener.com/{pair.get('chainId')}/{pair.get('pairAddress')}"
                continue
            
            # Create a new token entry
            formatted_token = {
                "symbol": symbol,
                "name": base_token.get("name", symbol),
                "address": base_token.get("address"),
                "chain": pair.get("chainId", "ethereum"),
                "price": pair.get("priceUsd"),
                "price_change_24h": pair.get("priceChange", {}).get("h24"),
                "volume_24h": pair.get("volume", {}).get("h24"),
                "liquidity": pair.get("liquidity", {}).get("usd"),
                "source": "dexscreener",
                "dexscreener_url": f"https://dexscreener.com/{pair.get('chainId')}/{pair.get('pairAddress')}"
            }
            
            formatted_results["tokens"].append(formatted_token)
            seen_symbols.add(symbol)
        
        # Update count
        formatted_results["count"] = len(formatted_results["tokens"])
        
        # Cache the results
        set_cache(cache_key, formatted_results, ttl=60*10)  # Cache for 10 minutes
        
        return jsonify(formatted_results)
        
    except Exception as e:
        logger.error(f"Error fetching popular DEX tokens: {str(e)}")
        return jsonify({"error": f"Failed to fetch popular tokens: {str(e)}"}), 500

# ---------- BACKGROUND CACHE REFRESH ----------
def background_cache_refresh():
    """Refresh popular cache entries in the background to prevent cache misses"""
    try:
        # Refresh top coins every 5 minutes
        if datetime.now().minute % 5 == 0:
            logger.info("Background refresh: Updating top coins cache")
            make_api_request(
                f"{COINGECKO_API_URL}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": "100",  # Get 100 coins in background refresh too
                    "page": 1,
                    "sparkline": False,
                    "price_change_percentage": "24h"
                },
                api_name="coingecko"
            )
    except Exception as e:
        logger.error(f"Error in background cache refresh: {str(e)}")

# ---------- NEW ENDPOINTS ----------

@app.route('/api/discover/<mode>', methods=['GET'])
@rate_limit('api_coins')
def discover_coins(mode):
    """
    AI-backed coin discovery - find coins with specific characteristics
    Mode can be 'bullish' or 'bearish'
    """
    try:
        if mode not in ['bullish', 'bearish']:
            return jsonify({"error": "Mode must be 'bullish' or 'bearish'"}), 400
            
        # First, get cached coin data
        cache_key = 'coingecko_top_usd_1_50_market_cap_desc'
        cached_data = get_cached_data(cache_key)
        
        if not cached_data:
            return jsonify({"error": "No cached coin data available"}), 500
            
        discovered_coins = []
        
        # For each coin in our cache, check if we have a prediction
        for coin in cached_data:
            symbol = coin['symbol']
            prediction_cache_key = f"ml_prediction_{symbol}"
            prediction_data = get_cached_data(prediction_cache_key)
            
            if prediction_data:
                # Only keep coins with predictions matching our mode
                if mode == 'bullish' and prediction_data.get('prediction') == 'Bullish':
                    # Check for bullish indicators (low RSI or strong uptrend)
                    rsi = prediction_data.get('current_rsi', 50)
                    
                    if rsi < BULLISH_RSI_THRESHOLD:
                        # RSI indicates potential oversold (bullish)
                        discovered_coins.append({
                            'symbol': symbol,
                            'name': coin.get('name', symbol),
                            'price': coin.get('price', prediction_data.get('last_price', 0)),
                            'confidence': prediction_data.get('confidence', 0),
                            'rsi': rsi,
                            'reason': f"RSI ({rsi:.1f}) below {BULLISH_RSI_THRESHOLD} indicates oversold conditions"
                        })
                        
                elif mode == 'bearish' and prediction_data.get('prediction') == 'Bearish':
                    # Check for bearish indicators (high RSI)
                    rsi = prediction_data.get('current_rsi', 50)
                    
                    if rsi > BEARISH_RSI_THRESHOLD:
                        # RSI indicates potential overbought (bearish)
                        discovered_coins.append({
                            'symbol': symbol,
                            'name': coin.get('name', symbol),
                            'price': coin.get('price', prediction_data.get('last_price', 0)),
                            'confidence': prediction_data.get('confidence', 0),
                            'rsi': rsi,
                            'reason': f"RSI ({rsi:.1f}) above {BEARISH_RSI_THRESHOLD} indicates overbought conditions"
                        })
        
        # Sort by confidence level (descending)
        discovered_coins = sorted(discovered_coins, key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Return top 5 results
        result = {
            'mode': mode,
            'count': len(discovered_coins[:5]),
            'coins': discovered_coins[:5],
            'disclaimer': DISCLAIMER_TEXT,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in discover_coins: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/prophecy/<symbol>', methods=['GET'])
@rate_limit('api_prophecy')
def get_prophecy(symbol):
    """
    Get cleaned prediction data for a specific cryptocurrency (better for 3rd party integration)
    """
    try:
        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400
            
        symbol = symbol.upper()
        
        # Check cache first - we can reuse the ML prediction cache
        cache_key = f"ml_prediction_{symbol}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            # Format the data to be cleaner for external use
            prophecy = {
                "symbol": symbol,
                "prediction": cached_data.get("prediction"),
                "confidence": cached_data.get("confidence"),
                "current_rsi": cached_data.get("current_rsi"),
                "price": cached_data.get("last_price"),
                "reason": cached_data.get("reason"),
                "timestamp": cached_data.get("timestamp"),
                "disclaimer": DISCLAIMER_TEXT
            }
            return jsonify(prophecy)
        
        # If not cached, fetch the data using Yahoo Finance
        try:
            # Get historical data
            data = yf.download(f"{symbol}-USD", period="90d")
            
            if data.empty or len(data) < 14:
                return jsonify({"error": f"Insufficient data for {symbol}"}), 400
                
            # Calculate RSI
            try:
                data['rsi'] = calculate_rsi(data['Close'])
            except Exception as e:
                logger.error(f"Error calculating RSI: {str(e)}")
                data['rsi'] = pd.Series(50, index=data.index)
            
            # Get technical analysis
            tech_analysis = analyze_any_coin(data)
            
            # Create prophecy response
            prophecy = {
                "symbol": symbol,
                "prediction": tech_analysis["overall_signal"],
                "confidence": tech_analysis["confidence"],
                "current_rsi": float(tech_analysis["rsi"]),
                "price": float(data['Close'].iloc[-1]),
                "reason": tech_analysis["explanation"],
                "timestamp": datetime.now().isoformat(),
                "disclaimer": DISCLAIMER_TEXT
            }
            
            # Cache the prophecy
            set_cache(cache_key, prophecy)
            
            return jsonify(prophecy)
            
        except Exception as e:
            logger.error(f"Error generating prophecy: {str(e)}")
            return jsonify({"error": f"Failed to generate prophecy: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error in get_prophecy: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ask_oracle', methods=['POST'])
@rate_limit('api_ml_predictions')
def ask_oracle():
    """
    Future LLM integration endpoint (currently returns mock data)
    """
    try:
        # Check if the request has JSON data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
            
        # Get the question from the request
        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({"error": "Missing 'question' parameter"}), 400
            
        # For now, return a predefined response
        # In the future, this would call an LLM API
        responses = [
            "Based on current trends, ETH and BTC are strong candidates for observation.",
            "The RSI indicators for LINK and SOL suggest potential upward movement.",
            "Consider analyzing volume patterns across major DeFi tokens in the next cycle.",
            "Technical indicators point to short-term consolidation across the market.",
            "The market is showing early signs of recovery based on several key metrics."
        ]
        
        import random
        response = random.choice(responses)
        
        return jsonify({
            "question": question,
            "answer": response,
            "disclaimer": DISCLAIMER_TEXT,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in ask_oracle: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Import and integrate the new features
try:
    from flask_server_charts import add_chart_routes
    # Add the chart routes to the Flask app
    add_chart_routes(app, rate_limit, get_cached_data, set_cache)
    logger.info("Chart routes added successfully")
except ImportError as e:
    logger.error(f"Failed to import chart routes: {str(e)}")

try:
    from backtesting import add_backtest_routes
    # Add the backtesting routes to the Flask app
    add_backtest_routes(app, rate_limit)
    logger.info("Backtesting routes added successfully")
except ImportError as e:
    logger.error(f"Failed to import backtesting routes: {str(e)}")

try:
    from easter_eggs import add_easter_egg_routes
    # Add the easter egg routes to the Flask app
    add_easter_egg_routes(app, rate_limit)
    logger.info("Easter egg features added successfully")
except ImportError as e:
    logger.error(f"Failed to import easter egg features: {str(e)}")

try:
    from news_routes import add_news_routes
    # Add the news sentiment routes to the Flask app
    add_news_routes(app, rate_limit, get_cached_data, set_cache)
    logger.info("News sentiment routes added successfully")
except ImportError as e:
    logger.error(f"Failed to import news sentiment routes: {str(e)}")

# Add route for currency selection
@app.route('/api/currencies', methods=['GET'])
def get_currencies():
    """
    Get available currencies for price conversion
    """
    currencies = {
        'fiat': [
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
            {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥'}
        ],
        'crypto': [
            {'code': 'BTC', 'name': 'Bitcoin', 'symbol': '₿'},
            {'code': 'ETH', 'name': 'Ethereum', 'symbol': 'Ξ'}
        ]
    }
    return jsonify(currencies)

# Admin routes
@app.route('/api/admin/refresh', methods=['GET'])
@rate_limit('api_coins')
def admin_refresh():
    """
    Manually refresh the coin data cache
    """
    try:
        # Force refresh of coin data
        cache_key = 'coingecko_top_usd_1_50_market_cap_desc'
        
        # Remove from cache to force refresh
        with cache_lock:
            if cache_key in cache['data']:
                del cache['data'][cache_key]
            if cache_key in cache['timestamps']:
                del cache['timestamps'][cache_key]
                
        # Make the API request to refresh the data
        response = make_api_request(
            f"{COINGECKO_API_URL}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": "100",
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h"
            },
            api_name="coingecko"
        )
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": "Cache refreshed successfully"})
        else:
            return jsonify({"success": False, "error": f"API returned {response.status_code}"})
    except Exception as e:
        logger.error(f"Error refreshing cache: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Debug endpoint for API limits
@app.route('/api/admin/limits', methods=['GET'])
def api_limits():
    """
    View current API usage and rate limits
    """
    try:
        limits = {}
        for api_name, data in rate_limit_data.items():
            if isinstance(data['calls'], dict):
                # For IP-tracked APIs, count total calls
                total_calls = sum(len(calls) for calls in data['calls'].values())
                limits[api_name] = {
                    'calls': total_calls,
                    'limit': data['limit'],
                    'period': data['period'],
                    'reset_in': f"{data['period']} seconds"
                }
            else:
                # For non-IP-tracked APIs
                now = time.time()
                active_calls = [t for t in data['calls'] if t > now - data['period']]
                limits[api_name] = {
                    'calls': len(active_calls),
                    'limit': data['limit'],
                    'period': data['period'],
                    'reset_in': f"{data['period']} seconds"
                }
        
        return jsonify(limits)
    except Exception as e:
        logger.error(f"Error getting API limits: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
# Add sentiment indicator endpoint
@app.route('/api/sentiment/<symbol>', methods=['GET'])
@rate_limit('api_ml_predictions')
def get_sentiment(symbol):
    """
    Get sentiment analysis for a cryptocurrency
    Currently uses a simplified model based on recent price/volume data
    """
    try:
        # Validate symbol
        if not symbol:
            return jsonify({"error": "Symbol is required"}), 400
            
        symbol = symbol.upper()
        
        # Check cache
        cache_key = f"sentiment_{symbol}"
        cached_data = get_cached_data(cache_key)
        
        if cached_data:
            return jsonify(cached_data)
        
        # Fetch data from Yahoo Finance
        ticker = f"{symbol}-USD" if "USD" not in symbol else symbol
        
        data = yf.download(ticker, period="30d")
        
        if data.empty or len(data) < 7:
            return jsonify({"error": f"Insufficient data for {symbol}"}), 400
        
        # Handle multi-dimensional data - this happens sometimes with yfinance data
        for col in data.columns:
            if hasattr(data[col], 'ndim') and data[col].ndim > 1:
                data[col] = data[col].iloc[:, 0]
        
        # Calculate simple sentiment metrics
        try:
            # 1. Price trend (last 7 days)
            price_change = (float(data['Close'].iloc[-1]) / float(data['Close'].iloc[-7]) - 1) * 100
            
            # 2. Volume trend
            if 'Volume' in data.columns and not pd.isna(data['Volume'].iloc[-1]) and data['Volume'].iloc[-1] > 0:
                recent_volumes = data['Volume'].iloc[-7:]
                if not recent_volumes.isna().all() and not all(recent_volumes == 0):
                    mean_volume = recent_volumes.replace(0, np.nan).mean()
                    if not pd.isna(mean_volume) and mean_volume > 0:
                        volume_change = (float(data['Volume'].iloc[-1]) / float(mean_volume) - 1) * 100
                    else:
                        volume_change = 0
                else:
                    volume_change = 0
            else:
                volume_change = 0
                
            # 3. Volatility (standard deviation of daily returns)
            returns = data['Close'].pct_change().dropna()
            if not returns.empty:
                volatility = float(returns.std() * 100)
            else:
                volatility = 10  # Default value if we can't calculate
            
            # Generate sentiment score (-100 to 100)
            price_factor = min(max(price_change * 2, -50), 50)  # -50 to 50 based on price change
            volume_factor = min(max(volume_change * 0.5, -25), 25)  # -25 to 25 based on volume change
            volatility_factor = min(max((20 - volatility) * 1.25, -25), 25)  # Negative for high volatility
            
            sentiment_score = price_factor + volume_factor + volatility_factor
            
            # Determine sentiment level
            if sentiment_score > 60:
                sentiment = "Very Bullish"
            elif sentiment_score > 20:
                sentiment = "Bullish"
            elif sentiment_score > -20:
                sentiment = "Neutral"
            elif sentiment_score > -60:
                sentiment = "Bearish"
            else:
                sentiment = "Very Bearish"
                
            # Construct response
            result = {
                "symbol": symbol,
                "sentiment": sentiment,
                "score": round(sentiment_score, 2),
                "factors": {
                    "price_trend": round(price_change, 2),
                    "volume_trend": round(volume_change, 2),
                    "volatility": round(volatility, 2)
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            set_cache(cache_key, result)
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Error calculating sentiment metrics: {str(e)}")
            return jsonify({
                "symbol": symbol,
                "sentiment": "Neutral",
                "score": 0,
                "factors": {
                    "price_trend": 0,
                    "volume_trend": 0,
                    "volatility": 0
                },
                "error": f"Error calculating sentiment: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

# We already have a prophecy endpoint defined above

# Add multi-signal analysis routes
try:
    # Pass the rate_limit decorator to the multi-signal routes
    add_multi_signal_routes(app, rate_limit)
    logger.info("Successfully added multi-signal analysis routes")
except Exception as e:
    logger.error(f"Error adding multi-signal routes: {str(e)}")

if __name__ == '__main__':
    # Start background thread for cache refreshing
    import threading
    import time
    
    def refresh_worker():
        while True:
            try:
                background_cache_refresh()
            except Exception as e:
                logger.error(f"Error in refresh worker: {str(e)}")
            time.sleep(60)  # Check every minute
    
    refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
    refresh_thread.start()
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5001, debug=True)
