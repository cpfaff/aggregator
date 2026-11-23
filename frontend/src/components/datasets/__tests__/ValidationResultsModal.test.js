import React from 'react';
import { render, screen } from '@testing-library/react';
import ValidationResultsModal from '../ValidationResultsModal';

const buildResults = (duplicateUnitIds) => ({
  last_validated_at: '2026-11-01T10:00:00Z',
  archive_id: 'arch-1',
  validation_results: {
    summary: { data_quality: {} },
    validation_results: {
      schema_validation: [],
      custom_rules: { mandatory: [], recommended: [] },
      archive_checks: { duplicate_unit_ids: duplicateUnitIds },
    },
  },
});

const renderModal = (results) =>
  render(<ValidationResultsModal isOpen onClose={jest.fn()} validationResults={results} />);

describe('ValidationResultsModal duplicate UnitIDs', () => {
  test('renders duplicate UnitID section', () => {
    renderModal(
      buildResults({
        total_units: 5000,
        units_without_unit_id: 0,
        distinct_unit_ids: 3000,
        duplicated_unit_ids: 2124,
        units_not_indexable: 2124,
        examples: [{ unit_id: 'ZFMK-Ac-00987', units: 2 }],
      })
    );

    expect(screen.getByText('Duplicate UnitIDs')).toBeInTheDocument();
    expect(
      screen.getByText(
        '2124 UnitIDs are used by more than one unit; 2124 units cannot be indexed separately.'
      )
    ).toBeInTheDocument();
    expect(screen.getByText('UnitID')).toBeInTheDocument();
    expect(screen.getByText('Units')).toBeInTheDocument();
    const row = screen.getByText('ZFMK-Ac-00987').closest('tr');
    expect(row).toHaveTextContent('ZFMK-Ac-00987');
    expect(row).toHaveTextContent('2');
  });

  test('hides section when check errored', () => {
    renderModal(buildResults({ error: 'corrupt member' }));
    expect(screen.queryByText('Duplicate UnitIDs')).not.toBeInTheDocument();
  });

  test('hides section when check absent', () => {
    renderModal(buildResults(undefined));
    expect(screen.queryByText('Duplicate UnitIDs')).not.toBeInTheDocument();
  });
});
