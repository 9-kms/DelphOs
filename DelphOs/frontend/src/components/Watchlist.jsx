import React, { useState, useEffect } from 'react';

const Watchlist = ({ onSelectCoin }) => {
  const [watchlistItems, setWatchlistItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch watchlist on component mount
  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/watchlist');
      if (!response.ok) {
        throw new Error('Failed to fetch watchlist');
      }
      const data = await response.json();
      setWatchlistItems(data.coins || []);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching watchlist:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  const removeCoin = async (symbol) => {
    try {
      const response = await fetch(`/api/watchlist/${symbol}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Failed to remove coin from watchlist');
      }
      
      // Refresh the watchlist
      fetchWatchlist();
    } catch (err) {
      console.error('Error removing coin:', err);
      setError(err.message);
    }
  };

  if (loading) {
    return <div className="watchlist-container">Loading watchlist...</div>;
  }

  if (error) {
    return <div className="watchlist-container">Error: {error}</div>;
  }

  return (
    <div className="watchlist-container">
      <h3>Watchlist</h3>
      {watchlistItems.length === 0 ? (
        <div className="watchlist-empty">
          Your watchlist is empty. Use 'star SYMBOL' to add coins.
        </div>
      ) : (
        <div className="watchlist-items">
          {watchlistItems.map((item) => (
            <div key={item.coin_symbol} className="watchlist-item">
              <span 
                className="watchlist-symbol"
                onClick={() => onSelectCoin(item.coin_symbol)}
              >
                {item.coin_symbol}
              </span>
              <span className="watchlist-date">
                {new Date(item.date_added).toLocaleDateString()}
              </span>
              {item.notes && <div className="watchlist-notes">{item.notes}</div>}
              <button 
                className="watchlist-remove"
                onClick={() => removeCoin(item.coin_symbol)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Watchlist;