import React from 'react';

// Button component
function Button({ children, onClick, variant = 'primary', isLoading, disabled, style, ...props }) {
  const getButtonStyle = () => {
    const baseStyle = {
      height: '2.75rem',
      padding: '0 1.5rem',
      borderRadius: '0.5rem',
      fontWeight: 500,
      fontSize: '1rem',
      cursor: 'pointer',
      transition: 'background 0.2s, transform 0.1s',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    };

    if (variant === 'primary') {
      return {
        ...baseStyle,
        backgroundColor: 'var(--primary)',
        color: 'white',
        border: 'none',
      };
    } else if (variant === 'danger') {
      return {
        ...baseStyle,
        backgroundColor: 'transparent',
        color: 'var(--error)',
        border: '1px solid var(--border)',
      };
    } else {
      return {
        ...baseStyle,
        backgroundColor: 'transparent',
        color: 'var(--text-light)',
        border: '1px solid var(--border)',
      };
    }
  };
  
  return (
    <button 
      style={{...getButtonStyle(), ...(style || {})}} 
      onClick={onClick}
      disabled={isLoading || disabled}
      {...props}
    >
      {isLoading && (
        <span style={{
          display: 'inline-block',
          width: '16px',
          height: '16px',
          border: '2px solid rgba(255, 255, 255, 0.3)',
          borderRadius: '50%',
          borderTopColor: '#fff',
          animation: 'spin 1s linear infinite',
        }}></span>
      )}
      {children}
    </button>
  );
}

export default Button;
