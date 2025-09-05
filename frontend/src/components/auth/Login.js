import React, { useEffect } from 'react';
import { useAuth } from './AuthContext';
import { API_BASE, API_VERSION, initCsrfProtection } from '../../utils/apiUtils';
import useFormValidation from '../../utils/useFormValidation';
import validationRules from '../../utils/validationRules';
import FormField from '../ui/FormField';
import Alert from '../ui/Alert';
import { showToast } from '../ui/Toast';

// Login component
function Login({ sessionExpired, onViewPublicStats }) {
  const { login, isLoading, setIsLoading, sessionExpired: authSessionExpired, setSessionExpired } = useAuth();
  
  // Define validation schema
  const validationSchema = {
    username: [
      validationRules.required('Username is required'),
      validationRules.minLength(3, 'Username must be at least 3 characters')
    ],
    password: [
      validationRules.required('Password is required'),
      validationRules.minLength(6, 'Password must be at least 6 characters')
    ]
  };

  // Form submission handler
  const handleFormSubmit = async (values) => {
    setIsLoading(true);
    
    try {
      // Get CSRF token first
      await initCsrfProtection();
      
      // We don't use apiRequest here because we're getting the token
      const res = await fetch(`${API_BASE}${API_VERSION}/auth-token`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRF-Token': localStorage.getItem('csrfToken')
        },
        body: new URLSearchParams(values),
        credentials: 'include', // Important for CSRF cookies
      });
      
      if (!res.ok) {
        form.setFieldErrors({ 
          username: ' ', // Space to show error styling
          password: 'Invalid username or password'
        });
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      
      // Use the context's login function
      await login(data.access_token, data.refresh_token, data.expires_in);
      setIsLoading(false);
      showToast('Successfully logged in!', 'success');
    } catch (err) {
      form.setFieldErrors({ 
        username: ' ', // Space to show error styling
        password: 'Network error. Please check your connection'
      });
      setIsLoading(false);
    }
  };

  // Initialize form validation hook
  const form = useFormValidation(
    {
      username: '',
      password: ''
    },
    validationSchema,
    handleFormSubmit
  );

  // Clear session expired message when user starts typing
  useEffect(() => {
    if ((sessionExpired || authSessionExpired) && (form.values.username || form.values.password)) {
      setSessionExpired(false);
    }
  }, [form.values.username, form.values.password, sessionExpired, authSessionExpired, setSessionExpired]);


  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      padding: '24px',
      backgroundColor: 'var(--background)',
      transition: 'background-color 0.3s',
    }}>
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        padding: '2rem',
        width: '400px',
        maxWidth: '100%',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        transition: 'background-color 0.3s',
      }}>
        <h1 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600, 
          marginTop: 0,
          marginBottom: '1.5rem',
          color: 'var(--text)',
        }}>
          Sign In
        </h1>
        
        {(sessionExpired || authSessionExpired) && (
          <Alert type="error">Your session has expired. Please sign in again.</Alert>
        )}
        
        <form onSubmit={form.handleSubmit}>
          <FormField
            type="text"
            name="username"
            label="Username"
            value={form.values.username}
            onChange={form.handleChange}
            onBlur={form.handleBlur}
            error={form.errors.username}
            touched={form.touched.username}
            placeholder="Enter your username"
            autoComplete="username"
            disabled={isLoading}
            required
            style={{
              padding: '0.75rem 1rem',
              fontSize: '1rem',
            }}
          />
          
          <FormField
            type="password"
            name="password"
            label="Password"
            value={form.values.password}
            onChange={form.handleChange}
            onBlur={form.handleBlur}
            error={form.errors.password}
            touched={form.touched.password}
            placeholder="Enter your password"
            autoComplete="current-password"
            disabled={isLoading}
            required
            showPasswordToggle={true}
            style={{
              padding: '0.75rem 1rem',
              fontSize: '1rem',
              marginBottom: '1.5rem'
            }}
          />
          
          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              backgroundColor: 'var(--primary)',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'background 0.2s',
            }}
          >
            {isLoading && (
              <span style={{
                display: 'inline-block',
                width: '16px',
                height: '16px',
                border: '2px solid rgba(255, 255, 255, 0.3)',
                borderRadius: '50%',
                borderTopColor: '#fff',
                animation: 'spin 1s linear infinite',
              }}></span>
            )}
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
