import React from 'react';

// Enhanced Modal component with proper scrollbar styling
function Modal({ isOpen, onClose, title, children, footer }) {
  React.useEffect(() => {
    if (isOpen) {
      // Save the current body overflow style
      const originalStyle = window.getComputedStyle(document.body).overflow;
      // Disable scrolling on body
      document.body.style.overflow = 'hidden';
      
      // Restore original overflow style when modal is closed
      return () => {
        document.body.style.overflow = originalStyle;
      };
    }
  }, [isOpen]); // Only re-run when isOpen changes

  if (!isOpen) return null;
  
  return (
    <div 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.1)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
      }} 
      onClick={onClose}
    >
      <div 
        style={{
          backgroundColor: 'var(--card-bg)',
          padding: '2rem',
          borderRadius: '0.75rem',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          width: '90%',
          maxWidth: '800px',
          maxHeight: '90vh',
          position: 'relative',
          transition: 'background-color 0.3s',
          display: 'flex',
          flexDirection: 'column',
        }} 
        onClick={e => e.stopPropagation()}
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '1.5rem',
        }}>
          <h3 style={{ 
            margin: 0, 
            fontSize: '1.25rem', 
            fontWeight: 600,
            color: 'var(--text)',
          }}>
            {title}
          </h3>
          <button 
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              fontSize: '1.5rem',
              lineHeight: 1,
              padding: '0.25rem',
              cursor: 'pointer',
              color: 'var(--text-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        
        <div 
          className="modal-content-scrollable"
          style={{ 
            flex: 1,
            overflowY: 'auto',
            marginRight: '-0.5rem',
            paddingRight: '0.5rem',
          }}
          onWheel={(e) => e.stopPropagation()}
        >
          {children}
        </div>
        
        {footer && (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'flex-end', 
            gap: '0.75rem',
            marginTop: '1.5rem',
            borderTop: '1px solid var(--border)',
            paddingTop: '1.5rem',
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;
