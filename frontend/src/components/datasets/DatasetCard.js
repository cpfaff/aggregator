import React, { useState, useEffect, useRef } from 'react';
import { Database, ExternalLink, FileText, Globe, Edit, Trash2, CheckCircle, XCircle, AlertCircle, HelpCircle, RefreshCw, Dna } from 'lucide-react';
import useSWR from 'swr';
import { useAuth } from '../auth/AuthContext';
import axios from 'axios';
import ValidationResultsModal from './ValidationResultsModal';
import { authStatsApi } from '../../utils/statisticsApi';
import { REQUEST_TIMEOUT_MS } from '../../utils/apiUtils';
import Skeleton from '../ui/Skeleton';

// Reserved heights that hold the harvest-status and biological-units regions at
// a fixed size while their slow index queries load, so resolving the data causes
// zero layout shift (CLS = 0). Each is sized to its region's worst-case loaded
// content: the harvest badge can wrap to two lines at the ~320px minimum card
// width (see the datasets grid), while the bio-units line is always single-line.
// Both are in rem, so they scale with the root font like the text they reserve.
// The harvest value carries slack above a two-line badge (safe up to a ~1.5
// line-height) since jsdom cannot measure layout; the real CLS = 0 is confirmed
// by the Playwright getBoundingClientRect() checkpoint. The SAME value is applied
// in the loading and loaded renders of each region.
const HARVEST_REGION_MIN_HEIGHT = '2.5rem';
const BIO_UNITS_REGION_MIN_HEIGHT = '1.25rem';
// Reserved height for the validation section's content area (status line + the
// action-button row). The whole validation section pops in only after the
// validation-status query resolves; without a reserve it shoves the card — and,
// because sibling cards share a grid row, the entire row — down when it lands
// (the "wave"). Pinning the content area (~67.5px measured; buttons never wrap
// at realistic card widths) keeps skeleton and result the same height.
const VALIDATION_CONTENT_MIN_HEIGHT = '4.25rem';

// SWR fetcher for the harvest-status endpoint. Reuses the already-imported axios
// (so the existing jest.mock('axios') intercepts it) and the same token idiom as
// the Validation fetch.
const harvestStatusFetcher = async (url) => {
  const token = localStorage.getItem('token');
  const res = await axios.get(url, {
    headers: { Authorization: `Bearer ${token}` },
    timeout: REQUEST_TIMEOUT_MS,
  });
  return res.data;
};

