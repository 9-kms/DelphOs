import numpy as np
import pandas as pd
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Configure logging
logger = logging.getLogger(__name__)

def generate_prediction(data):
    """
    Generate predictions based on RSI and price patterns

    Args:
        data: Pandas DataFrame with historical price data and RSI values

    Returns:
        prediction: String prediction (Bullish/Bearish/Neutral)
        confidence: Float confidence level (0-100)
        reason: String explanation for the prediction
    """
    try:
        logger.info(f"Starting prediction generation with data shape: {data.shape}")
        
        # Validate that we have the minimum required data
        if 'Close' not in data.columns:
            logger.error("Missing required price data")
            return "Neutral", 50, "Insufficient price data for prediction"
        
        # Create a working copy of the data
        df = data.copy()
        
        # Calculate RSI if not present
        if 'rsi' not in df.columns or df['rsi'].isna().all():
            logger.warning("RSI data missing or invalid, using price action only")
            # Just use recent price action for prediction
            recent_change = df['Close'].pct_change(5).iloc[-1] * 100  # 5-day change
            
            if recent_change > 5:
                return "Bearish", 60, "Recent sharp rise may lead to pullback"
            elif recent_change < -5:
                return "Bullish", 60, "Recent sharp decline may lead to bounce"
            else:
                return "Neutral", 55, "No significant recent price movement"
        
        # Calculate basic indicators from price data
        try:
            df['price_change'] = df['Close'].pct_change()
            df['price_volatility'] = df['price_change'].rolling(window=5).std()
            
            # Handle volume data if available
            if 'Volume' in df.columns and not df['Volume'].isnull().all():
                df['volume_change'] = df['Volume'].pct_change()
            else:
                df['volume_change'] = df['price_volatility']  # Use volatility as proxy
                
            # Target variable for prediction
            df['target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
            
            # Clean up any NaN values
            df = df.dropna()
            
            # Verify we still have enough data
            if len(df) < 20:
                logger.warning(f"Not enough clean data points: {len(df)}")
                return rule_based_prediction(df)
                
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            # Try rule-based prediction as fallback
            return rule_based_prediction(data)
        
        # Check if we have enough data for ML
        if len(df) < 30:
            logger.info("Using rule-based prediction due to limited data")
            return rule_based_prediction(df)
        
        # Try ML-based prediction
        try:
            # Features for our model
            features = ['rsi', 'price_volatility', 'volume_change', 'price_change']
            
            # Make sure all features exist
            for feature in features:
                if feature not in df.columns:
                    df[feature] = 0  # Default to zero if missing
            
            # Prepare data for ML
            X = df[features]
            y = df['target']
            
            # Standardize the features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train the model
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled[:-1], y[:-1], test_size=0.2, random_state=42
            )
            
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            
            # Make prediction
            latest_features = X_scaled[-1].reshape(1, -1)
            prediction_prob = model.predict_proba(latest_features)[0][1]
            
            # Convert probability to prediction
            if prediction_prob > 0.6:
                prediction = "Bullish"
                confidence = min(round(prediction_prob * 100, 1), 99.9)
                
                if df['rsi'].iloc[-1] > 70:
                    reason = "Potential Rise - Strong momentum but overbought conditions"
                else:
                    reason = "Potential Rise - Technical indicators suggest upward movement"
                    
            elif prediction_prob < 0.4:
                prediction = "Bearish"
                confidence = min(round((1 - prediction_prob) * 100, 1), 99.9)
                
                if df['rsi'].iloc[-1] < 30:
                    reason = "Potential Fall - Weak momentum with oversold conditions"
                else:
                    reason = "Potential Fall - Technical indicators suggest downward movement"
                    
            else:
                prediction = "Neutral"
                confidence = min(round(50 + abs(prediction_prob - 0.5) * 100, 1), 99.9)
                reason = "Sideways Movement - No clear directional signal"
                
            return prediction, confidence, reason
            
        except Exception as ml_error:
            logger.error(f"ML prediction failed: {str(ml_error)}")
            return rule_based_prediction(df)
            
    except Exception as e:
        logger.error(f"Unexpected error in prediction generation: {str(e)}")
        return "Neutral", 50, "Technical analysis error - insufficient data"

def rule_based_prediction(df):
    """
    Rule-based prediction when ML isn't possible
    
    Args:
        df: DataFrame with price and RSI data
        
    Returns:
        prediction: String prediction
        confidence: Float confidence
        reason: String explanation
    """
    try:
        # Use RSI if available
        if 'rsi' in df.columns and not df['rsi'].isna().all():
            last_rsi = df['rsi'].dropna().iloc[-1]
            
            if last_rsi < 30:
                return "Bullish", 70, "Oversold - Potential Reversal Upward"
            elif last_rsi > 70:
                return "Bearish", 70, "Overbought - Potential Reversal Downward"
        
        # Fall back to price action if needed
        if 'Close' in df.columns and len(df) > 5:
            # Calculate 5-day change
            price_5d_change = (df['Close'].iloc[-1] / df['Close'].iloc[-6] - 1) * 100
            
            if price_5d_change > 10:
                return "Bearish", 60, "Strong Recent Rise - Potential Pullback"
            elif price_5d_change < -10:
                return "Bullish", 60, "Strong Recent Drop - Potential Rebound"
        
        # Default if no strong signals
        return "Neutral", 50, "No Strong Technical Signals"
        
    except Exception as e:
        logger.error(f"Rule-based prediction error: {str(e)}")
        return "Neutral", 50, "Insufficient data for technical analysis"