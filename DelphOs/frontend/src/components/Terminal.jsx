import React, { useState } from 'react';
import CoinList from './CoinList';
import TerminalInput from './TerminalInput';
import TerminalLog from './TerminalLog';
import CoinChart from './CoinChart';
import MultiSignalAnalysis from './MultiSignalAnalysis';
import ScenarioTesting from './ScenarioTesting';

const Terminal = ({ 
  coins, 
  loading, 
  error, 
  logs, 
  onCommand, 
  onSearch, 
  onSelectCoin,
  favorites = [],
  onToggleFavorite,
  activeView = 'all',
  selectedCoin
}) => {
  const [showScenarioTesting, setShowScenarioTesting] = useState(false);
  return (
    <div className="terminal-body">
      <div className="terminal-logs">
        {logs.map(log => (
          <TerminalLog key={log.id} log={log} />
        ))}
      </div>
      
      {loading ? (
        <div className="loading">Loading cryptocurrency data...</div>
      ) : error ? (
        <div className="error-message">Error: {error}</div>
      ) : (
        <>
          <CoinList 
            coins={coins} 
            onSelectCoin={onSelectCoin}
            favorites={favorites}
            onToggleFavorite={onToggleFavorite}
            activeView={activeView}
          />
          
          {/* Display chart and advanced analysis when a coin is selected */}
          {selectedCoin && (
            <div className="coin-detail-container">
              <div className="coin-chart-container">
                <CoinChart symbol={selectedCoin.symbol} />
              </div>
              
              <div className="advanced-analysis-container">
                <div className="advanced-analysis-header">
                  <h3>Advanced Analysis for {selectedCoin.symbol}</h3>
                  <div className="advanced-analysis-controls">
                    <button 
                      className={`advanced-button ${!showScenarioTesting ? 'active' : ''}`}
                      onClick={() => setShowScenarioTesting(false)}
                    >
                      Multi-Signal Analysis
                    </button>
                    <button 
                      className={`advanced-button ${showScenarioTesting ? 'active' : ''}`}
                      onClick={() => setShowScenarioTesting(true)}
                    >
                      Scenario Testing
                    </button>
                  </div>
                </div>
                
                {showScenarioTesting ? (
                  <ScenarioTesting symbol={selectedCoin.symbol} />
                ) : (
                  <MultiSignalAnalysis symbol={selectedCoin.symbol} />
                )}
              </div>
            </div>
          )}
        </>
      )}
      
      <TerminalInput 
        onCommand={onCommand}
        onSearch={onSearch}
      />
    </div>
  );
};

export default Terminal;
