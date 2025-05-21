import pandas as pd
import numpy as np
import logging
from ta.volatility import BollingerBands
from ta.trend import ADXIndicator, MACD

logger = logging.getLogger(__name__)

def calculate_ema(data, period=14):
    """Calculate Exponential Moving Average"""
    try:
        return data.ewm(span=period, adjust=False).mean()
    except Exception as e:
        logger.error(f"Error calculating EMA: {str(e)}")
        return pd.Series(np.nan, index=data.index)

def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    try:
        # Calculate EMA values
        fast_ema = calculate_ema(data, fast_period)
        slow_ema = calculate_ema(data, slow_period)
        
        # Calculate MACD line and signal line
        macd_line = fast_ema - slow_ema
        signal_line = calculate_ema(macd_line, signal_period)
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    except Exception as e:
        logger.error(f"Error calculating MACD: {str(e)}")
        return pd.Series(np.nan, index=data.index), pd.Series(np.nan, index=data.index), pd.Series(np.nan, index=data.index)

def calculate_stochastic_rsi(data, period=14, k_period=3, d_period=3):
    """Calculate Stochastic RSI"""
    try:
        # Calculate RSI
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Handle division by zero
        rs = pd.Series(np.where(avg_loss == 0, 0, avg_gain / avg_loss), index=data.index)
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate Stochastic RSI
        min_rsi = rsi.rolling(window=period).min()
        max_rsi = rsi.rolling(window=period).max()
        
        # Handle division by zero
        denominator = max_rsi - min_rsi
        denominator = denominator.replace(0, np.nan)
        
        stoch_rsi = 100 * ((rsi - min_rsi) / denominator)
        stoch_rsi = stoch_rsi.fillna(50)  # Default value when no range
        
        # Calculate K and D
        k = stoch_rsi.rolling(window=k_period).mean()
        d = k.rolling(window=d_period).mean()
        
        return rsi, k, d
    except Exception as e:
        logger.error(f"Error calculating Stochastic RSI: {str(e)}")
        return pd.Series(np.nan, index=data.index), pd.Series(np.nan, index=data.index), pd.Series(np.nan, index=data.index)

def check_ema_crossover(data, short_period=50, long_period=200):
    """Check for EMA crossovers (golden cross / death cross)"""
    try:
        short_ema = calculate_ema(data, short_period)
        long_ema = calculate_ema(data, long_period)
        
        # Current status
        current_short = short_ema.iloc[-1]
        current_long = long_ema.iloc[-1]
        
        # Previous status
        prev_short = short_ema.iloc[-2] if len(short_ema) > 1 else None
        prev_long = long_ema.iloc[-2] if len(long_ema) > 1 else None
        
        # Check for recent crossover
        bullish_crossover = False
        bearish_crossover = False
        
        if prev_short is not None and prev_long is not None:
            bullish_crossover = prev_short < prev_long and current_short > current_long
            bearish_crossover = prev_short > prev_long and current_short < current_long
            
        # Current position
        if current_short > current_long:
            position = "bullish"
        else:
            position = "bearish"
            
        return {
            "short_ema": current_short,
            "long_ema": current_long,
            "position": position,
            "bullish_crossover": bullish_crossover,
            "bearish_crossover": bearish_crossover
        }
        
    except Exception as e:
        logger.error(f"Error checking EMA crossover: {str(e)}")
        return {
            "short_ema": None,
            "long_ema": None,
            "position": "unknown",
            "bullish_crossover": False,
            "bearish_crossover": False
        }

def calculate_bollinger_bands(data, window=20, window_dev=2):
    """Calculate Bollinger Bands"""
    try:
        # Initialize Bollinger Bands
        indicator_bb = BollingerBands(close=data, window=window, window_dev=window_dev)
        
        # Get the indicator values
        bb_high_band = indicator_bb.bollinger_hband()
        bb_low_band = indicator_bb.bollinger_lband()
        bb_mid_band = indicator_bb.bollinger_mavg()
        bb_width = (bb_high_band - bb_low_band) / bb_mid_band  # Width as a percentage of the middle band
        
        # Get band crossing signals
        price_above_high = data > bb_high_band
        price_below_low = data < bb_low_band
        
        return {
            'high_band': bb_high_band,
            'mid_band': bb_mid_band,
            'low_band': bb_low_band,
            'width': bb_width,
            'price_above_high': price_above_high,
            'price_below_low': price_below_low
        }
        
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {str(e)}")
        return None

def calculate_adx(data_frame, window=14):
    """Calculate Average Directional Index (ADX)"""
    try:
        # Requires High, Low, Close data
        adx = ADXIndicator(
            high=data_frame['High'],
            low=data_frame['Low'],
            close=data_frame['Close'],
            window=window
        )
        
        # Get the indicator values
        adx_value = adx.adx()
        plus_di = adx.adx_pos()
        minus_di = adx.adx_neg()
        
        return adx_value, plus_di, minus_di
    
    except Exception as e:
        logger.error(f"Error calculating ADX: {str(e)}")
        return pd.Series(np.nan, index=data_frame.index), pd.Series(np.nan, index=data_frame.index), pd.Series(np.nan, index=data_frame.index)

