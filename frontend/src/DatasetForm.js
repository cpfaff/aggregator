import React, { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { apiRequest } from './apiUtils';
import ConfirmModal from './components/ui/ConfirmModal';

// Re-using the Alert and Button components from your project structure
function Alert({ type = 'error', children }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      padding: '1rem',
      borderRadius: '0.5rem',
      marginBottom: '1rem',
      gap: '0.75rem',
      backgroundColor: type === 'error' ? '#fee2e2' : '#dcfce7',
      color: type === 'error' ? 'var(--error)' : 'var(--success)',
      borderLeft: `4px solid ${type === 'error' ? 'var(--error)' : 'var(--success)'}`,
    }}>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        {type === 'error' ? (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
        ) : (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        )}
      </svg>
      {children}
    </div>
  );
}

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

function DatasetForm({ providerId, dataset, onClose, onTokenExpired }) {
  const isEditing = dataset != null;
  const [formState, setFormState] = useState({
    source: dataset ? dataset.source : '',
    title: dataset ? dataset.title : '',
    landingPageUrl: dataset ? dataset.landingPageUrl : '',
    xmlArchives: dataset && dataset.xmlArchives ? [...dataset.xmlArchives] : [],
    usefulLinks: dataset && dataset.usefulLinks ? [...dataset.usefulLinks] : [],
  });
  const [originalData, setOriginalData] = useState({
    xmlArchives: dataset && dataset.xmlArchives ? [...dataset.xmlArchives] : [],
    usefulLinks: dataset && dataset.usefulLinks ? [...dataset.usefulLinks] : [],
  });
  const [validationErrors, setValidationErrors] = useState({});
  const [confirmAction, setConfirmAction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Helper to update form state with validation
  const updateFormField = (field, value) => {
    setFormState(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear validation error when field is updated
    if (validationErrors[field]) {
      setValidationErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  // XML Archive operations
  const addXmlArchive = () => {
    setFormState(prev => ({
      ...prev,
      xmlArchives: [
        ...prev.xmlArchives,
        { id: null, url: '', isLatest: false }
      ]
    }));
  };

  const updateXmlArchive = (index, field, value) => {
    setFormState(prev => {
      const updatedArchives = [...prev.xmlArchives];
      
      // If marking this item as latest, uncheck all other XML archives
      if (field === 'isLatest' && value === true) {
        // Uncheck all other XML archives
        updatedArchives.forEach((archive, idx) => {
          if (idx !== index) {
            updatedArchives[idx] = {
              ...archive,
              isLatest: false
            };
          }
        });
        
        // Set current archive as latest
        updatedArchives[index] = {
          ...updatedArchives[index],
          [field]: value
        };
        
        return {
          ...prev,
          xmlArchives: updatedArchives
        };
      } else {
        // For other fields or unchecking, just update normally
        updatedArchives[index] = {
          ...updatedArchives[index],
          [field]: value
        };
        
        return {
          ...prev,
          xmlArchives: updatedArchives
        };
      }
    });
    
    // Clear validation errors
    const errorKey = `xml_${index}_${field}`;
    if (validationErrors[errorKey]) {
      setValidationErrors(prev => ({
        ...prev,
        [errorKey]: null
      }));
    }
  };

  const removeXmlArchive = (index) => {
    const archive = formState.xmlArchives[index];
    const displayUrl = archive.url || `Archive ${index + 1}`;
    
    // Force the confirmAction state to update
    setConfirmAction(null);  // First clear it
    
    // Then set it with a slight delay to ensure state update
    setTimeout(() => {
      setConfirmAction({
        message: `Are you sure you want to remove XML Archive "${displayUrl}"? This action cannot be undone.`,
        onConfirm: () => {
          setFormState(prev => ({
            ...prev,
            xmlArchives: prev.xmlArchives.filter((_, idx) => idx !== index)
          }));
          setConfirmAction(null);
        },
        onCancel: () => setConfirmAction(null),
      });
    }, 10);
  };

  // Useful Links operations
  const addUsefulLink = () => {
    setFormState(prev => ({
      ...prev,
      usefulLinks: [
        ...prev.usefulLinks,
        { id: null, title: '', url: '', isLatest: false }
      ]
    }));
  };

  const updateUsefulLink = (index, field, value) => {
    setFormState(prev => {
      const updatedLinks = [...prev.usefulLinks];
      
      // If marking this item as latest, uncheck all other useful links
      if (field === 'isLatest' && value === true) {
        // Uncheck all other useful links
        updatedLinks.forEach((link, idx) => {
          if (idx !== index) {
            updatedLinks[idx] = {
              ...link,
              isLatest: false
            };
          }
        });
        
        // Set current link as latest
        updatedLinks[index] = {
          ...updatedLinks[index],
          [field]: value
        };
        
        return {
          ...prev,
          usefulLinks: updatedLinks
        };
      } else {
        // For other fields or unchecking, just update normally
        updatedLinks[index] = {
          ...updatedLinks[index],
          [field]: value
        };
        
        return {
          ...prev,
          usefulLinks: updatedLinks
        };
      }
    });
    
    // Clear validation errors
    const errorKey = `link_${index}_${field}`;
    if (validationErrors[errorKey]) {
      setValidationErrors(prev => ({
        ...prev,
        [errorKey]: null
      }));
    }
  };

  const removeUsefulLink = (index) => {
    const link = formState.usefulLinks[index];
    const displayName = link.title || `Link ${index + 1}`;
    
    // Force the confirmAction state to update
    setConfirmAction(null);  // First clear it
    
    // Then set it with a slight delay to ensure state update
    setTimeout(() => {
      setConfirmAction({
        message: `Are you sure you want to remove Useful Link "${displayName}"? This action cannot be undone.`,
        onConfirm: () => {
          setFormState(prev => ({
            ...prev,
            usefulLinks: prev.usefulLinks.filter((_, idx) => idx !== index)
          }));
          setConfirmAction(null);
        },
        onCancel: () => setConfirmAction(null),
      });
    }, 10);
  };

  // Form validation
  const validateForm = () => {
    const errors = {};
    
    // Validate dataset fields
    if (!formState.source.trim()) {
      errors.source = 'Source is required';
    }
    if (!formState.title.trim()) {
      errors.title = 'Title is required';
    }
    
    // Validate XML archives
    formState.xmlArchives.forEach((archive, archIndex) => {
      if (!archive.url.trim()) {
        errors[`xml_${archIndex}_url`] = 'URL is required';
      }
    });
    
    // Validate useful links
    formState.usefulLinks.forEach((link, linkIndex) => {
      if (!link.title.trim()) {
        errors[`link_${linkIndex}_title`] = 'Title is required';
      }
      if (!link.url.trim()) {
        errors[`link_${linkIndex}_url`] = 'URL is required';
      }
    });
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    if (!validateForm()) {
      setError('Please fix the validation errors before submitting.');
      setIsLoading(false);
      return;
    }
    
    try {
      // Filter out any empty items
      const filteredXmlArchives = formState.xmlArchives.filter(archive => 
        archive.url.trim() !== ''
      );
      
      const filteredUsefulLinks = formState.usefulLinks.filter(link => 
        link.title.trim() !== '' && 
        link.url.trim() !== ''
      );
      
      // Create sanitized form data object
      const sanitizedFormData = {
        source: formState.source,
        title: formState.title,
        landingPageUrl: formState.landingPageUrl && formState.landingPageUrl.trim() !== '' 
          ? formState.landingPageUrl 
          : null
      };
      
      // Only include non-empty arrays or empty arrays when editing (to signal deletion)
      if (filteredXmlArchives.length > 0 || isEditing) {
        sanitizedFormData.xmlArchives = filteredXmlArchives;
      }
      
      if (filteredUsefulLinks.length > 0 || isEditing) {
        sanitizedFormData.usefulLinks = filteredUsefulLinks;
      }
      
      let res;
      if (isEditing) {
        res = await apiRequest(`/data-providers/${providerId}/data-sets/${dataset.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sanitizedFormData)
        }, onTokenExpired);
      } else {
        res = await apiRequest(`/data-providers/${providerId}/data-sets`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sanitizedFormData)
        }, onTokenExpired);
      }
      
      if (!res.ok) {
        let errorMessage = 'Failed to save dataset';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // If we can't parse the error response, use the default message
        }
        setError(errorMessage);
        setIsLoading(false);
        return;
      }
      
      const updatedDataset = await res.json();
      
      // Normalize the dataset response to ensure xmlArchives and usefulLinks are always arrays
      const normalizedDataset = {
        ...updatedDataset,
        xmlArchives: Array.isArray(updatedDataset.xmlArchives) ? updatedDataset.xmlArchives : [],
        usefulLinks: Array.isArray(updatedDataset.usefulLinks) ? updatedDataset.usefulLinks : []
      };
      
      setIsLoading(false);
      onClose(normalizedDataset);
    } catch (err) {
      // Only set error if it's not a token expiration error
      // Token expiration is handled by the onTokenExpired callback
      if (!err.message || !err.message.includes('Session expired')) {
        setError('Error saving dataset: ' + err.message);
      }
      setIsLoading(false);
    }
  };

  // Field error display helper
  const getFieldErrorMessage = (fieldName) => {
    return validationErrors[fieldName] ? (
      <div style={{
        fontSize: '0.75rem',
        color: 'var(--error)',
        marginTop: '0.25rem',
      }}>
        {validationErrors[fieldName]}
      </div>
    ) : null;
  };

  // Check if there's a confirmation action in progress
  const hasConfirmAction = confirmAction !== null;

  return (
    <div>
      {error && <Alert type="error">{error}</Alert>}
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ 
            display: 'block', 
            fontSize: '0.875rem', 
            fontWeight: 500, 
            marginBottom: '0.5rem', 
            color: 'var(--text)',
          }}>
            Source
          </label>
          <input
            type="text"
            value={formState.source || ''}
            onChange={(e) => updateFormField('source', e.target.value)}
            required
            placeholder="Enter dataset source"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.source ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('source')}
        </div>
        
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ 
            display: 'block', 
            fontSize: '0.875rem', 
            fontWeight: 500, 
            marginBottom: '0.5rem', 
            color: 'var(--text)',
          }}>
            Title
          </label>
          <input
            type="text"
            value={formState.title || ''}
            onChange={(e) => updateFormField('title', e.target.value)}
            required
            placeholder="Enter dataset title"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.title ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('title')}
        </div>
        
        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ 
            display: 'block', 
            fontSize: '0.875rem', 
            fontWeight: 500, 
            marginBottom: '0.5rem', 
            color: 'var(--text)',
          }}>
            Landing Page URL
          </label>
          <input
            type="url"
            value={formState.landingPageUrl || ''}
            onChange={(e) => updateFormField('landingPageUrl', e.target.value)}
            placeholder="https://example.com/dataset"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.landingPageUrl ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('landingPageUrl')}
        </div>
        
        {/* XML Archives Section */}
        <div style={{ margin: '1rem 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h5 style={{ 
              fontSize: '0.875rem', 
              fontWeight: 600, 
              margin: 0,
              color: 'var(--text)',
            }}>
              XML Archives
            </h5>
            <Button 
              variant="primary" 
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                addXmlArchive();
              }} 
              style={{
                padding: '0.375rem 0.75rem',
                height: 'auto',
                fontSize: '0.75rem',
                backgroundColor: 'var(--card-bg)',
                color: 'var(--primary)',
                border: '1.5px solid var(--primary)',
                fontWeight: 500,
              }}
            >
              Add Archive
            </Button>
          </div>
          
          {formState.xmlArchives.length === 0 ? (
            <div style={{ 
              padding: '1rem', 
              backgroundColor: 'var(--subtle-bg)', 
              borderRadius: '0.5rem', 
              fontSize: '0.875rem', 
              color: 'var(--text-light)', 
              textAlign: 'center',
              marginBottom: '1rem',
            }}>
              No XML archives added
            </div>
          ) : (
            formState.xmlArchives.map((archive, archIndex) => (
              <div 
                key={archIndex} 
                style={{ 
                  padding: '1rem', 
                  backgroundColor: 'var(--subtle-bg)', 
                  borderRadius: '0.5rem', 
                  marginBottom: '0.75rem',
                }}
              >
                <div style={{ marginBottom: '0.75rem' }}>
                  <label style={{ 
                    display: 'block', 
                    fontSize: '0.875rem', 
                    fontWeight: 500, 
                    marginBottom: '0.5rem', 
                    color: 'var(--text)',
                  }}>
                    URL
                  </label>
                  <input
                    type="url"
                    value={archive.url || ''}
                    onChange={(e) => updateXmlArchive(archIndex, 'url', e.target.value)}
                    placeholder="https://example.com/archive.xml"
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      borderRadius: '0.5rem',
                      border: `1px solid ${validationErrors[`xml_${archIndex}_url`] ? 'var(--error)' : 'var(--border)'}`,
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--text)',
                      transition: 'border-color 0.2s',
                    }}
                  />
                  {getFieldErrorMessage(`xml_${archIndex}_url`)}
                </div>
                
                <div style={{ marginBottom: '0.75rem' }}>
                  <label style={{ 
                    display: 'flex', 
                    paddingLeft: '0.2rem',
                    alignItems: 'center',
                    fontSize: '0.875rem', 
                    fontWeight: 500, 
                    color: 'var(--text)',
                  }}>
                    <input
                      type="checkbox"
                      checked={archive.isLatest}
                      onChange={(e) => updateXmlArchive(archIndex, 'isLatest', e.target.checked)}
                      style={{
                        width: '1rem',
                        height: '1rem',
                        borderRadius: '0.25rem',
                        marginRight: '0.5rem',
                        accentColor: 'var(--primary)',
                      }}
                    />
                    Is Latest Version
                  </label>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      removeXmlArchive(archIndex);
                    }}
                    style={{
                      width: '36px',
                      height: '36px',
                      backgroundColor: 'var(--card-bg)',
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
                    aria-label="Remove XML Archive"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        
        {/* Useful Links Section */}
        <div style={{ margin: '1rem 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h5 style={{ 
              fontSize: '0.875rem', 
              fontWeight: 600, 
              margin: 0,
              color: 'var(--text)',
            }}>
              Useful Links
            </h5>
            <Button 
              variant="primary" 
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                addUsefulLink();
              }} 
              style={{
                padding: '0.375rem 0.75rem',
                height: 'auto',
                fontSize: '0.75rem',
                backgroundColor: 'var(--card-bg)',
                color: 'var(--primary)',
                border: '1.5px solid var(--primary)',
                fontWeight: 500,
              }}
            >
              Add Link
            </Button>
          </div>
          
          {formState.usefulLinks.length === 0 ? (
            <div style={{ 
              padding: '1rem', 
              backgroundColor: 'var(--subtle-bg)', 
              borderRadius: '0.5rem', 
              fontSize: '0.875rem', 
              color: 'var(--text-light)', 
              textAlign: 'center',
              marginBottom: '1rem',
            }}>
              No useful links added
            </div>
          ) : (
            formState.usefulLinks.map((link, linkIndex) => (
              <div 
                key={linkIndex} 
                style={{ 
                  padding: '1rem', 
                  backgroundColor: 'var(--subtle-bg)', 
                  borderRadius: '0.5rem', 
                  marginBottom: '0.75rem',
                }}
              >
                <div style={{ marginBottom: '0.75rem' }}>
                  <label style={{ 
                    display: 'block', 
                    fontSize: '0.875rem', 
                    fontWeight: 500, 
                    marginBottom: '0.5rem', 
                    color: 'var(--text)',
                  }}>
                    Title
                  </label>
                  <input
                    type="text"
                    value={link.title || ''}
                    onChange={(e) => updateUsefulLink(linkIndex, 'title', e.target.value)}
                    placeholder="Enter link title"
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      borderRadius: '0.5rem',
                      border: `1px solid ${validationErrors[`link_${linkIndex}_title`] ? 'var(--error)' : 'var(--border)'}`,
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--text)',
                      transition: 'border-color 0.2s',
                    }}
                  />
                  {getFieldErrorMessage(`link_${linkIndex}_title`)}
                </div>
                
                <div style={{ marginBottom: '0.75rem' }}>
                  <label style={{ 
                    display: 'block', 
                    fontSize: '0.875rem', 
                    fontWeight: 500, 
                    marginBottom: '0.5rem', 
                    color: 'var(--text)',
                  }}>
                    URL
                  </label>
                  <input
                    type="url"
                    value={link.url || ''}
                    onChange={(e) => updateUsefulLink(linkIndex, 'url', e.target.value)}
                    placeholder="https://example.com/resource"
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      borderRadius: '0.5rem',
                      border: `1px solid ${validationErrors[`link_${linkIndex}_url`] ? 'var(--error)' : 'var(--border)'}`,
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--text)',
                      transition: 'border-color 0.2s',
                    }}
                  />
                  {getFieldErrorMessage(`link_${linkIndex}_url`)}
                </div>
                
                <div style={{ marginBottom: '0.75rem' }}>
                  <label style={{ 
                    display: 'flex', 
                    paddingLeft: '0.2rem',
                    alignItems: 'center',
                    fontSize: '0.875rem', 
                    fontWeight: 500, 
                    color: 'var(--text)',
                  }}>
                    <input
                      type="checkbox"
                      checked={link.isLatest}
                      onChange={(e) => updateUsefulLink(linkIndex, 'isLatest', e.target.checked)}
                      style={{
                        width: '1rem',
                        height: '1rem',
                        borderRadius: '0.25rem',
                        marginRight: '0.5rem',
                        accentColor: 'var(--primary)',
                      }}
                    />
                    Is Latest Version
                  </label>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      removeUsefulLink(linkIndex);
                    }}
                    style={{
                      width: '36px',
                      height: '36px',
                      backgroundColor: 'var(--card-bg)',
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
                    aria-label="Remove Useful Link"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        
        <div style={{ 
          display: 'flex', 
          justifyContent: 'flex-end', 
          gap: '0.75rem',
          marginTop: '1.5rem', 
        }}>
          <Button
            variant="secondary"
            onClick={() => onClose(null)}
            type="button"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            isLoading={isLoading}
            disabled={isLoading}
          >
            {isEditing ? (isLoading ? 'Updating...' : 'Update Dataset') : (isLoading ? 'Creating...' : 'Create Dataset')}
          </Button>
        </div>
      </form>
      
      {/* The confirmation modal must be rendered at the top level */}
      {hasConfirmAction && (
        <ConfirmModal
          isOpen={hasConfirmAction}
          title="Confirm Removal"
          message={confirmAction?.message}
          confirmText="Delete"
          cancelText="Cancel"
          confirmVariant="danger"
          onConfirm={confirmAction?.onConfirm}
          onCancel={confirmAction?.onCancel}
        />
      )}
    </div>
  );
}

export default DatasetForm;
