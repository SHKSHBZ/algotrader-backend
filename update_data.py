#!/usr/bin/env python3
"""
Stock Data Update Utility
Updates historical data cache for paper trading bot
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from datetime import datetime
import pytz
from pathlib import Path
from data_cache_manager import DataCacheManager

IST = pytz.timezone('Asia/Kolkata')

def main():
    """
    Main data update function
    """
    print("=" * 60)
    print("[DATA] STOCK DATA UPDATE UTILITY")
    print("=" * 60)
    print("Updates historical data cache for your paper trading bot")
    print("=" * 60)
    print()
    
    # Load stock list
    try:
        with open('stock_universe_by_sector.json', 'r') as f:
            stock_data = json.load(f)
        
        # Extract all symbols
        all_symbols = []
        for sector_data in stock_data.values():
            if isinstance(sector_data, list):
                all_symbols.extend(sector_data)
            elif isinstance(sector_data, dict) and 'symbols' in sector_data:
                all_symbols.extend(sector_data['symbols'])
        
        # Remove duplicates and sort
        all_symbols = sorted(list(set(all_symbols)))
        
        print(f"[INFO] Found {len(all_symbols)} stocks to update")
        
    except Exception as e:
        print(f"[ERROR] Error loading stock list: {e}")
        print("[TIP] Make sure stock_universe_by_sector.json exists")
        return
    
    # Initialize cache manager
    try:
        cache_mgr = DataCacheManager()
        print(f"[OK] Data cache manager initialized")
        print(f"[CACHE] Cache directory: {cache_mgr.cache_dir}")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error initializing cache manager: {e}")
        return
    
    # Show update options
    print("[MENU] UPDATE OPTIONS:")
    print("1. Quick update (15min data only)")
    print("2. Full update (15min, 60min, daily)")
    print("3. Daily data only")
    print("4. Check data status")
    print("5. Update specific stocks")
    print()
    
    choice = input("[INPUT] Enter your choice (1-5): ").strip()
    print()
    
    if choice == '1':
        # Quick update - 15min data only
        print("[START] Starting quick update (15min data)...")
        update_timeframes = ['15min']
        
    elif choice == '2':
        # Full update
        print("[START] Starting full update (all timeframes)...")
        update_timeframes = ['15min', '60min', 'daily']
        
    elif choice == '3':
        # Daily data only
        print("[START] Starting daily data update...")
        update_timeframes = ['daily']
        
    elif choice == '4':
        # Check status
        print("[STATUS] CURRENT DATA STATUS:")
        print("=" * 30)
        cache_mgr.print_cache_summary()
        return
        
    elif choice == '5':
        # Update specific stocks
        print("[INPUT] Enter stock symbols (comma-separated):")
        print("[TIP] Example: RELIANCE,TCS,HDFCBANK")
        symbols_input = input("[SYMBOLS] Symbols: ").strip().upper()
        
        if not symbols_input:
            print("[ERROR] No symbols provided")
            return
        
        custom_symbols = [s.strip() for s in symbols_input.split(',')]
        all_symbols = [s for s in custom_symbols if s in all_symbols]
        
        if not all_symbols:
            print("[ERROR] No valid symbols found")
            return
        
        print(f"[TARGET] Updating {len(all_symbols)} stocks: {', '.join(all_symbols)}")
        update_timeframes = ['15min', '60min', 'daily']
        
    else:
        print("[ERROR] Invalid choice")
        return
    
    # Perform update
    print(f"[TIME] Started at: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[INFO] Stocks: {len(all_symbols)}")
    print(f"[INFO] Timeframes: {', '.join(update_timeframes)}")
    print(f"[INFO] Total downloads: {len(all_symbols) * len(update_timeframes)}")
    print()
    
    try:
        # Use the batch download method
        cache_mgr.download_all_stocks(all_symbols, update_timeframes)
        
        print()
        print("[SUCCESS] DATA UPDATE COMPLETE!")
        print("=" * 25)
        print(f"[TIME] Finished at: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("[READY] Your paper trading bot now has fresh data!")
        print("[TIP] Run: python paper_trading.py")
        
    except Exception as e:
        print(f"[ERROR] Update failed: {e}")
        print("[TIP] Check your internet connection and try again")

def quick_update():
    """
    Quick update function for 15min data only
    """
    print("[QUICK] QUICK DATA UPDATE (15min)")
    print("=" * 30)
    
    try:
        # Load stock list
        with open('hybrid_config.json', 'r') as f:
            config = json.load(f)
        
        symbols = config.get('watchlist', [])
        
        if not symbols:
            print("[ERROR] No watchlist found in config")
            return
        
        # Initialize cache manager
        cache_mgr = DataCacheManager()
        
        print(f"[INFO] Updating {len(symbols)} stocks (15min data)")
        print()
        
        # Update only 15min data
        cache_mgr.download_all_stocks(symbols, ['15min'])
        
        print("[SUCCESS] Quick update complete!")
        
    except Exception as e:
        print(f"[ERROR] Quick update failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_update()
    else:
        main()