import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function HistoricalChart({ data, color = '#3B82F6' }) {
  if (!data || data.length === 0) {
    return <div className="h-48 w-full flex items-center justify-center text-steel font-mono text-sm">Loading chart data...</div>;
  }

  // Format data for Recharts (convert ISO strings to locale strings or timestamps if needed)
  // Recharts can handle numbers or strings. We'll format the tick on the X-axis.
  const formatXAxis = (tickItem) => {
    const date = new Date(tickItem);
    // If it's today, just show time, otherwise show date and time
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-deep border border-gray-800 p-3 rounded-lg shadow-xl">
          <p className="font-mono text-steel text-xs mb-1">{new Date(label).toLocaleString()}</p>
          <p className="font-mono text-frost font-bold text-lg">
            ${payload[0].value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
          </p>
        </div>
      );
    }
    return null;
  };

  // Find min and max for tight Y-axis scaling
  const prices = data.map(d => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = (maxPrice - minPrice) * 0.05; // 5% padding

  return (
    <div className="h-48 w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="timestamp" 
            tickFormatter={formatXAxis} 
            tick={{ fill: '#9CA3AF', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
            axisLine={false}
            minTickGap={30}
          />
          <YAxis 
            type="number"
            domain={[minPrice - padding, maxPrice + padding]}
            hide={true} // Hide Y axis for a cleaner "sparkline/glanceable" look
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#374151', strokeWidth: 1, strokeDasharray: '4 4' }} />
          <Area
            type="monotone"
            dataKey="price"
            stroke={color}
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorPrice)"
            isAnimationActive={false} // Disable animation so live append doesn't re-animate the whole chart
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
