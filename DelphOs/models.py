from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create the SQLAlchemy instance
db = SQLAlchemy()

class Watchlist(db.Model):
    """Model for user watchlists"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)  # User identifier (could be session ID, username, etc.)
    coin_symbol = db.Column(db.String(20), nullable=False)  # Cryptocurrency symbol (e.g., BTC, ETH)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)  # Optional notes about this coin
    
    # Make sure we don't have duplicate entries for the same user/coin combination
    __table_args__ = (db.UniqueConstraint('user_id', 'coin_symbol', name='uq_user_coin'),)
    
    def __repr__(self):
        return f'<Watchlist {self.user_id}: {self.coin_symbol}>'
    
    def to_dict(self):
        """Convert the model to a dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'coin_symbol': self.coin_symbol,
            'date_added': self.date_added.isoformat(),
            'notes': self.notes
        }

class PredictionHistory(db.Model):
    """Model for tracking historical prediction accuracy"""
    id = db.Column(db.Integer, primary_key=True)
    coin_symbol = db.Column(db.String(20), nullable=False)
    prediction_date = db.Column(db.DateTime, default=datetime.utcnow)
    prediction = db.Column(db.String(20), nullable=False)  # Bullish, Bearish, Neutral
    confidence = db.Column(db.Integer, nullable=False)  # Confidence percentage
    actual_direction = db.Column(db.String(20), nullable=True)  # Actual direction, filled in later
    accurate = db.Column(db.Boolean, nullable=True)  # Whether prediction was accurate, filled in later
    price_at_prediction = db.Column(db.Float, nullable=False)
    price_after_period = db.Column(db.Float, nullable=True)  # Price after prediction period
    indicators = db.Column(db.JSON, nullable=True)  # Store technical indicators as JSON
    
    def __repr__(self):
        return f'<Prediction {self.coin_symbol}: {self.prediction} ({self.confidence}%)>'
    
    def to_dict(self):
        """Convert the model to a dictionary for API responses"""
        return {
            'id': self.id,
            'coin_symbol': self.coin_symbol,
            'prediction_date': self.prediction_date.isoformat(),
            'prediction': self.prediction,
            'confidence': self.confidence,
            'actual_direction': self.actual_direction,
            'accurate': self.accurate,
            'price_at_prediction': self.price_at_prediction,
            'price_after_period': self.price_after_period,
            'indicators': self.indicators
        }