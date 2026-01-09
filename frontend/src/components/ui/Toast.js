import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react';

const Toast = ({ message, type = 'success', duration = 5000, onClose, position = 'top-right' }) => {
  const [isVisible, setIsVisible] = useState(true);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      handleClose();
    }, duration);

    return () => clearTimeout(timer);
  }, [duration]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      setIsVisible(false);
      if (onClose) onClose();
    }, 300); // Match animation duration
  };

  if (!isVisible) return null;

  // Use theme variables for consistent colors
  const getTypeStyles = () => {
    switch (type) {
      case 'success':
        return {
          iconColor: 'var(--success)',
          backgroundColor: 'var(--card-bg)',
          borderColor: 'var(--success)',
          textColor: 'var(--text)'
        };
      case 'error':
        return {
          iconColor: 'var(--error)',
          backgroundColor: 'var(--card-bg)',
          borderColor: 'var(--error)',
          textColor: 'var(--text)'
        };
      case 'info':
        return {
          iconColor: 'var(--info)',
          backgroundColor: 'var(--card-bg)',
          borderColor: 'var(--info)',
          textColor: 'var(--text)'
        };
      case 'warning':
        return {
          iconColor: 'var(--warning)',
          backgroundColor: 'var(--card-bg)',
          borderColor: 'var(--warning)',
          textColor: 'var(--text)'
        };
      default:
        return {
          iconColor: 'var(--success)',
          backgroundColor: 'var(--card-bg)',
          borderColor: 'var(--success)',
          textColor: 'var(--text)'
        };
    }
  };

  const typeStyles = getTypeStyles();

  const icons = {
    success: <CheckCircle size={20} style={{ color: typeStyles.iconColor, flexShrink: 0 }} />,
    error: <XCircle size={20} style={{ color: typeStyles.iconColor, flexShrink: 0 }} />,
    info: <Info size={20} style={{ color: typeStyles.iconColor, flexShrink: 0 }} />,
    warning: <AlertTriangle size={20} style={{ color: typeStyles.iconColor, flexShrink: 0 }} />
  };

  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-center': 'top-4 left-1/2 transform -translate-x-1/2',
    'bottom-center': 'bottom-4 left-1/2 transform -translate-x-1/2'
  };

  return (
    <div
      className={`
        fixed z-50 ${positionClasses[position]}
        ${isExiting ? 'animate-slide-out' : 'animate-slide-in'}
      `}
      style={{
        animation: isExiting 
          ? 'slideOut 0.3s ease-in-out forwards'
          : 'slideIn 0.3s ease-in-out forwards'
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
          padding: '1rem',
          borderRadius: '0.5rem',
          minWidth: '320px',
          maxWidth: '500px',
          backgroundColor: typeStyles.backgroundColor,
          color: typeStyles.textColor,
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          border: '1px solid var(--border)',
          borderLeft: `4px solid ${typeStyles.borderColor}`,
          transition: 'all 0.2s ease',
          opacity: 1
        }}
      >
        <div style={{ flexShrink: 0 }}>
          {icons[type]}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ 
            margin: 0,
            fontSize: '0.875rem',
            fontWeight: 500,
            lineHeight: 1.4,
            color: typeStyles.textColor,
            wordWrap: 'break-word'
          }}>
            {message}
          </p>
        </div>
        <button
          onClick={handleClose}
          style={{
            flexShrink: 0,
            background: 'transparent',
            border: 'none',
            color: 'var(--text-light)',
            cursor: 'pointer',
            padding: '0.25rem',
            borderRadius: '0.25rem',
            transition: 'color 0.2s ease, background-color 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--subtle-bg)';
            e.currentTarget.style.color = 'var(--text)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--text-light)';
          }}
          aria-label="Close notification"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
};

// Toast Container to manage multiple toasts
export const ToastContainer = () => {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    const handleToast = (event) => {
      const { message, type, duration } = event.detail;
      const id = Date.now() + Math.random();
      
      setToasts(prev => [...prev, { id, message, type, duration }]);
    };

    window.addEventListener('showToast', handleToast);
    return () => window.removeEventListener('showToast', handleToast);
  }, []);

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return (
    <div className="toast-container">
      {toasts.map((toast, index) => (
        <div
          key={toast.id}
          style={{
            position: 'fixed',
            top: `${100 + index * 90}px`, // Start at 100px to clear navbar with comfortable spacing
            right: '1rem',
            zIndex: 50 + index
          }}
        >
          <Toast
            message={toast.message}
            type={toast.type}
            duration={toast.duration}
            onClose={() => removeToast(toast.id)}
            position="static"
          />
        </div>
      ))}
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes slideOut {
          from {
            transform: translateX(0);
            opacity: 1;
          }
          to {
            transform: translateX(100%);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
};

// Utility function to show toast
export const showToast = (message, type = 'success', duration = 5000) => {
  const event = new CustomEvent('showToast', {
    detail: { message, type, duration }
  });
  window.dispatchEvent(event);
};

export default Toast;