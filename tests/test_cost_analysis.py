"""Automated tests for cost aggregation, period comparisons, and concentration metrics."""
import pytest
import pandas as pd

from src.analytics.cost_engine import CostEngine


def test_period_metrics_calculation(synthetic_normalized_df):
    """Verifies total cost, previous period comparison, and highest-cost service."""
    # Current period: 2026-09-02 to 2026-09-03 (2 days, $60 total)
    # Previous period: 2026-08-31 to 2026-09-01 (2 days, $30 total recorded on 09-01)
    metrics = CostEngine.calculate_period_metrics(
        synthetic_normalized_df,
        start_date="2026-09-02",
        end_date="2026-09-03",
        currency="USD"
    )

    assert metrics.total_cost == 60.0
    assert metrics.previous_cost == 30.0
    assert metrics.absolute_change == 30.0
    # Increase from 30 to 60 is +100%
    assert pytest.approx(metrics.percentage_change, 0.1) == 100.0
    assert metrics.is_favorable is False
    assert metrics.highest_cost_service == "AmazonRDS"
    assert metrics.highest_cost_service_amount == 40.0


def test_zero_division_percentage_change():
    """Verifies correct edge case handling when previous-period spend is zero."""
    df = pd.DataFrame([
        {"usage_date": "2026-09-02", "service": "AmazonEC2", "cost_amount": 50.0},
    ])
    metrics = CostEngine.calculate_period_metrics(
        df,
        start_date="2026-09-02",
        end_date="2026-09-02"
    )

    assert metrics.total_cost == 50.0
    # Prior day 2026-09-01 had 0.0 spend
    assert metrics.previous_cost == 0.0
    assert metrics.percentage_change is None
    assert "New spend" in metrics.change_description


def test_daily_trend_alignment(synthetic_normalized_df):
    """Verifies continuous daily trend alignment with previous period."""
    trend_df = CostEngine.get_daily_trend(
        synthetic_normalized_df,
        start_date="2026-09-02",
        end_date="2026-09-03"
    )

    assert len(trend_df) == 2
    assert "cost" in trend_df.columns
    assert "previous_cost" in trend_df.columns
    assert trend_df["cost"].sum() == 60.0


def test_cost_by_service_breakdown(synthetic_normalized_df):
    """Verifies service breakdown rankings and percentage shares."""
    svc_df = CostEngine.get_cost_by_service(synthetic_normalized_df)

    assert len(svc_df) == 2
    assert svc_df.iloc[0]["service"] == "AmazonRDS"
    assert svc_df.iloc[0]["cost_amount"] == 60.0
    assert pytest.approx(svc_df.iloc[0]["percentage"], 0.1) == 66.7

    assert svc_df.iloc[1]["service"] == "AmazonEC2"
    assert svc_df.iloc[1]["cost_amount"] == 30.0
    assert pytest.approx(svc_df.iloc[1]["percentage"], 0.1) == 33.3


def test_cost_concentration_hhi():
    """Verifies Herfindahl-Hirschman Index and portfolio concentration calculation."""
    # 70% Service A, 30% Service B
    # HHI = 70^2 + 30^2 = 4900 + 900 = 5800 (High Concentration)
    df = pd.DataFrame([
        {"service": "AmazonEC2", "cost_amount": 70.0},
        {"service": "AmazonS3", "cost_amount": 30.0},
    ])
    conc = CostEngine.get_cost_concentration(df)

    assert conc["top3_pct"] == 100.0
    assert conc["hhi"] == 5800.0
    assert conc["tier"] == "High Concentration"
