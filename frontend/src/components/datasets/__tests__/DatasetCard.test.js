import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DatasetCard from '../DatasetCard';

// Mock dependencies
jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({
    currentUser: { username: 'admin', is_global_admin: true, provider_roles: {} },
    handleTokenExpiration: jest.fn(),
  }),
}));

jest.mock('axios', () => ({
  get: jest.fn().mockResolvedValue({
    data: { validation_status: 'completed', is_valid: true, has_latest_archive: false },
  }),
  post: jest.fn(),
}));

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
  // Suppress console.log from DatasetCard debug statements
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

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

    const link = screen.getByText('Landing page');
    expect(link.closest('a')).toHaveAttribute('href', 'https://example.com/dataset/10');
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
