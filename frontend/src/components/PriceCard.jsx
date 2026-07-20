import React, { useEffect, useState, useRef } from 'react';
import { ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';
import HistoricalChart from './HistoricalChart';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function PriceCard({ symbol, data }) {
  const [animationClass, setAnimationClass] = useState('');
  const [history, setHistory] = useState([]);
  const [range, setRange] = useState(24);
  const [isLoading, setIsLoading] = useState(true);
  
  // Fetch historical data
  const fetchHistory = async (hours) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/price-history/${symbol}?hours=${hours}`);
      if (res.ok) {
        const json = await res.json();
        setHistory(json.data);
      }
    } catch (e) {
      console.error(`Failed to fetch history for ${symbol}`, e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(range);
  }, [range, symbol]);

  // Handle live tick animations and appending to chart
  useEffect(() => {
    if (!data || !data.tick) return;
    
    // Trigger animation based on direction
    if (data.direction === 'up') {
      setAnimationClass('animate-ripple-up');
    } else if (data.direction === 'down') {
      setAnimationClass('animate-ripple-down');
    }
    
    // Append to history array for live chart update
    setHistory(prev => {
      // Avoid adding duplicate timestamps if the tick happens in the same second
      const lastPoint = prev[prev.length - 1];
      if (lastPoint && lastPoint.timestamp === data.timestamp) {
        return prev;
      }
      return [...prev, { timestamp: data.timestamp, price: data.price }];
    });
    
    const timer = setTimeout(() => {
      setAnimationClass('');
    }, 1000);
    
    return () => clearTimeout(timer);
  }, [data?.tick]);

  const price = data?.price ? `$${data.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}` : 'Waiting...';
  
  // Determine chart color based on the latest direction
  const chartColor = data?.direction === 'down' ? '#EF4444' : '#10B981';

  return (
    <div className={`p-6 rounded-xl border border-gray-800 transition-colors flex flex-col bg-slate-deep shadow-lg ${animationClass}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-midnight border border-gray-800 flex items-center justify-center font-display font-bold text-lg text-frost shadow-inner">
            {symbol.substring(0, 3)}
          </div>
          <div>
            <h3 className="font-display font-bold text-xl text-frost">{symbol}</h3>
            <p className="text-steel text-sm font-body tracking-wide">Real-time price</p>
          </div>
        </div>
        
        <div className="text-right">
          <div className="font-mono text-2xl font-bold text-frost flex items-center gap-2 justify-end">
            {data?.direction === 'up' && <ArrowUpRight className="text-emerald-muted w-5 h-5" />}
            {data?.direction === 'down' && <ArrowDownRight className="text-crimson w-5 h-5" />}
            {data?.direction === 'neutral' && <Activity className="text-steel w-5 h-5" />}
            {!data && <Activity className="text-steel w-5 h-5 animate-pulse" />}
            {price}
          </div>
          {data?.timestamp && (
            <p className="text-steel text-xs mt-1 font-mono">
              {new Date(data.timestamp).toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>
      
      {/* Range Toggles */}
      <div className="flex items-center gap-2 mt-6">
        {[1, 24, 168].map(h => (
          <button
            key={h}
            onClick={() => setRange(h)}
            className={`px-3 py-1 text-xs font-mono rounded-md transition-colors ${
              range === h 
                ? 'bg-azure text-white' 
                : 'bg-midnight border border-gray-700 text-steel hover:text-frost'
            }`}
          >
            {h === 1 ? '1H' : h === 24 ? '24H' : '7D'}
          </button>
        ))}
      </div>

      {/* Chart Area */}
      {isLoading && history.length === 0 ? (
        <div className="h-48 w-full flex items-center justify-center text-steel font-mono text-sm mt-4">
          Loading chart...
        </div>
      ) : (
        <HistoricalChart data={history} color={chartColor} />
      )}
    </div>
  );
}
