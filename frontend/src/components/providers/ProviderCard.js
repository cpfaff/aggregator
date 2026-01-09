import React from 'react';
import { Database, Globe, Server, Edit, Trash2, ExternalLink, Clock } from 'lucide-react';

const ProviderCard = ({ provider, currentUser, onEdit, onDelete, onViewDetails }) => {
  // Handler for card click
  const handleCardClick = (e) => {
    // Don't trigger navigation if clicking on edit or delete buttons
    if (e.target.closest('button')) {
      return;
    }
    onViewDetails(provider);
  };

  // Handle delete click
  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete(provider);
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
            Provider
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
        {/* Title with better prominence */}
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 600, 
          margin: '0 0 0.5rem 0',
          paddingLeft: '0.25rem',
          color: 'var(--text)',
          lineHeight: '1.4',
          display: '-webkit-box',
          WebkitLineClamp: '3',
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
        title={provider.name} // Adds tooltip on hover for long titles
        >
          {provider.name}
        </h3>
        
        {/* Datacenter location displayed prominently */}
        {provider.datacenter && (
          <div style={{ 
            paddingLeft: '0.25rem',
            marginBottom: '0.5rem',
          }}>
            <span style={{ 
              fontSize: '0.875rem', 
              color: 'var(--text)',
              fontWeight: 500
            }}>
              {provider.datacenter}
            </span>
          </div>
        )}
        
        {/* Last Updated timestamp - subtle styling below datacenter */}
        {provider.updated_at && (
          <div style={{ 
            paddingLeft: '0.25rem',
            marginBottom: '1rem',
          }}>
            <span style={{ 
              fontSize: '0.75rem', 
              color: 'var(--text-light)',
              opacity: 0.7,
            }}>
              Last updated: {new Date(provider.updated_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
              })}
            </span>
          </div>
        )}
                
        {/* Flexible spacer */}
        <div style={{ flexGrow: 1, minHeight: '0.5rem' }}></div>
        
        {/* Information sections with clear labels */}
        <div style={{ 
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}>
          {/* Stats section with flatter design */}
          <div style={{ position: 'relative' }}>
            {/* Vertical border for the section */}
            <div style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              left: '0.25rem',
              width: '1.5px',
              backgroundColor: 'var(--text-light)',
              opacity: 0.4,
              zIndex: 0
            }}></div>
            
            <div style={{ 
              fontSize: '0.8125rem', 
              textTransform: 'uppercase', 
              fontWeight: 600, 
              color: 'var(--text-light)',
              marginBottom: '0.75rem',
              letterSpacing: '0.025em',
              display: 'flex',
              alignItems: 'center',
              paddingLeft: '0.75rem',
              position: 'relative',
              zIndex: 1
            }}>
              Stats
            </div>
            
            <div style={{ 
              paddingLeft: '1.5rem',
              position: 'relative',
              zIndex: 1
            }}>
              {/* Datasets */}
              <div style={{
                display: 'flex',
                alignItems: 'center'
              }}>
                <Database
                  size={15}
                  style={{
                    color: 'var(--primary)',
                    marginRight: '0.75rem',
                    flexShrink: 0
                  }}
                />
                <span style={{ 
                  fontSize: '0.8125rem', 
                  color: 'var(--text)',
                  display: 'flex',
                  alignItems: 'center',
                }}>
                  <span style={{ 
                    fontWeight: 600, 
                    color: (provider.datasets && provider.datasets.length > 0) ? 'var(--text)' : 'var(--text-light)',
                    marginRight: '0.375rem'
                  }}>
                    {provider.datasets ? provider.datasets.length : 0}
                  </span> 
                  {(provider.datasets && provider.datasets.length === 1) ? 'dataset' : 'datasets'}
                </span>
              </div>
            </div>
          </div>
          
          {/* Links section with flatter design */}
          <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '1rem', position: 'relative' }}>
            {/* Vertical border for the section */}
            <div style={{
              position: 'absolute',
              top: '1rem', /* Account for the padding-top */
              bottom: 0,
              left: '0.25rem',
              width: '1.5px',
              backgroundColor: 'var(--text-light)',
              opacity: 0.4,
              zIndex: 0
            }}></div>
            
            <div style={{ 
              fontSize: '0.8125rem', 
              textTransform: 'uppercase', 
              fontWeight: 600, 
              color: 'var(--text-light)',
              marginBottom: '0.75rem',
              letterSpacing: '0.025em',
              display: 'flex',
              alignItems: 'center',
              paddingLeft: '0.75rem',
              position: 'relative',
              zIndex: 1
            }}>
              Links
            </div>
            
            <div style={{ 
              paddingLeft: '1.5rem',
              position: 'relative',
              zIndex: 1
            }}>
              {/* Website */}
              {provider.url && (
                <a
                  href={provider.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    fontSize: '0.8125rem',
                    color: 'var(--text)',
                    textDecoration: 'none',
                    fontWeight: 500,
                    marginBottom: provider.biocaseUrl ? '0.75rem' : 0
                  }}
                  onClick={(e) => e.stopPropagation()}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--text)';
                  }}
                >
                  <Globe
                    size={15}
                    style={{
                      marginRight: '0.75rem',
                      flexShrink: 0,
                      color: 'var(--primary)'
                    }}
                  />
                  Website
                  <ExternalLink size={11} style={{ marginLeft: '0.25rem', opacity: 0.5 }} />
                </a>
              )}
              
              {/* BioCASe URL */}
              {provider.biocaseUrl && (
                <a
                  href={provider.biocaseUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    fontSize: '0.8125rem',
                    color: 'var(--text)',
                    textDecoration: 'none',
                    fontWeight: 500,
                  }}
                  onClick={(e) => e.stopPropagation()}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--text)';
                  }}
                >
                  <Server
                    size={15}
                    style={{
                      marginRight: '0.75rem',
                      flexShrink: 0,
                      color: 'var(--primary)'
                    }}
                  />
                  BioCASe
                  <ExternalLink size={11} style={{ marginLeft: '0.25rem', opacity: 0.5 }} />
                </a>
              )}
              
              {/* Show placeholder if no links are available */}
              {!provider.url && !provider.biocaseUrl && (
                <div style={{ 
                  display: 'flex',
                  alignItems: 'center', 
                  fontSize: '0.8125rem',
                  color: 'var(--text-light)',
                }}>
                  <Globe 
                    size={15} 
                    style={{ 
                      marginRight: '0.75rem', 
                      flexShrink: 0 
                    }} 
                  />
                  <span style={{ fontStyle: 'italic' }}>
                    No links available
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* ACTIONS AREA */}
      <div style={{ 
        display: 'flex',
        padding: '0.75rem 1.25rem',
        gap: '0.625rem',
        borderTop: '1px solid var(--border)',
        justifyContent: 'flex-end',
        backgroundColor: 'var(--card-bg)',
        minHeight: '52px',
        height: 'auto',
        flexShrink: 0,
        boxSizing: 'border-box'
      }}>
        {/* Edit Button - visible to global admins and provider curators */}
        <button 
          onClick={(e) => {
            e.stopPropagation();
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
          aria-label={`Edit provider: ${provider.name}`}
          title="Edit provider"
        >
          <Edit size={18} />
        </button>
        
        {/* Delete Button - only visible to global admins */}
        {currentUser?.is_global_admin && (
          <button 
            onClick={handleDeleteClick}
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
            aria-label={`Delete provider: ${provider.name}`}
            title="Delete provider"
          >
            <Trash2 size={18} />
          </button>
        )}
      </div>
    </div>
  );
};

export default ProviderCard;
