import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
from datetime import datetime
import logging

# Shared hosting specific paths for addon domain
BASE_DIR = os.getenv('BASE_DIR', '/home/skshanawaz21/public_html/inditehealthcare.com/api')
PORTFOLIO_FILE = Path(os.getenv('PORTFOLIO_FILE', f'{BASE_DIR}/data/paper_trading_portfolio.json'))

# Setup logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add paths for imports
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, '/home/skshanawaz21/public_html/inditehealthcare.com')

app = Flask(__name__)

# CORS configuration for shared hosting
CORS(app, origins=[
    'https://inditehealthcare.com',
    'https://www.inditehealthcare.com',
    'http://inditehealthcare.com',
    'http://www.inditehealthcare.com'
])

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
    try:
        if PORTFOLIO_FILE.exists():
            with open(PORTFOLIO_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"Portfolio loaded successfully from {PORTFOLIO_FILE}")
                return data
        else:
            logger.warning(f"Portfolio file not found at {PORTFOLIO_FILE}, using defaults")
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
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        # Return default portfolio on error
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for frontend monitoring"""
    logger.info("Health check requested")
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AlgoTrader Backend API",
        "host": "inditehealthcare.com",
        "python_version": sys.version,
        "flask_env": os.getenv('FLASK_ENV', 'development'),
        "base_dir": BASE_DIR,
        "portfolio_file_exists": PORTFOLIO_FILE.exists()
    })

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get complete portfolio information"""
    try:
        portfolio_data = load_portfolio()
        
        # Calculate metrics
        total_value = portfolio_data.get('total_portfolio_value', 0)
        cash_available = portfolio_data.get('available_capital', 0)
        positions = portfolio_data.get('positions', {})
        
        # For shared hosting, we'll use static data since live trading APIs might not work
        invested_amount = 0
        total_pnl = 0
        day_pnl = 0
        
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

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current positions with detailed information"""
    try:
        portfolio = load_portfolio()
        positions = portfolio.get('positions', {})
        
        # Format positions for frontend
        formatted_positions = {}
        
        # For shared hosting demo, return static position data
        for symbol, position in positions.items():
            shares = position.get('shares', 0)
            avg_price = position.get('avg_price', 0)
            current_price = avg_price * 1.02  # Mock 2% gain
            
            market_value = shares * current_price
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
                "side": trade.get('action', ''),
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

@app.route('/api/strategy/status', methods=['GET'])
def get_strategy_status():
    """Get current strategy status and performance"""
    try:
        portfolio_data = load_portfolio()
        
        response = {
            "is_running": False,  # Static for demo
            "strategy_name": "MTFA",
            "last_update": datetime.now().isoformat(),
            "total_trades": portfolio_data.get('total_trades', 0),
            "win_rate": 65.2,  # Mock data
            "performance": {
                "total_return": 5.8,
                "sharpe_ratio": 1.2,
                "max_drawdown": -3.4
            }
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Add CORS headers for all requests
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__':
    app.run(debug=False)