"""
Multi-signal analyzer for cryptocurrency prediction
Combines technical indicators, on-chain data, and social sentiment for comprehensive analysis
"""

import logging
import random
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from advanced_indicators import calculate_ema, calculate_macd, calculate_stochastic_rsi, check_ema_crossover, calculate_bollinger_bands
from onchain_data import OnChainAnalyzer
from social_sentiment import SocialSentimentAnalyzer

# Setup logging
logger = logging.getLogger(__name__)

class MultiSignalAnalyzer:
    """
    Advanced crypto analyzer that combines multiple signals:
    - Technical indicators (price, volume, momentum)
    - On-chain data (wallet activity, whale movements)
    - Social sentiment (Twitter, Reddit, news)
    
    Provides comprehensive analysis and predictions with configurable timeframes
    """
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes
        self.onchain_analyzer = OnChainAnalyzer()
        self.sentiment_analyzer = SocialSentimentAnalyzer()
        
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
    
    def analyze_all_signals(self, symbol, price_data, timeframe='1d'):
        """
        Analyze cryptocurrency using multiple signal sources
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            price_data: DataFrame with historical price data
            timeframe: Analysis timeframe ('1h', '1d', '1w')
            
        Returns:
            Dictionary with comprehensive analysis results
        """
        cache_key = f"multi_signal_{symbol}_{timeframe}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # Get technical analysis
            technical = self._analyze_technical_indicators(price_data)
            
            # Get on-chain data
            onchain_timeframe = '24h' if timeframe == '1h' or timeframe == '1d' else '7d'
            onchain = self.onchain_analyzer.get_onchain_analysis(symbol, timeframe=onchain_timeframe)
            
            # Get social sentiment
            social = self.sentiment_analyzer.get_combined_social_sentiment(symbol)
            
            # Calculate combined signal
            combined_score, combined_confidence, prediction, explanation = self._calculate_combined_signal(
                technical, onchain, social, timeframe
            )
            
            # Determine agreement level
            signals = [
                technical['overall_signal'],
                'Bullish' if onchain['score'] > 20 else 'Bearish' if onchain['score'] < -20 else 'Neutral',
                social['sentiment']
            ]
            
            bullish_count = sum(1 for s in signals if s == 'Bullish')
            bearish_count = sum(1 for s in signals if s == 'Bearish')
            neutral_count = sum(1 for s in signals if s == 'Neutral')
            
            if bullish_count == 3 or bearish_count == 3:
                agreement = "Strong"
            elif bullish_count >= 2 or bearish_count >= 2:
                agreement = "Moderate"
            else:
                agreement = "Weak"
                
            result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'prediction': prediction,
                'confidence': combined_confidence,
                'score': combined_score,
                'explanation': explanation,
                'agreement': agreement,
                'signals': {
                    'technical': technical,
                    'onchain': onchain,
                    'social': social
                },
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error in multi-signal analysis for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'prediction': 'Neutral',
                'confidence': 50,
                'explanation': f"Error in analysis: {str(e)}",
                'agreement': 'Unknown',
                'error': str(e)
            }
    
    def _analyze_technical_indicators(self, price_data):
        """
        Calculate technical indicators from price data
        
        Args:
            price_data: DataFrame with historical price data
            
        Returns:
            Dictionary with technical analysis results
        """
        if price_data is None or len(price_data) < 30:
            return {
                'overall_signal': 'Neutral',
                'confidence': 50,
                'explanation': 'Insufficient price data for technical analysis'
            }
            
        try:
            df = price_data.copy()
            
            # Calculate basic indicators
            # RSI (Relative Strength Index)
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            macd_line, signal_line, histogram = calculate_macd(df['Close'])
            df['MACD'] = macd_line
            df['MACD_Signal'] = signal_line
            df['MACD_Hist'] = histogram
            
            # Bollinger Bands
            middle_band, upper_band, lower_band = calculate_bollinger_bands(df['Close'])
            df['BB_Middle'] = middle_band
            df['BB_Upper'] = upper_band
            df['BB_Lower'] = lower_band
            
            # EMA Crossover
            golden_cross, death_cross = check_ema_crossover(df['Close'])
            
            # Check last valid values (avoid NaN at the end)
            latest_valid_idx = -1
            while pd.isna(df['RSI'].iloc[latest_valid_idx]) and abs(latest_valid_idx) < len(df):
                latest_valid_idx -= 1
                
            # Get the latest values
            latest_close = df['Close'].iloc[latest_valid_idx]
            latest_rsi = df['RSI'].iloc[latest_valid_idx]
            latest_macd = df['MACD'].iloc[latest_valid_idx]
            latest_macd_signal = df['MACD_Signal'].iloc[latest_valid_idx]
            latest_bb_upper = df['BB_Upper'].iloc[latest_valid_idx]
            latest_bb_lower = df['BB_Lower'].iloc[latest_valid_idx]
            
            # Analyze RSI
            rsi_signal = 'Oversold' if latest_rsi < 30 else 'Overbought' if latest_rsi > 70 else 'Neutral'
            
            # Analyze MACD
            macd_signal = 'Bullish' if latest_macd > latest_macd_signal else 'Bearish'
            
            # Analyze Bollinger Bands
            if latest_close > latest_bb_upper:
                bb_signal = 'Overbought'
            elif latest_close < latest_bb_lower:
                bb_signal = 'Oversold'
            else:
                position_in_band = (latest_close - latest_bb_lower) / (latest_bb_upper - latest_bb_lower)
                bb_signal = 'Bullish' if position_in_band > 0.6 else 'Bearish' if position_in_band < 0.4 else 'Neutral'
            
            # Calculate volumne trend
            if len(df) >= 10:
                volume_5d = df['Volume'].iloc[-5:].mean()
                volume_10d = df['Volume'].iloc[-10:].mean()
                volume_trend = 'Increasing' if volume_5d > volume_10d * 1.1 else 'Decreasing' if volume_5d < volume_10d * 0.9 else 'Stable'
            else:
                volume_trend = 'Unknown'
                
            # Check price momentum (5-day)
            if len(df) >= 5:
                price_5d_change = (df['Close'].iloc[-1] / df['Close'].iloc[-5] - 1) * 100
                momentum = 'Strong' if price_5d_change > 5 else 'Weak' if price_5d_change < -5 else 'Neutral'
            else:
                momentum = 'Unknown'
                price_5d_change = 0
                
            # Calculate weighted signal
            signals = {
                'RSI': 2 if rsi_signal == 'Oversold' else -2 if rsi_signal == 'Overbought' else 0,
                'MACD': 2 if macd_signal == 'Bullish' else -2,
                'BB': 2 if bb_signal == 'Oversold' else -2 if bb_signal == 'Overbought' else 1 if bb_signal == 'Bullish' else -1 if bb_signal == 'Bearish' else 0,
                'EMA': 3 if golden_cross else -3 if death_cross else 0,
                'Momentum': 1 if momentum == 'Strong' and price_5d_change > 0 else -1 if momentum == 'Strong' and price_5d_change < 0 else 0
            }
            
            # Calculate total signal score (-10 to 10 scale)
            signal_score = sum(signals.values())
            signal_score = max(-10, min(10, signal_score))
            
            # Convert to overall signal
            if signal_score > 3:
                overall_signal = 'Bullish'
            elif signal_score < -3:
                overall_signal = 'Bearish'
            else:
                overall_signal = 'Neutral'
                
            # Calculate confidence (50-100)
            confidence = 50 + abs(signal_score) * 5
            
            # Generate explanation
            if overall_signal == 'Bullish':
                explanation = f"Technical indicators are bullish: "
                if signals['RSI'] > 0:
                    explanation += f"RSI is oversold at {latest_rsi:.1f}, "
                if signals['MACD'] > 0:
                    explanation += f"MACD is above signal line, "
                if signals['BB'] > 0:
                    explanation += f"Price is near lower Bollinger Band, "
                if signals['EMA'] > 0:
                    explanation += f"EMA indicates golden cross, "
                if signals['Momentum'] > 0:
                    explanation += f"Price momentum is positive {price_5d_change:.1f}%, "
            elif overall_signal == 'Bearish':
                explanation = f"Technical indicators are bearish: "
                if signals['RSI'] < 0:
                    explanation += f"RSI is overbought at {latest_rsi:.1f}, "
                if signals['MACD'] < 0:
                    explanation += f"MACD is below signal line, "
                if signals['BB'] < 0:
                    explanation += f"Price is near upper Bollinger Band, "
                if signals['EMA'] < 0:
                    explanation += f"EMA indicates death cross, "
                if signals['Momentum'] < 0:
                    explanation += f"Price momentum is negative {price_5d_change:.1f}%, "
            else:
                explanation = f"Technical indicators are mixed: RSI at {latest_rsi:.1f}, "
                if latest_macd > latest_macd_signal:
                    explanation += f"MACD slightly bullish, "
                else:
                    explanation += f"MACD slightly bearish, "
                explanation += f"Price in mid Bollinger Band range."
                
            # Remove trailing comma and space
            explanation = explanation.rstrip(', ')
            
            return {
                'overall_signal': overall_signal,
                'confidence': confidence,
                'explanation': explanation,
                'indicators': {
                    'rsi': latest_rsi,
                    'rsi_signal': rsi_signal,
                    'macd': latest_macd,
                    'macd_signal_line': latest_macd_signal,
                    'macd_signal': macd_signal,
                    'bb_upper': latest_bb_upper,
                    'bb_lower': latest_bb_lower,
                    'bb_signal': bb_signal,
                    'ema_signal': 'Golden Cross' if golden_cross else 'Death Cross' if death_cross else 'Neutral',
                    'volume_trend': volume_trend,
                    'momentum': momentum,
                    'price_5d_change': price_5d_change
                },
                'signals': signals,
                'signal_score': signal_score
            }
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {str(e)}")
            return {
                'overall_signal': 'Neutral',
                'confidence': 50,
                'explanation': f"Error in technical analysis: {str(e)}"
            }
    
    def _calculate_combined_signal(self, technical, onchain, social, timeframe):
        """
        Calculate combined signal from multiple data sources
        
        Args:
            technical: Technical analysis results
            onchain: On-chain analysis results
            social: Social sentiment analysis results
            timeframe: Analysis timeframe
            
        Returns:
            Tuple of (combined_score, confidence, prediction, explanation)
        """
        # Convert signals to numeric scores
        technical_score = technical.get('signal_score', 0)  # Already -10 to 10
        
        # Onchain score is already -100 to 100, normalize to -10 to 10
        onchain_score = onchain.get('score', 0) / 10
        
        # Social score is -1 to 1, normalize to -10 to 10
        social_score = social.get('score', 0) * 10
        
        # Weights depend on timeframe
        if timeframe == '1h':
            # Short-term: technical and social matter more
            weights = {
                'technical': 0.5,
                'onchain': 0.2,
                'social': 0.3
            }
        elif timeframe == '1d':
            # Medium-term: balanced approach
            weights = {
                'technical': 0.4,
                'onchain': 0.3,
                'social': 0.3
            }
        else:  # '1w' or longer
            # Long-term: fundamentals matter more
            weights = {
                'technical': 0.3,
                'onchain': 0.5,
                'social': 0.2
            }
            
        # Calculate weighted score
        combined_score = (
            technical_score * weights['technical'] +
            onchain_score * weights['onchain'] +
            social_score * weights['social']
        )
        
        # Determine prediction
        if combined_score > 2:
            prediction = 'Bullish'
        elif combined_score < -2:
            prediction = 'Bearish'
        else:
            prediction = 'Neutral'
            
        # Calculate confidence based on:
        # 1. The absolute score (stronger signal = higher confidence)
        # 2. Agreement between signals (more agreement = higher confidence)
        
        # Base confidence from score magnitude
        score_confidence = 50 + abs(combined_score) * 5
        
        # Check signal agreement
        signals = [
            'Bullish' if technical_score > 3 else 'Bearish' if technical_score < -3 else 'Neutral',
            'Bullish' if onchain_score > 3 else 'Bearish' if onchain_score < -3 else 'Neutral',
            'Bullish' if social_score > 3 else 'Bearish' if social_score < -3 else 'Neutral'
        ]
        
        bullish_count = sum(1 for s in signals if s == 'Bullish')
        bearish_count = sum(1 for s in signals if s == 'Bearish')
        
        # Calculate agreement factor (0-20 additional points)
        if bullish_count == 3 or bearish_count == 3:
            # All agree
            agreement_bonus = 20
        elif bullish_count >= 2 or bearish_count >= 2:
            # Two agree
            agreement_bonus = 10
        else:
            # All different or mostly neutral
            agreement_bonus = 0
            
        # Final confidence score
        combined_confidence = min(100, score_confidence + agreement_bonus)
        
        # Generate explanation text
        explanation = f"{timeframe.upper()} Forecast: {prediction} with {combined_confidence}% confidence. "
        
        if prediction == 'Bullish':
            explanation += "Positive signals from "
            signals_text = []
            if technical_score > 0:
                signals_text.append(f"technical indicators ({technical['explanation']})")
            if onchain_score > 0:
                signals_text.append(f"on-chain data (exchange outflows suggest accumulation)")
            if social_score > 0:
                signals_text.append(f"social sentiment ({social['agreement']} agreement across platforms)")
                
            explanation += ", ".join(signals_text)
            
        elif prediction == 'Bearish':
            explanation += "Negative signals from "
            signals_text = []
            if technical_score < 0:
                signals_text.append(f"technical indicators ({technical['explanation']})")
            if onchain_score < 0:
                signals_text.append(f"on-chain data (increasing exchange inflows suggest distribution)")
            if social_score < 0:
                signals_text.append(f"social sentiment ({social['agreement']} agreement across platforms)")
                
            explanation += ", ".join(signals_text)
            
        else:
            explanation += "Mixed signals: "
            if abs(technical_score) < 3:
                explanation += f"Technical indicators are neutral. "
            if abs(onchain_score) < 3:
                explanation += f"On-chain metrics show no clear trend. "
            if abs(social_score) < 3:
                explanation += f"Social sentiment is balanced. "
                
        return combined_score, combined_confidence, prediction, explanation
        
    def get_scenario_analysis(self, symbol, price_data, scenario_type):
        """
        Perform scenario analysis for different market conditions
        
        Args:
            symbol: Cryptocurrency symbol
            price_data: Historical price data
            scenario_type: Type of scenario ('bull', 'bear', 'sideways')
            
        Returns:
            Dictionary with scenario analysis
        """
        cache_key = f"scenario_{symbol}_{scenario_type}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # Baseline prediction
            baseline = self.analyze_all_signals(symbol, price_data, timeframe='1d')
            
            # Scenario parameters
            if scenario_type == 'bull':
                scenario_name = "Bullish Market Scenario"
                description = "Simulating a strong market uptrend with increased buying pressure"
                market_condition = "Bitcoin above $40K, market sentiment positive, increasing institutional adoption"
                # For bull scenario, we amplify positive signals and reduce negative ones
                modified_confidence = min(100, baseline['confidence'] + 20)
                price_change = random.uniform(15, 40)  # 15-40% price increase potential
                
            elif scenario_type == 'bear':
                scenario_name = "Bearish Market Scenario"
                description = "Simulating a market downturn with increased selling pressure"
                market_condition = "Bitcoin below $30K, regulatory concerns, institutional outflows"
                # For bear scenario, we amplify negative signals and reduce positive ones
                modified_confidence = min(100, baseline['confidence'] + 15)
                price_change = random.uniform(-35, -10)  # 10-35% price decrease potential
                
            else:  # sideways
                scenario_name = "Sideways Market Scenario"
                description = "Simulating a range-bound market with low volatility"
                market_condition = "Bitcoin consolidating, reduced market volatility, balanced flows"
                # For sideways, we reduce overall confidence
                modified_confidence = max(50, baseline['confidence'] - 15)
                price_change = random.uniform(-7, 7)  # -7% to +7% price change
            
            # Calculate potential price targets
            current_price = price_data['Close'].iloc[-1]
            target_price = current_price * (1 + price_change/100)
            
            # Generate timeframes
            if price_data is not None and len(price_data) >= 30:
                price_volatility = price_data['Close'].pct_change().std() * 100
            else:
                price_volatility = 3.5  # Default if we don't have enough data
                
            # Adjust timeframes based on volatility and scenario
            if scenario_type == 'bull':
                timeframe_days = int(max(7, min(45, 15 + 30 * (100 - modified_confidence)/100)))
            elif scenario_type == 'bear':
                timeframe_days = int(max(5, min(30, 10 + 20 * (100 - modified_confidence)/100)))
            else:
                timeframe_days = int(max(14, min(60, 30 + 30 * (100 - modified_confidence)/100)))
                
            # Key resistance and support levels (simplified)
            if scenario_type == 'bull':
                key_levels = {
                    'strong_resistance': current_price * 1.2,
                    'weak_resistance': current_price * 1.1,
                    'weak_support': current_price * 0.95,
                    'strong_support': current_price * 0.9
                }
            elif scenario_type == 'bear':
                key_levels = {
                    'strong_resistance': current_price * 1.1,
                    'weak_resistance': current_price * 1.03,
                    'weak_support': current_price * 0.85,
                    'strong_support': current_price * 0.7
                }
            else:
                key_levels = {
                    'strong_resistance': current_price * 1.07,
                    'weak_resistance': current_price * 1.03,
                    'weak_support': current_price * 0.97,
                    'strong_support': current_price * 0.93
                }
                
            # Format the explanation text
            if scenario_type == 'bull':
                explanation = (
                    f"In a bullish market scenario where {market_condition}, "
                    f"{symbol} could potentially rise {price_change:.1f}% to a target of ${target_price:.2f} "
                    f"over the next {timeframe_days} days. Watch for resistance at ${key_levels['weak_resistance']:.2f} "
                    f"and ${key_levels['strong_resistance']:.2f}. Support levels at ${key_levels['weak_support']:.2f} "
                    f"and ${key_levels['strong_support']:.2f} should hold in this scenario."
                )
            elif scenario_type == 'bear':
                explanation = (
                    f"In a bearish market scenario where {market_condition}, "
                    f"{symbol} could potentially fall {abs(price_change):.1f}% to a target of ${target_price:.2f} "
                    f"over the next {timeframe_days} days. Support levels at ${key_levels['weak_support']:.2f} "
                    f"and ${key_levels['strong_support']:.2f} will be critical. Any recovery would face "
                    f"resistance at ${key_levels['weak_resistance']:.2f} and ${key_levels['strong_resistance']:.2f}."
                )
            else:
                explanation = (
                    f"In a sideways market scenario where {market_condition}, "
                    f"{symbol} is likely to remain range-bound with potential fluctuations of {abs(price_change):.1f}% "
                    f"around ${current_price:.2f} over the next {timeframe_days} days. "
                    f"Expect resistance at ${key_levels['weak_resistance']:.2f} and support at ${key_levels['weak_support']:.2f}, "
                    f"with the price likely to remain within this channel in low volatility conditions."
                )
            
            result = {
                'symbol': symbol,
                'scenario': scenario_name,
                'description': description,
                'market_condition': market_condition,
                'prediction': 'Bullish' if price_change > 5 else 'Bearish' if price_change < -5 else 'Neutral',
                'confidence': modified_confidence,
                'current_price': current_price,
                'target_price': target_price,
                'price_change_pct': price_change,
                'timeframe_days': timeframe_days,
                'explanation': explanation,
                'key_levels': key_levels,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error in scenario analysis for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'scenario': scenario_type.capitalize() + " Market Scenario",
                'prediction': 'Neutral',
                'confidence': 50,
                'explanation': f"Error in scenario analysis: {str(e)}",
                'error': str(e)
            }