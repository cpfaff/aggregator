// API utility functions for handling requests and token expiration

// In production with Nginx, we use /api as the base URL
// In development, we use the full URL from environment or default to localhost:8000
export const API_BASE = process.env.NODE_ENV === 'production' 
  ? '' 
  : (process.env.REACT_APP_API_URL || 'http://localhost:8000');

// API version prefix
export const API_VERSION = '/api/v1';

/**
 * Get CSRF token from the backend
 * @returns {Promise<string>} - CSRF token
 */
export const getCsrfToken = async () => {
  try {
    // Check if we already have a token in memory
    let csrfToken = localStorage.getItem('csrfToken');
    
    // If no token exists or we're forcing a refresh, get a new one
    if (!csrfToken) {
      const response = await fetch(`${API_BASE}${API_VERSION}/csrf-token`, {
        credentials: 'include', // Important to include cookies
      });
      
      if (!response.ok) {
        throw new Error(`Failed to get CSRF token: ${response.status}`);
      }
      
      const data = await response.json();
      csrfToken = data.csrf_token;
      
      // Store token in localStorage for reuse
      localStorage.setItem('csrfToken', csrfToken);
    }
    
    return csrfToken;
  } catch (error) {
    console.error('Error getting CSRF token:', error);
    throw error;
  }
};

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
    // Exclude POST /auth-token endpoint which naturally returns 401 for invalid credentials
    if (response.status === 401 && !url.endsWith(`${API_VERSION}/auth-token`)) {
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
 * Makes an authenticated API request with CSRF protection
 * @param {string} endpoint - API endpoint (without base URL and version prefix)
 * @param {Object} options - Fetch options
 * @param {Function} onTokenExpired - Callback function to execute when token expires
 * @returns {Promise} - Fetch promise
 */
export const apiRequest = async (endpoint, options = {}, onTokenExpired) => {
  const token = localStorage.getItem('token');
  
  if (!token) {
    throw new Error('No authentication token found');
  }
  
  // Create headers object with Authorization token
  let headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`
  };
  
  // For state-changing methods (not GET or HEAD), add CSRF token
  const method = options.method || 'GET';
  if (!['GET', 'HEAD'].includes(method.toUpperCase())) {
    try {
      const csrfToken = await getCsrfToken();
      headers['X-CSRF-Token'] = csrfToken;
    } catch (error) {
      console.error('Failed to add CSRF token to request:', error);
      // Continue with the request even if CSRF token retrieval fails
    }
  }
  
  // Create a new options object with the merged headers
  const mergedOptions = {
    ...options,
    headers,
    credentials: 'include', // Important to include cookies for CSRF validation
  };
  
  return fetchWithTokenExpiration(
    `${API_BASE}${API_VERSION}${endpoint}`, 
    mergedOptions, 
    onTokenExpired
  );
};

/**
 * Initializes CSRF protection by fetching a token
 * Call this function when the app starts
 */
export const initCsrfProtection = async () => {
  try {
    await getCsrfToken();
    return true;
  } catch (error) {
    console.error('Failed to initialize CSRF protection:', error);
    return false;
  }
};

export default {
  API_BASE,
  API_VERSION,
  fetchWithTokenExpiration,
  apiRequest,
  getCsrfToken,
  initCsrfProtection
};
