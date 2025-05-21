import React, { useState, useEffect } from 'react';

const CoinList = ({ coins, onSelectCoin, favorites = [], onToggleFavorite, activeView = 'all' }) => {
  const [sortedCoins, setSortedCoins] = useState([]);
  
  // Use simple sorting config without window object - keep in component state
  const [sortConfig, setSortConfig] = useState({
    key: 'confidence',
    direction: 'desc'
  });

  // Filter coins based on activeView and then sort them
  useEffect(() => {
    console.log("Sorting with config:", sortConfig);
    // First filter coins based on active view (all or watchlist)
    let filteredCoins = [...coins];
    
    // Filter out stablecoins (usually have "USD" in name/symbol)
    filteredCoins = filteredCoins.filter(coin => 
      !coin.name.includes('USD') && 
      !coin.symbol.includes('USD') &&
      !coin.name.includes('Tether') &&
      !coin.symbol.includes('USDT')
    );
    
    // If we're in watchlist view, only show favorites
    if (activeView === 'watchlist') {
      filteredCoins = filteredCoins.filter(coin => 
        favorites.includes(coin.symbol)
      );
    }
    
    // Then sort the filtered coins
    if (sortConfig.key) {
      filteredCoins.sort((a, b) => {
        // Handle undefined values for confidence (coins without predictions)
        if (sortConfig.key === 'confidence') {
          const aValue = a[sortConfig.key] !== undefined ? a[sortConfig.key] : -1;
          const bValue = b[sortConfig.key] !== undefined ? b[sortConfig.key] : -1;
          
          if (sortConfig.direction === 'asc') {
            return aValue - bValue;
          } else {
            return bValue - aValue;
          }
        }
        
        // Sort by other numeric values
        if (typeof a[sortConfig.key] === 'number') {
          if (sortConfig.direction === 'asc') {
            return a[sortConfig.key] - b[sortConfig.key];
          } else {
            return b[sortConfig.key] - a[sortConfig.key];
          }
        }
        
        // Sort by strings
        if (sortConfig.direction === 'asc') {
          return a[sortConfig.key] > b[sortConfig.key] ? 1 : -1;
        } else {
          return a[sortConfig.key] < b[sortConfig.key] ? 1 : -1;
        }
      });
    }
    
    setSortedCoins(filteredCoins);
  }, [coins, sortConfig, favorites, activeView]);

  // Handle table header click for sorting
  const requestSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  // Get the sort direction indicator icon
  const getSortDirectionIndicator = (name) => {
    if (sortConfig.key !== name) return null; 
    return <span className="sort-arrow">
      {sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}
    </span>;
  };

  // Format price with appropriate decimals
  const formatPrice = (price) => {
    if (price >= 1000) return price.toLocaleString('en-US', { maximumFractionDigits: 2 });
    if (price >= 1) return price.toLocaleString('en-US', { maximumFractionDigits: 4 });
    if (price >= 0.01) return price.toLocaleString('en-US', { maximumFractionDigits: 6 });
    return price.toLocaleString('en-US', { maximumFractionDigits: 8 });
  };

  // Format volume with appropriate scaling (K, M, B)
  const formatVolume = (volume) => {
    if (volume >= 1000000000) return `${(volume / 1000000000).toFixed(2)}B`;
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(2)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(2)}K`;
    return volume.toFixed(2);
  };

  // Determine CSS class for price change
  const getPriceChangeClass = (change) => {
    if (!change) return 'neutral';
    return change > 0 ? 'positive' : 'negative';
  };

  // Determine CSS class for prediction
  const getPredictionClass = (prediction) => {
    if (!prediction) return '';
    switch (prediction.toLowerCase()) {
      case 'bullish': return 'prediction-bullish';
      case 'bearish': return 'prediction-bearish';
      case 'neutral': return 'prediction-neutral';
      default: return '';
    }
  };

  return (
    <div>
      {sortedCoins.length > 0 ? (
        <table className="coin-list">
          <thead>
            <tr>
              <th>⭐</th>
              <th onClick={() => requestSort('symbol')}>
                Symbol <span className="sort-arrow">
                  {sortConfig.key === 'symbol' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
              <th onClick={() => requestSort('name')}>
                Name <span className="sort-arrow">
                  {sortConfig.key === 'name' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
              <th onClick={() => requestSort('source')}>
                Source <span className="sort-arrow">
                  {sortConfig.key === 'source' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
              <th onClick={() => requestSort('price')}>
                Price (USD) <span className="sort-arrow">
                  {sortConfig.key === 'price' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
              <th onClick={() => requestSort('price_change_24h')}>
                24h Change <span className="sort-arrow">
                  {sortConfig.key === 'price_change_24h' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
              <th onClick={() => requestSort('volume')}>
                Volume <span className="sort-arrow">
                  {sortConfig.key === 'volume' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
              <th onClick={() => requestSort('prediction')}>
                Prediction <span className="sort-arrow">
                  {sortConfig.key === 'prediction' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
              <th onClick={() => requestSort('confidence')}>
                Confidence <span className="sort-arrow">
                  {sortConfig.key === 'confidence' ? (sortConfig.direction === 'asc' ? '↑' : '↓') : '↑↓'}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedCoins.map((coin) => {
              const isFavorite = favorites.includes(coin.symbol);
              const isSpecial = coin.is_special || coin.symbol === 'CLOUDY';
              const isDexToken = coin.source === 'dexscreener' || coin.is_dex_token;
              
              return (
                <tr 
                  key={coin.id} 
                  className={`
                    ${coin.lastUpdate ? 'price-flash' : ''} 
                    ${isSpecial ? 'special-token' : ''} 
                    ${isDexToken ? 'dex-token' : ''}
                  `}
                >
                  <td 
                    className={`favorite-cell ${isFavorite ? 'favorite-active' : ''}`} 
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleFavorite(coin.symbol);
                    }}
                  >
                    {isFavorite ? '★' : '☆'}
                  </td>
                  <td onClick={() => onSelectCoin(coin.id, coin.symbol)}>
                    {coin.symbol}
                    {isSpecial && <span className="special-indicator">✦</span>}
                  </td>
                  <td onClick={() => onSelectCoin(coin.id, coin.symbol)}>{coin.name}</td>
                  <td onClick={() => onSelectCoin(coin.id, coin.symbol)}>
                    {isDexToken ? 'DEX' : 'CoinGecko'}
                  </td>
                  <td onClick={() => onSelectCoin(coin.id, coin.symbol)}>${formatPrice(coin.price)}</td>
                  <td 
                    onClick={() => onSelectCoin(coin.id, coin.symbol)}
                    className={getPriceChangeClass(coin.price_change_24h)}
                  >
                    {coin.price_change_24h ? `${coin.price_change_24h.toFixed(2)}%` : 'N/A'}
                  </td>
                  <td onClick={() => onSelectCoin(coin.id, coin.symbol)}>${formatVolume(coin.volume)}</td>
                  <td 
                    onClick={() => onSelectCoin(coin.id, coin.symbol)}
                    className={getPredictionClass(coin.prediction)}
                  >
                    {coin.prediction || 'No data'}
                  </td>
                  <td 
                    onClick={() => onSelectCoin(coin.id, coin.symbol)}
                    className="coin-confidence"
                    title={coin.reason || 'No prediction data available'}
                  >
                    {coin.confidence ? `${coin.confidence.toFixed(1)}%` : 'N/A'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <div className="no-coins">No cryptocurrency data available</div>
      )}
    </div>
  );
};

export default CoinList;
