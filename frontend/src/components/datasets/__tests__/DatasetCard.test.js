import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SWRConfig } from 'swr';
import axios from 'axios';
import DatasetCard from '../DatasetCard';

// Mock dependencies
jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    currentUser: { username: 'admin', is_global_admin: true, provider_roles: {} },
    handleTokenExpiration: jest.fn(),
  }),
}));

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

// Default validation payload returned for the validation-status URL.
const VALIDATION_PAYLOAD = {
  validation_status: 'completed',
  is_valid: true,
  has_latest_archive: false,
};

// Helper: wire axios.get to return a harvest payload for the harvest-status URL
// and the validation payload for everything else (per-URL branching).
const mockHarvest = (harvestPayload) => {
  axios.get.mockImplementation((url) =>
    typeof url === 'string' && url.includes('harvest-status')
      ? Promise.resolve({ data: harvestPayload })
      : Promise.resolve({ data: VALIDATION_PAYLOAD })
  );
};

jest.mock('../../../utils/statisticsApi', () => ({
  authStatsApi: {
    getDatasetStats: jest.fn().mockResolvedValue({ unit_count: 42 }),
  },
}));

jest.mock('../ValidationResultsModal', () => () => <div data-testid="validation-modal" />);

const mockDataset = {
  id: 10,
  title: 'Test Dataset',
  provider_id: 1,
  updated_at: '2024-06-01T12:00:00Z',
  xmlArchives: [{ id: 1 }, { id: 2 }, { id: 3 }],
  usefulLinks: [{ id: 1 }],
  landingPageUrl: 'https://example.com/dataset/10',
};

beforeEach(() => {
  jest.clearAllMocks();
  // Default axios.get: validation payload for any URL (overridden per-test via mockHarvest).
  axios.get.mockResolvedValue({ data: VALIDATION_PAYLOAD });
  // Suppress console.log from DatasetCard debug statements
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

// Render the card inside an isolated SWR cache so harvest-status fetches
// are deterministic and never bleed between tests.
const renderCard = (dataset) =>
  render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <DatasetCard dataset={dataset} onEdit={jest.fn()} onDelete={jest.fn()} />
    </SWRConfig>
  );

afterEach(() => {
  console.log.mockRestore();
  console.error.mockRestore();
});

describe('DatasetCard', () => {
  test('renders dataset title and ID badge', () => {
    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />);

    expect(screen.getByText('Test Dataset')).toBeInTheDocument();
    expect(screen.getByLabelText('Dataset ID: 10')).toHaveTextContent('#10');
  });

  test('renders archive and link counts', () => {
    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />);

    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('archives')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('link')).toBeInTheDocument();
  });

  test('shows delete button for global admin', () => {
    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />);

    expect(screen.getByLabelText('Delete dataset: Test Dataset')).toBeInTheDocument();
  });

  test('calls onDelete when delete button is clicked', () => {
    const onDelete = jest.fn();

    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={onDelete} />);

    userEvent.click(screen.getByLabelText('Delete dataset: Test Dataset'));

    expect(onDelete).toHaveBeenCalledWith(mockDataset);
  });

  test('calls onEdit when edit button is clicked', () => {
    const onEdit = jest.fn();

    render(<DatasetCard dataset={mockDataset} onEdit={onEdit} onDelete={jest.fn()} />);

    userEvent.click(screen.getByLabelText('Edit dataset: Test Dataset'));

    expect(onEdit).toHaveBeenCalledWith(mockDataset);
  });

  test('renders landing page link when URL is provided', () => {
    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />);

    const link = screen.getByRole('link', { name: /landing page/i });
    expect(link).toHaveAttribute('href', 'https://example.com/dataset/10');
  });

  test('shows "No landing page" when URL is missing', () => {
    const noLandingPage = { ...mockDataset, landingPageUrl: null };
    render(<DatasetCard dataset={noLandingPage} onEdit={jest.fn()} onDelete={jest.fn()} />);

    expect(screen.getByText('No landing page available')).toBeInTheDocument();
  });

  test('uses singular "archive" for single archive', () => {
    const singleArchive = { ...mockDataset, xmlArchives: [{ id: 1 }] };
    render(<DatasetCard dataset={singleArchive} onEdit={jest.fn()} onDelete={jest.fn()} />);

    expect(screen.getByText('archive')).toBeInTheDocument();
  });
});

