import io
import csv
from typing import List
from backend.app.services.backtesting.schemas import (
    BacktestRunResult,
    ComparisonReportRow,
)


class BacktestReportFormatter:
    """
    Renders dimensional forecast skill comparison tables, executive summaries,
    and CSV export formats.
    """

    @classmethod
    def format_comparison_table(cls, rows: List[ComparisonReportRow]) -> str:
        """
        Formats report rows as a GitHub-flavored Markdown table:
        model | variable | lead time | region | metric | value | sample size | improvement vs model
        """
        header = "| Model | Variable | Lead Time | Region | Metric | Value | Sample Size | Hybrid Improvement |"
        separator = "|:---|:---|:---:|:---|:---|:---:|:---:|:---:|"
        lines = [header, separator]

        for r in rows:
            lead_str = f"{r.lead_time_hours}h" if r.lead_time_hours is not None else "All Leads"
            reg_str = r.region if r.region else "All Regions"
            imp_str = f"{r.relative_improvement_pct:+.2f}%" if r.relative_improvement_pct is not None else "-"
            val_str = f"{r.value:.2f}" if isinstance(r.value, float) else str(r.value)

            line = f"| {r.model_name} | {r.variable} | {lead_str} | {reg_str} | {r.metric} | {val_str} {r.unit} | {r.sample_size} | {imp_str} |"
            lines.append(line)

        return "\n".join(lines)

    @classmethod
    def format_executive_summary(cls, result: BacktestRunResult) -> str:
        """
        Renders the executive dashboard summary statements.
        """
        lines = [
            f"# Forecast Skill Comparison & Backtesting Executive Report",
            f"**Evaluation ID:** `{result.backtest_id}` | **Date:** {result.evaluated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Split:** {int(result.config.train_ratio * 100)}% Train / {int((1 - result.config.train_ratio) * 100)}% Test (No Data Leakage)",
            f"**Train Window:** {result.train_start} to {result.train_end} ({result.train_sample_count} pairs)",
            f"**Test Window:** {result.test_start} to {result.test_end} ({result.test_sample_count} pairs)",
            "",
            "## Key Findings by Variable",
        ]

        for var, headline in result.headlines.items():
            lines.extend([
                f"### {var.title()} Verification",
                f"- **{headline.statement_hybrid_rmse}**",
                f"- **{headline.statement_best_model_rmse}**",
                f"- **{headline.statement_relative_improvement}**",
                f"> {headline.summary_paragraph}",
                "",
            ])

        return "\n".join(lines)

    @classmethod
    def export_report_csv(cls, rows: List[ComparisonReportRow]) -> str:
        """Exports rows to a standard CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["model", "variable", "lead_time_hours", "region", "metric", "value", "unit", "sample_size", "hybrid_improvement_pct"])

        for r in rows:
            writer.writerow([
                r.model_name,
                r.variable,
                r.lead_time_hours if r.lead_time_hours is not None else "",
                r.region if r.region else "",
                r.metric,
                r.value,
                r.unit,
                r.sample_size,
                r.relative_improvement_pct if r.relative_improvement_pct is not None else "",
            ])

        return output.getvalue()
