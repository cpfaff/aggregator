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
 * Updates authentication tokens and dispatches an event for AuthContext
 * @param {string} access_token - The new access token
 * @param {string} refresh_token - The new refresh token
 * @param {number} expires_in - Expiry time in seconds
 * @returns {boolean} - Whether the update was successful
 */
export const updateTokens = (access_token, refresh_token, expires_in) => {
  localStorage.setItem('token', access_token);
  localStorage.setItem('refreshToken', refresh_token);
  localStorage.setItem('tokenExpiry', Date.now() + (expires_in * 1000));

  // Dispatch a custom event that AuthContext can listen for
  window.dispatchEvent(new CustomEvent('auth:tokens-updated', {
    detail: { access_token, refresh_token, expires_in }
  }));

  return true;
};

/**
 * Attempts to refresh the access token using the refresh token
 * @returns {Promise<boolean>} - Whether the refresh was successful
 */
export const refreshAccessToken = async () => {
  try {
    // Get stored refresh token
    const refreshToken = localStorage.getItem('refreshToken');

    if (!refreshToken) {
      return false;
    }

    // Get CSRF token for the request
    let csrfToken;
    try {
      csrfToken = await getCsrfToken();
    } catch (error) {
      console.error('Failed to get CSRF token for refresh:', error);
      return false;
    }

    // Call refresh endpoint
    const response = await fetch(`${API_BASE}${API_VERSION}/refresh-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
      credentials: 'include'
    });

    if (!response.ok) {
      return false;
    }

    // Parse response and update stored tokens using the updateTokens function
    const data = await response.json();
    return updateTokens(data.access_token, data.refresh_token, data.expires_in);
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
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
    // Check if token is about to expire (30 seconds buffer)
    const tokenExpiry = localStorage.getItem('tokenExpiry');
    if (tokenExpiry && Date.now() > (parseInt(tokenExpiry) - 30000)) {
      // Proactively refresh token before it expires
      const refreshSuccess = await refreshAccessToken();
      if (!refreshSuccess) {
        // If refresh fails, trigger expiration callback
        if (onTokenExpired && typeof onTokenExpired === 'function') {
          onTokenExpired();
          throw new Error('Session expired. Please login again.');
        }
      }

      // Update Authorization header with new token
      if (options.headers && options.headers.Authorization) {
        options.headers.Authorization = `Bearer ${localStorage.getItem('token')}`;
      }
    }

    // Make the API request
    const response = await fetch(url, options);

    // Handle 401 Unauthorized errors
    if (response.status === 401 && !url.endsWith(`${API_VERSION}/auth-token`)) {
      // Try to refresh the token
      const refreshSuccess = await refreshAccessToken();

      if (refreshSuccess) {
        // If refresh succeeded, retry the original request with new token
        const newOptions = { ...options };
        if (newOptions.headers && newOptions.headers.Authorization) {
          newOptions.headers.Authorization = `Bearer ${localStorage.getItem('token')}`;
        }
        return fetch(url, newOptions);
      } else {
        // If refresh failed, trigger expiration callback
        if (onTokenExpired && typeof onTokenExpired === 'function') {
          onTokenExpired();
        }
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
  refreshAccessToken,
  updateTokens,
  initCsrfProtection
};
