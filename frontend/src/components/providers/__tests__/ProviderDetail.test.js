import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProviderDetail from '../ProviderDetail';

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ handleTokenExpiration: jest.fn() }),
}));

jest.mock('../../../utils/apiUtils', () => ({
  apiRequest: jest.fn(),
}));

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({ getGridColumns: () => 'repeat(2, 1fr)' }),
}));

jest.mock('../../../utils/statisticsApi', () => ({
  authStatsApi: { getProviderStats: jest.fn().mockResolvedValue({}) },
}));

// Heavy children are irrelevant to the loading state; stub them out.
jest.mock('../../datasets/DatasetCard', () => ({ dataset }) => (
  <div data-testid="dataset-card">{dataset?.id}</div>
));
jest.mock('../../datasets/DatasetForm', () => () => <div data-testid="dataset-form" />);
jest.mock('../ProviderForm', () => () => <div data-testid="provider-form" />);
jest.mock('../../statistics', () => ({ ProviderStatistics: () => <div data-testid="provider-statistics" /> }));
jest.mock('../../ui/Modal', () => ({ children, isOpen }) => (isOpen ? <div>{children}</div> : null));
jest.mock('../../ui/ConfirmModal', () => () => <div data-testid="confirm-modal" />);
jest.mock('../../ui/ActionMenu', () => () => <div data-testid="action-menu" />);
jest.mock('../../ui/Breadcrumbs', () => () => <nav data-testid="breadcrumbs" />);
jest.mock('../../ui/Alert', () => ({ children }) => <div data-testid="alert">{children}</div>);
jest.mock('../../ui/Toast', () => ({ showToast: jest.fn() }));

const { apiRequest } = require('../../../utils/apiUtils');

const adminUser = { username: 'admin', is_global_admin: true, provider_roles: {} };

const renderDetail = () =>
  render(
    <MemoryRouter initialEntries={['/providers/1']}>
      <ProviderDetail currentUser={adminUser} />
    </MemoryRouter>
  );

beforeEach(() => {
  jest.clearAllMocks();
});

describe('ProviderDetail', () => {
  test('shows a skeleton while the provider is loading', () => {
    apiRequest.mockReturnValue(new Promise(() => {})); // never resolves

    renderDetail();

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  test('removes the skeleton once the provider loads', async () => {
    apiRequest.mockImplementation((url) => {
      if (url.includes('/data-sets')) {
        return Promise.resolve({ ok: true, json: jest.fn().mockResolvedValue({ data: [] }) });
      }
      return Promise.resolve({
        ok: true,
        json: jest.fn().mockResolvedValue({
          id: 1,
          name: 'Prov',
          datacenter: 'DC',
          shortName: 'P',
        }),
      });
    });

    renderDetail();

    await waitFor(() => {
      expect(screen.getByText('Prov')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
