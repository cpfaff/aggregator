import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DatasetForm from '../DatasetForm';

jest.mock('../../../utils/apiUtils', () => ({
  // readJson stays real: it is the content-type guard the component now relies on.
  readJson: jest.requireActual('../../../utils/apiUtils').readJson,
  apiRequest: jest.fn(),
}));
jest.mock('../../ui/Toast', () => ({ showToast: jest.fn() }));

const { apiRequest } = require('../../../utils/apiUtils');

beforeEach(() => {
  jest.clearAllMocks();
});

describe('DatasetForm 422 degradation', () => {
  // FR-08 (REQ-FE-DEG-2): a FastAPI 422 array detail must surface the field
  // message, not pass the raw array to the error Alert.
  test('surfaces the field message on a 422 array detail', async () => {
    apiRequest.mockResolvedValue({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [
            {
              loc: ['body', 'title'],
              msg: 'Title must be less than 300 characters',
              type: 'string_too_long',
            },
          ],
        }),
    });

    render(<DatasetForm providerId={1} onClose={jest.fn()} onTokenExpired={jest.fn()} />);

    // Fill required fields with valid values so client validation passes and the
    // only matching text can come from the server 422.
    userEvent.type(screen.getByPlaceholderText('Enter dataset source'), 'src');
    userEvent.type(screen.getByPlaceholderText('Enter dataset title'), 'My title');
    userEvent.click(screen.getByRole('button', { name: /create dataset/i }));

    // RED (pre-fix): setError stores the truthy 422 array, passed to <Alert> as
    // a React child -> React 18 throws "Objects are not valid as a React child",
    // so the field message never appears.
    expect(
      await screen.findByText(/Title must be less than 300 characters/i),
    ).toBeInTheDocument();
  });
});
