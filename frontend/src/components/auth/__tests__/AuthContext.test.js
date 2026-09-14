import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { apiRequest } from '../../../utils/apiUtils';

// Mock apiUtils to prevent actual API calls.
//
// readJson is deliberately the REAL implementation: it is the content-type guard
// under test in the DASS-3814 regression case below, and stubbing it would make
// that test assert against itself. The default apiRequest therefore has to return
// a response whose headers say JSON, or readJson will (correctly) reject it.
jest.mock('../../../utils/apiUtils', () => ({
  readJson: jest.requireActual('../../../utils/apiUtils').readJson,
  refreshAccessToken: jest.fn(),
  apiRequest: jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: { get: () => 'application/json' },
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


describe('DASS-3814 maintenance page must not surface as a raw SyntaxError', () => {
  test('a 200 text/html on /me/permissions is typed, and the cached user survives', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    localStorage.setItem('token', 't');
    localStorage.setItem('currentUser', JSON.stringify({ username: 'admin' }));

    // Exactly what the maintenance nginx returned before the fix.
    apiRequest.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'text/html' },
      json: () =>
        Promise.reject(new SyntaxError(`Unexpected token '<', "<!DOCTYPE "... is not valid JSON`)),
    });

    render(
      <AuthProvider>
        <div data-testid="child">Hello</div>
      </AuthProvider>
    );

    await waitFor(() => expect(consoleError).toHaveBeenCalled());

    const logged = consoleError.mock.calls[0][1];
    expect(logged).not.toBeInstanceOf(SyntaxError);
    expect(logged.name).toBe('NonJsonResponseError');
    expect(logged.class).toBe('server');
    // the maintenance page must not evict the cached identity
    expect(JSON.parse(localStorage.getItem('currentUser'))).toEqual({ username: 'admin' });

    consoleError.mockRestore();
  });
});
