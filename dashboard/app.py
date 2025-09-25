
import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
import sys
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))
from paper_trading import ZerodhaLiveAPI

app = Flask(__name__)

# Production-ready CORS configuration
if os.getenv('FLASK_ENV') == 'production':
    # Add your production domain here
    CORS(app, origins=[
        'https://inditehealthcare.com',  # Your actual domain
        'https://www.inditehealthcare.com',  # Your actual domain
        'http://inditehealthcare.com',   # HTTP fallback
        'http://www.inditehealthcare.com'  # HTTP fallback
    ])
else:
    # Development CORS
    CORS(app, origins=['http://localhost:5173'])  # React dev server

PORTFOLIO_FILE = Path(__file__).parent.parent / 'paper_trading_portfolio.json'

def format_currency(amount):
    """Format amount with Indian Rupee symbol"""
    if amount == 0:
        return "₹0"
    return f"₹{amount:,.2f}"

def format_pnl(amount):
    """Format P&L with Indian Rupee symbol and +/- sign"""
    if amount == 0:
        return "₹0.00"
    sign = "+" if amount > 0 else ""
    return f"{sign}₹{amount:,.2f}"


def load_portfolio():
    """Load portfolio data from JSON file"""
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r') as f:
            data = json.load(f)
            return data
    else:
        # Return default portfolio with initial capital
        return {
            'initial_capital': 250000,
            'available_capital': 250000,
            'total_portfolio_value': 250000,
            'positions': {},
            'trade_history': [],
            'total_trades': 0,
            'winning_trades': 0
        }

def load_trade_history():
    """Load trade history from portfolio data"""
    portfolio = load_portfolio()
    return portfolio.get('trade_history', [])

def get_current_strategy_status():
    """Get current strategy status"""
    # This would connect to your actual strategy implementation
    return {
        'running': False,  # Update with actual status
        'total_trades': 0,
        'win_rate': 0,
        'total_return': 0,
        'sharpe_ratio': 0,
        'max_drawdown': 0
    }

def start_trading_strategy():
    """Start the trading strategy"""
    # Implement your strategy start logic here
    pass

def stop_trading_strategy():
    """Stop the trading strategy"""
    # Implement your strategy stop logic here
    pass

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for frontend monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AlgoTrader Backend API"
    })

