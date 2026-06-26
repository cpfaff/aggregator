import { formatChartDate } from '../dateUtils';

describe('formatChartDate — one locale-pinned chart-axis date helper (REQ-SH-FE-4/5)', () => {
  // A locally-constructed date avoids ISO-string UTC-parse timezone shifts, so the
  // assertion turns purely on the locale's date order — which is the point.
  const jan15 = new Date(2024, 0, 15);

  test('pins en-US (month-first) by default rather than the runtime locale (REQ-SH-FE-5)', () => {
    expect(formatChartDate(jan15)).toBe('1/15/2024');
  });

  test('accepts an explicit locale override (en-GB is day-first)', () => {
    expect(formatChartDate(jan15, 'en-GB')).toBe('15/01/2024');
  });

  test('accepts an ISO date string as input', () => {
    expect(typeof formatChartDate('2024-01-15')).toBe('string');
  });
});
