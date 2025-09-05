import React from 'react';
import { AlertCircle, Check, Eye, EyeOff } from 'lucide-react';

/**
 * Reusable form field component with consistent styling and error handling
 * Supports various input types and provides visual feedback for validation states
 */
const FormField = ({
  type = 'text',
  name,
  label,
  value,
  onChange,
  onBlur,
  error,
  touched,
  required,
  disabled,
  placeholder,
  helpText,
  autoComplete,
  className,
  style,
  rows,
  options, // For select fields
  multiple, // For select fields
  checked, // For checkbox fields
  min, // For number fields
  max, // For number fields
  step, // For number fields
  accept, // For file fields
  showPasswordToggle = true, // For password fields
  ...props
}) => {
  const [showPassword, setShowPassword] = React.useState(false);
  
  // Determine if field has an error and should show it
  const showError = touched && error;
  const fieldId = `field-${name}`;
  const errorId = `${fieldId}-error`;
  const helpId = `${fieldId}-help`;
  
  // Get field border color based on state
  const getBorderColor = () => {
    if (showError) return 'var(--error)';
    if (touched && !error) return 'var(--success)';
    return 'var(--border)';
  };
  
  // Common input styles
  const inputStyles = {
    display: 'block',
    width: '100%',
    padding: type === 'checkbox' ? '0' : '0.625rem 0.75rem',
    fontSize: '0.875rem',
    borderRadius: '0.5rem',
    border: `1px solid ${getBorderColor()}`,
    backgroundColor: disabled ? 'var(--subtle-bg)' : 'var(--card-bg)',
    color: 'var(--text)',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    outline: 'none',
    ...style
  };
  
  // Add focus styles
  const focusStyles = {
    ':focus': {
      borderColor: 'var(--primary)',
      boxShadow: '0 0 0 3px rgba(var(--primary-rgb), 0.1)'
    }
  };
  
  // Render the appropriate input element
  const renderInput = () => {
    // Checkbox input
    if (type === 'checkbox') {
      return (
        <label style={{ 
          display: 'flex', 
          alignItems: 'center',
          fontSize: '0.875rem', 
          fontWeight: 500, 
          color: 'var(--text)',
          cursor: disabled ? 'not-allowed' : 'pointer'
        }}>
          <input
            type="checkbox"
            id={fieldId}
            name={name}
            checked={checked || value || false}
            onChange={onChange}
            onBlur={onBlur}
            disabled={disabled}
            aria-invalid={showError}
            aria-describedby={`${error ? errorId : ''} ${helpText ? helpId : ''}`}
            style={{
              width: '1rem',
              height: '1rem',
              borderRadius: '0.25rem',
              marginRight: '0.5rem',
              accentColor: 'var(--primary)',
              cursor: disabled ? 'not-allowed' : 'pointer'
            }}
            {...props}
          />
          {label}
          {required && <span style={{ color: 'var(--error)', marginLeft: '0.25rem' }}>*</span>}
        </label>
      );
    }
    
    // Select input
    if (type === 'select') {
      return (
        <>
          {label && (
            <label 
              htmlFor={fieldId}
              style={{ 
                display: 'block', 
                fontSize: '0.875rem', 
                fontWeight: 500, 
                marginBottom: '0.5rem', 
                color: 'var(--text)',
              }}
            >
              {label}
              {required && <span style={{ color: 'var(--error)', marginLeft: '0.25rem' }}>*</span>}
            </label>
          )}
          <select
            id={fieldId}
            name={name}
            value={value}
            onChange={onChange}
            onBlur={onBlur}
            disabled={disabled}
            multiple={multiple}
            aria-invalid={showError}
            aria-describedby={`${error ? errorId : ''} ${helpText ? helpId : ''}`}
            style={inputStyles}
            {...props}
          >
            {!multiple && <option value="">Select an option</option>}
            {options?.map(option => (
              <option 
                key={option.value} 
                value={option.value}
              >
                {option.label}
              </option>
            ))}
          </select>
        </>
      );
    }
    
    // Textarea input
    if (type === 'textarea') {
      return (
        <>
          {label && (
            <label 
              htmlFor={fieldId}
              style={{ 
                display: 'block', 
                fontSize: '0.875rem', 
                fontWeight: 500, 
                marginBottom: '0.5rem', 
                color: 'var(--text)',
              }}
            >
              {label}
              {required && <span style={{ color: 'var(--error)', marginLeft: '0.25rem' }}>*</span>}
            </label>
          )}
          <textarea
            id={fieldId}
            name={name}
            value={value || ''}
            onChange={onChange}
            onBlur={onBlur}
            disabled={disabled}
            placeholder={placeholder}
            rows={rows || 3}
            aria-invalid={showError}
            aria-describedby={`${error ? errorId : ''} ${helpText ? helpId : ''}`}
            style={{
              ...inputStyles,
              resize: 'vertical',
              minHeight: '80px'
            }}
            {...props}
          />
        </>
      );
    }
    
    // Password input with show/hide toggle
    if (type === 'password' && showPasswordToggle) {
      return (
        <>
          {label && (
            <label 
              htmlFor={fieldId}
              style={{ 
                display: 'block', 
                fontSize: '0.875rem', 
                fontWeight: 500, 
                marginBottom: '0.5rem', 
                color: 'var(--text)',
              }}
            >
              {label}
              {required && <span style={{ color: 'var(--error)', marginLeft: '0.25rem' }}>*</span>}
            </label>
          )}
          <div style={{ position: 'relative' }}>
            <input
              type={showPassword ? 'text' : 'password'}
              id={fieldId}
              name={name}
              value={value || ''}
              onChange={onChange}
              onBlur={onBlur}
              disabled={disabled}
              placeholder={placeholder}
              autoComplete={autoComplete}
              aria-invalid={showError}
              aria-describedby={`${error ? errorId : ''} ${helpText ? helpId : ''}`}
              style={{
                ...inputStyles,
                paddingRight: '2.5rem'
              }}
              {...props}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              style={{
                position: 'absolute',
                right: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-light)',
                cursor: 'pointer',
                padding: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </>
      );
    }
    
    // All other input types
    return (
      <>
        {label && (
          <label 
            htmlFor={fieldId}
            style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }}
          >
            {label}
            {required && <span style={{ color: 'var(--error)', marginLeft: '0.25rem' }}>*</span>}
          </label>
        )}
        <div style={{ position: 'relative' }}>
          <input
            type={type}
            id={fieldId}
            name={name}
            value={value || ''}
            onChange={onChange}
            onBlur={onBlur}
            disabled={disabled}
            placeholder={placeholder}
            autoComplete={autoComplete}
            required={required}
            min={min}
            max={max}
            step={step}
            accept={accept}
            aria-invalid={showError}
            aria-describedby={`${error ? errorId : ''} ${helpText ? helpId : ''}`}
            style={{
              ...inputStyles,
              paddingRight: showError || (touched && !error) ? '2.5rem' : inputStyles.padding
            }}
            {...props}
          />
          {/* Validation status icon */}
          {touched && (
            <div style={{
              position: 'absolute',
              right: '0.75rem',
              top: '50%',
              transform: 'translateY(-50%)',
              pointerEvents: 'none'
            }}>
              {error ? (
                <AlertCircle size={18} color="var(--error)" />
              ) : (
                <Check size={18} color="var(--success)" />
              )}
            </div>
          )}
        </div>
      </>
    );
  };
  
  return (
    <div className={className} style={{ marginBottom: '1rem' }}>
      {renderInput()}
      
      {/* Help text */}
      {helpText && !showError && (
        <div 
          id={helpId}
          style={{
            fontSize: '0.75rem',
            color: 'var(--text-light)',
            marginTop: '0.25rem',
            marginLeft: type === 'checkbox' ? '1.5rem' : '0'
          }}
        >
          {helpText}
        </div>
      )}
      
      {/* Error message */}
      {showError && (
        <div 
          id={errorId}
          role="alert"
          style={{
            fontSize: '0.75rem',
            color: 'var(--error)',
            marginTop: '0.25rem',
            marginLeft: type === 'checkbox' ? '1.5rem' : '0',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
};

export default FormField;