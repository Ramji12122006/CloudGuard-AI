"""Overview dashboard page for CloudGuard AI."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.analytics.cost_engine import CostEngine
from src.analytics.anomaly_detector import AnomalyDetector
from src.analytics.forecaster import CostForecaster
from src.ui.components import (
    render_metric_card,
    render_alert_card,
    create_time_series_chart,
    create_service_bar_chart,
)


def render_overview_page(
    records_df: pd.DataFrame,
    dataset_info: Dict[str, Any],
    db_manager: Any
) -> None:
    """Renders the minimal, uncluttered primary overview dashboard."""

    # ---------------------------------------------------------
    # A. Compact Top Section
    # ---------------------------------------------------------
    st.markdown("## CloudGuard AI")

    top_col1, top_col2, top_col3 = st.columns([3, 2, 2])

    with top_col1:
        st.markdown(f"**Dataset:** `{dataset_info.get('name', 'Active Dataset')}`")
        if dataset_info.get("notes") and "demonstration" in dataset_info.get("notes", "").lower():
            st.caption("ℹ️ *Notice: Active dataset contains synthetic demonstration data.*")

    # Date range options from dataset
    min_date = str(records_df["usage_date"].min())
    max_date = str(records_df["usage_date"].max())
    distinct_months = sorted(list(records_df["billing_period"].unique()))

    with top_col2:
        period_mode = st.selectbox(
            "Billing Period Scope",
            options=["Latest Month", "All Available Data", "Custom Month"],
            index=0,
            label_visibility="collapsed"
        )

    # Determine start and end date based on selection
    if period_mode == "Latest Month" and distinct_months:
        sel_month = distinct_months[-1]
        month_df = records_df[records_df["billing_period"] == sel_month]
        start_date = str(month_df["usage_date"].min())
        end_date = str(month_df["usage_date"].max())
        period_label = f"Month: {sel_month}"
    elif period_mode == "Custom Month" and distinct_months:
        with top_col3:
            sel_month = st.selectbox("Select Month", options=distinct_months, index=len(distinct_months)-1)
        month_df = records_df[records_df["billing_period"] == sel_month]
        start_date = str(month_df["usage_date"].min())
        end_date = str(month_df["usage_date"].max())
        period_label = f"Month: {sel_month}"
    else:
        start_date = min_date
        end_date = max_date
        period_label = f"{min_date} to {max_date}"

    currency = dataset_info.get("currency", "USD")

    # Filter records for selected period
    period_df = records_df[(records_df["usage_date"] >= start_date) & (records_df["usage_date"] <= end_date)]

    # ---------------------------------------------------------
    # B. Four Key Metric Cards
    # ---------------------------------------------------------
    metrics = CostEngine.calculate_period_metrics(records_df, start_date, end_date, currency=currency)

    # Calculate Projected Monthly Cost
    forecast_res = CostForecaster.forecast_current_month(records_df)
    if forecast_res.is_eligible:
        proj_str = CostEngine.format_currency(forecast_res.projected_total, currency)
        proj_subtext = f"Forecast ({forecast_res.forecast_horizon})"
    else:
        proj_str = "Insufficient data"
        proj_subtext = forecast_res.error_message or "Need >= 3 days in current month"

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        render_metric_card(
            label="Total Cloud Cost",
            value=CostEngine.format_currency(metrics.total_cost, currency),
            subtext=f"Selected: {period_label}",
            is_favorable=None
        )

    with m_col2:
        if metrics.previous_cost is not None:
            render_metric_card(
                label="Change vs Prior Period",
                value=metrics.change_description.split(" ")[0],
                subtext=" ".join(metrics.change_description.split(" ")[1:]),
                is_favorable=metrics.is_favorable
            )
        else:
            render_metric_card(
                label="Change vs Prior Period",
                value="N/A",
                subtext="No previous period data",
                is_favorable=None
            )

    with m_col3:
        top_svc_name = metrics.highest_cost_service or "None"
        render_metric_card(
            label="Highest-Cost Service",
            value=top_svc_name,
            subtext=CostEngine.format_currency(metrics.highest_cost_service_amount, currency),
            is_favorable=None
        )

    with m_col4:
        render_metric_card(
            label="Projected Monthly Cost",
            value=proj_str,
            subtext=proj_subtext,
            is_favorable=None
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # C. Main Cost Chart & D. Service Cost Breakdown
    # ---------------------------------------------------------
    chart_col, svc_col = st.columns([5, 3])

    with chart_col:
        chart_header_col1, chart_header_col2 = st.columns([3, 2])
        with chart_header_col1:
            st.markdown("##### Expenditure Trend")
        with chart_header_col2:
            time_grouping = st.radio(
                "Grouping",
                options=["Daily", "Monthly"],
                index=0,
                horizontal=True,
                label_visibility="collapsed"
            )

        if time_grouping == "Daily":
            trend_df = CostEngine.get_daily_trend(records_df, start_date, end_date)
            fig_trend = create_time_series_chart(trend_df, currency=currency, show_previous=True)
        else:
            monthly_df = CostEngine.get_monthly_trend(records_df)
            monthly_plot_df = pd.DataFrame({
                "usage_date": monthly_df["billing_period"],
                "cost": monthly_df["cost_amount"],
                "previous_cost": [None] * len(monthly_df)
            })
            fig_trend = create_time_series_chart(monthly_plot_df, currency=currency, show_previous=False)

        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    with svc_col:
        st.markdown("##### Top 5 Services")
        svc_df = CostEngine.get_cost_by_service(period_df, top_n=5)
        fig_svc = create_service_bar_chart(svc_df, currency=currency)
        st.plotly_chart(fig_svc, use_container_width=True, config={"displayModeBar": False})

    # ---------------------------------------------------------
    # E. Important Alerts (Max 3 Highest-Priority Findings)
    # ---------------------------------------------------------
    st.markdown("##### Priority Cost Alerts")

    # Check anomalies from DB or detect on the fly
    dataset_id = dataset_info["id"]
    db_anomalies = db_manager.get_anomalies(dataset_id)

    if not db_anomalies:
        detector = AnomalyDetector()
        detected = detector.detect_anomalies(records_df)
        if detected:
            db_manager.save_anomalies(dataset_id, [a.to_dict() for a in detected])
            db_anomalies = db_manager.get_anomalies(dataset_id)

    if db_anomalies:
        # Show at most 3 highest priority alerts
        top_alerts = db_anomalies[:3]
        for a in top_alerts:
            inc_val = a["absolute_increase"]
            pct_val = a.get("percentage_increase")
            pct_str = f" (+{pct_val:.1f}%)" if pct_val is not None else ""
            inc_str = f"+${inc_val:,.2f}{pct_str}"

            render_alert_card(
                title=f"{a['service']} Spike Detected ({a['detection_method']})",
                service=a["service"],
                detection_date=a["detection_date"],
                increase_str=inc_str,
                reason=a["trigger_reason"],
                evidence_level=a.get("evidence_level", "Confirmed by billing data")
            )
    else:
        st.info("ℹ️ No statistical anomalies detected by configured rules for this dataset. (Note: this does not guarantee spending is strictly optimal).")
