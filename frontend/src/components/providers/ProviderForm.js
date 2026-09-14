import React from 'react';
import { apiRequest, readJson } from '../../utils/apiUtils';
import useFormValidation from '../../utils/useFormValidation';
import validationRules from '../../utils/validationRules';
import FormField from '../ui/FormField';
import Button from '../ui/Button';
import Alert from '../ui/Alert';
import ConfirmModal from '../ui/ConfirmModal';
import { showToast } from '../ui/Toast';

// Simplified ProviderForm component focused only on core provider information
function ProviderForm({ provider, onClose, onTokenExpired, currentUser, onDirtyChange }) {
  const isEditing = provider != null;
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const [confirmDiscardChanges, setConfirmDiscardChanges] = React.useState(false);

  // Define validation schema
  const validationSchema = {
    datacenter: [
      validationRules.required('Datacenter is required'),
      validationRules.maxLength(100, 'Datacenter name must be less than 100 characters')
    ],
    shortName: [
      validationRules.required('Short Name is required'),
      validationRules.minLength(2, 'Short Name must be at least 2 characters'),
      validationRules.maxLength(50, 'Short Name must be less than 50 characters')
    ],
    name: [
      validationRules.required('Full Name is required'),
      validationRules.minLength(3, 'Full Name must be at least 3 characters'),
      validationRules.maxLength(200, 'Full Name must be less than 200 characters')
    ],
    url: [
      validationRules.conditional(
        (values) => values.url && values.url.trim() !== '',
        validationRules.url('Please enter a valid URL (e.g., https://example.com)')
      )
    ],
    biocaseUrl: [
      validationRules.conditional(
        (values) => values.biocaseUrl && values.biocaseUrl.trim() !== '',
        validationRules.url('Please enter a valid BioCASe URL')
      )
    ]
  };

  // Form submission handler
  const handleFormSubmit = async (values) => {
    setIsLoading(true);
    setError('');

    try {
      // Clone the form values to avoid mutating
      const sanitizedFormData = { ...values };

      // Remove any empty strings for optional URL fields
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

      const updatedProvider = await readJson(res);
      setIsLoading(false);
      showToast(
        isEditing
          ? `Provider "${updatedProvider.name}" updated successfully!`
          : `Provider "${updatedProvider.name}" created successfully!`,
        'success'
      );
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

  // Initialize form validation hook
  const form = useFormValidation(
    {
      name: provider ? provider.name : '',
      shortName: provider ? provider.shortName : '',
      datacenter: provider ? provider.datacenter : '',
      url: provider ? provider.url : '',
      biocaseUrl: provider ? provider.biocaseUrl : '',
      isDataCenter: provider ? provider.isDataCenter : false,
    },
    validationSchema,
    handleFormSubmit
  );

  // Notify parent of dirty state changes
  React.useEffect(() => {
    if (onDirtyChange) {
      onDirtyChange(form.isDirty);
    }
  }, [form.isDirty, onDirtyChange]);

  return (
    <div>
      {error && <Alert type="error">{error}</Alert>}

      <form onSubmit={form.handleSubmit} noValidate>
        <FormField
          type="text"
          name="datacenter"
          label="Datacenter"
          value={form.values.datacenter}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.datacenter}
          touched={form.touched.datacenter}
          placeholder="Enter datacenter name"
          required
        />

        <FormField
          type="text"
          name="shortName"
          label="Short Name"
          value={form.values.shortName}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.shortName}
          touched={form.touched.shortName}
          placeholder="Enter short name"
          helpText="A brief identifier for this provider"
          required
        />

        <FormField
          type="text"
          name="name"
          label="Full Name"
          value={form.values.name}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.name}
          touched={form.touched.name}
          placeholder="Enter full provider name"
          required
        />

        <FormField
          type="url"
          name="url"
          label="URL"
          value={form.values.url}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.url}
          touched={form.touched.url}
          placeholder="https://example.com"
          helpText="Optional: The provider's website URL"
        />

        <FormField
          type="url"
          name="biocaseUrl"
          label="BioCASe URL"
          value={form.values.biocaseUrl}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.biocaseUrl}
          touched={form.touched.biocaseUrl}
          placeholder="https://biocase.example.com"
          helpText="Optional: The provider's BioCASe service URL"
        />

        {/* Data Center Checkbox - only visible to global admins */}
        {currentUser?.is_global_admin && (
          <FormField
            type="checkbox"
            name="isDataCenter"
            label="Is Data Center"
            checked={form.values.isDataCenter}
            onChange={form.handleChange}
            onBlur={form.handleBlur}
            error={form.errors.isDataCenter}
            touched={form.touched.isDataCenter}
            helpText="Designates this provider as an official data center (global admin only)"
          />
        )}

        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '0.75rem',
          marginTop: '1.5rem',
        }}>
          <Button
            variant="secondary"
            onClick={() => {
              if (form.isDirty) {
                setConfirmDiscardChanges(true);
              } else {
                onClose(null);
              }
            }}
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

      {confirmDiscardChanges && (
        <ConfirmModal
          isOpen={true}
          title="Discard changes?"
          message="You have unsaved changes. Are you sure you want to close this form?"
          confirmText="Discard"
          cancelText="Keep Editing"
          onConfirm={() => {
            setConfirmDiscardChanges(false);
            onClose(null);
          }}
          onCancel={() => setConfirmDiscardChanges(false)}
        />
      )}
    </div>
  );
}

export default ProviderForm;
