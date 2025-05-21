"""
Routes to serve historical chart data for cryptocurrencies
"""
from flask import request, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def add_chart_routes(app, rate_limit_decorator, get_cached_data, set_cache):
    """
    Add chart-related routes to Flask app
    """
    
    @app.route('/api/charts/<symbol>', methods=['GET'])
    @rate_limit_decorator('api_charts')
    def get_chart_data(symbol):
        """
        Get historical chart data for a cryptocurrency
        
        Parameters:
        - timeframe: 1d, 7d, 30d, 90d, 1y, 2y, 5y, max (default: 30d)
        - interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo (default: 1d)
        - type: line, candle (default: candle)
        """
        try:
            # Validate symbol
            if not symbol:
                return jsonify({"error": "Symbol is required"}), 400
                
            symbol = symbol.upper()
            
            # Check if we're requesting a USD pair
            if not symbol.endswith('-USD'):
                symbol = f"{symbol}-USD"
                
            # Get parameters
            timeframe = request.args.get('timeframe', '30d')
            interval = request.args.get('interval', '1d')
            chart_type = request.args.get('type', 'candle')
            
            # Validate parameters
            valid_timeframes = ['1d', '7d', '30d', '90d', '1y', '2y', '5y', 'max']
            valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']
            valid_types = ['line', 'candle']
            
            if timeframe not in valid_timeframes:
                return jsonify({"error": f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}"}), 400
                
            if interval not in valid_intervals:
                return jsonify({"error": f"Invalid interval. Valid options: {', '.join(valid_intervals)}"}), 400
                
            if chart_type not in valid_types:
                return jsonify({"error": f"Invalid chart type. Valid options: {', '.join(valid_types)}"}), 400
                
            # Check cache first
            cache_key = f"chart_{symbol}_{timeframe}_{interval}"
            cached_data = get_cached_data(cache_key)
            
            if cached_data:
                logger.debug(f"Using cached chart data for {symbol}")
                return jsonify(cached_data)
                
            # Get data from yfinance
            logger.info(f"Fetching chart data for {symbol} ({timeframe}, {interval})")
            
            # Map between our timeframes and yfinance periods
            period_map = {
                '1d': '1d',
                '7d': '7d',
                '30d': '1mo',
                '90d': '3mo',
                '1y': '1y',
                '2y': '2y',
                '5y': '5y',
                'max': 'max'
            }
            
            yf_period = period_map.get(timeframe, '1mo')
            
            try:
                # Download data
                data = yf.download(symbol, period=yf_period, interval=interval)
                
                # Check if we got data
                if data.empty:
                    return jsonify({"error": f"No data available for {symbol}"}), 404
                
                # Handle multi-dimensional data - this happens sometimes with yfinance data
                for col in data.columns:
                    if hasattr(data[col], 'ndim') and data[col].ndim > 1:
                        data[col] = data[col].iloc[:, 0]
                
                # Format data for charts
                chart_data = []
                
                try:
                    if chart_type == 'candle':
                        # Format for candlestick chart
                        for idx, row in data.iterrows():
                            try:
                                timestamp = int(idx.timestamp() * 1000)  # Convert to milliseconds
                                
                                # Safely extract each value with backup for problematic data
                                open_val = float(row['Open']) if not pd.isna(row['Open']) else None
                                high_val = float(row['High']) if not pd.isna(row['High']) else None
                                low_val = float(row['Low']) if not pd.isna(row['Low']) else None
                                close_val = float(row['Close']) if not pd.isna(row['Close']) else None
                                
                                # Skip this candle if any essential value is missing
                                if None in (open_val, high_val, low_val, close_val):
                                    continue
                                    
                                volume_val = float(row['Volume']) if 'Volume' in row and not pd.isna(row['Volume']) and row['Volume'] > 0 else 0
                                
                                chart_data.append({
                                    'timestamp': timestamp,
                                    'open': open_val,
                                    'high': high_val,
                                    'low': low_val,
                                    'close': close_val,
                                    'volume': volume_val,
                                    # Add color for better visualization
                                    'color': 'green' if close_val >= open_val else 'red'
                                })
                            except Exception as e:
                                logger.warning(f"Error processing candlestick row: {str(e)}")
                                continue
                    else:
                        # Format for line chart (simpler, just need close prices)
                        for idx, row in data.iterrows():
                            try:
                                timestamp = int(idx.timestamp() * 1000)  # Convert to milliseconds
                                close_val = float(row['Close']) if not pd.isna(row['Close']) else None
                                
                                # Skip invalid points
                                if close_val is None:
                                    continue
                                    
                                chart_data.append({
                                    'timestamp': timestamp,
                                    'price': close_val
                                })
                            except Exception as e:
                                logger.warning(f"Error processing line chart row: {str(e)}")
                                continue
                except Exception as e:
                    logger.error(f"Error formatting chart data: {str(e)}")
                    return jsonify({"error": f"Error formatting chart data: {str(e)}"}), 500
                
                # Check if we have data after processing
                if not chart_data:
                    return jsonify({"error": "No valid data points for charting"}), 404
                
                # Calculate additional statistics
                if isinstance(data['Close'], pd.Series):
                    latest_price = float(data['Close'].iloc[-1])
                elif hasattr(data['Close'], 'ndim') and data['Close'].ndim > 1:
                    latest_price = float(data['Close'].iloc[-1, 0])
                else:
                    latest_price = float(data['Close'].iloc[-1])
                
                # For period change calculation, calculate first non-NaN price
                start_idx = 0
                try:
                    while start_idx < len(data):
                        if isinstance(data['Close'], pd.Series):
                            if not pd.isna(data['Close'].iloc[start_idx]):
                                break
                        elif hasattr(data['Close'], 'ndim') and data['Close'].ndim > 1:
                            if not pd.isna(data['Close'].iloc[start_idx, 0]):
                                break
                        else:
                            if not pd.isna(data['Close'].iloc[start_idx]):
                                break
                        start_idx += 1
                        
                    if start_idx < len(data):
                        if isinstance(data['Close'], pd.Series):
                            start_price = float(data['Close'].iloc[start_idx])
                        elif hasattr(data['Close'], 'ndim') and data['Close'].ndim > 1:
                            start_price = float(data['Close'].iloc[start_idx, 0])
                        else:
                            start_price = float(data['Close'].iloc[start_idx])
                        period_change_pct = ((latest_price / start_price) - 1) * 100
                    else:
                        period_change_pct = 0
                except Exception as e:
                    logger.error(f"Error calculating change: {str(e)}")
                    period_change_pct = 0
                
                # Get min/max for the period
                try:
                    if isinstance(data['High'], pd.Series):
                        period_high = float(data['High'].max())
                    elif hasattr(data['High'], 'ndim') and data['High'].ndim > 1:
                        period_high = float(data['High'].iloc[:, 0].max())
                    else:
                        period_high = float(data['High'].max())
                        
                    if isinstance(data['Low'], pd.Series):
                        period_low = float(data['Low'].min())
                    elif hasattr(data['Low'], 'ndim') and data['Low'].ndim > 1:
                        period_low = float(data['Low'].iloc[:, 0].min())
                    else:
                        period_low = float(data['Low'].min())
                except Exception as e:
                    logger.error(f"Error calculating high/low: {str(e)}")
                    period_high = latest_price * 1.1  # Fallback
                    period_low = latest_price * 0.9  # Fallback
                
                # Add technical indicators for more advanced analysis
                rsi_data = []
                try:
                    # Calculate RSI directly with pandas to avoid dependency issues
                    if len(data) >= 14:  # Need at least 14 periods for RSI
                        # Make sure we're working with Series data
                        if isinstance(data['Close'], pd.Series):
                            close_prices = data['Close']
                        else:
                            close_prices = data['Close'].iloc[:, 0] if hasattr(data['Close'], 'ndim') and data['Close'].ndim > 1 else data['Close']
                        
                        # Calculate RSI using pandas implementation
                        delta = close_prices.diff()
                        gains = delta.where(delta > 0, 0)
                        losses = -delta.where(delta < 0, 0)
                        avg_gain = gains.rolling(window=14).mean()
                        avg_loss = losses.rolling(window=14).mean()
                        
                        # Handle division by zero (safely)
                        avg_loss = avg_loss.replace(0, 0.001)
                        rs = avg_gain / avg_loss
                        rsi_series = 100 - (100 / (1 + rs))
                            
                        # Create RSI data in the same time format
                        for i, idx in enumerate(data.index):
                            if i < len(rsi_series) and not pd.isna(rsi_series.iloc[i]):
                                rsi_data.append({
                                    'timestamp': int(idx.timestamp() * 1000),
                                    'value': float(rsi_series.iloc[i])
                                })
                except Exception as e:
                    logger.warning(f"Could not calculate RSI: {str(e)}")
                    # Keep rsi_data as empty list
                
                # Create response
                response = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'interval': interval,
                    'type': chart_type,
                    'data': chart_data,
                    'indicators': {
                        'rsi': rsi_data
                    },
                    'stats': {
                        'latest_price': latest_price,
                        'period_change_pct': period_change_pct,
                        'period_high': period_high,
                        'period_low': period_low,
                        'period_high_low_spread_pct': ((period_high / period_low) - 1) * 100 if period_low > 0 else 0
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                # Cache the response
                set_cache(cache_key, response)
                
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error fetching chart data: {str(e)}")
                return jsonify({"error": f"Failed to fetch chart data: {str(e)}"}), 500
                
        except Exception as e:
            logger.error(f"Error in get_chart_data: {str(e)}")
            return jsonify({"error": str(e)}), 500