/**
 * Reusable validation rules for form fields
 * Each validator returns an error message string if validation fails, null if valid
 */

// Basic validators
const required = (message = 'This field is required') => (value) => {
  if (value === null || value === undefined || value === '') {
    return message;
  }
  if (typeof value === 'string' && !value.trim()) {
    return message;
  }
  if (Array.isArray(value) && value.length === 0) {
    return message;
  }
  return null;
};

const email = (message = 'Please enter a valid email address') => (value) => {
  if (!value) return null; // Let required validator handle empty values

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(value) ? null : message;
};

const url = (message = 'Please enter a valid URL') => (value) => {
  if (!value) return null; // Let required validator handle empty values

  try {
    new URL(value);
    return null;
  } catch {
    // Try with protocol if missing
    try {
      new URL(`https://${value}`);
      return 'Please include http:// or https:// in the URL';
    } catch {
      return message;
    }
  }
};

const minLength = (min, message) => (value) => {
  if (!value) return null; // Let required validator handle empty values

  const defaultMessage = `Must be at least ${min} characters`;
  if (value.length < min) {
    return message || defaultMessage;
  }
  return null;
};

const maxLength = (max, message) => (value) => {
  if (!value) return null;

  const defaultMessage = `Must be no more than ${max} characters`;
  if (value.length > max) {
    return message || defaultMessage;
  }
  return null;
};

const pattern = (regex, message = 'Invalid format') => (value) => {
  if (!value) return null;

  const regexPattern = typeof regex === 'string' ? new RegExp(regex) : regex;
  return regexPattern.test(value) ? null : message;
};

const matches = (fieldName, message) => (value, allValues) => {
  const defaultMessage = `Must match ${fieldName}`;
  if (value !== allValues[fieldName]) {
    return message || defaultMessage;
  }
  return null;
};

const minValue = (min, message) => (value) => {
  if (value === null || value === undefined || value === '') return null;

  const defaultMessage = `Must be at least ${min}`;
  const numValue = Number(value);
  if (isNaN(numValue) || numValue < min) {
    return message || defaultMessage;
  }
  return null;
};

const maxValue = (max, message) => (value) => {
  if (value === null || value === undefined || value === '') return null;

  const defaultMessage = `Must be no more than ${max}`;
  const numValue = Number(value);
  if (isNaN(numValue) || numValue > max) {
    return message || defaultMessage;
  }
  return null;
};

// Password strength validator
const passwordStrength = (requirements = {}) => (value) => {
  if (!value) return null;

  const {
    minLength: min = 8,
    requireUppercase = true,
    requireLowercase = true,
    requireNumbers = true,
    requireSpecialChars = false
  } = requirements;

  const errors = [];

  if (value.length < min) {
    errors.push(`at least ${min} characters`);
  }

  if (requireUppercase && !/[A-Z]/.test(value)) {
    errors.push('one uppercase letter');
  }

  if (requireLowercase && !/[a-z]/.test(value)) {
    errors.push('one lowercase letter');
  }

  if (requireNumbers && !/\d/.test(value)) {
    errors.push('one number');
  }

  if (requireSpecialChars && !/[!@#$%^&*(),.?":{}|<>]/.test(value)) {
    errors.push('one special character');
  }

  if (errors.length > 0) {
    return `Password must contain ${errors.join(', ')}`;
  }

  return null;
};

// Username validator
const username = (message = 'Username must be 3-20 characters and contain only letters, numbers, and underscores') => (value) => {
  if (!value) return null;

  const usernameRegex = /^[a-zA-Z0-9_]{3,20}$/;
  return usernameRegex.test(value) ? null : message;
};

// Phone number validator (basic international format)
const phoneNumber = (message = 'Please enter a valid phone number') => (value) => {
  if (!value) return null;

  // Remove all non-digit characters for validation
  const digits = value.replace(/\D/g, '');

  // Check if it's a valid phone number length (7-15 digits internationally)
  if (digits.length < 7 || digits.length > 15) {
    return message;
  }

  return null;
};

// Array validators
const arrayMinLength = (min, message) => (value) => {
  if (!Array.isArray(value)) return null;

  const defaultMessage = `Must have at least ${min} item${min !== 1 ? 's' : ''}`;
  if (value.length < min) {
    return message || defaultMessage;
  }
  return null;
};

const arrayMaxLength = (max, message) => (value) => {
  if (!Array.isArray(value)) return null;

  const defaultMessage = `Must have no more than ${max} item${max !== 1 ? 's' : ''}`;
  if (value.length > max) {
    return message || defaultMessage;
  }
  return null;
};

// Custom async validator example (for checking uniqueness)
const unique = (checkFunction, message = 'This value is already taken') => async (value) => {
  if (!value) return null;

  try {
    const isUnique = await checkFunction(value);
    return isUnique ? null : message;
  } catch {
    return 'Unable to validate uniqueness';
  }
};

// Composite validator - combines multiple validators
const compose = (...validators) => async (value, allValues) => {
  for (const validator of validators) {
    const error = await validator(value, allValues);
    if (error) return error;
  }
  return null;
};

// Conditional validator - applies validation based on a condition
const conditional = (condition, validator) => (value, allValues) => {
  const shouldValidate = typeof condition === 'function' ? condition(allValues) : condition;

  if (shouldValidate) {
    return validator(value, allValues);
  }

  return null;
};

// Export all validators
const validationRules = {
  required,
  email,
  url,
  minLength,
  maxLength,
  pattern,
  matches,
  minValue,
  maxValue,
  passwordStrength,
  username,
  phoneNumber,
  arrayMinLength,
  arrayMaxLength,
  unique,
  compose,
  conditional
};

export default validationRules;

// Export individual validators for direct import
export {
  required,
  email,
  url,
  minLength,
  maxLength,
  pattern,
  matches,
  minValue,
  maxValue,
  passwordStrength,
  username,
  phoneNumber,
  arrayMinLength,
  arrayMaxLength,
  unique,
  compose,
  conditional
};
