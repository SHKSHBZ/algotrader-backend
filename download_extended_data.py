"""
Download Extended Historical Data - Multi-Timeframe
Downloads 7 YEARS of data across multiple timeframes for comprehensive analysis
"""
import os
import sys
from pathlib import Path

# Ensure we're in the correct directory
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

from data_cache_manager import DataCacheManager
from watchlist import WATCHLIST

def download_extended_data():
    """
    Download extended historical data for all timeframes:
    - Daily: 2+ years (for long-term trends)
    - 60min: 6 months (for medium-term analysis) 
    - 15min: 2 months (for entry/exit timing)
    
    Note: Zerodha limits minute data to 60 days per request
    """
    
    cache_mgr = DataCacheManager()
    
    # Combine all stocks from watchlist
    all_stocks = (
        WATCHLIST.get('LARGE_CAP', []) + 
        WATCHLIST.get('MID_CAP', []) + 
        WATCHLIST.get('SMALL_CAP', [])
    )
    
    total = len(all_stocks)
    success_count = 0
    failed_count = 0
    
    print("=" * 60)
    print(f"DOWNLOADING EXTENDED DATA FOR {total} STOCKS")
    print("=" * 60)
    print()
    
    for i, symbol in enumerate(all_stocks, 1):
        print(f"[{i}/{total}] Downloading {symbol}...")
        
        try:
            # 1. Download DAILY data (2+ years) - Most important for SMA200
            print(f"  📊 Daily timeframe...")
            cache_mgr.download_historical_data(symbol, 'day', force_download=True)
            
            # 2. Download 60MIN data (6 months)
            print(f"  📊 60-minute timeframe...")
            cache_mgr.download_historical_data(symbol, '60min', force_download=True)
            
            # 3. Download 15MIN data (2 months) - Already done, but refresh
            print(f"  📊 15-minute timeframe...")
            cache_mgr.download_historical_data(symbol, '15min', force_download=True)
            
            print(f"   ✅ Success\n")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)}\n")
            failed_count += 1
            continue
    
    print("=" * 60)
    print("DOWNLOAD COMPLETE")
    print(f"   Success: {success_count}")
    print(f"   Failed: {failed_count}")
    print("=" * 60)

if __name__ == '__main__':
    download_extended_data()
