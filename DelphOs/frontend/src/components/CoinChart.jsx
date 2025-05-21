import React, { useState, useEffect } from 'react';
import Chart from 'chart.js/auto';

const CoinChart = ({ symbol, type = 'candle', timeframe = '30d', interval = '1d' }) => {
  const [chartData, setChartData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartInstance, setChartInstance] = useState(null);

  useEffect(() => {
    // Clean up previous chart instance when component unmounts or chart changes
    return () => {
      if (chartInstance) {
        chartInstance.destroy();
      }
    };
  }, [chartInstance]);

  useEffect(() => {
    const fetchChartData = async () => {
      if (!symbol) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        const apiBase = window.API_BASE_URL || 'http://localhost:5001';
        const response = await fetch(
          `${apiBase}/api/charts/${symbol}?timeframe=${timeframe}&interval=${interval}&type=${type}`
        );
        
        if (!response.ok) {
          throw new Error(`Failed to fetch chart data: ${response.status}`);
        }
        
        const data = await response.json();
        setChartData(data);
        
        // Create chart after data is loaded
        createChart(data, type);
      } catch (err) {
        console.error('Error fetching chart data:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchChartData();
  }, [symbol, timeframe, interval, type]);
  
  const createChart = (data, chartType) => {
    if (!data || !data.chart_data || data.chart_data.length === 0) return;
    
    // Destroy previous chart instance if it exists
    if (chartInstance) {
      chartInstance.destroy();
    }
    
    const chartElement = document.getElementById('price-chart');
    if (!chartElement) return;
    
    const ctx = chartElement.getContext('2d');
    
    if (chartType === 'line') {
      // Line chart configuration
      const lineChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.chart_data.map(item => new Date(item.date).toLocaleDateString()),
          datasets: [{
            label: `${symbol} Price`,
            data: data.chart_data.map(item => item.close),
            borderColor: '#00ff00',
            backgroundColor: 'rgba(0, 255, 0, 0.1)',
            borderWidth: 1,
            pointRadius: 0,
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              labels: {
                color: '#00ff00'
              }
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              backgroundColor: '#111111',
              titleColor: '#00ff00',
              bodyColor: '#00ff00',
              borderColor: '#00ff00',
              borderWidth: 1
            }
          },
          scales: {
            x: {
              ticks: {
                color: '#00ff00',
                maxRotation: 0,
                autoSkip: true,
                maxTicksLimit: 10
              },
              grid: {
                display: false
              }
            },
            y: {
              ticks: {
                color: '#00ff00'
              },
              grid: {
                color: 'rgba(0, 255, 0, 0.1)'
              }
            }
          }
        }
      });
      
      setChartInstance(lineChart);
    } else {
      // Candlestick chart configuration using financial chart plugin
      const candleChart = new Chart(ctx, {
        type: 'line', // We'll customize this to look like candlesticks
        data: {
          labels: data.chart_data.map(item => new Date(item.date).toLocaleDateString()),
          datasets: [
            // Candlestick wicks (high-low)
            {
              label: 'Price Range',
              data: data.chart_data.map(item => ({
                x: new Date(item.date).toLocaleDateString(),
                y: [item.low, item.high]
              })),
              borderColor: '#00ff00',
              borderWidth: 1,
              pointRadius: 0,
              showLine: false // Don't connect the points
            },
            // Candlestick bodies (open-close)
            {
              label: 'Open-Close',
              data: data.chart_data.map(item => {
                return {
                  x: new Date(item.date).toLocaleDateString(),
                  y: item.open < item.close 
                    ? [item.open, item.close] // Bullish
                    : [item.close, item.open]  // Bearish
                };
              }),
              backgroundColor: data.chart_data.map(item => 
                item.open < item.close 
                  ? 'rgba(0, 255, 0, 0.8)' // Bullish (green)
                  : 'rgba(255, 0, 0, 0.8)'  // Bearish (red)
              ),
              borderColor: data.chart_data.map(item => 
                item.open < item.close ? '#00ff00' : '#ff0000'
              ),
              borderWidth: 2,
              pointRadius: 0,
              barPercentage: 0.8
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              backgroundColor: '#111111',
              titleColor: '#00ff00',
              bodyColor: '#00ff00',
              borderColor: '#00ff00',
              borderWidth: 1,
              callbacks: {
                label: (context) => {
                  const dataPoint = data.chart_data[context.dataIndex];
                  return [
                    `Open: $${dataPoint.open.toFixed(2)}`,
                    `High: $${dataPoint.high.toFixed(2)}`,
                    `Low: $${dataPoint.low.toFixed(2)}`,
                    `Close: $${dataPoint.close.toFixed(2)}`,
                    `Volume: ${dataPoint.volume.toLocaleString()}`
                  ];
                }
              }
            }
          },
          scales: {
            x: {
              ticks: {
                color: '#00ff00',
                maxRotation: 0,
                autoSkip: true,
                maxTicksLimit: 10
              },
              grid: {
                display: false
              }
            },
            y: {
              ticks: {
                color: '#00ff00'
              },
              grid: {
                color: 'rgba(0, 255, 0, 0.1)'
              }
            }
          }
        }
      });
      
      setChartInstance(candleChart);
    }
  };
  
  return (
    <div className="coin-chart-container">
      <div className="chart-header">
        <h3>{symbol} Price Chart</h3>
        <div className="chart-controls">
          <select 
            value={timeframe} 
            onChange={(e) => setTimeframe(e.target.value)}
            className="chart-select"
          >
            <option value="1d">1 Day</option>
            <option value="7d">1 Week</option>
            <option value="30d">1 Month</option>
            <option value="90d">3 Months</option>
            <option value="1y">1 Year</option>
            <option value="2y">2 Years</option>
          </select>
          
          <select 
            value={interval} 
            onChange={(e) => setInterval(e.target.value)}
            className="chart-select"
          >
            <option value="1d">Daily</option>
            <option value="1h">Hourly</option>
            <option value="15m">15 Minutes</option>
            <option value="5m">5 Minutes</option>
          </select>
          
          <select 
            value={type} 
            onChange={(e) => setType(e.target.value)}
            className="chart-select"
          >
            <option value="candle">Candlestick</option>
            <option value="line">Line</option>
          </select>
        </div>
      </div>
      
      <div className="chart-container">
        {isLoading && <div className="loading">Loading chart data...</div>}
        {error && <div className="error">Error: {error}</div>}
        <canvas id="price-chart" width="800" height="400"></canvas>
      </div>
    </div>
  );
};

export default CoinChart;