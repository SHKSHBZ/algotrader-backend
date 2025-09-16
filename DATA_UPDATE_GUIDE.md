# Stock Data Update Guide

This guide explains how to keep your paper trading bot's stock data fresh and up-to-date.

## Quick Start

### Daily Workflow (Recommended)

1. **Check data status**:
   ```bash
   python check_data.py
   ```

2. **Quick update** (if data is stale):
   ```bash
   python update_data.py --quick
   ```

3. **Start paper trading**:
   ```bash
   python paper_trading.py
   ```

## Data Update Methods

### 1. Check Data Status
```bash
python check_data.py
```
- Shows freshness of your cached stock data
- Reports which stocks have fresh/aging/stale data
- Provides recommendations based on data age
- Shows total cache size and file count

**Output Example:**
```
[STATUS] STOCK DATA STATUS CHECKER
[TIME] Current time: 2025-09-16 12:53:07 IST
[INFO] Checking 49 key stocks

[REPORT] DATA FRESHNESS REPORT:
[STALE] RELIANCE     - 5.0d   old (09-11 12:45)
[FRESH] TCS          - 2.1h   old (09-16 10:42)
[AGING] HDFCBANK     - 1.5d   old (09-15 15:30)

[SUMMARY]:
[FRESH] Fresh data:   1
[AGING] Aging data:   1  
[MISSING] Missing data: 1

[TIP] RECOMMENDATION: Run quick update
   python update_data.py --quick
```

### 2. Update Data
```bash
python update_data.py
```

Interactive menu with options:

#### Option 1: Quick Update (Recommended)
- Updates only 15-minute timeframe data
- Fastest option for daily use
- Downloads data for all watchlist stocks
- Takes 2-5 minutes depending on internet speed

#### Option 2: Full Update
- Updates all timeframes (15min, 60min, daily)
- Use when setting up initially or after long breaks
- Takes 10-20 minutes for complete download

#### Option 3: Daily Data Only
- Updates only daily timeframe data
- Useful for strategy development and backtesting
- Fastest update for longer-term analysis

#### Option 4: Check Data Status
- Same as running `check_data.py`
- Quick way to verify data freshness

#### Option 5: Update Specific Stocks
- Enter comma-separated stock symbols
- Updates all timeframes for selected stocks
- Example: `RELIANCE,TCS,HDFCBANK`

### 3. Quick Command Line Update
```bash
python update_data.py --quick
```
- Directly runs quick update without menu
- Perfect for automation or daily scripts
- Updates 15-minute data for watchlist stocks

## Data Freshness Rules

### Fresh Data (Green)
- **Age**: Less than 24 hours
- **Status**: Ready for trading
- **Action**: No update needed

### Aging Data (Yellow)  
- **Age**: 1-3 days old
- **Status**: Usable but should update soon
- **Action**: Consider quick update

### Stale Data (Red)
- **Age**: More than 3 days old
- **Status**: Too old for reliable trading
- **Action**: Must update before trading

### Missing Data
- **Status**: No data file exists
- **Action**: Run full update

## Understanding Your Data Cache

### Cache Structure
```
data_cache/
├── RELIANCE/
│   ├── 15min.csv
│   ├── 60min.csv
│   └── daily.csv
├── TCS/
│   ├── 15min.csv
│   ├── 60min.csv
│   └── daily.csv
└── metadata.json
```

### Timeframe Details

| Timeframe | Use Case | Data Period | Update Frequency |
|-----------|----------|-------------|------------------|
| **15min** | Paper trading signals | 200 days | Daily |
| **60min** | Trend confirmation | 400 days | Weekly |
| **daily** | Long-term analysis | 5+ years | Weekly |

### Cache Size
- **Typical size**: 3-5 MB for 50 stocks
- **Full cache**: ~10-15 MB with all timeframes
- **Storage location**: `data_cache/` folder

## Troubleshooting

### "No module named 'zerodha_loader'"
**Problem**: Zerodha integration not set up
**Solution**: 
1. Run: `python authenticate_zerodha.py`
2. Complete authentication process
3. Retry data update

### "charmap codec can't encode character"
**Problem**: Windows console encoding issue
**Solution**: Already fixed in latest utilities

### "No watchlist found in config"
**Problem**: Missing or empty `hybrid_config.json`
**Solution**: File exists with your watchlist - this should not occur

### Slow downloads
**Problem**: Network or API rate limits
**Solution**: 
- Wait and retry
- Use quick update instead of full update
- Check internet connection

### Empty data files
**Problem**: API authentication failed
**Solution**:
1. Run: `python authenticate_zerodha.py`
2. Re-authenticate with fresh login
3. Retry data update

## Best Practices

### Daily Routine
1. **Morning** (before market open):
   ```bash
   python check_data.py
   python update_data.py --quick  # if needed
   ```

2. **Trading hours**:
   ```bash
   python paper_trading.py
   ```

### Weekly Maintenance
1. **Full data refresh**:
   ```bash
   python update_data.py  # Choose option 2: Full update
   ```

2. **Verify cache health**:
   ```bash
   python check_data.py
   ```

### Monthly Cleanup
- Check cache size growth
- Verify all stocks have complete data
- Update watchlist if needed in `hybrid_config.json`

## Performance Tips

### Faster Updates
- Use `--quick` flag for daily updates
- Update only specific stocks when needed
- Avoid full updates during market hours

### Optimal Schedule
- **Best time**: Early morning (6:00-9:00 AM IST)
- **Avoid**: During market hours (9:15 AM - 3:30 PM IST)
- **Weekend**: Perfect for full data refresh

### Network Optimization
- Stable internet connection recommended
- Avoid during peak internet usage
- Each stock takes ~0.5-1 second to download

## Data Sources

### Primary Source: Zerodha Kite API
- **Reliability**: High (official broker data)
- **Speed**: Fast (direct API access)
- **Limitations**: Requires valid session token
- **Update frequency**: Real-time during market hours

### Backup Handling
- **Cache fallback**: Uses existing data if download fails
- **Graceful degradation**: Trading continues with available data
- **Error logging**: All failures logged for debugging

## Integration with Paper Trading

### Data Flow
1. **Data Update** → Cache files updated
2. **Cache Validation** → Check data freshness
3. **Strategy Execution** → Use cached data for signals
4. **Real-time Updates** → During market hours

### Key Files
- `check_data.py` - Data status checker
- `update_data.py` - Data download utility  
- `data_cache_manager.py` - Core cache management
- `hybrid_config.json` - Watchlist configuration

## Automation Ideas

### Windows Task Scheduler
Create daily task to run:
```bash
cd "C:\path\to\Perfect_Trader"
python update_data.py --quick
```

### Batch Script
Create `daily_update.bat`:
```batch
@echo off
cd /d "C:\Users\shaik\OneDrive\Desktop\Project\Perfect_Trader"
python check_data.py
echo.
echo Running quick update...
python update_data.py --quick
pause
```

This ensures your paper trading bot always has fresh, reliable data for optimal performance!