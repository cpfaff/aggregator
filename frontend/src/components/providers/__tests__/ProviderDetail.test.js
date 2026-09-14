import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProviderDetail from '../ProviderDetail';

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ handleTokenExpiration: jest.fn() }),
}));

jest.mock('../../../utils/apiUtils', () => ({
  // readJson stays real: it is the content-type guard the component now relies on.
  readJson: jest.requireActual('../../../utils/apiUtils').readJson,
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
const { authStatsApi } = require('../../../utils/statisticsApi');

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
        return Promise.resolve({ ok: true, headers: { get: () => 'application/json' }, json: jest.fn().mockResolvedValue({ data: [] }) });
      }
      return Promise.resolve({
        ok: true, headers: { get: () => 'application/json' },
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

describe('ProviderDetail validation-rate reserve (CLS)', () => {
  // Wire the provider + datasets endpoints; getProviderStats is controlled
  // per-test (it is the slow index query whose landing shifts the header, which
  // sits above the dataset grid — so a header shift ripples the whole page).
  const wireProvider = ({ datasets = [], name = 'Prov' } = {}) => {
    apiRequest.mockImplementation((url) => {
      if (url.includes('/data-sets')) {
        return Promise.resolve({ ok: true, headers: { get: () => 'application/json' }, json: jest.fn().mockResolvedValue({ data: datasets }) });
      }
      return Promise.resolve({
        ok: true, headers: { get: () => 'application/json' },
        json: jest.fn().mockResolvedValue({ id: 1, name, datacenter: 'DC', shortName: 'P' }),
      });
    });
  };

  test('reserves the validation-rate slot with a skeleton while stats are pending (datasets present)', async () => {
    wireProvider({ datasets: [{ id: 1 }] });
    authStatsApi.getProviderStats.mockReturnValue(new Promise(() => {})); // never resolves

    renderDetail();

    expect(await screen.findByLabelText('Loading validation success rate')).toBeInTheDocument();
    // The real rate value is not shown while the reserve skeleton is up.
    expect(screen.queryByText('87.5%')).toBeNull();
  });

  test('shows the rate and no skeleton once stats land', async () => {
    wireProvider({ datasets: [{ id: 1 }] });
    authStatsApi.getProviderStats.mockResolvedValue({ validation_success_rate: 87.5 });

    renderDetail();

    expect(await screen.findByText('87.5%')).toBeInTheDocument();
    expect(screen.getByText('validation success rate')).toBeInTheDocument();
    expect(screen.queryByLabelText('Loading validation success rate')).toBeNull();
  });

  test('does NOT reserve the slot when the provider has no datasets (predictor false)', async () => {
    wireProvider({ datasets: [] });
    authStatsApi.getProviderStats.mockReturnValue(new Promise(() => {})); // pending, but no datasets

    renderDetail();

    // Header has loaded (provider name shown) yet no reserve skeleton appears.
    expect(await screen.findByText('Prov')).toBeInTheDocument();
    expect(screen.queryByLabelText('Loading validation success rate')).toBeNull();
    expect(screen.queryByTestId('validation-rate-region')).toBeNull();
  });

  test('collapses the slot (no permanent skeleton) when stats resolve without a rate', async () => {
    wireProvider({ datasets: [{ id: 1 }] });
    authStatsApi.getProviderStats.mockResolvedValue({}); // no validation_success_rate

    renderDetail();

    expect(await screen.findByText('Prov')).toBeInTheDocument();
    // The transient reserve skeleton resolves away and the slot collapses (the
    // accepted minor shift for a provider with datasets but no rate); it must
    // not spin the skeleton forever.
    await waitFor(() => {
      expect(screen.queryByTestId('validation-rate-region')).toBeNull();
    });
    // With the region gone, its skeleton is necessarily gone too.
    expect(screen.queryByLabelText('Loading validation success rate')).toBeNull();
  });

  test('reserved validation-rate min-height is a non-empty string, equal across loading and loaded', async () => {
    wireProvider({ datasets: [{ id: 1 }] });
    authStatsApi.getProviderStats.mockReturnValue(new Promise(() => {}));
    const { unmount } = renderDetail();
    await screen.findByLabelText('Loading validation success rate');
    const loadingMinH = screen.getByTestId('validation-rate-region').style.minHeight;
    unmount();

    wireProvider({ datasets: [{ id: 1 }] });
    authStatsApi.getProviderStats.mockResolvedValue({ validation_success_rate: 87.5 });
    renderDetail();
    await screen.findByText('87.5%');
    const loadedMinH = screen.getByTestId('validation-rate-region').style.minHeight;

    expect(loadingMinH).not.toBe('');
    expect(loadingMinH).toBe(loadedMinH);
  });
});
