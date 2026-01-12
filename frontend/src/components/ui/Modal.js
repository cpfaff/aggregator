import React from 'react';
import { useIsMobile } from '../../hooks/useMediaQuery';

// Enhanced Modal component with proper scrollbar styling and mobile responsiveness
function Modal({ isOpen, onClose, title, children, footer, zIndex = 1000 }) {
  const isMobile = useIsMobile();

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

  // Modal container styles - full screen on mobile
  const modalContainerStyle = isMobile
    ? {
        backgroundColor: 'var(--card-bg)',
        padding: '1rem',
        borderRadius: 0,
        boxShadow: 'none',
        width: '100%',
        maxWidth: '100%',
        height: '100vh',
        maxHeight: '100vh',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        transition: 'background-color 0.3s',
        display: 'flex',
        flexDirection: 'column',
      }
    : {
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
      };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: isMobile ? 'transparent' : 'rgba(0, 0, 0, 0.1)',
        backdropFilter: isMobile ? 'none' : 'blur(4px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: zIndex,
      }}
      onClick={isMobile ? undefined : onClose}
    >
      <div
        style={modalContainerStyle}
        onClick={e => e.stopPropagation()}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: isMobile ? '1rem' : '2rem',
          padding: isMobile ? '0 0 1rem' : '0 0 1.5rem',
          borderBottom: '1px solid var(--border-light)'
        }}>
          <h3 style={{
            margin: 0,
            fontSize: isMobile ? '1rem' : '1.125rem',
            fontWeight: 600,
            color: 'var(--text)',
            letterSpacing: '-0.25px'
          }}>
            {title}
          </h3>
          <button
            onClick={onClose}
            style={{
              backgroundColor: 'var(--subtle-bg)',
              border: '1px solid var(--border)',
              fontSize: '1.25rem',
              lineHeight: 1,
              padding: '0.5rem',
              cursor: 'pointer',
              color: 'var(--text-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '0.375rem',
              width: '44px',
              height: '44px',
              transition: 'all 0.2s ease',
              flexShrink: 0,
            }}
            aria-label="Close modal"
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--border)';
              e.currentTarget.style.color = 'var(--text)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--subtle-bg)';
              e.currentTarget.style.color = 'var(--text-light)';
            }}
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
            marginTop: isMobile ? '1rem' : '1.5rem',
            borderTop: '1px solid var(--border)',
            paddingTop: isMobile ? '1rem' : '1.5rem',
            flexWrap: 'wrap',
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;
