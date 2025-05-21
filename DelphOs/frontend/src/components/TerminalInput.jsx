import React, { useState, useRef, useEffect } from 'react';

const TerminalInput = ({ onCommand, onSearch }) => {
  const [input, setInput] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const inputRef = useRef(null);
  const searchTimeoutRef = useRef(null);

  // Focus input on component mount
  useEffect(() => {
    inputRef.current.focus();
  }, []);

  // Handle input change
  const handleInputChange = (e) => {
    const value = e.target.value;
    setInput(value);
    
    // If input starts with search syntax, trigger coin search
    if (value.startsWith('search ') || value.startsWith('find ')) {
      const query = value.split(' ').slice(1).join(' ');
      
      if (query.length >= 2) {
        setSearching(true);
        setShowResults(true);
        
        // Clear previous timeout
        if (searchTimeoutRef.current) {
          clearTimeout(searchTimeoutRef.current);
        }
        
        // Debounce search to avoid too many requests
        searchTimeoutRef.current = setTimeout(async () => {
          const results = await onSearch(query);
          setSearchResults(results);
          setSearching(false);
        }, 300);
      } else {
        setSearchResults([]);
        setSearching(false);
        setShowResults(false);
      }
    } else {
      // Hide search results when not in search mode
      setShowResults(false);
    }
  };

  // Handle key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      
      const trimmedInput = input.trim();
      if (trimmedInput) {
        // Special handling for "666" Easter egg
        if (trimmedInput === "666") {
          onCommand("666");
        } else {
          onCommand(input);
        }
        setInput('');
        setShowResults(false);
      }
    } else if (e.key === 'Escape') {
      setShowResults(false);
    }
  };

  // Handle search result selection
  const handleSelectResult = (coin) => {
    onCommand(`predict ${coin.symbol}`);
    setInput('');
    setShowResults(false);
    inputRef.current.focus();
  };

  return (
    <div className="terminal-input-wrapper">
      <div className="terminal-input-container">
        <span className="terminal-prompt">$</span>
        <input
          ref={inputRef}
          type="text"
          className="terminal-input"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyPress}
          placeholder="Type help for commands or search <query> to find coins"
          autoFocus
        />
      </div>
      
      {showResults && (
        <div className="search-results">
          {searching ? (
            <div className="search-result-item">Searching...</div>
          ) : searchResults.length > 0 ? (
            searchResults.map(coin => (
              <div 
                key={coin.id} 
                className="search-result-item"
                onClick={() => handleSelectResult(coin)}
              >
                {coin.symbol} - {coin.name}
              </div>
            ))
          ) : (
            <div className="search-result-item">No results found</div>
          )}
        </div>
      )}
    </div>
  );
};

export default TerminalInput;
