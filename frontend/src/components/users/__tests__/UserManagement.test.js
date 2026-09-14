import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UserManagement from '../UserManagement';

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    handleTokenExpiration: jest.fn(),
    user: { username: 'admin', is_global_admin: true, provider_roles: {} },
  }),
}));

jest.mock('../../../utils/apiUtils', () => ({
  // readJson stays real: it is the content-type guard the component now relies on.
  readJson: jest.requireActual('../../../utils/apiUtils').readJson,
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
          ok: true, headers: { get: () => 'application/json' },
          json: jest.fn().mockResolvedValue({
            data: [{ username: 'alice', provider_roles: {}, is_global_admin: false }],
          }),
        });
      }
      // providers (or anything else)
      return Promise.resolve({ ok: true, headers: { get: () => 'application/json' }, json: jest.fn().mockResolvedValue({ data: [] }) });
    });

    render(<UserManagement />);

    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});

describe('UserManagement 422 degradation', () => {
  // FR-07 (REQ-FE-DEG-1): a FastAPI 422 array detail must surface the per-field
  // message, not pass the raw array to the error Alert.
  test('shows the per-field message when create returns a 422 array detail', async () => {
    apiRequest.mockImplementation((url, options) => {
      if (url === '/users' && options?.method === 'POST') {
        return Promise.resolve({
          ok: false,
          status: 422,
          json: () =>
            Promise.resolve({
              detail: [
                {
                  loc: ['body', 'password'],
                  msg: 'String should have at least 8 characters',
                  type: 'string_too_short',
                },
              ],
            }),
        });
      }
      // mount fetches (users + providers) -> empty so the empty-state Add User
      // button renders.
      return Promise.resolve({ ok: true, headers: { get: () => 'application/json' }, json: () => Promise.resolve({ data: [] }) });
    });

    render(<UserManagement />);

    const addButton = await screen.findByRole('button', { name: /add user/i });
    userEvent.click(addButton);

    // Fill valid values so client-side validation passes (>=3 / >=8 chars) and
    // the only "at least 8 characters" text can come from the server 422.
    const usernameInput = await screen.findByPlaceholderText('Enter username');
    userEvent.type(usernameInput, 'alice');
    userEvent.type(screen.getByPlaceholderText('Enter password'), 'password123');
    userEvent.click(screen.getByRole('button', { name: /create user/i }));

    // RED (pre-fix): the truthy 422 array is stored in formError and passed to
    // <Alert> as a React child -> React 18 throws "Objects are not valid as a
    // React child", so the field message never appears.
    expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument();
  });
});
