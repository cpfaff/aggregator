"""Tests for resource allocation module."""

import pytest
from unittest.mock import patch, MagicMock
from app.core.resource_allocation import (
    get_validator_cpu_count,
    get_stats_worker_concurrency
)


class TestValidatorCPUCount:
    """Test validator CPU allocation calculations."""
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_default_percentage(self, mock_cpu_count):
        """Test default 75% allocation."""
        mock_cpu_count.return_value = 8
        result = get_validator_cpu_count()
        assert result == 6  # 75% of 8
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_custom_percentage(self, mock_cpu_count):
        """Test custom percentage allocation."""
        mock_cpu_count.return_value = 8
        result = get_validator_cpu_count(50)
        assert result == 4  # 50% of 8
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_minimum_threshold(self, mock_cpu_count):
        """Test minimum 1 CPU threshold."""
        mock_cpu_count.return_value = 1
        result = get_validator_cpu_count(10)  # 10% of 1 = 0.1
        assert result == 1  # Should be minimum 1
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_single_core(self, mock_cpu_count):
        """Test single core system."""
        mock_cpu_count.return_value = 1
        result = get_validator_cpu_count(75)
        assert result == 1
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_odd_core_count(self, mock_cpu_count):
        """Test odd number of cores."""
        mock_cpu_count.return_value = 3
        result = get_validator_cpu_count(50)
        assert result == 1  # int(3 * 0.5) = 1
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_high_core_count(self, mock_cpu_count):
        """Test high core count system."""
        mock_cpu_count.return_value = 128
        result = get_validator_cpu_count(75)
        assert result == 96  # 75% of 128
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_invalid_percentage_low(self, mock_cpu_count):
        """Test invalid low percentage."""
        mock_cpu_count.return_value = 8
        result = get_validator_cpu_count(0)
        assert result == 6  # Should use default 75%
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_invalid_percentage_high(self, mock_cpu_count):
        """Test invalid high percentage."""
        mock_cpu_count.return_value = 8
        result = get_validator_cpu_count(101)
        assert result == 6  # Should use default 75%
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_edge_percentages(self, mock_cpu_count):
        """Test edge case percentages."""
        mock_cpu_count.return_value = 8
        
        # 1% should give 1 (minimum)
        assert get_validator_cpu_count(1) == 1
        
        # 99% should give 7
        assert get_validator_cpu_count(99) == 7
        
        # 100% should give 8
        assert get_validator_cpu_count(100) == 8


class TestStatsWorkerConcurrency:
    """Test statistics worker concurrency calculations."""
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_explicit_value(self, mock_cpu_count):
        """Test explicit integer value."""
        result = get_stats_worker_concurrency(4, validator_cpus=2)
        assert result == 4
        mock_cpu_count.assert_not_called()
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_explicit_below_minimum(self, mock_cpu_count):
        """Test explicit value below minimum."""
        result = get_stats_worker_concurrency(1, validator_cpus=2)
        assert result == 2  # Should enforce minimum
        mock_cpu_count.assert_not_called()
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_auto_mode(self, mock_cpu_count):
        """Test auto mode calculation."""
        mock_cpu_count.return_value = 8
        result = get_stats_worker_concurrency('auto', validator_cpus=6)
        assert result == 2  # 8 - 6 = 2
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_auto_mode_with_minimum(self, mock_cpu_count):
        """Test auto mode with minimum threshold."""
        mock_cpu_count.return_value = 2
        result = get_stats_worker_concurrency('auto', validator_cpus=1)
        assert result == 2  # max(2, 2 - 1) = 2
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_auto_mode_insufficient_cpus(self, mock_cpu_count):
        """Test auto mode when validator uses all CPUs."""
        mock_cpu_count.return_value = 8
        result = get_stats_worker_concurrency('auto', validator_cpus=8)
        assert result == 2  # Should use minimum 2
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_auto_mode_no_validator_cpus(self, mock_cpu_count):
        """Test auto mode without providing validator_cpus."""
        mock_cpu_count.return_value = 8
        with patch('app.core.resource_allocation.get_validator_cpu_count') as mock_validator:
            mock_validator.return_value = 6
            result = get_stats_worker_concurrency('auto')
            assert result == 2  # 8 - 6 = 2
            mock_validator.assert_called_once()
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_invalid_string_value(self, mock_cpu_count):
        """Test invalid string value."""
        mock_cpu_count.return_value = 8
        with patch('app.core.resource_allocation.get_validator_cpu_count') as mock_validator:
            mock_validator.return_value = 6
            result = get_stats_worker_concurrency('invalid', validator_cpus=6)
            assert result == 2  # Should fallback to auto mode
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_various_cpu_counts(self, mock_cpu_count):
        """Test various CPU count scenarios."""
        test_cases = [
            (1, 1, 2),   # 1 CPU total, 1 for validator, 2 for stats (minimum)
            (2, 1, 2),   # 2 CPUs total, 1 for validator, 2 for stats (minimum)
            (4, 3, 2),   # 4 CPUs total, 3 for validator, 2 for stats (minimum)
            (8, 6, 2),   # 8 CPUs total, 6 for validator, 2 for stats
            (16, 12, 4), # 16 CPUs total, 12 for validator, 4 for stats
            (32, 24, 8), # 32 CPUs total, 24 for validator, 8 for stats
        ]
        
        for total_cpus, validator_cpus, expected_stats in test_cases:
            mock_cpu_count.return_value = total_cpus
            result = get_stats_worker_concurrency('auto', validator_cpus=validator_cpus)
            assert result == expected_stats, f"Failed for {total_cpus} CPUs"


class TestIntegration:
    """Test integration between validator and stats allocation."""
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_full_allocation_flow(self, mock_cpu_count):
        """Test complete allocation flow."""
        mock_cpu_count.return_value = 8
        
        # Allocate validator CPUs first
        validator_cpus = get_validator_cpu_count(75)
        assert validator_cpus == 6
        
        # Then allocate stats concurrency
        stats_concurrency = get_stats_worker_concurrency('auto', validator_cpus)
        assert stats_concurrency == 2
        
        # Total should not exceed available CPUs
        assert validator_cpus + stats_concurrency <= 8
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_edge_case_single_cpu(self, mock_cpu_count):
        """Test edge case with single CPU."""
        mock_cpu_count.return_value = 1
        
        validator_cpus = get_validator_cpu_count(75)
        assert validator_cpus == 1
        
        stats_concurrency = get_stats_worker_concurrency('auto', validator_cpus)
        assert stats_concurrency == 2  # Minimum threshold
    
    @patch('app.core.resource_allocation.multiprocessing.cpu_count')
    def test_edge_case_hundred_cpus(self, mock_cpu_count):
        """Test edge case with 100+ CPUs."""
        mock_cpu_count.return_value = 128
        
        validator_cpus = get_validator_cpu_count(75)
        assert validator_cpus == 96
        
        stats_concurrency = get_stats_worker_concurrency('auto', validator_cpus)
        assert stats_concurrency == 32  # 128 - 96