"""
Easter egg features for the crypto dashboard
"""
import logging
import random
from flask import jsonify

logger = logging.getLogger(__name__)

# Demonic quotes for the 666 easter egg
DEMONIC_QUOTES = [
    "The market will bathe in the blood of weak hands today.",
    "Your portfolio shall burn with the fires of volatility!",
    "Hodl through the darkness, and riches shall be yours.",
    "Those who sell will face eternal damnation in bear market purgatory.",
    "The charts foretell pain for those who doubt the prophecy.",
    "Bearish souls will be consumed by the green candles of doom.",
    "The crypto gods demand sacrifice! Buy high, sell low!",
    "Death crosses lead only to rebirth for the faithful HODLers.",
    "The Crypto Reaper comes for those with paper hands!",
    "Let your greed consume you as the market consumes your soul!",
    "Bulls will feast on the entrails of the bears this quarter.",
    "The damned shall rise from the depths of red candles!",
    "Liquidation is the path to enlightenment for the unworthy.",
    "Diamonds hands shall be forged in hellfire!",
    "The market manipulators have made a pact with darkness."
]

def add_easter_egg_routes(app, rate_limit_decorator):
    """
    Add easter egg routes to Flask app
    """
    
    @app.route('/api/666', methods=['GET'])
    def demonic_mode():
        """
        Easter egg: Demonic mode - returns spooky crypto insights
        """
        try:
            # Get three random demonic quotes
            selected_quotes = random.sample(DEMONIC_QUOTES, min(3, len(DEMONIC_QUOTES)))
            
            # Create top coins to predict doom for
            top_coins = ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "DOT", "AVAX", "LINK", "PEPE"]
            
            # Create demonic predictions for random coins
            demonic_predictions = []
            for _ in range(3):
                coin = random.choice(top_coins)
                top_coins.remove(coin)  # Don't predict for the same coin twice
                
                demonic_predictions.append({
                    'symbol': coin,
                    'message': random.choice(DEMONIC_QUOTES),
                    'prediction': random.choice(['DOOM', 'DESPAIR', 'BLOOD']),
                    'confidence': random.randint(66, 99)
                })
            
            # Create a demonic response
            response = {
                'mode': 'demonic',
                'timestamp': '666',
                'message': "Welcome to the Crypto Underworld!",
                'predictions': demonic_predictions,
                'warning': random.choice([
                    "Those who sell shall be cursed for 7 trading days!",
                    "The crypto gods demand sacrifice! Buy high, sell low!",
                    "HODL or be cast into the pit of eternal losses!",
                    "Whisper '666' thrice into your wallet for untold riches..."
                ]),
                'theme': {
                    'background': '#300000',
                    'text': '#ff0000',
                    'accent': '#660000',
                    'flames': True,
                    'pentagram': True
                }
            }
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"Error in demonic mode: {str(e)}")
            return jsonify({
                'mode': 'demonic',
                'error': "Even demons have technical difficulties"
            }), 500