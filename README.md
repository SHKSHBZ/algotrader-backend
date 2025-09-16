# 🚀 Perfect Trader - Paper Trading Bot

A clean, focused paper trading system using MTFA (Multi-Timeframe Analysis) strategy with Zerodha integration.

## 📁 Directory Structure

```
Perfect_Trader/
├── 📊 CORE FILES
│   ├── paper_trading.py              # Main paper trading bot
│   ├── mtfa_strategy.py              # MTFA trading strategy
│   └── data_cache_manager.py         # Historical data management
│
├── ⚙️ SETUP & CONFIG
│   ├── setup_zerodha.py             # One-time Zerodha API setup
│   ├── zerodha_status.py            # Check session status
│   ├── ZERODHA_SETUP.md             # Complete setup guide
│   └── requirements.txt             # Python dependencies
│
├── 📂 DATA & STATE
│   ├── stock_universe_by_sector.json # List of stocks to trade
│   ├── zerodha_config.json          # Your API credentials
│   ├── zerodha_session.json         # Session tokens
│   ├── paper_trading_portfolio.json # Your portfolio state
│   └── data_cache/                  # Historical price data
│
└── 🗂️ ARCHIVE
    └── archive/                     # Old files (unused)
```

## 🚀 Quick Start

### First Time Setup
```bash
python setup_zerodha.py
```

### Daily Usage
```bash
python paper_trading.py
```

### Check Status
```bash
python zerodha_status.py
```

## 📊 What Each File Does

### **Core Trading Files**
- **`paper_trading.py`** - Your main trading bot with Zerodha integration
- **`mtfa_strategy.py`** - Multi-timeframe analysis strategy (Daily + 60min + 15min)
- **`data_cache_manager.py`** - Downloads and manages historical data

### **Setup & Utilities**
- **`setup_zerodha.py`** - Configure API credentials once
- **`zerodha_status.py`** - Check your session status anytime
- **`ZERODHA_SETUP.md`** - Complete documentation

### **Data & Configuration**
- **`stock_universe_by_sector.json`** - 105 stocks across Large/Mid/Small cap
- **`zerodha_config.json`** - Your saved API credentials
- **`zerodha_session.json`** - Current session token
- **`paper_trading_portfolio.json`** - Your virtual portfolio state

## ✅ Features

- ✅ **Paper Trading**: Safe simulation with Rs.2,50,000 virtual capital
- ✅ **MTFA Strategy**: Multi-timeframe analysis for better signals
- ✅ **Zerodha Integration**: Real-time prices during market hours
- ✅ **Persistent Sessions**: Login once, trade all day
- ✅ **Portfolio Tracking**: Detailed P&L and position management
- ✅ **Risk Management**: Trailing stops and position sizing

## 🛡️ Safety Features

- **No Real Money**: 100% virtual trading
- **Session Management**: Secure token handling
- **Data Validation**: Stale data rejection (>24 hours)
- **Error Handling**: Graceful fallbacks to cached data

## 📈 Performance

- **Starting Capital**: Rs.2,50,000
- **Max Positions**: 20 concurrent trades
- **Trading Hours**: 9:15 AM - 3:30 PM IST
- **Update Frequency**: 30-second price updates
- **Data Freshness**: Real-time Zerodha + cache fallback

---

**Ready to start paper trading? Run `python setup_zerodha.py` first, then `python paper_trading.py` daily!** 🎯