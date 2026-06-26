import React from 'react';

/**
 * React error boundary (REQ-FE-EB-1 / REQ-FE-CORE-3).
 *
 * React 18 `createRoot` unmounts the entire tree on any uncaught render error,
 * blanking every route (including /login) with no recovery affordance. This
 * boundary contains a render-time throw from any descendant and renders a
 * static fallback — a reload affordance — in its place. The fallback makes NO
 * new network calls (failover, not cold fallback).
 *
 * Used as a top-level boundary in index.js (FR-04); reused as a finer
 * per-widget bulkhead in FR-18.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Log to the console; a reporter hook can be attached here later.
    console.error('ErrorBoundary caught a render error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            padding: '2rem',
            minHeight: '50vh',
            textAlign: 'center',
            color: 'var(--text)',
          }}
        >
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>
            Something went wrong
          </h1>
          <p style={{ color: 'var(--text-light)', margin: 0 }}>
            An unexpected error occurred. Reloading the page may recover it.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              padding: '0.5rem 1rem',
              border: '1.5px solid var(--primary)',
              borderRadius: '0.5rem',
              backgroundColor: 'var(--primary)',
              color: '#fff',
              fontSize: '0.875rem',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Reload
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
