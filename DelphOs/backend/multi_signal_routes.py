"""
Flask routes for multi-signal analysis and scenario testing
"""

import logging
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from multi_signal_analyzer import MultiSignalAnalyzer

# Setup logging
logger = logging.getLogger(__name__)

# Create analyzer instance
multi_signal_analyzer = MultiSignalAnalyzer()

# Cache for historical price data
PRICE_CACHE = {}
CACHE_TTL = 1800  # 30 minutes

def get_cached_price_data(symbol, period='1y', interval='1d'):
    """Get price data from cache if not expired"""
    cache_key = f"price_{symbol}_{period}_{interval}"
    if cache_key in PRICE_CACHE:
        timestamp, data = PRICE_CACHE[cache_key]
        if datetime.now().timestamp() - timestamp < CACHE_TTL:
            return data
    return None

def set_price_cache(symbol, period, interval, data):
    """Store price data in cache with timestamp"""
    cache_key = f"price_{symbol}_{period}_{interval}"
    PRICE_CACHE[cache_key] = (datetime.now().timestamp(), data)

def fetch_historical_data(symbol, period='1y', interval='1d'):
    """
    Fetch historical price data for analysis
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC-USD')
        period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max')
        interval: Data interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
        
    Returns:
        DataFrame with historical price data
    """
    try:
        # Check cache first
        cached_data = get_cached_price_data(symbol, period, interval)
        if cached_data is not None:
            return cached_data
            
        # Format symbol for yfinance
        if not symbol.endswith('-USD'):
            yf_symbol = f"{symbol}-USD"
        else:
            yf_symbol = symbol
            
        # Fetch data using yfinance
        df = yf.download(
            tickers=yf_symbol,
            period=period,
            interval=interval,
            progress=False,
            rounding=True
        )
        
        # Process data
        if df is not None and not df.empty:
            # Make sure the index is datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
                
            # Reset index to make Date a column
            df = df.reset_index()
            df = df.rename(columns={'index': 'Date', 'Adj Close': 'AdjClose'})
            
            # Make sure we have all required columns
            required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"Missing required columns for {symbol}. Available: {df.columns}")
                return None
                
            # Cache the data
            set_price_cache(symbol, period, interval, df)
            return df
        return None
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return None

