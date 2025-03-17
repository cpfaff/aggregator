import React from 'react';
import { Database, Globe, Server, Edit, Trash2 } from 'lucide-react';

const ProviderCard = ({ provider, currentUser, onEdit, onDelete, onViewDetails }) => {
  // Handler for card click
  const handleCardClick = (e) => {
    // Don't trigger navigation if clicking on edit or delete buttons
    if (e.target.closest('button')) {
      return;
    }
    onViewDetails(provider);
  };

  return (
    <div 
      style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        border: '1px solid var(--border)',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        transition: 'box-shadow 0.2s',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        cursor: 'pointer',
      }}
      onClick={handleCardClick}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.05)';
      }}
      role="button"
      aria-label={`View details for ${provider.name}`}
    >
      {/* HEADER AREA */}
      <div style={{ 
        padding: '1.25rem 1.25rem 0.75rem',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        {/* Provider badge */}
        <div>
          <span style={{ 
            backgroundColor: 'var(--subtle-bg)',
            padding: '0.25rem 0.625rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: 500,
            color: 'var(--text-light)',
            display: 'inline-block',
          }}>
            Provider: {provider.shortName || ''}
          </span>
        </div>
        
        {/* Provider ID badge if available */}
        {provider.id && (
          <span style={{
            backgroundColor: 'var(--subtle-bg)',
            padding: '0.25rem 0.625rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: 700,
            color: 'var(--text-light)',
            display: 'inline-block',
          }}
          aria-label={`Provider ID: ${provider.id}`}
          >
            #{provider.id}
          </span>
        )}
      </div>

      {/* CONTENT AREA */}
      <div style={{ 
        padding: '1.25rem', 
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Provider name with better prominence */}
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 600, 
          margin: '0 0 1rem 0',
          paddingLeft: '0.25rem',
          color: 'var(--text)',
          lineHeight: '1.4',
        }}
        title={provider.name}
        >
          {provider.name}
        </h3>
        
        {/* Datacenter location displayed prominently */}
        {provider.datacenter && (
          <div style={{ 
            display: 'flex',
            marginBottom: '1.25rem',
            paddingLeft: '0.25rem',
          }}>
            <span style={{ 
              color: 'var(--text-light)', 
              fontSize: '0.875rem',
            }}>
              {provider.datacenter}
            </span>
          </div>
        )}
                
        {/* Flexible spacer */}
        <div style={{ flexGrow: 1 }}></div>
        
        {/* Information sections with clear labels */}
        <div style={{ 
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}>
          {/* Stats section with improved styling */}
          <div>
            <h4 style={{ 
              fontSize: '0.75rem', 
              textTransform: 'uppercase', 
              fontWeight: 500, 
              color: 'var(--text-light)',
              marginBottom: '0.5rem',
              letterSpacing: '0.025em',
              paddingLeft: '0.25rem',
            }}>
              Stats
            </h4>
            
            <div style={{ 
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'var(--subtle-bg)',
              padding: '0.5rem 0.75rem',
              borderRadius: '0.375rem',
            }}>
              <Database size={16} style={{ color: 'var(--text-light)', marginRight: '0.5rem' }} />
              <span style={{ fontSize: '0.875rem', color: 'var(--text-light)' }}>
                <span style={{ fontWeight: 600, color: 'var(--text)' }}>
                  {provider.datasets ? provider.datasets.length : 0}
                </span> datasets
              </span>
            </div>
          </div>
          
          {/* Links section with improved styling */}
          <div>
            <h4 style={{ 
              fontSize: '0.75rem', 
              textTransform: 'uppercase', 
              fontWeight: 500, 
              color: 'var(--text-light)',
              marginBottom: '0.5rem',
              letterSpacing: '0.025em',
              paddingLeft: '0.25rem',
            }}>
              Links
            </h4>
            
            <div style={{ 
              display: 'flex', 
              flexWrap: 'wrap', 
              gap: '0.75rem', 
              backgroundColor: 'var(--subtle-bg)',
              padding: '0.75rem',
              borderRadius: '0.375rem',
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
                    fontWeight: 500,
                  }}
                  onClick={(e) => e.stopPropagation()} // Prevent card click
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
                    fontWeight: 500,
                  }}
                  onClick={(e) => e.stopPropagation()} // Prevent card click
                >
                  <Server size={16} style={{ marginRight: '0.5rem' }} />
                  BioCASe
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
      </div>
      
      {/* FOOTER with action buttons only for admins */}
      {currentUser?.is_global_admin && (
        <div style={{ 
          borderTop: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          padding: '0.75rem 1.25rem',
          gap: '0.5rem',
          backgroundColor: 'var(--card-bg)',
          minHeight: '52px',
          height: 'auto',
          flexShrink: 0,
          boxSizing: 'border-box'
        }}>
          <button 
            onClick={(e) => {
              e.stopPropagation(); // Prevent card click
              onEdit(provider);
            }}
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
          
          <button 
            onClick={(e) => {
              e.stopPropagation(); // Prevent card click
              onDelete(provider);
            }}
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
        </div>
      )}
    </div>
  );
};

export default ProviderCard;
