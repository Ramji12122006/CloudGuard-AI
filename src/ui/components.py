"""Reusable UI components and Plotly chart builders for CloudGuard AI."""
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import PALETTE


def render_metric_card(
    label: str,
    value: str,
    subtext: Optional[str] = None,
    is_favorable: Optional[bool] = None
) -> None:
    """Renders a minimal, consistent enterprise metric card."""
    subtext_class = "cg-subtext-neutral"
    if is_favorable is True:
        subtext_class = "cg-subtext-favorable"
    elif is_favorable is False:
        subtext_class = "cg-subtext-unfavorable"

    subtext_html = f'<div class="cg-metric-subtext {subtext_class}">{subtext}</div>' if subtext else ""

    html = f"""
    <div class="cg-metric-card">
        <div class="cg-metric-label">{label}</div>
        <div class="cg-metric-value">{value}</div>
        {subtext_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_alert_card(
    title: str,
    service: str,
    detection_date: str,
    increase_str: str,
    reason: str,
    evidence_level: str
) -> None:
    """Renders a prioritized anomaly alert card with clear evidence classification."""
    badge_class = "cg-badge-confirmed"
    if "Strongly" in evidence_level:
        badge_class = "cg-badge-inferred"
    elif "Possible" in evidence_level or "Insufficient" in evidence_level:
        badge_class = "cg-badge-neutral"

    html = f"""
    <div class="cg-alert-card">
        <div class="cg-alert-title">
            {title}
            <span class="cg-badge {badge_class}">{evidence_level}</span>
        </div>
        <div class="cg-alert-meta">
            Service: <strong>{service}</strong> &bull; Date: <strong>{detection_date}</strong> &bull; Impact: <strong>{increase_str}</strong>
        </div>
        <div class="cg-alert-reason">{reason}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def create_time_series_chart(
    trend_df: pd.DataFrame,
    currency: str = "USD",
    show_previous: bool = True
) -> go.Figure:
    """Creates a high-contrast, uncluttered Plotly time-series chart."""
    fig = go.Figure()

    if trend_df.empty:
        fig.add_annotation(
            text="No trend data available for selected range",
            showarrow=False,
            font=dict(size=14, color=PALETTE["neutral"])
        )
        _style_figure(fig, title="")
        return fig

    # Previous period comparison trace (subtle gray dashed line)
    if show_previous and "previous_cost" in trend_df.columns and trend_df["previous_cost"].dropna().any():
        fig.add_trace(go.Scatter(
            x=trend_df["usage_date"],
            y=trend_df["previous_cost"],
            mode="lines",
            name="Previous Period",
            line=dict(color=PALETTE["neutral"], width=2, dash="dot"),
            hovertemplate=f"Prior Period: %{{y:$,.2f}}<extra></extra>"
        ))

    # Current period expenditure trace (vibrant sky blue line with area fill)
    fig.add_trace(go.Scatter(
        x=trend_df["usage_date"],
        y=trend_df["cost"],
        mode="lines+markers",
        name="Current Period",
        line=dict(color=PALETTE["primary"], width=2.5),
        marker=dict(size=5, color=PALETTE["primary"]),
        fill="tozeroy",
        fillcolor="rgba(2, 132, 199, 0.08)",
        hovertemplate=f"Date: %{{x}}<br>Cost: %{{y:$,.2f}}<extra></extra>"
    ))

    _style_figure(fig, title="")
    fig.update_layout(
        yaxis_tickprefix="$" if currency == "USD" else "",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=PALETTE["neutral"])
        )
    )
    return fig


def create_service_bar_chart(service_df: pd.DataFrame, currency: str = "USD") -> go.Figure:
    """Creates a clean horizontal bar chart showing top services."""
    fig = go.Figure()

    if service_df.empty:
        fig.add_annotation(
            text="No service data available",
            showarrow=False,
            font=dict(size=14, color=PALETTE["neutral"])
        )
        _style_figure(fig, title="")
        return fig

    # Reverse order so largest is at the top
    plot_df = service_df.head(5).iloc[::-1]

    fig.add_trace(go.Bar(
        x=plot_df["cost_amount"],
        y=plot_df["service"],
        orientation="h",
        marker=dict(
            color=PALETTE["primary"],
            line=dict(color="#38BDF8", width=1)
        ),
        text=[f"${c:,.2f} ({p:.1f}%)" for c, p in zip(plot_df["cost_amount"], plot_df["percentage"])],
        textposition="auto",
        textfont=dict(size=11, color="#FFFFFF"),
        hovertemplate=f"Service: %{{y}}<br>Cost: %{{x:$,.2f}}<extra></extra>"
    ))

    _style_figure(fig, title="")
    fig.update_layout(
        xaxis=dict(showticklabels=True, tickprefix="$" if currency == "USD" else ""),
        yaxis=dict(showgrid=False),
        margin=dict(l=10, r=10, t=10, b=10),
        height=260
    )
    return fig


def create_forecast_chart(
    historical_daily: pd.DataFrame,
    forecast_daily: pd.DataFrame,
    currency: str = "USD"
) -> go.Figure:
    """Plots historical actuals alongside future projected points with confidence bounds."""
    fig = go.Figure()

    # Historical actuals
    if not historical_daily.empty:
        fig.add_trace(go.Scatter(
            x=historical_daily["usage_date"],
            y=historical_daily["cost_amount"],
            mode="lines+markers",
            name="Historical Actuals",
            line=dict(color=PALETTE["primary"], width=2.5),
            marker=dict(size=5),
            hovertemplate="Actual: %{y:$,.2f}<extra></extra>"
        ))

    # Forecast bounds (shaded envelope)
    if not forecast_daily.empty and "upper_bound" in forecast_daily.columns:
        fig.add_trace(go.Scatter(
            x=forecast_daily["usage_date"],
            y=forecast_daily["upper_bound"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(
            x=forecast_daily["usage_date"],
            y=forecast_daily["lower_bound"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(56, 189, 248, 0.12)",
            name="95% Confidence Interval",
            hoverinfo="skip"
        ))

        # Forecast line
        fig.add_trace(go.Scatter(
            x=forecast_daily["usage_date"],
            y=forecast_daily["projected_cost"],
            mode="lines+markers",
            name="Projected Trend",
            line=dict(color="#38BDF8", width=2.5, dash="dash"),
            marker=dict(size=5, symbol="diamond"),
            hovertemplate="Projected: %{y:$,.2f}<extra></extra>"
        ))

    _style_figure(fig, title="")
    fig.update_layout(
        yaxis_tickprefix="$" if currency == "USD" else "",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def _style_figure(fig: go.Figure, title: str = "") -> None:
    """Applies unified enterprise dark theme to Plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30, 41, 59, 0.5)",
        font=dict(family="inherit", size=12, color=PALETTE["text_muted"]),
        margin=dict(l=30, r=20, t=30, b=30),
        xaxis=dict(
            showgrid=True,
            gridcolor="#334155",
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#334155",
            zeroline=False
        )
    )
