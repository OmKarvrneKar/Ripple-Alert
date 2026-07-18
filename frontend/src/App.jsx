import React from 'react';
import { AuthProvider, useAuth } from './hooks/useAuth';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';

function AppContent() {
  const { token } = useAuth();
  
  // Simple state-based routing: if we have a token in memory, show the Dashboard.
  // Otherwise, show the Login/Signup page.
  return token ? <Dashboard /> : <Auth />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
