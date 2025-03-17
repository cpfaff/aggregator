import React from 'react';

// Alert component for notifications
function Alert({ type = 'error', children }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      padding: '1rem',
      borderRadius: '0.5rem',
      marginBottom: '1rem',
      gap: '0.75rem',
      backgroundColor: type === 'error' ? '#fee2e2' : '#dcfce7',
      color: type === 'error' ? 'var(--error)' : 'var(--success)',
      borderLeft: `4px solid ${type === 'error' ? 'var(--error)' : 'var(--success)'}`,
    }}>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        {type === 'error' ? (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
        ) : (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        )}
      </svg>
      {children}
    </div>
  );
}

export default Alert;
