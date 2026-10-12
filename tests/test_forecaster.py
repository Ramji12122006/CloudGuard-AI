"""Automated tests for cost forecasting and eligibility checks."""
import pytest
import pandas as pd

from src.analytics.forecaster import CostForecaster


def test_mtd_run_rate_sufficient_data():
    """Verifies MTD run-rate projection for an incomplete month."""
    # 5 days in September 2026 (September has 30 days)
    # Total spend across 5 days = $100 ($20/day)
    # Expected extrapolation for 30 days = 30 * $20 = $600
    dates = [f"2026-09-{i:02d}" for i in range(1, 6)]
    data = [{"usage_date": d, "cost_amount": 20.0} for d in dates]
    df = pd.DataFrame(data)

    forecast = CostForecaster.forecast_current_month(df, target_month="2026-09")

    assert forecast.is_eligible is True
    assert forecast.current_actual_total == 100.0
    assert pytest.approx(forecast.projected_total, 1.0) == 600.0
    assert "25 remaining days" in forecast.forecast_horizon


def test_mtd_run_rate_insufficient_data():
    """Verifies that fewer than 3 days of data refuses projection."""
    # Only 2 days of data
    df = pd.DataFrame([
        {"usage_date": "2026-09-01", "cost_amount": 20.0},
        {"usage_date": "2026-09-02", "cost_amount": 20.0},
    ])

    forecast = CostForecaster.forecast_current_month(df, target_month="2026-09")

    assert forecast.is_eligible is False
    assert "Insufficient data" in (forecast.error_message or "")


def test_linear_trend_forecasting():
    """Verifies linear trend regression model on continuous daily data."""
    # 10 days of data with slope
    dates = [f"2026-09-{i:02d}" for i in range(1, 11)]
    data = [{"usage_date": d, "cost_amount": 10.0 + i} for i, d in enumerate(dates)]
    df = pd.DataFrame(data)

    forecast = CostForecaster.forecast_linear_trend(df, horizon_days=14)

    assert forecast.is_eligible is True
    assert forecast.daily_forecast_df is not None
    assert len(forecast.daily_forecast_df) == 14
    assert forecast.lower_bound is not None
    assert forecast.upper_bound is not None
    assert forecast.lower_bound <= forecast.projected_total <= forecast.upper_bound


def test_linear_trend_insufficient_data():
    """Verifies that < 7 days refuses linear trend modeling."""
    df = pd.DataFrame([
        {"usage_date": "2026-09-01", "cost_amount": 10.0},
        {"usage_date": "2026-09-02", "cost_amount": 10.0},
        {"usage_date": "2026-09-03", "cost_amount": 10.0},
    ])

    forecast = CostForecaster.forecast_linear_trend(df, horizon_days=14)

    assert forecast.is_eligible is False
    assert "Insufficient data" in (forecast.error_message or "")
