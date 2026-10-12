"""Cost forecasting and expenditure projection page."""
from typing import Any, Dict, Optional
import pandas as pd
import streamlit as st

from src.analytics.forecaster import CostForecaster
from src.analytics.cost_engine import CostEngine
from src.ui.components import render_metric_card, create_forecast_chart


def render_forecast_page(
    records_df: pd.DataFrame,
    dataset_info: Dict[str, Any]
) -> None:
    """Renders cost forecasting models, uncertainty envelopes, and methodology notes."""
    st.markdown("### Cloud Spend Forecasting & Projections")
    currency = dataset_info.get("currency", "USD")

    if records_df.empty:
        st.warning("No records available in dataset.")
        return

    # ---------------------------------------------------------
    # 1. Model Selection & Configuration
    # ---------------------------------------------------------
    f_col1, f_col2 = st.columns([3, 2])
    with f_col1:
        model_choice = st.radio(
            "Forecasting Methodology",
            options=["Month-to-Date Weighted Run-Rate", "Linear Trend Regression (OLS)"],
            horizontal=True
        )

    # ---------------------------------------------------------
    # 2. Compute Forecast
    # ---------------------------------------------------------
    if model_choice == "Month-to-Date Weighted Run-Rate":
        forecast = CostForecaster.forecast_current_month(records_df)
    else:
        with f_col2:
            horizon_days = st.slider("Forecast Horizon (Days)", min_value=7, max_value=60, value=30, step=1)
        forecast = CostForecaster.forecast_linear_trend(records_df, horizon_days=horizon_days)

    if not forecast.is_eligible:
        st.warning(f"⚠️ **Forecast Withheld:** {forecast.error_message}")
        st.info(
            "**Forecasting Data Requirements:**\n"
            "- Month-to-Date Run-Rate requires at least **3 distinct days** in the active month.\n"
            "- Linear Trend Regression requires at least **7 continuous historical days**.\n\n"
            "CloudGuard AI does not synthesize unverified future data points."
        )
        return

    # ---------------------------------------------------------
    # 3. Forecast Metric Summary Cards
    # ---------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        render_metric_card(
            label="Projected Total Spend",
            value=CostEngine.format_currency(forecast.projected_total, currency),
            subtext=f"Horizon: {forecast.forecast_horizon}"
        )
    with m2:
        render_metric_card(
            label="Current Actual Spend",
            value=CostEngine.format_currency(forecast.current_actual_total, currency),
            subtext="Recorded to date"
        )
    with m3:
        if forecast.lower_bound is not None and forecast.upper_bound is not None:
            bound_str = f"{CostEngine.format_currency(forecast.lower_bound, currency)} — {CostEngine.format_currency(forecast.upper_bound, currency)}"
            render_metric_card(
                label="95% Confidence Interval",
                value=CostEngine.format_currency(forecast.upper_bound, currency),
                subtext=f"Range: {bound_str}"
            )
        else:
            render_metric_card("Confidence Bounds", "N/A", subtext="Completed period")
    with m4:
        render_metric_card(
            label="Confidence Level",
            value=forecast.confidence_level,
            subtext=f"Method: {forecast.method_name}"
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 4. Interactive Forecast Chart
    # ---------------------------------------------------------
    st.markdown("##### Historical Actuals vs Projected Trend")

    historical_daily = records_df.groupby("usage_date")["cost_amount"].sum().reset_index()

    if forecast.daily_forecast_df is not None:
        fig = create_forecast_chart(historical_daily, forecast.daily_forecast_df, currency=currency)
    else:
        # Month to date run-rate display
        fig = create_forecast_chart(historical_daily, pd.DataFrame(), currency=currency)

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ---------------------------------------------------------
    # 5. Method Explanation & Assumptions
    # ---------------------------------------------------------
    with st.expander("📖 Methodology Explanation & Modeling Assumptions", expanded=True):
        st.markdown(f"**Method Explanation:** {forecast.method_explanation}")
        st.markdown("**Assumptions and Limitations:**")
        for lim in forecast.assumptions_and_limitations:
            st.markdown(f"- {lim}")
        st.caption(
            "Note: CloudGuard AI uses deterministic time-series baselines. "
            "Financial forecasts should be reviewed alongside planned infrastructure modifications."
        )
