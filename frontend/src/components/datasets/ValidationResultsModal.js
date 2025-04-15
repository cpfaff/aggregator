import React from 'react';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import Modal from '../ui/Modal';

// CSS styles to match the HTML template
const styles = {
  results: {
    margin: 0,
    padding: 0,
    backgroundColor: 'var(--card-bg)',
    maxHeight: 'calc(80vh - 150px)',
    overflowY: 'auto',
    marginRight: '-0.5rem',
    paddingRight: '0.5rem',
  },
  sectionTitle: {
    fontSize: '1.25rem',
    fontWeight: 600,
    marginTop: '1.5rem',
    marginBottom: '1rem',
    color: 'var(--text)',
  },
  subSectionTitle: {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginTop: '1.25rem',
    marginBottom: '0.75rem',
    color: 'var(--text)',
  },
  validationSummary: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
    margin: '1rem 0 1.5rem 0',
  },
  summaryItem: {
    padding: '1.25rem',
    backgroundColor: 'var(--card-bg)',
    borderRadius: '0.5rem',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    border: '1px solid var(--border)',
    margin: '0',
  },
  summaryLabel: {
    fontSize: '0.85rem',
    fontWeight: 500,
    color: 'var(--text-light)',
    marginBottom: '0.5rem',
  },
  summaryValue: {
    fontSize: '1.1rem',
    fontWeight: 600,
    color: 'var(--text)',
    marginTop: '0.25rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  fullWidth: {
    gridColumn: '1 / -1',
  },
  qualityScores: {
    display: 'flex',
    gap: '1rem',
    marginTop: '0.5rem',
    flexWrap: 'wrap',
  },
  qualityScore: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '0.5rem 1rem',
    borderRadius: '1rem',
    fontWeight: 500,
    fontSize: '0.875rem',
    whiteSpace: 'nowrap',
  },
  qualityScoreHigh: {
    backgroundColor: '#dcfce7',
    color: 'var(--success)',
  },
  qualityScoreMedium: {
    backgroundColor: '#ffedd5',
    color: 'var(--warning)',
  },
  qualityScoreLow: {
    backgroundColor: '#fee2e2',
    color: 'var(--error)',
  },
  schemaHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    margin: '0',
  },
  schemaVersionPill: {
    backgroundColor: 'transparent',
    color: 'var(--text)',
    padding: '0.15rem 0.5rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '0.75em',
    fontWeight: 500,
    letterSpacing: '0.03em',
    display: 'inline-flex',
    alignItems: 'center',
    marginLeft: '0.5rem',
    position: 'relative',
    top: '-1px',
  },
  errorCount: {
    color: 'var(--text-light)',
    marginBottom: '1rem',
    fontSize: '0.875rem',
  },
  ruleSection: {
    margin: '1rem 0 1.5rem 0',
  },
  rule: {
    padding: '1rem',
    margin: '0.75rem 0',
    backgroundColor: 'var(--card-bg)',
    borderLeft: '4px solid',
    borderTop: '1px solid var(--border)',
    borderRight: '1px solid var(--border)',
    borderBottom: '1px solid var(--border)',
    borderRadius: '0.25rem',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
  },
  rulePassed: {
    borderLeftColor: 'var(--success)',
  },
  ruleFailed: {
    borderLeftColor: 'var(--error)',
  },
  ruleWarning: {
    borderLeftColor: 'var(--warning)',
  },
  ruleName: {
    fontWeight: 600,
    marginBottom: '0.5rem',
    fontSize: '1rem',
  },
  ruleNamePassed: {
    color: 'var(--success)',
  },
  ruleNameFailed: {
    color: 'var(--error)',
  },
  ruleNameWarning: {
    color: 'var(--warning)',
  },
  ruleDetails: {
    marginTop: '0.5rem',
    marginLeft: '1.5rem',
    fontSize: '0.9rem',
    color: 'var(--text)',
  },
  rulePath: {
    wordBreak: 'break-all',
    overflowWrap: 'break-word',
    marginBottom: '0.5rem',
    color: 'var(--text)',
    fontFamily: 'monospace',
    fontSize: '0.85em',
  },
  ruleSummary: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
    marginBottom: '0.5rem',
  },
  ruleCategory: {
    margin: '0.25rem 0',
    marginLeft: '1rem',
    color: 'var(--text)',
    fontSize: '0.9em',
  },
  ruleMessage: {
    margin: '0.5rem 0',
    color: 'var(--text)',
  },
  ruleExamples: {
    marginTop: '0.5rem',
    fontSize: '0.9rem',
    color: 'var(--text-light)',
    backgroundColor: 'var(--subtle-bg)',
    padding: '0.75rem',
    borderRadius: '0.375rem',
    overflowWrap: 'break-word',
    wordBreak: 'break-all',
    border: '1px solid var(--border-light)',
  },
  exampleValueLabel: {
    fontWeight: 500,
    color: 'var(--text)',
    display: 'block',
    marginBottom: '0.25rem',
  },
  exampleValueList: {
    listStyleType: 'none',
    margin: '0.5rem 0 0 2rem',
    padding: 0,
    maxWidth: '100%',
  },
  exampleValueListItem: {
    padding: '0.25rem 0',
    border: 'none',
    position: 'relative',
    fontSize: '0.85em',
  },
  exampleValueListItemBefore: {
    content: '"•"',
    position: 'absolute',
    left: '-1rem',
    color: 'var(--text-light)',
  },
  affectedFiles: {
    marginTop: '0.5rem',
    color: 'var(--text)',
    fontSize: '0.85rem',
    fontStyle: 'italic',
  },
  messageContent: {
    fontSize: '0.9rem',
    color: 'var(--text)',
    padding: '0.5rem',
    backgroundColor: 'var(--subtle-bg)',
    borderRadius: '0.375rem',
    overflowWrap: 'break-word',
    wordBreak: 'break-all',
    border: '1px solid var(--border-light)',
  },
};

