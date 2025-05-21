"""
Routes for news sentiment analysis for the crypto dashboard
"""

import logging
from flask import jsonify, request
from datetime import datetime
from news_scraper import get_news_sentiment_for_symbol

# Setup logging
logger = logging.getLogger(__name__)

def add_news_routes(app, rate_limit_decorator, get_cached_data, set_cache, cache_duration=60*30):
    """
    Add news sentiment routes to Flask app
    """
    
    @app.route('/api/news_sentiment/<symbol>', methods=['GET'])
    @rate_limit_decorator('api_news')
    def get_news_sentiment(symbol):
        """
        Get news sentiment analysis for a cryptocurrency
        
        Parameters:
        - limit: Maximum number of articles to return (default: 5)
        - include_articles: Whether to include full article data (default: true)
        """
        try:
            # Validate symbol
            if not symbol:
                return jsonify({"error": "Symbol is required"}), 400
                
            symbol = symbol.upper()
            
            # Get parameters
            limit = int(request.args.get('limit', 5))
            include_articles = request.args.get('include_articles', 'true').lower() == 'true'
            
            # Check cache
            cache_key = f"news_sentiment_{symbol}_{limit}_{include_articles}"
            cached_data = get_cached_data(cache_key)
            
            if cached_data:
                return jsonify(cached_data)
            
            # Get news sentiment
            sentiment_data = get_news_sentiment_for_symbol(symbol, limit)
            
            # Format the response
            result = {
                "symbol": symbol,
                "sentiment": sentiment_data.get("sentiment", "Neutral"),
                "score": sentiment_data.get("score", 0),
                "article_count": sentiment_data.get("article_count", 0),
                "positive_count": sentiment_data.get("positive_count", 0),
                "negative_count": sentiment_data.get("negative_count", 0),
                "neutral_count": sentiment_data.get("neutral_count", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            # Include articles if requested
            if include_articles and "articles" in sentiment_data:
                result["articles"] = sentiment_data["articles"]
            
            # Cache the result
            set_cache(cache_key, result)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in news sentiment analysis: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    # Add combined prediction including news sentiment
    @app.route('/api/combined_analysis/<symbol>', methods=['GET'])
    @rate_limit_decorator('api_combined')
    def get_combined_analysis(symbol):
        """
        Get combined technical and news analysis for a cryptocurrency
        Integrates ML predictions with news sentiment
        """
        try:
            # First get the ML predictions
            ml_predictions = app.view_functions['get_ml_predictions']()
            ml_data = ml_predictions.json if hasattr(ml_predictions, 'json') else {}
            
            # Then get news sentiment
            news_sentiment = get_news_sentiment_for_symbol(symbol, 3)
            
            # Combine the results
            combined_score = 0
            confidence = ml_data.get("confidence", 50)
            
            # Weight the scores (70% ML predictions, 30% news sentiment)
            technical_weight = 0.7
            news_weight = 0.3
            
            # Convert ML prediction to a score (-100 to +100)
            if ml_data.get("prediction") == "Bullish":
                technical_score = confidence 
            elif ml_data.get("prediction") == "Bearish":
                technical_score = -confidence
            else:
                technical_score = 0
                
            # News sentiment is already -100 to +100
            news_score = news_sentiment.get("score", 0)
            
            # Calculate weighted combined score
            combined_score = (technical_weight * technical_score) + (news_weight * news_score)
            
            # Determine overall sentiment
            if combined_score > 60:
                overall_sentiment = "Very Bullish"
            elif combined_score > 20:
                overall_sentiment = "Bullish"
            elif combined_score > -20:
                overall_sentiment = "Neutral"
            elif combined_score > -60:
                overall_sentiment = "Bearish"
            else:
                overall_sentiment = "Very Bearish"
                
            # Calculate combined confidence
            combined_confidence = abs(int(combined_score))
            if combined_confidence > 100:
                combined_confidence = 100
                
            result = {
                "symbol": symbol,
                "overall_sentiment": overall_sentiment,
                "combined_confidence": combined_confidence,
                "technical_analysis": {
                    "prediction": ml_data.get("prediction", "Neutral"),
                    "confidence": ml_data.get("confidence", 50),
                    "reason": ml_data.get("reason", "")
                },
                "news_sentiment": {
                    "sentiment": news_sentiment.get("sentiment", "Neutral"),
                    "score": news_sentiment.get("score", 0),
                    "article_count": news_sentiment.get("article_count", 0)
                },
                "combined_score": round(combined_score, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            # Add detailed technical analysis if available
            if "detailed_analysis" in ml_data:
                result["detailed_analysis"] = ml_data["detailed_analysis"]
                
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in combined analysis: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    logger.info("News sentiment routes added successfully")
    return True