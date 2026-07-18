import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useLivePrices } from '../hooks/useLivePrices';
import PriceCard from '../components/PriceCard';
import AlertManager from '../components/AlertManager';
import { LogOut, Plus, Wifi, WifiOff, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const { token, logout } = useAuth();
  const [watchlist, setWatchlist] = useState([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Connect to live prices WebSocket
  const { prices, status } = useLivePrices();

  // Fetch initial watchlist
  const fetchWatchlist = async () => {
    try {
      const res = await fetch(`${API_URL}/watchlist`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setWatchlist(data.watchlist);
      } else if (res.status === 401) {
        logout();
      }
    } catch (e) {
      console.error("Failed to fetch watchlist", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const handleAddSymbol = async (e) => {
    e.preventDefault();
    if (!newSymbol.trim()) return;
    
    setIsAdding(true);
    try {
      const res = await fetch(`${API_URL}/watchlist`, {
        method: 'POST',
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ symbol: newSymbol.toUpperCase() })
      });
      if (res.ok) {
        setNewSymbol('');
        fetchWatchlist();
      } else {
        alert("Failed to add symbol");
      }
    } catch (e) {
      console.error("Failed to add to watchlist", e);
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="min-h-screen bg-midnight text-frost p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-col md:flex-row items-center justify-between mb-8 gap-4 border-b border-gray-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="bg-azure/20 p-2 rounded-lg">
              <svg className="w-6 h-6 text-azure" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="font-display text-2xl font-bold text-frost">RippleAlert</h1>
            
            {/* Connection Status Indicator */}
            <div className="ml-4 flex items-center gap-2 px-3 py-1 bg-slate-deep rounded-full border border-gray-800 text-sm">
              {status === 'connected' ? (
                <><Wifi className="w-4 h-4 text-emerald-muted" /> <span className="text-steel">Live</span></>
              ) : status === 'connecting' ? (
                <><Loader2 className="w-4 h-4 text-azure animate-spin" /> <span className="text-steel">Connecting...</span></>
              ) : (
                <><WifiOff className="w-4 h-4 text-crimson" /> <span className="text-crimson">Reconnecting...</span></>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-4 w-full md:w-auto">
            <form onSubmit={handleAddSymbol} className="flex flex-1 md:flex-none">
              <input 
                type="text" 
                placeholder="Add symbol (e.g. BTC)" 
                value={newSymbol}
                onChange={e => setNewSymbol(e.target.value)}
                className="bg-slate-deep border border-gray-700 rounded-l-lg px-4 py-2 text-frost focus:outline-none focus:border-azure w-full md:w-48 transition-colors uppercase"
              />
              <button 
                type="submit"
                disabled={isAdding || !newSymbol.trim()}
                className="bg-azure hover:bg-blue-600 text-white px-4 py-2 rounded-r-lg transition-colors disabled:opacity-50 flex items-center justify-center"
              >
                {isAdding ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
              </button>
            </form>

            <button 
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 bg-slate-deep hover:bg-gray-800 rounded-lg text-steel transition-colors border border-gray-800 flex-shrink-0"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>
        
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-steel">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-azure" />
            <p>Loading watchlist...</p>
          </div>
        ) : watchlist.length === 0 ? (
          <div className="bg-slate-deep rounded-xl border border-gray-800 p-12 text-center text-steel">
            <p className="text-xl font-display mb-2 text-frost">Your watchlist is empty</p>
            <p>Add a cryptocurrency symbol (like BTC or ETH) above to start tracking live prices.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {watchlist.map(sym => (
              <PriceCard 
                key={sym} 
                symbol={sym} 
                data={prices[sym]} 
              />
            ))}
          </div>
        )}
        
        {/* Alert Management Section */}
        {!loading && <AlertManager />}
      </div>
    </div>
  );
}