@app.route('/')
def dashboard():
    portfolio = load_portfolio()
    return render_template('dashboard.html', portfolio=portfolio)

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get complete portfolio information"""
    try:
        portfolio_data = load_portfolio()
        
        # Calculate metrics
        total_value = portfolio_data.get('total_portfolio_value', 0)
        cash_available = portfolio_data.get('available_capital', 0)
        positions = portfolio_data.get('positions', {})
        
        # Calculate invested amount
        invested_amount = 0
        total_pnl = 0
        day_pnl = 0
        
        # If we have positions, calculate current values
        if positions:
            try:
                live_api = ZerodhaLiveAPI()
                if live_api.authenticate():
                    live_api.load_instruments()
                    
                    for symbol, position in positions.items():
                        shares = position.get('shares', 0)
                        avg_price = position.get('avg_price', 0)
                        current_price = live_api.get_live_price(symbol)
                        
                        if current_price > 0:
                            market_value = shares * current_price
                            invested_value = shares * avg_price
                            pnl = market_value - invested_value
                            
                            invested_amount += invested_value
                            total_pnl += pnl
                            day_pnl += pnl  # Simplified - would need previous day prices for accurate day P&L
            except Exception as e:
                print(f"Error calculating portfolio metrics: {e}")
        
        response = {
            "total_value": total_value,
            "total_value_formatted": format_currency(total_value),
            "cash_available": cash_available,
            "cash_available_formatted": format_currency(cash_available),
            "invested_amount": invested_amount,
            "invested_amount_formatted": format_currency(invested_amount),
            "total_pnl": total_pnl,
            "total_pnl_formatted": format_pnl(total_pnl),
            "day_pnl": day_pnl,
            "day_pnl_formatted": format_pnl(day_pnl),
            "positions": positions,
            "last_updated": datetime.now().isoformat(),
            "currency": "INR"
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/strategy/status', methods=['GET'])
def get_strategy_status():
    """Get current strategy status and performance"""
    try:
        strategy_status = get_current_strategy_status()
        portfolio_data = load_portfolio()
        
        response = {
            "is_running": strategy_status.get('running', False),
            "strategy_name": "MTFA",
            "last_update": datetime.now().isoformat(),
            "total_trades": portfolio_data.get('total_trades', 0),
            "win_rate": portfolio_data.get('winning_trades', 0) / max(portfolio_data.get('total_trades', 1), 1) * 100,
            "performance": {
                "total_return": strategy_status.get('total_return', 0),
                "sharpe_ratio": strategy_status.get('sharpe_ratio', 0),
                "max_drawdown": strategy_status.get('max_drawdown', 0)
            }
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/strategy/start', methods=['POST'])
def start_strategy():
    """Start the trading strategy"""
    try:
        start_trading_strategy()
        
        return jsonify({
            "success": True,
            "message": "Strategy started successfully",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/strategy/stop', methods=['POST'])
def stop_strategy():
    """Stop the trading strategy"""
    try:
        stop_trading_strategy()
        
        return jsonify({
            "success": True,
            "message": "Strategy stopped successfully",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current positions with detailed information"""
    try:
        portfolio = load_portfolio()
        positions = portfolio.get('positions', {})
        
        # Format positions for frontend
        formatted_positions = {}
        
        if positions:
            try:
                live_api = ZerodhaLiveAPI()
                if live_api.authenticate():
                    live_api.load_instruments()
                    
                    for symbol, position in positions.items():
                        shares = position.get('shares', 0)
                        avg_price = position.get('avg_price', 0)
                        current_price = live_api.get_live_price(symbol)
                        
                        market_value = shares * current_price if current_price > 0 else 0
                        invested_value = shares * avg_price
                        pnl = market_value - invested_value
                        pnl_percentage = (pnl / invested_value * 100) if invested_value > 0 else 0
                        
                        formatted_positions[symbol] = {
                            "symbol": symbol,
                            "quantity": shares,
                            "average_price": avg_price,
                            "average_price_formatted": format_currency(avg_price),
                            "current_price": current_price,
                            "current_price_formatted": format_currency(current_price),
                            "pnl": pnl,
                            "pnl_formatted": format_pnl(pnl),
                            "pnl_percentage": pnl_percentage,
                            "market_value": market_value,
                            "market_value_formatted": format_currency(market_value),
                            "invested_value": invested_value,
                            "invested_value_formatted": format_currency(invested_value)
                        }
            except Exception as e:
                print(f"Error getting live prices: {e}")
                # Fallback to basic position data
                for symbol, position in positions.items():
                    formatted_positions[symbol] = {
                        "symbol": symbol,
                        "quantity": position.get('shares', 0),
                        "average_price": position.get('avg_price', 0),
                        "average_price_formatted": format_currency(position.get('avg_price', 0)),
                        "current_price": 0,
                        "current_price_formatted": format_currency(0),
                        "pnl": 0,
                        "pnl_formatted": format_pnl(0),
                        "pnl_percentage": 0,
                        "market_value": 0,
                        "market_value_formatted": format_currency(0),
                        "invested_value": position.get('shares', 0) * position.get('avg_price', 0),
                        "invested_value_formatted": format_currency(position.get('shares', 0) * position.get('avg_price', 0))
                    }
        
        return jsonify(formatted_positions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trades', methods=['GET'])
def get_trade_history():
    """Get complete trade history"""
    try:
        trades = load_trade_history()
        
        # Format trades for frontend
        formatted_trades = []
        for i, trade in enumerate(trades):
            price = trade.get('price', 0)
            pnl = trade.get('pnl', 0)
            formatted_trades.append({
                "id": str(i),
                "symbol": trade.get('symbol', ''),
                "side": trade.get('action', ''),  # BUY/SELL
                "quantity": trade.get('shares', 0),
                "price": price,
                "price_formatted": format_currency(price),
                "timestamp": trade.get('timestamp', trade.get('date', '')),
                "pnl": pnl,
                "pnl_formatted": format_pnl(pnl),
                "status": "FILLED"
            })
        
        return jsonify(formatted_trades)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Environment configuration
    is_production = os.getenv('FLASK_ENV') == 'production'
    port = int(os.getenv('PORT', 5000))
    host = '0.0.0.0' if is_production else '127.0.0.1'
    debug_mode = not is_production
    
    # Add CORS headers for all requests
    @app.after_request
    def after_request(response):
        if is_production:
            # Production CORS headers
            response.headers.add('Access-Control-Allow-Origin', 'https://inditehealthcare.com')  # Your domain
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        else:
            # Development CORS headers
            response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    if is_production:
        print("🚀 AlgoTrader Backend API Server Starting (Production Mode)...")
        print(f"🔗 Backend API: Running on port {port}")
    else:
        print("🚀 AlgoTrader Backend API Server Starting (Development Mode)...")
        print("📊 Frontend URL: http://localhost:5173")
        print("🔗 Backend API: http://localhost:5000")
    
    app.run(host=host, port=port, debug=debug_mode)
