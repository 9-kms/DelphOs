"""
News scraper and sentiment analyzer for cryptocurrency dashboard
"""

import logging
import random
import requests
import time
from datetime import datetime, timedelta
import trafilatura
from trafilatura.settings import use_config
import re

# Setup logging
logger = logging.getLogger(__name__)

# Set trafilatura configuration for better content extraction
config = use_config()
config.set("DEFAULT", "EXTRACTION_TIMEOUT", "10")

# Cache for news data
NEWS_CACHE = {}
CACHE_TTL = 3600  # 1 hour


def get_crypto_news(symbol, max_articles=10):
    """
    Get news articles for a specific cryptocurrency
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
        max_articles: Maximum number of articles to return
        
    Returns:
        List of news article dictionaries
    """
    cache_key = f"news_{symbol}_{max_articles}"
    if cache_key in NEWS_CACHE:
        timestamp, data = NEWS_CACHE[cache_key]
        if datetime.now().timestamp() - timestamp < CACHE_TTL:
            return data
    
    try:
        # In a real production environment, we would use a proper news API
        # This is a simplified implementation using simulated data
        
        # Seed the random generator with symbol for consistent results
        random.seed(f"{symbol}_news_{datetime.now().strftime('%Y-%m-%d')}")
        
        # News sources
        sources = [
            "CoinDesk", "CoinTelegraph", "Bitcoin.com", "Decrypt", 
            "The Block", "Crypto Briefing", "CryptoSlate"
        ]
        
        # News titles based on sentiment
        bullish_titles = [
            f"{symbol} Poised for Breakout as Market Sentiment Improves",
            f"{symbol} Surges After Major Partnership Announcement",
            f"Institutional Investors Flock to {symbol} Amid Market Recovery",
            f"Analysts Predict {symbol} Could Reach New Highs This Year",
            f"{symbol} Network Activity Reaches All-Time High",
            f"Major Upgrade Coming to {symbol} Blockchain",
            f"{symbol} Adoption Grows with New Exchange Listings"
        ]
        
        bearish_titles = [
            f"{symbol} Faces Selling Pressure as Whales Dump Holdings",
            f"{symbol} Drops Following Regulatory Concerns",
            f"Technical Analysis Shows {symbol} in Bearish Pattern",
            f"{symbol} Network Metrics Signal Weakness",
            f"Analysts Lower Price Targets for {symbol}",
            f"{symbol} Sentiment Turns Negative After Recent Events",
            f"Market Uncertainty Weighs on {symbol} Price"
        ]
        
        neutral_titles = [
            f"{symbol} Price Stabilizes Following Market Fluctuations",
            f"Experts Discuss {symbol}'s Long-term Potential",
            f"New Research Report Examines {symbol} Fundamentals",
            f"{symbol} Development Update: Q2 Progress",
            f"Understanding {symbol}'s Market Positioning",
            f"Is {symbol} a Good Investment? Analysts Weigh In",
            f"{symbol} Market Analysis: Trends and Patterns"
        ]
        
        # Generate random articles
        articles = []
        now = datetime.now()
        
        for i in range(max_articles):
            # Randomize publication time
            hours_ago = random.randint(1, 48)
            pub_time = now - timedelta(hours=hours_ago)
            
            # Randomly choose sentiment for the article
            sentiment_type = random.choice(['bullish', 'bearish', 'neutral'])
            
            if sentiment_type == 'bullish':
                title = random.choice(bullish_titles)
                sentiment_score = random.uniform(0.3, 0.9)
            elif sentiment_type == 'bearish':
                title = random.choice(bearish_titles)
                sentiment_score = random.uniform(-0.9, -0.3)
            else:
                title = random.choice(neutral_titles)
                sentiment_score = random.uniform(-0.2, 0.2)
                
            # Create article object
            article = {
                'title': title,
                'source': random.choice(sources),
                'published_at': pub_time.strftime('%Y-%m-%d %H:%M:%S'),
                'url': f"https://example.com/crypto/{symbol.lower()}/news/{i}",
                'summary': f"This is a simulated {sentiment_type} article about {symbol}.",
                'sentiment': 'positive' if sentiment_score > 0.2 else 'negative' if sentiment_score < -0.2 else 'neutral',
                'sentiment_score': sentiment_score
            }
            
            articles.append(article)
            
        # Cache the results
        NEWS_CACHE[cache_key] = (datetime.now().timestamp(), articles)
        return articles
        
    except Exception as e:
        logger.error(f"Error getting news for {symbol}: {str(e)}")
        return []


def get_news_sentiment_for_symbol(symbol, max_articles=10):
    """
    Get and analyze news sentiment for a specific cryptocurrency symbol
    
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
        max_articles: Maximum number of articles to analyze
        
    Returns:
        Dictionary with sentiment analysis results
    """
    # Get news articles for the symbol
    articles = get_crypto_news(symbol, max_articles)
    
    # Return the sentiment analysis
    return analyze_news_sentiment(articles)

def analyze_news_sentiment(articles):
    """
    Analyze sentiment from a list of news articles
    
    Args:
        articles: List of news article dictionaries
        
    Returns:
        Dictionary with sentiment analysis results
    """
    if not articles:
        return {
            'sentiment': 'Neutral',
            'score': 0.0
        }
    
    # Calculate average sentiment score
    total_score = sum(article.get('sentiment_score', 0) for article in articles)
    avg_score = total_score / len(articles)
    
    # Count sentiment categories
    positive_count = sum(1 for article in articles if article.get('sentiment_score', 0) > 0.2)
    negative_count = sum(1 for article in articles if article.get('sentiment_score', 0) < -0.2)
    neutral_count = len(articles) - positive_count - negative_count
    
    # Determine overall sentiment
    if avg_score > 0.2:
        sentiment = "Positive"
    elif avg_score < -0.2:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
        
    return {
        'sentiment': sentiment,
        'score': avg_score,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': neutral_count
    }


def get_website_content(url):
    """
    Get the text content of a website using trafilatura
    
    Args:
        url: URL to scrape
        
    Returns:
        Extracted text content
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch URL {url}: Status code {response.status_code}")
            return None
            
        # Extract the main content using trafilatura
        content = trafilatura.extract(response.text, config=config, include_comments=False)
        
        return content
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return None