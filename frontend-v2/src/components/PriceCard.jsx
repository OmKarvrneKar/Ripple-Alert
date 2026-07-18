import React, { useEffect, useState } from 'react';
import { ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';

export default function PriceCard({ symbol, data }) {
  const [animationClass, setAnimationClass] = useState('');
  
  useEffect(() => {
    if (!data || !data.tick) return;
    
    // Trigger animation based on direction
    if (data.direction === 'up') {
      setAnimationClass('animate-ripple-up');
    } else if (data.direction === 'down') {
      setAnimationClass('animate-ripple-down');
    }
    
    // Clear the animation class so it can re-trigger on next tick
    const timer = setTimeout(() => {
      setAnimationClass('');
    }, 1000);
    
    return () => clearTimeout(timer);
  }, [data?.tick]);

  const price = data?.price ? `$${data.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}` : 'Waiting...';
  
  return (
    <div className={`p-6 rounded-xl border border-gray-800 transition-colors flex items-center justify-between ${animationClass}`}>
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-midnight border border-gray-800 flex items-center justify-center font-display font-bold text-lg text-frost">
          {symbol.substring(0, 3)}
        </div>
        <div>
          <h3 className="font-display font-bold text-xl text-frost">{symbol}</h3>
          <p className="text-steel text-sm font-body">Real-time price</p>
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
  );
}
