import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
// Order matters and is deliberate: tokens first, then the rules that consume
// them. Both are in force before anything renders — render-blocking in the
// production build, injected at module evaluation by the dev server — which is
// what keeps the first painted frame correctly themed.
import './styles/theme.css';
import './styles/global.css';
import App from './App';
import { AuthProvider } from './components/auth/AuthContext';
import ErrorBoundary from './components/ui/ErrorBoundary';

const container = document.getElementById('root');
const root = createRoot(container);
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <ErrorBoundary>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  </React.StrictMode>
);
