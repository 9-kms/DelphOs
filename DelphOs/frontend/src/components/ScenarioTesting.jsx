import React, { useState } from 'react';
import '../styles.css';

const ScenarioTesting = ({ symbol }) => {
  const [scenarioType, setScenarioType] = useState('btc_change');
  const [magnitude, setMagnitude] = useState(10);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runScenario = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/scenario/${symbol}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          scenario_type: scenarioType,
          magnitude: Number(magnitude)
        })
      });
      
      if (!response.ok) {
        throw new Error(`Error running scenario: ${response.statusText}`);
      }
      
      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error("Error running scenario test:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleScenarioChange = (e) => {
    setScenarioType(e.target.value);
  };

  const handleMagnitudeChange = (e) => {
    setMagnitude(e.target.value);
  };

  const renderScenarioDescription = () => {
    switch (scenarioType) {
      case 'btc_change':
        return `Bitcoin price changes by ${magnitude}%`;
      case 'market_crash':
        return `Market crashes by ${magnitude}%`;
      case 'pump':
        return `${symbol} pumps by ${magnitude}%`;
      case 'whale_buy':
        return `Whale buys ${magnitude}% of daily volume`;
      case 'whale_sell':
        return `Whale sells ${magnitude}% of daily volume`;
      default:
        return 'Select a scenario';
    }
  };

  const renderImpactClass = (impact) => {
    if (!impact) return '';
    
    const absImpact = Math.abs(impact);
    
    if (absImpact < 2) return 'low-impact';
    if (absImpact < 5) return 'medium-impact';
    return 'high-impact';
  };

  const renderImpactDirection = (impact) => {
    if (!impact) return '';
    return impact >= 0 ? 'positive' : 'negative';
  };

  return (
    <div className="scenario-testing-container">
      <h3>Scenario Testing</h3>
      <p className="scenario-description">
        Test how {symbol} price might react to different market scenarios
      </p>
      
      <div className="scenario-controls">
        <div className="scenario-select-container">
          <label htmlFor="scenario-type">Scenario Type:</label>
          <select 
            id="scenario-type" 
            value={scenarioType} 
            onChange={handleScenarioChange}
            className="chart-select"
          >
            <option value="btc_change">Bitcoin Price Change</option>
            <option value="market_crash">Market Crash</option>
            <option value="pump">Price Pump</option>
            <option value="whale_buy">Whale Buy</option>
            <option value="whale_sell">Whale Sell</option>
          </select>
        </div>
        
        <div className="magnitude-container">
          <label htmlFor="magnitude">Magnitude (%):</label>
          <input 
            type="range" 
            id="magnitude" 
            min={scenarioType === 'market_crash' ? -30 : -20} 
            max={scenarioType === 'pump' ? 50 : 20} 
            value={magnitude} 
            onChange={handleMagnitudeChange}
            className="magnitude-slider"
          />
          <div className="magnitude-value">{magnitude}%</div>
        </div>
        
        <button 
          onClick={runScenario} 
          disabled={loading}
          className="run-scenario-button"
        >
          {loading ? 'Running...' : 'Run Scenario'}
        </button>
      </div>
      
      <div className="scenario-summary">
        <strong>Scenario:</strong> {renderScenarioDescription()}
      </div>
      
      {error && (
        <div className="error-message">
          Error: {error}
        </div>
      )}
      
      {result && (
        <div className="scenario-results">
          <h4>Impact Analysis</h4>
          
          <div className="price-impact">
            <div className="impact-label">Estimated Price Impact:</div>
            <div className={`impact-value ${renderImpactClass(result.price_impact)} ${renderImpactDirection(result.price_impact)}`}>
              {result.price_impact > 0 ? '+' : ''}{result.price_impact.toFixed(2)}%
            </div>
          </div>
          
          <div className="volume-impact">
            <div className="impact-label">Estimated Volume Impact:</div>
            <div className={`impact-value ${renderImpactClass(result.volume_impact)} ${renderImpactDirection(result.volume_impact)}`}>
              {result.volume_impact > 0 ? '+' : ''}{result.volume_impact.toFixed(2)}%
            </div>
          </div>
          
          <div className="scenario-explanation">
            <div className="explanation-label">Analysis:</div>
            <div className="explanation-text">{result.explanation}</div>
          </div>
          
          <div className="scenario-confidence">
            <div className="confidence-label">Confidence:</div>
            <div className="confidence-value">{result.confidence}%</div>
            <div className="confidence-bar-container">
              <div 
                className="confidence-bar"
                style={{ width: `${result.confidence}%` }}
              />
            </div>
          </div>
          
          <div className="probabilities">
            <h5>Outcome Probabilities</h5>
            
            <div className="probability-row">
              <div className="outcome">Rise &gt; 5%</div>
              <div className="probability-bar-container">
                <div 
                  className="probability-bar positive"
                  style={{ width: `${result.probabilities.rise * 100}%` }}
                />
              </div>
              <div className="probability-value">
                {(result.probabilities.rise * 100).toFixed(1)}%
              </div>
            </div>
            
            <div className="probability-row">
              <div className="outcome">Stable (±5%)</div>
              <div className="probability-bar-container">
                <div 
                  className="probability-bar neutral"
                  style={{ width: `${result.probabilities.stable * 100}%` }}
                />
              </div>
              <div className="probability-value">
                {(result.probabilities.stable * 100).toFixed(1)}%
              </div>
            </div>
            
            <div className="probability-row">
              <div className="outcome">Fall &gt; 5%</div>
              <div className="probability-bar-container">
                <div 
                  className="probability-bar negative"
                  style={{ width: `${result.probabilities.fall * 100}%` }}
                />
              </div>
              <div className="probability-value">
                {(result.probabilities.fall * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScenarioTesting;