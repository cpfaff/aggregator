import fs from 'fs';
import path from 'path';
import { formatCompactNumber } from '../numberFormat';

describe('formatCompactNumber — the one compact-number helper (REQ-SH-FE-3)', () => {
  test('formats millions with a M suffix', () => {
    expect(formatCompactNumber(1500000)).toBe('1.5M');
  });

  test('formats thousands with a K suffix', () => {
    expect(formatCompactNumber(2500)).toBe('2.5K');
  });

  test('returns values below 1000 unchanged (raw number, as the axes expect)', () => {
    expect(formatCompactNumber(999)).toBe(999);
    expect(formatCompactNumber(0)).toBe(0);
  });

  test('honours an explicit decimals option (integer-only axes pass decimals: 0)', () => {
    expect(formatCompactNumber(2400, { decimals: 0 })).toBe('2K');
    expect(formatCompactNumber(1000000, { decimals: 0 })).toBe('1M');
  });
});

describe('the K/M ladder is defined once and reused (REQ-SH-FE-3 static grep)', () => {
  const UI = path.join(__dirname, '..', '..', 'components', 'ui');
  const CHART_FILES = ['BarChart.js', 'TimeSeriesChart.js', 'MultiLineTimeSeriesChart.js'];

  test('no chart tick formatter inlines the >=1e6/>=1e3 division ladder', () => {
    for (const file of CHART_FILES) {
      const src = fs.readFileSync(path.join(UI, file), 'utf8');
      expect(src).not.toMatch(/1000000\)\.toFixed/);
      expect(src).not.toMatch(/1000\)\.toFixed/);
    }
  });

  test('the ladder lives in the shared numberFormat helper', () => {
    const src = fs.readFileSync(path.join(__dirname, '..', 'numberFormat.js'), 'utf8');
    expect(src).toMatch(/1000000/);
    expect(src).toMatch(/toFixed/);
  });
});
