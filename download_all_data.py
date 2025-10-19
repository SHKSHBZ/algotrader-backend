#!/usr/bin/env python3
"""
Download historical data for all stocks in watchlist
MTFA Strategy requires: Daily (7 years), 60min, 15min data
Includes rate limiting to respect Zerodha API limits (3 req/sec)
"""
import sys
import json
import os
import time
from pathlib import Path

# Change to script directory
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

from data_cache_manager import DataCacheManager
from zerodha_loader import EnhancedHybridDataLoader

# Load watchlist
with open('hybrid_config.json', 'r') as f:
    config = json.load(f)
    watchlist = config['watchlist']

# Timeframes needed for MTFA strategy
timeframes = ['daily', '60min', '15min']

# Zerodha API Rate Limits (to avoid getting blocked):
# - Max 3 requests per second
# - Max 10 concurrent connections
# - Safe approach: 1 request every 0.4 seconds = 2.5 req/sec
RATE_LIMIT_DELAY = 0.4  # seconds between API calls

print(f"=" * 60)
print(f"DOWNLOADING MULTI-TIMEFRAME DATA FOR {len(watchlist)} STOCKS")
print(f"Timeframes: Daily (5 years), 60min, 15min")
print(f"⏱️  Rate Limited: {RATE_LIMIT_DELAY}s delay between requests")
print(f"=" * 60)

# Create managers
cache_mgr = DataCacheManager()

# Download for each stock
success_count = 0
fail_count = 0

for i, symbol in enumerate(watchlist, 1):
    print(f"\n[{i}/{len(watchlist)}] Downloading {symbol}...")
    stock_success = True
    
    try:
        # Download all timeframes for MTFA
        for tf in timeframes:
            print(f"   📊 {tf} timeframe...", end=" ", flush=True)
            cache_mgr.download_historical_data(symbol, tf, force_download=True)
            print("✅")
            
            # RATE LIMITING: Wait between each API call
            time.sleep(RATE_LIMIT_DELAY)
        
        success_count += 1
        print(f"   ✅ ALL TIMEFRAMES SUCCESS")
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Download interrupted by user at stock #{i}")
        print(f"   Downloaded: {success_count}/{len(watchlist)} stocks")
        print(f"   Resume by running this script again (cached data will be skipped)")
        break
    except Exception as e:
        fail_count += 1
        print(f"\n   ❌ Failed: {e}")

print(f"\n" + "=" * 60)
print(f"DOWNLOAD COMPLETE")
print(f"   Success: {success_count}")
print(f"   Failed: {fail_count}")
print(f"=" * 60)
