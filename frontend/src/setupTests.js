// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// jsdom implements no window.matchMedia at all, and styles/theme.js reads
// prefers-color-scheme to pick a palette for users who have never toggled.
// Without this shim every suite that mounts App throws.
//
// Two load-bearing details:
//   1. Plain functions, NOT jest.fn(). CRA sets `resetMocks: true`, which
//      strips a jest.fn()'s implementation before every test and would leave
//      matchMedia() returning undefined.
//   2. The shim retains listeners and exposes `__emit`, so a test can drive a
//      simulated OS theme change rather than only assert the initial value.
if (typeof window.matchMedia !== 'function') {
  const listenersByQuery = new Map();

  window.matchMedia = (query) => {
    const listeners = listenersByQuery.get(query) || new Set();
    listenersByQuery.set(query, listeners);
    return {
      media: query,
      matches: false,
      onchange: null,
      addEventListener: (_event, handler) => listeners.add(handler),
      removeEventListener: (_event, handler) => listeners.delete(handler),
      addListener: (handler) => listeners.add(handler),
      removeListener: (handler) => listeners.delete(handler),
      dispatchEvent: () => false,
    };
  };

  // Test helper: window.matchMedia.__emit('(prefers-color-scheme: dark)', true)
  window.matchMedia.__emit = (query, matches) => {
    const listeners = listenersByQuery.get(query);
    if (listeners) listeners.forEach((handler) => handler({ matches, media: query }));
  };
}
