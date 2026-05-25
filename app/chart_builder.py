"""
Chart Builder Module
Builds various charts using pyecharts
"""
from pyecharts import options as opts
from pyecharts.charts import Line, Pie, Bar, Gauge
from pyecharts.globals import ThemeType


class ChartBuilder:
    """Build charts for performance reports"""

    @staticmethod
    def build_response_time_trend(timestamps, response_times):
        """
        Build response time trend line chart

        Args:
            timestamps: List of timestamps
            response_times: List of response times

        Returns:
            str: HTML embed code
        """
        if not timestamps or not response_times:
            return "<div>No data available</div>"

        # Limit data points for better performance
        max_points = 100
        if len(timestamps) > max_points:
            step = len(timestamps) // max_points
            timestamps = timestamps[::step]
            response_times = response_times[::step]

        # Format response times to 5 significant figures
        formatted_times = [round(t, 2) for t in response_times]

        line = (
            Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="450px"))
            .add_xaxis([str(t).split('.')[0] for t in timestamps])  # Remove microseconds
            .add_yaxis(
                "响应时间",
                formatted_times,
                is_smooth=True,
                label_opts=opts.LabelOpts(is_show=False),
                linestyle_opts=opts.LineStyleOpts(width=2),
                areastyle_opts=opts.AreaStyleOpts(opacity=0.3)
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="响应时间趋势",
                    subtitle="执行时间线上的响应时间变化",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=18),
                    subtitle_textstyle_opts=opts.TextStyleOpts(font_size=14)
                ),
                xaxis_opts=opts.AxisOpts(
                    name="时间",
                    type_="category",
                    axislabel_opts=opts.LabelOpts(rotate=45, interval="auto", font_size=11),
                    name_textstyle_opts=opts.TextStyleOpts(font_size=12)
                ),
                yaxis_opts=opts.AxisOpts(
                    name="响应时间 (ms)",
                    type_="value",
                    name_textstyle_opts=opts.TextStyleOpts(font_size=12)
                ),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                datazoom_opts=[opts.DataZoomOpts(type_="slider", xaxis_index=0)]
            )
        )
        return line.render_embed()

    @staticmethod
    def build_success_rate_pie(success, failed, error=0):
        """
        Build success rate pie chart

        Args:
            success: Number of successful requests
            failed: Number of failed requests
            error: Number of error requests

        Returns:
            str: HTML embed code
        """
        data = []
        if success > 0:
            data.append(("Success", success))
        if failed > 0:
            data.append(("Failed", failed))
        if error > 0:
            data.append(("Error", error))

        if not data:
            return "<div>No data available</div>"

        pie = (
            Pie(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="450px"))
            .add(
                "",
                data,
                radius=["40%", "70%"],
                label_opts=opts.LabelOpts(
                    formatter="{b}: {c} ({d}%)",
                    font_size=12
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="成功率分布",
                    subtitle="测试执行结果",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=18),
                    subtitle_textstyle_opts=opts.TextStyleOpts(font_size=14)
                ),
                legend_opts=opts.LegendOpts(
                    orient="vertical",
                    pos_left="left",
                    textstyle_opts=opts.TextStyleOpts(font_size=12)
                )
            )
            .set_series_opts(
                tooltip_opts=opts.TooltipOpts(formatter="{b}: {c} ({d}%)")
            )
        )
        return pie.render_embed()

    @staticmethod
    def build_response_time_distribution(bins, counts):
        """
        Build response time distribution bar chart

        Args:
            bins: List of bin labels
            counts: List of counts for each bin

        Returns:
            str: HTML embed code
        """
        if not bins or not counts:
            return "<div>No data available</div>"

        # Format bin labels to 5 significant figures
        formatted_bins = [f"{float(b.split('-')[0]):.2f}-{float(b.split('-')[1]):.2f}" if '-' in b else b for b in bins]

        bar = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="450px"))
            .add_xaxis(formatted_bins)
            .add_yaxis(
                "数量",
                counts.tolist() if hasattr(counts, 'tolist') else counts,
                label_opts=opts.LabelOpts(is_show=False)
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="响应时间分布",
                    subtitle="响应时间的频率分布",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=18),
                    subtitle_textstyle_opts=opts.TextStyleOpts(font_size=14)
                ),
                xaxis_opts=opts.AxisOpts(
                    name="响应时间范围 (ms)",
                    axislabel_opts=opts.LabelOpts(rotate=45, interval="auto", font_size=11),
                    name_textstyle_opts=opts.TextStyleOpts(font_size=12)
                ),
                yaxis_opts=opts.AxisOpts(
                    name="数量",
                    name_textstyle_opts=opts.TextStyleOpts(font_size=12)
                ),
                tooltip_opts=opts.TooltipOpts(trigger="axis")
            )
        )
        return bar.render_embed()

    @staticmethod
    def build_success_rate_gauge(success_rate):
        """
        Build success rate gauge chart

        Args:
            success_rate: Success rate percentage (0-100)

        Returns:
            str: HTML embed code
        """
        gauge = (
            Gauge(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="450px"))
            .add(
                "",
                [("成功率", round(success_rate, 2))],
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(
                        color=[(0.3, "#FF6E76"), (0.7, "#FDDD60"), (1, "#58D9F9")],
                        width=30
                    )
                ),
                detail_label_opts=opts.LabelOpts(font_size=24)
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="成功率",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=18)
                ),
                tooltip_opts=opts.TooltipOpts(formatter="{a} <br/>{b} : {c}%")
            )
        )
        return gauge.render_embed()

    @staticmethod
    def build_percentile_comparison(percentiles):
        """
        Build percentile comparison bar chart

        Args:
            percentiles: Dict with p50, p90, p95, p99 values

        Returns:
            str: HTML embed code
        """
        if not percentiles:
            return "<div>No data available</div>"

        labels = ['P50', 'P90', 'P95', 'P99']
        values = [
            round(percentiles.get('p50', 0), 2),
            round(percentiles.get('p90', 0), 2),
            round(percentiles.get('p95', 0), 2),
            round(percentiles.get('p99', 0), 2)
        ]

        bar = (
            Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="100%", height="450px"))
            .add_xaxis(labels)
            .add_yaxis(
                "响应时间 (ms)",
                values,
                label_opts=opts.LabelOpts(position="top", font_size=12),
                itemstyle_opts=opts.ItemStyleOpts(
                    color="#5470C6"
                )
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="百分位响应时间",
                    subtitle="P50、P90、P95、P99对比",
                    title_textstyle_opts=opts.TextStyleOpts(font_size=18),
                    subtitle_textstyle_opts=opts.TextStyleOpts(font_size=14)
                ),
                xaxis_opts=opts.AxisOpts(
                    name="百分位",
                    axislabel_opts=opts.LabelOpts(font_size=12),
                    name_textstyle_opts=opts.TextStyleOpts(font_size=12)
                ),
                yaxis_opts=opts.AxisOpts(
                    name="响应时间 (ms)",
                    name_textstyle_opts=opts.TextStyleOpts(font_size=12)
                ),
                tooltip_opts=opts.TooltipOpts(formatter="{b}: {c}ms")
            )
        )
        return bar.render_embed()
