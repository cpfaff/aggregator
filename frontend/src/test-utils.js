import React from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock auth context value matching AuthContext.js shape
const AuthContext = React.createContext(null);

export const defaultAuth = {
  token: null,
  currentUser: null,
  isLoading: false,
  setIsLoading: jest.fn(),
  sessionExpired: false,
  setSessionExpired: jest.fn(),
  login: jest.fn(),
  logout: jest.fn(),
  handleTokenExpiration: jest.fn(),
};

export const adminAuth = {
  token: 'fake-token',
  currentUser: {
    username: 'admin',
    is_global_admin: true,
    provider_roles: {},
  },
  isLoading: false,
  setIsLoading: jest.fn(),
  sessionExpired: false,
  setSessionExpired: jest.fn(),
  login: jest.fn(),
  logout: jest.fn(),
  handleTokenExpiration: jest.fn(),
};

export const regularUserAuth = {
  token: 'fake-token',
  currentUser: {
    username: 'user1',
    is_global_admin: false,
    provider_roles: { '1': 'curator' },
  },
  isLoading: false,
  setIsLoading: jest.fn(),
  sessionExpired: false,
  setSessionExpired: jest.fn(),
  login: jest.fn(),
  logout: jest.fn(),
  handleTokenExpiration: jest.fn(),
};

/**
 * Renders a component wrapped with MemoryRouter and a mock AuthContext.
 * Import useAuth from this module in your tests to get the mocked context.
 */
export function renderWithProviders(
  ui,
  { authValue = adminAuth, initialEntries = ['/'], ...renderOptions } = {}
) {
  function Wrapper({ children }) {
    return (
      <AuthContext.Provider value={authValue}>
        <MemoryRouter initialEntries={initialEntries}>
          {children}
        </MemoryRouter>
      </AuthContext.Provider>
    );
  }

  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }), authValue };
}

// Re-export the mock AuthContext for manual use
export { AuthContext };
