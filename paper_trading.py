#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Perfect Trader - Paper Trading System
Complete MTFA strategy simulation with virtual money
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Windows console compatibility
import locale
if sys.platform.startswith('win'):
    locale.setlocale(locale.LC_ALL, 'C')

import pandas as pd
import numpy as np
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
import pytz
import requests
import webbrowser
from urllib.parse import urlparse, parse_qs
from kiteconnect import KiteConnect
import hashlib
from zerodha_auth import ZerodhaAuth
from reports import reporting

IST = pytz.timezone('Asia/Kolkata')


class ZerodhaAuthenticationError(RuntimeError):
    """Raised when Zerodha authentication is required before proceeding."""

    def __init__(self, message: str = "Zerodha authentication required"):
        super().__init__(message)


class ZerodhaLiveAPI:
    """Professional Zerodha API integration with KiteConnect"""
    
    def __init__(self):
        self.auth = ZerodhaAuth()
        self.kite = None
        self.instruments = {}  # symbol -> instrument_token mapping
        self.instruments_df = None
        self.valid_symbols = set()
        self.symbol_mapping = {}
        self.stock_universe = {}
        self.sector_mapping = {}
        self.rate_limit_count = 0
        self.last_rate_limit_reset = datetime.now()
        self.config_file = Path('zerodha_config.json')
        self.session_file = Path('zerodha_session.json')
        self.instrument_cache_file = Path('instruments_cache.json')

        # Try to attach saved Zerodha session immediately so instrument calls work without extra prompts
        attached = self._auto_attach_session()
        if not attached or self.kite is None:
            raise ZerodhaAuthenticationError(
                "Zerodha authentication required. Run: python authenticate_zerodha.py"
            )

        # Pre-load static resources for symbol validation
        self.load_stock_universe()
        self._load_instruments_cache()
    
    @classmethod
    def setup_config(cls, api_key: str, api_secret: str):
        """Create configuration file for easy setup"""
        config_data = {
            'api_key': api_key,
            'api_secret': api_secret,
            'created_at': datetime.now().isoformat(),
            'instructions': {
                'usage': 'This file stores your Zerodha API credentials',
                'get_credentials': 'Get your API key and secret from https://kite.trade/',
                'security': 'Keep this file secure and do not share it'
            }
        }
        
        config_file = Path('zerodha_config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"[SETUP] ✅ Configuration saved to {config_file}")
        print(f"[SETUP] API Key: {api_key}")
        print(f"[SETUP] You can now use the bot without entering credentials each time")
        return config_file
    
    def load_config(self):
        """Load API credentials from config file"""
        try:
            if not self.config_file.exists():
                return False
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            self.api_key = config.get('api_key')
            self.api_secret = config.get('api_secret')
            
            if self.api_key and self.api_secret:
                print(f"[CONFIG] ✅ Loaded credentials from {self.config_file}")
                return True
            
        except Exception as e:
            print(f"[CONFIG] Error loading config: {e}")
        
        return False
        
    def authenticate(self, api_key: str = None, api_secret: str = None):
        """Complete Zerodha authentication with proper session management"""
        
        # Try to load credentials from config file first
        if not api_key and not api_secret:
            if self.load_config():
                print(f"[AUTH] Using saved credentials")
            else:
                print(f"[AUTH] No saved credentials found")
                print(f"[AUTH] Please provide API key and secret")
                return False
        else:
            self.api_key = api_key
            self.api_secret = api_secret
        
        # Try to load existing session
        if self._load_existing_session():
            return True
        
        if not api_secret:
            print(f"[ERROR] API Secret is required for authentication")
            print(f"[INFO] Get both API Key and Secret from: https://kite.trade/")
            return False
        
        # Step 1: Initialize KiteConnect
        self.kite = KiteConnect(api_key=api_key)
        
        # Step 2: Generate login URL
        login_url = self.kite.login_url()
        
        print(f"\n[AUTH] Zerodha Authentication Required")
        print(f"[AUTH] 1. Opening browser for login...")
        print(f"[AUTH] 2. Login with your Zerodha credentials")
        print(f"[AUTH] 3. Authorize the application")
        print(f"[AUTH] 4. Copy the complete URL after authorization")
        print("-" * 60)
        
        # Open browser
        webbrowser.open(login_url)
        
        # Get callback URL from user
        callback_url = input("[AUTH] Paste the complete redirect URL here: ").strip()
        
        # Extract request token
        try:
            parsed_url = urlparse(callback_url)
            query_params = parse_qs(parsed_url.query)
            
            if 'request_token' not in query_params:
                raise Exception("Request token not found in URL")
                
            request_token = query_params['request_token'][0]
            
            # Step 3: Generate session
            data = self.kite.generate_session(request_token, api_secret=api_secret)
            self.access_token = data["access_token"]
            
            # Step 4: Set access token
            self.kite.set_access_token(self.access_token)
            
            # Step 5: Save session for reuse
            self._save_session()
            
            print(f"[AUTH] ✅ Authentication successful!")
            print(f"[AUTH] Access token: {self.access_token[:20]}...")
            
            return True
            
        except Exception as e:
            print(f"[AUTH] ❌ Authentication failed: {e}")
            print(f"[AUTH] Please check your API credentials and try again")
            return False
            
    def _load_existing_session(self) -> bool:
        """Load existing session if valid and test it"""
        try:
            if not self.session_file.exists():
                print(f"[AUTH] No existing session found")
                return False
                
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if session has required fields
            if 'access_token' not in session_data or 'api_key' not in session_data:
                print(f"[AUTH] Invalid session data")
                return False
            
            # Check if API key matches
            if session_data['api_key'] != self.api_key:
                print(f"[AUTH] API key mismatch in saved session")
                return False
            
            # Check session age (Zerodha tokens are valid until 6:00 AM next day)
            session_time = datetime.fromisoformat(session_data['created_at'])
            now = datetime.now()
            
            # Calculate next 6:00 AM from session creation
            next_6am = session_time.replace(hour=6, minute=0, second=0, microsecond=0)
            if session_time.hour >= 6:  # If created after 6 AM, expires next day at 6 AM
                next_6am += timedelta(days=1)
            
            if now >= next_6am:
                print(f"[AUTH] Session expired at {next_6am.strftime('%Y-%m-%d 06:00:00')}")
                return False
            
            # Restore session data
            self.access_token = session_data['access_token']
            self.api_secret = session_data.get('api_secret')
            
            # Initialize KiteConnect with existing token
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            
            # Test the session by making an API call
            try:
                profile = self.kite.profile()
                expires_at = next_6am.strftime('%Y-%m-%d 06:00:00')
                print(f"[AUTH] ✅ Session restored for: {profile['user_name']}")
                print(f"[AUTH] Session expires at: {expires_at}")
                return True
                
            except Exception as api_error:
                print(f"[AUTH] Session test failed: {api_error}")
                print(f"[AUTH] Removing invalid session")
                self.session_file.unlink(missing_ok=True)
                return False
            
        except Exception as e:
            print(f"[AUTH] Error loading session: {e}")
            return False
    
    def _save_session(self):
        """Save session for reuse with comprehensive data"""
        try:
            # Get user profile for session validation
            profile = self.kite.profile() if self.kite else {}
            
            # Calculate session expiry (6:00 AM next day for Zerodha)
            now = datetime.now()
            next_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if now.hour >= 6:  # If after 6 AM, expires next day at 6 AM
                next_6am += timedelta(days=1)
            
            session_data = {
                'access_token': self.access_token,
                'api_key': self.api_key,
                'api_secret': self.api_secret,
                'created_at': now.isoformat(),
                'expires_at': next_6am.isoformat(),
                'user_name': profile.get('user_name', 'Unknown'),
                'user_id': profile.get('user_id', 'Unknown'),
                'broker': profile.get('broker', 'ZERODHA'),
                'session_version': '2.0'  # For future compatibility
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            print(f"[AUTH] ✅ Session saved for: {profile.get('user_name', 'Unknown')}")
            print(f"[AUTH] Session valid until: {next_6am.strftime('%Y-%m-%d 06:00:00')}")
                
        except Exception as e:
            print(f"[AUTH] Failed to save session: {e}")
    
    def get_session_status(self):
        """Get current session status"""
        if not self.session_file.exists():
            return {
                'active': False,
                'message': 'No session found'
            }
        
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            created_at = datetime.fromisoformat(session_data['created_at'])
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            now = datetime.now()
            
            is_active = now < expires_at
            time_left = expires_at - now if is_active else timedelta(0)
            
            return {
                'active': is_active,
                'user_name': session_data.get('user_name', 'Unknown'),
                'created_at': created_at,
                'expires_at': expires_at,
                'time_left': str(time_left).split('.')[0],  # Remove microseconds
                'message': f"Session {'active' if is_active else 'expired'}"
            }
            
        except Exception as e:
            return {
                'active': False,
                'message': f'Error reading session: {e}'
            }
    
    def clear_session(self):
        """Clear saved session"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                print(f"[AUTH] Session cleared")
            else:
                print(f"[AUTH] No session to clear")
        except Exception as e:
            print(f"[AUTH] Error clearing session: {e}")
        
    def load_instruments(self, force_refresh: bool = False):
        """Backward-compatible wrapper that delegates to load_all_instruments."""
        return self.load_all_instruments(force_refresh=force_refresh)

    def _auto_attach_session(self) -> bool:
        """Attach an existing Zerodha session so that instrument lookups work instantly."""
        try:
            kite = self.auth.get_kite_instance()
            if kite:
                self.kite = kite
                # These attributes are convenient later when refreshing sessions
                self.api_key = getattr(self.auth, 'api_key', None)
                self.access_token = getattr(self.auth, 'access_token', None)
                print(f"[AUTH] Using saved Zerodha session")
                return True
        except Exception as exc:
            print(f"[AUTH] Unable to attach saved session: {exc}")
        return False

    def load_stock_universe(self) -> bool:
        """Load sector-wise stock universe for better validation and reporting."""
        try:
            universe_path = Path('stock_universe_by_sector.json')
            if not universe_path.exists():
                return False
            data = json.loads(universe_path.read_text(encoding='utf-8'))
            self.stock_universe = {}
            self.sector_mapping = {}
            total_symbols = 0
            for sector, payload in data.items():
                sector_info = {
                    'description': payload.get('description', ''),
                    'large_cap': payload.get('large_cap', []),
                    'mid_cap': payload.get('mid_cap', []),
                    'small_cap': payload.get('small_cap', []),
                }
                self.stock_universe[sector] = sector_info
                for cap_bucket, symbols in (
                    ('LARGE', sector_info['large_cap']),
                    ('MID', sector_info['mid_cap']),
                    ('SMALL', sector_info['small_cap']),
                ):
                    for symbol in symbols:
                        total_symbols += 1
                        self.sector_mapping[symbol] = {
                            'sector': sector,
                            'market_cap': cap_bucket,
                        }
            if total_symbols:
                print(f"[UNIVERSE] Loaded {total_symbols} symbols across {len(self.stock_universe)} sectors")
            return bool(total_symbols)
        except Exception as exc:
            print(f"[UNIVERSE] Failed to load stock universe: {exc}")
            return False

    def _save_instruments_cache(self):
        """Persist instrument metadata so we can validate symbols offline."""
        try:
            snapshot = {
                'timestamp': datetime.now(IST).isoformat(),
                'valid_symbols': sorted(self.valid_symbols),
                'symbol_mapping': self.symbol_mapping,
                'instruments': self.instruments,
            }
            self.instrument_cache_file.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
            print(f"[CACHE] Saved {len(self.valid_symbols)} symbols to instruments cache")
        except Exception as exc:
            print(f"[CACHE] Unable to save instruments cache: {exc}")

    def _load_instruments_cache(self) -> bool:
        """Load instrument metadata from cache if it is still fresh."""
        try:
            if not self.instrument_cache_file.exists():
                return False
            data = json.loads(self.instrument_cache_file.read_text(encoding='utf-8'))
            timestamp = data.get('timestamp')
            if timestamp:
                cached_at = datetime.fromisoformat(timestamp)
                age_hours = (datetime.now(IST) - cached_at).total_seconds() / 3600
                if age_hours > 24:
                    print(f"[CACHE] Instruments cache is {age_hours:.1f}h old - refresh recommended")
                else:
                    print(f"[CACHE] Loaded instruments cache ({age_hours:.1f}h old)")
            self.valid_symbols = set(data.get('valid_symbols', []))
            self.symbol_mapping = data.get('symbol_mapping', {})
            self.instruments = data.get('instruments', {})
            return bool(self.valid_symbols)
        except Exception as exc:
            print(f"[CACHE] Failed to load instruments cache: {exc}")
            return False

    def load_all_instruments(self, force_refresh: bool = False) -> bool:
        """Download the latest instrument master and prepare validation helpers."""
        if self.valid_symbols and not force_refresh:
            return True

        if not self.kite:
            if not self._auto_attach_session():
                print(f"[INSTRUMENTS] No live session - using cached symbols if available")
                return self._load_instruments_cache()

        try:
            print(f"[INSTRUMENTS] Fetching instruments from Zerodha...")
            nse_instruments = self.kite.instruments("NSE")
            if not nse_instruments:
                raise ValueError("Empty response from Zerodha")

            df = pd.DataFrame(nse_instruments)
            if df.empty:
                raise ValueError("Instrument dataframe is empty")

            # Keep only equity symbols for NSE
            equity_df = df[(df['instrument_type'] == 'EQ') & (df['exchange'] == 'NSE')]
            self.instruments_df = equity_df

            instruments = {}
            valid_symbols = set()
            symbol_mapping = {}

            for row in equity_df.itertuples():
                symbol = getattr(row, 'tradingsymbol')
                token = int(getattr(row, 'instrument_token'))
                instruments[symbol] = token
                valid_symbols.add(symbol)

                # Normalised variations to aid lookups
                if symbol.endswith('-EQ'):
                    symbol_mapping[symbol[:-3]] = symbol
                cleaned = symbol.replace('-', '')
                if cleaned != symbol:
                    symbol_mapping[cleaned] = symbol

            self.instruments = instruments
            self.valid_symbols = valid_symbols
            self.symbol_mapping = symbol_mapping

            print(f"[INSTRUMENTS] Loaded {len(self.valid_symbols)} NSE equity symbols")
            self._save_instruments_cache()
            return True

        except Exception as exc:
            print(f"[INSTRUMENTS] Failed to refresh instruments: {exc}")
            return self._load_instruments_cache()

    def validate_symbol(self, symbol: str) -> str | None:
        """Return a vetted Zerodha symbol or None if no match is found."""
        if not symbol:
            return None

        if not self.valid_symbols:
            self.load_all_instruments()

        candidate = symbol.strip().upper()
        if candidate in self.valid_symbols:
            return candidate

        if candidate in self.symbol_mapping:
            return self.symbol_mapping[candidate]

        variations = {
            candidate.replace('_', '-'),
            candidate.replace('-', ''),
            f"{candidate}-EQ" if not candidate.endswith('-EQ') else candidate[:-3],
        }

        for variant in variations:
            if variant in self.valid_symbols:
                return variant
            if variant in self.symbol_mapping:
                return self.symbol_mapping[variant]

        return None

    def validate_watchlist(self, symbols: list[str]) -> dict:
        """Validate a list of symbols and provide mapping details."""
        results = {
            'valid': [],
            'invalid': [],
            'mapped': {},
        }

        seen = set()
        for raw_symbol in symbols:
            if not raw_symbol:
                continue
            validated = self.validate_symbol(raw_symbol)
            if validated:
                if validated not in seen:
                    results['valid'].append(validated)
                    seen.add(validated)
                if validated != raw_symbol:
                    results['mapped'][raw_symbol] = validated
            else:
                results['invalid'].append(raw_symbol)
        return results

    def validate_watchlist_by_sector(self, symbols: list[str]) -> dict:
        """Validate symbols and include sector breakdown when available."""
        base = self.validate_watchlist(symbols)
        by_sector: dict[str, list[str]] = {}
        for symbol in base['valid']:
            sector_info = self.get_symbol_sector(symbol)
            sector_key = sector_info.get('sector', 'UNKNOWN') if sector_info else 'UNKNOWN'
            by_sector.setdefault(sector_key, []).append(symbol)
        base['by_sector'] = by_sector
        return base

    def get_symbol_sector(self, symbol: str) -> dict:
        """Return sector metadata for a symbol if present in the universe file."""
        if symbol in self.sector_mapping:
            return self.sector_mapping[symbol]
        if symbol in self.symbol_mapping:
            mapped = self.symbol_mapping[symbol]
            return self.sector_mapping.get(mapped, {})
        return {}
    
    def get_live_price(self, symbol: str) -> float:
        """Get real-time price from Zerodha"""
        try:
            # Rate limiting (Zerodha allows 3 requests/second)
            if self.rate_limit_count >= 2:  # Conservative limit
                if (datetime.now() - self.last_rate_limit_reset).seconds < 1:
                    return 0  # Rate limited
                else:
                    self.rate_limit_count = 0
                    self.last_rate_limit_reset = datetime.now()
            
            if not self.kite:
                print(f"[ERROR] Not authenticated")
                return 0
            
            lookup_symbol = symbol
            if lookup_symbol not in self.instruments:
                # Try to validate/normalise the symbol and reload instruments if needed
                validated = self.validate_symbol(symbol)
                if validated and validated in self.instruments:
                    lookup_symbol = validated
                else:
                    self.load_all_instruments()
                    validated = self.validate_symbol(symbol)
                    if validated and validated in self.instruments:
                        lookup_symbol = validated
            
            if lookup_symbol not in self.instruments:
                print(f"[ERROR] Instrument token not found for {symbol}")
                return 0

            instrument_token = self.instruments[lookup_symbol]

            # Get live quote
            quote = self.kite.ltp(f"NSE:{lookup_symbol}")
            
            if f"NSE:{lookup_symbol}" in quote:
                price = quote[f"NSE:{lookup_symbol}"]["last_price"]
                self.rate_limit_count += 1
                print(f"[ZERODHA] {lookup_symbol}: Rs.{price:.2f} (REAL-TIME)")
                return price
            
            return 0
            
        except Exception as e:
            print(f"[ZERODHA ERROR] {symbol}: {e}")
            return 0
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now(IST)
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        is_weekday = now.weekday() < 5
        return is_weekday and market_open <= now <= market_close
    
    def get_profile(self):
        """Get user profile for verification"""
        try:
            if self.kite:
                return self.kite.profile()
        except Exception as e:
            print(f"[PROFILE ERROR] {e}")
        return None


class PerfectTraderPaperTrading:
    """
    Complete paper trading system with MTFA strategy
    """
    
    def __init__(self, initial_capital: float = 250000, use_live_data: bool = True, force_fresh_start: bool = False,
                 dry_run: bool = False, allow_after_hours: bool = False):
        # Live data configuration
        self.use_live_data = use_live_data
        self.live_api = None
        self.price_cache = {}  # Cache recent prices to reduce API calls
        self.last_cache_update = {}

        # Trading mode controls
        self.enable_trading = not dry_run  # can be overridden by market-hours logic
        self.dry_run_configured = dry_run
        self.allow_after_hours = allow_after_hours

        # Initialize base portfolio defaults BEFORE loading saved state
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.available_capital = initial_capital
        self.positions = {}
        self.trade_history = []

    # Initialize live API if requested (now handled by main() authentication)
        if use_live_data:
            try:
                print(f"[LIVE] Initializing Zerodha connection...")
                self.live_api = ZerodhaLiveAPI()
                print(f"[LIVE] Zerodha connection established")
            except ZerodhaAuthenticationError as exc:
                print(f"[LIVE] [ERROR] {exc}")
                print(f"[LIVE] Please authenticate before starting the bot.")
                raise
            except Exception as e:
                print(f"[LIVE] [ERROR] Zerodha connection failed: {e}")
                print(f"[LIVE] Falling back to cached data only")
                self.use_live_data = False
                self.live_api = None
        else:
            print(f"[LIVE] Using cached data only")
            self.use_live_data = False
            self.live_api = None
        
        # Portfolio persistence files
        self.portfolio_file = Path('paper_trading_portfolio.json')
        self.daily_state_file = Path('daily_portfolio_state.json')
        
        # Store the force_fresh_start flag
        self.force_fresh_start = force_fresh_start
        
        # Load existing portfolio (if available) to override defaults
        self._load_portfolio_state()
        
        # Load config and build validated watchlist
        with open('hybrid_config.json', 'r') as f:
            self.config = json.load(f)

        self.watchlist = []
        self.sector_mapping = {}
        self._load_and_validate_watchlist()
        self.max_positions = self.config.get('max_positions', 20)
        self.risk_per_trade = 0.01
        
        # Costs
        self.transaction_cost = 0.002
        self.slippage = 0.001
        
        # Initialize stats if not loaded
        if not hasattr(self, 'total_trades'):
            self.total_trades = 0
            self.winning_trades = 0
        
        self.session_start_time = datetime.now(IST)
        self.last_trading_date = datetime.now(IST).date()
        
        # Try to load MTFA strategy
        self.strategy = self._load_strategy()

        # Scan counter persistence
        self.scan_counter_file = Path('scan_counter.json')
        self.session_scan_count = 0

    def _load_scan_counter(self) -> dict:
        """Load or initialize the daily scan counter (per local IST day)."""
        today = datetime.now(IST).date().isoformat()
        try:
            if self.scan_counter_file.exists():
                data = json.load(self.scan_counter_file.open('r', encoding='utf-8'))
                # Reset if date changed
                if data.get('date') != today:
                    data = {'date': today, 'count': 0}
            else:
                data = {'date': today, 'count': 0}
        except Exception:
            data = {'date': today, 'count': 0}
        return data

    def _save_scan_counter(self, data: dict):
        try:
            json.dump(data, self.scan_counter_file.open('w', encoding='utf-8'), indent=2)
        except Exception:
            pass

    def _increment_daily_scan_counter(self) -> int:
        """Increment and return today's scan count (persistent)."""
        data = self._load_scan_counter()
        data['count'] = int(data.get('count', 0)) + 1
        self._save_scan_counter(data)
        return data['count']

    def _load_and_validate_watchlist(self):
        """Load watchlist symbols and ensure they match live market tickers."""
        fallback_watchlist = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'SBIN', 'BHARTIARTL', 'ITC', 'KOTAKBANK']
        original_watchlist = list(self.config.get('watchlist', []))
        watchlist_source = 'hybrid_config.json'

        # If sector universe is available, prefer that so symbols stay curated
        if self.live_api and self.live_api.stock_universe:
            combined = []
            sector_mapping = {}
            for sector, payload in self.live_api.stock_universe.items():
                for cap_bucket in ('large_cap', 'mid_cap', 'small_cap'):
                    symbols = payload.get(cap_bucket, [])
                    if not isinstance(symbols, list):
                        continue
                    bucket_label = cap_bucket.replace('_cap', '').upper()
                    for symbol in symbols:
                        if symbol not in combined:
                            combined.append(symbol)
                            sector_mapping[symbol] = {
                                'sector': sector,
                                'market_cap': bucket_label,
                            }
            if combined:
                original_watchlist = combined
                self.sector_mapping = sector_mapping
                watchlist_source = 'stock_universe_by_sector.json'

        if not original_watchlist:
            print(f"[WATCHLIST] No symbols configured - using fallback large caps")
            original_watchlist = fallback_watchlist[:]

        validation_result = None
        final_watchlist = list(dict.fromkeys(original_watchlist))

        if self.live_api:
            self.live_api.load_all_instruments()
            try:
                validation_result = self.live_api.validate_watchlist_by_sector(final_watchlist)
                final_watchlist = validation_result['valid']

                if validation_result['invalid']:
                    print(f"[WATCHLIST] Removed {len(validation_result['invalid'])} invalid symbols")
                if validation_result['mapped']:
                    print(f"[WATCHLIST] Normalised {len(validation_result['mapped'])} symbols to official tickers")

                # Rebuild sector mapping for valid symbols only
                validated_mapping = {}
                for symbol in final_watchlist:
                    sector_info = self.live_api.get_symbol_sector(symbol)
                    if not sector_info:
                        sector_info = self.sector_mapping.get(symbol, {'sector': 'UNKNOWN', 'market_cap': 'UNKNOWN'})
                    validated_mapping[symbol] = {
                        'sector': sector_info.get('sector', 'UNKNOWN'),
                        'market_cap': sector_info.get('market_cap', 'UNKNOWN'),
                    }
                self.sector_mapping = validated_mapping
            except Exception as exc:
                print(f"[WATCHLIST] Validation failed: {exc}")

        if not final_watchlist:
            print(f"[WATCHLIST] Validation left no symbols, reverting to fallback list")
            final_watchlist = fallback_watchlist[:]
            self.sector_mapping = {symbol: {'sector': 'UNKNOWN', 'market_cap': 'UNKNOWN'} for symbol in final_watchlist}

        if not self.sector_mapping:
            self.sector_mapping = {symbol: {'sector': 'UNKNOWN', 'market_cap': 'UNKNOWN'} for symbol in final_watchlist}
        else:
            self.sector_mapping = {
                symbol: self.sector_mapping.get(symbol, {'sector': 'UNKNOWN', 'market_cap': 'UNKNOWN'})
                for symbol in final_watchlist
            }

        self.watchlist = final_watchlist
        print(f"[WATCHLIST] Ready with {len(self.watchlist)} symbols ({watchlist_source})")

        # Persist validated watchlist so other modules (like auto_update_data) pick up the latest list
        self._persist_watchlist_update(watchlist_source, validation_result)

    def _persist_watchlist_update(self, source: str, validation_result: dict | None):
        """Write the validated watchlist back to the config with a timestamp."""
        config_path = Path('hybrid_config.json')
        try:
            existing_config = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
        except Exception:
            existing_config = {}

        needs_write = (
            existing_config.get('watchlist') != self.watchlist
            or existing_config.get('sector_mapping') != self.sector_mapping
        )

        if not needs_write:
            # Nothing material changed; leave config untouched to avoid noisy backups
            return

        backup_path = None

        if config_path.exists():
            try:
                timestamp = datetime.now(IST).strftime('%Y%m%d_%H%M%S')
                backup_path = config_path.with_name(f"hybrid_config_backup_{timestamp}.json")
                backup_path.write_text(config_path.read_text(encoding='utf-8'), encoding='utf-8')
            except Exception as exc:
                print(f"[CONFIG] Failed to create config backup: {exc}")
                backup_path = None

        self.config['watchlist'] = self.watchlist
        self.config['sector_mapping'] = self.sector_mapping
        metadata = {
            'last_validated': datetime.now(IST).isoformat(),
            'source': source,
            'symbol_count': len(self.watchlist),
        }
        if validation_result:
            metadata['invalid_symbols'] = validation_result.get('invalid', [])
            metadata['mapped_symbols'] = validation_result.get('mapped', {})
        self.config['watchlist_metadata'] = metadata

        try:
            config_path.write_text(json.dumps(self.config, indent=2), encoding='utf-8')
            if backup_path:
                print(f"[CONFIG] Watchlist updated and saved ({backup_path.name} backup)")
            else:
                print(f"[CONFIG] Watchlist updated and saved")
        except Exception as exc:
            print(f"[CONFIG] Failed to persist watchlist: {exc}")

    def _print_session_metrics(self):
        """Print capital usage, P&L, and open positions before scans begin."""
        try:
            utilisation = 0.0
            holdings_details = []
            for symbol, pos in self.positions.items():
                qty = pos.get('shares') or pos.get('quantity') or pos.get('qty', 0)
                if not qty:
                    continue
                qty = float(qty)
                entry_price = float(pos.get('avg_price', pos.get('entry_price', 0)))
                current_price = self.get_current_price(symbol)
                if current_price <= 0:
                    current_price = entry_price
                current_value = qty * current_price
                utilised_entry = qty * entry_price
                utilisation += current_value
                pnl = current_value - utilised_entry
                pnl_pct = (pnl / utilised_entry * 100) if utilised_entry else 0.0
                holdings_details.append({
                    'symbol': symbol,
                    'qty': qty,
                    'entry': entry_price,
                    'current': current_price,
                    'value': current_value,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                })

            total_value = self.available_capital + utilisation
            total_pnl = total_value - self.initial_capital
            total_pnl_pct = (total_pnl / self.initial_capital * 100) if self.initial_capital else 0.0

            print(f"[$] Starting Capital: Rs.{self.initial_capital:,.0f}")
            print(f"[CAPITAL] Available: Rs.{self.available_capital:,.0f} | Utilised: Rs.{utilisation:,.0f}")
            print(f"[P&L] Mark-to-market: Rs.{total_pnl:,.0f} ({total_pnl_pct:+.2f}%)")

            if holdings_details:
                print("[HOLDINGS] Open Positions (qty | entry -> current | P&L)")
                for detail in holdings_details:
                    print(
                        f"   {detail['symbol']:<12} | {int(detail['qty']):>4} | "
                        f"Rs.{detail['entry']:>8.2f} → Rs.{detail['current']:>8.2f} | "
                        f"Rs.{detail['pnl']:>8.0f} ({detail['pnl_pct']:+.2f}%)"
                    )
            else:
                print("[HOLDINGS] No open positions")

            if self.total_trades > 0:
                win_rate = (self.winning_trades / self.total_trades * 100)
                print(f"[STATS] Trades: {self.total_trades} | Win Rate: {win_rate:.1f}%")
            else:
                print("[STATS] No trades recorded yet")

        except Exception as exc:
            print(f"[SESSION] Unable to compute detailed metrics: {exc}")

    def _find_latest_portfolio_snapshot(self) -> tuple[Path | None, dict | None]:
        """Return path and contents of the freshest portfolio snapshot (main or backups)."""
        candidates: list[tuple[Path, dict, datetime, float]] = []

        def _load_snapshot_file(path: Path):
            try:
                payload = json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                return
            last_dt_raw = payload.get('last_trading_date')
            last_dt = None
            if last_dt_raw:
                try:
                    last_dt = datetime.fromisoformat(last_dt_raw)
                except Exception:
                    last_dt = None
            if isinstance(last_dt, datetime):
                if last_dt.tzinfo:
                    last_dt = last_dt.astimezone(IST)
                else:
                    last_dt = last_dt.replace(tzinfo=IST)
            else:
                last_dt = datetime.min.replace(tzinfo=IST)
            candidates.append((path, payload, last_dt, path.stat().st_mtime))

        # Primary portfolio file
        if self.portfolio_file.exists():
            _load_snapshot_file(self.portfolio_file)

        # Timestamped backups
        backups_dir = Path('Reports Day Trading')
        if backups_dir.exists():
            for backup_path in backups_dir.glob('paper_trading_portfolio_*.json.bak'):
                _load_snapshot_file(backup_path)

        if not candidates:
            return None, None

        # Pick snapshot with latest trading date, breaking ties with file mtime
        best_path, best_payload, _, _ = max(candidates, key=lambda item: (item[2], item[3]))
        return best_path, best_payload

    def _apply_portfolio_snapshot(self, payload: dict, label: str):
        """Populate in-memory state from a persisted snapshot."""
        self.initial_capital = payload.get('initial_capital', self.initial_capital)
        self.capital = payload.get('capital', self.capital)
        self.available_capital = payload.get('available_capital', self.available_capital)
        self.positions = payload.get('positions', {}) or {}
        self.trade_history = payload.get('trade_history', []) or []
        self.total_trades = payload.get('total_trades', 0)
        self.winning_trades = payload.get('winning_trades', 0)

        last_dt_raw = payload.get('last_trading_date')
        if last_dt_raw:
            try:
                last_dt = datetime.fromisoformat(last_dt_raw)
                if last_dt.tzinfo:
                    last_dt = last_dt.astimezone(IST)
                else:
                    last_dt = last_dt.replace(tzinfo=IST)
                self.last_trading_date = last_dt.date()
            except Exception:
                pass

        portfolio_value = payload.get('total_portfolio_value')
        if portfolio_value is None:
            portfolio_value = self.available_capital
            for pos in self.positions.values():
                qty = pos.get('shares') or pos.get('quantity') or pos.get('qty', 0)
                avg_price = pos.get('avg_price') or pos.get('entry_price', 0)
                if qty and avg_price:
                    try:
                        portfolio_value += float(qty) * float(avg_price)
                    except Exception:
                        continue

        print(f"[PORTFOLIO] {label}: Rs.{portfolio_value:,.0f} | Positions: {len(self.positions)}")

    def _load_portfolio_state(self):
        """Load portfolio state from persistence files"""
        today = datetime.now(IST).date()
        
        # Force fresh start if requested
        if self.force_fresh_start:
            print(f"[FRESH START] Ignoring existing portfolio data")
            return
        
        snapshot_path, snapshot_payload = self._find_latest_portfolio_snapshot()
        if not snapshot_payload:
            print(f"[PORTFOLIO] No prior snapshot found - starting fresh")
            return

        try:
            source = "primary snapshot" if snapshot_path == self.portfolio_file else f"backup ({snapshot_path.name})"
            self._apply_portfolio_snapshot(snapshot_payload, f"Restored {source}")

            # Ensure main portfolio file mirrors the restored snapshot for continuity
            if snapshot_path != self.portfolio_file:
                try:
                    self.portfolio_file.write_text(json.dumps(snapshot_payload, indent=2), encoding='utf-8')
                    print(f"[PORTFOLIO] Synced main snapshot from {snapshot_path.name}")
                except Exception as exc:
                    print(f"[PORTFOLIO] Warning: could not sync main snapshot: {exc}")
        except Exception as e:
            print(f"[WARNING] Error loading portfolio state: {e}")
            print("[RESET] Starting fresh with default capital")
    
    def _save_portfolio_state(self, is_end_of_day=False):
        """Save current portfolio state for persistence"""
        try:
            # In dry-run mode, avoid overwriting a real portfolio with an empty snapshot
            if getattr(self, 'dry_run_configured', False):
                if not self.positions and self.available_capital == self.initial_capital:
                    print("[DRY-RUN] Skipping portfolio save (no positions, full cash)")
                    return

            # Calculate total portfolio value
            total_value = self.available_capital
            for symbol, position in self.positions.items():
                current_price = self.get_current_price(symbol)
                if current_price > 0:
                    total_value += position['shares'] * current_price
            
            state = {
                'last_trading_date': datetime.now(IST).isoformat(),
                'session_end_time': datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                'initial_capital': self.initial_capital,
                'capital': self.capital,
                'available_capital': self.available_capital,
                'positions': self.positions,
                'trade_history': self.trade_history,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'total_portfolio_value': total_value,
                'end_of_day_balance': total_value if is_end_of_day else self.available_capital
            }
            
            # Backup current file (if exists) with timestamp for recovery
            try:
                if self.portfolio_file.exists():
                    ts = datetime.now(IST).strftime('%Y%m%d_%H%M%S')
                    # Save backup files to Reports Day Trading folder
                    reports_dir = Path('Reports Day Trading')
                    reports_dir.mkdir(exist_ok=True)  # Ensure directory exists
                    backup = reports_dir / f"paper_trading_portfolio_{ts}.json.bak"
                    backup.write_text(self.portfolio_file.read_text(encoding='utf-8'), encoding='utf-8')
            except Exception:
                pass

            with open(self.portfolio_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            if is_end_of_day:
                print(f"[SAVE] End-of-day portfolio: Rs.{total_value:,.0f}")
            else:
                print(f"[SAVE] Portfolio state: Rs.{total_value:,.0f} total value")
                
        except Exception as e:
            print(f"[ERROR] Saving portfolio state: {e}")
        
    def _load_strategy(self):
        """Load MTFA strategy with fallback"""
        try:
            from mtfa_strategy import MTFAStrategy
            strategy = MTFAStrategy()
            
            # Override data loading to use cached data only
            def cached_load(symbol):
                data = {}
                cache_dir = Path('data_cache') / symbol
                for timeframe in ['daily', '60min', '15min']:
                    cache_file = cache_dir / f"{timeframe}.csv"
                    if cache_file.exists():
                        try:
                            df = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                            if not df.empty:
                                data[timeframe] = df
                        except:
                            pass
                return data
            
            strategy._load_mtf_data = cached_load
            return strategy
        except:
            return None
    
    def get_signal(self, symbol: str):
        """Get trading signal"""
        if self.strategy:
            try:
                return self.strategy.analyze(symbol)
            except:
                pass
        
        # Simple fallback signal
        try:
            cache_file = Path('data_cache') / symbol / '15min.csv'
            if not cache_file.exists():
                return {'signal': 'HOLD', 'score': 50, 'entry_price': 0}
            
            data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
            if len(data) < 50:
                return {'signal': 'HOLD', 'score': 50, 'entry_price': 0}
            
            current_price = data['close'].iloc[-1]
            sma_20 = data['close'].rolling(20).mean().iloc[-1]
            sma_50 = data['close'].rolling(50).mean().iloc[-1]
            
            # Generate simple signal
            if current_price > sma_20 > sma_50:
                signal = 'BUY'
                score = 70
            elif current_price < sma_20 < sma_50:
                signal = 'SELL'
                score = 30
            else:
                signal = 'HOLD'
                score = 50
            
            return {
                'signal': signal,
                'score': score,
                'entry_price': current_price,
                'stop_loss': current_price * 0.98,
                'target': current_price * 1.03
            }
        except:
            return {'signal': 'HOLD', 'score': 50, 'entry_price': 0}
    
    def get_current_price(self, symbol: str, add_slippage: bool = False):
        """Get current price with live data and realistic trading friction"""
        price = 0.0
        
        # FORCE live data during market hours (critical for accuracy)
        market_open = self.live_api.is_market_open() if self.live_api else self._is_market_open_basic()
        
        # Try live data first if market is open
        try:
            if market_open and self.use_live_data and self.live_api:
                # Zerodha API path
                cache_key = symbol
                now = datetime.now()
                if (
                    cache_key in self.price_cache and
                    cache_key in self.last_cache_update and
                    (now - self.last_cache_update[cache_key]).seconds < 30
                ):
                    price = float(self.price_cache[cache_key])
                    print(f"[CACHE] {symbol}: Rs.{price:.2f} (30s cache)")
                else:
                    # Get fresh live price - CRITICAL for accuracy
                    live_price = self.live_api.get_live_price(symbol)
                    if live_price > 0:
                        price = float(live_price)
                        self.price_cache[cache_key] = price
                        self.last_cache_update[cache_key] = now
        except Exception:
            # ignore and fallback
            price = 0.0

        # Fallback: use latest cached 15min close if live not available
        if price <= 0:
            try:
                cache_file = Path('data_cache') / symbol / '15min.csv'
                if cache_file.exists():
                    data = pd.read_csv(cache_file, index_col='datetime', parse_dates=True)
                    if not data.empty and 'close' in data.columns:
                        price = float(data['close'].iloc[-1])
            except Exception:
                pass

        # If still not available, return 0
        if price <= 0:
            return 0

        # Apply trading friction if requested
        if add_slippage:
            return self._apply_trading_friction(price, symbol)
        return round(price, 2)
    
    def _apply_trading_friction(self, price: float, symbol: str) -> float:
        """Apply realistic slippage and bid-ask spread"""
        # Base slippage (0.05%)
        base_slippage = 0.0005
        
        # Variable slippage based on volatility and liquidity
        # Large cap: lower slippage, Small cap: higher slippage
        if symbol in ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']:
            volatility_factor = 1.0  # Large cap
        elif len([s for s in self.watchlist if s == symbol]) < 50:
            volatility_factor = 1.5  # Mid cap
        else:
            volatility_factor = 2.0  # Small cap
        
        # Random slippage component (market impact)
        random_slippage = random.uniform(0, base_slippage * volatility_factor)
        
        # Bid-ask spread simulation (0.01-0.05%)
        spread = random.uniform(0.0001, 0.0005) * volatility_factor
        
        # Apply friction (always increases cost)
        total_friction = random_slippage + spread
        adjusted_price = price * (1 + total_friction)
        
        return round(adjusted_price, 2)
    
    def _is_market_open_basic(self) -> bool:
        """Basic market hours check without API"""
        now = datetime.now(IST)
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
        is_weekday = now.weekday() < 5
        return is_weekday and market_open <= now <= market_close
    
    def execute_buy(self, symbol: str, signal_result: dict):
        """Execute virtual buy order"""
        if not self.enable_trading:
            print(f"[DRY-RUN] BUY skipped for {symbol}")
            return False
        if len(self.positions) >= self.max_positions:
            return False
        
        price = signal_result.get('entry_price', 0)
        if price <= 0:
            return False
            
        # Get realistic entry price with slippage
        entry_price = self.get_current_price(symbol, add_slippage=True)
        stop_loss = signal_result.get('stop_loss', entry_price * 0.98)
        target = signal_result.get('target', entry_price * 1.03)
        
        # Position sizing - Use available capital, not total capital
        risk_amount = self.available_capital * self.risk_per_trade
        risk_per_share = entry_price - stop_loss
        shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Check capital
        cost = shares * entry_price * (1 + self.transaction_cost)
        if cost > self.available_capital or shares <= 0:
            return False
            
        # Get trailing stop parameters from config
        trailing_config = self.config.get('strategy', {})
        trailing_enabled = trailing_config.get('trailing_stop_enabled', True)
        trailing_percent = trailing_config.get('trailing_stop_percent', 2.0)
        activation_percent = trailing_config.get('trailing_stop_activation_percent', 1.5)
        
        # Create position with trailing stop data
        self.positions[symbol] = {
            'entry_time': datetime.now(IST).isoformat(),
            'entry_price': entry_price,
            'shares': shares,
            'stop_loss': stop_loss,
            'original_stop_loss': stop_loss,
            'target': target,
            'score': signal_result.get('score', 50),
            'trailing_stop_enabled': trailing_enabled,
            'trailing_stop_percent': trailing_percent / 100,  # Convert to decimal
            'activation_percent': activation_percent / 100,
            'highest_price': entry_price,  # Track highest price for trailing
            'trailing_activated': False
        }
        
        self.available_capital -= cost
        self.total_trades += 1
        
        print(f"[BUY] {symbol} - {shares} shares @ Rs.{entry_price:.2f}")
        print(f"   Stop: Rs.{stop_loss:.2f}, Target: Rs.{target:.2f}")
        # Persist immediately to treat account as original
        try:
            self._save_portfolio_state(is_end_of_day=False)
        except Exception:
            pass
        
        return True
    
    def update_trailing_stops(self):
        """Update trailing stop losses for all positions"""
        for symbol, position in self.positions.items():
            if not position.get('trailing_stop_enabled', False):
                continue
                
            current_price = self.get_current_price(symbol)
            if current_price <= 0:
                continue
                
            entry_price = position['entry_price']
            highest_price = position.get('highest_price', entry_price)
            activation_percent = position.get('activation_percent', 0.015)
            trailing_percent = position.get('trailing_stop_percent', 0.02)
            
            # Update highest price
            if current_price > highest_price:
                position['highest_price'] = current_price
                highest_price = current_price
            
            # Check if trailing should be activated
            profit_percent = (current_price - entry_price) / entry_price
            if not position.get('trailing_activated', False) and profit_percent >= activation_percent:
                position['trailing_activated'] = True
                print(f"[TRAIL] ACTIVATED for {symbol} at {profit_percent*100:.1f}% profit")
            
            # Update trailing stop if activated
            if position.get('trailing_activated', False):
                new_stop = highest_price * (1 - trailing_percent)
                current_stop = position['stop_loss']
                
                # Only move stop up (for long positions)
                if new_stop > current_stop:
                    position['stop_loss'] = new_stop
                    print(f"[TRAIL] STOP updated for {symbol}: Rs.{current_stop:.2f} -> Rs.{new_stop:.2f}")
    
    def execute_sell(self, symbol: str, price: float, reason: str):
        """Execute virtual sell order"""
        if not self.enable_trading:
            print(f"[DRY-RUN] SELL skipped for {symbol} [{reason}]")
            return False
        if symbol not in self.positions:
            return False
            
        position = self.positions[symbol]
        exit_price = price * (1 - self.slippage)
        
        # Calculate P&L
        proceeds = position['shares'] * exit_price * (1 - self.transaction_cost)
        cost = position['shares'] * position['entry_price'] * (1 + self.transaction_cost)
        pnl = proceeds - cost
        pnl_pct = (pnl / cost) * 100
        
        self.available_capital += proceeds
        
        if pnl > 0:
            self.winning_trades += 1
            status = "[+] PROFIT"
        else:
            status = "[-] LOSS"
            
        print(f"{status}: {symbol} @ Rs.{exit_price:.2f} - P&L: Rs.{pnl:,.0f} ({pnl_pct:+.2f}%) [{reason}]")
        
        # Record trade
        self.trade_history.append({
            'symbol': symbol,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        })
        
        del self.positions[symbol]
        # Persist immediately to treat account as original
        try:
            self._save_portfolio_state(is_end_of_day=False)
        except Exception:
            pass
        return True
    
    def scan_and_trade(self):
        """Scan market and execute trades"""
        scan_start = datetime.now(IST)
        print(f"\n[SCAN] MARKET SCAN - {scan_start.strftime('%H:%M:%S')}")
        print(f"   Strategy: {'MTFA' if self.strategy else 'Simple SMA'}")
        print("-" * 50)
        
        signals_found = 0
        buy_opportunities = []
        actions_log = []
        price_fallbacks = []
        errors = []
        
        # Update trailing stops for existing positions first
        if self.positions:
            self.update_trailing_stops()
        
        # Scan all 105 stocks in watchlist
        scan_list = self.watchlist
        
        for i, symbol in enumerate(scan_list, 1):
            try:
                # Show which category we're scanning
                if i <= 35:
                    category = "L"  # Large cap (first 35)
                elif i <= 70:
                    category = "M"  # Mid cap (next 35)
                else:
                    category = "S"  # Small cap (last 35)
                    
                print(f"[{i:3}/{len(scan_list)}] {symbol:<12} {category}", end=" ")
                
                # Check existing position
                if symbol in self.positions:
                    position = self.positions[symbol]
                    current_price = self.get_current_price(symbol)
                    
                    if current_price <= 0:
                        print("NO DATA")
                        continue
                    
                    # Check stop/target
                    if current_price <= position['stop_loss']:
                        if self.execute_sell(symbol, current_price, 'STOP'):
                            actions_log.append({
                                'type': 'SELL', 'symbol': symbol, 'qty': position['shares'],
                                'price_used': round(current_price, 2), 'source': 'live_or_cache',
                                'reason': 'STOP', 'sl': position['stop_loss'], 'tp': position['target']
                            })
                        signals_found += 1
                        print("STOP LOSS")
                    elif current_price >= position['target']:
                        if self.execute_sell(symbol, current_price, 'TARGET'):
                            actions_log.append({
                                'type': 'SELL', 'symbol': symbol, 'qty': position['shares'],
                                'price_used': round(current_price, 2), 'source': 'live_or_cache',
                                'reason': 'TARGET', 'sl': position['stop_loss'], 'tp': position['target']
                            })
                        signals_found += 1
                        print("TARGET HIT")
                    else:
                        pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
                        print(f"HOLD [{pnl_pct:+.1f}%]")
                else:
                    # Get new signal
                    signal_result = self.get_signal(symbol)
                    signal = signal_result.get('signal', 'HOLD')
                    score = signal_result.get('score', 50)
                    
                    if signal == 'BUY':
                        buy_opportunities.append((symbol, signal_result, score))
                        print(f"BUY ({score:.0f})")
                    elif signal == 'SELL':
                        print(f"SELL ({score:.0f})")
                    else:
                        print("HOLD")
                        
            except Exception as e:
                print("ERROR")
        
        # Execute best buy signals
        buy_opportunities.sort(key=lambda x: x[2], reverse=True)
        for symbol, signal_result, score in buy_opportunities[:3]:
            if self.execute_buy(symbol, signal_result):
                actions_log.append({
                    'type': 'BUY', 'symbol': symbol,
                    'qty': self.positions.get(symbol, {}).get('shares', 0),
                    'price_used': self.positions.get(symbol, {}).get('entry_price', 0),
                    'source': 'live_or_cache_slippage',
                    'reason': 'MTFA',
                    'sl': self.positions.get(symbol, {}).get('stop_loss', 0),
                    'tp': self.positions.get(symbol, {}).get('target', 0)
                })
                signals_found += 1
                
        scan_end = datetime.now(IST)
        # Write per-scan report
        try:
            payload = {
                'timestamp_ist': scan_start.isoformat(),
                'watchlist_size': len(self.watchlist),
                'candidates': [s for (s, _, _) in buy_opportunities],
                'actions': actions_log,
                'price_fallbacks': price_fallbacks,
                'errors': errors,
                'durations_ms': {
                    'scan_total': int((scan_end - scan_start).total_seconds() * 1000)
                }
            }
            reporting.write_scan_audit(payload)
        except Exception:
            pass

        if signals_found == 0 and not self.positions:
            print("\n⚪ No trading opportunities found")
    
    def print_status(self):
        """Print current status"""
        # Calculate total portfolio value
        total_value = self.available_capital
        for symbol, position in self.positions.items():
            current_price = self.get_current_price(symbol)
            if current_price > 0:
                total_value += position['shares'] * current_price
                
        total_return = (total_value - self.initial_capital) / self.initial_capital * 100
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        print(f"\n[PORTFOLIO] STATUS")
        print(f"   Value: Rs.{total_value:,.0f} ({total_return:+.2f}%)")
        print(f"   Cash: Rs.{self.available_capital:,.0f}")
        print(f"   Positions: {len(self.positions)}/{self.max_positions}")
        
        # Show detailed position breakdown
        if self.positions:
            print(f"\n[HOLDINGS] CURRENT POSITIONS:")
            total_invested = 0
            for symbol, position in self.positions.items():
                current_price = self.get_current_price(symbol)
                if current_price > 0:
                    shares = position['shares']
                    # Handle different field names for entry price
                    entry_price = position.get('entry_price', position.get('avg_price', 0))
                    if entry_price == 0:
                        continue
                    
                    invested = shares * entry_price
                    current_value = shares * current_price
                    pnl = current_value - invested
                    pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
                    
                    total_invested += invested
                    
                    # Calculate position age
                    entry_time = position.get('entry_time', '')
                    if isinstance(entry_time, str):
                        try:
                            from datetime import datetime
                            if entry_time and len(entry_time) > 10:
                                entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                                age_hours = (datetime.now(IST) - entry_dt.replace(tzinfo=IST)).total_seconds() / 3600
                                if age_hours < 24:
                                    age_str = f"{age_hours:.1f}h"
                                else:
                                    age_str = f"{age_hours/24:.1f}d"
                            else:
                                age_str = "N/A"
                        except:
                            age_str = "N/A"
                    else:
                        age_str = "N/A"
                    
                    # Add trailing stop info
                    trailing_info = ""
                    if position.get('trailing_stop_enabled', False):
                        if position.get('trailing_activated', False):
                            trailing_info = f" | Trail: Rs.{position['stop_loss']:.2f}"
                        else:
                            activation_pct = position.get('activation_percent', 0.015) * 100
                            trailing_info = f" | Trail: {activation_pct:.1f}%+"
                    
                    print(f"   {symbol:<12} | {shares:>3} shares | Entry: Rs.{entry_price:>7.2f} | Current: Rs.{current_price:>7.2f} | P&L: {pnl:>+8.0f} ({pnl_pct:>+5.1f}%) | Age: {age_str}{trailing_info}")
            
            print(f"   {'─'*85}")
            print(f"   {'TOTAL INVESTED':<12} | Rs.{total_invested:>8.0f} | Available Cash: Rs.{self.available_capital:>8.0f}")
        
        if self.total_trades > 0:
            print(f"\n[STATS] TRADING PERFORMANCE:")
            print(f"   Trades: {self.total_trades} | Win Rate: {win_rate:.0f}%")
    
    def _is_market_open(self):
        """Check if market is currently open"""
        now_ist = datetime.now(IST)
        
        # Market hours: 9:15 AM - 3:30 PM IST, Monday-Friday
        market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Check if weekday (Monday=0, Sunday=6)
        is_weekday = now_ist.weekday() < 5
        is_market_hours = market_open <= now_ist <= market_close
        
        return is_weekday and is_market_hours
    
    def _get_market_close_time(self):
        """Get today's market close time"""
        now_ist = datetime.now(IST)
        return now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    
    def _time_until_market_close(self):
        """Get minutes until market closes"""
        if not self._is_market_open():
            return 0
        
        now_ist = datetime.now(IST)
        market_close = self._get_market_close_time()
        remaining = (market_close - now_ist).total_seconds() / 60
        return max(0, remaining)

    def run(self, hours: float = 4.0):
        """Run paper trading session"""
        print("[BOT] PERFECT TRADER - PAPER TRADING")
        print("=" * 50)
        # Show an opening summary of the last saved state before starting scans
        try:
            self._print_opening_summary()
        except Exception:
            pass

        self._print_session_metrics()
        
        print(f"[#] Total Stocks: {len(self.watchlist)} (Large+Mid+Small Cap)")
        print(f"[~] Scans: All {len(self.watchlist)} stocks per cycle")
        print(f"[T] Max Duration: {hours} hours")
        print(f"[~] Scan Interval: 10 minutes")
        print(f"[!] Press Ctrl+C to stop")
        print("=" * 50)
        
        # Check market hours
        now_ist = datetime.now(IST)
        if not self._is_market_open():
            next_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
            if now_ist.hour >= 15:  # After market close, next day
                next_open += timedelta(days=1)

            print(f"\n[X] MARKET IS CLOSED")
            print(f"   Current time: {now_ist.strftime('%H:%M:%S IST')}")
            print(f"   Market hours: 9:15 AM - 3:30 PM IST (Mon-Fri)")
            print(f"   Next open: {next_open.strftime('%Y-%m-%d %H:%M IST')}")

            if self.allow_after_hours:
                print("\n[INFO] After-hours run enabled: DRY-RUN mode (no orders)")
                self.enable_trading = False
            else:
                print("\n[INFO] Exiting. Use --allow-after-hours for dry-run or --dry-run for scans without orders.")
                return
        else:
            remaining_minutes = self._time_until_market_close()
            print(f"\n[+] MARKET IS OPEN")
            print(f"   Current time: {now_ist.strftime('%H:%M:%S IST')}")
            print(f"   Market closes in: {remaining_minutes:.0f} minutes")
            if self.dry_run_configured:
                print("[INFO] DRY-RUN enabled: scans only, no orders will be placed")
                self.enable_trading = False
        
        # Check data
        cache_dir = Path('data_cache')
        if not cache_dir.exists():
            print("\n❌ No data found! Run: python download_historical_data.py")
            return
        
        # Determine session end time
        market_close = self._get_market_close_time()
        user_end_time = datetime.now(IST) + timedelta(hours=hours)
        
        # Use whichever is sooner: market close or user-specified duration
        if self._is_market_open() and market_close < user_end_time:
            end_time = market_close
            print(f"[#] Session will end at market close: {market_close.strftime('%H:%M IST')}")
        else:
            end_time = user_end_time
            print(f"[#] Session will end in {hours} hours")
        
        scan_count = 0
        
        try:
            while datetime.now(IST) < end_time:
                scan_count += 1
                # Increment persistent daily counter
                today_count = self._increment_daily_scan_counter()
                print(f"\n[SCAN] #{scan_count} | Today: {today_count}")
                
                # Check if market just closed during session
                if self._is_market_open() and datetime.now(IST) >= self._get_market_close_time():
                    print("\n[!] MARKET CLOSED - Ending session")
                    break
                
                scan_before = datetime.now(IST)
                self.scan_and_trade()
                scan_after = datetime.now(IST)

                # Update rolling daily summary
                try:
                    # Portfolio snapshot basics
                    total_value = self.available_capital
                    for s, pos in self.positions.items():
                        price = self.get_current_price(s)
                        if price > 0:
                            total_value += pos['shares'] * price
                    daily_update = {
                        'date_ist': datetime.now(IST).date().isoformat(),
                        'scans_today': today_count,
                        'trades_placed': self.total_trades,
                        'portfolio_snapshot': {
                            'positions': len(self.positions),
                            'gross_exposure': round(total_value - self.available_capital, 2),
                            'cash': round(self.available_capital, 2)
                        },
                        'unrealized_pnl': round(total_value - self.initial_capital, 2),
                    }
                    reporting.upsert_daily_summary(daily_update)
                except Exception:
                    pass
                self.print_status()
                
                # Show time until market close if market is open
                if self._is_market_open():
                    remaining_market = self._time_until_market_close()
                    remaining_session = (end_time - datetime.now(IST)).total_seconds() / 60
                    
                    if remaining_market < remaining_session and remaining_market > 0:
                        print(f"\n[T] Market closes in {remaining_market:.0f} minutes")
                
                # Save portfolio state periodically
                self._save_portfolio_state(is_end_of_day=False)
                
                # Wait for next scan
                remaining = (end_time - datetime.now(IST)).total_seconds()
                if remaining > 600:  # More than 10 minutes left
                    print("\n[~] Next scan in 10 minutes...")
                    time.sleep(600)  # 10 minutes
                elif remaining > 0:
                    print(f"\n[~] Session ending in {remaining/60:.0f} minutes...")
                    time.sleep(remaining)
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n[!] Stopped by user")
        
        # Keep positions open - no forced closure
        if self.positions:
            print(f"\n[HOLD] Keeping {len(self.positions)} positions open")
            print("[INFO] Positions will be held until strategy signals exit")
        
        # Save portfolio state
        is_end_of_day = not self._is_market_open() or datetime.now(IST).hour >= 15
        self._save_portfolio_state(is_end_of_day=is_end_of_day)
        
        # Final results
        print("\n" + "=" * 50)
        print("[DONE] SESSION COMPLETE")
        print("=" * 50)
        self.print_status()
        self._report_data_gaps()
        
        if self.trade_history:
            print(f"\n[PERFORMANCE] RESULTS:")
            avg_return = np.mean([t['pnl_pct'] for t in self.trade_history])
            print(f"   Average Trade: {avg_return:+.2f}%")
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades else 0
            
            if len(self.trade_history) >= 5:
                if win_rate >= 60 and avg_return > 0:
                    print(f"   ✅ Good performance! Consider live testing.")
                else:
                    print(f"   [WARNING] Review strategy before live trading.")

    def _report_data_gaps(self):
        """Report any symbols that were skipped due to insufficient historical data."""
        try:
            if not self.strategy:
                return
            limited = getattr(self.strategy, '_insufficient_logged', set()) or set()
            if not limited:
                return
            print("\n[DATA] Symbols skipped because of limited history:")
            limited_list = sorted(limited)
            for i in range(0, len(limited_list), 10):
                chunk = limited_list[i:i+10]
                print(f"   {', '.join(chunk)}")
            print("   ⚠️  These scripts are newly listed or lack multi-timeframe data.")
            print("   💡 Re-run tomorrow after fresh data downloads, or remove them from the watchlist.")
        except Exception:
            pass

    def _print_opening_summary(self):
        """Print past-day capital balance and holdings before the first scan.
        Uses the last saved portfolio snapshot without fetching live prices."""
        try:
            state_file = self.portfolio_file if hasattr(self, 'portfolio_file') else Path('paper_trading_portfolio.json')
            if not state_file.exists():
                print("[OPENING] No prior portfolio state found")
                return
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            last_dt = None
            try:
                last_dt = datetime.fromisoformat(state.get('last_trading_date', ''))
            except Exception:
                last_dt = None
            today = datetime.now(IST).date()
            last_date = (last_dt.astimezone(IST).date() if isinstance(last_dt, datetime) else today)

            # Prefer saved total_portfolio_value if present; else approximate from entries
            total_value = state.get('total_portfolio_value')
            if total_value is None:
                total_value = float(state.get('available_capital', 0))
                for sym, pos in state.get('positions', {}).items():
                    entry_price = pos.get('entry_price', pos.get('avg_price', 0))
                    qty = pos.get('shares', pos.get('qty', 0))
                    if entry_price and qty:
                        total_value += qty * entry_price

            cash = float(state.get('available_capital', 0))
            positions = state.get('positions', {}) or {}
            pos_count = len(positions)

            # Determine label based on whether it's a new day
            label = "Previous day" if last_date < today else "Current session"
            when = (last_dt.astimezone(IST).strftime('%Y-%m-%d %H:%M IST') if isinstance(last_dt, datetime) else "unknown time")

            print(f"[OPENING] {label} snapshot ({when})")
            print(f"   Closing/Last Value: Rs.{total_value:,.0f}")
            print(f"   Cash: Rs.{cash:,.0f} | Positions: {pos_count}")

            if pos_count:
                print(f"\n[HOLDINGS] As last saved (symbol | qty | entry)")
                for sym, pos in positions.items():
                    qty = pos.get('shares', pos.get('qty', 0))
                    entry = pos.get('entry_price', pos.get('avg_price', 0))
                    print(f"   {sym:<12} | {int(qty):>4} | Rs.{float(entry):>7.2f}")
        except Exception:
            print("[OPENING] Unable to read prior portfolio snapshot")


def auto_update_data():
    """Automatically update data cache before trading starts"""
    print("\n" + "=" * 60)
    print("[AUTO] AUTOMATIC DATA UPDATE")
    print("=" * 60)
    
    try:
        from data_cache_manager import DataCacheManager
        
        # Initialize cache manager
        cache_mgr = DataCacheManager()
        
        # Load watchlist
        try:
            with open('hybrid_config.json', 'r') as f:
                config = json.load(f)
            symbols = config.get('watchlist', [])
        except:
            symbols = ['RELIANCE', 'TCS', 'HDFCBANK']  # Fallback
        
        print(f"[AUTO] Checking data freshness for {len(symbols)} stocks...")
        required_timeframes = {
            'daily': {'min_rows': 120, 'check_fresh': False},
            '60min': {'min_rows': 160, 'check_fresh': False},
            '15min': {'min_rows': 200, 'check_fresh': True},
        }

        to_refresh = {tf: [] for tf in required_timeframes}

        for symbol in symbols:
            for tf, rules in required_timeframes.items():
                meta = cache_mgr.metadata.get(f"{symbol}_{tf}", {})
                rows = int(meta.get('rows', 0) or 0)
                cache_file = cache_mgr.get_cache_path(symbol, tf)
                needs_update = False

                if not cache_file.exists() or rows < rules['min_rows']:
                    needs_update = True
                elif rules['check_fresh'] and not cache_mgr.is_cache_valid(symbol, tf):
                    needs_update = True

                if needs_update:
                    to_refresh[tf].append(symbol)

        refreshed_any = False
        for tf in ['daily', '60min', '15min']:
            symbols_needed = to_refresh.get(tf, [])
            if not symbols_needed:
                continue

            refreshed_any = True
            preview = ', '.join(symbols_needed[:5])
            suffix = '...' if len(symbols_needed) > 5 else ''
            print(f"[AUTO] Refreshing {tf} data for {len(symbols_needed)} symbols: {preview}{suffix}")

            for symbol in symbols_needed:
                try:
                    cache_mgr.download_historical_data(symbol, tf, force_download=True)
                    # Light rate limit to respect API caps
                    time.sleep(0.35)
                except Exception as e:
                    print(f"[AUTO] [WARNING] Failed to update {symbol} ({tf}): {e}")

        if not refreshed_any:
            print(f"[AUTO] [OK] All required timeframes look good")
        else:
            print(f"[AUTO] [SUCCESS] Data update completed!")
            
        return True
        
    except Exception as e:
        print(f"[AUTO] [ERROR] Data update failed: {e}")
        print(f"[AUTO] [TIP] Run: python authenticate_zerodha.py")
        print(f"[AUTO] Continuing with cached data...")
        return False

def auto_authenticate_zerodha():
    """Automatically check and refresh Zerodha authentication"""
    print("\n" + "=" * 60)
    print("[AUTH] AUTOMATIC SESSION MANAGEMENT")
    print("=" * 60)
    
    try:
        from zerodha_auth import ZerodhaAuth
        
        auth = ZerodhaAuth()
        
        # Check if session is valid
        if auth.is_session_valid():
            kite = auth.get_kite_instance()
            if kite:
                try:
                    profile = kite.profile()
                    print(f"[AUTH] [SUCCESS] Session active for: {profile.get('user_name', 'Unknown')}")
                    return True
                except Exception:
                    print(f"[AUTH] [WARNING] Saved session expired")
            
        print(f"[AUTH] [INFO] Authentication required")
        print(f"[AUTH] [TIP] Run: python authenticate_zerodha.py")
        return False
        
    except Exception as e:
        print(f"[AUTH] [ERROR] Authentication check failed: {e}")
        print(f"[AUTH] [TIP] Run: python authenticate_zerodha.py")
        return False

def main():
    """Main paper trading function with integrated workflow"""
    
    print("=" * 60)
    print("[START] PERFECT TRADER - INTEGRATED WORKFLOW")
    print("=" * 60)
    print(f"[TIME] Started at: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
    print("=" * 60)
    
    # CLI args
    run_hours = 4.0
    dry_run = False
    allow_after_hours = False
    try:
        import argparse
        parser = argparse.ArgumentParser(description='Perfect Trader - Paper Trading')
        parser.add_argument('--hours', type=float, default=4.0, help='Run duration in hours (default: 4.0)')
        parser.add_argument('--dry-run', action='store_true', help='Scan only, do not place orders')
        parser.add_argument('--allow-after-hours', action='store_true', help='Allow running after market close (dry-run only)')
        args = parser.parse_args()
        run_hours = float(args.hours)
        dry_run = bool(args.dry_run)
        allow_after_hours = bool(args.allow_after_hours)
    except Exception:
        pass

    # Step 1: Auto-authenticate Zerodha session
    auth_success = auto_authenticate_zerodha()

    if not auth_success and not dry_run:
        print("\n[TRADING] Cannot continue without an active Zerodha session.")
        print("[ACTION] Run: python authenticate_zerodha.py")
        return

    # Step 2: Auto-update data (only if authenticated)
    data_success = False
    if auth_success:
        data_success = auto_update_data()
    else:
        print("[DATA] Skipping automatic data update because Zerodha is not authenticated.")

    # Step 3: Start paper trading
    print("\n" + "=" * 60)
    print("[TRADING] STARTING PAPER TRADING ENGINE")
    print("=" * 60)
    
    if auth_success:
        print("[TRADING] Using live Zerodha data + fresh cache")
        use_live = True
    else:
        print("[TRADING] Using cached data only")
        use_live = False
    
    # Initialize engine
    try:
        engine = PerfectTraderPaperTrading(
            initial_capital=250000,
            use_live_data=use_live,
            force_fresh_start=False,  # Don't reset portfolio every time
            dry_run=dry_run,
            allow_after_hours=allow_after_hours
        )
    except ZerodhaAuthenticationError:
        print("\n[TRADING] Aborting start until authentication is completed.")
        print("[ACTION] Run: python authenticate_zerodha.py")
        return

    # Start trading
    engine.run(hours=run_hours)


if __name__ == "__main__":
    main()