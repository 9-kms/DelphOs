import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def analyze_any_coin(data):
    """
    Robust general technical analysis for any cryptocurrency that works even with problematic data
    
    Args:
        data: DataFrame with price data (must include 'Close' column)
        
    Returns:
        Dictionary with technical analysis information
    """
    try:
        # Simple approach that works with any dataframe format
        # Get the closing prices
        try:
            # Try to get values safely from a DataFrame or Series
            if isinstance(data, pd.DataFrame) and 'Close' in data.columns:
                close_prices = data['Close'].values.flatten()
            elif isinstance(data, pd.Series):
                close_prices = data.values.flatten()
            else:
                # If we can't get values directly, try this approach
                close_prices = np.array(data['Close']).flatten()
        except Exception as e:
            logger.error(f"Error extracting close prices: {str(e)}")
            # Last resort, try manually extracting values
            close_prices = []
            for i in range(len(data)):
                try:
                    close_prices.append(float(data['Close'].iloc[i]))
                except:
                    close_prices.append(0)
            close_prices = np.array(close_prices)
        
        # Make sure we have at least some data to work with
        if len(close_prices) < 5:
            raise ValueError("Not enough price data for analysis")
            
        # Calculate basic metrics that don't require complex Series operations
        current_price = float(close_prices[-1])
        price_1d_ago = float(close_prices[-2]) if len(close_prices) > 1 else current_price
        price_7d_ago = float(close_prices[-8]) if len(close_prices) > 7 else current_price
        price_14d_ago = float(close_prices[-15]) if len(close_prices) > 14 else current_price
        price_30d_ago = float(close_prices[-31]) if len(close_prices) > 30 else current_price
        
        # Calculate percentage changes
        change_1d = ((current_price / price_1d_ago) - 1) * 100
        change_7d = ((current_price / price_7d_ago) - 1) * 100
        change_14d = ((current_price / price_14d_ago) - 1) * 100
        change_30d = ((current_price / price_30d_ago) - 1) * 100
        
        # Calculate RSI (simplified version)
        price_changes = []
        for i in range(1, len(close_prices)):
            price_changes.append(close_prices[i] - close_prices[i-1])
        
        if len(price_changes) < 14:
            # Not enough data for proper RSI
            rsi = 50
        else:
            # Get the last 14 changes for RSI calculation
            recent_changes = price_changes[-14:]
            
            # Calculate gains and losses
            gains = [max(0, change) for change in recent_changes]
            losses = [max(0, -change) for change in recent_changes]
            
            # Calculate average gain and loss
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0.001  # Avoid division by zero
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Calculate simple moving averages
        sma_short = np.mean(close_prices[-10:]) if len(close_prices) >= 10 else current_price
        sma_medium = np.mean(close_prices[-20:]) if len(close_prices) >= 20 else current_price
        sma_long = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else current_price
        
        # Determine market trend based on SMAs
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
            
        # Determine MACD-like signal (simplified)
        ema12 = np.mean(close_prices[-12:]) if len(close_prices) >= 12 else current_price
        ema26 = np.mean(close_prices[-26:]) if len(close_prices) >= 26 else current_price
        macd = ema12 - ema26
        
        # Generate signals based on multiple indicators
        bullish_signals = 0
        bearish_signals = 0
        
        # RSI signals
        if rsi < 30:
            bullish_signals += 1  # Oversold
        elif rsi > 70:
            bearish_signals += 1  # Overbought
            
        # Trend signals
        if "Uptrend" in trend:
            bullish_signals += 1
        elif "Downtrend" in trend:
            bearish_signals += 1
            
        # Recent price action signals
        if change_7d > 10:
            bullish_signals += 1  # Strong weekly gain
        elif change_7d < -10:
            bearish_signals += 1  # Strong weekly loss
            
        # MACD signal
        if macd > 0:
            bullish_signals += 1
        else:
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
            
        # Generate explanation text
        explanation_parts = []
        explanation_parts.append(f"RSI: {rsi:.1f}")
        explanation_parts.append(f"Trend: {trend}")
        explanation_parts.append(f"7d Change: {change_7d:.1f}%")
        
        if macd > 0:
            explanation_parts.append("MACD: Positive")
        else:
            explanation_parts.append("MACD: Negative")
            
        # Build the complete analysis result
        return {
            "price": current_price,
            "rsi": rsi,
            "srsi_k": 50,  # Simplified value
            "srsi_d": 50,  # Simplified value
            "macd": macd,
            "macd_signal": 0,  # Simplified value
            "ema_status": {"position": trend.split()[0].lower()},
            "overall_signal": signal,
            "confidence": confidence,
            "explanation": " | ".join(explanation_parts)
        }
        
    except Exception as e:
        logger.error(f"Error in general analyzer: {str(e)}")
        # Fallback prediction
        return {
            "price": float(data['Close'].iloc[-1]) if 'Close' in data.columns else 0,
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