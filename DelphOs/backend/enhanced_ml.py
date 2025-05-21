"""
Enhanced machine learning utilities for crypto predictions
Including multiple technical indicators and feature engineering
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands
from ta.momentum import StochasticOscillator, RSIIndicator, StochRSIIndicator
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator
import logging

logger = logging.getLogger(__name__)

def generate_features(df):
    """
    Generate technical indicators and custom features from price data
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        DataFrame with added technical indicators and features
    """
    try:
        # Make a copy to avoid modifying the original
        data = df.copy()
        
        # Check for required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_cols:
            if col not in data.columns:
                logger.warning(f"Missing required column: {col}")
                # Add empty columns if missing
                if col == 'Volume':
                    data[col] = 0
                else:
                    data[col] = data['Close']
        
        # 1. Technical Indicators
        # RSI
        rsi = RSIIndicator(close=data['Close'], window=14)
        data['rsi'] = rsi.rsi()
        
        # MACD
        macd = MACD(close=data['Close'])
        data['macd'] = macd.macd()
        data['macd_signal'] = macd.macd_signal()
        data['macd_diff'] = macd.macd_diff()
        
        # EMA
        ema12 = EMAIndicator(close=data['Close'], window=12)
        ema26 = EMAIndicator(close=data['Close'], window=26)
        data['ema12'] = ema12.ema_indicator()
        data['ema26'] = ema26.ema_indicator()
        
        # Bollinger Bands
        bollinger = BollingerBands(close=data['Close'], window=20)
        data['bb_high'] = bollinger.bollinger_hband()
        data['bb_low'] = bollinger.bollinger_lband()
        data['bb_mid'] = bollinger.bollinger_mavg()
        data['bb_width'] = (data['bb_high'] - data['bb_low']) / data['bb_mid']
        
        # Stochastic Oscillator
        stoch = StochasticOscillator(high=data['High'], low=data['Low'], close=data['Close'])
        data['stoch_k'] = stoch.stoch()
        data['stoch_d'] = stoch.stoch_signal()
        
        # ADX
        adx_indicator = ADXIndicator(high=data['High'], low=data['Low'], close=data['Close'])
        data['adx'] = adx_indicator.adx()
        
        # On-Balance Volume
        if 'Volume' in data.columns and not all(data['Volume'] == 0):
            obv = OnBalanceVolumeIndicator(close=data['Close'], volume=data['Volume'])
            data['obv'] = obv.on_balance_volume()
        else:
            data['obv'] = 0
        
        # Stochastic RSI
        stoch_rsi = StochRSIIndicator(close=data['Close'])
        data['stoch_rsi_k'] = stoch_rsi.stochrsi_k()
        data['stoch_rsi_d'] = stoch_rsi.stochrsi_d()
        
        # 2. Custom Engineered Features
        # Rolling mean and std for close price
        data['close_5d_mean'] = data['Close'].rolling(window=5).mean()
        data['close_10d_mean'] = data['Close'].rolling(window=10).mean()
        data['close_5d_std'] = data['Close'].rolling(window=5).std()
        data['close_10d_std'] = data['Close'].rolling(window=10).std()
        
        # Daily high-low spread
        data['daily_spread'] = (data['High'] - data['Low']) / data['Close']
        
        # Volume spike ratio (if volume data exists)
        if 'Volume' in data.columns and not all(data['Volume'] == 0):
            data['volume_5d_mean'] = data['Volume'].rolling(window=5).mean()
            data['volume_spike'] = data['Volume'] / data['volume_5d_mean']
        else:
            data['volume_spike'] = 1.0
        
        # RSI divergence (simple implementation)
        # Price making higher highs but RSI making lower highs = bearish divergence
        # Price making lower lows but RSI making higher lows = bullish divergence
        data['price_diff'] = data['Close'].diff(5)
        data['rsi_diff'] = data['rsi'].diff(5)
        data['divergence'] = np.where((data['price_diff'] > 0) & (data['rsi_diff'] < 0), -1,  # Bearish
                              np.where((data['price_diff'] < 0) & (data['rsi_diff'] > 0), 1,  # Bullish
                              0))  # No divergence
        
        # 3. Target Features (for training only)
        # Future price direction (1 = up, 0 = down or flat)
        data['next_day_return'] = data['Close'].pct_change(1).shift(-1)
        data['target'] = (data['next_day_return'] > 0).astype(int)
        
        # Fill NaN values that may have been created during calculations
        data = data.fillna(method='bfill').fillna(method='ffill').fillna(0)
        
        return data
        
    except Exception as e:
        logger.error(f"Error generating features: {str(e)}")
        return df  # Return original data if there's an error
    
def enhanced_prediction(data):
    """
    Generate predictions based on enhanced technical indicators
    
    Args:
        data: Pandas DataFrame with historical price data (will be augmented with indicators)
        
    Returns:
        prediction: String prediction (Bullish/Bearish/Neutral)
        confidence: Float confidence level (0-100)
        reason: String explanation for the prediction
    """
    try:
        # Check if we have enough data
        if data is None or len(data) < 30:
            logger.warning("Not enough data for enhanced prediction, using rule-based fallback")
            return rule_based_prediction(data)
            
        # Fix for non-standard data format from yfinance
        # Handle multi-dimensional data - this happens sometimes with yfinance data
        if isinstance(data['Close'], pd.DataFrame) or (hasattr(data['Close'], 'ndim') and data['Close'].ndim > 1):
            # Take the first column if it's a multi-dimensional array
            for col in data.columns:
                if hasattr(data[col], 'ndim') and data[col].ndim > 1:
                    data[col] = data[col].iloc[:, 0]
        
        # Generate all features
        try:
            enhanced_data = generate_features(data)
        except Exception as e:
            logger.error(f"Error generating features: {str(e)}")
            return rule_based_prediction(data)
        
        # Get the most recent data point
        latest = enhanced_data.iloc[-1]
        
        # Use an ensemble of indicators for the prediction
        signals = []
        confidences = []
        reasons = []
        
        # 1. RSI Signal
        if latest['rsi'] < 30:
            signals.append(1)  # Bullish
            confidences.append(70 + (30 - latest['rsi']) * 1.5)  # Higher confidence the lower RSI is
            reasons.append(f"RSI oversold ({latest['rsi']:.1f})")
        elif latest['rsi'] > 70:
            signals.append(-1)  # Bearish
            confidences.append(70 + (latest['rsi'] - 70) * 1.5)  # Higher confidence the higher RSI is
            reasons.append(f"RSI overbought ({latest['rsi']:.1f})")
        else:
            # Neutral but with a bias
            bias = 1 if latest['rsi'] < 50 else -1
            strength = abs(latest['rsi'] - 50) / 20  # 0 to 1 scale
            signals.append(bias * strength)
            confidences.append(50 + strength * 10)
            if bias == 1:
                reasons.append(f"RSI transitioning lower ({latest['rsi']:.1f})")
            else:
                reasons.append(f"RSI transitioning higher ({latest['rsi']:.1f})")
        
        # 2. MACD Signal
        if latest['macd'] > latest['macd_signal']:
            signals.append(1)  # Bullish
            # Confidence based on how far apart they are
            strength = min(abs(latest['macd_diff']) * 20, 25)  # Cap at 25
            confidences.append(50 + strength)
            reasons.append("MACD above signal line")
        else:
            signals.append(-1)  # Bearish
            # Confidence based on how far apart they are
            strength = min(abs(latest['macd_diff']) * 20, 25)  # Cap at 25
            confidences.append(50 + strength)
            reasons.append("MACD below signal line")
        
        # 3. EMA Signal
        if latest['ema12'] > latest['ema26']:
            signals.append(1)  # Bullish
            # Confidence based on the percentage difference
            diff_pct = (latest['ema12'] - latest['ema26']) / latest['ema26'] * 100
            confidences.append(50 + min(diff_pct * 5, 30))  # Cap at 30
            reasons.append("Short-term EMA above long-term EMA")
        else:
            signals.append(-1)  # Bearish
            # Confidence based on the percentage difference
            diff_pct = (latest['ema26'] - latest['ema12']) / latest['ema26'] * 100
            confidences.append(50 + min(diff_pct * 5, 30))  # Cap at 30
            reasons.append("Short-term EMA below long-term EMA")
        
        # 4. Bollinger Bands signal
        bb_pos = (latest['Close'] - latest['bb_low']) / (latest['bb_high'] - latest['bb_low'])
        if bb_pos < 0.2:  # Close to lower band
            signals.append(1)  # Bullish
            confidences.append(60 + (0.2 - bb_pos) * 100)
            reasons.append("Price near lower Bollinger Band")
        elif bb_pos > 0.8:  # Close to upper band
            signals.append(-1)  # Bearish
            confidences.append(60 + (bb_pos - 0.8) * 100)
            reasons.append("Price near upper Bollinger Band")
        else:
            # Neutral signal
            pass
        
        # 5. Stochastic Signal
        if latest['stoch_k'] < 20 and latest['stoch_d'] < 20:
            signals.append(1)  # Bullish
            confidences.append(60 + (20 - latest['stoch_k']) * 1.5)
            reasons.append(f"Stochastic oversold ({latest['stoch_k']:.1f})")
        elif latest['stoch_k'] > 80 and latest['stoch_d'] > 80:
            signals.append(-1)  # Bearish
            confidences.append(60 + (latest['stoch_k'] - 80) * 1.5)
            reasons.append(f"Stochastic overbought ({latest['stoch_k']:.1f})")
        elif latest['stoch_k'] > latest['stoch_d'] and latest['stoch_k'] < 80:
            signals.append(0.5)  # Mildly bullish
            confidences.append(55)
            reasons.append("Stochastic K crossing above D")
        elif latest['stoch_k'] < latest['stoch_d'] and latest['stoch_k'] > 20:
            signals.append(-0.5)  # Mildly bearish
            confidences.append(55)
            reasons.append("Stochastic K crossing below D")
        
        # 6. ADX Signal - strength of trend
        if latest['adx'] > 25:
            # Strong trend - amplify the most recent signal
            # We don't add a new signal but boost confidence in other signals
            for i in range(len(confidences)):
                confidences[i] = min(confidences[i] * (1 + (latest['adx'] - 25) / 100), 95)
            reasons.append(f"Strong trend (ADX: {latest['adx']:.1f})")
        
        # 7. Volume Spike Signal
        if latest['volume_spike'] > 2:
            # Volume spike can confirm the direction
            avg_signal = sum(signals[-2:]) / min(len(signals), 2)  # Average of recent signals
            if avg_signal > 0:
                signals.append(1)  # Confirm bullish
                confidences.append(60 + min(latest['volume_spike'] * 5, 25))
                reasons.append(f"High volume confirming uptrend ({latest['volume_spike']:.1f}x)")
            elif avg_signal < 0:
                signals.append(-1)  # Confirm bearish
                confidences.append(60 + min(latest['volume_spike'] * 5, 25))
                reasons.append(f"High volume confirming downtrend ({latest['volume_spike']:.1f}x)")
        
        # 8. RSI Divergence
        if latest['divergence'] == 1:  # Bullish divergence
            signals.append(1.5)  # Strong bullish
            confidences.append(80)
            reasons.append("Bullish RSI divergence")
        elif latest['divergence'] == -1:  # Bearish divergence
            signals.append(-1.5)  # Strong bearish
            confidences.append(80)
            reasons.append("Bearish RSI divergence")
        
        # Calculate the overall signal as a weighted average
        overall_signal = sum(signals) / len(signals)
        
        # Determine the prediction
        if overall_signal > 0.2:
            prediction = "Bullish"
        elif overall_signal < -0.2:
            prediction = "Bearish"
        else:
            prediction = "Neutral"
        
        # Calculate the confidence as average, adjusted by signal strength
        base_confidence = sum(confidences) / len(confidences)
        signal_multiplier = min(abs(overall_signal) * 1.5, 1.5)  # 1.0 to 1.5
        confidence = min(base_confidence * signal_multiplier, 95)  # Cap at 95
        
        # Round to nearest integer
        confidence = int(round(confidence))
        
        # Format the standard reason (top 3 most significant)
        significant_reasons = sorted(reasons, key=lambda x: len(x), reverse=True)[:3]
        reason = " | ".join(significant_reasons)
        
        # Create detailed analysis for deeper insights
        detailed_analysis = {
            "indicators": {
                "rsi": {
                    "value": round(float(latest['rsi']), 2),
                    "interpretation": "Oversold" if latest['rsi'] < 30 else 
                                     "Overbought" if latest['rsi'] > 70 else 
                                     "Neutral",
                    "signal": "Buy" if latest['rsi'] < 30 else 
                             "Sell" if latest['rsi'] > 70 else 
                             "Hold"
                },
                "macd": {
                    "value": round(float(latest['macd']), 2),
                    "signal_line": round(float(latest['macd_signal']), 2),
                    "histogram": round(float(latest['macd_diff']), 2),
                    "trend": "Bullish" if latest['macd'] > latest['macd_signal'] else "Bearish",
                    "strength": "Strong" if abs(latest['macd_diff']) > 0.5 else "Weak"
                },
                "bollinger_bands": {
                    "upper": round(float(latest['bb_high']), 2),
                    "middle": round(float(latest['bb_mid']), 2),
                    "lower": round(float(latest['bb_low']), 2),
                    "width": round(float(latest['bb_width']), 2),
                    "position": round(float((latest['Close'] - latest['bb_low']) / (latest['bb_high'] - latest['bb_low']) * 100), 2)
                },
                "stochastic": {
                    "k": round(float(latest['stoch_k']), 2),
                    "d": round(float(latest['stoch_d']), 2),
                    "condition": "Oversold" if latest['stoch_k'] < 20 else 
                                "Overbought" if latest['stoch_k'] > 80 else 
                                "Neutral"
                },
                "adx": {
                    "value": round(float(latest['adx']), 2),
                    "trend_strength": "Strong" if latest['adx'] > 25 else 
                                     "Very Strong" if latest['adx'] > 50 else 
                                     "Weak"
                },
                "ema_crossover": {
                    "ema12": round(float(latest['ema12']), 2),
                    "ema26": round(float(latest['ema26']), 2),
                    "status": "Golden Cross" if latest['ema12'] > latest['ema26'] else "Death Cross",
                    "percent_diff": round(float(abs(latest['ema12'] - latest['ema26']) / latest['ema26'] * 100), 2)
                },
                "divergence": {
                    "type": "Bullish" if latest['divergence'] == 1 else 
                           "Bearish" if latest['divergence'] == -1 else 
                           "None",
                    "strength": "Strong" if abs(latest['divergence']) == 1 else "None"
                }
            },
            "price_metrics": {
                "volatility": {
                    "daily_range": round(float(latest['daily_spread'] * 100), 2),
                    "5d_std": round(float(latest['close_5d_std']), 2),
                    "10d_std": round(float(latest['close_10d_std']), 2)
                },
                "momentum": {
                    "recent_trend": "Up" if latest['Close'] > latest['close_5d_mean'] else "Down",
                    "volume_spike": round(float(latest['volume_spike']), 2),
                    "magnitude": "Strong" if abs(latest['Close'] / latest['close_5d_mean'] - 1) > 0.05 else "Weak"
                }
            },
            "prediction_weights": {
                "technical_indicators": 65,
                "price_momentum": 25,
                "volume_analysis": 10
            },
            "best_timeframe": "Short-term" if prediction == "Bullish" and confidence > 75 else 
                           "Medium-term" if prediction == "Bullish" and 60 < confidence <= 75 else
                           "Long-term" if prediction == "Bullish" else
                           "Short-term" if prediction == "Bearish" and confidence > 75 else
                           "Wait" if prediction == "Neutral" else "Medium-term",
            "sentiment_impact": "Strong Momentum" if confidence > 80 else
                            "Building Momentum" if confidence > 65 else
                            "Mixed Signals" if confidence > 50 else
                            "Consolidating" if confidence > 30 else
                            "Trend Reversal Possible"
        }
        
        return prediction, confidence, reason, detailed_analysis
        
    except Exception as e:
        logger.error(f"Error in enhanced prediction: {str(e)}")
        # Fall back to rule-based prediction
        return rule_based_prediction(data)

def rule_based_prediction(df):
    """
    Rule-based prediction when enhanced prediction isn't possible
    
    Args:
        df: DataFrame with price and RSI data
        
    Returns:
        prediction: String prediction
        confidence: Float confidence
        reason: String explanation
    """
    try:
        # Ensure we have the basic data we need
        if df is None or len(df) < 5:
            return "Neutral", 50, "Insufficient data for prediction"
        
        # Simple price trend (last 7 days if available)
        lookback = min(7, len(df) - 1)
        
        if len(df) <= lookback:
            return "Neutral", 50, "Insufficient historical data"
            
        # Calculate recent trend
        recent_change = (df['Close'].iloc[-1] / df['Close'].iloc[-lookback - 1] - 1) * 100
            
        # Calculate RSI if not already present
        if 'rsi' not in df.columns:
            try:
                # Use ta library's RSI
                rsi_indicator = RSIIndicator(close=df['Close'])
                current_rsi = rsi_indicator.rsi().iloc[-1]
            except:
                current_rsi = 50  # Neutral if we can't calculate
        else:
            current_rsi = df['rsi'].iloc[-1]
            
        # RSI-based signals
        if current_rsi < 30:
            rsi_signal = "oversold"
            prediction = "Bullish"
            confidence = 70 + (30 - current_rsi)  # More oversold = higher confidence
        elif current_rsi > 70:
            rsi_signal = "overbought"
            prediction = "Bearish" 
            confidence = 70 + (current_rsi - 70)  # More overbought = higher confidence
        else:
            # RSI in neutral zone - use the direction
            rsi_direction = "bullish" if current_rsi > 50 else "bearish"
            rsi_signal = f"neutral-{rsi_direction}"
            
            # Use price trend to determine prediction
            if recent_change > 2:
                prediction = "Bullish"
                confidence = 50 + min(recent_change, 20)
            elif recent_change < -2:
                prediction = "Bearish"
                confidence = 50 + min(abs(recent_change), 20)
            else:
                prediction = "Neutral"
                confidence = 50 + min(abs(recent_change) * 2.5, 10)  # Slight confidence boost
        
        # Cap confidence at 95
        confidence = min(int(confidence), 95)
        
        # Create reason text
        trend_text = f"{recent_change:.1f}%" if recent_change is not None else "unknown"
        rsi_text = f"{current_rsi:.1f}" if current_rsi is not None else "unknown"
        
        reason = f"RSI: {rsi_text} | Trend: "
        
        if recent_change > 10:
            reason += f"Strong Uptrend | 7d Change: {trend_text}"
        elif recent_change > 3:
            reason += f"Uptrend | 7d Change: {trend_text}"
        elif recent_change < -10:
            reason += f"Strong Downtrend | 7d Change: {trend_text}"
        elif recent_change < -3:
            reason += f"Downtrend | 7d Change: {trend_text}"
        else:
            reason += f"Sideways | 7d Change: {trend_text}"
            
        return prediction, confidence, reason
        
    except Exception as e:
        logger.error(f"Rule-based prediction error: {str(e)}")
        return "Neutral", 50, "Error in prediction algorithm"