def get_technical_analysis(data):
    """
    Generate comprehensive technical analysis for a given price series
    
    Args:
        data: DataFrame with price data (needs at least 'Close' column)
        
    Returns:
        Dictionary with various technical indicators and their interpretation
    """
    try:
        close_prices = data['Close']
        
        # Calculate RSI and Stochastic RSI
        rsi, srsi_k, srsi_d = calculate_stochastic_rsi(close_prices)
        
        # Calculate MACD
        macd_line, signal_line, histogram = calculate_macd(close_prices)
        
        # Check for EMA crossovers
        ema_status = check_ema_crossover(close_prices)
        
        # Calculate Bollinger Bands
        bollinger_data = calculate_bollinger_bands(close_prices)
        
        # Calculate ADX if we have HLOC data
        adx_value = None
        plus_di = None
        minus_di = None
        if all(col in data.columns for col in ['High', 'Low', 'Close']):
            adx_value, plus_di, minus_di = calculate_adx(data)
        
        # Get the most recent values
        latest_price = close_prices.iloc[-1]
        latest_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        latest_srsi_k = srsi_k.iloc[-1] if not pd.isna(srsi_k.iloc[-1]) else 50
        latest_srsi_d = srsi_d.iloc[-1] if not pd.isna(srsi_d.iloc[-1]) else 50
        latest_macd = macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0
        latest_signal = signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0
        
        # Get latest Bollinger Band values
        if bollinger_data is not None:
            latest_bb_high = bollinger_data['high_band'].iloc[-1] if not pd.isna(bollinger_data['high_band'].iloc[-1]) else 0
            latest_bb_low = bollinger_data['low_band'].iloc[-1] if not pd.isna(bollinger_data['low_band'].iloc[-1]) else 0
            latest_bb_mid = bollinger_data['mid_band'].iloc[-1] if not pd.isna(bollinger_data['mid_band'].iloc[-1]) else 0
            latest_bb_width = bollinger_data['width'].iloc[-1] if not pd.isna(bollinger_data['width'].iloc[-1]) else 0
            
            # Check if price is outside Bollinger Bands
            price_above_high = bollinger_data['price_above_high'].iloc[-1] if not pd.isna(bollinger_data['price_above_high'].iloc[-1]) else False
            price_below_low = bollinger_data['price_below_low'].iloc[-1] if not pd.isna(bollinger_data['price_below_low'].iloc[-1]) else False
        else:
            latest_bb_high = 0
            latest_bb_low = 0
            latest_bb_mid = 0
            latest_bb_width = 0
            price_above_high = False
            price_below_low = False
            
        # Get latest ADX values if available
        if adx_value is not None and not pd.isna(adx_value.iloc[-1]):
            latest_adx = adx_value.iloc[-1]
            latest_plus_di = plus_di.iloc[-1] if not pd.isna(plus_di.iloc[-1]) else 0
            latest_minus_di = minus_di.iloc[-1] if not pd.isna(minus_di.iloc[-1]) else 0
        else:
            latest_adx = 0
            latest_plus_di = 0
            latest_minus_di = 0
        
        # Interpret RSI
        if latest_rsi > 70:
            rsi_signal = "Overbought"
            rsi_action = "Potential sell or bearish reversal"
        elif latest_rsi < 30:
            rsi_signal = "Oversold"
            rsi_action = "Potential buy or bullish reversal"
        else:
            rsi_signal = "Neutral"
            rsi_action = "No clear signal from RSI"
            
        # Interpret Stochastic RSI
        if latest_srsi_k > 80:
            srsi_signal = "Overbought"
            srsi_action = "Potential sell"
        elif latest_srsi_k < 20:
            srsi_signal = "Oversold"
            srsi_action = "Potential buy"
        else:
            srsi_signal = "Neutral"
            srsi_action = "No clear signal from Stochastic RSI"
            
        # MACD interpretation
        if latest_macd > latest_signal:
            macd_signal = "Bullish"
            if latest_macd > 0:
                macd_action = "Strong bullish momentum"
            else:
                macd_action = "Bullish momentum building"
        else:
            macd_signal = "Bearish"
            if latest_macd < 0:
                macd_action = "Strong bearish momentum"
            else:
                macd_action = "Bearish momentum building"
        
        # Bollinger Bands interpretation
        if price_above_high:
            bollinger_signal = "Overbought"
            bollinger_action = "Potential reversal or continuation of strong trend"
        elif price_below_low:
            bollinger_signal = "Oversold"
            bollinger_action = "Potential reversal or continuation of strong downtrend"
        else:
            # Price is within bands
            if latest_bb_width > 0.05:  # Wider bands indicate higher volatility
                bollinger_signal = "High Volatility"
                bollinger_action = "Prepare for potential breakout"
            else:
                bollinger_signal = "Low Volatility"
                bollinger_action = "Potential for upcoming volatility"
        
        # ADX interpretation
        if latest_adx > 25:
            if latest_plus_di > latest_minus_di:
                adx_signal = "Strong Uptrend"
                adx_action = "Consider trend-following strategies"
            else:
                adx_signal = "Strong Downtrend"
                adx_action = "Consider defensive positions"
        else:
            adx_signal = "No Strong Trend"
            adx_action = "Range-bound market likely"
                
        # Overall analysis
        signals = {
            "bullish": 0,
            "bearish": 0,
            "neutral": 0
        }
        
        # Count signals from RSI
        if rsi_signal == "Oversold":
            signals["bullish"] += 1
        elif rsi_signal == "Overbought":
            signals["bearish"] += 1
        else:
            signals["neutral"] += 1
            
        # Count signals from Stochastic RSI
        if srsi_signal == "Oversold":
            signals["bullish"] += 1
        elif srsi_signal == "Overbought":
            signals["bearish"] += 1
        else:
            signals["neutral"] += 1
            
        # Count signals from MACD
        if macd_signal == "Bullish":
            signals["bullish"] += 1
        else:
            signals["bearish"] += 1
            
        # Count signals from EMA crossovers
        if ema_status["position"] == "bullish":
            signals["bullish"] += 1
        else:
            signals["bearish"] += 1
            
        # Count signals from Bollinger Bands
        if bollinger_signal == "Oversold":
            signals["bullish"] += 1
        elif bollinger_signal == "Overbought":
            signals["bearish"] += 1
        else:
            signals["neutral"] += 1
            
        # Count signals from ADX
        if adx_signal == "Strong Uptrend":
            signals["bullish"] += 1
        elif adx_signal == "Strong Downtrend":
            signals["bearish"] += 1
        else:
            signals["neutral"] += 1
            
        # Determine overall sentiment with more indicators
        if signals["bullish"] > signals["bearish"]:
            overall_signal = "Bullish"
            confidence = min(50 + (signals["bullish"] * 8), 90)
        elif signals["bearish"] > signals["bullish"]:
            overall_signal = "Bearish"
            confidence = min(50 + (signals["bearish"] * 8), 90)
        else:
            overall_signal = "Neutral"
            confidence = 50
            
        # Generate explanation
        details = []
        details.append(f"RSI at {latest_rsi:.1f}: {rsi_signal}")
        details.append(f"Stochastic RSI at {latest_srsi_k:.1f}: {srsi_signal}")
        details.append(f"MACD: {macd_signal} ({macd_action})")
        
        if bollinger_data is not None:
            details.append(f"Bollinger Bands: {bollinger_signal}")
        
        if latest_adx > 0:
            details.append(f"ADX at {latest_adx:.1f}: {adx_signal}")
        
        if ema_status["bullish_crossover"]:
            details.append("Recent bullish EMA crossover (Golden Cross)")
        elif ema_status["bearish_crossover"]:
            details.append("Recent bearish EMA crossover (Death Cross)")
        else:
            details.append(f"EMA position: {ema_status['position'].capitalize()}")
        
        explanation = " | ".join(details)
            
        return {
            "price": latest_price,
            "rsi": latest_rsi,
            "srsi_k": latest_srsi_k,
            "srsi_d": latest_srsi_d,
            "macd": latest_macd,
            "macd_signal": latest_signal,
            "bollinger": {
                "high": latest_bb_high,
                "mid": latest_bb_mid,
                "low": latest_bb_low,
                "width": latest_bb_width,
                "signal": bollinger_signal
            },
            "adx": {
                "value": latest_adx,
                "plus_di": latest_plus_di,
                "minus_di": latest_minus_di,
                "signal": adx_signal
            },
            "ema_status": ema_status,
            "overall_signal": overall_signal,
            "confidence": confidence,
            "explanation": explanation,
            "signal_count": signals
        }
        
    except Exception as e:
        logger.error(f"Error in technical analysis: {str(e)}")
        return {
            "price": data['Close'].iloc[-1] if not data['Close'].empty else 0,
            "rsi": 50,
            "srsi_k": 50,
            "srsi_d": 50,
            "macd": 0,
            "macd_signal": 0,
            "bollinger": {
                "high": 0,
                "mid": 0,
                "low": 0,
                "width": 0,
                "signal": "Unknown"
            },
            "adx": {
                "value": 0,
                "plus_di": 0,
                "minus_di": 0,
                "signal": "Unknown"
            },
            "ema_status": {"position": "unknown"},
            "overall_signal": "Neutral",
            "confidence": 50,
            "explanation": "Error generating technical analysis",
            "signal_count": {"bullish": 0, "bearish": 0, "neutral": 0}
        }