const DatasetCard = ({ dataset, onEdit, onDelete }) => {
  const { currentUser, handleTokenExpiration } = useAuth();
  const [validationStatus, setValidationStatus] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [datasetStats, setDatasetStats] = useState(null);
  // Backpressure guard (FR-05, REQ-FE-POLL-1): true while a validation-status
  // request is in flight, so a 3s poll tick cannot stack a second request on a
  // slow/hung backend.
  const inFlightRef = useRef(false);
  // Abort controller for the validation requests (FR-06, REQ-FE-POLL-2): aborted
  // on unmount so an in-flight request is cancelled and no setState runs after.
  const abortControllerRef = useRef(null);

  // Debug logging
  console.log('Dataset Provider ID:', dataset.provider_id);
  console.log('Current User Roles:', currentUser?.provider_roles);
  console.log('Is Global Admin:', currentUser?.is_global_admin);

  // Check if user is global admin or provider admin
  // Convert provider_id to string for comparison since IDs from API might be numbers
  const canDelete = currentUser?.is_global_admin ||
                   (currentUser?.provider_roles &&
                    currentUser.provider_roles[String(dataset.provider_id)] === 'admin');

  // Debug the result
  console.log('Can Delete:', canDelete);

  // --- Harvest-status badge (SWR) ---
  // Only the STRICT boolean false means "definitely staged, skip fetch"; an
  // undefined/null prop must still fetch so the server stays the source of truth.
  const isStaged = dataset?.isHarvestReady === false;
  // A null SWR key makes SWR NOT fetch — this makes `staged` fetch-free and also
  // guards the missing-id case.
  const harvestKey = (dataset?.id && !isStaged)
    ? `${process.env.REACT_APP_API_BASE_URL || ''}/api/v1/datasets/${dataset.id}/harvest-status`
    : null;
  const { data: harvestData, error: harvestError } = useSWR(harvestKey, harvestStatusFetcher);

  // Derive the effective status (pure; no extra state). unknown/error -> unavailable.
  const harvestEffectiveStatus = isStaged
    ? 'staged'
    : (harvestError || harvestData?.harvest_status === 'unknown')
      ? 'unknown'
      : (harvestData?.harvest_status ?? 'loading');

  // Validation section reservation (CLS): a dataset that has archives will get a
  // validation result, so reserve the section's space with a skeleton while the
  // validation-status request is in flight (validationStatus === null) instead
  // of letting the whole section pop in and shove the card (and its grid row)
  // down when it lands. archive presence is a reliable predictor of
  // has_latest_archive; the slot collapses only in the rare case a dataset with
  // archives resolves to no latest archive.
  const hasArchives = Array.isArray(dataset?.xmlArchives) && dataset.xmlArchives.length > 0;
  const reserveValidation = validationStatus === null && hasArchives;
  const validationSlotVisible = reserveValidation || (validationStatus && validationStatus.has_latest_archive);

  // Fetch validation status and dataset stats when component mounts
  useEffect(() => {
    const controller = new AbortController();
    abortControllerRef.current = controller;

    if (dataset && dataset.id) {
      fetchValidationStatus();
      fetchDatasetStats();
    }

    // On unmount: abort the in-flight validation request and clear the poll.
    // Release the overlap guard too, so a remount (React StrictMode's dev
    // double-mount) is not blocked by the aborted request's lingering flag.
    return () => {
      controller.abort();
      inFlightRef.current = false;
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset]);

  // Function to fetch dataset statistics (for biological units count)
  const fetchDatasetStats = async () => {
    try {
      const stats = await authStatsApi.getDatasetStats(dataset.id, handleTokenExpiration);
      setDatasetStats(stats);
    } catch (error) {
      console.error('Error fetching dataset stats:', error);
      // Don't surface the error - stats are optional. But settle the state off
      // null (the "still loading" sentinel) so the biological-units region
      // leaves its loading skeleton and shows an empty reserved box instead of
      // spinning forever on a failed/aborted stats fetch.
      setDatasetStats((prev) => prev ?? {});
    }
  };

  // Function to fetch validation status
  const fetchValidationStatus = async () => {
    // Overlap guard: skip this tick if a request is still in flight.
    if (inFlightRef.current) {
      return;
    }
    inFlightRef.current = true;
    // Capture THIS request's signal up front so the catch/finally test the
    // controller that owns this request — not a newer one a remount installed
    // into the ref (which would mis-attribute this request's abort).
    const signal = abortControllerRef.current?.signal;
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${process.env.REACT_APP_API_BASE_URL || ''}/api/v1/validators/datasets/${dataset.id}/validation-status`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          timeout: REQUEST_TIMEOUT_MS,
          signal,
        }
      );

      // Aborted mid-flight (unmount): do not touch state.
      if (signal?.aborted) {
        return;
      }

      const newStatus = response.data;
      setValidationStatus(newStatus);

      // If the status is no longer running or pending, ensure we're not in validating state
      if (newStatus.validation_status !== 'running' && newStatus.validation_status !== 'pending') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        setIsValidating(false);
      }
    } catch (error) {
      // This request was aborted (unmount/remount): not a real failure — bail
      // without logging or clearing state a newer owner may now hold.
      if (signal?.aborted) {
        return;
      }
      console.error('Error fetching validation status:', error);

      // If there's an error, stop polling and validating
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
      setIsValidating(false);
    } finally {
      // Release the overlap guard once the request settles (but not for a request
      // aborted by unmount/remount — a newer owner may hold the guard now). A
      // never-resolving request never reaches here, so its guard stays set.
      if (!signal?.aborted) {
        inFlightRef.current = false;
      }
    }
  };

  // Update the useEffect to also react to validation status changes
  useEffect(() => {
    // If validation status changes and is not running/pending, make sure isValidating is false
    if (validationStatus &&
        validationStatus.validation_status !== 'running' &&
        validationStatus.validation_status !== 'pending') {
      setIsValidating(false);
    }
  }, [validationStatus]);

  // Add a safety timeout to reset validation state if it gets stuck
  useEffect(() => {
    // If we've been validating for more than 45 seconds, force reset state
    let validationTimeout;

    if (isValidating) {
      console.log('Starting validation safety timeout...');
      validationTimeout = setTimeout(() => {
        console.log('Validation timeout reached, resetting state');
        setIsValidating(false);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        // Force fetch latest status
        fetchValidationStatus();
      }, 45000); // 45 second timeout
    }

    return () => {
      if (validationTimeout) {
        clearTimeout(validationTimeout);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isValidating]);

  // Function to trigger validation
  const triggerValidation = async (e) => {
    e.stopPropagation();

    // Prevent multiple clicks
    if (isValidating) return;

    setIsValidating(true);

    // Clear any existing polling
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }

    try {
      const token = localStorage.getItem('token');
      // Idempotency key captured once per validation intent (FR-09,
      // REQ-FE-CLIENT-4) so a retry or double-click cannot enqueue duplicate
      // validation jobs; the backend deduplicates on this key.
      const idempotencyKey =
        typeof crypto !== 'undefined' && crypto.randomUUID
          ? crypto.randomUUID()
          : `${dataset.id}:validate:${Date.now()}`;
      const response = await axios.post(
        `${process.env.REACT_APP_API_BASE_URL || ''}/api/v1/validators/datasets/${dataset.id}/validate`,
        { force: true },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Idempotency-Key': idempotencyKey,
          },
          timeout: REQUEST_TIMEOUT_MS,
        }
      );

      // Check if response indicates an immediate error
      if (response.data && response.data.status === 'error') {
        console.error('Validation API returned error:', response.data.message);
        setIsValidating(false);
        return;
      }

      // Immediately fetch status to update UI
      await fetchValidationStatus();

      // Set up polling to check status every 3 seconds
      const interval = setInterval(fetchValidationStatus, 3000);
      setPollingInterval(interval);
    } catch (error) {
      console.error('Error triggering validation:', error);
      setIsValidating(false);

      // Show an alert if there was an error (optional)
      alert('Error triggering validation. Please try again later.');
    }
  };

  // Function to open validation modal
  const openValidationModal = (e) => {
    e.stopPropagation();
    setShowValidationModal(true);
  };

  // Handle delete click
  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete(dataset);
  };

  // Handle edit click
  const handleEditClick = (e) => {
    e.stopPropagation();
    onEdit(dataset);
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        border: '1px solid var(--border)',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        transition: 'box-shadow 0.2s',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: 'relative',
        cursor: 'default',
      }}
      className="dataset-card"
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.05)';
      }}
      role="article"
      aria-label={`Dataset: ${dataset.title}`}
    >
      {/* HEADER AREA */}
      <div style={{
        padding: '1.25rem 1.25rem 0.75rem',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        {/* Dataset badge */}
        <div>
          <span style={{
            backgroundColor: 'var(--subtle-bg)',
            padding: '0.25rem 0.625rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: 500,
            color: 'var(--text-light)',
            display: 'inline-block',
          }}>
            Dataset
          </span>
        </div>

        {/* Dataset ID badge if available */}
        {dataset.id && (
          <span style={{
            backgroundColor: 'var(--subtle-bg)',
            padding: '0.25rem 0.625rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: 700,
            color: 'var(--text-light)',
            display: 'inline-block',
          }}
          aria-label={`Dataset ID: ${dataset.id}`}
          >
            #{dataset.id}
          </span>
        )}
      </div>

      {/* BODY CONTENT */}
      <div style={{
        padding: '0.75rem 1.25rem 1.25rem',
        flexGrow: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Title with better prominence */}
        <h3 style={{
          fontSize: '1.125rem',
          fontWeight: 600,
          margin: '0 0 0.5rem 0',
          paddingLeft: '0.25rem',
          color: 'var(--text)',
          lineHeight: '1.4',
          display: '-webkit-box',
          WebkitLineClamp: '3',
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
        title={dataset.title} // Adds tooltip on hover for long titles
        >
          {dataset.title}
        </h3>

        {/* Last Updated timestamp - subtle styling below title */}
        {dataset.updated_at && (
          <div style={{
            paddingLeft: '0.25rem',
            marginBottom: '1rem',
          }}>
            <span style={{
              fontSize: '0.75rem',
              color: 'var(--text-light)',
              opacity: 0.7,
            }}>
              Last updated: {new Date(dataset.updated_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
              })}
            </span>
          </div>
        )}

        {/* Main content sections */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1.25rem',
        }}>
          {/* Stats section with flatter design */}
          <div>
            {/* Stats content with accent bar */}
            <div style={{ position: 'relative' }}>
              {/* Vertical border for the section */}
              <div style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: '0.25rem',
                width: '1.5px',
                backgroundColor: 'var(--text-light)',
                opacity: 0.4,
                zIndex: 0
              }}></div>

              <div style={{
                fontSize: '0.8125rem',
                textTransform: 'uppercase',
                fontWeight: 600,
                color: 'var(--text-light)',
                marginBottom: '0.75rem',
                letterSpacing: '0.025em',
                display: 'flex',
                alignItems: 'center',
                paddingLeft: '0.75rem',
                position: 'relative',
                zIndex: 1
              }}>
                Stats
              </div>

              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
                paddingLeft: '1.5rem',
                position: 'relative',
                zIndex: 1
              }}>
                {/* Archives */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                }}>
                  <FileText
                    size={15}
                    style={{
                      color: 'var(--primary)',
                      marginRight: '0.75rem',
                      flexShrink: 0
                    }}
                  />
                  <span style={{
                    fontSize: '0.8125rem',
                    color: 'var(--text)',
                    display: 'flex',
                    alignItems: 'center',
                  }}>
                    <span style={{
                      fontWeight: 600,
                      color: (Array.isArray(dataset.xmlArchives) && dataset.xmlArchives.length > 0) ? 'var(--text)' : 'var(--text-light)',
                      marginRight: '0.375rem'
                    }}>
                      {Array.isArray(dataset.xmlArchives) ? dataset.xmlArchives.length : 0}
                    </span>
                    {(Array.isArray(dataset.xmlArchives) && dataset.xmlArchives.length === 1) ? 'archive' : 'archives'}
                  </span>
                </div>

                {/* Useful Links */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                }}>
                  <Globe
                    size={15}
                    style={{
                      color: 'var(--primary)',
                      marginRight: '0.75rem',
                      flexShrink: 0
                    }}
                  />
                  <span style={{
                    fontSize: '0.8125rem',
                    color: 'var(--text)',
                    display: 'flex',
                    alignItems: 'center',
                  }}>
                    <span style={{
                      fontWeight: 600,
                      color: (Array.isArray(dataset.usefulLinks) && dataset.usefulLinks.length > 0) ? 'var(--text)' : 'var(--text-light)',
                      marginRight: '0.375rem'
                    }}>
                      {Array.isArray(dataset.usefulLinks) ? dataset.usefulLinks.length : 0}
                    </span>
                    {(Array.isArray(dataset.usefulLinks) && dataset.usefulLinks.length === 1) ? 'link' : 'links'}
                  </span>
                </div>

                {/* Biological Units — reserved height so the datasetStats fetch
                    lands without shifting the card (CLS = 0). While the stats are
                    in flight (datasetStats === null) a Skeleton fills the reserved
                    space; once settled the unit line renders, or (when the dataset
                    reports no unit count) the reserved box stays empty. */}
                <div
                  data-testid="bio-units-region"
                  style={{
                    minHeight: BIO_UNITS_REGION_MIN_HEIGHT,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  {datasetStats === null ? (
                    <Skeleton width="55%" height="0.85rem" ariaLabel="Loading biological units" />
                  ) : (datasetStats.unit_count !== undefined && datasetStats.unit_count !== null) ? (
                    <>
                      <Dna
                        size={15}
                        style={{
                          color: 'var(--primary)',
                          marginRight: '0.75rem',
                          flexShrink: 0
                        }}
                      />
                      <span style={{
                        fontSize: '0.8125rem',
                        color: 'var(--text)',
                        display: 'flex',
                        alignItems: 'center',
                      }}>
                        <span style={{
                          fontWeight: 600,
                          color: datasetStats.unit_count > 0 ? 'var(--text)' : 'var(--text-light)',
                          marginRight: '0.375rem'
                        }}>
                          {datasetStats.unit_count.toLocaleString()}
                        </span>
                        {datasetStats.unit_count === 1 ? 'biological unit' : 'biological units'}
                      </span>
                    </>
                  ) : null}
                </div>

                {/* Sample count (if exists in the data) */}
                {dataset.sampleCount !== undefined && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                  }}>
                    <Database
                      size={15}
                      style={{
                        color: 'var(--primary)',
                        marginRight: '0.75rem',
                        flexShrink: 0
                      }}
                    />
                    <span style={{
                      fontSize: '0.8125rem',
                      color: 'var(--text)',
                      display: 'flex',
                      alignItems: 'center',
                    }}>
                      <span style={{
                        fontWeight: 600,
                        color: dataset.sampleCount > 0 ? 'var(--text)' : 'var(--text-light)',
                        marginRight: '0.375rem'
                      }}>
                        {dataset.sampleCount?.toLocaleString() || 0}
                      </span>
                      samples
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* VALIDATION section - dedicated section for all validation UI.
              Rendered when the dataset has archives (reserve, with a skeleton
              while validation-status loads) or once a latest-archive result has
              arrived, so the section does not pop in and shift the card. */}
          {validationSlotVisible && (
            <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '1rem', position: 'relative' }}>
              {/* Vertical border for the section */}
              <div style={{
                position: 'absolute',
                top: '1rem',
                bottom: 0,
                left: '0.25rem',
                width: '1.5px',
                backgroundColor: 'var(--text-light)',
                opacity: 0.4,
                zIndex: 0
              }}></div>

              <div style={{
                fontSize: '0.8125rem',
                textTransform: 'uppercase',
                fontWeight: 600,
                color: 'var(--text-light)',
                marginBottom: '0.75rem',
                letterSpacing: '0.025em',
                display: 'flex',
                alignItems: 'center',
                paddingLeft: '0.75rem',
                position: 'relative',
                zIndex: 1
              }}>
                Validation
              </div>

              <div
                data-testid="validation-region"
                style={{
                  paddingLeft: '1.5rem',
                  minHeight: VALIDATION_CONTENT_MIN_HEIGHT,
                  position: 'relative',
                  zIndex: 1
                }}
              >
                {reserveValidation ? (
                  <Skeleton
                    count={2}
                    width="65%"
                    height="1.25rem"
                    gap="0.75rem"
                    ariaLabel="Loading validation status"
                  />
                ) : (
                <>
                {/* Validation Status - shows previous result during re-validation for stability */}
                {(() => {
                  const hasPreviousResult = validationStatus.is_valid !== undefined && validationStatus.is_valid !== null;

                  // Determine what to display: previous result if available, otherwise current status
                  const showValid = hasPreviousResult ? validationStatus.is_valid : false;

                  return (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: '1rem',
                    }}>
                      {hasPreviousResult || validationStatus.validation_status === 'completed' ? (
                        showValid ? (
                          <CheckCircle
                            size={15}
                            style={{
                              color: 'var(--success)',
                              marginRight: '0.75rem',
                              flexShrink: 0
                            }}
                          />
                        ) : (
                          <XCircle
                            size={15}
                            style={{
                              color: 'var(--error)',
                              marginRight: '0.75rem',
                              flexShrink: 0
                            }}
                          />
                        )
                      ) : (
                        <AlertCircle
                          size={15}
                          style={{
                            color: 'var(--text-light)',
                            marginRight: '0.75rem',
                            flexShrink: 0
                          }}
                        />
                      )}
                      <span style={{
                        fontSize: '0.8125rem',
                        color: 'var(--text)',
                        display: 'flex',
                        alignItems: 'center',
                      }}>
                        <span style={{
                          fontWeight: 600,
                          color: hasPreviousResult || validationStatus.validation_status === 'completed'
                            ? (showValid ? 'var(--success)' : 'var(--error)')
                            : 'var(--text-light)',
                        }}>
                          {hasPreviousResult || validationStatus.validation_status === 'completed'
                            ? (showValid
                              ? `Valid (${validationStatus.quality_score?.toFixed(1)}%)`
                              : 'Invalid')
                            : 'Not validated'}
                        </span>
                      </span>
                    </div>
                  );
                })()}

                {/* Action buttons - both always visible, disabled during validation */}
                {(() => {
                  const isRunning = isValidating || validationStatus.validation_status === 'pending' || validationStatus.validation_status === 'running';
                  const hasPreviousResult = validationStatus.is_valid !== undefined && validationStatus.is_valid !== null;
                  const showViewDetails = hasPreviousResult || validationStatus.validation_status === 'completed';

                  return (
                    <div style={{
                      display: 'flex',
                      gap: '0.5rem',
                      flexWrap: 'wrap',
                    }}>
                      <button
                        onClick={triggerValidation}
                        disabled={isRunning}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.375rem',
                          padding: '0.375rem 0.75rem',
                          border: '1.5px solid var(--primary)',
                          borderRadius: '0.5rem',
                          backgroundColor: 'var(--card-bg)',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          color: 'var(--primary)',
                          cursor: isRunning ? 'not-allowed' : 'pointer',
                          transition: 'all 150ms ease',
                          opacity: isRunning ? 0.5 : 1,
                        }}
                        onMouseEnter={(e) => {
                          if (!e.currentTarget.disabled) {
                            e.currentTarget.style.backgroundColor = 'var(--subtle-bg)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'var(--card-bg)';
                        }}
                        aria-label={isRunning ? 'Re-validating dataset...' : 'Re-validate dataset'}
                      >
                        <RefreshCw
                          size={14}
                          style={{
                            animation: isRunning ? 'spin 2s linear infinite' : 'none'
                          }}
                        />
                        Re-validate
                      </button>
                      {showViewDetails && (
                        <button
                          onClick={openValidationModal}
                          disabled={isRunning}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.375rem',
                            padding: '0.375rem 0.75rem',
                            border: '1.5px solid var(--primary)',
                            borderRadius: '0.5rem',
                            backgroundColor: 'var(--card-bg)',
                            fontSize: '0.75rem',
                            fontWeight: 500,
                            color: 'var(--primary)',
                            cursor: isRunning ? 'not-allowed' : 'pointer',
                            transition: 'all 150ms ease',
                            opacity: isRunning ? 0.5 : 1,
                          }}
                          onMouseEnter={(e) => {
                            if (!isRunning) {
                              e.currentTarget.style.backgroundColor = 'var(--subtle-bg)';
                            }
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.backgroundColor = 'var(--card-bg)';
                          }}
                        >
                          <FileText size={14} />
                          View Details
                        </button>
                      )}
                    </div>
                  );
                })()}
                </>
                )}
              </div>
            </div>
          )}

          {/* HARVEST section - peer of Validation; SWR-driven harvest-status badge */}
          <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '1rem', position: 'relative' }}>
            {/* Vertical border for the section */}
            <div style={{
              position: 'absolute',
              top: '1rem',
              bottom: 0,
              left: '0.25rem',
              width: '1.5px',
              backgroundColor: 'var(--text-light)',
              opacity: 0.4,
              zIndex: 0
            }}></div>

            <div style={{
              fontSize: '0.8125rem',
              textTransform: 'uppercase',
              fontWeight: 600,
              color: 'var(--text-light)',
              marginBottom: '0.75rem',
              letterSpacing: '0.025em',
              display: 'flex',
              alignItems: 'center',
              paddingLeft: '0.75rem',
              position: 'relative',
              zIndex: 1
            }}>
              Harvest
            </div>

            <div style={{
              paddingLeft: '1.5rem',
              position: 'relative',
              zIndex: 1
            }}>
              {/* Reserved height so the harvest badge lands without shifting the
                  card (CLS = 0). While the status is loading a Skeleton fills the
                  reserved space (superseding the "Checking index…" text); once it
                  resolves the status row renders. The min-height covers the
                  worst-case two-line badge at the ~320px minimum card width. */}
              <div
                data-testid="harvest-region"
                style={{
                  minHeight: HARVEST_REGION_MIN_HEIGHT,
                  display: 'flex',
                  // Anchor the badge/skeleton to the top so the loaded status keeps
                  // its current vertical position; the reserved slack sits below.
                  alignItems: 'flex-start',
                }}
              >
                {harvestEffectiveStatus === 'loading' ? (
                  <Skeleton width="70%" height="0.85rem" ariaLabel="Loading harvest status" />
                ) : (() => {
                // M = units present in the index; N = expected unit count (snapshot).
                const m = harvestData?.units_in_index;
                const n = harvestData?.units_expected;
                const lastSeen = harvestData?.last_seen_in_index_at;
                // Guard new Date(null/undefined) -> only format when truthy.
                // Pin 'en-US' so the badge copy is locale-stable ("Jun 20, 2026"),
                // matching the frozen contract copy regardless of runtime locale.
                const lastSeenText = lastSeen
                  ? ` · last seen ${new Date(lastSeen).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}`
                  : '';
                const hasN = (n !== null && n !== undefined);
                // partial visible+label use "M of N units".
                const partialUnits = `${m} of ${n} units`;
                // in_index: visible text is "N units" when N known (M==N), else "M units"
                // (never "M of null"); the aria-label keeps the "M of N" form when N known.
                const inIndexText = hasN ? `${n} units` : `${m} units`;
                const inIndexLabel = hasN ? `${m} of ${n} units` : `${m} units`;

                // amber has no CSS token; literal per ticket for partial/not-yet states.
                const AMBER = '#d97706';

                let Icon = AlertCircle;
                let color = 'var(--text-light)';
                let text;
                let label;
                switch (harvestEffectiveStatus) {
                  case 'in_index':
                    Icon = CheckCircle;
                    color = 'var(--success)';
                    text = `In index · ${inIndexText}${lastSeenText}`;
                    label = `Harvest status: in index, ${inIndexLabel}`;
                    break;
                  case 'partial':
                    Icon = AlertCircle;
                    color = AMBER;
                    text = `Partially in index · ${partialUnits}${lastSeenText}`;
                    label = `Harvest status: partially in index, ${partialUnits}`;
                    break;
                  case 'not_in_index':
                    Icon = AlertCircle;
                    color = AMBER;
                    text = 'Not yet in index';
                    label = 'Harvest status: not yet in index';
                    break;
                  case 'staged':
                    Icon = AlertCircle;
                    color = 'var(--text-light)';
                    text = 'Staged · not in harvester feed';
                    label = 'Harvest status: staged';
                    break;
                  case 'loading':
                    Icon = AlertCircle;
                    color = 'var(--text-light)';
                    text = 'Checking index…';
                    label = 'Harvest status: checking index';
                    break;
                  case 'unknown':
                  default:
                    Icon = HelpCircle;
                    color = 'var(--text-light)';
                    text = 'Status unavailable';
                    label = 'Harvest status: unavailable';
                    break;
                }

                return (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                    }}
                    aria-label={label}
                  >
                    <Icon
                      size={15}
                      style={{
                        color,
                        marginRight: '0.75rem',
                        flexShrink: 0,
                      }}
                    />
                    <span style={{
                      fontSize: '0.8125rem',
                      fontWeight: 600,
                      color,
                    }}>
                      {text}
                    </span>
                  </div>
                );
                })()}
              </div>
            </div>
          </div>

          {/* Links section with flatter design */}
          <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '1rem', position: 'relative' }}>
            {/* Vertical border for the section */}
            <div style={{
              position: 'absolute',
              top: '1rem', /* Account for the padding-top */
              bottom: 0,
              left: '0.25rem',
              width: '1.5px',
              backgroundColor: 'var(--text-light)',
              opacity: 0.4,
              zIndex: 0
            }}></div>

            <div style={{
              fontSize: '0.8125rem',
              textTransform: 'uppercase',
              fontWeight: 600,
              color: 'var(--text-light)',
              marginBottom: '0.75rem',
              letterSpacing: '0.025em',
              display: 'flex',
              alignItems: 'center',
              paddingLeft: '0.75rem',
              position: 'relative',
              zIndex: 1
            }}>
              Links
            </div>

            <div style={{
              paddingLeft: '1.5rem',
              position: 'relative',
              zIndex: 1
            }}>
              {/* Landing Page */}
              {dataset.landingPageUrl ? (
                <a
                  href={dataset.landingPageUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    fontSize: '0.8125rem',
                    color: 'var(--text)',
                    textDecoration: 'none',
                    fontWeight: 500,
                  }}
                  onClick={(e) => e.stopPropagation()}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--text)';
                  }}
                >
                  <Globe
                    size={15}
                    style={{
                      marginRight: '0.75rem',
                      flexShrink: 0,
                      color: 'var(--primary)'
                    }}
                  />
                  Landing page
                  <ExternalLink size={11} style={{ marginLeft: '0.25rem', opacity: 0.5 }} />
                </a>
              ) : (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  fontSize: '0.8125rem',
                  color: 'var(--text-light)',
                }}>
                  <Globe
                    size={15}
                    style={{
                      marginRight: '0.75rem',
                      flexShrink: 0
                    }}
                  />
                  <span style={{ fontStyle: 'italic' }}>
                    No landing page available
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ACTIONS AREA */}
      <div style={{
        display: 'flex',
        padding: '0.75rem 1.25rem',
        gap: '0.625rem',
        height: 'auto',
        minHeight: '52px',
        flexShrink: 0,
        boxSizing: 'border-box',
        borderTop: '1px solid var(--border)',
        backgroundColor: 'var(--card-bg)',
        justifyContent: 'flex-end',
      }}>
        {/* Action buttons on the right */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={handleEditClick}
            style={{
              width: '44px',
              height: '44px',
              backgroundColor: 'var(--subtle-bg)',
              color: 'var(--text-light)',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              padding: 0
            }}
            aria-label={`Edit dataset: ${dataset.title}`}
            title="Edit dataset"
          >
            <Edit size={20} />
          </button>

          {canDelete && (
            <button
              onClick={handleDeleteClick}
              style={{
                width: '44px',
                height: '44px',
                backgroundColor: 'var(--subtle-bg)',
                color: 'var(--error)',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
                padding: 0
              }}
              aria-label={`Delete dataset: ${dataset.title}`}
              title="Delete dataset"
            >
              <Trash2 size={20} />
            </button>
          )}
        </div>
      </div>

      {/* Validation Results Modal */}
      {showValidationModal && validationStatus && (
        <ValidationResultsModal
          isOpen={showValidationModal}
          onClose={() => setShowValidationModal(false)}
          validationResults={validationStatus}
        />
      )}
    </div>
  );
};

// Add CSS styles to the document for more complex hover effects
const injectDatasetCardStyles = () => {
  if (!document.getElementById('dataset-card-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'dataset-card-styles';
    styleEl.innerHTML = `
      .dataset-card:focus-within {
        outline: 2px solid var(--primary);
        outline-offset: 2px;
      }

      .dataset-card button:focus, .dataset-card a:focus {
        outline: 2px solid var(--primary);
        outline-offset: 1px;
      }

      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(styleEl);
  }
};

// Inject the styles when the component is used
if (typeof window !== 'undefined') {
  injectDatasetCardStyles();
}

export default DatasetCard;
