"""Reports export and executive summary page."""
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.analytics.cost_engine import CostEngine
from src.analytics.anomaly_detector import AnomalyDetector
from src.analytics.forecaster import CostForecaster
from src.analytics.recommender import RecommendationEngine
from src.reports.exporter import ReportExporter


def render_reports_page(
    records_df: pd.DataFrame,
    dataset_info: Dict[str, Any],
    db_manager: Any
) -> None:
    """Renders report exports and full audit summary."""
    st.markdown("### Export Reports & Executive Summaries")
    dataset_id = dataset_info["id"]
    dataset_name = dataset_info.get("name", "Active Dataset")
    currency = dataset_info.get("currency", "USD")
    cost_measure = dataset_info.get("cost_measure", "UnblendedCost")

    if records_df.empty:
        st.warning("No records available in dataset.")
        return

    min_date = str(records_df["usage_date"].min())
    max_date = str(records_df["usage_date"].max())
    period_label = f"{min_date} to {max_date}"

    # Calculate metrics
    metrics = CostEngine.calculate_period_metrics(records_df, min_date, max_date, currency=currency)
    svc_df = CostEngine.get_cost_by_service(records_df)
    detector = AnomalyDetector()
    detected_anoms = detector.detect_anomalies(records_df)
    forecast = CostForecaster.forecast_current_month(records_df)

    # ---------------------------------------------------------
    # 1. Downloadable Data Exports (CSVs)
    # ---------------------------------------------------------
    st.markdown("##### Download Export Files")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        cost_csv = ReportExporter.export_cost_summary_csv(metrics, period_label, cost_measure)
        st.download_button(
            "📥 Cost Summary CSV",
            data=cost_csv,
            file_name=f"cloudguard_cost_summary_{min_date}_{max_date}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c2:
        svc_csv = ReportExporter.export_service_breakdown_csv(svc_df, currency=currency)
        st.download_button(
            "📥 Service Breakdown CSV",
            data=svc_csv,
            file_name=f"cloudguard_service_breakdown_{min_date}_{max_date}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c3:
        # Generate anomaly CSV
        anom_objs = []
        detector = AnomalyDetector()
        detected_anoms = detector.detect_anomalies(records_df)
        anom_csv = ReportExporter.export_anomalies_csv(detected_anoms)
        st.download_button(
            "📥 Anomalies CSV",
            data=anom_csv,
            file_name=f"cloudguard_anomalies_{min_date}_{max_date}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c4:
        forecast_csv = ReportExporter.export_forecast_csv(forecast)
        st.download_button(
            "📥 Forecast CSV",
            data=forecast_csv,
            file_name=f"cloudguard_forecast_{min_date}_{max_date}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c5:
        recs_objs = RecommendationEngine.generate_recommendations(records_df)
        recs_csv = ReportExporter.export_recommendations_csv(recs_objs)
        st.download_button(
            "📥 Recommendations CSV",
            data=recs_csv,
            file_name=f"cloudguard_recommendations_{min_date}_{max_date}.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.divider()

    # ---------------------------------------------------------
    # 2. Executive Summary Report Viewer
    # ---------------------------------------------------------
    st.markdown("##### Executive Cost Summary")

    summary_md = ReportExporter.generate_executive_summary_markdown(
        dataset_name=dataset_name,
        period_label=period_label,
        cost_measure=cost_measure,
        currency=currency,
        metrics=metrics,
        top_services_df=svc_df,
        anomalies=detected_anoms,
        forecast=forecast
    )

    st.markdown(summary_md)

    st.download_button(
        "📄 Download Executive Summary (.md)",
        data=summary_md,
        file_name=f"cloudguard_executive_summary_{min_date}_{max_date}.md",
        mime="text/markdown"
    )
