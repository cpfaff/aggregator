import React, { useState, useEffect } from 'react';
import { Database, ExternalLink, FileText, Globe, Edit, Trash2, Archive, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import axios from 'axios';
import ValidationResultsModal from './ValidationResultsModal';

const DatasetCard = ({ dataset, onEdit, onDelete }) => {
  const { currentUser } = useAuth();
  const [validationStatus, setValidationStatus] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);

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
  
  // Fetch validation status when component mounts
  useEffect(() => {
    if (dataset && dataset.id) {
      fetchValidationStatus();
    }
    
    // Clear any existing polling interval when component unmounts
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [dataset]);
  
  // Function to fetch validation status
  const fetchValidationStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${process.env.REACT_APP_API_BASE_URL || ''}/api/v1/validators/datasets/${dataset.id}/validation-status`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      
      const newStatus = response.data;
      setValidationStatus(newStatus);
      
      // If the status is no longer running or pending, ensure we're not in validating state
      if (newStatus.validation_status !== 'running' && newStatus.validation_status !== 'pending') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        setIsValidating(false);
      }
    } catch (error) {
      console.error('Error fetching validation status:', error);
      
      // If there's an error, stop polling and validating
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
      setIsValidating(false);
    }
  };
  
  // Update the useEffect to also react to validation status changes
  useEffect(() => {
    // If validation status changes and is not running/pending, make sure isValidating is false
    if (validationStatus && 
        validationStatus.validation_status !== 'running' && 
        validationStatus.validation_status !== 'pending') {
      setIsValidating(false);
    }
  }, [validationStatus]);
  
  // Add a safety timeout to reset validation state if it gets stuck
  useEffect(() => {
    // If we've been validating for more than 45 seconds, force reset state
    let validationTimeout;
    
    if (isValidating) {
      console.log('Starting validation safety timeout...');
      validationTimeout = setTimeout(() => {
        console.log('Validation timeout reached, resetting state');
        setIsValidating(false);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        // Force fetch latest status
        fetchValidationStatus();
      }, 45000); // 45 second timeout
    }
    
    return () => {
      if (validationTimeout) {
        clearTimeout(validationTimeout);
      }
    };
  }, [isValidating]);

  // Function to trigger validation
  const triggerValidation = async (e) => {
    e.stopPropagation();
    
    // Prevent multiple clicks
    if (isValidating) return;
    
    setIsValidating(true);
    
    // Clear any existing polling
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
    
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${process.env.REACT_APP_API_BASE_URL || ''}/api/v1/validators/datasets/${dataset.id}/validate`,
        { force: true },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      
      // Check if response indicates an immediate error
      if (response.data && response.data.status === 'error') {
        console.error('Validation API returned error:', response.data.message);
        setIsValidating(false);
        return;
      }
      
      // Immediately fetch status to update UI
      await fetchValidationStatus();
      
      // Set up polling to check status every 3 seconds
      const interval = setInterval(fetchValidationStatus, 3000);
      setPollingInterval(interval);
    } catch (error) {
      console.error('Error triggering validation:', error);
      setIsValidating(false);
      
      // Show an alert if there was an error (optional)
      alert('Error triggering validation. Please try again later.');
    }
  };
  
  // Function to open validation modal
  const openValidationModal = (e) => {
    e.stopPropagation();
    setShowValidationModal(true);
  };

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
        title={dataset.title} // Adds tooltip on hover for long titles
        >
          {dataset.title}
        </h3>
        
        {/* Last Updated timestamp - subtle styling below title */}
        {dataset.updated_at && (
          <div style={{ 
            paddingLeft: '0.25rem',
            marginBottom: '1rem',
          }}>
            <span style={{ 
              fontSize: '0.75rem', 
              color: 'var(--text-light)',
              opacity: 0.7,
            }}>
              Last updated: {new Date(dataset.updated_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
              })}
            </span>
          </div>
        )}
        
        {/* Flexible spacer */}
        <div style={{ flexGrow: 1, minHeight: '0.5rem' }}></div>
        
        {/* Main content sections */}
        <div style={{ 
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}>
          {/* Stats section with flatter design */}
          <div>
            {/* Stats content with accent bar */}
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
                      color: (Array.isArray(dataset.usefulLinks) && dataset.usefulLinks.length > 0) ? 'var(--text)' : 'var(--text-light)',
                      marginRight: '0.375rem'
                    }}>
                      {Array.isArray(dataset.usefulLinks) ? dataset.usefulLinks.length : 0}
                    </span>
                    {(Array.isArray(dataset.usefulLinks) && dataset.usefulLinks.length === 1) ? 'link' : 'links'}
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
          </div>

          {/* VALIDATION section - dedicated section for all validation UI */}
          {validationStatus && validationStatus.has_latest_archive && (
            <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '1rem', position: 'relative' }}>
              {/* Vertical border for the section */}
              <div style={{
                position: 'absolute',
                top: '1rem',
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
                Validation
              </div>

              <div style={{
                paddingLeft: '1.5rem',
                position: 'relative',
                zIndex: 1
              }}>
                {/* Validation Status - shows previous result during re-validation for stability */}
                {(() => {
                  const isRunning = isValidating || validationStatus.validation_status === 'pending' || validationStatus.validation_status === 'running';
                  const hasPreviousResult = validationStatus.is_valid !== undefined && validationStatus.is_valid !== null;

                  // Determine what to display: previous result if available, otherwise current status
                  const showValid = hasPreviousResult ? validationStatus.is_valid : false;
                  const showScore = hasPreviousResult && validationStatus.is_valid;
                  const showNotValidated = !hasPreviousResult && validationStatus.validation_status !== 'completed';

                  return (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: '1rem',
                    }}>
                      {hasPreviousResult || validationStatus.validation_status === 'completed' ? (
                        showValid ? (
                          <CheckCircle
                            size={15}
                            style={{
                              color: 'var(--success)',
                              marginRight: '0.75rem',
                              flexShrink: 0
                            }}
                          />
                        ) : (
                          <XCircle
                            size={15}
                            style={{
                              color: 'var(--error)',
                              marginRight: '0.75rem',
                              flexShrink: 0
                            }}
                          />
                        )
                      ) : (
                        <AlertCircle
                          size={15}
                          style={{
                            color: 'var(--text-light)',
                            marginRight: '0.75rem',
                            flexShrink: 0
                          }}
                        />
                      )}
                      <span style={{
                        fontSize: '0.8125rem',
                        color: 'var(--text)',
                        display: 'flex',
                        alignItems: 'center',
                      }}>
                        <span style={{
                          fontWeight: 600,
                          color: hasPreviousResult || validationStatus.validation_status === 'completed'
                            ? (showValid ? 'var(--success)' : 'var(--error)')
                            : 'var(--text-light)',
                        }}>
                          {hasPreviousResult || validationStatus.validation_status === 'completed'
                            ? (showValid
                              ? `Valid (${validationStatus.quality_score?.toFixed(1)}%)`
                              : 'Invalid')
                            : 'Not validated'}
                        </span>
                      </span>
                    </div>
                  );
                })()}

                {/* Action buttons - both always visible, disabled during validation */}
                {(() => {
                  const isRunning = isValidating || validationStatus.validation_status === 'pending' || validationStatus.validation_status === 'running';
                  const hasPreviousResult = validationStatus.is_valid !== undefined && validationStatus.is_valid !== null;
                  const showViewDetails = hasPreviousResult || validationStatus.validation_status === 'completed';

                  return (
                    <div style={{
                      display: 'flex',
                      gap: '0.5rem',
                      flexWrap: 'wrap',
                    }}>
                      <button
                        onClick={triggerValidation}
                        disabled={isRunning}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.375rem',
                          padding: '0.375rem 0.75rem',
                          border: '1.5px solid var(--primary)',
                          borderRadius: '0.5rem',
                          backgroundColor: 'var(--card-bg)',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          color: 'var(--primary)',
                          cursor: isRunning ? 'not-allowed' : 'pointer',
                          transition: 'all 150ms ease',
                          opacity: isRunning ? 0.5 : 1,
                        }}
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = 'var(--subtle-bg)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'var(--card-bg)';
                        }}
                        aria-label={isRunning ? 'Re-validating dataset...' : 'Re-validate dataset'}
                      >
                        <RefreshCw
                          size={14}
                          style={{
                            animation: isRunning ? 'spin 2s linear infinite' : 'none'
                          }}
                        />
                        Re-validate
                      </button>
                      {showViewDetails && (
                        <button
                          onClick={openValidationModal}
                          disabled={isRunning}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.375rem',
                            padding: '0.375rem 0.75rem',
                            border: '1.5px solid var(--primary)',
                            borderRadius: '0.5rem',
                            backgroundColor: 'var(--card-bg)',
                            fontSize: '0.75rem',
                            fontWeight: 500,
                            color: 'var(--primary)',
                            cursor: isRunning ? 'not-allowed' : 'pointer',
                            transition: 'all 150ms ease',
                            opacity: isRunning ? 0.5 : 1,
                          }}
                          onMouseEnter={(e) => {
                            if (!isRunning) {
                              e.currentTarget.style.backgroundColor = 'var(--subtle-bg)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = 'var(--card-bg)';
                          }}
                        >
                          <FileText size={14} />
                          View Details
                        </button>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>
          )}

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
                  <Globe
                    size={15}
                    style={{
                      marginRight: '0.75rem',
                      flexShrink: 0,
                      color: 'var(--primary)'
                    }}
                  />
                  Landing page
                  <ExternalLink size={11} style={{ marginLeft: '0.25rem', opacity: 0.5 }} />
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
        {/* Action buttons on the right */}
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
              aria-label={`Delete dataset: ${dataset.title}`}
              title="Delete dataset"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
      </div>
      
      {/* Validation Results Modal */}
      {showValidationModal && validationStatus && (
        <ValidationResultsModal
          isOpen={showValidationModal}
          onClose={() => setShowValidationModal(false)}
          validationResults={validationStatus}
        />
      )}
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
      
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
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
