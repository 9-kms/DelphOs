"""
On-chain data analyzer for crypto dashboard
Analyzes blockchain data including wallet activity and whale movements
"""

import logging
import random
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Setup logging
logger = logging.getLogger(__name__)

class OnChainAnalyzer:
    """
    Analyzes on-chain data for cryptocurrencies
    Note: This is currently using simulated data. For production, would integrate with
    actual blockchain data providers like Etherscan API, Glassnode, etc.
    """
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        self.supported_chains = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'BNB': 'Binance Chain',
            'MATIC': 'Polygon',
            'SOL': 'Solana',
            'ADA': 'Cardano',
            'DOT': 'Polkadot',
            'AVAX': 'Avalanche',
            'ALGO': 'Algorand',
            'XTZ': 'Tezos'
        }
        
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
        
    def _get_chain_for_symbol(self, symbol):
        """Determine which blockchain to analyze based on symbol"""
        if symbol in self.supported_chains:
            return symbol
        elif symbol in ['WBTC', 'BTCB']:
            return 'BTC'
        elif symbol in ['WETH', 'BETH', 'UNI', 'LINK', 'AAVE', 'COMP', 'MKR', 'SNX']:
            return 'ETH'
        elif symbol in ['CAKE', 'BAKE', 'BURGER']:
            return 'BNB'
        else:
            # Default to ETH for most tokens
            return 'ETH'
    
    def _simulate_whale_activity(self, symbol, timeframe='24h'):
        """
        Simulate whale activity data based on crypto volatility patterns
        In production, this would be replaced with actual on-chain analytics
        """
        # Seed the random generator with symbol for consistent results
        random.seed(f"{symbol}_{timeframe}_{datetime.now().strftime('%Y-%m-%d')}")
        
        # Higher activity for major coins
        activity_multiplier = 2.5 if symbol in ['BTC', 'ETH'] else 1.0
        
        days = 1 if timeframe == '24h' else 7 if timeframe == '7d' else 30
        
        # Generate simulated data
        large_inflows = max(1, int(random.randrange(2, 8) * activity_multiplier))
        large_outflows = max(1, int(random.randrange(2, 7) * activity_multiplier))
        
        # More volatile coins have higher activity
        volatility_factor = 2.0 if symbol in ['SHIB', 'DOGE', 'PEPE'] else 1.0
        
        exchange_inflows = max(1, int(random.randrange(5, 15) * activity_multiplier * volatility_factor))
        exchange_outflows = max(1, int(random.randrange(4, 12) * activity_multiplier * volatility_factor))
        
        # Calculate ratio - slightly random but based on symbol characteristics
        # Bullish coins tend to have outflows > inflows (less selling pressure)
        bullish_bias = 0.2 if symbol in ['BTC', 'ETH', 'SOL'] else -0.1
        
        # Base slightly above 1.0 for positive outlook
        base_ratio = 1.0 + bullish_bias + (random.random() - 0.5) * 0.5
        inflow_outflow_ratio = max(0.3, min(2.0, base_ratio))
        
        return {
            'large_inflows': large_inflows * days,
            'large_outflows': large_outflows * days,
            'exchange_inflows': exchange_inflows * days,
            'exchange_outflows': exchange_outflows * days,
            'inflow_outflow_ratio': inflow_outflow_ratio,
            'timeframe': timeframe
        }
    
    def _simulate_wallet_activity(self, symbol, timeframe='24h'):
        """
        Simulate wallet activity metrics based on typical blockchain patterns
        In production, this would use actual blockchain data
        """
        # Seed for consistent results
        random.seed(f"{symbol}_{timeframe}_{datetime.now().strftime('%Y-%m-%d')}")
        
        # Base values depend on token popularity
        popularity_factor = 10.0 if symbol in ['BTC', 'ETH'] else \
                            5.0 if symbol in ['SOL', 'MATIC', 'ADA', 'DOT'] else 1.0
                            
        days = 1 if timeframe == '24h' else 7 if timeframe == '7d' else 30
        day_multiplier = days ** 0.8  # Non-linear scale for longer timeframes
        
        # Generate metrics
        transactions_per_day = int(random.randrange(10000, 50000) * popularity_factor)
        active_addresses = int(random.randrange(5000, 30000) * popularity_factor * (0.7 + 0.3 * day_multiplier))
        new_addresses = int(active_addresses * random.uniform(0.01, 0.05) * day_multiplier)
        
        # Transaction volume and size
        base_price = 30000 if symbol == 'BTC' else 2000 if symbol == 'ETH' else random.uniform(0.1, 50)
        transaction_volume = int(transactions_per_day * base_price * random.uniform(0.1, 0.3) * day_multiplier)
        avg_transaction_size = int(transaction_volume / transactions_per_day * random.uniform(0.8, 1.2))
        
        return {
            'transactions_per_day': transactions_per_day,
            'active_addresses': int(active_addresses),
            'new_addresses': int(new_addresses),
            'transaction_volume': int(transaction_volume),
            'avg_transaction_size': int(avg_transaction_size),
            'timeframe': timeframe
        }
        
    def get_onchain_analysis(self, symbol, timeframe='24h'):
        """
        Get comprehensive on-chain analysis for a cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            timeframe: Time period for analysis ('24h', '7d', '30d')
            
        Returns:
            Dictionary with on-chain analysis data
        """
        cache_key = f"onchain_{symbol}_{timeframe}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        try:
            chain = self._get_chain_for_symbol(symbol)
            
            # Get whale activity data
            whale_data = self._simulate_whale_activity(symbol, timeframe)
            
            # Get wallet activity data
            wallet_data = self._simulate_wallet_activity(symbol, timeframe)
            
            # Determine overall on-chain sentiment
            # Outflows > inflows is typically bullish (accumulation)
            # High new addresses is bullish (adoption)
            whale_sentiment = 'Bullish' if whale_data['exchange_outflows'] > whale_data['exchange_inflows'] else 'Bearish'
            address_growth_factor = wallet_data['new_addresses'] / wallet_data['active_addresses']
            wallet_sentiment = 'Bullish' if address_growth_factor > 0.02 else 'Neutral' if address_growth_factor > 0.01 else 'Bearish'
            
            # Calculate weighted score -100 to 100
            whale_score = (whale_data['exchange_outflows'] - whale_data['exchange_inflows']) / max(whale_data['exchange_inflows'], 1) * 50
            whale_score = max(-80, min(80, whale_score))
            
            wallet_score = (address_growth_factor - 0.015) * 1000  # Normalize around 0.015 as neutral
            wallet_score = max(-70, min(70, wallet_score))
            
            # Combined score with more weight on whale activity
            combined_score = (whale_score * 0.6) + (wallet_score * 0.4)
            combined_score = max(-100, min(100, combined_score))
            
            result = {
                'symbol': symbol,
                'blockchain': self.supported_chains.get(chain, 'Ethereum'),
                'timeframe': timeframe,
                'whale_sentiment': whale_sentiment,
                'wallet_sentiment': wallet_sentiment,
                'overall_sentiment': 'Bullish' if combined_score > 20 else 'Bearish' if combined_score < -20 else 'Neutral',
                'score': combined_score,
                'details': {
                    'whale': whale_data,
                    'wallet': wallet_data
                },
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error in on-chain analysis for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'overall_sentiment': 'Neutral',
                'score': 0,
                'error': str(e)
            }
    
    def get_whale_alerts(self, symbol, min_amount=1000000):
        """
        Get recent large transactions (whale alerts) for a cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            min_amount: Minimum transaction amount in USD
            
        Returns:
            List of whale transactions
        """
        cache_key = f"whale_alerts_{symbol}_{min_amount}"
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # This is simulated data - in production would use an API like Whale Alert
            random.seed(f"{symbol}_{datetime.now().strftime('%Y-%m-%d')}")
            
            # Number of transactions depends on the token
            tx_count = 10 if symbol in ['BTC', 'ETH'] else \
                      5 if symbol in ['SOL', 'BNB', 'MATIC'] else 2
            
            # Base transaction size depends on token value
            base_value = 50000000 if symbol == 'BTC' else \
                        5000000 if symbol == 'ETH' else \
                        1000000
            
            results = []
            now = datetime.now()
            
            for i in range(tx_count):
                # Random time in last 24 hours
                tx_time = now - timedelta(minutes=random.randint(10, 1440))
                
                # Transaction size
                amount_usd = random.randint(min_amount, base_value)
                
                # Random transaction type and source/destination
                tx_type = random.choice(['exchange_to_wallet', 'wallet_to_exchange', 'exchange_to_exchange', 'wallet_to_wallet'])
                
                exchanges = ['Binance', 'Coinbase', 'Kraken', 'FTX', 'Huobi', 'Bitfinex']
                wallets = ['Unknown Wallet', 'Whale Wallet', 'Treasury Wallet', 'Mining Pool']
                
                if 'exchange_to' in tx_type:
                    source = random.choice(exchanges)
                else:
                    source = random.choice(wallets)
                    
                if 'to_exchange' in tx_type:
                    destination = random.choice(exchanges) 
                else:
                    destination = random.choice(wallets)
                
                results.append({
                    'timestamp': tx_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'amount_usd': amount_usd,
                    'transaction_type': tx_type,
                    'source': source,
                    'destination': destination
                })
            
            self._set_cache(cache_key, results)
            return results
            
        except Exception as e:
            logger.error(f"Error getting whale alerts for {symbol}: {str(e)}")
            return []