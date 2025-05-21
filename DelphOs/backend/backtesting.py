"""
Backtesting module for cryptocurrency prediction models
Tests the performance of ML prediction models on historical data
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import logging
from enhanced_ml import generate_features, enhanced_prediction

logger = logging.getLogger(__name__)

def run_backtest(symbol, period="1y", prediction_interval=7):
    """
    Run a backtest of prediction model on historical data
    
    Args:
        symbol: Cryptocurrency symbol (e.g., BTC)
        period: Historical period to test ('1mo', '3mo', '6mo', '1y', '2y')
        prediction_interval: Days to hold position after prediction (default: 7)
        
    Returns:
        Dict with backtest results
    """
    try:
        # Validate inputs
        if not symbol:
            return {"error": "Symbol is required"}, 400
            
        # Uppercase and add USD if needed
        symbol = symbol.upper()
        if not symbol.endswith('-USD'):
            symbol = f"{symbol}-USD"
            
        # Map period strings to days for our calculations
        period_days = {
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825
        }
        
        # Get extra data to account for initial indicators calculation
        extra_days = 30  # Need some extra days for indicator calculation
        
        # Download historical data
        logger.info(f"Fetching data for {symbol} for backtesting ({period})")
        data = yf.download(symbol, period=period)
        
        if data.empty or len(data) < 30:
            return {"error": f"Insufficient data for {symbol} to run backtest"}, 400
            
        # Handle multi-dimensional data - this happens sometimes with yfinance data
        for col in data.columns:
            if hasattr(data[col], 'ndim') and data[col].ndim > 1:
                data[col] = data[col].iloc[:, 0]
                
        # Generate all technical indicators and features
        try:
            enhanced_data = generate_features(data)
        except Exception as e:
            logger.error(f"Error generating features for backtest: {str(e)}")
            return {"error": f"Failed to process data for backtest: {str(e)}"}, 500
        
        # Prepare backtest results
        backtest_results = []
        trades = []
        
        # Start from index 30 to ensure enough data for indicators
        start_idx = 30
        
        # Iterate through historical data points
        for i in range(start_idx, len(enhanced_data) - prediction_interval):
            # Get data up to this point (simulate what we would know at this time)
            historical_slice = enhanced_data.iloc[:i+1].copy()
            
            # Get actual future data for comparison (only for backtesting)
            future_price = enhanced_data.iloc[i + prediction_interval]['Close']
            current_price = historical_slice.iloc[-1]['Close']
            
            # Calculate actual return
            actual_return = (future_price / current_price - 1) * 100
            
            # Generate prediction using our model
            prediction, confidence, reason = enhanced_prediction(historical_slice)
            
            # Record the result
            trade_result = {
                'date': historical_slice.index[-1].strftime('%Y-%m-%d'),
                'timestamp': historical_slice.index[-1].timestamp() * 1000,  # for charting
                'prediction': prediction,
                'confidence': confidence,
                'price': float(current_price),
                'future_price': float(future_price),
                'actual_return': float(actual_return),
                'reason': reason
            }
            
            # Add calculated success/failure
            if (prediction == 'Bullish' and actual_return > 0) or (prediction == 'Bearish' and actual_return < 0):
                trade_result['outcome'] = 'Success'
            elif prediction == 'Neutral':
                trade_result['outcome'] = 'Neutral'
            else:
                trade_result['outcome'] = 'Failure'
                
            trades.append(trade_result)
            
            # Only check every 3 days to avoid too many data points
            # This simulates making a new prediction every 3 days
            i += 3
        
        # Calculate performance metrics
        if trades:
            successful_trades = sum(1 for t in trades if t['outcome'] == 'Success')
            failed_trades = sum(1 for t in trades if t['outcome'] == 'Failure')
            neutral_trades = sum(1 for t in trades if t['outcome'] == 'Neutral')
            
            total_predictions = successful_trades + failed_trades + neutral_trades
            
            # Simulate portfolio performance
            initial_capital = 10000  # $10,000 starting capital
            portfolio_value = initial_capital
            hodl_value = initial_capital
            
            first_price = trades[0]['price'] if trades else 0
            
            for trade in trades:
                # Strategy: If bullish, enter long position with 100% of capital
                # If bearish, exit position (hold cash)
                # If neutral, do nothing (hold whatever position we had)
                
                if trade['prediction'] == 'Bullish':
                    # Simulate buying and holding for prediction_interval days
                    portfolio_value = portfolio_value * (1 + trade['actual_return'] / 100)
                elif trade['prediction'] == 'Bearish':
                    # For bearish, we don't participate in the market (hold cash)
                    pass
                    
                # Calculate HODL strategy value
                if trade == trades[-1]:  # Only for the last trade
                    hodl_return = (trade['price'] / first_price - 1) * 100
                    hodl_value = initial_capital * (1 + hodl_return / 100)
            
            # Calculate results
            success_rate = (successful_trades / total_predictions * 100) if total_predictions > 0 else 0
            portfolio_return = (portfolio_value / initial_capital - 1) * 100
            hodl_return = (hodl_value / initial_capital - 1) * 100
            
            # Alpha - excess return over the benchmark (HODL strategy)
            alpha = portfolio_return - hodl_return
            
            # Prepare results
            results = {
                'symbol': symbol,
                'period': period,
                'prediction_interval': prediction_interval,
                'num_trades': len(trades),
                'successful_trades': successful_trades,
                'failed_trades': failed_trades,
                'neutral_trades': neutral_trades,
                'success_rate': round(success_rate, 2),
                'initial_capital': initial_capital,
                'final_portfolio_value': round(portfolio_value, 2),
                'portfolio_return': round(portfolio_return, 2),
                'hodl_return': round(hodl_return, 2),
                'alpha': round(alpha, 2),
                'trades': trades[-20:],  # Return only the last 20 trades to keep response size reasonable
                'timestamp': datetime.now().isoformat()
            }
            
            return results
        else:
            return {"error": "No valid trades generated during backtest"}, 400
            
    except Exception as e:
        logger.error(f"Error running backtest: {str(e)}")
        return {"error": f"Backtest failed: {str(e)}"}, 500


def add_backtest_routes(app, rate_limit_decorator):
    """
    Add backtesting routes to Flask app
    """
    @app.route('/api/backtest/<symbol>', methods=['GET'])
    @rate_limit_decorator('api_backtest')
    def backtest(symbol):
        """
        Run a backtest for a given cryptocurrency
        
        Parameters:
        - period: 1mo, 3mo, 6mo, 1y, 2y, 5y (default: 1y)
        - interval: Prediction interval in days (default: 7)
        """
        from flask import request, jsonify
        
        # Get parameters
        period = request.args.get('period', '1y')
        prediction_interval = int(request.args.get('interval', '7'))
        
        # Validate parameters
        valid_periods = ['1mo', '3mo', '6mo', '1y', '2y', '5y']
        
        if period not in valid_periods:
            return jsonify({"error": f"Invalid period. Valid options: {', '.join(valid_periods)}"}), 400
            
        if prediction_interval < 1 or prediction_interval > 30:
            return jsonify({"error": "Interval must be between 1 and 30 days"}), 400
            
        # Run backtest
        results, status_code = run_backtest(symbol, period, prediction_interval)
        
        if isinstance(status_code, int):
            return jsonify(results), status_code
        else:
            return jsonify(results)