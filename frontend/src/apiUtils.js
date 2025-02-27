// API utility functions for handling requests and token expiration

// In production with Nginx, we use /api as the base URL
// In development, we use the full URL from environment or default to localhost:8000
export const API_BASE = process.env.NODE_ENV === 'production' 
  ? '/api' 
  : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

/**
 * Custom fetch function that handles token expiration
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @param {Function} onTokenExpired - Callback function to execute when token expires
 * @returns {Promise} - Fetch promise
 */
export const fetchWithTokenExpiration = async (url, options = {}, onTokenExpired) => {
  try {
    const response = await fetch(url, options);
    
    // Only trigger token expiration for 401 responses from authenticated endpoints
    // Exclude POST /token endpoint which naturally returns 401 for invalid credentials
    if (response.status === 401 && !url.endsWith('/token')) {
      // Call the token expired callback
      if (onTokenExpired && typeof onTokenExpired === 'function') {
        onTokenExpired();
      }
    }
    
    return response;
  } catch (error) {
    throw error;
  }
};

/**
 * Makes an authenticated API request
 * @param {string} endpoint - API endpoint (without base URL)
 * @param {Object} options - Fetch options
 * @param {Function} onTokenExpired - Callback function to execute when token expires
 * @returns {Promise} - Fetch promise
 */
export const apiRequest = async (endpoint, options = {}, onTokenExpired) => {
  const token = localStorage.getItem('token');
  
  if (!token) {
    throw new Error('No authentication token found');
  }
  
  // Create a new headers object that merges the existing headers with our Authorization header
  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`
  };
  
  // Create a new options object with the merged headers
  const mergedOptions = {
    ...options,
    headers
  };
  
  return fetchWithTokenExpiration(
    `${API_BASE}${endpoint}`, 
    mergedOptions, 
    onTokenExpired
  );
};

export default {
  API_BASE,
  fetchWithTokenExpiration,
  apiRequest
};
