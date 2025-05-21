"""
Social sentiment analyzer for cryptocurrency dashboard
Analyzes sentiment from Twitter, Reddit, and other social platforms
"""

import logging
import random
import time
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from news_scraper import analyze_news_sentiment, get_crypto_news

# Setup logging
logger = logging.getLogger(__name__)

class SocialSentimentAnalyzer:
    """
    Analyzes social media sentiment for cryptocurrencies
    Note: This is currently using simulated data. For production, would integrate with
    actual social media APIs like Twitter API, Reddit API, etc.
    """
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
    def _get_cached_data(self, cache_key):
        """Get data from cache if not expired"""
        if cache_key in self.cache:
            timestamp, data = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                return data
        return None
        
    def _set_cache(self, cache_key, data):
        """Store data in cache with timestamp"""
        self.cache[cache_key] = (datetime.now().timestamp(), data)
    
    def _simulate_twitter_sentiment(self, symbol):
        """
        Simulate Twitter sentiment data
        In production, this would be replaced with actual Twitter API integration
        """
        # Seed the random generator with symbol for consistent results
        random.seed(f"{symbol}_twitter_{datetime.now().strftime('%Y-%m-%d')}")
        
        # Sentiment is based on coin popularity and recent performance
        # More popular coins tend to have more positive sentiment
        popularity_factor = 0.2 if symbol in ['BTC', 'ETH'] else \
                          0.1 if symbol in ['SOL', 'BNB', 'MATIC'] else 0
        
        # Random sentiment baseline with slight positive bias for popular coins
        base_sentiment = random.uniform(-0.5, 0.5) + popularity_factor
        sentiment_score = max(-1.0, min(1.0, base_sentiment))
        
        # Determine the sentiment category
        if sentiment_score > 0.2:
            sentiment = "Positive"
        elif sentiment_score < -0.2:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        # Generate tweet counts based on coin popularity
        tweet_factor = 10 if symbol in ['BTC', 'ETH'] else \
                      5 if symbol in ['SOL', 'BNB', 'MATIC', 'ADA', 'DOT'] else 2
        
        tweet_count = int(random.randrange(50, 200) * tweet_factor)
        
        # Distribute sentiment
        positive_pct = max(10, min(80, 50 + int(sentiment_score * 40)))
        negative_pct = max(10, min(80, 50 - int(sentiment_score * 30)))
        neutral_pct = 100 - positive_pct - negative_pct
        
        positive_count = int(tweet_count * positive_pct / 100)
        negative_count = int(tweet_count * negative_pct / 100)
        neutral_count = tweet_count - positive_count - negative_count
        
        return {
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'tweet_count': tweet_count,
            'positive_count': positive_count,
            'neutral_count': neutral_count,
            'negative_count': negative_count,
            'trending_hashtags': [
                f"#{symbol}", 
                f"#{symbol}coin", 
                "#crypto", 
                "#cryptocurrency",
                f"#{symbol.lower()}army" if sentiment_score > 0.3 else "#trading"
            ]
        }
    
    def _simulate_reddit_sentiment(self, symbol):
        """
        Simulate Reddit sentiment data
        In production, this would be replaced with actual Reddit API integration
        """
        # Seed the random generator with symbol for consistent results
        random.seed(f"{symbol}_reddit_{datetime.now().strftime('%Y-%m-%d')}")
        
        # Sentiment is slightly more extreme on Reddit
        sentiment_score = random.uniform(-0.8, 0.8)
        
        # Determine the sentiment category
        if sentiment_score > 0.2:
            sentiment = "Positive"
        elif sentiment_score < -0.2:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        # Generate post and comment counts
        popularity_factor = 5 if symbol in ['BTC', 'ETH'] else \
                          3 if symbol in ['SOL', 'BNB', 'MATIC', 'ADA', 'DOT'] else 1
        
        post_count = int(random.randrange(10, 50) * popularity_factor)
        comment_count = post_count * random.randrange(5, 20)
        
        # Reddit-specific metrics
        upvote_ratio = max(0.5, min(0.95, 0.7 + (sentiment_score * 0.2)))
        
        # Top subreddits
        subreddits = [f"r/{symbol}", "r/cryptocurrency", "r/CryptoMarkets"]
        if symbol == 'BTC':
            subreddits = ["r/Bitcoin", "r/CryptoCurrency", "r/BitcoinMarkets"]
        elif symbol == 'ETH':
            subreddits = ["r/ethereum", "r/CryptoCurrency", "r/ethtrader"]
            
        # Hot topics
        if sentiment_score > 0.3:
            hot_topics = ["Bull run", "To the moon", "Hodl", "Price prediction"]
        elif sentiment_score < -0.3:
            hot_topics = ["Bear market", "Price drop", "Selling", "Concerns"]
        else:
            hot_topics = ["Technical analysis", "News", "Development", "Adoption"]
            
        return {
            'sentiment': sentiment,
            'sentiment_score': sentiment_score,
            'post_count': post_count,
            'comment_count': comment_count,
            'upvote_ratio': upvote_ratio,
            'subreddits': subreddits,
            'hot_topics': hot_topics
        }
        
    def _get_news_sentiment(self, symbol):
        """
        Get sentiment from news articles
        This integrates with our existing news_scraper module
        """
        try:
            # Try to get real news data
            news = get_crypto_news(symbol, max_articles=10)
            if news and len(news) > 0:
                sentiment = analyze_news_sentiment(news)
                return {
                    'sentiment': sentiment['sentiment'],
                    'score': sentiment['score'],
                    'article_count': len(news),
                    'sources': list(set([article['source'] for article in news[:5]]))
                }
        except Exception as e:
            logger.error(f"Error getting news sentiment for {symbol}: {str(e)}")
            
        # Fallback to simulated data if real data not available
        random.seed(f"{symbol}_news_{datetime.now().strftime('%Y-%m-%d')}")
        
        sentiment_score = random.uniform(-0.7, 0.7)
        
        # Determine the sentiment category
        if sentiment_score > 0.2:
            sentiment = "Positive"
        elif sentiment_score < -0.2:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        return {
            'sentiment': sentiment,
            'score': sentiment_score,
            'article_count': random.randint(5, 20),
            'sources': ["CoinDesk", "CoinTelegraph", "Bitcoin.com", "Decrypt", "The Block"]
        }
        
    def get_twitter_sentiment(self, symbol, limit=100):
        """
        Get Twitter sentiment for a cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            limit: Maximum number of tweets to analyze
            
        Returns:
            Dictionary with Twitter sentiment analysis
        """
        cache_key = f"twitter_sentiment_{symbol}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # In production, this would use the Twitter API
            sentiment_data = self._simulate_twitter_sentiment(symbol)
            self._set_cache(cache_key, sentiment_data)
            return sentiment_data
        except Exception as e:
            logger.error(f"Error getting Twitter sentiment for {symbol}: {str(e)}")
            return {
                'sentiment': 'Neutral',
                'sentiment_score': 0,
                'error': str(e)
            }
    
    def get_reddit_sentiment(self, symbol, limit=50):
        """
        Get Reddit sentiment for a cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            limit: Maximum number of posts to analyze
            
        Returns:
            Dictionary with Reddit sentiment analysis
        """
        cache_key = f"reddit_sentiment_{symbol}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # In production, this would use the Reddit API
            sentiment_data = self._simulate_reddit_sentiment(symbol)
            self._set_cache(cache_key, sentiment_data)
            return sentiment_data
        except Exception as e:
            logger.error(f"Error getting Reddit sentiment for {symbol}: {str(e)}")
            return {
                'sentiment': 'Neutral',
                'sentiment_score': 0,
                'error': str(e)
            }
            
    def get_combined_social_sentiment(self, symbol):
        """
        Get combined social sentiment from Twitter, Reddit, and news sources
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            Dictionary with comprehensive social sentiment analysis
        """
        cache_key = f"combined_sentiment_{symbol}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # Get sentiment from different sources
            twitter_data = self.get_twitter_sentiment(symbol)
            reddit_data = self.get_reddit_sentiment(symbol)
            news_data = self._get_news_sentiment(symbol)
            
            # Calculate weighted score
            twitter_weight = 0.4
            reddit_weight = 0.3
            news_weight = 0.3
            
            weighted_score = (
                twitter_data['sentiment_score'] * twitter_weight +
                reddit_data['sentiment_score'] * reddit_weight +
                news_data['score'] * news_weight
            )
            
            # Determine agreement level across platforms
            scores = [
                twitter_data['sentiment_score'],
                reddit_data['sentiment_score'],
                news_data['score']
            ]
            
            # Check if all sources are in the same direction (all positive or all negative)
            all_positive = all(score > 0.1 for score in scores)
            all_negative = all(score < -0.1 for score in scores)
            strong_agreement = all_positive or all_negative
            
            # Check if at least 2 sources agree in direction
            moderate_agreement = (sum(1 for score in scores if score > 0.1) >= 2) or \
                                (sum(1 for score in scores if score < -0.1) >= 2)
            
            # Final sentiment categorization
            if weighted_score > 0.2:
                sentiment = "Bullish"
            elif weighted_score < -0.2:
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
                
            # Calculate sentiment strength (0-100)
            sentiment_strength = int(abs(weighted_score) * 100)
            sentiment_strength = min(100, max(20, sentiment_strength))
            
            result = {
                'symbol': symbol,
                'sentiment': sentiment,
                'score': weighted_score,
                'strength': sentiment_strength,
                'agreement': 'Strong' if strong_agreement else 'Moderate' if moderate_agreement else 'Weak',
                'twitter_sentiment': twitter_data['sentiment'],
                'reddit_sentiment': reddit_data['sentiment'],
                'news_sentiment': news_data['sentiment'],
                'details': {
                    'twitter': twitter_data,
                    'reddit': reddit_data,
                    'news': news_data
                },
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error in combined sentiment analysis for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'sentiment': 'Neutral',
                'score': 0,
                'strength': 50,
                'agreement': 'Unknown',
                'error': str(e)
            }