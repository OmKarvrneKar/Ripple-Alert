import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { LogIn, UserPlus, AlertCircle, Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (isLogin) {
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);
        
        const res = await fetch(`${API_URL}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData
        });
        
        const data = await res.json();
        
        if (res.ok) {
          login(data.access_token);
        } else {
          setError(data.detail || "Invalid credentials");
        }
      } else {
        const res = await fetch(`${API_URL}/signup`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        
        const data = await res.json();
        
        if (res.ok) {
          setSuccess("Account created successfully! Please log in.");
          setIsLogin(true);
          setPassword('');
        } else {
          setError(data.detail || "Failed to create account");
        }
      }
    } catch (err) {
      setError("Network error. Could not connect to server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-midnight text-frost flex flex-col items-center justify-center p-4">
      <div className="mb-8 text-center">
        <h1 className="font-display text-4xl font-bold text-azure flex items-center gap-2 justify-center">
          <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          RippleAlert
        </h1>
        <p className="font-body text-steel mt-2">Real-time crypto monitoring</p>
      </div>

      <div className="bg-slate-deep p-8 rounded-xl shadow-2xl w-full max-w-md border border-gray-800">
        <h2 className="text-2xl font-display font-semibold mb-6">
          {isLogin ? 'Sign In' : 'Create Account'}
        </h2>

        {error && (
          <div className="bg-crimson/10 border border-crimson/20 text-crimson p-3 rounded-lg mb-4 flex items-center gap-2 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}
        
        {success && (
          <div className="bg-emerald-muted/10 border border-emerald-muted/20 text-emerald-muted p-3 rounded-lg mb-4 text-sm">
            <p>{success}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-steel mb-1">Email Address</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-midnight border border-gray-700 rounded-lg p-3 text-frost focus:ring-2 focus:ring-azure focus:border-transparent outline-none transition-all"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-steel mb-1">Password</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-midnight border border-gray-700 rounded-lg p-3 text-frost focus:ring-2 focus:ring-azure focus:border-transparent outline-none transition-all"
              placeholder="••••••••"
            />
          </div>
          
          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-azure hover:bg-blue-600 text-white font-medium p-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isLogin ? (
              <><LogIn className="w-5 h-5" /> Sign In</>
            ) : (
              <><UserPlus className="w-5 h-5" /> Sign Up</>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button 
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
              setSuccess(null);
            }}
            className="text-steel hover:text-frost text-sm transition-colors"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