const ValidationResultsModal = ({ isOpen, onClose, validationResults }) => {
  
  if (!isOpen || !validationResults) return null;

  // Extract relevant data from validation results
  const summary = validationResults.validation_results?.summary || {};
  const schemaValidation = validationResults.validation_results?.validation_results?.schema_validation || [];
  const mandatoryRules = validationResults.validation_results?.validation_results?.custom_rules?.mandatory || [];
  const recommendedRules = validationResults.validation_results?.validation_results?.custom_rules?.recommended || [];

  // Calculate overall quality and validity
  const totalQuality = summary?.data_quality?.total_weighted_quality || 0;
  const isValid = validationResults.is_valid || false;
  const mandatoryPercentage = summary?.data_quality?.mandatory?.valid_percentage || 0;
  const recommendedPercentage = summary?.data_quality?.recommended?.valid_percentage || 0;

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    
    try {
      // Explicitly treat the input date as UTC if it doesn't have timezone info
      // This addresses the 2-hour difference issue
      let date;
      if (dateString.endsWith('Z') || dateString.includes('+')) {
        // Date already has timezone info
        date = new Date(dateString);
      } else {
        // Assume UTC and convert
        date = new Date(dateString + 'Z');
      }
      
      return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short' // Show timezone to make it clear
      });
    } catch (error) {
      console.error('Error formatting date:', error, dateString);
      return 'Invalid Date';
    }
  };

  // Get quality class based on score
  const getQualityClass = (score) => {
    if (score >= 90) return styles.qualityScoreHigh;
    if (score >= 70) return styles.qualityScoreMedium;
    return styles.qualityScoreLow;
  };

  // Format file list
  const formatFileList = (fileInfo) => {
    if (!fileInfo) return '';
    
    if (Array.isArray(fileInfo)) {
      const lastItem = fileInfo[fileInfo.length - 1];
      if (lastItem && lastItem.includes('more files')) {
        const displayFiles = fileInfo.slice(0, -1).map(f => {
          const parts = f.split('/');
          return parts[parts.length - 1];
        }).join(', ');
        return `${displayFiles} ${lastItem}`;
      }
      return fileInfo.map(f => {
        const parts = f.split('/');
        return parts[parts.length - 1];
      }).join(', ');
    }
    
    const displayFiles = fileInfo.examples || [];
    const text = displayFiles.map(f => {
      const parts = f.split('/');
      return parts[parts.length - 1];
    }).join(', ');
    
    if (fileInfo.remaining_count > 0) {
      return `${text} (... ${fileInfo.remaining_count} more)`;
    }
    return text;
  };

  // Handler for HTML content in messages
  const createMarkup = (htmlContent) => {
    return {__html: htmlContent};
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title="Validation Results"
      footer={
        <button 
          onClick={onClose}
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: 'var(--primary)',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '1rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'background-color 0.3s',
          }}
        >
          Close
        </button>
      }
    >
      <div style={styles.results}>
        {/* Validation Summary */}
        <div style={styles.validationSummary}>
          <div style={styles.summaryItem}>
            <p style={styles.summaryLabel}>Status</p>
            <h3 style={styles.summaryValue}>
              {isValid 
                ? <><CheckCircle size={18} style={{ color: 'var(--success)' }} /> Valid</> 
                : <><XCircle size={18} style={{ color: 'var(--error)' }} /> Invalid</>
              }
            </h3>
          </div>
          <div style={styles.summaryItem}>
            <p style={styles.summaryLabel}>Validated</p>
            <h3 style={styles.summaryValue}>{formatDate(validationResults.last_validated_at)}</h3>
          </div>
          <div style={styles.summaryItem}>
            <p style={styles.summaryLabel}>Archive ID</p>
            <h3 style={{...styles.summaryValue, wordBreak: 'break-all'}}>{validationResults.archive_id || 'N/A'}</h3>
          </div>
          <div style={{...styles.summaryItem, ...styles.fullWidth}}>
            <p style={styles.summaryLabel}>Quality Scores</p>
            <div style={styles.qualityScores}>
              <span style={{...styles.qualityScore, ...getQualityClass(mandatoryPercentage)}}>
                Mandatory Rules: {mandatoryPercentage.toFixed(1)}%
              </span>
              <span style={{...styles.qualityScore, ...getQualityClass(recommendedPercentage)}}>
                Recommended Rules: {recommendedPercentage.toFixed(1)}%
              </span>
              <span style={{...styles.qualityScore, ...getQualityClass(totalQuality)}}>
                Overall: {totalQuality.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Schema Validation */}
        {schemaValidation.length > 0 && (
          <>
            <div style={styles.schemaHeader}>
              <h2 style={styles.sectionTitle}>Schema Validation</h2>
              {summary.schema_version && (
                <span style={styles.schemaVersionPill}>v{summary.schema_version}</span>
              )}
            </div>
            <div style={styles.ruleSection}>
              <div style={styles.errorCount}>{schemaValidation.length} error{schemaValidation.length !== 1 ? 's' : ''} found</div>
              {schemaValidation.map((error, index) => (
                <div key={index} style={{...styles.rule, ...styles.ruleFailed}}>
                  <div style={{...styles.ruleName, ...styles.ruleNameFailed}}>
                    ✗ {error.heading || 'Schema Error'}
                  </div>
                  <div style={styles.ruleDetails}>
                    {error.details?.sample_paths && error.details.sample_paths.length > 0 && (
                      <div style={styles.rulePath}>Path: {error.details.sample_paths[0]}</div>
                    )}
                    <div style={styles.ruleSummary}>
                      Found {error.total_errors} occurrences
                      {error.details?.distinct_count ? ` with ${error.details.distinct_count} unique invalid values` : ''}
                    </div>

                    {/* Display the error message with heading in a prominent way */}
                    <div style={styles.ruleExamples}>
                      <div>
                        <span style={styles.exampleValueLabel}>✗ Message:</span>
                        <div style={styles.messageContent} dangerouslySetInnerHTML={createMarkup(error.message)} />
                      </div>
                    </div>

                    {/* Conditionally show examples only for non-length constraint errors */}
                    {(() => {
                      // Check if this is a length constraint error
                      const isLengthConstraint = 
                        error.details?.validation_type === "SCHEMAV_CVC_MINLENGTH_VALID" || 
                        error.details?.validation_type === "SCHEMAV_CVC_MAXLENGTH_VALID";
                      
                      // Only show examples for non-length constraint errors
                      if (!isLengthConstraint && error.details?.distinct_values && error.details.distinct_values.length > 0) {
                        return (
                          <div style={styles.ruleExamples}>
                            <div>
                              <span style={styles.exampleValueLabel}>✗ Invalid examples:</span>
                              <ul style={styles.exampleValueList}>
                                {error.details.distinct_values.map((value, i) => (
                                  <li key={i} style={styles.exampleValueListItem}>
                                    <span style={{
                                      content: '"•"',
                                      position: 'absolute',
                                      left: '-1rem',
                                      color: 'var(--text-light)',
                                    }}>•</span>
                                    {value}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        );
                      }
                      
                      return null;
                    })()}

                    {error.affected_files && (
                      <div style={styles.affectedFiles}>
                        Affected files: {formatFileList(error.affected_files)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Rule Validation */}
        {(mandatoryRules.length > 0 || recommendedRules.length > 0) && (
          <h2 style={styles.sectionTitle}>Rule Validation</h2>
        )}

        {/* Mandatory Rules */}
        {mandatoryRules.length > 0 && (
          <div style={styles.ruleSection}>
            <h3 style={styles.subSectionTitle}>Mandatory Rules</h3>
            {mandatoryRules.map((rule, index) => (
              <div key={index} style={{
                ...styles.rule,
                ...(rule.valid ? styles.rulePassed : styles.ruleFailed)
              }}>
                <div style={{
                  ...styles.ruleName,
                  ...(rule.valid ? styles.ruleNamePassed : styles.ruleNameFailed)
                }}>
                  {rule.valid ? '✓' : '✗'} {rule.name}
                </div>
                <div style={styles.ruleDetails}>
                  {rule.path && <div style={styles.rulePath}>Path: {rule.path}</div>}
                  {rule.message && (
                    <div 
                      style={styles.ruleMessage}
                      dangerouslySetInnerHTML={createMarkup(
                        Array.isArray(rule.message) ? rule.message.join('<br>') : rule.message
                      )}
                    />
                  )}
                  {rule.counts && (
                    <>
                      <div style={styles.ruleSummary}>
                        → {rule.counts.categories.valid.count}/{rule.counts.total} {rule.context_name || 'item'}s valid ({rule.counts.categories.valid.percentage.toFixed(1)}%)
                      </div>
                      {rule.counts.example_values && rule.counts.example_values.valid.length > 0 && (
                        <div style={styles.ruleExamples}>
                          <div>
                            <span style={styles.exampleValueLabel}>✓ Valid examples:</span>
                            <ul style={styles.exampleValueList}>
                              {rule.counts.example_values.valid.map((value, i) => (
                                <li key={i} style={styles.exampleValueListItem}>
                                  <span style={{
                                    content: '"•"',
                                    position: 'absolute',
                                    left: '-1rem',
                                    color: 'var(--text-light)',
                                  }}>•</span>
                                  {value}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}
                      {!rule.valid && (
                        <>
                          {rule.counts.categories.invalid.count > 0 && (
                            <>
                              <div style={styles.ruleCategory}>• Invalid: {rule.counts.categories.invalid.count} ({rule.counts.categories.invalid.percentage.toFixed(1)}%)</div>
                              {rule.counts.example_values && rule.counts.example_values.invalid.length > 0 && (
                                <div style={styles.ruleExamples}>
                                  <div>
                                    <span style={styles.exampleValueLabel}>✗ Invalid examples:</span>
                                    <ul style={styles.exampleValueList}>
                                      {rule.counts.example_values.invalid.map((value, i) => (
                                        <li key={i} style={styles.exampleValueListItem}>
                                          <span style={{
                                            content: '"•"',
                                            position: 'absolute',
                                            left: '-1rem',
                                            color: 'var(--text-light)',
                                          }}>•</span>
                                          {value}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              )}
                            </>
                          )}
                          {rule.counts.categories.missing.count > 0 && (
                            <div style={styles.ruleCategory}>
                              • Missing: {rule.counts.categories.missing.count} ({rule.counts.categories.missing.percentage.toFixed(1)}%)
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                  {rule.affected_files && (
                    <div style={styles.affectedFiles}>
                      Affected files: {formatFileList(rule.affected_files)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Recommended Rules */}
        {recommendedRules.length > 0 && (
          <div style={styles.ruleSection}>
            <h3 style={styles.subSectionTitle}>Recommended Rules</h3>
            {recommendedRules.map((rule, index) => (
              <div key={index} style={{
                ...styles.rule,
                ...(rule.valid ? styles.rulePassed : styles.ruleWarning)
              }}>
                <div style={{
                  ...styles.ruleName,
                  ...(rule.valid ? styles.ruleNamePassed : styles.ruleNameWarning)
                }}>
                  {rule.valid ? '✓' : '!'} {rule.name}
                </div>
                <div style={styles.ruleDetails}>
                  {rule.path && <div style={styles.rulePath}>Path: {rule.path}</div>}
                  {rule.message && (
                    <div 
                      style={styles.ruleMessage}
                      dangerouslySetInnerHTML={createMarkup(
                        Array.isArray(rule.message) ? rule.message.join('<br>') : rule.message
                      )}
                    />
                  )}
                  {rule.counts && (
                    <>
                      <div style={styles.ruleSummary}>
                        → {rule.counts.categories.valid.count}/{rule.counts.total} {rule.context_name || 'item'}s valid ({rule.counts.categories.valid.percentage.toFixed(1)}%)
                      </div>
                      {rule.counts.example_values && rule.counts.example_values.valid.length > 0 && (
                        <div style={styles.ruleExamples}>
                          <div>
                            <span style={styles.exampleValueLabel}>✓ Valid examples:</span>
                            <ul style={styles.exampleValueList}>
                              {rule.counts.example_values.valid.map((value, i) => (
                                <li key={i} style={styles.exampleValueListItem}>
                                  <span style={{
                                    content: '"•"',
                                    position: 'absolute',
                                    left: '-1rem',
                                    color: 'var(--text-light)',
                                  }}>•</span>
                                  {value}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}
                      {!rule.valid && (
                        <>
                          {rule.counts.categories.invalid.count > 0 && (
                            <>
                              <div style={styles.ruleCategory}>• Invalid: {rule.counts.categories.invalid.count} ({rule.counts.categories.invalid.percentage.toFixed(1)}%)</div>
                              {rule.counts.example_values && rule.counts.example_values.invalid.length > 0 && (
                                <div style={styles.ruleExamples}>
                                  <div>
                                    <span style={styles.exampleValueLabel}>✗ Invalid examples:</span>
                                    <ul style={styles.exampleValueList}>
                                      {rule.counts.example_values.invalid.map((value, i) => (
                                        <li key={i} style={styles.exampleValueListItem}>
                                          <span style={{
                                            content: '"•"',
                                            position: 'absolute',
                                            left: '-1rem',
                                            color: 'var(--text-light)',
                                          }}>•</span>
                                          {value}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              )}
                            </>
                          )}
                          {rule.counts.categories.missing.count > 0 && (
                            <div style={styles.ruleCategory}>
                              • Missing: {rule.counts.categories.missing.count} ({rule.counts.categories.missing.percentage.toFixed(1)}%)
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                  {rule.affected_files && (
                    <div style={styles.affectedFiles}>
                      Affected files: {formatFileList(rule.affected_files)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
};

// Helper function to determine color based on quality score
const getQualityColor = (score) => {
  if (score >= 90) return 'var(--success)';
  if (score >= 70) return 'var(--warning)';
  return 'var(--error)';
};

export default ValidationResultsModal;
