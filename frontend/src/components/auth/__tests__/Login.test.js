import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Login from '../Login';

// Mock useAuth hook
const mockLogin = jest.fn();
const mockSetIsLoading = jest.fn();
const mockSetSessionExpired = jest.fn();

jest.mock('../AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
    isLoading: false,
    setIsLoading: mockSetIsLoading,
    sessionExpired: false,
    setSessionExpired: mockSetSessionExpired,
  }),
}));

// Mock apiUtils
jest.mock('../../../utils/apiUtils', () => ({
  API_BASE: '',
  API_VERSION: '/api/v1',
  initCsrfProtection: jest.fn().mockResolvedValue(undefined),
  // readJson stays real: it is the content-type guard Login now relies on.
  readJson: jest.requireActual('../../../utils/apiUtils').readJson,
  NON_JSON_RESPONSE_MESSAGE:
    jest.requireActual('../../../utils/apiUtils').NON_JSON_RESPONSE_MESSAGE,
}));

// Mock Toast
jest.mock('../../ui/Toast', () => ({
  showToast: jest.fn(),
}));

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe('Login', () => {
  test('renders username and password input fields', () => {
    render(<Login />);

    expect(screen.getByPlaceholderText('Enter your username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
  });

  test('renders a sign in button', () => {
    render(<Login />);

    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  test('shows validation error when submitting with empty username', async () => {
    render(<Login />);

    const usernameInput = screen.getByPlaceholderText('Enter your username');
    // Focus and blur to trigger validation
    userEvent.click(usernameInput);
    userEvent.tab();

    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument();
    });
  });

  test('calls login API with correct credentials on valid submit', async () => {
    const mockResponse = {
      ok: true,
      json: jest.fn().mockResolvedValue({
        access_token: 'test-token',
        refresh_token: 'test-refresh',
        expires_in: 3600,
      }),
    };
    global.fetch = jest.fn().mockResolvedValue(mockResponse);

    render(<Login />);

    userEvent.type(screen.getByPlaceholderText('Enter your username'), 'testuser');
    userEvent.type(screen.getByPlaceholderText('Enter your password'), 'password123');
    userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/tokens',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    // Cleanup
    delete global.fetch;
  });

  test('displays error message when login API returns 401', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
    });

    render(<Login />);

    userEvent.type(screen.getByPlaceholderText('Enter your username'), 'baduser');
    userEvent.type(screen.getByPlaceholderText('Enter your password'), 'wrongpass');
    userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid username or password/i)).toBeInTheDocument();
    });

    // Cleanup
    delete global.fetch;
  });
});
