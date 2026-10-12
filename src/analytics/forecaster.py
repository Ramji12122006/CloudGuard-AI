"""Explainable cost forecasting module for month-to-date run-rate and time-series projections."""
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.config import MIN_DAYS_FOR_RUN_RATE, MIN_DAYS_FOR_DAILY_FORECAST, DEFAULT_FORECAST_DAYS


@dataclass
class ForecastResult:
    """Encapsulates forecasting outcome, bounds, and transparency disclosures."""
    is_eligible: bool
    method_name: str
    projected_total: float
    current_actual_total: float
    forecast_horizon: str
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    confidence_level: str = "Medium"
    method_explanation: str = ""
    assumptions_and_limitations: List[str] = field(default_factory=list)
    daily_forecast_df: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None


class CostForecaster:
    """Generates explainable run-rate and trend forecasts."""

    @classmethod
    def forecast_current_month(
        cls,
        df: pd.DataFrame,
        target_month: Optional[str] = None
    ) -> ForecastResult:
        """
        Projects month-to-date run-rate for the latest or specified billing month.
        Requires at least MIN_DAYS_FOR_RUN_RATE days of data.
        """
        if df.empty or "usage_date" not in df.columns or "cost_amount" not in df.columns:
            return ForecastResult(
                is_eligible=False,
                method_name="Month-to-Date Run-Rate",
                projected_total=0.0,
                current_actual_total=0.0,
                forecast_horizon="None",
                error_message="Insufficient data: Dataset is empty."
            )

        df_copy = df.copy()
        df_copy["usage_date_dt"] = pd.to_datetime(df_copy["usage_date"]).dt.date
        df_copy["billing_period"] = df_copy["usage_date"].str.slice(0, 7)

        # Determine target month
        if not target_month:
            target_month = str(df_copy["billing_period"].max())

        month_df = df_copy[df_copy["billing_period"] == target_month]
        if month_df.empty:
            return ForecastResult(
                is_eligible=False,
                method_name="Month-to-Date Run-Rate",
                projected_total=0.0,
                current_actual_total=0.0,
                forecast_horizon=f"Month {target_month}",
                error_message=f"No billing data found for month {target_month}."
            )

        daily_spend = month_df.groupby("usage_date_dt")["cost_amount"].sum().sort_index()
        days_recorded = len(daily_spend)

        if days_recorded < MIN_DAYS_FOR_RUN_RATE:
            return ForecastResult(
                is_eligible=False,
                method_name="Month-to-Date Run-Rate",
                projected_total=0.0,
                current_actual_total=float(daily_spend.sum()),
                forecast_horizon=f"Month {target_month}",
                error_message=(
                    f"Insufficient data: Month {target_month} has only {days_recorded} recorded day(s). "
                    f"A minimum of {MIN_DAYS_FOR_RUN_RATE} days is required for reliable extrapolation."
                )
            )

        # Days in target month
        year, month = map(int, target_month.split("-"))
        _, days_in_month = monthrange(year, month)

        actual_mtd_cost = float(daily_spend.sum())

        if days_recorded >= days_in_month:
            # Full month is already completed
            return ForecastResult(
                is_eligible=True,
                method_name="Completed Month Actuals",
                projected_total=actual_mtd_cost,
                current_actual_total=actual_mtd_cost,
                forecast_horizon=f"Completed {target_month} (all {days_in_month} days present)",
                lower_bound=actual_mtd_cost,
                upper_bound=actual_mtd_cost,
                confidence_level="High",
                method_explanation=f"All {days_in_month} calendar days for {target_month} are recorded. Forecast equals actual spend.",
                assumptions_and_limitations=["Historical billing records for this period are complete."]
            )

        # Incomplete month: extrapolate remaining days
        remaining_days = days_in_month - days_recorded
        # Use recent 7-day weighted rate if available, else average daily
        recent_window = min(7, days_recorded)
        recent_daily_avg = float(daily_spend.tail(recent_window).mean())
        overall_daily_avg = actual_mtd_cost / days_recorded

        # Blended run-rate: 60% recent average + 40% overall average
        blended_daily_rate = (0.6 * recent_daily_avg) + (0.4 * overall_daily_avg)
        projected_future_spend = blended_daily_rate * remaining_days
        projected_total = actual_mtd_cost + projected_future_spend

        # Standard error of daily spend for uncertainty intervals
        daily_std = float(daily_spend.std()) if days_recorded > 1 else (overall_daily_avg * 0.15)
        margin_of_error = 1.96 * (daily_std / np.sqrt(days_recorded)) * remaining_days

        lower_bound = max(actual_mtd_cost, projected_total - margin_of_error)
        upper_bound = projected_total + margin_of_error

        horizon = f"{remaining_days} remaining days in {target_month}"
        explanation = (
            f"Based on {days_recorded} observed days in {target_month} averaging ${overall_daily_avg:.2f}/day "
            f"(recent {recent_window}-day pace: ${recent_daily_avg:.2f}/day). "
            f"Extrapolates remaining {remaining_days} days."
        )

        limitations = [
            "Assumes continuous workload run-rates without sudden planned decommissioning or scaling.",
            "Does not account for non-linear end-of-month volume discount tier resets.",
            "Unexpected spikes or resource termination will alter final billing totals."
        ]

        return ForecastResult(
            is_eligible=True,
            method_name="Month-to-Date Weighted Run-Rate",
            projected_total=round(projected_total, 2),
            current_actual_total=round(actual_mtd_cost, 2),
            forecast_horizon=horizon,
            lower_bound=round(lower_bound, 2),
            upper_bound=round(upper_bound, 2),
            confidence_level="Medium" if days_recorded >= 10 else "Low",
            method_explanation=explanation,
            assumptions_and_limitations=limitations
        )

    @classmethod
    def forecast_linear_trend(
        cls,
        df: pd.DataFrame,
        horizon_days: int = DEFAULT_FORECAST_DAYS
    ) -> ForecastResult:
        """
        Fits a linear regression model on daily total spend across the entire dataset
        and projects future daily costs with uncertainty bounds.
        """
        if df.empty or "usage_date" not in df.columns or "cost_amount" not in df.columns:
            return ForecastResult(
                is_eligible=False,
                method_name="Linear Trend Regression",
                projected_total=0.0,
                current_actual_total=0.0,
                forecast_horizon="None",
                error_message="Insufficient data: Dataset is empty."
            )

        daily = df.groupby("usage_date")["cost_amount"].sum().reset_index()
        daily.sort_values("usage_date", inplace=True)
        n_points = len(daily)

        if n_points < MIN_DAYS_FOR_DAILY_FORECAST:
            return ForecastResult(
                is_eligible=False,
                method_name="Linear Trend Regression",
                projected_total=0.0,
                current_actual_total=float(daily["cost_amount"].sum()),
                forecast_horizon=f"Next {horizon_days} days",
                error_message=(
                    f"Insufficient data: Only {n_points} distinct days recorded. "
                    f"A minimum of {MIN_DAYS_FOR_DAILY_FORECAST} days is required for trend modeling."
                )
            )

        # Prepare X and y
        daily["day_index"] = np.arange(n_points)
        X = daily[["day_index"]].values
        y = daily["cost_amount"].values

        model = LinearRegression()
        model.fit(X, y)

        # Residual standard error
        preds_hist = model.predict(X)
        residuals = y - preds_hist
        rse = float(np.std(residuals))

        # Project future days
        future_indices = np.arange(n_points, n_points + horizon_days).reshape(-1, 1)
        future_daily_preds = model.predict(future_indices)
        # Ensure non-negative costs
        future_daily_preds = np.maximum(future_daily_preds, 0.0)

        # Generate future dates
        last_date = datetime.strptime(str(daily["usage_date"].iloc[-1]), "%Y-%m-%d").date()
        future_dates = [(last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(horizon_days)]

        forecast_df = pd.DataFrame({
            "usage_date": future_dates,
            "projected_cost": future_daily_preds,
            "lower_bound": np.maximum(0.0, future_daily_preds - 1.96 * rse),
            "upper_bound": future_daily_preds + 1.96 * rse
        })

        projected_total = float(future_daily_preds.sum())
        current_total = float(y.sum())
        margin = 1.96 * rse * np.sqrt(horizon_days)

        return ForecastResult(
            is_eligible=True,
            method_name="Ordinary Least Squares Trend Regression",
            projected_total=round(projected_total, 2),
            current_actual_total=round(current_total, 2),
            forecast_horizon=f"Next {horizon_days} days ({future_dates[0]} to {future_dates[-1]})",
            lower_bound=round(max(0.0, projected_total - margin), 2),
            upper_bound=round(projected_total + margin, 2),
            confidence_level="Medium",
            method_explanation=(
                f"Trained OLS model on {n_points} historical daily observations. "
                f"Daily trend slope: ${model.coef_[0]:+.2f}/day. "
                f"Residual std error: ${rse:.2f}."
            ),
            assumptions_and_limitations=[
                "Linear model assumes consistent ongoing spend trajectory.",
                "Does not forecast sudden step-function architecture migrations or price revisions.",
                "Prediction intervals widen further into the future."
            ],
            daily_forecast_df=forecast_df
        )
