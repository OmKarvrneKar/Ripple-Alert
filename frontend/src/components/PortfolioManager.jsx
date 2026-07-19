import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useLivePrices } from '../hooks/useLivePrices';
import { Wallet, Loader2, Plus, TrendingUp } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function PortfolioManager() {
  const { token } = useAuth();
  const { prices } = useLivePrices();
  
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);
  const [symbol, setSymbol] = useState('');
  const [amount, setAmount] = useState('');
  const [updating, setUpdating] = useState(false);

  const fetchPortfolio = async () => {
    try {
      const res = await fetch(`${API_URL}/portfolio`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPortfolio(data.portfolio);
      }
    } catch (e) {
      console.error("Failed to fetch portfolio", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, [token]);

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!symbol || !amount) return;
    
    setUpdating(true);
    try {
      const res = await fetch(`${API_URL}/portfolio`, {
        method: 'POST',
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ symbol: symbol.toUpperCase(), amount: parseFloat(amount) })
      });
      if (res.ok) {
        setSymbol('');
        setAmount('');
        fetchPortfolio();
      }
    } catch (e) {
      console.error("Failed to update portfolio", e);
    } finally {
      setUpdating(false);
    }
  };

  // Calculate live portfolio value
  const totalValue = portfolio.reduce((acc, item) => {
    const livePrice = prices[item.symbol]?.price || 0;
    return acc + (item.amount_held * livePrice);
  }, 0);

  return (
    <div className="bg-slate-deep rounded-xl border border-gray-800 p-6 shadow-lg mb-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h2 className="font-display text-xl font-bold text-frost flex items-center gap-2 mb-2">
            <Wallet className="w-5 h-5 text-azure" />
            My Holdings
          </h2>
          <p className="text-sm text-steel mb-4">Add your assets to track total live value and set portfolio rules.</p>
          
          <form onSubmit={handleUpdate} className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-steel mb-1">Symbol</label>
              <input 
                type="text" 
                value={symbol}
                onChange={e => setSymbol(e.target.value)}
                placeholder="BTC"
                className="w-24 bg-midnight border border-gray-700 rounded-lg p-2 text-frost focus:ring-1 focus:ring-azure outline-none transition-all uppercase"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-steel mb-1">Amount</label>
              <input 
                type="number"
                step="any" 
                value={amount}
                onChange={e => setAmount(e.target.value)}
                placeholder="0.5"
                className="w-32 bg-midnight border border-gray-700 rounded-lg p-2 text-frost focus:ring-1 focus:ring-azure outline-none transition-all"
              />
            </div>
            <button 
              type="submit"
              disabled={updating || !symbol || !amount}
              className="bg-azure hover:bg-blue-600 text-white font-medium p-2 rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {updating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
              Update
            </button>
          </form>
        </div>

        <div className="bg-midnight border border-gray-800 rounded-xl p-5 md:min-w-[280px] relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-azure"></div>
          <p className="text-sm text-steel font-medium flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-emerald-muted" />
            Live Portfolio Value
          </p>
          <p className="text-3xl font-display font-bold text-frost">
            ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          
          <div className="mt-3 space-y-1 max-h-32 overflow-y-auto pr-2">
            {loading ? (
               <Loader2 className="w-4 h-4 animate-spin text-steel" />
            ) : portfolio.length === 0 ? (
               <p className="text-xs text-gray-500">No holdings set.</p>
            ) : (
              portfolio.map(item => (
                <div key={item.symbol} className="flex justify-between text-xs text-steel">
                  <span>{item.amount_held} {item.symbol}</span>
                  <span>${((prices[item.symbol]?.price || 0) * item.amount_held).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
