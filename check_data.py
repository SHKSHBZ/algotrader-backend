#!/usr/bin/env python3
"""
Data Status Checker
Quick check of your stock data cache status
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import pandas as pd

IST = pytz.timezone('Asia/Kolkata')

def main():
    """
    Check data status
    """
    print("=" * 50)
    print("[STATUS] STOCK DATA STATUS CHECKER")
    print("=" * 50)
    
    cache_dir = Path('data_cache')
    
    if not cache_dir.exists():
        print("[ERROR] No data cache found!")
        print("[TIP] Run: python update_data.py")
        return
    
    # Get current time
    now = datetime.now(IST)
    
    # Load your watchlist
    try:
        with open('hybrid_config.json', 'r') as f:
            config = json.load(f)
        watchlist = config.get('watchlist', [])
    except:
        watchlist = ['RELIANCE', 'TCS', 'HDFCBANK']  # Fallback
    
    print(f"[TIME] Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} IST")
    print(f"[INFO] Checking {len(watchlist)} key stocks")
    print()
    
    # Check data for key stocks
    print("[REPORT] DATA FRESHNESS REPORT:")
    print("-" * 40)
    
    fresh_count = 0
    stale_count = 0
    missing_count = 0
    
    for symbol in watchlist[:10]:  # Check first 10 stocks
        symbol_dir = cache_dir / symbol
        
        if not symbol_dir.exists():
            print(f"[MISS] {symbol:12} - NO DATA")
            missing_count += 1
            continue
        
        # Check 15min data (most important)
        data_file = symbol_dir / '15min.csv'
        
        if not data_file.exists():
            print(f"❌ {symbol:12} - NO 15MIN DATA")
            missing_count += 1
            continue
        
        try:
            # Read last timestamp
            data = pd.read_csv(data_file, index_col='datetime', parse_dates=True)
            if data.empty:
                print(f"❌ {symbol:12} - EMPTY FILE")
                missing_count += 1
                continue
            
            last_update = data.index[-1]
            if last_update.tz is None:
                last_update = last_update.tz_localize(IST)
            
            # Calculate age
            age = now - last_update
            age_hours = age.total_seconds() / 3600
            
            # Determine status
            if age_hours < 24:
                status = "[FRESH]"
                fresh_count += 1
            elif age_hours < 72:
                status = "[AGING]"
                stale_count += 1
            else:
                status = "[STALE]"
                stale_count += 1
            
            # Format age
            if age_hours < 24:
                age_str = f"{age_hours:.1f}h"
            else:
                age_str = f"{age_hours/24:.1f}d"
            
            print(f"{status} {symbol:12} - {age_str:6} old ({last_update.strftime('%m-%d %H:%M')})")
            
        except Exception as e:
            print(f"[ERROR] {symbol:12} - ERROR: {e}")
            missing_count += 1
    
    print()
    print("[SUMMARY]:")
    print(f"[FRESH] Fresh data:   {fresh_count}")
    print(f"[AGING] Aging data:   {stale_count}")
    print(f"[MISSING] Missing data: {missing_count}")
    print()
    
    # Recommendations
    if missing_count > 0:
        print("[TIP] RECOMMENDATION: Run full data update")
        print("   python update_data.py")
    elif stale_count > fresh_count:
        print("[TIP] RECOMMENDATION: Run quick update")
        print("   python update_data.py --quick")
    else:
        print("[GOOD] Your data looks good!")
        print("   Ready for paper trading!")
    
    print()
    
    # Show disk usage
    try:
        total_size = sum(f.stat().st_size for f in cache_dir.rglob('*.csv'))
        size_mb = total_size / (1024 * 1024)
        print(f"[CACHE] Cache size: {size_mb:.1f} MB")
        
        # Count files
        file_count = len(list(cache_dir.rglob('*.csv')))
        print(f"[FILES] Total files: {file_count}")
        
    except Exception as e:
        print(f"[CACHE] Cache size: Unable to calculate ({e})")

if __name__ == "__main__":
    main()