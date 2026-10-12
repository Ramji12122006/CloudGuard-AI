"""Cost calculation engine for period-over-period comparisons, breakdowns, and concentration metrics."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class PeriodMetrics:
    """Core financial metrics for the selected period."""
    total_cost: float
    previous_cost: Optional[float]
    absolute_change: Optional[float]
    percentage_change: Optional[float]
    change_description: str
    highest_cost_service: Optional[str]
    highest_cost_service_amount: float
    currency: str = "USD"
    is_favorable: Optional[bool] = None  # True if spending decreased, False if increased


class CostEngine:
    """Performs financial calculations across billing dimensions."""

    @staticmethod
    def format_currency(amount: Optional[float], currency: str = "USD") -> str:
        """Formats a float as a professional currency string."""
        if amount is None or pd.isna(amount):
            return "N/A"
        symbol = "$" if currency.upper() == "USD" else (f"{currency} " if currency else "$")
        if abs(amount) >= 1_000_000:
            return f"{symbol}{amount:,.2f}"
        return f"{symbol}{amount:,.2f}"

    @classmethod
    def calculate_period_metrics(
        cls,
        df: pd.DataFrame,
        start_date: str,
        end_date: str,
        currency: str = "USD"
    ) -> PeriodMetrics:
        """
        Calculates total cost, previous period comparison, and highest-cost service.
        Gracefully handles zero-division and missing historical periods.
        """
        if df.empty:
            return PeriodMetrics(
                total_cost=0.0,
                previous_cost=None,
                absolute_change=None,
                percentage_change=None,
                change_description="No data available for selected period",
                highest_cost_service=None,
                highest_cost_service_amount=0.0,
                currency=currency
            )

        # Ensure datetime parsing
        df_copy = df.copy()
        df_copy["usage_date_dt"] = pd.to_datetime(df_copy["usage_date"]).dt.date
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        if s_date > e_date:
            s_date, e_date = e_date, s_date

        period_mask = (df_copy["usage_date_dt"] >= s_date) & (df_copy["usage_date_dt"] <= e_date)
        period_df = df_copy[period_mask]
        total_cost = float(period_df["cost_amount"].sum()) if not period_df.empty else 0.0

        # Calculate previous period matching duration
        duration_days = (e_date - s_date).days + 1
        prev_end_date = s_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=duration_days - 1)

        prev_mask = (df_copy["usage_date_dt"] >= prev_start_date) & (df_copy["usage_date_dt"] <= prev_end_date)
        prev_df = df_copy[prev_mask]

        previous_cost: Optional[float] = None
        absolute_change: Optional[float] = None
        percentage_change: Optional[float] = None
        change_desc = "No prior period data available"
        is_favorable: Optional[bool] = None

        if not prev_df.empty or prev_start_date >= df_copy["usage_date_dt"].min():
            previous_cost = float(prev_df["cost_amount"].sum()) if not prev_df.empty else 0.0
            absolute_change = total_cost - previous_cost

            if previous_cost > 0:
                percentage_change = (absolute_change / previous_cost) * 100.0
                sign = "+" if absolute_change > 0 else ""
                change_desc = f"{sign}{cls.format_currency(absolute_change, currency)} ({sign}{percentage_change:.1f}%)"
                is_favorable = absolute_change < 0
            elif previous_cost == 0 and total_cost > 0:
                percentage_change = None
                change_desc = f"+{cls.format_currency(total_cost, currency)} (New spend; prior period was 0.00)"
                is_favorable = False
            else:
                percentage_change = 0.0
                change_desc = "No change (0.00 in both periods)"
                is_favorable = None

        # Highest-cost service
        highest_service: Optional[str] = None
        highest_amount = 0.0
        if not period_df.empty:
            service_sums = period_df.groupby("service")["cost_amount"].sum().sort_values(ascending=False)
            if not service_sums.empty:
                highest_service = str(service_sums.index[0])
                highest_amount = float(service_sums.iloc[0])

        return PeriodMetrics(
            total_cost=total_cost,
            previous_cost=previous_cost,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            change_description=change_desc,
            highest_cost_service=highest_service,
            highest_cost_service_amount=highest_amount,
            currency=currency,
            is_favorable=is_favorable
        )

    @classmethod
    def get_daily_trend(
        cls,
        df: pd.DataFrame,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Computes daily expenditure trend for current period and aligns previous period for comparison.
        """
        if df.empty:
            return pd.DataFrame(columns=["usage_date", "cost_amount", "previous_cost"])

        df_copy = df.copy()
        df_copy["usage_date_dt"] = pd.to_datetime(df_copy["usage_date"]).dt.date
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        duration_days = (e_date - s_date).days + 1
        prev_end_date = s_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=duration_days - 1)

        # Current period daily
        curr_mask = (df_copy["usage_date_dt"] >= s_date) & (df_copy["usage_date_dt"] <= e_date)
        curr_daily = df_copy[curr_mask].groupby("usage_date_dt")["cost_amount"].sum().reset_index()
        curr_daily.rename(columns={"usage_date_dt": "date", "cost_amount": "cost"}, inplace=True)

        # Prior period daily
        prev_mask = (df_copy["usage_date_dt"] >= prev_start_date) & (df_copy["usage_date_dt"] <= prev_end_date)
        prev_daily = df_copy[prev_mask].groupby("usage_date_dt")["cost_amount"].sum().reset_index()
        prev_daily.sort_values("usage_date_dt", inplace=True)

        # Create full continuous date range for current period
        all_curr_dates = [s_date + timedelta(days=i) for i in range(duration_days)]
        trend_df = pd.DataFrame({"date": all_curr_dates})
        trend_df = trend_df.merge(curr_daily, on="date", how="left").fillna({"cost": 0.0})

        # Attach previous period aligned by day index (0..N)
        prev_costs = prev_daily["cost_amount"].tolist() if not prev_daily.empty else []
        aligned_prev = []
        for i in range(len(trend_df)):
            if i < len(prev_costs):
                aligned_prev.append(float(prev_costs[i]))
            else:
                aligned_prev.append(None)
        trend_df["previous_cost"] = aligned_prev
        trend_df["usage_date"] = trend_df["date"].astype(str)

        return trend_df[["usage_date", "cost", "previous_cost"]]

    @classmethod
    def get_monthly_trend(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Computes monthly aggregate expenditure trends."""
        if df.empty:
            return pd.DataFrame(columns=["billing_period", "cost_amount"])
        grouped = df.groupby("billing_period")["cost_amount"].sum().reset_index()
        return grouped.sort_values("billing_period")

    @classmethod
    def get_cost_by_service(
        cls,
        df: pd.DataFrame,
        top_n: Optional[int] = None
    ) -> pd.DataFrame:
        """Returns aggregated costs per AWS service with percentages."""
        if df.empty:
            return pd.DataFrame(columns=["service", "cost_amount", "percentage"])

        totals = df.groupby("service")["cost_amount"].sum().reset_index()
        total_sum = totals["cost_amount"].sum()
        totals["percentage"] = (totals["cost_amount"] / total_sum * 100.0) if total_sum > 0 else 0.0
        totals = totals.sort_values("cost_amount", ascending=False)

        if top_n and len(totals) > top_n:
            top_records = totals.head(top_n).copy()
            other_cost = totals.iloc[top_n:]["cost_amount"].sum()
            other_pct = (other_cost / total_sum * 100.0) if total_sum > 0 else 0.0
            other_row = pd.DataFrame([{"service": "Other Services", "cost_amount": other_cost, "percentage": other_pct}])
            return pd.concat([top_records, other_row], ignore_index=True)

        return totals

    @classmethod
    def get_cost_by_region(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Returns cost grouped by AWS Region."""
        if df.empty:
            return pd.DataFrame(columns=["region", "cost_amount", "percentage"])
        totals = df.groupby("region")["cost_amount"].sum().reset_index()
        total_sum = totals["cost_amount"].sum()
        totals["percentage"] = (totals["cost_amount"] / total_sum * 100.0) if total_sum > 0 else 0.0
        return totals.sort_values("cost_amount", ascending=False)

    @classmethod
    def get_cost_by_usage_type(cls, df: pd.DataFrame, service: Optional[str] = None, top_n: int = 10) -> pd.DataFrame:
        """Returns cost grouped by usage type, optionally filtered by a specific service."""
        sub = df if not service else df[df["service"] == service]
        if sub.empty:
            return pd.DataFrame(columns=["usage_type", "cost_amount", "percentage"])
        totals = sub.groupby("usage_type")["cost_amount"].sum().reset_index()
        total_sum = totals["cost_amount"].sum()
        totals["percentage"] = (totals["cost_amount"] / total_sum * 100.0) if total_sum > 0 else 0.0
        totals = totals.sort_values("cost_amount", ascending=False)
        return totals.head(top_n)

    @classmethod
    def get_cost_by_resource(cls, df: pd.DataFrame, service: Optional[str] = None, top_n: int = 15) -> pd.DataFrame:
        """Returns cost grouped by resource_id if available."""
        sub = df[df["resource_id"].notna() & (df["resource_id"] != "")]
        if service:
            sub = sub[sub["service"] == service]
        if sub.empty:
            return pd.DataFrame(columns=["resource_id", "service", "cost_amount", "percentage"])
        totals = sub.groupby(["resource_id", "service"])["cost_amount"].sum().reset_index()
        total_sum = totals["cost_amount"].sum()
        totals["percentage"] = (totals["cost_amount"] / total_sum * 100.0) if total_sum > 0 else 0.0
        totals = totals.sort_values("cost_amount", ascending=False)
        return totals.head(top_n)

    @classmethod
    def get_cost_concentration(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates spending concentration using Top 3 ratio and Herfindahl-Hirschman Index (HHI).
        HHI scale: < 1500 (diversified), 1500-2500 (moderate concentration), > 2500 (high concentration).
        """
        if df.empty:
            return {"top3_pct": 0.0, "hhi": 0.0, "tier": "No data", "top_services": []}

        svc_totals = df.groupby("service")["cost_amount"].sum()
        total_spend = svc_totals.sum()
        if total_spend <= 0:
            return {"top3_pct": 0.0, "hhi": 0.0, "tier": "Zero spend", "top_services": []}

        shares = (svc_totals / total_spend) * 100.0
        sorted_shares = shares.sort_values(ascending=False)

        top3_pct = float(sorted_shares.head(3).sum())
        hhi = float((shares ** 2).sum())

        if hhi > 2500:
            tier = "High Concentration"
        elif hhi >= 1500:
            tier = "Moderate Concentration"
        else:
            tier = "Diversified"

        return {
            "top3_pct": round(top3_pct, 1),
            "hhi": round(hhi, 1),
            "tier": tier,
            "top_services": sorted_shares.head(3).to_dict()
        }
