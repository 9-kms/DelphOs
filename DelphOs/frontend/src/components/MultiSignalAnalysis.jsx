import React, { useState, useEffect } from 'react';
import '../styles.css';

const MultiSignalAnalysis = ({ symbol }) => {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeframe, setTimeframe] = useState('24h');
  const [selectedTab, setSelectedTab] = useState('summary');

  useEffect(() => {
    if (!symbol) return;
    
    fetchAnalysisData();
  }, [symbol, timeframe]);

  const fetchAnalysisData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/multi_signal/${symbol}?timeframe=${timeframe}`);
      
      if (!response.ok) {
        throw new Error(`Error fetching multi-signal analysis: ${response.statusText}`);
      }
      
      const data = await response.json();
      setAnalysisData(data);
    } catch (err) {
      console.error("Error fetching multi-signal analysis:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTimeframeChange = (newTimeframe) => {
    setTimeframe(newTimeframe);
  };

  const renderPredictionClass = (prediction) => {
    if (!prediction) return "";
    
    switch (prediction.toLowerCase()) {
      case 'bullish': 
        return "prediction-bullish";
      case 'bearish': 
        return "prediction-bearish";
      default: 
        return "prediction-neutral";
    }
  };

  const renderConfidenceBar = (confidence) => {
    const confidenceValue = confidence || 0;
    
    return (
      <div className="confidence-bar-container">
        <div 
          className={`confidence-bar ${confidenceValue > 70 ? 'high-confidence' : 
                                        confidenceValue > 50 ? 'medium-confidence' : 
                                        'low-confidence'}`}
          style={{ width: `${confidenceValue}%` }}
        />
        <span className="confidence-value">{confidenceValue}%</span>
      </div>
    );
  };

  const renderSignalStrength = (score) => {
    const absScore = Math.abs(score);
    const isPositive = score > 0;
    const scoreClass = isPositive ? 'positive' : 'negative';
    
    let strengthLabel;
    if (absScore > 70) {
      strengthLabel = isPositive ? 'Very Bullish' : 'Very Bearish';
    } else if (absScore > 40) {
      strengthLabel = isPositive ? 'Bullish' : 'Bearish';
    } else if (absScore > 20) {
      strengthLabel = isPositive ? 'Slightly Bullish' : 'Slightly Bearish';
    } else {
      strengthLabel = 'Neutral';
      return <span className="prediction-neutral">{strengthLabel}</span>;
    }
    
    return <span className={scoreClass}>{strengthLabel}</span>;
  };

  const renderSummaryTab = () => {
    if (!analysisData) return null;
    
    return (
      <div className="multi-signal-summary">
        <div className="multi-signal-result">
          <div className="result-header">
            <h3>Multi-Signal Prediction</h3>
            <div className="timeframe-selector">
              <span>Timeframe:</span>
              <select 
                value={timeframe} 
                onChange={(e) => handleTimeframeChange(e.target.value)}
                className="chart-select"
              >
                <option value="1h">1 Hour</option>
                <option value="24h">24 Hours</option>
                <option value="7d">7 Days</option>
                <option value="30d">30 Days</option>
              </select>
            </div>
          </div>
          
          <div className="prediction-box">
            <div className="prediction-result">
              <div className="prediction-label">Prediction:</div>
              <div className={`prediction-value ${renderPredictionClass(analysisData.prediction)}`}>
                {analysisData.prediction}
              </div>
            </div>
            
            <div className="prediction-confidence">
              <div className="confidence-label">Confidence:</div>
              <div className="confidence-meter">
                {renderConfidenceBar(analysisData.confidence)}
              </div>
            </div>
          </div>
          
          <div className="prediction-explanation">
            <div className="explanation-label">Analysis:</div>
            <div className="explanation-text">{analysisData.explanation}</div>
          </div>
        </div>
        
        <div className="signal-breakdown">
          <h3>Signal Breakdown</h3>
          
          <div className="signal-row">
            <div className="signal-type">Technical Analysis</div>
            <div className="signal-strength">
              {renderSignalStrength(analysisData.signals.technical.score)}
            </div>
            <div className="signal-weight">{(analysisData.signals.technical.weight * 100).toFixed(0)}%</div>
          </div>
          
          <div className="signal-row">
            <div className="signal-type">Social Sentiment</div>
            <div className="signal-strength">
              {renderSignalStrength(analysisData.signals.social.score)}
            </div>
            <div className="signal-weight">{(analysisData.signals.social.weight * 100).toFixed(0)}%</div>
          </div>
          
          <div className="signal-row">
            <div className="signal-type">On-Chain Data</div>
            <div className="signal-strength">
              {renderSignalStrength(analysisData.signals.onchain.score)}
            </div>
            <div className="signal-weight">{(analysisData.signals.onchain.weight * 100).toFixed(0)}%</div>
          </div>
          
          <div className="signal-agreement">
            <span className="agreement-label">Signal Agreement:</span>
            <span className={analysisData.signal_agreement ? 'positive' : 'negative'}>
              {analysisData.signal_agreement ? 'YES' : 'NO'}
            </span>
          </div>
        </div>
      </div>
    );
  };

  const renderTechnicalTab = () => {
    if (!analysisData || !analysisData.signals.technical.indicators) return null;
    
    const { technical } = analysisData.signals;
    const indicators = technical.indicators;
    
    return (
      <div className="technical-analysis-tab">
        <h3>Technical Indicators</h3>
        
        <div className="indicator-container">
          <div className="indicator-group">
            <h4>Momentum Indicators</h4>
            <div className="indicator-row">
              <div className="indicator-name">RSI (14)</div>
              <div className="indicator-value">{indicators.rsi.value.toFixed(2)}</div>
              <div className={`indicator-signal ${indicators.rsi.interpretation === 'Oversold' ? 'positive' : 
                indicators.rsi.interpretation === 'Overbought' ? 'negative' : 'neutral'}`}
              >
                {indicators.rsi.interpretation}
              </div>
            </div>
            
            <div className="indicator-row">
              <div className="indicator-name">MACD</div>
              <div className="indicator-value">
                {indicators.macd.value.toFixed(2)} / {indicators.macd.signal_line.toFixed(2)}
              </div>
              <div className={`indicator-signal ${indicators.macd.trend === 'Bullish' ? 'positive' : 'negative'}`}>
                {indicators.macd.trend}
              </div>
            </div>
            
            <div className="indicator-row">
              <div className="indicator-name">Stochastic</div>
              <div className="indicator-value">
                K: {indicators.stochastic.k.toFixed(1)} / D: {indicators.stochastic.d.toFixed(1)}
              </div>
              <div className={`indicator-signal ${indicators.stochastic.condition === 'Oversold' ? 'positive' : 
                indicators.stochastic.condition === 'Overbought' ? 'negative' : 'neutral'}`}
              >
                {indicators.stochastic.condition}
              </div>
            </div>
          </div>
          
          <div className="indicator-group">
            <h4>Trend Indicators</h4>
            <div className="indicator-row">
              <div className="indicator-name">EMA Crossover</div>
              <div className="indicator-value">
                {indicators.ema_crossover.ema12.toFixed(2)} / {indicators.ema_crossover.ema26.toFixed(2)}
              </div>
              <div className={`indicator-signal ${indicators.ema_crossover.status === 'Golden Cross' ? 'positive' : 'negative'}`}>
                {indicators.ema_crossover.status}
              </div>
            </div>
            
            <div className="indicator-row">
              <div className="indicator-name">ADX</div>
              <div className="indicator-value">{indicators.adx.value.toFixed(2)}</div>
              <div className="indicator-signal">
                {indicators.adx.trend_strength}
              </div>
            </div>
            
            <div className="indicator-row">
              <div className="indicator-name">Bollinger Bands</div>
              <div className="indicator-value">Width: {indicators.bollinger_bands.width.toFixed(3)}</div>
              <div className="indicator-signal">
                Position: {indicators.bollinger_bands.position.toFixed(0)}%
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderSocialTab = () => {
    if (!analysisData || !analysisData.signals.social.details) return null;
    
    const { social } = analysisData.signals;
    const { twitter, reddit, news } = social.details;
    
    return (
      <div className="social-sentiment-tab">
        <h3>Social Sentiment Analysis</h3>
        
        <div className="sentiment-sources">
          <div className="sentiment-source">
            <h4>Twitter</h4>
            <div className="sentiment-stats">
              <div>Analyzed: {twitter.tweet_count} tweets</div>
              <div>
                Sentiment: <span className={twitter.sentiment_score > 0 ? 'positive' : 
                                twitter.sentiment_score < 0 ? 'negative' : 'neutral'}>
                  {twitter.sentiment} ({twitter.sentiment_score.toFixed(1)})
                </span>
              </div>
              <div className="sentiment-distribution">
                <div>Positive: {twitter.positive_count} ({((twitter.positive_count / twitter.tweet_count) * 100).toFixed(1)}%)</div>
                <div>Neutral: {twitter.neutral_count} ({((twitter.neutral_count / twitter.tweet_count) * 100).toFixed(1)}%)</div>
                <div>Negative: {twitter.negative_count} ({((twitter.negative_count / twitter.tweet_count) * 100).toFixed(1)}%)</div>
              </div>
            </div>
          </div>
          
          <div className="sentiment-source">
            <h4>Reddit</h4>
            <div className="sentiment-stats">
              <div>Posts: {reddit.post_count} / Comments: {reddit.comment_count}</div>
              <div>
                Sentiment: <span className={reddit.sentiment_score > 0 ? 'positive' : 
                                reddit.sentiment_score < 0 ? 'negative' : 'neutral'}>
                  {reddit.sentiment} ({reddit.sentiment_score.toFixed(1)})
                </span>
              </div>
              <div>Upvote Ratio: {(reddit.upvote_ratio * 100).toFixed(1)}%</div>
            </div>
          </div>
          
          <div className="sentiment-source">
            <h4>News Coverage</h4>
            <div className="sentiment-stats">
              <div>Articles Analyzed: {news.article_count}</div>
              <div>
                Sentiment: <span className={news.score > 0 ? 'positive' : 
                                news.score < 0 ? 'negative' : 'neutral'}>
                  {news.sentiment} ({news.score.toFixed(1)})
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderOnchainTab = () => {
    if (!analysisData || !analysisData.signals.onchain.details) return null;
    
    const { onchain } = analysisData.signals;
    const { whale, wallet } = onchain.details;
    
    return (
      <div className="onchain-data-tab">
        <h3>On-Chain Analysis</h3>
        
        <div className="onchain-metrics">
          <div className="onchain-section">
            <h4>Whale Activity</h4>
            <div className="onchain-stats">
              <div className="metric-row">
                <div className="metric-name">Large Inflows:</div>
                <div className="metric-value">{whale.large_inflows}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">Large Outflows:</div>
                <div className="metric-value">{whale.large_outflows}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">Exchange Inflows:</div>
                <div className="metric-value">{whale.exchange_inflows}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">Exchange Outflows:</div>
                <div className="metric-value">{whale.exchange_outflows}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">Inflow/Outflow Ratio:</div>
                <div className={`metric-value ${whale.inflow_outflow_ratio > 1 ? 'positive' : 
                                whale.inflow_outflow_ratio < 1 ? 'negative' : 'neutral'}`}>
                  {whale.inflow_outflow_ratio.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
          
          <div className="onchain-section">
            <h4>Wallet Activity</h4>
            <div className="onchain-stats">
              <div className="metric-row">
                <div className="metric-name">Daily Transactions:</div>
                <div className="metric-value">{wallet.transactions_per_day.toLocaleString()}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">Active Addresses:</div>
                <div className="metric-value">{wallet.active_addresses.toLocaleString()}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">New Addresses:</div>
                <div className="metric-value">{wallet.new_addresses.toLocaleString()}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">Transaction Volume:</div>
                <div className="metric-value">${wallet.transaction_volume.toLocaleString()}</div>
              </div>
              <div className="metric-row">
                <div className="metric-name">Avg Transaction Size:</div>
                <div className="metric-value">${wallet.avg_transaction_size.toLocaleString()}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderTabContent = () => {
    switch (selectedTab) {
      case 'summary':
        return renderSummaryTab();
      case 'technical':
        return renderTechnicalTab();
      case 'social':
        return renderSocialTab();
      case 'onchain':
        return renderOnchainTab();
      default:
        return renderSummaryTab();
    }
  };

  if (loading) {
    return <div className="loading">Loading multi-signal analysis...</div>;
  }

  if (error) {
    return (
      <div className="error-message">
        Error loading multi-signal analysis: {error}
      </div>
    );
  }

  if (!analysisData) {
    return (
      <div className="no-data">
        No multi-signal analysis data available for {symbol}
      </div>
    );
  }

  return (
    <div className="multi-signal-container">
      <div className="multi-signal-tabs">
        <button 
          className={`tab-button ${selectedTab === 'summary' ? 'active' : ''}`}
          onClick={() => setSelectedTab('summary')}
        >
          Summary
        </button>
        <button 
          className={`tab-button ${selectedTab === 'technical' ? 'active' : ''}`}
          onClick={() => setSelectedTab('technical')}
        >
          Technical
        </button>
        <button 
          className={`tab-button ${selectedTab === 'social' ? 'active' : ''}`}
          onClick={() => setSelectedTab('social')}
        >
          Social
        </button>
        <button 
          className={`tab-button ${selectedTab === 'onchain' ? 'active' : ''}`}
          onClick={() => setSelectedTab('onchain')}
        >
          On-Chain
        </button>
      </div>
      
      <div className="multi-signal-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default MultiSignalAnalysis;