import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def analyze_link(data):
    """
    Special technical analysis for LINK token that works even with problematic data structures
    
    Args:
        data: DataFrame with price data (must include 'Close' column)
        
    Returns:
        Dictionary with technical analysis information
    """
    try:
        # Extract close prices as a simple list/array
        close_prices = data['Close'].values
        
        # Calculate basic price changes
        current_price = close_prices[-1]
        price_1d_ago = close_prices[-2] if len(close_prices) > 1 else current_price
        price_7d_ago = close_prices[-8] if len(close_prices) > 7 else current_price
        price_14d_ago = close_prices[-15] if len(close_prices) > 14 else current_price
        price_30d_ago = close_prices[-31] if len(close_prices) > 30 else current_price
        
        # Calculate percentage changes
        change_1d = ((current_price / price_1d_ago) - 1) * 100
        change_7d = ((current_price / price_7d_ago) - 1) * 100
        change_14d = ((current_price / price_14d_ago) - 1) * 100
        change_30d = ((current_price / price_30d_ago) - 1) * 100
        
        # Calculate manual RSI (simplified)
        gains = []
        losses = []
        
        for i in range(1, min(15, len(close_prices))):
            change = close_prices[-i] - close_prices[-(i+1)]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0.001  # Avoid division by zero
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate simple moving averages
        sma_short = np.mean(close_prices[-10:]) if len(close_prices) >= 10 else current_price
        sma_medium = np.mean(close_prices[-20:]) if len(close_prices) >= 20 else current_price
        sma_long = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else current_price
        
        # Determine trend based on SMA relationships
        if sma_short > sma_medium > sma_long:
            trend = "Strong Uptrend"
        elif sma_short > sma_medium:
            trend = "Uptrend"
        elif sma_short < sma_medium < sma_long:
            trend = "Strong Downtrend"
        elif sma_short < sma_medium:
            trend = "Downtrend"
        else:
            trend = "Sideways"
            
        # Determine overall signal
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI signals
        if rsi < 30:
            bullish_signals += 1
        elif rsi > 70:
            bearish_signals += 1
            
        # Moving average signals
        if sma_short > sma_medium:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        # Recent price action
        if change_7d > 10:  # Strong weekly gain
            bullish_signals += 1
        elif change_7d < -10:  # Strong weekly loss
            bearish_signals += 1
            
        # Generate overall prediction
        if bullish_signals > bearish_signals:
            signal = "Bullish"
            confidence = min(50 + (bullish_signals * 10), 90)
        elif bearish_signals > bullish_signals:
            signal = "Bearish"
            confidence = min(50 + (bearish_signals * 10), 90)
        else:
            signal = "Neutral"
            confidence = 50
            
        # Generate explanation
        explanation = []
        explanation.append(f"RSI: {rsi:.1f}")
        explanation.append(f"Trend: {trend}")
        explanation.append(f"1d Change: {change_1d:.1f}%")
        explanation.append(f"7d Change: {change_7d:.1f}%")
        
        # Return complete analysis
        return {
            "price": current_price,
            "rsi": rsi,
            "srsi_k": 50,  # Placeholder
            "srsi_d": 50,  # Placeholder
            "macd": 0,  # Placeholder
            "macd_signal": 0,  # Placeholder
            "ema_status": {"position": trend.split()[0].lower()},
            "overall_signal": signal,
            "confidence": confidence,
            "explanation": " | ".join(explanation)
        }
        
    except Exception as e:
        logger.error(f"Error in LINK analyzer: {str(e)}")
        # Fallback prediction based on recent data
        return {
            "price": data['Close'].iloc[-1],
            "rsi": 50,
            "srsi_k": 50,
            "srsi_d": 50,
            "macd": 0,
            "macd_signal": 0,
            "ema_status": {"position": "unknown"},
            "overall_signal": "Neutral",
            "confidence": 50,
            "explanation": "Technical analysis unavailable"
        }