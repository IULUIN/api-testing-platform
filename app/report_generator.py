"""
Report Generator Module
Returns pure data dicts for ECharts rendering in the template.
"""
from app.performance_analyzer import PerformanceAnalyzer
from datetime import datetime


class ReportGenerator:

    def __init__(self, test_results):
        self.results = test_results
        self.analyzer = PerformanceAnalyzer(test_results)

    def generate_summary_data(self):
        summary = self.analyzer.get_summary()
        percentiles = summary['percentiles']
        sr = summary['success_rate']
        return {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_requests': sr['total'],
            'success_count': sr['success'],
            'failed_count': sr['failed'],
            'error_count': sr['error'],
            'success_rate': sr['success_rate'],
            'tps': summary['tps'],
            'avg_response_time': round(percentiles['avg'] * 1000, 2),
            'min_response_time': round(percentiles['min'] * 1000, 2),
            'max_response_time': round(percentiles['max'] * 1000, 2),
            'p50': round(percentiles['p50'] * 1000, 2),
            'p90': round(percentiles['p90'] * 1000, 2),
            'p95': round(percentiles['p95'] * 1000, 2),
            'p99': round(percentiles['p99'] * 1000, 2),
        }

    def generate_chart_data(self):
        """Return plain dicts consumed by ECharts in the template."""
        summary = self.analyzer.get_summary()
        sr = summary['success_rate']
        ts = summary['time_series']
        dist = summary['distribution']
        pct = summary['percentiles']

        # --- trend ---
        trend_x = [str(t).split('.')[0][-8:] for t in ts['timestamps']]  # HH:MM:SS
        trend_y = [round(v * 1000, 2) for v in ts['response_times']]

        # --- pie ---
        pie_data = []
        if sr['success'] > 0:
            pie_data.append({'name': '成功', 'value': sr['success']})
        if sr['failed'] > 0:
            pie_data.append({'name': '失败', 'value': sr['failed']})
        if sr['error'] > 0:
            pie_data.append({'name': '错误', 'value': sr['error']})

        # --- distribution ---
        dist_x = dist['bins']
        dist_y = dist['counts'] if isinstance(dist['counts'], list) else dist['counts'].tolist()

        # --- percentiles ---
        pct_values = [
            round(pct['p50'] * 1000, 2),
            round(pct['p90'] * 1000, 2),
            round(pct['p95'] * 1000, 2),
            round(pct['p99'] * 1000, 2),
        ]

        return {
            'trend_x': trend_x,
            'trend_y': trend_y,
            'pie_data': pie_data,
            'success_rate': sr['success_rate'],
            'dist_x': dist_x,
            'dist_y': dist_y,
            'pct_values': pct_values,
        }

    def generate_report_data(self):
        return {
            'summary': self.generate_summary_data(),
            'chart_data': self.generate_chart_data(),
        }
