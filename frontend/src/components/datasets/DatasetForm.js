import React, { useState, useEffect, useMemo } from 'react';
import { Trash2 } from 'lucide-react';
import { apiRequest } from '../../utils/apiUtils';
import useFormValidation from '../../utils/useFormValidation';
import validationRules from '../../utils/validationRules';
import { getArrayFieldName, flattenArrayForValidation } from '../../utils/arrayValidation';
import FormField from '../ui/FormField';
import Alert from '../ui/Alert';
import Button from '../ui/Button';
import ConfirmModal from '../ui/ConfirmModal';
import { showToast } from '../ui/Toast';

function DatasetForm({ providerId, dataset, onClose, onTokenExpired, onDirtyChange }) {
  const isEditing = dataset != null;
  const [confirmAction, setConfirmAction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [confirmDiscardChanges, setConfirmDiscardChanges] = useState(false);

  // Create validation schema that handles both static and dynamic fields
  const createValidationSchema = (xmlArchives, usefulLinks) => {
    const schema = {
      source: [
        validationRules.required('Source is required'),
        validationRules.maxLength(200, 'Source must be less than 200 characters')
      ],
      title: [
        validationRules.required('Title is required'),
        validationRules.maxLength(300, 'Title must be less than 300 characters')
      ],
      landingPageUrl: [
        validationRules.conditional(
          (values) => values.landingPageUrl && values.landingPageUrl.trim() !== '',
          validationRules.url('Please enter a valid URL')
        )
      ]
    };

    // Add validation for each XML archive
    xmlArchives.forEach((_, index) => {
      schema[getArrayFieldName('xmlArchives', index, 'url')] = [
        validationRules.required('URL is required'),
        validationRules.url('Please enter a valid URL')
      ];
    });

    // Add validation for each useful link
    usefulLinks.forEach((_, index) => {
      schema[getArrayFieldName('usefulLinks', index, 'title')] = [
        validationRules.required('Title is required'),
        validationRules.maxLength(200, 'Title must be less than 200 characters')
      ];
      schema[getArrayFieldName('usefulLinks', index, 'url')] = [
        validationRules.required('URL is required'),
        validationRules.url('Please enter a valid URL')
      ];
    });

    return schema;
  };

  // Form submission handler
  const handleFormSubmit = async (values) => {
    setIsLoading(true);
    setError('');

    try {
      // Reconstruct arrays from flattened values
      const xmlArchives = form.values.xmlArchives || [];
      const usefulLinks = form.values.usefulLinks || [];

      // Filter out any empty items
      const filteredXmlArchives = xmlArchives.filter(archive =>
        archive.url && archive.url.trim() !== ''
      );

      const filteredUsefulLinks = usefulLinks.filter(link =>
        link.title && link.title.trim() !== '' &&
        link.url && link.url.trim() !== ''
      );

      // Create sanitized form data object
      const sanitizedFormData = {
        source: values.source,
        title: values.title,
        landingPageUrl: values.landingPageUrl && values.landingPageUrl.trim() !== ''
          ? values.landingPageUrl
          : null,
        isHarvestReady: values.isHarvestReady
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
      showToast(
        isEditing
          ? `Dataset "${normalizedDataset.title}" updated successfully!`
          : `Dataset "${normalizedDataset.title}" created successfully!`,
        'success'
      );
      onClose(normalizedDataset);
    } catch (err) {
      // Only set error if it's not a token expiration error
      if (!err.message || !err.message.includes('Session expired')) {
        setError('Error saving dataset: ' + err.message);
      }
      setIsLoading(false);
    }
  };

  // Initialize form with initial values
  const initialValues = {
    source: dataset?.source || '',
    title: dataset?.title || '',
    landingPageUrl: dataset?.landingPageUrl || '',
    isHarvestReady: dataset?.isHarvestReady ?? false,
    xmlArchives: dataset?.xmlArchives || [],
    usefulLinks: dataset?.usefulLinks || []
  };

  // Flatten initial array values
  const flattenedInitialValues = {
    ...initialValues,
    ...flattenArrayForValidation('xmlArchives', initialValues.xmlArchives),
    ...flattenArrayForValidation('usefulLinks', initialValues.usefulLinks)
  };

  // Initialize form validation hook
  const form = useFormValidation(
    flattenedInitialValues,
    createValidationSchema(initialValues.xmlArchives, initialValues.usefulLinks),
    handleFormSubmit
  );

  // Notify parent of dirty state changes
  useEffect(() => {
    if (onDirtyChange) {
      onDirtyChange(form.isDirty);
    }
  }, [form.isDirty, onDirtyChange]);

  // XML Archive operations
  const addXmlArchive = () => {
    const newArchives = [...(form.values.xmlArchives || []), { id: null, url: '', isLatest: false }];
    form.setFieldValue('xmlArchives', newArchives);

    // Update validation schema with the new array
    const newSchema = createValidationSchema(newArchives, form.values.usefulLinks || []);
    // Note: We'd need to enhance useFormValidation to support dynamic schema updates
    // For now, we'll handle validation manually for new fields
  };

  const updateXmlArchive = (index, field, value) => {
    const updatedArchives = [...(form.values.xmlArchives || [])];

    // If marking this item as latest, uncheck all other XML archives
    if (field === 'isLatest' && value === true) {
      updatedArchives.forEach((archive, idx) => {
        if (idx !== index) {
          updatedArchives[idx] = { ...archive, isLatest: false };
        }
      });
    }

    updatedArchives[index] = { ...updatedArchives[index], [field]: value };
    form.setFieldValue('xmlArchives', updatedArchives);

    // Also update the flattened field for validation
    const fieldName = getArrayFieldName('xmlArchives', index, field);
    form.setFieldValue(fieldName, value);

    // Manually validate the field immediately
    if (field === 'url') {
      const validators = [
        validationRules.required('URL is required'),
        validationRules.url('Please enter a valid URL')
      ];

      let error = null;
      for (const validator of validators) {
        error = validator(value);
        if (error) break;
      }

      if (error) {
        form.setFieldError(fieldName, error);
      } else {
        form.setFieldError(fieldName, null);
      }
    }
  };

  const removeXmlArchive = (index) => {
    const archive = form.values.xmlArchives[index];
    const displayUrl = archive.url || `Archive ${index + 1}`;

    setConfirmAction({
      message: `Are you sure you want to remove XML Archive "${displayUrl}"? This action cannot be undone.`,
      onConfirm: () => {
        const newArchives = form.values.xmlArchives.filter((_, idx) => idx !== index);
        form.setFieldValue('xmlArchives', newArchives);
        setConfirmAction(null);
      },
      onCancel: () => setConfirmAction(null),
    });
  };

  // Useful Links operations
  const addUsefulLink = () => {
    const newLinks = [...(form.values.usefulLinks || []), { id: null, title: '', url: '', isLatest: false }];
    form.setFieldValue('usefulLinks', newLinks);
  };

  const updateUsefulLink = (index, field, value) => {
    const updatedLinks = [...(form.values.usefulLinks || [])];

    // If marking this item as latest, uncheck all other useful links
    if (field === 'isLatest' && value === true) {
      updatedLinks.forEach((link, idx) => {
        if (idx !== index) {
          updatedLinks[idx] = { ...link, isLatest: false };
        }
      });
    }

    updatedLinks[index] = { ...updatedLinks[index], [field]: value };
    form.setFieldValue('usefulLinks', updatedLinks);

    // Also update the flattened field for validation
    const fieldName = getArrayFieldName('usefulLinks', index, field);
    form.setFieldValue(fieldName, value);

    // Manually validate the field immediately
    if (field === 'url') {
      const validators = [
        validationRules.required('URL is required'),
        validationRules.url('Please enter a valid URL')
      ];

      let error = null;
      for (const validator of validators) {
        error = validator(value);
        if (error) break;
      }

      if (error) {
        form.setFieldError(fieldName, error);
      } else {
        form.setFieldError(fieldName, null);
      }
    } else if (field === 'title') {
      const validators = [
        validationRules.required('Title is required'),
        validationRules.maxLength(200, 'Title must be less than 200 characters')
      ];

      let error = null;
      for (const validator of validators) {
        error = validator(value);
        if (error) break;
      }

      if (error) {
        form.setFieldError(fieldName, error);
      } else {
        form.setFieldError(fieldName, null);
      }
    }
  };

  const removeUsefulLink = (index) => {
    const link = form.values.usefulLinks[index];
    const displayName = link.title || `Link ${index + 1}`;

    setConfirmAction({
      message: `Are you sure you want to remove Useful Link "${displayName}"? This action cannot be undone.`,
      onConfirm: () => {
        const newLinks = form.values.usefulLinks.filter((_, idx) => idx !== index);
        form.setFieldValue('usefulLinks', newLinks);
        setConfirmAction(null);
      },
      onCancel: () => setConfirmAction(null),
    });
  };

  return (
    <div>
      {error && <Alert type="error">{error}</Alert>}

      <form onSubmit={form.handleSubmit} noValidate>
        <FormField
          type="text"
          name="source"
          label="Source"
          value={form.values.source}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.source}
          touched={form.touched.source}
          placeholder="Enter dataset source"
          required
        />

        <FormField
          type="text"
          name="title"
          label="Title"
          value={form.values.title}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.title}
          touched={form.touched.title}
          placeholder="Enter dataset title"
          required
        />

        <FormField
          type="url"
          name="landingPageUrl"
          label="Landing Page URL"
          value={form.values.landingPageUrl}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.landingPageUrl}
          touched={form.touched.landingPageUrl}
          placeholder="https://example.com/dataset"
          helpText="Optional: The dataset's landing page URL"
        />

        {/* Harvest Ready Checkbox - available to any provider editor (not admin-gated) */}
        <FormField
          type="checkbox"
          name="isHarvestReady"
          label="Harvest ready"
          checked={form.values.isHarvestReady}
          onChange={form.handleChange}
          onBlur={form.handleBlur}
          error={form.errors.isHarvestReady}
          touched={form.touched.isHarvestReady}
          helpText="When checked, this dataset is published to the public harvester feed and search index. Leave unchecked to keep it staged: visible and editable here, but not yet searchable."
        />

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

          {(!form.values.xmlArchives || form.values.xmlArchives.length === 0) ? (
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
            form.values.xmlArchives.map((archive, archIndex) => {
              const urlFieldName = getArrayFieldName('xmlArchives', archIndex, 'url');
              return (
                <div
                  key={archIndex}
                  style={{
                    padding: '1rem',
                    backgroundColor: 'var(--subtle-bg)',
                    borderRadius: '0.5rem',
                    marginBottom: '0.75rem',
                  }}
                >
                  <FormField
                    type="url"
                    name={urlFieldName}
                    label="URL"
                    value={archive.url || ''}
                    onChange={(e) => updateXmlArchive(archIndex, 'url', e.target.value)}
                    onBlur={(e) => {
                      // Create a synthetic event for the form's handleBlur
                      const syntheticEvent = {
                        target: {
                          name: urlFieldName,
                          value: e.target.value
                        }
                      };
                      form.handleBlur(syntheticEvent);
                    }}
                    error={form.errors[urlFieldName]}
                    touched={form.touched[urlFieldName]}
                    placeholder="https://example.com/archive.xml"
                    required
                  />

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
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
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
              );
            })
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

          {(!form.values.usefulLinks || form.values.usefulLinks.length === 0) ? (
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
            form.values.usefulLinks.map((link, linkIndex) => {
              const titleFieldName = getArrayFieldName('usefulLinks', linkIndex, 'title');
              const urlFieldName = getArrayFieldName('usefulLinks', linkIndex, 'url');
              return (
                <div
                  key={linkIndex}
                  style={{
                    padding: '1rem',
                    backgroundColor: 'var(--subtle-bg)',
                    borderRadius: '0.5rem',
                    marginBottom: '0.75rem',
                  }}
                >
                  <FormField
                    type="text"
                    name={titleFieldName}
                    label="Title"
                    value={link.title || ''}
                    onChange={(e) => updateUsefulLink(linkIndex, 'title', e.target.value)}
                    onBlur={(e) => {
                      // Create a synthetic event for the form's handleBlur
                      const syntheticEvent = {
                        target: {
                          name: titleFieldName,
                          value: e.target.value
                        }
                      };
                      form.handleBlur(syntheticEvent);
                    }}
                    error={form.errors[titleFieldName]}
                    touched={form.touched[titleFieldName]}
                    placeholder="Enter link title"
                    required
                  />

                  <FormField
                    type="url"
                    name={urlFieldName}
                    label="URL"
                    value={link.url || ''}
                    onChange={(e) => updateUsefulLink(linkIndex, 'url', e.target.value)}
                    onBlur={(e) => {
                      // Create a synthetic event for the form's handleBlur
                      const syntheticEvent = {
                        target: {
                          name: urlFieldName,
                          value: e.target.value
                        }
                      };
                      form.handleBlur(syntheticEvent);
                    }}
                    error={form.errors[urlFieldName]}
                    touched={form.touched[urlFieldName]}
                    placeholder="https://example.com/resource"
                    required
                  />

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
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
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
              );
            })
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
            {isEditing ? (isLoading ? 'Updating...' : 'Update Dataset') : (isLoading ? 'Creating...' : 'Create Dataset')}
          </Button>
        </div>
      </form>

      {/* The confirmation modal for item removal */}
      {confirmAction && (
        <ConfirmModal
          isOpen={true}
          title="Confirm Removal"
          message={confirmAction.message}
          confirmText="Delete"
          cancelText="Cancel"
          confirmVariant="danger"
          onConfirm={confirmAction.onConfirm}
          onCancel={confirmAction.onCancel}
        />
      )}

      {/* Discard changes confirmation modal */}
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

export default DatasetForm;
