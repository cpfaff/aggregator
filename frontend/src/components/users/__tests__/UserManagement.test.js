import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import UserManagement from '../UserManagement';

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    handleTokenExpiration: jest.fn(),
    user: { username: 'admin', is_global_admin: true, provider_roles: {} },
  }),
}));

jest.mock('../../../utils/apiUtils', () => ({
  apiRequest: jest.fn(),
}));

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({ getGridColumns: () => 'repeat(3, 1fr)' }),
}));

jest.mock('../../ui/Breadcrumbs', () => () => <nav data-testid="breadcrumbs" />);
jest.mock('../../ui/ActionMenu', () => () => <div data-testid="action-menu" />);
jest.mock('../../ui/Modal', () => ({ children, isOpen }) => (isOpen ? <div>{children}</div> : null));
jest.mock('../../ui/ConfirmModal', () => () => <div data-testid="confirm-modal" />);
jest.mock('../../ui/Toast', () => ({ showToast: jest.fn() }));

const { apiRequest } = require('../../../utils/apiUtils');

beforeEach(() => {
  jest.clearAllMocks();
});

describe('UserManagement', () => {
  test('shows user-card skeletons while loading', () => {
    apiRequest.mockReturnValue(new Promise(() => {})); // never resolves

    render(<UserManagement />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
    expect(screen.queryByText('No users found')).not.toBeInTheDocument();
  });

  test('removes the skeletons once users load', async () => {
    apiRequest.mockImplementation((url) => {
      if (url.includes('/users')) {
        return Promise.resolve({
          ok: true,
          json: jest.fn().mockResolvedValue({
            data: [{ username: 'alice', provider_roles: {}, is_global_admin: false }],
          }),
        });
      }
      // providers (or anything else)
      return Promise.resolve({ ok: true, json: jest.fn().mockResolvedValue({ data: [] }) });
    });

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
