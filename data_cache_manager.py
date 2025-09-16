"""
Data Cache Manager for Perfect Trader
Handles historical data storage, retrieval, and updates
Optimized for 3-year backtesting and real-time updates
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import os
import json
import pytz
from pathlib import Path

# Force IST timezone
IST = pytz.timezone('Asia/Kolkata')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataCacheManager:
    """
    Manages cached historical data for all stocks
    - Downloads and stores 3 years of historical data
    - Provides incremental updates
    - Handles multiple timeframes (5min, 15min, 60min, daily)
    """
    
    def __init__(self, cache_dir: str = 'data_cache'):
        """Initialize cache manager"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Timeframe configurations
        self.timeframes = {
            '5min': {'interval': '5m', 'days': 100, 'bars_per_day': 75},
            '15min': {'interval': '15m', 'days': 200, 'bars_per_day': 25},
            '60min': {'interval': '1h', 'days': 400, 'bars_per_day': 6},
            'daily': {'interval': '1d', 'days': 1825, 'bars_per_day': 1}  # 7 years for daily
        }
        
        # Metadata tracking
        self.metadata_file = self.cache_dir / 'metadata.json'
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Load metadata about cached data"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """Save metadata about cached data"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def get_cache_path(self, symbol: str, timeframe: str) -> Path:
        """Get cache file path for symbol and timeframe"""
        symbol_dir = self.cache_dir / symbol
        symbol_dir.mkdir(exist_ok=True)
        return symbol_dir / f"{timeframe}.csv"
    
    def is_cache_valid(self, symbol: str, timeframe: str) -> bool:
        """Check if cached data exists and is recent"""
        cache_file = self.get_cache_path(symbol, timeframe)
        
        if not cache_file.exists():
            return False
        
        # Check metadata for last update
        key = f"{symbol}_{timeframe}"
        if key not in self.metadata:
            return False
        
        last_update = datetime.fromisoformat(self.metadata[key]['last_update'])
        now_ist = datetime.now(IST)
        
        # Cache is valid if updated today (for intraday) or within last trading day
        if timeframe in ['5min', '15min', '60min']:
            # Intraday data - needs update if market is open and last update > 15 mins
            if self._is_market_open():
                return (now_ist - last_update).seconds < 900  # 15 minutes
            else:
                # If market closed, data from last trading day is valid
                return (now_ist.date() - last_update.date()).days <= 1
        else:
            # Daily data - valid if updated within last day
            return (now_ist.date() - last_update.date()).days == 0
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open"""
        now_ist = datetime.now(IST)
        
        # Market hours: 9:15 AM - 3:30 PM IST
        market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Check if weekday (Monday=0, Sunday=6)
        is_weekday = now_ist.weekday() < 5
        
        return is_weekday and market_open <= now_ist <= market_close
    
    def download_historical_data(self, symbol: str, timeframe: str, 
                                force_download: bool = False) -> pd.DataFrame:
        """
        Download historical data from Zerodha
        Uses Zerodha API for reliable market data
        """
        cache_file = self.get_cache_path(symbol, timeframe)
        
        # Return cached data if valid and not forcing download
        if not force_download and self.is_cache_valid(symbol, timeframe):
            logging.info(f"[CACHE] Loading {symbol} {timeframe} from cache")
            data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
            # Ensure timezone-aware index
            if data.index.tz is None:
                data.index = data.index.tz_localize(IST)
            return data
        
        logging.info(f"[DOWNLOAD] Downloading {symbol} {timeframe} data...")
        
        try:
            # Use Zerodha only
            data = self._download_from_zerodha(symbol, timeframe)
        except Exception as e:
            logging.error(f"Zerodha failed for {symbol}: {e}")
            return pd.DataFrame()
        
        if data is not None and not data.empty:
            # Save to cache
            data.to_csv(cache_file)
            
            # Update metadata
            key = f"{symbol}_{timeframe}"
            self.metadata[key] = {
                'last_update': datetime.now(IST).isoformat(),
                'rows': len(data),
                'start_date': str(data.index[0]),
                'end_date': str(data.index[-1])
            }
            self._save_metadata()
            
            logging.info(f"[SUCCESS] Cached {len(data)} bars for {symbol} {timeframe}")
        
        return data
    
    def _download_from_zerodha(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Download from Zerodha (implementation depends on your loader)"""
        try:
            from zerodha_loader import EnhancedHybridDataLoader
            loader = EnhancedHybridDataLoader(prefer_zerodha=True)
            
            # Map timeframe to Zerodha interval
            interval_map = {
                '5min': '5minute',
                '15min': '15minute', 
                '60min': '60minute',
                'daily': 'day'
            }
            
            # Calculate period based on timeframe
            days = self.timeframes[timeframe]['days']
            
            data = loader.get_historical_data(
                symbol=symbol,
                period=f'{days}day',
                interval=interval_map[timeframe]
            )
            
            if data is not None:
                # Ensure datetime index
                if 'date' in data.columns:
                    data.set_index('date', inplace=True)
                data.index = pd.to_datetime(data.index)
                data.index.name = 'datetime'
                
            return data
            
        except Exception as e:
            raise Exception(f"Zerodha download failed: {e}")
    
    
    def update_latest_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Update cache with only the latest bars (incremental update)
        Much faster than full download
        """
        cache_file = self.get_cache_path(symbol, timeframe)
        
        # Load existing data
        if cache_file.exists():
            existing_data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
            last_datetime = existing_data.index[-1]
            
            # Download only new data since last update
            logging.info(f"[UPDATE] Updating {symbol} {timeframe} from {last_datetime}")
            
            try:
                # Get only recent data
                new_data = self._download_recent_data(symbol, timeframe, last_datetime)
                
                if new_data is not None and not new_data.empty:
                    # Append new data
                    updated_data = pd.concat([existing_data, new_data])
                    updated_data = updated_data[~updated_data.index.duplicated(keep='last')]
                    
                    # Save updated data
                    updated_data.to_csv(cache_file)
                    
                    # Update metadata
                    key = f"{symbol}_{timeframe}"
                    self.metadata[key]['last_update'] = datetime.now(IST).isoformat()
                    self.metadata[key]['rows'] = len(updated_data)
                    self.metadata[key]['end_date'] = str(updated_data.index[-1])
                    self._save_metadata()
                    
                    logging.info(f"[SUCCESS] Added {len(new_data)} new bars to {symbol} {timeframe}")
                    return updated_data
                    
            except Exception as e:
                logging.error(f"Update failed: {e}")
                
        # If no existing data or update failed, do full download
        return self.download_historical_data(symbol, timeframe, force_download=True)
    
    def _download_recent_data(self, symbol: str, timeframe: str, 
                             since: datetime) -> pd.DataFrame:
        """Download recent data using Zerodha only"""
        try:
            # Use Zerodha for recent data updates
            return self._download_from_zerodha(symbol, timeframe)
            
        except Exception as e:
            logging.error(f"Recent data download failed: {e}")
            return pd.DataFrame()
    
    def get_data(self, symbol: str, timeframe: str = '15min') -> pd.DataFrame:
        """
        Get data for a symbol - from cache if valid, else download
        This is the main method to use
        """
        if self.is_cache_valid(symbol, timeframe):
            # During market hours, update with latest bars
            if self._is_market_open() and timeframe != 'daily':
                return self.update_latest_data(symbol, timeframe)
            else:
                # Return cached data
                cache_file = self.get_cache_path(symbol, timeframe)
                data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                # Ensure timezone-aware index
                if data.index.tz is None:
                    data.index = data.index.tz_localize(IST)
                return data
        else:
            # Download full historical data
            return self.download_historical_data(symbol, timeframe)
    
    def download_all_stocks(self, symbols: List[str], timeframes: List[str] = None):
        """
        Batch download all stocks and timeframes
        Used for initial setup
        """
        if timeframes is None:
            timeframes = list(self.timeframes.keys())
        
        total = len(symbols) * len(timeframes)
        completed = 0
        
        logging.info(f"[INFO] Downloading data for {len(symbols)} stocks, {len(timeframes)} timeframes")
        logging.info(f"[INFO] Total downloads: {total}")
        
        for symbol in symbols:
            for timeframe in timeframes:
                completed += 1
                logging.info(f"[{completed}/{total}] Downloading {symbol} {timeframe}...")
                
                try:
                    self.download_historical_data(symbol, timeframe, force_download=True)
                except Exception as e:
                    logging.error(f"Failed to download {symbol} {timeframe}: {e}")
                
                # Small delay to avoid rate limits
                import time
                time.sleep(0.5)
        
        logging.info(f"[SUCCESS] Download complete! Check {self.cache_dir} for data")
        self.print_cache_summary()
    
    def print_cache_summary(self):
        """Print summary of cached data"""
        print("\n" + "="*60)
        print("[CACHE] CACHE SUMMARY")
        print("="*60)
        
        total_size = 0
        total_files = 0
        
        for symbol_dir in self.cache_dir.iterdir():
            if symbol_dir.is_dir() and symbol_dir.name != '__pycache__':
                print(f"\n{symbol_dir.name}:")
                for csv_file in symbol_dir.glob("*.csv"):
                    size_mb = csv_file.stat().st_size / (1024 * 1024)
                    total_size += size_mb
                    total_files += 1
                    
                    # Get row count from metadata
                    key = f"{symbol_dir.name}_{csv_file.stem}"
                    rows = self.metadata.get(key, {}).get('rows', 'N/A')
                    
                    print(f"  {csv_file.stem:10} - {rows:6} rows, {size_mb:.2f} MB")
        
        print(f"\nTotal: {total_files} files, {total_size:.2f} MB")
        print("="*60)


if __name__ == "__main__":
    # Test the cache manager
    cache_mgr = DataCacheManager()
    
    # Test with a single stock
    print("Testing with RELIANCE...")
    
    # Download different timeframes
    for timeframe in ['15min', 'daily']:
        print(f"\nTesting {timeframe} data:")
        data = cache_mgr.get_data('RELIANCE', timeframe)
        
        if data is not None and not data.empty:
            print(f"[SUCCESS] Got {len(data)} bars")
            print(f"   Date range: {data.index[0]} to {data.index[-1]}")
            print(f"   Latest close: {data['close'].iloc[-1]:.2f}")
        else:
            print(f"[ERROR] Failed to get data")
    
    # Print cache summary
    cache_mgr.print_cache_summary()