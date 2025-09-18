from flask import Flask, jsonify
import json
from pathlib import Path
from paper_trading import ZerodhaLiveAPI

app = Flask(__name__)

PORTFOLIO_FILE = Path('paper_trading_portfolio.json')

def load_portfolio():
    """Load portfolio data from JSON file"""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {}

@app.route('/api/portfolio')
def api_portfolio():
    """API endpoint to get portfolio data with live prices"""
    portfolio = load_portfolio()
    positions = portfolio.get('positions', {})
    
    if not positions:
        return jsonify({
            'total_value': portfolio.get('cash_available', 250000),
            'cash_available': portfolio.get('cash_available', 250000),
            'invested_amount': 0,
            'total_pnl': 0,
            'day_pnl': 0,
            'positions': {}
        })

    # Initialize Zerodha API for live prices
    live_api = ZerodhaLiveAPI()
    if not live_api.authenticate():
        return jsonify({'error': 'Zerodha authentication failed'})
    live_api.load_instruments()

    enriched_positions = {}
    total_invested = 0
    total_current_value = 0
    total_pnl = 0

    for symbol, pos in positions.items():
        shares = pos.get('shares', pos.get('quantity', 0))
        avg_price = pos.get('avg_price', pos.get('average_price', 0))
        
        # Fetch live price and volume
        current_price = live_api.get_live_price(symbol)
        
        # Try to get volume from Zerodha API (if available)
        volume = 0
        try:
            quote = live_api.kite.ltp(f"NSE:{symbol}")
            if f"NSE:{symbol}" in quote:
                volume = quote[f"NSE:{symbol}"].get("volume", 0)
        except:
            volume = 0

        if current_price:
            invested_value = shares * avg_price
            current_value = shares * current_price
            pnl = current_value - invested_value
            pnl_percent = (pnl / invested_value * 100) if invested_value > 0 else 0
            
            total_invested += invested_value
            total_current_value += current_value
            total_pnl += pnl
            
            enriched_positions[symbol] = {
                'shares': shares,
                'avg_price': avg_price,
                'current_price': current_price,
                'volume': volume,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'invested_value': invested_value,
                'current_value': current_value
            }

    cash_available = portfolio.get('cash_available', 250000)
    total_value = total_current_value + cash_available
    day_pnl = portfolio.get('day_pnl', 0)

    return jsonify({
        'total_value': total_value,
        'cash_available': cash_available,
        'invested_amount': total_invested,
        'total_pnl': total_pnl,
        'day_pnl': day_pnl,
        'positions': enriched_positions
    })

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'AlgoTrader Backend API'})

@app.route('/api/strategy/status')
def strategy_status():
    """Get trading strategy status"""
    # This can be enhanced to check if the trading bot is running
    return jsonify({
        'strategy_active': True,
        'last_signal_time': None,
        'positions_count': len(load_portfolio().get('positions', {}))
    })

if __name__ == '__main__':
    print("🚀 Starting AlgoTrader Backend API...")
    print("📊 Portfolio API: http://localhost:5000/api/portfolio")
    print("🔍 Health Check: http://localhost:5000/api/health")
    print("⚡ Strategy Status: http://localhost:5000/api/strategy/status")
    
    app.run(debug=True, host='127.0.0.1', port=5000)