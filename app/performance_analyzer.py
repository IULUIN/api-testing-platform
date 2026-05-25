"""
Performance Analyzer Module
Calculates performance metrics like P90/P95/P99, TPS, QPS
"""
import numpy as np
import pandas as pd
from datetime import datetime


class PerformanceAnalyzer:
    """Performance analysis for test results"""

    def __init__(self, results):
        """
        Initialize with test results

        Args:
            results: List of test result dictionaries
        """
        self.results = results
        if results:
            self.df = pd.DataFrame(results)
        else:
            self.df = pd.DataFrame()

    def calculate_percentiles(self):
        """
        Calculate percentile response times

        Returns:
            dict: Percentile statistics (P50, P90, P95, P99, avg, max, min)
        """
        if self.df.empty or 'response_time' not in self.df.columns:
            return {
                'p50': 0,
                'p90': 0,
                'p95': 0,
                'p99': 0,
                'avg': 0,
                'max': 0,
                'min': 0
            }

        response_times = self.df['response_time'].dropna()

        if len(response_times) == 0:
            return {
                'p50': 0,
                'p90': 0,
                'p95': 0,
                'p99': 0,
                'avg': 0,
                'max': 0,
                'min': 0
            }

        return {
            'p50': float(np.percentile(response_times, 50)),
            'p90': float(np.percentile(response_times, 90)),
            'p95': float(np.percentile(response_times, 95)),
            'p99': float(np.percentile(response_times, 99)),
            'avg': float(response_times.mean()),
            'max': float(response_times.max()),
            'min': float(response_times.min())
        }

    def calculate_tps(self, duration=None):
        """
        Calculate TPS (Transactions Per Second)

        Args:
            duration: Test duration in seconds. If None, calculate from timestamps

        Returns:
            float: TPS value
        """
        if self.df.empty:
            return 0.0

        total_requests = len(self.df)

        if duration is None:
            # Try to calculate duration from timestamps
            if 'executed_at' in self.df.columns:
                try:
                    timestamps = pd.to_datetime(self.df['executed_at'])
                    duration = (timestamps.max() - timestamps.min()).total_seconds()
                except:
                    duration = 1  # Default to 1 second if calculation fails
            else:
                duration = 1

        if duration == 0:
            duration = 1

        return round(total_requests / duration, 2)

    def calculate_success_rate(self):
        """
        Calculate success rate

        Returns:
            dict: Success rate statistics
        """
        if self.df.empty or 'status' not in self.df.columns:
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'error': 0,
                'success_rate': 0.0
            }

        total = len(self.df)
        success = len(self.df[self.df['status'] == 'success'])
        failed = len(self.df[self.df['status'] == 'failed'])
        error = len(self.df[self.df['status'] == 'error'])

        success_rate = (success / total * 100) if total > 0 else 0.0

        return {
            'total': total,
            'success': success,
            'failed': failed,
            'error': error,
            'success_rate': round(success_rate, 2)
        }

    def get_response_time_distribution(self, bins=10):
        """
        Get response time distribution

        Args:
            bins: Number of bins for histogram

        Returns:
            dict: Distribution data
        """
        if self.df.empty or 'response_time' not in self.df.columns:
            return {'bins': [], 'counts': []}

        response_times = self.df['response_time'].dropna()

        if len(response_times) == 0:
            return {'bins': [], 'counts': []}

        counts, bin_edges = np.histogram(response_times, bins=bins)

        return {
            'bins': [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(bin_edges)-1)],
            'counts': counts.tolist()
        }

    def get_time_series_data(self):
        """
        Get time series data for response time trend

        Returns:
            dict: Time series data
        """
        if self.df.empty:
            return {'timestamps': [], 'response_times': []}

        if 'executed_at' not in self.df.columns or 'response_time' not in self.df.columns:
            return {'timestamps': [], 'response_times': []}

        # Sort by timestamp
        df_sorted = self.df.sort_values('executed_at')

        timestamps = df_sorted['executed_at'].tolist()
        response_times = df_sorted['response_time'].tolist()

        return {
            'timestamps': [str(ts) for ts in timestamps],
            'response_times': response_times
        }

    def get_summary(self):
        """
        Get complete performance summary

        Returns:
            dict: Complete performance metrics
        """
        return {
            'percentiles': self.calculate_percentiles(),
            'tps': self.calculate_tps(),
            'success_rate': self.calculate_success_rate(),
            'distribution': self.get_response_time_distribution(),
            'time_series': self.get_time_series_data()
        }
