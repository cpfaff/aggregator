import React from 'react';
import { Database, Globe, Server, Edit, Trash2 } from 'lucide-react';

const ProviderCard = ({ provider, currentUser, onEdit, onDelete }) => {
  return (
    <div 
      style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        border: '1px solid var(--border)',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        transition: 'all 0.3s',
        display: 'flex',
        flexDirection: 'column',
        height: '100%', // Make card fill its container height
      }}
    >
      <div style={{ 
        padding: '1.25rem', 
        flexGrow: 1, // Make body expand to fill available space
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Provider name and shortName on the same line */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.25rem' }}>
          <h3 style={{ 
            fontSize: '1.125rem', 
            fontWeight: 600, 
            margin: 0,
            color: 'var(--text)',
          }}>
            {provider.name}
          </h3>
          <span style={{ 
            backgroundColor: 'var(--subtle-bg)',
            padding: '0.25rem 0.625rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: 500,
            color: 'var(--text)',
            marginLeft: '0.5rem',
          }}>
            {provider.shortName}
          </span>
        </div>
        
        <p style={{ 
          color: 'var(--text-light)', 
          fontSize: '0.875rem', 
          margin: '0 0 1rem 0',
        }}>
          {provider.datacenter}
        </p>
        
        {/* Flexible spacer to push links and stats to the bottom */}
        <div style={{ flexGrow: 1 }}></div>
        
        {/* Stats section with subtle heading */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ 
            fontSize: '0.75rem', 
            textTransform: 'uppercase', 
            fontWeight: 500, 
            color: 'var(--text-light)',
            marginBottom: '0.5rem',
            letterSpacing: '0.025em',
          }}>
            Stats
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Database size={16} style={{ color: 'var(--text-light)', marginRight: '0.5rem' }} />
            <span style={{ fontSize: '0.875rem', color: 'var(--text-light)' }}>
              <span style={{ fontWeight: 500, color: 'var(--text)' }}>
                {provider.datasets ? provider.datasets.length : 0}
              </span> datasets
            </span>
          </div>
        </div>
        
        {/* Links section with subtle heading */}
        <div>
          <div style={{ 
            fontSize: '0.75rem', 
            textTransform: 'uppercase', 
            fontWeight: 500, 
            color: 'var(--text-light)',
            marginBottom: '0.5rem',
            letterSpacing: '0.025em',
          }}>
            Links
          </div>
          
          <div style={{ 
            display: 'flex', 
            flexWrap: 'wrap', 
            gap: '1rem', 
          }}>
            {provider.url && (
              <a 
                href={provider.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  fontSize: '0.875rem',
                  color: 'var(--primary)',
                  textDecoration: 'none',
                }}
              >
                <Globe size={16} style={{ marginRight: '0.5rem' }} />
                Website
              </a>
            )}
            
            {provider.biocaseUrl && (
              <a 
                href={provider.biocaseUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  fontSize: '0.875rem',
                  color: 'var(--primary)',
                  textDecoration: 'none',
                }}
              >
                <Server size={16} style={{ marginRight: '0.5rem' }} />
                Biocase
              </a>
            )}
            
            {/* Show placeholder if no links are available */}
            {!provider.url && !provider.biocaseUrl && (
              <span style={{ 
                fontSize: '0.875rem',
                color: 'var(--text-light)',
                fontStyle: 'italic'
              }}>
                No links available
              </span>
            )}
          </div>
        </div>
      </div>
      
      {/* Footer with action buttons - fixed height, not affected by content */}
      <div style={{ 
        borderTop: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'center',
        padding: '0.75rem',
        gap: '0.5rem',
        height: '60px',
        flexShrink: 0, // Prevent footer from shrinking
        boxSizing: 'border-box'
      }}>
        <button 
          onClick={() => onEdit(provider)}
          style={{
            width: '36px',
            height: '36px',
            backgroundColor: 'var(--subtle-bg)',
            color: 'var(--text-light)',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s',
            padding: 0
          }}
          aria-label="Edit provider"
        >
          <Edit size={18} />
        </button>
        
        {currentUser?.is_global_admin && (
          <button 
            onClick={() => onDelete(provider)}
            style={{
              width: '36px',
              height: '36px',
              backgroundColor: 'var(--subtle-bg)',
              color: 'var(--error)',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              padding: 0
            }}
            aria-label="Delete provider"
          >
            <Trash2 size={18} />
          </button>
        )}
      </div>
    </div>
  );
};

export default ProviderCard;
