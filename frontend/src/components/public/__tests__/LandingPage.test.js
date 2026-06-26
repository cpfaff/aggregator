import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import LandingPage from '../LandingPage';

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({ getGridColumns: () => 'repeat(3, 1fr)' }),
}));

afterEach(() => {
  delete global.fetch;
});

describe('LandingPage', () => {
  test('shows stat skeletons while overview statistics load', () => {
    global.fetch = jest.fn(() => new Promise(() => {})); // never resolves

    render(<LandingPage />);

    // The three StatCards render skeletons in place of their values.
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  test('removes the stat skeletons once statistics load', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () =>
          Promise.resolve({ total_providers: 5, total_datacenters: 3, total_datasets: 42 }),
      })
    );

    render(<LandingPage />);

    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
