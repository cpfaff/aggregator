import React, { useState } from 'react';
import { apiRequest } from '../../utils/apiUtils';
import Button from '../ui/Button';
import Alert from '../ui/Alert';

// Simplified ProviderForm component focused only on core provider information
function ProviderForm({ provider, onClose, onTokenExpired }) {
  const isEditing = provider != null;
  const [formState, setFormState] = useState({
    name: provider ? provider.name : '',
    shortName: provider ? provider.shortName : '',
    datacenter: provider ? provider.datacenter : '',
    url: provider ? provider.url : '',
    biocaseUrl: provider ? provider.biocaseUrl : '',
  });
  const [validationErrors, setValidationErrors] = useState({});
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

  // Form validation
  const validateForm = () => {
    const errors = {};
    
    // Validate provider fields
    if (!formState.datacenter.trim()) {
      errors.datacenter = 'Datacenter is required';
    }
    if (!formState.shortName.trim()) {
      errors.shortName = 'Short Name is required';
    }
    if (!formState.name.trim()) {
      errors.name = 'Full Name is required';
    }
    
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
      // Clone the form state to avoid mutating the state directly
      const sanitizedFormData = { ...formState };
      
      // Remove any empty strings for optional URL fields
      // Modified to handle all empty string cases consistently
      if (!sanitizedFormData.url || sanitizedFormData.url.trim() === '') {
        sanitizedFormData.url = null;
      }
      
      if (!sanitizedFormData.biocaseUrl || sanitizedFormData.biocaseUrl.trim() === '') {
        sanitizedFormData.biocaseUrl = null;
      }
      
      let res;
      if (isEditing) {
        res = await apiRequest(`/data-providers/${provider.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sanitizedFormData)
        }, onTokenExpired);
      } else {
        res = await apiRequest('/data-providers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sanitizedFormData)
        }, onTokenExpired);
      }
      
      if (!res.ok) {
        let errorMessage = 'Failed to save provider';
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
      
      const updatedProvider = await res.json();
      setIsLoading(false);
      onClose(updatedProvider);
    } catch (err) {
      // Only set error if it's not a token expiration error
      // Token expiration is handled by the onTokenExpired callback
      if (!err.message || !err.message.includes('Session expired')) {
        setError('Error saving provider: ' + err.message);
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
            Datacenter
          </label>
          <input
            type="text"
            value={formState.datacenter || ''}
            onChange={(e) => updateFormField('datacenter', e.target.value)}
            required
            placeholder="Enter datacenter name"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.datacenter ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('datacenter')}
        </div>
        
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ 
            display: 'block', 
            fontSize: '0.875rem', 
            fontWeight: 500, 
            marginBottom: '0.5rem', 
            color: 'var(--text)',
          }}>
            Short Name
          </label>
          <input
            type="text"
            value={formState.shortName || ''}
            onChange={(e) => updateFormField('shortName', e.target.value)}
            required
            placeholder="Enter short name"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.shortName ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('shortName')}
          <div style={{
            fontSize: '0.75rem',
            color: 'var(--text-light)',
            marginTop: '0.25rem',
          }}>
            A brief identifier for this provider
          </div>
        </div>
        
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ 
            display: 'block', 
            fontSize: '0.875rem', 
            fontWeight: 500, 
            marginBottom: '0.5rem', 
            color: 'var(--text)',
          }}>
            Full Name
          </label>
          <input
            type="text"
            value={formState.name || ''}
            onChange={(e) => updateFormField('name', e.target.value)}
            required
            placeholder="Enter full provider name"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.name ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('name')}
        </div>
        
        <div style={{ marginBottom: '1rem' }}>
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
            value={formState.url || ''}
            onChange={(e) => updateFormField('url', e.target.value)}
            placeholder="https://example.com"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.url ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('url')}
        </div>
        
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ 
            display: 'block', 
            fontSize: '0.875rem', 
            fontWeight: 500, 
            marginBottom: '0.5rem', 
            color: 'var(--text)',
          }}>
            Biocase URL
          </label>
          <input
            type="url"
            value={formState.biocaseUrl || ''}
            onChange={(e) => updateFormField('biocaseUrl', e.target.value)}
            placeholder="https://biocase.example.com"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.625rem 0.75rem',
              fontSize: '0.875rem',
              borderRadius: '0.5rem',
              border: `1px solid ${validationErrors.biocaseUrl ? 'var(--error)' : 'var(--border)'}`,
              backgroundColor: 'var(--card-bg)',
              color: 'var(--text)',
              transition: 'border-color 0.2s',
            }}
          />
          {getFieldErrorMessage('biocaseUrl')}
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
            {isEditing ? (isLoading ? 'Updating...' : 'Update Provider') : (isLoading ? 'Creating...' : 'Create Provider')}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default ProviderForm;
