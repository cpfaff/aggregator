import React from 'react';
import { Database, ExternalLink, FileText, Globe, Edit, Trash2, Archive } from 'lucide-react';
import { useAuth } from './AuthContext';

const DatasetCard = ({ dataset, onEdit, onDelete }) => {
  const { currentUser } = useAuth();

  // Debug logging
  console.log('Dataset Provider ID:', dataset.provider_id);
  console.log('Current User Roles:', currentUser?.provider_roles);
  console.log('Is Global Admin:', currentUser?.is_global_admin);

  // Check if user is global admin or provider admin
  // Convert provider_id to string for comparison since IDs from API might be numbers
  const canDelete = currentUser?.is_global_admin || 
                   (currentUser?.provider_roles && 
                    currentUser.provider_roles[String(dataset.provider_id)] === 'admin');

  // Debug the result
  console.log('Can Delete:', canDelete);

  // Handle delete click
  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete(dataset);
  };

  // Handle edit click
  const handleEditClick = (e) => {
    e.stopPropagation();
    onEdit(dataset);
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
        position: 'relative',
        cursor: 'default',
      }}
      className="dataset-card"
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.05)';
      }}
      role="article"
      aria-label={`Dataset: ${dataset.title}`}
    >
      {/* HEADER AREA */}
      <div style={{ 
        padding: '1.25rem 1.25rem 0.75rem',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        {/* Dataset badge */}
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
            Dataset
          </span>
        </div>
        
        {/* Dataset ID badge if available */}
        {dataset.id && (
          <span style={{
            backgroundColor: 'var(--subtle-bg)',
            padding: '0.25rem 0.625rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: 700,
            color: 'var(--text-light)',
            display: 'inline-block',
          }}
          aria-label={`Dataset ID: ${dataset.id}`}
          >
            #{dataset.id}
          </span>
        )}
      </div>
      
      {/* BODY CONTENT */}
      <div style={{ 
        padding: '0.75rem 1.25rem 1.25rem', 
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Title with better prominence */}
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 600, 
          margin: '0 0 1rem 0',
          paddingLeft: '0.25rem',
          color: 'var(--text)',
          lineHeight: '1.4',
          display: '-webkit-box',
          WebkitLineClamp: '3',
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
        title={dataset.title} // Adds tooltip on hover for long titles
        >
          {dataset.title}
        </h3>
        
        {/* Flexible spacer */}
        <div style={{ flexGrow: 1, minHeight: '0.5rem' }}></div>
        
        {/* Main content sections */}
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
              display: 'flex', 
              flexDirection: 'column', 
              gap: '0.75rem',
              paddingLeft: '1.5rem',
              position: 'relative',
              zIndex: 1
            }}>
              {/* Archives */}
              <div style={{ 
                display: 'flex', 
                alignItems: 'center',
              }}>
                <FileText 
                  size={15} 
                  style={{ 
                    color: (Array.isArray(dataset.xmlArchives) && dataset.xmlArchives.length > 0) ? 'var(--primary)' : 'var(--text-light)', 
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
                    color: (Array.isArray(dataset.xmlArchives) && dataset.xmlArchives.length > 0) ? 'var(--text)' : 'var(--text-light)',
                    marginRight: '0.375rem'
                  }}>
                    {Array.isArray(dataset.xmlArchives) ? dataset.xmlArchives.length : 0}
                  </span> 
                  {(Array.isArray(dataset.xmlArchives) && dataset.xmlArchives.length === 1) ? 'archive' : 'archives'}
                </span>
              </div>
              
              {/* Useful Links */}
              <div style={{ 
                display: 'flex', 
                alignItems: 'center',
              }}>
                <Globe 
                  size={15} 
                  style={{ 
                    color: (Array.isArray(dataset.usefulLinks) && dataset.usefulLinks.length > 0) ? 'var(--primary)' : 'var(--text-light)', 
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
                    color: (Array.isArray(dataset.usefulLinks) && dataset.usefulLinks.length > 0) ? 'var(--text)' : 'var(--text-light)',
                    marginRight: '0.375rem'
                  }}>
                    {Array.isArray(dataset.usefulLinks) ? dataset.usefulLinks.length : 0}
                  </span> 
                  {(Array.isArray(dataset.usefulLinks) && dataset.usefulLinks.length === 1) ? 'useful link' : 'useful links'}
                </span>
              </div>
              
              {/* Sample count (if exists in the data) */}
              {dataset.sampleCount !== undefined && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center',
                }}>
                  <Database 
                    size={15} 
                    style={{ 
                      color: dataset.sampleCount > 0 ? 'var(--primary)' : 'var(--text-light)', 
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
                      color: dataset.sampleCount > 0 ? 'var(--text)' : 'var(--text-light)',
                      marginRight: '0.375rem'
                    }}>
                      {dataset.sampleCount?.toLocaleString() || 0}
                    </span> 
                    samples
                  </span>
                </div>
              )}
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
              {/* Landing Page */}
              {dataset.landingPageUrl ? (
                <a 
                  href={dataset.landingPageUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ 
                    display: 'flex',
                    alignItems: 'center', 
                    fontSize: '0.8125rem',
                    color: 'var(--primary)',
                    textDecoration: 'none',
                    fontWeight: 500,
                  }}
                  onClick={(e) => e.stopPropagation()} // Prevent card click
                >
                  <Globe 
                    size={15} 
                    style={{ 
                      marginRight: '0.75rem', 
                      flexShrink: 0 
                    }} 
                  />
                  Landing page
                  <ExternalLink size={11} style={{ marginLeft: '0.25rem' }} />
                </a>
              ) : (
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
                    No landing page available
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
        height: 'auto',
        minHeight: '52px',
        flexShrink: 0,
        boxSizing: 'border-box',
        borderTop: '1px solid var(--border)',
        backgroundColor: 'var(--card-bg)',
        justifyContent: 'flex-end',
      }}>
        {/* Secondary actions */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            onClick={handleEditClick}
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
            aria-label={`Edit dataset: ${dataset.title}`}
            title="Edit dataset"
          >
            <Edit size={18} />
          </button>
          
          {canDelete && (
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
              aria-label="Delete dataset"
              title="Delete dataset"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Add CSS styles to the document for more complex hover effects
const injectDatasetCardStyles = () => {
  if (!document.getElementById('dataset-card-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'dataset-card-styles';
    styleEl.innerHTML = `
      .dataset-card:focus-within {
        outline: 2px solid var(--primary);
        outline-offset: 2px;
      }
      
      .dataset-card button:focus, .dataset-card a:focus {
        outline: 2px solid var(--primary);
        outline-offset: 1px;
      }
    `;
    document.head.appendChild(styleEl);
  }
};

// Inject the styles when the component is used
if (typeof window !== 'undefined') {
  injectDatasetCardStyles();
}

export default DatasetCard;
