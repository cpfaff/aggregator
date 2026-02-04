import React from 'react';
import { render, screen } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';

// Mock apiUtils to prevent actual API calls
jest.mock('../../../utils/apiUtils', () => ({
  refreshAccessToken: jest.fn(),
  apiRequest: jest.fn().mockResolvedValue({
    ok: true,
    json: jest.fn().mockResolvedValue({ username: 'test' }),
  }),
}));

beforeEach(() => {
  localStorage.clear();
});

describe('AuthContext', () => {
  test('renders children without crashing', () => {
    render(
      <AuthProvider>
        <div data-testid="child">Hello</div>
      </AuthProvider>
    );

    expect(screen.getByTestId('child')).toHaveTextContent('Hello');
  });

  test('useAuth provides login and logout functions', () => {
    let authValue;

    function Consumer() {
      authValue = useAuth();
      return null;
    }

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );

    expect(typeof authValue.login).toBe('function');
    expect(typeof authValue.logout).toBe('function');
  });

  test('initially has no user or token when localStorage is empty', () => {
    let authValue;

    function Consumer() {
      authValue = useAuth();
      return null;
    }

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>
    );

    expect(authValue.token).toBeNull();
    expect(authValue.currentUser).toBeNull();
  });
});
