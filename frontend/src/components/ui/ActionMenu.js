import React, { useEffect, useState, useRef, useCallback } from 'react';
import './ActionMenu.css';

/**
 * ActionMenu - A floating action menu that stays visible during scroll
 * 
 * @param {Object} props - Component props
 * @param {Array} props.actions - Array of action objects with icon, label, onClick, and color props
 * @param {Object} props.style - Additional styles to apply to the container
 * @param {String} props.position - Position of the menu: 'right' (default) or 'left'
 * @param {Number} props.offset - Offset from the edge in pixels (default: 24)
 * @param {String} props.mode - Positioning mode: 'fixed' (default) or 'content-relative'
 * @param {String} props.contentSelector - CSS selector for the content container when mode is 'content-relative'
 */
function ActionMenu({ 
  actions = [], 
  style = {}, 
  position = 'right',
  offset = 24,
  mode = 'fixed',
  contentSelector = '.content-container'
}) {
  const [containerStyle, setContainerStyle] = useState({});
  const actionMenuRef = useRef(null);
  const styleRef = useRef(style);
  
  // Update styleRef when style prop changes
  useEffect(() => {
    styleRef.current = style;
  }, [style]);
  
  // Function to update position based on mode
  const updatePosition = useCallback(() => {
    // Base styles for both modes
    const baseStyle = {
      display: 'flex',
      flexDirection: 'column',
      gap: '0.75rem',
      zIndex: 100,
      ...styleRef.current
    };
    
    if (mode === 'fixed') {
      // Original fixed positioning
      const fixedStyle = {
        ...baseStyle,
        position: 'fixed',
        top: '50%',
        transform: 'translateY(-50%)'
      };
      
      // Apply position (left or right)
      if (position === 'right') {
        fixedStyle.right = `${offset}px`;
      } else {
        fixedStyle.left = `${offset}px`;
      }
      
      setContainerStyle(fixedStyle);
    } else if (mode === 'content-relative') {
      // Content-relative positioning
      const contentContainer = document.querySelector(contentSelector);
      
      if (contentContainer) {
        const contentRect = contentContainer.getBoundingClientRect();
        const windowWidth = window.innerWidth;
        
        // Calculate position relative to the content container
        const relativeStyle = {
          ...baseStyle,
          position: 'fixed'
        };
        
        // Check if there's enough space for the menu
        const actionMenuWidth = actionMenuRef.current ? actionMenuRef.current.offsetWidth : 60; // Default width estimate
        
        if (position === 'right') {
          // Place it to the right of the content container with appropriate spacing
          relativeStyle.right = `${Math.max(offset, windowWidth - contentRect.right - actionMenuWidth - 20)}px`;
          relativeStyle.top = '50%';
          relativeStyle.transform = 'translateY(-50%)';
        } else {
          // Place it to the left of the content container with appropriate spacing
          relativeStyle.left = `${Math.max(offset, contentRect.left - actionMenuWidth - 20)}px`;
          relativeStyle.top = '50%';
          relativeStyle.transform = 'translateY(-50%)';
        }
        
        setContainerStyle(relativeStyle);
      }
    }
  }, [mode, position, offset, contentSelector]); // Removed style from dependencies
  
  // Set up position and event listeners - add delay and multiple updates for reliability
  useEffect(() => {
    // Set initial positioning immediately
    updatePosition();
    
    // Add a slight delay to ensure DOM is fully rendered
    const initialDelayTimer = setTimeout(() => {
      updatePosition();
      
      // Schedule one more update to ensure measurements are accurate
      const secondUpdateTimer = setTimeout(() => {
        updatePosition();
      }, 50);
      
      return () => clearTimeout(secondUpdateTimer);
    }, 10);
    
    // Add event listeners for resize if using content-relative mode
    if (mode === 'content-relative') {
      window.addEventListener('resize', updatePosition);
      window.addEventListener('scroll', updatePosition);
      
      // Call update when any images load, as this can affect layout
      const handleImageLoad = () => {
        updatePosition();
      };
      
      // Watch for DOM changes that might affect positioning
      const observer = new MutationObserver(() => {
        updatePosition();
      });
      
      const contentContainer = document.querySelector(contentSelector);
      if (contentContainer) {
        observer.observe(contentContainer, { 
          childList: true, 
          subtree: true,
          attributes: true
        });
      }
      
      document.addEventListener('load', handleImageLoad, true);
      
      // Cleanup
      return () => {
        clearTimeout(initialDelayTimer);
        window.removeEventListener('resize', updatePosition);
        window.removeEventListener('scroll', updatePosition);
        document.removeEventListener('load', handleImageLoad, true);
        observer.disconnect();
      };
    }
    
    return () => clearTimeout(initialDelayTimer);
  }, [mode, updatePosition, contentSelector]);
  
  if (!actions || actions.length === 0) return null;
  
  return (
    <div 
      ref={actionMenuRef}
      style={containerStyle}
      className="action-menu"
      aria-label="Action menu"
    >
      {actions.map((action, index) => (
        <button
          key={`action-${index}`}
          onClick={action.onClick}
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            backgroundColor: action.color || 'var(--primary)',
            color: 'white',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
            transition: 'transform 0.2s, box-shadow 0.2s',
            position: 'relative',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.15)';
          }}
          aria-label={action.label}
          title={action.label}
        >
          {React.cloneElement(action.icon, { size: 24 })}
          
          {/* Tooltip */}
          <div
            style={{
              position: 'absolute',
              [position === 'right' ? 'right' : 'left']: '56px',
              top: '50%',
              transform: 'translateY(-50%)',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              color: 'white',
              padding: '0.4rem 0.75rem',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
              opacity: 0,
              transition: 'opacity 0.2s',
            }}
            className="action-tooltip"
          >
            {action.label}
          </div>
        </button>
      ))}
    </div>
  );
}

export default ActionMenu;
