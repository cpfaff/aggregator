import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import Providers from '../Providers';

// Mock dependencies
jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    handleTokenExpiration: jest.fn(),
  }),
}));

jest.mock('../../../utils/apiUtils', () => ({
  apiRequest: jest.fn(),
}));

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    getGridColumns: () => 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))',
  }),
}));

jest.mock('../../ui/Alert', () => ({ children, type }) => (
  <div data-testid={`alert-${type}`}>{children}</div>
));

jest.mock('../../ui/Breadcrumbs', () => ({ items }) => (
  <nav data-testid="breadcrumbs">{items.map((i) => i.label).join(' > ')}</nav>
));

jest.mock('../../ui/ActionMenu', () => () => <div data-testid="action-menu" />);
jest.mock('../../ui/Modal', () => ({ children, isOpen }) => isOpen ? <div data-testid="modal">{children}</div> : null);
jest.mock('../../ui/ConfirmModal', () => () => <div data-testid="confirm-modal" />);
jest.mock('../../ui/Button', () => ({ children, onClick }) => <button onClick={onClick}>{children}</button>);
jest.mock('../../ui/Toast', () => ({ showToast: jest.fn() }));
jest.mock('../ProviderForm', () => () => <div data-testid="provider-form" />);
jest.mock('../ProviderCard', () => ({ provider }) => (
  <div data-testid={`provider-card-${provider.id}`}>{provider.name}</div>
));

const { apiRequest } = require('../../../utils/apiUtils');

const adminUser = {
  username: 'admin',
  is_global_admin: true,
  provider_roles: {},
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('Providers', () => {
  test('shows loading spinner while fetching providers', () => {
    // Never resolve the API call to keep loading state
    apiRequest.mockReturnValue(new Promise(() => {}));

    render(<Providers currentUser={adminUser} onViewProviderDetails={jest.fn()} />);

    // Loading spinner is a div with animation, check loading state indirectly
    // by confirming no providers or empty message are shown
    expect(screen.queryByText('No providers found')).not.toBeInTheDocument();
  });

  test('renders provider cards after data loads', async () => {
    apiRequest.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        data: [
          { id: 1, name: 'Provider A' },
          { id: 2, name: 'Provider B' },
        ],
      }),
    });

    render(<Providers currentUser={adminUser} onViewProviderDetails={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId('provider-card-1')).toHaveTextContent('Provider A');
      expect(screen.getByTestId('provider-card-2')).toHaveTextContent('Provider B');
    });
  });

  test('shows empty state when no providers exist', async () => {
    apiRequest.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({ data: [] }),
    });

    render(<Providers currentUser={adminUser} onViewProviderDetails={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('No providers found')).toBeInTheDocument();
      expect(screen.getByText(/get started by adding/i)).toBeInTheDocument();
    });
  });

  test('shows error alert when API returns error', async () => {
    apiRequest.mockResolvedValue({
      ok: false,
      status: 500,
    });

    render(<Providers currentUser={adminUser} onViewProviderDetails={jest.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId('alert-error')).toHaveTextContent('Failed to fetch providers');
    });
  });

  test('shows action menu for admin users', async () => {
    apiRequest.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({ data: [] }),
    });

    render(<Providers currentUser={adminUser} onViewProviderDetails={jest.fn()} />);

    expect(screen.getByTestId('action-menu')).toBeInTheDocument();
  });

  test('hides action menu for non-admin users', async () => {
    apiRequest.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({ data: [] }),
    });

    const regularUser = { username: 'user1', is_global_admin: false, provider_roles: {} };
    render(<Providers currentUser={regularUser} onViewProviderDetails={jest.fn()} />);

    expect(screen.queryByTestId('action-menu')).not.toBeInTheDocument();
  });
});
