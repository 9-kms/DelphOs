import React, { useState, useEffect } from 'react';
import Terminal from './components/Terminal';
import Watchlist from './components/Watchlist';
import CoinChart from './components/CoinChart';
import './styles.css';

function App() {
  const [coins, setCoins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [logs, setLogs] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [favorites, setFavorites] = useState([]);
  const [watchlistItems, setWatchlistItems] = useState([]);
  const [activeView, setActiveView] = useState('all'); // 'all' or 'watchlist'
  const [selectedCoin, setSelectedCoin] = useState(null);

  // Add a new log message
  const addLog = (message, type = 'info') => {
    const newLog = {
      id: Date.now(),
      message,
      type,
      timestamp: new Date().toLocaleTimeString()
    };
    
    setLogs(prevLogs => [...prevLogs, newLog]);
    
    // Keep only the latest 50 logs
    if (logs.length > 50) {
      setLogs(prevLogs => prevLogs.slice(prevLogs.length - 50));
    }
  };

  // Fetch all coins data
  const fetchCoins = async (silent = false) => {
    try {
      setRefreshing(true);
      if (!silent) {
        addLog('Fetching latest cryptocurrency data...', 'info');
      }
      
      const apiBase = window.API_BASE_URL || 'http://localhost:5001';
      const response = await fetch(`${apiBase}/api/coins`);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Compare with existing data to mark updated prices
      if (coins.length > 0) {
        const updatedData = data.map(newCoin => {
          const oldCoin = coins.find(c => c.symbol === newCoin.symbol);
          if (oldCoin && oldCoin.price !== newCoin.price) {
            // Mark this coin as having a price update
            return {
              ...newCoin,
              lastUpdate: Date.now()
            };
          }
          return newCoin;
        });
        setCoins(updatedData);
      } else {
        setCoins(data);
      }
      
      if (!silent) {
        addLog(`Successfully fetched data for ${data.length} cryptocurrencies.`, 'success');
      }
    } catch (err) {
      setError(err.message);
      if (!silent) {
        addLog(`Error fetching coins: ${err.message}`, 'error');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Get ML prediction for a specific coin
  const fetchPrediction = async (coinId, symbol) => {
    try {
      addLog(`Generating ML prediction for ${symbol}...`, 'info');
      
      const apiBase = window.API_BASE_URL || 'http://localhost:5001';
      const response = await fetch(`${apiBase}/api/ml_predictions?coin=${symbol}`);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const predictionData = await response.json();
      
      // Update the coins array with the enhanced prediction data
      setCoins(prevCoins => 
        prevCoins.map(coin => 
          coin.symbol === symbol 
            ? { 
                ...coin, 
                prediction: predictionData.prediction, 
                confidence: predictionData.confidence,
                reason: predictionData.reason,
                rsi: predictionData.current_rsi,
                // Add advanced indicators if available
                stochastic_rsi: predictionData.stochastic_rsi,
                macd_signal: predictionData.macd_signal,
                ema_position: predictionData.ema_position
              } 
            : coin
        )
      );
      
      addLog(`Prediction generated for ${symbol}: ${predictionData.prediction} (${predictionData.confidence}%)`, 'success');
      return predictionData;
    } catch (err) {
      addLog(`Error generating prediction for ${symbol}: ${err.message}`, 'error');
      return null;
    }
  };

  // Search for coins
  const searchCoins = async (query) => {
    try {
      const apiBase = window.API_BASE_URL || 'http://localhost:5001';
      const response = await fetch(`${apiBase}/api/search?q=${encodeURIComponent(query)}`);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      return await response.json();
    } catch (err) {
      addLog(`Search error: ${err.message}`, 'error');
      return [];
    }
  };

  // Fetch popular DexScreener tokens including CloudyHeart
  const fetchPopularDexTokens = async () => {
    try {
      addLog('Fetching popular tokens from DexScreener...', 'info');
      
      const apiBase = window.API_BASE_URL || 'http://localhost:5001';
      const response = await fetch(`${apiBase}/api/dex/popular`);
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data && data.tokens && data.tokens.length > 0) {
        // Add the special tokens to our coins array
        const dexTokens = data.tokens.map(token => ({
          id: token.address || `dex-${token.symbol}`,
          symbol: token.symbol,
          name: token.name,
          price: token.price || 0,
          price_change_24h: token.price_change_24h || 0,
          volume: token.volume_24h || 0,
          is_dex_token: true,
          dexscreener_url: token.dexscreener_url,
          source: token.source || 'dexscreener',
          is_special: token.is_special || false,
          chain: token.chain || 'ethereum'
        }));
        
        // Only add tokens that aren't already in the list
        const existingSymbols = new Set(coins.map(c => c.symbol));
        const newTokens = dexTokens.filter(token => !existingSymbols.has(token.symbol));
        
        if (newTokens.length > 0) {
          setCoins(prevCoins => [...prevCoins, ...newTokens]);
          addLog(`Added ${newTokens.length} popular DexScreener tokens including CloudyHeart`, 'success');
        } else {
          addLog('No new DexScreener tokens to add', 'info');
        }
      } else {
        addLog('No popular tokens found on DexScreener', 'warning');
      }
    } catch (err) {
      addLog(`Error fetching popular DexScreener tokens: ${err.message}`, 'error');
    }
  };

  // Handle command inputs
  const handleCommand = async (command) => {
    const trimmedCommand = command.trim().toLowerCase();
    
    if (trimmedCommand === 'help') {
      addLog('Available commands:', 'info');
      addLog('- help: Show this help message', 'info');
      addLog('- refresh: Refresh coin data', 'info');
      addLog('- predict <symbol>: Generate prediction for a specific coin', 'info');
      addLog('- clear: Clear the terminal logs', 'info');
      addLog('- watchlist: Toggle between all coins and your watchlist', 'info');
      addLog('- star <symbol>: Add or remove a coin from your watchlist', 'info');
      addLog('- dexscreen <token>: Search for token on DexScreener', 'info');
      addLog('- cloudy: Show special token CloudyHeart information', 'info');
      addLog('- dextokens: Fetch popular tokens from DexScreener', 'info');
      addLog('- 666: Easter egg - activate demonic mode', 'info');
      return;
    }
    
    if (trimmedCommand === 'refresh') {
      await fetchCoins();
      return;
    }
    
    if (trimmedCommand === 'dextokens') {
      await fetchPopularDexTokens();
      return;
    }
    
    if (trimmedCommand === 'cloudy') {
      addLog('Fetching CloudyHeart token information...', 'info');
      await fetchPopularDexTokens();
      
      const cloudyToken = coins.find(c => c.symbol === 'CLOUDY');
      if (cloudyToken) {
        addLog('CloudyHeart (CLOUDY) Information:', 'success');
        addLog(`Current Price: $${cloudyToken.price ? cloudyToken.price.toFixed(6) : 'Unknown'}`, 'info');
        addLog(`24h Change: ${cloudyToken.price_change_24h ? cloudyToken.price_change_24h.toFixed(2) + '%' : 'Unknown'}`, 'info');
        addLog(`Chain: ${cloudyToken.chain || 'Ethereum'}`, 'info');
        
        if (cloudyToken.dexscreener_url) {
          addLog(`DexScreener Link: ${cloudyToken.dexscreener_url}`, 'info');
        }
        
        addLog('Use "predict CLOUDY" for ML prediction on CloudyHeart', 'info');
      } else {
        addLog('CloudyHeart token not found. Trying to fetch it...', 'warning');
        await fetchPopularDexTokens();
      }
      return;
    }
    
    if (trimmedCommand === 'clear') {
      setLogs([]);
      return;
    }
    
    if (trimmedCommand === 'watchlist') {
      setActiveView(prev => prev === 'all' ? 'watchlist' : 'all');
      addLog(`Switched to ${activeView === 'all' ? 'watchlist' : 'all coins'} view`, 'info');
      return;
    }

    if (trimmedCommand.startsWith('star ')) {
      const symbol = trimmedCommand.split(' ')[1].toUpperCase();
      const coin = coins.find(c => c.symbol === symbol);
      
      if (coin) {
        toggleFavorite(symbol);
      } else {
        addLog(`Coin ${symbol} not found. Try searching for it first.`, 'error');
      }
      return;
    }
    
    if (trimmedCommand.startsWith('predict ')) {
      const symbol = trimmedCommand.split(' ')[1].toUpperCase();
      const coin = coins.find(c => c.symbol === symbol);
      
      if (coin) {
        setSelectedCoin({ id: coin.id, symbol });
        await fetchPrediction(coin.id, symbol);
      } else {
        addLog(`Coin ${symbol} not found. Try searching for it first.`, 'error');
      }
      return;
    }

    if (trimmedCommand.startsWith('dexscreen ')) {
      const query = trimmedCommand.split(' ')[1];
      addLog(`Searching DexScreener for ${query}...`, 'info');
      
      try {
        const apiBase = window.API_BASE_URL || 'http://localhost:5001';
        const response = await fetch(`${apiBase}/api/search_dex?q=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        
        const dexData = await response.json();
        
        if (dexData && dexData.length > 0) {
          addLog(`Found ${dexData.length} results on DexScreener:`, 'success');
          dexData.slice(0, 5).forEach(token => {
            addLog(`${token.name} (${token.symbol}) - $${token.price} | Chain: ${token.chain}`, 'info');
          });
        } else {
          addLog(`No results found on DexScreener for ${query}`, 'warning');
        }
      } catch (err) {
        addLog(`DexScreener search error: ${err.message}`, 'error');
      }
      return;
    }
    
    // Easter egg - Demonic Mode with server-side integration
    if (trimmedCommand === '666') {
      addLog('**DEMONIC MODE ACTIVATED**', 'error');
      document.body.classList.add('demonic-mode');
      
      // Fetch demonic predictions from the backend Easter egg API
      try {
        const apiBase = window.API_BASE_URL || 'http://localhost:5001';
        const response = await fetch(`${apiBase}/api/666`);
        
        if (response.ok) {
          const demonicData = await response.json();
          
          // Display demonic predictions
          addLog('👹 THE CRYPTO ORACLE OF DARKNESS SPEAKS...', 'error');
          
          if (demonicData && demonicData.predictions) {
            demonicData.predictions.forEach(prediction => {
              addLog(`${prediction.symbol}: ${prediction.message}`, 'error');
            });
            
            if (demonicData.warning) {
              addLog(`WARNING: ${demonicData.warning}`, 'error');
            }
          }
        }
      } catch (err) {
        // Even if the API call fails, still show local demonic mode
        addLog('THE DARK POWERS ARE STIRRING...', 'error');
      }
      
      // Create flashing effect for demonic mode
      let flashCount = 0;
      const flashInterval = setInterval(() => {
        document.body.classList.toggle('demonic-flash');
        flashCount++;
        if (flashCount > 6) {
          clearInterval(flashInterval);
          document.body.classList.remove('demonic-flash');
          document.body.classList.remove('demonic-mode');
        }
      }, 500);
      
      return;
    }
    
    addLog(`Unknown command: ${command}. Type 'help' for available commands.`, 'error');
  };

  // Fetch watchlist from the server
  const fetchWatchlist = async () => {
    try {
      const apiBase = window.API_BASE_URL || 'http://localhost:5001';
      const response = await fetch(`${apiBase}/api/watchlist`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch watchlist');
      }
      
      const data = await response.json();
      setWatchlistItems(data.coins || []);
      
      // Extract just the symbols for filtering
      const symbols = (data.coins || []).map(item => item.coin_symbol);
      setFavorites(symbols);
    } catch (err) {
      console.error('Error fetching watchlist:', err);
      addLog(`Error fetching watchlist: ${err.message}`, 'error');
    }
  };

  // Initial data fetch
  useEffect(() => {
    addLog('Initializing DelphOs Terminal...', 'info');
    addLog('Welcome to DelphOs Crypto Terminal v1.0', 'info');
    addLog('Type "help" for available commands.', 'info');
    
    // Fetch main coins first
    fetchCoins().then(() => {
      // Then fetch special tokens like CloudyHeart
      fetchPopularDexTokens();
    });
    
    fetchWatchlist();
  }, []);

  // Toggle a coin in the favorites list using the database API
  const toggleFavorite = async (symbol) => {
    try {
      const apiBase = window.API_BASE_URL || 'http://localhost:5001';
      
      if (favorites.includes(symbol)) {
        // Remove from watchlist
        const response = await fetch(`${apiBase}/api/watchlist/${symbol}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error(`Failed to remove ${symbol} from watchlist`);
        }
        
        addLog(`Removed ${symbol} from watchlist`, 'info');
      } else {
        // Add to watchlist
        const response = await fetch(`${apiBase}/api/watchlist/${symbol}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            notes: `Added on ${new Date().toLocaleDateString()}`
          })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to add ${symbol} to watchlist`);
        }
        
        addLog(`Added ${symbol} to watchlist`, 'success');
      }
      
      // Refresh the watchlist from the server
      fetchWatchlist();
    } catch (err) {
      console.error('Error updating watchlist:', err);
      addLog(`Error updating watchlist: ${err.message}`, 'error');
    }
  };

  // Auto-refresh data every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchCoins(true); // Silent update to avoid log spam
    }, 60000); // 60 seconds
    
    return () => clearInterval(interval);
  }, []);

  // Handle 666 search Easter egg with server-side demonic mode
  const handleSearchQuery = async (query) => {
    if (query === '666') {
      addLog('**DEMONIC MODE ACTIVATED**', 'error');
      document.body.classList.add('demonic-mode');
      
      // Fetch demonic predictions from the backend Easter egg API
      try {
        const apiBase = window.API_BASE_URL || 'http://localhost:5001';
        const response = await fetch(`${apiBase}/api/666`);
        
        if (response.ok) {
          const demonicData = await response.json();
          
          // Display demonic predictions
          addLog('👹 THE CRYPTO ORACLE OF DARKNESS SPEAKS...', 'error');
          
          if (demonicData && demonicData.predictions) {
            demonicData.predictions.forEach(prediction => {
              addLog(`${prediction.symbol}: ${prediction.message}`, 'error');
            });
            
            if (demonicData.warning) {
              addLog(`WARNING: ${demonicData.warning}`, 'error');
            }
          }
        }
      } catch (err) {
        // Even if the API call fails, still show local demonic mode
        addLog('THE DARK POWERS ARE STIRRING...', 'error');
      }
      
      // Create flashing effect for demonic mode
      let flashCount = 0;
      const flashInterval = setInterval(() => {
        document.body.classList.toggle('demonic-flash');
        flashCount++;
        if (flashCount > 6) {
          clearInterval(flashInterval);
          document.body.classList.remove('demonic-flash');
          document.body.classList.remove('demonic-mode');
        }
      }, 500);
      
      return [];
    }
    return searchCoins(query);
  };

  return (
    <div className="app-container">
      <div className="terminal-header">
        <div className="terminal-title">
          <span>DelphOs</span>
          <span style={{ marginLeft: '10px', color: 'var(--terminal-dim)' }}>v1.0</span>
        </div>
        <div className="view-switcher">
          <button 
            className={activeView === 'all' ? 'active' : ''}
            onClick={() => setActiveView('all')}
          >
            All Coins
          </button>
          <button 
            className={activeView === 'watchlist' ? 'active' : ''}
            onClick={() => setActiveView('watchlist')}
          >
            My Watchlist ({favorites.length})
          </button>
        </div>
        <div className="terminal-controls">
          <button onClick={fetchCoins} disabled={refreshing}>
            {refreshing ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>
      </div>
      
      <div className="main-content">
        {activeView === 'watchlist' && (
          <div className="watchlist-panel">
            <Watchlist onSelectCoin={(symbol) => {
              const coin = coins.find(c => c.symbol === symbol);
              if (coin) {
                fetchPrediction(coin.id, symbol);
              }
            }} />
          </div>
        )}
        
        <Terminal 
          coins={coins}
          loading={loading}
          error={error}
          logs={logs}
          onCommand={handleCommand}
          onSearch={handleSearchQuery}
          onSelectCoin={fetchPrediction}
          favorites={favorites}
          onToggleFavorite={toggleFavorite}
          activeView={activeView}
          selectedCoin={selectedCoin}
        />
      </div>
    </div>
  );
}

export default App;
