import React from 'react';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// A child that throws during render.
const Boom = () => {
  throw new Error('boom');
};

describe('ErrorBoundary', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    // React logs the boundary-caught error under --ci; silence it so the
    // expected error does not redden the suite (mirrors DatasetCard.test.js).
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  describe('FR-04 top-level containment (REQ-FE-EB-1)', () => {
    test('renders a fallback UI when a child throws during render instead of unmounting the whole tree', () => {
      render(
        <ErrorBoundary>
          <Boom />
        </ErrorBoundary>,
      );

      // RED (pre-fix): no ErrorBoundary component/file exists, so the import
      // target is missing and a child throw propagates uncaught. (Heading-only
      // matcher: the fallback also carries a "Reload" button, so a
      // /reload/-inclusive getByText would match multiple nodes.)
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });
});
