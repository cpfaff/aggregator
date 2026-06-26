import { useState, useCallback, useEffect } from 'react';

/**
 * Custom hook for form validation and state management
 * Provides consistent validation behavior across all forms
 *
 * @param {Object} initialValues - Initial form values
 * @param {Object} validationSchema - Validation rules for each field
 * @param {Function} onSubmit - Callback function when form is valid and submitted
 */
const useFormValidation = (initialValues = {}, validationSchema = {}, onSubmit) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // Deep comparison helper for objects
  const isEqual = (a, b) => {
    if (a === b) return true;
    if (typeof a !== typeof b) return false;
    if (typeof a === 'object' && a !== null && b !== null) {
      return JSON.stringify(a) === JSON.stringify(b);
    }
    return false;
  };

  // Track if form has been modified (with deep comparison for objects)
  useEffect(() => {
    const hasChanges = Object.keys(values).some(
      key => !isEqual(values[key], initialValues[key])
    );
    setIsDirty(hasChanges);
  }, [values, initialValues]);

  // Validate a single field
  const validateField = useCallback(async (name, value) => {
    const fieldValidators = validationSchema[name];
    if (!fieldValidators) return null;

    const validators = Array.isArray(fieldValidators) ? fieldValidators : [fieldValidators];

    for (const validator of validators) {
      let error = null;

      if (typeof validator === 'function') {
        // Handle both sync and async validators
        error = await Promise.resolve(validator(value, values));
      }

      if (error) {
        return error;
      }
    }

    return null;
  }, [validationSchema, values]);

  // Validate all fields
  const validateForm = useCallback(async () => {
    const newErrors = {};
    let isValid = true;

    for (const fieldName of Object.keys(validationSchema)) {
      const error = await validateField(fieldName, values[fieldName]);
      if (error) {
        newErrors[fieldName] = error;
        isValid = false;
      }
    }

    setErrors(newErrors);
    return isValid;
  }, [validationSchema, values, validateField]);

  // Handle field value change
  const handleChange = useCallback(async (e) => {
    const { name, value, type, checked } = e.target;
    const fieldValue = type === 'checkbox' ? checked : value;

    setValues(prev => ({
      ...prev,
      [name]: fieldValue
    }));

    // Re-validate on change if field has been touched (for real-time feedback)
    if (touched[name]) {
      const error = await validateField(name, fieldValue);
      setErrors(prev => ({
        ...prev,
        [name]: error
      }));
    }
  }, [touched, validateField]);

  // Handle field blur - validate on blur
  const handleBlur = useCallback(async (e) => {
    const { name } = e.target;

    setTouched(prev => ({
      ...prev,
      [name]: true
    }));

    // Validate field on blur
    const error = await validateField(name, values[name]);
    if (error) {
      setErrors(prev => ({
        ...prev,
        [name]: error
      }));
    }
  }, [values, validateField]);

  // Set field value programmatically
  const setFieldValue = useCallback((name, value) => {
    setValues(prev => ({
      ...prev,
      [name]: value
    }));

    // Clear error when value is set
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  }, [errors]);

  // Set field error programmatically
  const setFieldError = useCallback((name, error) => {
    setErrors(prev => ({
      ...prev,
      [name]: error
    }));
  }, []);

  // Set multiple field errors
  const setFieldErrors = useCallback((newErrors) => {
    setErrors(newErrors);
  }, []);

  // Handle form submission
  const handleSubmit = useCallback(async (e) => {
    if (e && e.preventDefault) {
      e.preventDefault();
    }

    setIsSubmitting(true);

    // Touch all fields to show errors
    const allTouched = {};
    Object.keys(validationSchema).forEach(key => {
      allTouched[key] = true;
    });
    setTouched(allTouched);

    // Validate form
    const isValid = await validateForm();

    if (isValid && onSubmit) {
      try {
        await onSubmit(values);
        // Reset form on successful submission
        resetForm();
      } catch (error) {
        // Allow parent component to handle submission errors
        console.error('Form submission error:', error);
        throw error;
      } finally {
        setIsSubmitting(false);
      }
    } else {
      setIsSubmitting(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values, validateForm, validationSchema, onSubmit]);

  // Reset form to initial state
  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
    setIsDirty(false);
  }, [initialValues]);

  // Reset specific field
  const resetField = useCallback((name) => {
    setValues(prev => ({
      ...prev,
      [name]: initialValues[name]
    }));
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[name];
      return newErrors;
    });
    setTouched(prev => {
      const newTouched = { ...prev };
      delete newTouched[name];
      return newTouched;
    });
  }, [initialValues]);

  // Check if field has error and has been touched
  const getFieldError = useCallback((name) => {
    return touched[name] ? errors[name] : null;
  }, [errors, touched]);

  // Check if form is valid
  const isValid = Object.keys(errors).length === 0;

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isDirty,
    isValid,
    handleChange,
    handleBlur,
    handleSubmit,
    setFieldValue,
    setFieldError,
    setFieldErrors,
    validateField,
    validateForm,
    resetForm,
    resetField,
    getFieldError
  };
};

export default useFormValidation;
