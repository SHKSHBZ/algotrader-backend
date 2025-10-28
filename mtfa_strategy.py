"""
Enhanced Multi-Timeframe Analysis (MTFA) Strategy
Moderate complexity with 3/4 timeframe agreement for realistic trading
Based on expert feedback for 65-70% win rate target
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
import talib
import pytz
from data_cache_manager import DataCacheManager

# Force IST timezone
IST = pytz.timezone('Asia/Kolkata')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MTFAStrategy:
    """
    Multi-Timeframe Analysis Strategy
    - Daily: Overall trend direction (filter)
    - 60-min: Intermediate trend and setup
    - 15-min: Entry signals
    - 5-min: Precise timing (optional, for later)
    """
    
    def __init__(self, config: Dict = None):
        """Initialize MTFA strategy"""
        self.config = config or {}
        
        # Cache manager for data
        self.cache_mgr = DataCacheManager()
        self._insufficient_logged: set[str] = set()
        self._min_rows = {
            'daily': 20,
            '60min': 40,
            '15min': 40,
        }
        
        # Centralized strategy configuration
        strategy_config = self.config.get('strategy', {})
        
        # Signal thresholds
        self.buy_threshold = strategy_config.get('buy_threshold', 55)
        self.sell_threshold = strategy_config.get('sell_threshold', 45)
        self.min_components = strategy_config.get('min_bullish_votes', 2)
        self.trend_bias_strength = strategy_config.get('trend_bias_strength', 10)
        
        # Component weights based on market regime
        weights_config = strategy_config.get('timeframe_weights', {})
        self.default_weights = {
            'daily': weights_config.get('daily', 0.30),
            '60min': weights_config.get('60min', 0.40),
            '15min': weights_config.get('15min', 0.30)
        }
        
        # Volatility-based weight adjustments
        vol_weights = strategy_config.get('volatility_weights', {})
        self.high_vol_weights = vol_weights.get('high_volatility', {'daily': 0.20, '60min': 0.35, '15min': 0.45})
        self.low_vol_weights = vol_weights.get('low_volatility', {'daily': 0.40, '60min': 0.40, '15min': 0.20})
        self.vol_thresholds = strategy_config.get('volatility_thresholds', {'high': 2.0, 'low': 0.5})
        
        # Risk parameters
        self.max_risk_per_trade = strategy_config.get('max_risk_per_trade', 0.01)
        
        # Target and stop parameters
        self.default_target_pct = strategy_config.get('default_target_percent', 3.0)
        self.default_stop_pct = strategy_config.get('default_stop_percent', 2.0)
        
    def analyze(self, symbol: str) -> Dict:
        """
        Main analysis method - combines all timeframes
        Returns trading signal with confidence score
        """
        result = {
            'symbol': symbol,
            'timestamp': datetime.now(IST),
            'signal': 'HOLD',
            'score': 50.0,
            'components': {},
            'votes': {},
            'confidence': 'low',
            'entry_price': 0,
            'stop_loss': 0,
            'target': 0
        }
        
        try:
            # Step 1: Get multi-timeframe data
            data_dict = self._load_mtf_data(symbol)
            
            valid, missing = self._validate_data(data_dict)
            if not valid and symbol not in self._insufficient_logged:
                if self._recover_symbol_data(symbol, missing):
                    data_dict = self._load_mtf_data(symbol)
                    valid, missing = self._validate_data(data_dict)

            if not valid:
                if symbol not in self._insufficient_logged:
                    missing_desc = ', '.join(sorted(missing)) if missing else 'unknown timeframes'
                    logging.warning(f"Insufficient data for {symbol} (missing: {missing_desc})")
                    self._insufficient_logged.add(symbol)
                return result
            
            # Step 2: Analyze each timeframe
            daily_analysis = self._analyze_daily(data_dict['daily'])
            h1_analysis = self._analyze_60min(data_dict['60min'])
            m15_analysis = self._analyze_15min(data_dict['15min'])
            
            # Step 3: Apply trend filter (daily) - Simplified
            if daily_analysis['trend'] == 'UP':
                trend_bias = self.trend_bias_strength  # Bullish bias
                allowed_signals = ['BUY', 'HOLD']
            elif daily_analysis['trend'] == 'DOWN':
                trend_bias = -self.trend_bias_strength  # Bearish bias
                allowed_signals = ['SELL', 'HOLD']
            else:
                trend_bias = 0  # Neutral
                allowed_signals = ['BUY', 'SELL', 'HOLD']
            
            # Step 4: Calculate component scores 
            components = {
                'daily': daily_analysis['score'],
                '60min': h1_analysis['score'],
                '15min': m15_analysis['score']
            }
            
            # Step 5: Get dynamic weights BEFORE voting calculation
            weights = self._get_dynamic_weights(data_dict)
            
            # Step 6: Calculate weighted score BEFORE voting
            final_score = (
                components['daily'] * weights['daily'] +
                components['60min'] * weights['60min'] +
                components['15min'] * weights['15min'] +
                trend_bias
            )
            
            # Step 7: Determine votes based on component scores (after weighting is calculated)
            votes = {
                'daily': daily_analysis['score'] > 50,   # Neutral+
                '60min': h1_analysis['score'] > 50,
                '15min': m15_analysis['score'] > 50
            }
            
            bullish_votes = sum(votes.values())
            
            # Step 8: Generate signal (moderate criteria) with rejection logging
            signal = 'HOLD'
            confidence = 'low'
            rejection_reason = None
            
            if bullish_votes >= self.min_components and final_score >= self.buy_threshold:
                if 'BUY' in allowed_signals:
                    signal = 'BUY'
                    confidence = 'high' if bullish_votes == 3 else 'medium'
                else:
                    rejection_reason = f"BUY signal blocked by daily trend filter (trend={daily_analysis['trend']})"
            elif bullish_votes <= 1 and final_score <= self.sell_threshold:
                if 'SELL' in allowed_signals:
                    signal = 'SELL'
                    confidence = 'high' if bullish_votes == 0 else 'medium'
                else:
                    rejection_reason = f"SELL signal blocked by daily trend filter (trend={daily_analysis['trend']})"
            else:
                # Log specific rejection reasons
                if bullish_votes >= self.min_components:
                    if final_score < self.buy_threshold:
                        rejection_reason = f"BUY rejected: score {final_score:.1f} < threshold {self.buy_threshold}"
                    else:
                        rejection_reason = f"BUY meets criteria but votes={bullish_votes} < required {self.min_components}"
                elif bullish_votes <= 1:
                    if final_score > self.sell_threshold:
                        rejection_reason = f"SELL rejected: score {final_score:.1f} > threshold {self.sell_threshold}"
                    else:
                        rejection_reason = f"SELL meets criteria but votes={bullish_votes} > allowed 1"
                else:
                    rejection_reason = f"HOLD: inconclusive signals (votes={bullish_votes}, score={final_score:.1f})"
            
            # Log rejection reasons for analysis
            if rejection_reason and signal == 'HOLD':
                logging.info(f"{symbol}: {rejection_reason}")
                logging.debug(f"{symbol} components: Daily={components['daily']:.1f}, 60min={components['60min']:.1f}, 15min={components['15min']:.1f}")
            
            # Step 9: Calculate entry, stop, target
            current_price = data_dict['15min']['close'].iloc[-1]
            
            if signal == 'BUY':
                # Use 60-min support for stop loss, or default percentage
                support_level = h1_analysis.get('support', 0)
                if support_level > 0 and support_level < current_price:
                    stop_loss = support_level
                else:
                    stop_loss = current_price * (1 - self.default_stop_pct / 100)
                target = current_price * (1 + self.default_target_pct / 100)
                entry_price = current_price
            elif signal == 'SELL':
                resistance_level = h1_analysis.get('resistance', 0)
                if resistance_level > current_price:
                    stop_loss = resistance_level
                else:
                    stop_loss = current_price * (1 + self.default_stop_pct / 100)
                target = current_price * (1 - self.default_target_pct / 100)
                entry_price = current_price
            else:
                stop_loss = 0
                target = 0
                entry_price = 0
            
            # Update result
            result.update({
                'signal': signal,
                'score': round(final_score, 2),
                'components': components,
                'votes': votes,
                'bullish_votes': bullish_votes,
                'confidence': confidence,
                'entry_price': round(entry_price, 2),
                'stop_loss': round(stop_loss, 2),
                'target': round(target, 2),
                'trend': daily_analysis['trend'],
                'weights': weights
            })
            
        except Exception as e:
            logging.error(f"MTFA analysis error for {symbol}: {e}")
            
        return result
    
    def _load_mtf_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Load data for multiple timeframes from cache with proper synchronization"""
        data = {}
        
        # Load raw data
        for timeframe in ['daily', '60min', '15min']:
            try:
                df = self.cache_mgr.get_data(symbol, timeframe)
                if df is not None and not df.empty:
                    data[timeframe] = df
            except Exception as e:
                logging.error(f"Error loading {symbol} {timeframe}: {e}")
        
        # Synchronize timeframes to prevent look-ahead bias
        if len(data) == 3:  # All timeframes loaded
            data = self._synchronize_timeframes(data)
                
        return data
    
    def _synchronize_timeframes(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Ensure proper timestamp alignment across timeframes"""
        try:
            # Get the latest common timestamp from 15-min data (highest frequency)
            latest_15min = data_dict['15min'].index[-1]
            
            # Find corresponding 60-min candle (should be <= latest_15min)
            # 60-min candles close at :00, so find the last :00 before or at latest_15min
            hour_boundary = latest_15min.replace(minute=0, second=0, microsecond=0)
            if latest_15min.minute < 60:
                # If we're not at hour boundary, use previous hour
                if latest_15min.minute < 60 and latest_15min != hour_boundary:
                    hour_boundary = hour_boundary - timedelta(hours=1)
            
            # Find corresponding daily candle (should be same trading day)
            daily_boundary = latest_15min.replace(hour=15, minute=30, second=0, microsecond=0)
            if latest_15min < daily_boundary:
                # If before market close, use previous trading day
                daily_boundary = daily_boundary - timedelta(days=1)
                # Skip weekends
                while daily_boundary.weekday() >= 5:
                    daily_boundary = daily_boundary - timedelta(days=1)
            
            # Filter data to synchronized timestamps
            sync_data = {}
            
            # 15-min: use as-is (highest frequency)
            sync_data['15min'] = data_dict['15min'][data_dict['15min'].index <= latest_15min]
            
            # 60-min: use data up to hour boundary
            sync_data['60min'] = data_dict['60min'][data_dict['60min'].index <= hour_boundary]
            
            # Daily: use data up to daily boundary
            sync_data['daily'] = data_dict['daily'][data_dict['daily'].index <= daily_boundary]
            
            return sync_data
            
        except Exception as e:
            logging.error(f"Timeframe synchronization error: {e}")
            return data_dict  # Return original if sync fails
    
    def _validate_data(self, data_dict: Dict) -> Tuple[bool, List[str]]:
        """Validate we have sufficient data for analysis"""
        required = ['daily', '60min', '15min']
        missing: List[str] = []
        
        for tf in required:
            df = data_dict.get(tf)
            if df is None:
                missing.append(tf)
                continue
            min_rows = self._min_rows.get(tf, 20)
            if len(df) < min_rows:
                missing.append(tf)
        
        return (len(missing) == 0), missing

    def _recover_symbol_data(self, symbol: str, missing: List[str]) -> bool:
        """Attempt to download missing timeframes for a symbol."""
        attempted = False
        for tf in missing:
            try:
                self.cache_mgr.download_historical_data(symbol, tf, force_download=True)
                attempted = True
            except Exception as exc:
                logging.info(f"{symbol}: unable to refresh {tf} data ({exc})")
        return attempted
    
    def _analyze_daily(self, data: pd.DataFrame) -> Dict:
        """Analyze daily timeframe for overall trend - Single SMA filter only"""
        analysis = {
            'trend': 'NEUTRAL',
            'strength': 50,
            'score': 50
        }
        
        try:
            # Get price data
            close = data['close'].values.astype(np.float64)
            
            # Single primary trend filter: SMA alignment
            if len(close) >= 200:
                sma_50 = talib.SMA(close, timeperiod=50)[-1]
                sma_200 = talib.SMA(close, timeperiod=200)[-1]
                current = close[-1]
                
                # Determine trend using only SMA alignment
                if current > sma_50 > sma_200:
                    analysis['trend'] = 'UP'
                    analysis['strength'] = 70
                    analysis['score'] = 75  # Strong bullish
                elif current < sma_50 < sma_200:
                    analysis['trend'] = 'DOWN'
                    analysis['strength'] = 70
                    analysis['score'] = 25  # Strong bearish
                else:
                    analysis['trend'] = 'NEUTRAL'
                    analysis['strength'] = 50
                    analysis['score'] = 50  # Neutral
            elif len(close) >= 50:
                # Fallback to shorter MA if insufficient data
                sma_20 = talib.SMA(close, timeperiod=20)[-1]
                sma_50 = talib.SMA(close, timeperiod=50)[-1]
                current = close[-1]
                
                if current > sma_20 > sma_50:
                    analysis['trend'] = 'UP'
                    analysis['strength'] = 60
                    analysis['score'] = 70
                elif current < sma_20 < sma_50:
                    analysis['trend'] = 'DOWN'
                    analysis['strength'] = 60
                    analysis['score'] = 30
                else:
                    analysis['trend'] = 'NEUTRAL'
                    analysis['strength'] = 50
                    analysis['score'] = 50
                
        except Exception as e:
            logging.error(f"Daily analysis error: {e}")
            
        return analysis
    
    def _analyze_60min(self, data: pd.DataFrame) -> Dict:
        """Analyze 60-min timeframe for intermediate trend"""
        analysis = {
            'score': 50,
            'support': 0,
            'resistance': 0
        }
        
        try:
            close = data['close'].values.astype(np.float64)
            high = data['high'].values.astype(np.float64)
            low = data['low'].values.astype(np.float64)
            volume = data['volume'].values.astype(np.float64)
            
            score = 50
            
            # RSI
            if len(close) >= 14:
                rsi = talib.RSI(close, timeperiod=14)
                if len(rsi) > 0 and not np.isnan(rsi[-1]):
                    rsi_val = rsi[-1]
                    if rsi_val < 30:
                        score += 20  # Oversold
                    elif rsi_val > 70:
                        score -= 20  # Overbought
                    else:
                        score += (50 - rsi_val) / 2  # Normalize
            
            # MACD
            if len(close) >= 26:
                macd, signal, hist = talib.MACD(close)
                if len(hist) > 0 and not np.isnan(hist[-1]):
                    if hist[-1] > 0 and hist[-1] > hist[-2]:
                        score += 15  # Bullish momentum
                    elif hist[-1] < 0 and hist[-1] < hist[-2]:
                        score -= 15  # Bearish momentum
            
            # Bollinger Bands for support/resistance
            if len(close) >= 20:
                upper, middle, lower = talib.BBANDS(close, timeperiod=20)
                if len(upper) > 0:
                    analysis['support'] = lower[-1]
                    analysis['resistance'] = upper[-1]
                    
                    # Position within bands
                    current = close[-1]
                    if current < lower[-1]:
                        score += 15  # Oversold
                    elif current > upper[-1]:
                        score -= 15  # Overbought
            
            # Volume confirmation
            if len(volume) >= 20:
                vol_sma = talib.SMA(volume, timeperiod=20)
                if len(vol_sma) > 0 and not np.isnan(vol_sma[-1]):
                    if volume[-1] > vol_sma[-1] * 1.5:
                        # High volume confirms direction
                        if close[-1] > close[-2]:
                            score += 10
                        else:
                            score -= 10
            
            analysis['score'] = max(0, min(100, score))
            
        except Exception as e:
            logging.error(f"60-min analysis error: {e}")
            
        return analysis
    
    def _analyze_15min(self, data: pd.DataFrame) -> Dict:
        """Analyze 15-min timeframe for entry signals"""
        analysis = {'score': 50}
        
        try:
            close = data['close'].values.astype(np.float64)
            high = data['high'].values.astype(np.float64)
            low = data['low'].values.astype(np.float64)
            
            score = 50
            
            # Short-term momentum
            if len(close) >= 10:
                # Price action
                recent_move = (close[-1] - close[-5]) / close[-5] * 100
                if recent_move > 0.5:
                    score += 10
                elif recent_move < -0.5:
                    score -= 10
                
                # RSI for short-term
                rsi = talib.RSI(close, timeperiod=9)
                if len(rsi) > 0 and not np.isnan(rsi[-1]):
                    if rsi[-1] < 35:
                        score += 15
                    elif rsi[-1] > 65:
                        score -= 15
            
            # Stochastic
            if len(close) >= 14:
                slowk, slowd = talib.STOCH(high, low, close)
                if len(slowk) > 0 and not np.isnan(slowk[-1]):
                    if slowk[-1] < 20:
                        score += 15  # Oversold
                    elif slowk[-1] > 80:
                        score -= 15  # Overbought
                    
                    # Crossover
                    if len(slowk) > 1 and slowk[-1] > slowd[-1] and slowk[-2] <= slowd[-2]:
                        score += 10  # Bullish crossover
            
            # Moving average alignment
            if len(close) >= 20:
                sma_10 = talib.SMA(close, timeperiod=10)[-1]
                sma_20 = talib.SMA(close, timeperiod=20)[-1]
                
                if close[-1] > sma_10 > sma_20:
                    score += 10  # Bullish alignment
                elif close[-1] < sma_10 < sma_20:
                    score -= 10  # Bearish alignment
            
            analysis['score'] = max(0, min(100, score))
            
        except Exception as e:
            logging.error(f"15-min analysis error: {e}")
            
        return analysis
    
    def _get_dynamic_weights(self, data_dict: Dict) -> Dict:
        """Get dynamic weights based on market conditions"""
        weights = self.default_weights.copy()
        
        try:
            # Check volatility (using 15-min data)
            if '15min' in data_dict:
                close = data_dict['15min']['close'].values
                if len(close) >= 20:
                    returns = np.diff(close) / close[:-1]
                    volatility = np.std(returns) * 100
                    
                    if volatility > self.vol_thresholds['high']:  # High volatility
                        # Give more weight to shorter timeframes
                        weights = self.high_vol_weights.copy()
                    elif volatility < self.vol_thresholds['low']:  # Low volatility
                        # Give more weight to longer timeframes
                        weights = self.low_vol_weights.copy()
                        
        except Exception as e:
            logging.error(f"Dynamic weight calculation error: {e}")
            
        return weights


def test_mtfa_strategy():
    """Test the MTFA strategy with a few stocks"""
    print("="*60)
    print("TESTING MTFA STRATEGY")
    print("="*60)
    
    strategy = MTFAStrategy()
    test_symbols = ['RELIANCE', 'TCS', 'HDFCBANK']
    
    for symbol in test_symbols:
        print(f"\n{symbol}:")
        print("-"*40)
        
        result = strategy.analyze(symbol)
        
        print(f"Signal: {result['signal']}")
        print(f"Score: {result['score']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Components: Daily={result['components'].get('daily', 0):.1f}, "
              f"60min={result['components'].get('60min', 0):.1f}, "
              f"15min={result['components'].get('15min', 0):.1f}")
        print(f"Votes: {result.get('bullish_votes', 0)}/3 bullish")
        
        if result['signal'] != 'HOLD':
            print(f"Entry: ₹{result['entry_price']}")
            print(f"Stop: ₹{result['stop_loss']}")
            print(f"Target: ₹{result['target']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    test_mtfa_strategy()