"""Report generator and CSV exporter for CloudGuard AI."""
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional
import pandas as pd

from src.analytics.cost_engine import PeriodMetrics
from src.analytics.anomaly_detector import AnomalyRecord
from src.analytics.forecaster import ForecastResult
from src.analytics.recommender import OptimizationRecommendation


class ReportExporter:
    """Generates standardized CSV exports and executive analysis summaries."""

    @classmethod
    def export_cost_summary_csv(
        cls,
        metrics: PeriodMetrics,
        period_label: str,
        cost_measure: str = "UnblendedCost"
    ) -> str:
        """Exports key cost metrics summary as a CSV string."""
        data = [
            {"Metric": "Billing Period", "Value": period_label, "Classification": "Dimension"},
            {"Metric": "Cost Measure", "Value": cost_measure, "Classification": "Accounting Method"},
            {"Metric": "Currency", "Value": metrics.currency, "Classification": "Standard"},
            {"Metric": "Total Cloud Cost", "Value": f"{metrics.total_cost:.2f}", "Classification": "Actual Spend"},
            {"Metric": "Previous Period Cost", "Value": f"{metrics.previous_cost:.2f}" if metrics.previous_cost is not None else "N/A", "Classification": "Calculated Baseline"},
            {"Metric": "Absolute Change", "Value": f"{metrics.absolute_change:+.2f}" if metrics.absolute_change is not None else "N/A", "Classification": "Calculated Difference"},
            {"Metric": "Percentage Change", "Value": f"{metrics.percentage_change:+.1f}%" if metrics.percentage_change is not None else "N/A", "Classification": "Calculated Percentage"},
            {"Metric": "Highest-Cost Service", "Value": metrics.highest_cost_service or "None", "Classification": "Actual Dimension"},
            {"Metric": "Highest Service Spend", "Value": f"{metrics.highest_cost_service_amount:.2f}", "Classification": "Actual Spend"},
        ]
        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    @classmethod
    def export_service_breakdown_csv(cls, service_df: pd.DataFrame, currency: str = "USD") -> str:
        """Exports service breakdown table as CSV."""
        if service_df.empty:
            return "service,cost_amount,percentage\n"
        out_df = service_df.copy()
        out_df["currency"] = currency
        return out_df.to_csv(index=False)

    @classmethod
    def export_anomalies_csv(cls, anomalies: List[AnomalyRecord]) -> str:
        """Exports detected anomalies table as CSV."""
        if not anomalies:
            return "detection_date,service,actual_cost,baseline_cost,absolute_increase,percentage_increase,detection_method,trigger_reason,evidence_level,status\n"
        rows = [a.to_dict() for a in anomalies]
        df = pd.DataFrame(rows)
        # Drop internal id column if present for export
        cols_to_drop = [c for c in ["id", "supporting_records_count"] if c in df.columns]
        df.drop(columns=cols_to_drop, inplace=True)
        return df.to_csv(index=False)

    @classmethod
    def export_forecast_csv(cls, forecast: ForecastResult) -> str:
        """Exports forecast details and daily projection if available."""
        if not forecast.is_eligible or forecast.daily_forecast_df is None:
            data = [
                {"Metric": "Method", "Value": forecast.method_name},
                {"Metric": "Status", "Value": "Eligible" if forecast.is_eligible else "Ineligible"},
                {"Metric": "Projected Total", "Value": f"{forecast.projected_total:.2f}"},
                {"Metric": "Current Actual Total", "Value": f"{forecast.current_actual_total:.2f}"},
                {"Metric": "Lower Bound (95%)", "Value": f"{forecast.lower_bound:.2f}" if forecast.lower_bound is not None else "N/A"},
                {"Metric": "Upper Bound (95%)", "Value": f"{forecast.upper_bound:.2f}" if forecast.upper_bound is not None else "N/A"},
                {"Metric": "Horizon", "Value": forecast.forecast_horizon},
                {"Metric": "Note", "Value": forecast.method_explanation or forecast.error_message or ""},
            ]
            return pd.DataFrame(data).to_csv(index=False)

        return forecast.daily_forecast_df.to_csv(index=False)

    @classmethod
    def export_recommendations_csv(cls, recommendations: List[OptimizationRecommendation]) -> str:
        """Exports recommendations table as CSV."""
        if not recommendations:
            return "category,title,service,supporting_evidence,suggested_action,estimated_savings,limitations,status\n"
        rows = [r.to_dict() for r in recommendations]
        df = pd.DataFrame(rows)
        if "id" in df.columns:
            df.drop(columns=["id"], inplace=True)
        return df.to_csv(index=False)

    @classmethod
    def generate_executive_summary_markdown(
        cls,
        dataset_name: str,
        period_label: str,
        cost_measure: str,
        currency: str,
        metrics: PeriodMetrics,
        top_services_df: pd.DataFrame,
        anomalies: List[AnomalyRecord],
        forecast: Optional[ForecastResult] = None
    ) -> str:
        """Generates a concise, audit-ready executive summary in markdown."""
        lines = []
        lines.append(f"# CloudGuard AI Executive Cost Report")
        lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
        lines.append(f"**Dataset:** `{dataset_name}` | **Billing Period:** `{period_label}`  ")
        lines.append(f"**Cost Measure:** `{cost_measure}` | **Currency:** `{currency}`\n")
        lines.append("---")

        # 1. Financial overview
        lines.append("## 1. Financial Overview")
        lines.append(f"- **Total Period Spend:** **${metrics.total_cost:,.2f}** (Actual)")
        if metrics.previous_cost is not None:
            change_str = metrics.change_description
            lines.append(f"- **Prior Period Comparison:** {change_str} (Calculated)")
        else:
            lines.append("- **Prior Period Comparison:** No previous period data recorded.")
        if metrics.highest_cost_service:
            lines.append(f"- **Dominant Service:** **{metrics.highest_cost_service}** (${metrics.highest_cost_service_amount:,.2f})")
        lines.append("")

        # 2. Top services
        lines.append("## 2. Top Contributing Services")
        if not top_services_df.empty:
            for _, r in top_services_df.head(5).iterrows():
                lines.append(f"- **{r['service']}**: ${r['cost_amount']:,.2f} ({r['percentage']:.1f}%)")
        else:
            lines.append("No service breakdown data available.")
        lines.append("")

        # 3. Anomaly findings
        lines.append("## 3. Anomaly Findings & Statistical Alerts")
        if anomalies:
            lines.append(f"A total of **{len(anomalies)}** spending anomalies were detected by statistical rules:")
            for i, a in enumerate(anomalies[:3], 1):
                lines.append(f"{i}. **{a.service}** on `{a.detection_date}`: Surge of +${a.absolute_increase:,.2f} (+{f'{a.percentage_increase:.1f}%' if a.percentage_increase else 'N/A'})")
                lines.append(f"   - *Method:* {a.detection_method}")
                lines.append(f"   - *Evidence Level:* {a.evidence_level}")
                lines.append(f"   - *Trigger Reason:* {a.trigger_reason}")
        else:
            lines.append("No statistical anomalies detected under current threshold rules. Spending remained within expected baselines.")
        lines.append("")

        # 4. Forecast projection
        lines.append("## 4. Spend Projections")
        if forecast and forecast.is_eligible:
            lines.append(f"- **Method:** {forecast.method_name}")
            lines.append(f"- **Horizon:** {forecast.forecast_horizon}")
            lines.append(f"- **Projected Total:** **${forecast.projected_total:,.2f}** (Forecast)")
            if forecast.lower_bound and forecast.upper_bound:
                lines.append(f"- **95% Confidence Range:** ${forecast.lower_bound:,.2f} — ${forecast.upper_bound:,.2f}")
            lines.append(f"- **Methodology Note:** {forecast.method_explanation}")
        else:
            reason = forecast.error_message if forecast else "Insufficient historical observations."
            lines.append(f"- **Status:** Projection withheld ({reason})")
        lines.append("")

        # 5. Limitations
        lines.append("## 5. Important Data Limitations & Accounting Disclosures")
        lines.append("- Billing data records financial charges billed by cloud providers, not real-time resource performance (CPU/RAM).")
        lines.append("- Run-rate forecasts assume workload continuity without architectural modifications.")
        lines.append("- Credits, refunds, and discounts are reported according to the selected accounting cost measure.")

        return "\n".join(lines)
