"""
Zerodha Data Loader for Perfect Trader
Integrates with KiteConnect API for live data downloads
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import logging
from pathlib import Path
import json
from zerodha_auth import ZerodhaAuth

IST = pytz.timezone('Asia/Kolkata')

class EnhancedHybridDataLoader:
    """
    Enhanced data loader that uses Zerodha KiteConnect API
    Automatically handles authentication and session management
    """
    
    def __init__(self, prefer_zerodha=True):
        """Initialize the data loader"""
        self.prefer_zerodha = prefer_zerodha
        self.kite = None
        self.auth = ZerodhaAuth()
        self.symbol_map = self._load_symbol_map()
        
    def _load_symbol_map(self):
        """Load NSE symbol mappings for Zerodha"""
        # Common NSE symbols used in your watchlist
        return {
            'RELIANCE': 'RELIANCE',
            'TCS': 'TCS',
            'HDFCBANK': 'HDFCBANK',
            'HINDUNILVR': 'HINDUNILVR',
            'KOTAKBANK': 'KOTAKBANK',
            'ITC': 'ITC',
            'AXISBANK': 'AXISBANK',
            'INFY': 'INFY',
            'HCLTECH': 'HCLTECH',
            'MARUTI': 'MARUTI',
            'SUNPHARMA': 'SUNPHARMA',
            'BHARTIARTL': 'BHARTIARTL',
            'NTPC': 'NTPC',
            'POWERGRID': 'POWERGRID',
            'COALINDIA': 'COALINDIA',
            'ULTRACEMCO': 'ULTRACEMCO',
            'SBIN': 'SBIN',
            'ONGC': 'ONGC',
            'ASIANPAINT': 'ASIANPAINT',
            'NESTLEIND': 'NESTLEIND',
            'TATASTEEL': 'TATASTEEL',
            'HINDALCO': 'HINDALCO',
            'JSWSTEEL': 'JSWSTEEL',
            'GRASIM': 'GRASIM',
            'TECHM': 'TECHM',
            'DRREDDY': 'DRREDDY',
            'CIPLA': 'CIPLA',
            'BAJAJ-AUTO': 'BAJAJ-AUTO',
            'GODREJCP': 'GODREJCP',
            'PIDILITIND': 'PIDILITIND',
            'BANDHANBNK': 'BANDHANBNK',
            'TORNTPHARM': 'TORNTPHARM',
            'UBL': 'UBL',
            'INDIGO': 'INDIGO',
            'ADANIPORTS': 'ADANIPORTS',
            'PAGEIND': 'PAGEIND',
            'DABUR': 'DABUR',
            'MARICO': 'MARICO',
            'BIOCON': 'BIOCON',
            'CADILAHC': 'CADILAHC',
            'MOTHERSUMI': 'MOTHERSUMI',
            'ASHOKLEY': 'ASHOKLEY',
            'LUPIN': 'LUPIN',
            'BOSCHLTD': 'BOSCHLTD',
            'MRF': 'MRF',
            'SIEMENS': 'SIEMENS',
            'TITAN': 'TITAN',
            'DIVISLAB': 'DIVISLAB',
            'BAJAJFINSV': 'BAJAJFINSV'
        }
    
    def _ensure_authenticated(self):
        """Ensure we have a valid Zerodha connection"""
        if self.kite is None:
            try:
                # Try to get authenticated kite instance
                self.kite = self.auth.get_kite_instance()
                if self.kite is None:
                    raise Exception("Authentication required")
                    
                # Test the connection
                profile = self.kite.profile()
                logging.info(f"[AUTH] Connected to Zerodha as: {profile.get('user_name', 'Unknown')}")
                
            except Exception as e:
                logging.error(f"[AUTH] Authentication failed: {e}")
                print(f"[ERROR] Zerodha authentication failed: {e}")
                print("[TIP] Run: python authenticate_zerodha.py")
                raise Exception(f"Zerodha authentication required: {e}")
    
    def get_historical_data(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        """
        Get historical data from Zerodha
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE')
            period: Period string (e.g., '200day')
            interval: Interval string ('5minute', '15minute', '60minute', 'day')
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Ensure we're authenticated
            self._ensure_authenticated()
            
            # Map symbol to NSE format
            nse_symbol = self.symbol_map.get(symbol, symbol)
            instrument_token = self._get_instrument_token(nse_symbol)
            
            if instrument_token is None:
                raise Exception(f"Could not find instrument token for {symbol}")
            
            # Calculate date range
            end_date = datetime.now(IST).date()
            
            # Parse period (e.g., '200day' -> 200 days)
            if period.endswith('day'):
                days = int(period.replace('day', ''))
            else:
                days = 200  # Default
                
            start_date = end_date - timedelta(days=days)
            
            logging.info(f"[DOWNLOAD] Fetching {symbol} {interval} data from {start_date} to {end_date}")
            
            # Download data from Zerodha
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=start_date,
                to_date=end_date,
                interval=interval
            )
            
            if not data:
                logging.warning(f"[WARNING] No data received for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            if df.empty:
                logging.warning(f"[WARNING] Empty dataframe for {symbol}")
                return pd.DataFrame()
            
            # Rename columns to match expected format
            df.columns = [col.lower() for col in df.columns]
            
            # Set datetime index
            if 'date' in df.columns:
                df.set_index('date', inplace=True)
            df.index.name = 'datetime'
            
            # Ensure timezone-aware index
            if df.index.tz is None:
                df.index = df.index.tz_localize(IST)
            
            # Sort by datetime
            df.sort_index(inplace=True)
            
            logging.info(f"[SUCCESS] Downloaded {len(df)} bars for {symbol} {interval}")
            return df
            
        except Exception as e:
            logging.error(f"[ERROR] Failed to download {symbol} data: {e}")
            raise Exception(f"Data download failed for {symbol}: {e}")
    
    def _get_instrument_token(self, symbol: str) -> int:
        """Get instrument token for a symbol"""
        try:
            # Get all instruments
            instruments = self.kite.instruments("NSE")
            
            # Find the instrument
            for instrument in instruments:
                if instrument['tradingsymbol'] == symbol:
                    return instrument['instrument_token']
            
            # If exact match not found, try with -EQ suffix
            eq_symbol = f"{symbol}-EQ" if not symbol.endswith("-EQ") else symbol
            for instrument in instruments:
                if instrument['tradingsymbol'] == eq_symbol:
                    return instrument['instrument_token']
            
            # Still not found, try fuzzy matching
            for instrument in instruments:
                if instrument['name'].upper().replace(' ', '') == symbol.upper().replace('-', '').replace(' ', ''):
                    return instrument['instrument_token']
            
            logging.error(f"[ERROR] Could not find instrument token for {symbol}")
            return None
            
        except Exception as e:
            logging.error(f"[ERROR] Error getting instrument token for {symbol}: {e}")
            return None
    
    def get_live_price(self, symbol: str) -> dict:
        """Get current live price for a symbol"""
        try:
            self._ensure_authenticated()
            
            nse_symbol = self.symbol_map.get(symbol, symbol)
            instrument_token = self._get_instrument_token(nse_symbol)
            
            if instrument_token is None:
                raise Exception(f"Could not find instrument token for {symbol}")
            
            # Get live quote
            quote = self.kite.quote(f"NSE:{nse_symbol}")
            
            if f"NSE:{nse_symbol}" in quote:
                data = quote[f"NSE:{nse_symbol}"]
                return {
                    'symbol': symbol,
                    'ltp': data.get('last_price', 0),
                    'open': data.get('ohlc', {}).get('open', 0),
                    'high': data.get('ohlc', {}).get('high', 0),
                    'low': data.get('ohlc', {}).get('low', 0),
                    'close': data.get('ohlc', {}).get('close', 0),
                    'volume': data.get('volume', 0),
                    'timestamp': datetime.now(IST)
                }
            else:
                raise Exception(f"No quote data received for {symbol}")
                
        except Exception as e:
            logging.error(f"[ERROR] Failed to get live price for {symbol}: {e}")
            raise Exception(f"Live price fetch failed for {symbol}: {e}")
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now_ist = datetime.now(IST)
        
        # Market hours: 9:15 AM - 3:30 PM IST
        market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Check if weekday (Monday=0, Sunday=6)
        is_weekday = now_ist.weekday() < 5
        
        return is_weekday and market_open <= now_ist <= market_close


if __name__ == "__main__":
    # Test the loader
    print("[TEST] Testing Zerodha Data Loader...")
    
    try:
        loader = EnhancedHybridDataLoader()
        
        # Test authentication
        print("[TEST] Testing authentication...")
        loader._ensure_authenticated()
        print("[SUCCESS] Authentication successful!")
        
        # Test data download
        print("[TEST] Testing data download for RELIANCE...")
        data = loader.get_historical_data("RELIANCE", "30day", "15minute")
        
        if not data.empty:
            print(f"[SUCCESS] Downloaded {len(data)} bars")
            print(f"[INFO] Date range: {data.index[0]} to {data.index[-1]}")
            print(f"[INFO] Latest close: {data['close'].iloc[-1]:.2f}")
        else:
            print("[ERROR] No data received")
            
        # Test live price
        if loader.is_market_open():
            print("[TEST] Testing live price...")
            live_data = loader.get_live_price("RELIANCE")
            print(f"[SUCCESS] Live price: {live_data['ltp']:.2f}")
        else:
            print("[INFO] Market closed - skipping live price test")
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        print("[TIP] Make sure to run: python authenticate_zerodha.py first")