describe('DatasetCard harvest-status badge', () => {
  // A harvest-ready dataset triggers the SWR fetch (no strict-false short-circuit).
  const harvestReadyDataset = { ...mockDataset, isHarvestReady: true };

  test('renders in_index with M==N: "In index · 5 units · last seen Jun 20, 2026"', async () => {
    mockHarvest({
      dataset_id: 10,
      is_harvest_ready: true,
      harvest_status: 'in_index',
      units_in_index: 5,
      units_expected: 5,
      last_seen_in_index_at: '2026-06-20T09:00:00Z',
      index_checked_at: '2026-06-21T03:00:00Z',
    });

    renderCard(harvestReadyDataset);

    expect(
      await screen.findByLabelText('Harvest status: in index, 5 of 5 units')
    ).toBeInTheDocument();
    expect(screen.getByText('In index · 5 units · last seen Jun 20, 2026')).toBeInTheDocument();
    // Adjacent wrong-state copy absent.
    expect(screen.queryByText(/^Partially in index/)).toBeNull();
  });

  test('renders in_index with N null: "5 units" (no "of N")', async () => {
    mockHarvest({
      dataset_id: 10,
      is_harvest_ready: true,
      harvest_status: 'in_index',
      units_in_index: 5,
      units_expected: null,
      last_seen_in_index_at: '2026-06-20T09:00:00Z',
      index_checked_at: '2026-06-21T03:00:00Z',
    });

    renderCard(harvestReadyDataset);

    expect(
      await screen.findByLabelText('Harvest status: in index, 5 units')
    ).toBeInTheDocument();
    expect(screen.getByText('In index · 5 units · last seen Jun 20, 2026')).toBeInTheDocument();
    // Never "5 of null"/"5 of undefined".
    expect(screen.queryByText(/of null/)).toBeNull();
    expect(screen.queryByText(/of undefined/)).toBeNull();
  });

  test('renders partial: "Partially in index · 3 of 5 units · last seen Jun 20, 2026"', async () => {
    mockHarvest({
      dataset_id: 10,
      is_harvest_ready: true,
      harvest_status: 'partial',
      units_in_index: 3,
      units_expected: 5,
      last_seen_in_index_at: '2026-06-20T09:00:00Z',
      index_checked_at: '2026-06-21T03:00:00Z',
    });

    renderCard(harvestReadyDataset);

    expect(
      await screen.findByLabelText('Harvest status: partially in index, 3 of 5 units')
    ).toBeInTheDocument();
    expect(
      screen.getByText('Partially in index · 3 of 5 units · last seen Jun 20, 2026')
    ).toBeInTheDocument();
    // Adjacent wrong-state copy absent.
    expect(screen.queryByText(/^In index/)).toBeNull();
  });

  test('renders not_in_index: "Not yet in index" with no last-seen segment', async () => {
    mockHarvest({
      dataset_id: 10,
      is_harvest_ready: true,
      harvest_status: 'not_in_index',
      units_in_index: 0,
      units_expected: 5,
      last_seen_in_index_at: null,
      index_checked_at: '2026-06-21T03:00:00Z',
    });

    renderCard(harvestReadyDataset);

    expect(
      await screen.findByLabelText('Harvest status: not yet in index')
    ).toBeInTheDocument();
    expect(screen.getByText('Not yet in index')).toBeInTheDocument();
    // last_seen_in_index_at is null -> the segment must be absent (no Invalid Date).
    expect(screen.queryByText(/last seen/)).toBeNull();
    expect(screen.queryByText(/Invalid Date/)).toBeNull();
    // Adjacent wrong-state copy absent.
    expect(screen.queryByText(/^In index/)).toBeNull();
  });

  test('renders server unknown as "Status unavailable"', async () => {
    mockHarvest({
      dataset_id: 10,
      is_harvest_ready: true,
      harvest_status: 'unknown',
      units_in_index: null,
      units_expected: null,
      last_seen_in_index_at: null,
      index_checked_at: '2026-06-21T03:00:00Z',
    });

    renderCard(harvestReadyDataset);

    expect(
      await screen.findByLabelText('Harvest status: unavailable')
    ).toBeInTheDocument();
    expect(screen.getByText('Status unavailable')).toBeInTheDocument();
    expect(screen.queryByText(/^In index/)).toBeNull();
  });

  test('renders fetch error as "Status unavailable" and card still renders', async () => {
    axios.get.mockImplementation((url) =>
      typeof url === 'string' && url.includes('harvest-status')
        ? Promise.reject(new Error('boom'))
        : Promise.resolve({ data: VALIDATION_PAYLOAD })
    );

    renderCard(harvestReadyDataset);

    expect(
      await screen.findByLabelText('Harvest status: unavailable')
    ).toBeInTheDocument();
    expect(screen.getByText('Status unavailable')).toBeInTheDocument();
    // No thrown error escaped: the card body still rendered.
    expect(screen.getByLabelText('Dataset: Test Dataset')).toBeInTheDocument();
  });

  test('staged (isHarvestReady === false) shows staged copy and does NOT fetch harvest-status', async () => {
    const stagedDataset = { ...mockDataset, isHarvestReady: false };

    renderCard(stagedDataset);

    expect(
      await screen.findByLabelText('Harvest status: staged')
    ).toBeInTheDocument();
    expect(screen.getByText('Staged · not in harvester feed')).toBeInTheDocument();
    // No harvest-status request was ever made (null SWR key).
    expect(axios.get).not.toHaveBeenCalledWith(
      expect.stringContaining('harvest-status'),
      expect.anything()
    );
  });

  test('isHarvestReady === true DOES fetch harvest-status', async () => {
    mockHarvest({
      dataset_id: 10,
      is_harvest_ready: true,
      harvest_status: 'in_index',
      units_in_index: 5,
      units_expected: 5,
      last_seen_in_index_at: '2026-06-20T09:00:00Z',
      index_checked_at: '2026-06-21T03:00:00Z',
    });

    renderCard(harvestReadyDataset);

    await screen.findByLabelText('Harvest status: in index, 5 of 5 units');
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('harvest-status'),
      expect.anything()
    );
  });

  test('isHarvestReady undefined still fetches (not treated as staged)', async () => {
    // mockDataset has no isHarvestReady field at all.
    mockHarvest({
      dataset_id: 10,
      is_harvest_ready: true,
      harvest_status: 'in_index',
      units_in_index: 5,
      units_expected: 5,
      last_seen_in_index_at: '2026-06-20T09:00:00Z',
      index_checked_at: '2026-06-21T03:00:00Z',
    });

    renderCard(mockDataset);

    expect(
      await screen.findByLabelText('Harvest status: in index, 5 of 5 units')
    ).toBeInTheDocument();
    // Must NOT be treated as staged.
    expect(screen.queryByText('Staged · not in harvester feed')).toBeNull();
    expect(axios.get).toHaveBeenCalledWith(
      expect.stringContaining('harvest-status'),
      expect.anything()
    );
  });

  test('shows loading placeholder while harvest fetch is pending and card still renders', async () => {
    axios.get.mockImplementation((url) =>
      typeof url === 'string' && url.includes('harvest-status')
        ? new Promise(() => {}) // never resolves
        : Promise.resolve({ data: VALIDATION_PAYLOAD })
    );

    renderCard(harvestReadyDataset);

    expect(await screen.findByText('Checking index…')).toBeInTheDocument();
    // Card still renders (non-blocking placeholder).
    expect(screen.getByLabelText('Dataset: Test Dataset')).toBeInTheDocument();
  });

  test('dataset.id undefined: no harvest-status fetch fires and card renders', async () => {
    const noId = { ...mockDataset, id: undefined, isHarvestReady: true };

    renderCard(noId);

    // Card renders.
    expect(screen.getByLabelText('Dataset: Test Dataset')).toBeInTheDocument();
    // Null SWR key -> no harvest fetch.
    await waitFor(() => {
      expect(axios.get).not.toHaveBeenCalledWith(
        expect.stringContaining('harvest-status'),
        expect.anything()
      );
    });
  });
});

describe('DatasetCard transport resilience', () => {
  // FR-03 (REQ-FE-CLIENT-3): axios defaults to no timeout, so a hung
  // validation/harvest/validate endpoint pins the request forever.
  test('validation-status request is issued with a request timeout', async () => {
    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />);

    // RED (pre-fix): the config is { headers: { Authorization } } with no
    // timeout key, so the objectContaining matcher fails.
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining('validation-status'),
        expect.objectContaining({ timeout: expect.any(Number) })
      );
    });
  });
});
