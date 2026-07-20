import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/prices';

export function useLivePrices(watchlist) {
  const [prices, setPrices] = useState({});
  const [status, setStatus] = useState('connecting');
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  
  // Keep track of the last prices to calculate up/down direction
  const lastPricesRef = useRef({});

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setStatus('connecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'prices') {
        setPrices((prev) => {
          const newPrices = { ...prev };
          const data = message.data;
          
          Object.keys(data).forEach(sym => {
            // Only track if it's in our watchlist (or track all and filter in UI)
            const newPrice = data[sym];
            const oldPrice = lastPricesRef.current[sym]?.price || newPrice;
            const direction = newPrice > oldPrice ? 'up' : newPrice < oldPrice ? 'down' : 'neutral';
            
            newPrices[sym] = {
              price: newPrice,
              timestamp: message.timestamp,
              direction,
              // We add a random tick counter so React knows a new event fired even if the price is exactly the same, 
              // which triggers the animation pulse
              tick: (prev[sym]?.tick || 0) + 1 
            };
            
            lastPricesRef.current[sym] = { price: newPrice };
          });
          
          return newPrices;
        });
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      wsRef.current = null;
      // Auto reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { prices, status };
}
