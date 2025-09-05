/**
 * Enhanced validation utilities for handling array fields in forms
 * Extends the base validation system to support dynamic array validation
 */

import validationRules from './validationRules';

/**
 * Creates validation schema for array fields
 * @param {Object} itemSchema - Schema for each item in the array
 * @param {Object} options - Additional options for array validation
 * @returns {Function} Validation function for the array
 */
export const arrayValidation = (itemSchema, options = {}) => {
  const { minItems, maxItems, validateEach = true } = options;
  
  return (arrayValue, allValues) => {
    const errors = {};
    
    if (!Array.isArray(arrayValue)) {
      return 'Must be an array';
    }
    
    // Check min/max constraints
    if (minItems && arrayValue.length < minItems) {
      return `Must have at least ${minItems} item${minItems !== 1 ? 's' : ''}`;
    }
    
    if (maxItems && arrayValue.length > maxItems) {
      return `Must have no more than ${maxItems} item${maxItems !== 1 ? 's' : ''}`;
    }
    
    // Validate each item if required
    if (validateEach && itemSchema) {
      arrayValue.forEach((item, index) => {
        Object.keys(itemSchema).forEach(field => {
          const validators = Array.isArray(itemSchema[field]) 
            ? itemSchema[field] 
            : [itemSchema[field]];
          
          for (const validator of validators) {
            if (typeof validator === 'function') {
              const error = validator(item[field], allValues);
              if (error) {
                errors[`${index}_${field}`] = error;
                break;
              }
            }
          }
        });
      });
    }
    
    return Object.keys(errors).length > 0 ? errors : null;
  };
};

/**
 * Creates validation schema for dynamic arrays
 * This returns a function that generates the appropriate validation schema
 * based on the current array state
 */
export const createDynamicArraySchema = (baseFieldName, itemSchema) => {
  return (formValues) => {
    const schema = {};
    const arrayValue = formValues[baseFieldName] || [];
    
    if (Array.isArray(arrayValue)) {
      arrayValue.forEach((item, index) => {
        Object.keys(itemSchema).forEach(field => {
          schema[`${baseFieldName}_${index}_${field}`] = itemSchema[field];
        });
      });
    }
    
    return schema;
  };
};

/**
 * Helper to get field name for array items
 */
export const getArrayFieldName = (arrayName, index, fieldName) => {
  return `${arrayName}_${index}_${fieldName}`;
};

/**
 * Helper to parse array field name
 */
export const parseArrayFieldName = (fieldName) => {
  const match = fieldName.match(/^(.+)_(\d+)_(.+)$/);
  if (match) {
    return {
      arrayName: match[1],
      index: parseInt(match[2]),
      field: match[3]
    };
  }
  return null;
};

/**
 * Flattens array values for form validation
 * Converts array of objects to flat key-value pairs
 */
export const flattenArrayForValidation = (arrayName, arrayValue) => {
  const flattened = {};
  
  if (Array.isArray(arrayValue)) {
    arrayValue.forEach((item, index) => {
      Object.keys(item).forEach(field => {
        const key = getArrayFieldName(arrayName, index, field);
        flattened[key] = item[field];
      });
    });
  }
  
  return flattened;
};

/**
 * Unflattens validation errors back to array structure
 */
export const unflattenArrayErrors = (errors, arrayName) => {
  const arrayErrors = [];
  
  Object.keys(errors).forEach(key => {
    const parsed = parseArrayFieldName(key);
    if (parsed && parsed.arrayName === arrayName) {
      if (!arrayErrors[parsed.index]) {
        arrayErrors[parsed.index] = {};
      }
      arrayErrors[parsed.index][parsed.field] = errors[key];
    }
  });
  
  return arrayErrors;
};

export default {
  arrayValidation,
  createDynamicArraySchema,
  getArrayFieldName,
  parseArrayFieldName,
  flattenArrayForValidation,
  unflattenArrayErrors
};