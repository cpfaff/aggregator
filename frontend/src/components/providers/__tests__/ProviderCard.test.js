import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProviderCard from '../ProviderCard';

const mockProvider = {
  id: 1,
  name: 'Test Provider',
  datacenter: 'Berlin',
  url: 'https://example.com',
  biocaseUrl: 'https://biocase.example.com',
  updated_at: '2024-01-15T10:00:00Z',
  datasets: [{ id: 1 }, { id: 2 }],
};

const defaultProps = {
  provider: mockProvider,
  currentUser: { username: 'admin', is_global_admin: true, provider_roles: {} },
  onEdit: jest.fn(),
  onDelete: jest.fn(),
  onViewDetails: jest.fn(),
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('ProviderCard', () => {
  test('renders provider name and dataset count', () => {
    render(<ProviderCard {...defaultProps} />);

    expect(screen.getByText('Test Provider')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('datasets')).toBeInTheDocument();
  });

  test('renders provider ID badge', () => {
    render(<ProviderCard {...defaultProps} />);

    expect(screen.getByLabelText('Provider ID: 1')).toHaveTextContent('#1');
  });

  test('shows delete button for global admin', () => {
    render(<ProviderCard {...defaultProps} />);

    expect(screen.getByLabelText('Delete provider: Test Provider')).toBeInTheDocument();
  });

  test('hides delete button for non-admin user', () => {
    render(
      <ProviderCard
        {...defaultProps}
        currentUser={{ username: 'user1', is_global_admin: false, provider_roles: {} }}
      />
    );

    expect(screen.queryByLabelText('Delete provider: Test Provider')).not.toBeInTheDocument();
  });

  test('calls onViewDetails when card is clicked', () => {
    render(<ProviderCard {...defaultProps} />);

    userEvent.click(screen.getByRole('button', { name: /view details for test provider/i }));

    expect(defaultProps.onViewDetails).toHaveBeenCalledWith(mockProvider);
  });

  test('calls onDelete when delete button is clicked', () => {
    render(<ProviderCard {...defaultProps} />);

    userEvent.click(screen.getByLabelText('Delete provider: Test Provider'));

    expect(defaultProps.onDelete).toHaveBeenCalledWith(mockProvider);
    // Should NOT trigger onViewDetails
    expect(defaultProps.onViewDetails).not.toHaveBeenCalled();
  });

  test('shows "No links available" when provider has no URLs', () => {
    const noLinksProvider = { ...mockProvider, url: null, biocaseUrl: null };
    render(<ProviderCard {...defaultProps} provider={noLinksProvider} />);

    expect(screen.getByText('No links available')).toBeInTheDocument();
  });

  test('shows 0 datasets when provider has no datasets', () => {
    const emptyProvider = { ...mockProvider, datasets: [] };
    render(<ProviderCard {...defaultProps} provider={emptyProvider} />);

    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('datasets')).toBeInTheDocument();
  });
});
