import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [portfolio, setPortfolio] = useState({});

  useEffect(() => {
    const fetchPortfolio = () => {
      axios.get('http://localhost:5000/api/portfolio')
        .then(res => setPortfolio(res.data))
        .catch(() => setPortfolio({}));
    };
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 10000); // 10 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>AlgoTrader React Dashboard</h1>
      </header>
      <section>
        <h2>Account Details</h2>
        <p><strong>Initial Capital:</strong> Rs. {portfolio.initial_capital || 'N/A'}</p>
        <p><strong>Available Capital:</strong> Rs. {portfolio.available_capital || 'N/A'}</p>
        <p><strong>Total Portfolio Value:</strong> Rs. {portfolio.total_portfolio_value || 'N/A'}</p>
        <p><strong>Last Trading Date:</strong> {portfolio.last_trading_date || 'N/A'}</p>
      </section>
      <section>
        <h2>Open Positions</h2>
        {portfolio.positions && Object.keys(portfolio.positions).length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Shares</th>
                <th>Avg Price</th>
                <th>Current Price</th>
                <th>Volume</th>
                <th>P&L</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(portfolio.positions).map(([symbol, pos]) => (
                <tr key={symbol}>
                  <td>{symbol}</td>
                  <td>{pos.shares}</td>
                  <td>Rs. {pos.avg_price}</td>
                  <td>Rs. {pos.current_price !== undefined ? pos.current_price : '--'}</td>
                  <td>{pos.volume !== undefined ? pos.volume : '--'}</td>
                  <td>{pos.pnl !== undefined ? `Rs. ${pos.pnl}` : '--'}</td>
                  {/* Render any extra fields from API */}
                  {Object.entries(pos).map(([key, value]) => (
                    ['shares','avg_price','current_price','volume','pnl'].includes(key) ? null : <td key={key}>{value}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No open positions.</p>
        )}
      </section>
      <section>
        <h2>Trade History</h2>
        {portfolio.trade_history && portfolio.trade_history.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Symbol</th>
                <th>Action</th>
                <th>Shares</th>
                <th>Price</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.trade_history.map((trade, idx) => (
                <tr key={idx}>
                  <td>{trade.date || 'N/A'}</td>
                  <td>{trade.symbol || 'N/A'}</td>
                  <td>{trade.action || 'N/A'}</td>
                  <td>{trade.shares || 'N/A'}</td>
                  <td>Rs. {trade.price || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No trade history.</p>
        )}
      </section>
    </div>
  );
}

export default App;
