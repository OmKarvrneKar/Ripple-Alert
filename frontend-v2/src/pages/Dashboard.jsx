import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { LogOut } from 'lucide-react';

export default function Dashboard() {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-midnight text-frost p-6">
      <div className="max-w-7xl mx-auto">
        <header className="flex items-center justify-between mb-8 border-b border-gray-800 pb-4">
          <h1 className="font-display text-2xl font-bold text-azure flex items-center gap-2">
            <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            RippleAlert Dashboard
          </h1>
          
          <button 
            onClick={logout}
            className="flex items-center gap-2 px-4 py-2 bg-slate-deep hover:bg-gray-800 rounded-lg text-steel transition-colors border border-gray-800"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </header>
        
        <div className="bg-slate-deep rounded-xl border border-gray-800 p-8 text-center text-steel">
          <p className="text-xl mb-2">Welcome to the Dashboard</p>
          <p>We are currently building this section according to the new design plan.</p>
        </div>
      </div>
    </div>
  );
}