def add_multi_signal_routes(app, rate_limit_decorator):
    """
    Add multi-signal analysis routes to Flask app
    """
    
    @app.route('/api/multi-signal/<symbol>', methods=['GET'])
    @rate_limit_decorator('multi_signal')
    def get_multi_signal_analysis(symbol):
        """
        Get comprehensive multi-signal analysis for a cryptocurrency
        
        Parameters:
        - timeframe: 1h, 1d, 1w (default: 1d) - Analysis timeframe
        """
        try:
            # Extract query parameters
            timeframe = request.args.get('timeframe', '1d')
            
            # Map timeframe to yfinance parameters
            if timeframe == '1h':
                period, interval = '7d', '1h'
            elif timeframe == '1w':
                period, interval = '6mo', '1d'
            else:  # 1d (default)
                period, interval = '1y', '1d'
                
            # Fetch historical price data
            df = fetch_historical_data(symbol, period, interval)
            
            if df is None or df.empty:
                return jsonify({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'prediction': 'Neutral',
                    'confidence': 50,
                    'explanation': 'Insufficient historical data for analysis',
                    'error': 'No price data available'
                }), 404
                
            # Run multi-signal analysis
            result = multi_signal_analyzer.analyze_all_signals(symbol, df, timeframe)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in multi-signal analysis for {symbol}: {str(e)}")
            # Set a default timeframe value in case of error
            default_timeframe = '1d'
            timeframe_val = timeframe if 'timeframe' in locals() else default_timeframe
            
            return jsonify({
                'symbol': symbol,
                'timeframe': timeframe_val,
                'prediction': 'Neutral',
                'confidence': 50,
                'explanation': f"Error in analysis: {str(e)}",
                'error': str(e)
            }), 500
            
    @app.route('/api/scenario/<symbol>', methods=['GET'])
    @rate_limit_decorator('scenario')
    def get_scenario_analysis(symbol):
        """
        Get scenario analysis for a cryptocurrency
        
        Parameters:
        - scenario: bull, bear, sideways (default: bull) - Scenario type
        """
        try:
            # Extract query parameters
            scenario_type = request.args.get('scenario', 'bull')
            
            # Validate scenario type
            if scenario_type not in ['bull', 'bear', 'sideways']:
                return jsonify({
                    'error': f"Invalid scenario type: {scenario_type}. Must be one of: bull, bear, sideways"
                }), 400
                
            # Fetch historical price data (use 1-year daily data for all scenarios)
            df = fetch_historical_data(symbol, period='1y', interval='1d')
            
            if df is None or df.empty:
                return jsonify({
                    'symbol': symbol,
                    'scenario': scenario_type,
                    'prediction': 'Neutral',
                    'confidence': 50,
                    'explanation': 'Insufficient historical data for scenario analysis',
                    'error': 'No price data available'
                }), 404
                
            # Run scenario analysis
            result = multi_signal_analyzer.get_scenario_analysis(symbol, df, scenario_type)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in scenario analysis for {symbol}: {str(e)}")
            # Set a default scenario value in case of error
            default_scenario = 'bull'
            scenario_val = scenario_type if 'scenario_type' in locals() else default_scenario
            
            return jsonify({
                'symbol': symbol,
                'scenario': scenario_val,
                'prediction': 'Neutral',
                'confidence': 50,
                'explanation': f"Error in analysis: {str(e)}",
                'error': str(e)
            }), 500
            
    @app.route('/api/onchain/<symbol>', methods=['GET'])
    @rate_limit_decorator('onchain')
    def get_onchain_analysis(symbol):
        """
        Get on-chain analysis for a cryptocurrency
        
        Parameters:
        - timeframe: 24h, 7d, 30d (default: 24h) - Analysis timeframe
        """
        try:
            # Extract query parameters
            timeframe = request.args.get('timeframe', '24h')
            
            # Validate timeframe
            if timeframe not in ['24h', '7d', '30d']:
                return jsonify({
                    'error': f"Invalid timeframe: {timeframe}. Must be one of: 24h, 7d, 30d"
                }), 400
                
            # Run on-chain analysis
            result = multi_signal_analyzer.onchain_analyzer.get_onchain_analysis(symbol, timeframe)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in on-chain analysis for {symbol}: {str(e)}")
            # Set a default timeframe value in case of error
            default_timeframe = '24h'
            timeframe_val = timeframe if 'timeframe' in locals() else default_timeframe
            
            return jsonify({
                'symbol': symbol,
                'timeframe': timeframe_val,
                'overall_sentiment': 'Neutral',
                'score': 0,
                'explanation': f"Error in analysis: {str(e)}",
                'error': str(e)
            }), 500
            
    @app.route('/api/social/<symbol>', methods=['GET'])
    @rate_limit_decorator('social')
    def get_social_sentiment(symbol):
        """
        Get social sentiment analysis for a cryptocurrency
        """
        try:
            # Run social sentiment analysis
            result = multi_signal_analyzer.sentiment_analyzer.get_combined_social_sentiment(symbol)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in social sentiment analysis for {symbol}: {str(e)}")
            return jsonify({
                'symbol': symbol,
                'sentiment': 'Neutral',
                'score': 0,
                'strength': 50,
                'explanation': f"Error in analysis: {str(e)}",
                'error': str(e)
            }), 500
            
    @app.route('/api/whale-alerts/<symbol>', methods=['GET'])
    @rate_limit_decorator('whale_alerts')
    def get_whale_alerts(symbol):
        """
        Get whale alerts (large transactions) for a cryptocurrency
        
        Parameters:
        - min_amount: Minimum transaction amount in USD (default: 1000000)
        """
        try:
            # Extract query parameters
            min_amount = request.args.get('min_amount', 1000000, type=int)
            
            # Get whale alerts
            result = multi_signal_analyzer.onchain_analyzer.get_whale_alerts(symbol, min_amount)
            
            return jsonify({
                'symbol': symbol,
                'min_amount': min_amount,
                'transactions': result
            })
            
        except Exception as e:
            logger.error(f"Error getting whale alerts for {symbol}: {str(e)}")
            # Set a default min_amount value in case of error
            default_min_amount = 1000000
            min_amount_val = min_amount if 'min_amount' in locals() else default_min_amount
            
            return jsonify({
                'symbol': symbol,
                'min_amount': min_amount_val,
                'transactions': [],
                'error': str(e)
            }), 500