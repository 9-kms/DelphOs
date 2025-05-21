import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting prediction generation with data shape: {data.shape}")
        
        # Validate that we have RSI data
        if 'rsi' not in data.columns:
            logger.error("RSI column missing from input data")
            return "Neutral", 50, "Insufficient data for accurate prediction"
            
        # Check for valid RSI values
        valid_rsi = data['rsi'].dropna()
        if len(valid_rsi) < 10:  # Need at least 10 valid RSI datapoints
            logger.warning(f"Not enough valid RSI data points: {len(valid_rsi)}")
            return "Neutral", 50, "Insufficient RSI data for analysis"
            
        # Extract features from data
        df = data.copy()
        
        # Calculate some basic technical indicators
        df['price_change'] = df['Close'].pct_change()
        df['price_volatility'] = df['price_change'].rolling(window=5).std()
        
        # Handle volume data safely
        if 'Volume' in df.columns and not df['Volume'].isnull().all():
            df['volume_change'] = df['Volume'].pct_change()
        else:
            # If volume data is not available, use price volatility as a proxy
            logger.info("Volume data unavailable, using price volatility as proxy")
            df['volume_change'] = df['price_volatility'] 

        # Create target variable (price direction for next day)
        df['target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)

        # Drop NaN values
        original_len = len(df)
        df = df.dropna()
        logger.info(f"Rows after NaN removal: {len(df)} (removed {original_len - len(df)} rows)")

        # If we don't have enough data for ML, use rule-based approach
        if len(df) < 30:
            logger.info(f"Insufficient data points for ML model: {len(df)} rows. Using rule-based approach.")
            return rule_based_prediction(df)
            
        # Define features and target
        features = ['rsi', 'price_volatility', 'volume_change', 'price_change']
        
        # Make sure all features are available and handle any missing ones
        for feature in features:
            if feature not in df.columns:
                df[feature] = 0
        
        X = df[features]
        y = df['target']

        # Standard scale features
        scaler = StandardScaler()
        
        # Handle the case when X might be empty or have issues
        X_scaled = None
        try:
            X_scaled = scaler.fit_transform(X)
        except Exception as e:
            logger.error(f"Error scaling features: {str(e)}")
            return rule_based_prediction(df)

        # Split data (use all historical data for training)
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled[:-1], y[:-1], test_size=0.2, random_state=42
        )

        # Train a simple RandomForest model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # Make prediction for the latest data point
        latest_features = X_scaled[-1].reshape(1, -1)
        prediction_prob = model.predict_proba(latest_features)[0][1]  # Probability of price increase

        # Convert probability to prediction and confidence
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
        
    except Exception as e:
        logger.error(f"Error in prediction generation: {str(e)}")
        
        # Fall back to rule-based prediction if we have any RSI data
        if 'rsi' in data.columns and not data['rsi'].isna().all():
            logger.info("Falling back to rule-based prediction due to error")
            try:
                return rule_based_prediction(data)
            except Exception as inner_e:
                logger.error(f"Rule-based prediction also failed: {str(inner_e)}")
        
        # Last resort fallback
        return "Neutral", 50, "Technical analysis error - using conservative prediction"

def rule_based_prediction(df):
    """
    Rule-based prediction when not enough data for ML

    Args:
        df: Pandas DataFrame with historical price data and RSI

    Returns:
        prediction: String prediction
        confidence: Float confidence
        reason: String explanation
    """
    # Get latest RSI value
    rsi = df['rsi'].iloc[-1]

    # Check price trend (last 5 days)
    price_5d_change = (df['Close'].iloc[-1] / df['Close'].iloc[-6] - 1) * 100

    if rsi < 30:
        prediction = "Bullish"
        confidence = min(75 - rsi, 70)  # Lower RSI = higher confidence for bullish reversal
        reason = "Oversold - Potential Reversal Upward"
    elif rsi > 70:
        prediction = "Bearish" 
        confidence = min(rsi - 30, 70)  # Higher RSI = higher confidence for bearish reversal
        reason = "Overbought - Potential Reversal Downward"
    elif price_5d_change > 10:
        prediction = "Bearish"
        confidence = 60
        reason = "Strong Recent Rise - Potential Pullback"
    elif price_5d_change < -10:
        prediction = "Bullish"
        confidence = 60
        reason = "Strong Recent Drop - Potential Rebound"
    else:
        prediction = "Neutral"
        confidence = 50
        reason = "No Strong Technical Signals"

    return prediction, confidence, reason
