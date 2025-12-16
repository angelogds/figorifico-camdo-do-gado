import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { Login } from './pages/Login';
import { Portaria } from './pages/Portaria';
import { Operador } from './pages/Operador';
import { Admin } from './pages/Admin';
import { Toaster } from './components/ui/sonner';
import '@/App.css';

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return children;
};

const AppRoutes = () => {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      
      <Route
        path="/"
        element={
          <ProtectedRoute>
            {user?.role === 'portaria' && <Navigate to="/portaria" replace />}
            {user?.role === 'operador' && <Navigate to="/operador" replace />}
            {user?.role === 'admin' && <Navigate to="/admin" replace />}
          </ProtectedRoute>
        }
      />
      
      <Route
        path="/portaria"
        element={
          <ProtectedRoute allowedRoles={['portaria', 'admin']}>
            <Portaria />
          </ProtectedRoute>
        }
      />
      
      <Route
        path="/operador"
        element={
          <ProtectedRoute allowedRoles={['operador', 'admin']}>
            <Operador />
          </ProtectedRoute>
        }
      />
      
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <Admin />
          </ProtectedRoute>
        }
      />
      
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster position="top-right" richColors closeButton />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;