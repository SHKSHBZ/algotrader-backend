
from flask import Flask, render_template, jsonify
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from paper_trading import ZerodhaLiveAPI

app = Flask(__name__)

PORTFOLIO_FILE = Path('../paper_trading_portfolio.json')


def load_portfolio():
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {}

@app.route('/')
def dashboard():
    portfolio = load_portfolio()
    return render_template('dashboard.html', portfolio=portfolio)


@app.route('/api/portfolio')
def api_portfolio():
    portfolio = load_portfolio()
    positions = portfolio.get('positions', {})
    result = []
    if not positions:
        return jsonify([])

    # Initialize Zerodha API (assumes credentials/session already set up)
    live_api = ZerodhaLiveAPI()
    if not live_api.authenticate():
        return jsonify({'error': 'Zerodha authentication failed'})
    live_api.load_instruments()

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
        except Exception:
            volume = 0
        pnl = (current_price - avg_price) * shares if shares and avg_price else 0
        result.append({
            'symbol': symbol,
            'shares': shares,
            'avg_price': avg_price,
            'current_price': current_price,
            'volume': volume,
            'pnl': pnl
        })
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
