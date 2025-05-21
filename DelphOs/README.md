# DelphOs - Terminal-Style Crypto Dashboard with ML Predictions

DelphOs is a crypto dashboard application with a clean, terminal-style UI that provides real-time cryptocurrency data and machine learning predictions.

## Features

- Terminal-style interface with green monospace text on a black background
- Real-time cryptocurrency data from CoinGecko API
- Machine learning predictions based on RSI and technical indicators
- Command-line interface for interacting with the application
- Search functionality for finding cryptocurrencies
- Sortable coin list with price, volume, and prediction data

## Installation

### Backend Setup

1. Install the required Python packages:

```bash
pip install flask flask-cors yfinance pandas ta scikit-learn requests
