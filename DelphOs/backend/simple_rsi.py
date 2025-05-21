import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_rsi(price_series, window=14):
    """
    A simpler RSI implementation that's more robust to different data formats
    
    Args:
        price_series: Series or array-like of prices
        window: RSI calculation window (default 14)
        
    Returns:
        Series containing RSI values (with leading NaNs due to window)
    """
    try:
        # Ensure we have a pandas Series
        if not isinstance(price_series, pd.Series):
            price_series = pd.Series(price_series)
            
        # Calculate price changes
        delta = price_series.diff()
        
        # Create copy to avoid assignment warning
        up = delta.copy()
        down = delta.copy()
        
        # Separate into up and down moves
        up[up < 0] = 0
        down[down > 0] = 0
        down = down.abs()  # Make positive
        
        # Calculate rolling averages
        roll_up = up.rolling(window).mean()
        roll_down = down.rolling(window).mean()
        
        # Calculate RS and avoid division by zero
        # Handle the division more safely
        roll_down_safe = roll_down.copy()
        roll_down_safe[roll_down_safe == 0] = 1e-10
        rs = roll_up / roll_down_safe
        
        # Calculate RSI
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
        
    except Exception as e:
        logger.error(f"Error in RSI calculation: {str(e)}")
        # Return a Series of NaNs with same index as input
        return pd.Series(np.nan, index=price_series.index)