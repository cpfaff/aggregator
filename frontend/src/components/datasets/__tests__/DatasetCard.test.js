import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
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

  // FR-09 (REQ-FE-CLIENT-4): the side-effecting validate POST must carry a
  // client-supplied Idempotency-Key so a retry/double-click cannot enqueue
  // duplicate validation jobs.
  test('triggerValidation sends an Idempotency-Key header on the validate POST', async () => {
    axios.get.mockImplementation((url) =>
      typeof url === 'string' && url.includes('validation-status')
        ? Promise.resolve({
            data: { has_latest_archive: true, validation_status: 'completed', is_valid: true },
          })
        : Promise.resolve({ data: VALIDATION_PAYLOAD })
    );
    axios.post.mockResolvedValue({ data: {} });

    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />);

    const button = await screen.findByRole('button', { name: /re-validate/i });
    userEvent.click(button);

    // RED (pre-fix): the post headers are only { Authorization }, so the
    // Idempotency-Key matcher fails.
    await waitFor(() => {
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/validate'),
        expect.anything(),
        expect.objectContaining({
          headers: expect.objectContaining({ 'Idempotency-Key': expect.any(String) }),
        })
      );
    });
  });

  // Regression (same root cause as the public-stats abort bug): under React
  // StrictMode's dev double-mount the discarded mount's validation request is
  // aborted; the catch must attribute that to the OWNING controller (not the
  // surviving mount's) and the overlap guard must release on unmount, so the
  // validation status still loads instead of silently going missing.
  test('loads validation status under StrictMode remount without mis-attributing the discarded mount abort', async () => {
    const abortAware = (data) => (url, config = {}) =>
      new Promise((resolve, reject) => {
        const { signal } = config;
        const fail = () => {
          const e = new Error('canceled');
          e.name = 'CanceledError';
          reject(e);
        };
        if (signal?.aborted) {
          fail();
          return;
        }
        if (signal) {
          signal.addEventListener('abort', fail, { once: true });
        }
        Promise.resolve().then(() => {
          if (!signal?.aborted) {
            resolve({ data });
          }
        });
      });

    axios.get.mockImplementation((url, config) =>
      typeof url === 'string' && url.includes('validation-status')
        ? abortAware({ has_latest_archive: true, validation_status: 'completed', is_valid: true })(url, config)
        : Promise.resolve({ data: VALIDATION_PAYLOAD })
    );

    render(
      <React.StrictMode>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
          <DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />
        </SWRConfig>
      </React.StrictMode>
    );

    // RED (pre-fix): the discarded mount's abort is mis-attributed and the
    // remount's fetch is skipped by the stuck guard, so validationStatus stays
    // null and the Re-validate button never renders.
    expect(await screen.findByRole('button', { name: /re-validate/i })).toBeInTheDocument();
  });
});

describe('DatasetCard validation poller backpressure', () => {
  // Count validation-status GETs across the lifecycle:
  //  #1 mount  -> completed (Re-validate button enabled, no poll yet)
  //  #2 immediate post-validate fetch -> running (interval starts)
  //  #3+ interval ticks -> never resolve (stay in flight)
  const wireValidationCounter = () => {
    let validationCalls = 0;
    axios.get.mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('validation-status')) {
        validationCalls += 1;
        if (validationCalls === 1) {
          return Promise.resolve({
            data: { has_latest_archive: true, validation_status: 'completed', is_valid: true },
          });
        }
        if (validationCalls === 2) {
          return Promise.resolve({
            data: { has_latest_archive: true, validation_status: 'running' },
          });
        }
        return new Promise(() => {}); // never resolves -> in flight
      }
      return Promise.resolve({ data: VALIDATION_PAYLOAD });
    });
    axios.post.mockResolvedValue({ data: {} });
    return () => validationCalls;
  };

  const flush = async () => {
    await act(async () => {
      for (let i = 0; i < 10; i++) {
        // eslint-disable-next-line no-await-in-loop
        await Promise.resolve();
      }
    });
  };

  // FR-05 (REQ-FE-POLL-1): a never-resolving backend must not let 3s ticks
  // accumulate overlapping in-flight validation-status requests.
  test('validation poll does not stack a second request while the first is still pending', async () => {
    const getCalls = wireValidationCounter();

    render(<DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />);

    // Mount fetch (#1, completed) renders the Re-validate button.
    const button = await screen.findByRole('button', { name: /re-validate/i });

    // Scope fake timers to this test (suite default is real timers).
    jest.useFakeTimers();
    try {
      // userEvent v13 click already wraps the synchronous state update in act.
      userEvent.click(button);
      // Flush the validate POST + immediate fetch (#2) so the interval is armed.
      await flush();
      const callsAfterStart = getCalls(); // expect 2 (mount + immediate)

      // Three 3s ticks against a never-resolving backend.
      await act(async () => {
        jest.advanceTimersByTime(9000);
      });

      // GREEN: the first tick starts one in-flight GET that never resolves; the
      // overlap guard early-returns the next two ticks -> at most one extra GET.
      // RED (pre-fix): each tick fires axios.get regardless, so the delta is 3.
      expect(getCalls() - callsAfterStart).toBeLessThanOrEqual(1);
    } finally {
      jest.useRealTimers();
    }
  });

  // FR-06 (REQ-FE-POLL-2): a validation request in flight at unmount must carry
  // an AbortSignal and be aborted, so no setState runs after unmount. (React 18
  // emits no "state update on an unmounted component" warning, so the assertion
  // is on the signal itself, not on console.error.)
  test('unmounting mid-validation-fetch passes an abort signal and aborts the in-flight request', async () => {
    // The validation-status GET never resolves -> it is in flight at unmount.
    axios.get.mockImplementation((url) =>
      typeof url === 'string' && url.includes('validation-status')
        ? new Promise(() => {})
        : Promise.resolve({ data: VALIDATION_PAYLOAD })
    );

    const { unmount } = render(
      <DatasetCard dataset={mockDataset} onEdit={jest.fn()} onDelete={jest.fn()} />
    );

    // RED (pre-fix): the GET config is { headers, timeout } with no signal, so
    // this objectContaining matcher fails.
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalledWith(
        expect.stringContaining('validation-status'),
        expect.objectContaining({ signal: expect.any(AbortSignal) })
      );
    });

    const validationCall = axios.get.mock.calls.find(
      ([url]) => typeof url === 'string' && url.includes('validation-status')
    );
    const { signal } = validationCall[1];
    expect(signal.aborted).toBe(false);

    unmount();

    // RED (pre-fix): the unmount cleanup clears only the interval, never aborting.
    expect(signal.aborted).toBe(true);
  });
});
