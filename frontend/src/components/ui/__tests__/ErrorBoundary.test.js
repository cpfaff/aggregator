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

  describe('FR-18 widget bulkheads (REQ-FE-EB-2)', () => {
    // Spec-named verification. NOTE: this assertion is satisfied by the FR-04
    // boundary already (any ErrorBoundary contains a child throw, so a sibling
    // outside it always survives) — it is a conformance check, not the RED lock.
    test('contains a throwing child to its own boundary while a sibling subtree keeps rendering', () => {
      render(
        <>
          <ErrorBoundary>
            <Boom />
          </ErrorBoundary>
          <div>sibling-ok</div>
        </>,
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByText('sibling-ok')).toBeInTheDocument();
    });

    // Genuine RED lock for FR-18's new code: the optional fallback prop that lets
    // ErrorBoundary act as a per-widget bulkhead with its own affordance.
    test('renders a provided fallback prop in place of the default when a child throws', () => {
      render(
        <ErrorBoundary fallback={<div>custom-widget-fallback</div>}>
          <Boom />
        </ErrorBoundary>,
      );

      // RED (pre-FR-18): ErrorBoundary ignores the fallback prop and renders the
      // static default, so the custom fallback is absent and the default present.
      expect(screen.getByText('custom-widget-fallback')).toBeInTheDocument();
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });
  });
});
