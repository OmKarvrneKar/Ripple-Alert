import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { BellRing, CheckCircle2, History, AlertTriangle, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function AlertManager() {
  const { token } = useAuth();
  
  const [rules, setRules] = useState([]);
  const [history, setHistory] = useState([]);
  
  const [symbol, setSymbol] = useState('BTC');
  const [condition, setCondition] = useState('above');
  const [threshold, setThreshold] = useState('');
  const [windowMinutes, setWindowMinutes] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const fetchAlertData = async () => {
    setLoading(true);
    try {
      const [rulesRes, historyRes] = await Promise.all([
        fetch(`${API_URL}/rules`, { headers: { "Authorization": `Bearer ${token}` } }),
        fetch(`${API_URL}/alert-history`, { headers: { "Authorization": `Bearer ${token}` } })
      ]);
      
      if (rulesRes.ok) {
        const rulesData = await rulesRes.json();
        setRules(rulesData.rules);
      }
      if (historyRes.ok) {
        const historyData = await historyRes.json();
        setHistory(historyData.history);
      }
    } catch (e) {
      console.error("Failed to fetch alert data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlertData();
  }, [token]);

  const handleCreateRule = async (e) => {
    e.preventDefault();
    if (!symbol || !threshold) return;
    if (condition === 'percent_change_in_window' && !windowMinutes) return;

    setCreating(true);
    setError(null);
    
    const payload = {
      symbol: symbol.toUpperCase(),
      condition,
      threshold: parseFloat(threshold),
      window_minutes: condition === 'percent_change_in_window' ? parseFloat(windowMinutes) : null
    };

    try {
      const res = await fetch(`${API_URL}/rules`, {
        method: 'POST',
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (res.ok) {
        setThreshold('');
        setWindowMinutes('');
        fetchAlertData(); // Refresh rules
      } else {
        setError(data.detail || "Failed to create rule");
      }
    } catch (e) {
      setError("Network error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-12">
      {/* Create Rule Panel */}
      <div className="bg-slate-deep rounded-xl border border-gray-800 p-6 shadow-lg lg:col-span-1">
        <h2 className="font-display text-xl font-bold text-frost flex items-center gap-2 mb-6">
          <BellRing className="w-5 h-5 text-azure" />
          Create Alert Rule
        </h2>
        
        {error && (
          <div className="bg-crimson/10 border border-crimson/20 text-crimson p-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleCreateRule} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-steel mb-1">Symbol</label>
            <input 
              type="text" 
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              className="w-full bg-midnight border border-gray-700 rounded-lg p-2.5 text-frost focus:ring-1 focus:ring-azure outline-none transition-all uppercase"
              placeholder="BTC"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-steel mb-1">Condition</label>
            <select 
              value={condition}
              onChange={e => setCondition(e.target.value)}
              className="w-full bg-midnight border border-gray-700 rounded-lg p-2.5 text-frost focus:ring-1 focus:ring-azure outline-none transition-all appearance-none"
            >
              <option value="above">Above Price ($)</option>
              <option value="below">Below Price ($)</option>
              <option value="percent_change_in_window">Percent Change (%)</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-steel mb-1">Threshold</label>
            <input 
              type="number" 
              step="any"
              value={threshold}
              onChange={e => setThreshold(e.target.value)}
              className="w-full bg-midnight border border-gray-700 rounded-lg p-2.5 text-frost focus:ring-1 focus:ring-azure outline-none transition-all"
              placeholder={condition === 'percent_change_in_window' ? "e.g. 5" : "e.g. 60000"}
            />
          </div>

          {condition === 'percent_change_in_window' && (
            <div>
              <label className="block text-sm font-medium text-steel mb-1">Window (Minutes)</label>
              <input 
                type="number" 
                step="any"
                value={windowMinutes}
                onChange={e => setWindowMinutes(e.target.value)}
                className="w-full bg-midnight border border-gray-700 rounded-lg p-2.5 text-frost focus:ring-1 focus:ring-azure outline-none transition-all"
                placeholder="e.g. 60"
              />
            </div>
          )}

          <button 
            type="submit" 
            disabled={creating}
            className="w-full bg-azure hover:bg-blue-600 text-white font-medium p-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 mt-2"
          >
            {creating ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Create Rule'}
          </button>
        </form>
      </div>

      {/* Active Rules List */}
      <div className="bg-slate-deep rounded-xl border border-gray-800 p-6 shadow-lg lg:col-span-1 flex flex-col">
        <h2 className="font-display text-xl font-bold text-frost flex items-center gap-2 mb-6">
          <CheckCircle2 className="w-5 h-5 text-emerald-muted" />
          Active Rules
        </h2>
        
        <div className="flex-1 overflow-y-auto pr-2 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-steel" /></div>
          ) : rules.length === 0 ? (
            <div className="text-center text-steel mt-8">
              <p>No active rules yet.</p>
              <p className="text-sm mt-1">Set a rule to get notified the moment something changes.</p>
            </div>
          ) : (
            rules.map(rule => (
              <div key={rule.id} className={`p-4 rounded-lg border ${rule.is_currently_triggered ? 'border-crimson/50 bg-crimson/10' : 'border-gray-700 bg-midnight'}`}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-frost">{rule.symbol}</span>
                  {rule.is_currently_triggered ? (
                    <span className="text-xs bg-crimson text-white px-2 py-0.5 rounded-full flex items-center gap-1 font-bold">
                      <AlertTriangle className="w-3 h-3" /> TRIGGERED
                    </span>
                  ) : (
                    <span className="text-xs bg-gray-700 text-steel px-2 py-0.5 rounded-full">IDLE</span>
                  )}
                </div>
                <p className="text-sm text-steel">
                  {rule.condition === 'percent_change_in_window' 
                    ? `Alert if moves > ${rule.threshold}% in ${rule.window_minutes}m`
                    : `Alert if ${rule.condition} $${rule.threshold}`}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Alert History List */}
      <div className="bg-slate-deep rounded-xl border border-gray-800 p-6 shadow-lg lg:col-span-1 flex flex-col">
        <h2 className="font-display text-xl font-bold text-frost flex items-center gap-2 mb-6">
          <History className="w-5 h-5 text-azure" />
          Alert History
        </h2>
        
        <div className="flex-1 overflow-y-auto pr-2 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-steel" /></div>
          ) : history.length === 0 ? (
            <div className="text-center text-steel mt-8">
              <p>No alerts triggered yet.</p>
              <p className="text-sm mt-1">When a rule threshold is crossed, it will appear here.</p>
            </div>
          ) : (
            history.map((item, i) => (
              <div key={i} className="p-4 rounded-lg border border-gray-800 bg-midnight relative overflow-hidden">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-crimson"></div>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-frost">{item.symbol}</span>
                  <span className="text-xs text-steel font-mono">{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <p className="text-sm text-steel mb-1">{item.rule_description}</p>
                <p className="text-sm font-mono text-crimson font-bold">Price: ${item.triggered_price.toLocaleString()}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
