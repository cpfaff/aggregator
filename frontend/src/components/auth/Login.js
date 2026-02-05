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
  const [loginError, setLoginError] = React.useState('');

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
    setLoginError('');

    try {
      // Get CSRF token first
      await initCsrfProtection();

      // We don't use apiRequest here because we're getting the token
      const res = await fetch(`${API_BASE}${API_VERSION}/tokens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRF-Token': localStorage.getItem('csrfToken')
        },
        body: new URLSearchParams(values),
        credentials: 'include', // Important for CSRF cookies
      });

      if (!res.ok) {
        setLoginError('Invalid username or password. Please try again.');
        setIsLoading(false);
        return;
      }

      const data = await res.json();

      // Use the context's login function
      await login(data.access_token, data.refresh_token, data.expires_in);
      setIsLoading(false);
      showToast('Successfully logged in!', 'success');
    } catch (err) {
      setLoginError('Network error. Please check your connection and try again.');
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

  // Clear session expired message and login error when user starts typing
  useEffect(() => {
    if ((sessionExpired || authSessionExpired) && (form.values.username || form.values.password)) {
      setSessionExpired(false);
    }
    if (loginError && (form.values.username || form.values.password)) {
      setLoginError('');
    }
  }, [form.values.username, form.values.password, sessionExpired, authSessionExpired, setSessionExpired, loginError]);


  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      padding: '2rem',
      backgroundColor: 'var(--background)',
      transition: 'background-color 0.3s',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      overflow: 'hidden',
    }}>
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        padding: '2rem',
        width: '400px',
        maxWidth: '90%',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        transition: 'background-color 0.3s',
        position: 'relative',
        margin: 'auto 0',
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

        {loginError && (
          <Alert type="error">{loginError}</Alert>
        )}

        <form onSubmit={form.handleSubmit} noValidate>
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
            showPasswordToggle={true}
            style={{
              padding: '0.75rem 1rem',
              fontSize: '1rem',
            }}
          />

          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              marginTop: '0.5rem',
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

        {/* Optional help text */}
        <div style={{
          marginTop: '2rem',
          paddingTop: '2rem',
          borderTop: '1px solid var(--border)',
          textAlign: 'center',
        }}>
          <p style={{
            fontSize: '0.875rem',
            color: 'var(--text-light)',
            margin: 0,
          }}>
            Access for registered data providers only
          </p>
          <p style={{
            fontSize: '0.875rem',
            color: 'var(--text-light)',
            marginTop: '0.5rem',
          }}>
            Need help? Contact{' '}
            <a
              href="mailto:info@gfbio.org"
              style={{
                color: 'var(--primary)',
                textDecoration: 'none',
              }}
            >
              info@gfbio.org
            </a>
          </p>
        </div>
      </div>

      {/* Minimal footer info */}
      <div style={{
        position: 'absolute',
        bottom: '2rem',
        left: '50%',
        transform: 'translateX(-50%)',
        fontSize: '0.75rem',
        color: 'var(--text-light)',
        opacity: 0.6,
      }}>
        © {new Date().getFullYear()} GFBio e.V. All rights reserved.
      </div>
    </div>
  );
}

export default Login;
