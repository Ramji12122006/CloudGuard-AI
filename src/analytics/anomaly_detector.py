"""Transparent statistical anomaly detection engine for AWS billing data."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.config import (
    DEFAULT_PCT_THRESHOLD,
    DEFAULT_ABS_THRESHOLD,
    DEFAULT_ZSCORE_THRESHOLD,
    DEFAULT_MAD_THRESHOLD,
    MIN_HISTORY_DAYS_FOR_ANOMALY,
    EVIDENCE_CONFIRMED,
    EVIDENCE_STRONGLY_SUPPORTED,
    EVIDENCE_POSSIBLE,
    EVIDENCE_INSUFFICIENT,
)


@dataclass
class AnomalyRecord:
    """Represents a validated financial anomaly finding."""
    detection_date: str
    billing_period: str
    service: str
    resource_id: Optional[str]
    actual_cost: float
    baseline_cost: float
    absolute_increase: float
    percentage_increase: Optional[float]
    detection_method: str
    trigger_reason: str
    evidence_level: str
    supporting_records_count: int = 0
    status: str = "Open"
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "detection_date": self.detection_date,
            "billing_period": self.billing_period,
            "service": self.service,
            "resource_id": self.resource_id,
            "actual_cost": round(self.actual_cost, 2),
            "baseline_cost": round(self.baseline_cost, 2),
            "absolute_increase": round(self.absolute_increase, 2),
            "percentage_increase": round(self.percentage_increase, 1) if self.percentage_increase is not None else None,
            "detection_method": self.detection_method,
            "trigger_reason": self.trigger_reason,
            "evidence_level": self.evidence_level,
            "status": self.status,
            "supporting_records_count": self.supporting_records_count
        }


class AnomalyDetector:
    """
    Statistical anomaly detector supporting rolling baselines,
    Median Absolute Deviation (MAD), and threshold rules.
    """

    def __init__(
        self,
        pct_threshold: float = DEFAULT_PCT_THRESHOLD,
        abs_threshold: float = DEFAULT_ABS_THRESHOLD,
        zscore_threshold: float = DEFAULT_ZSCORE_THRESHOLD,
        mad_threshold: float = DEFAULT_MAD_THRESHOLD,
        min_history_days: int = MIN_HISTORY_DAYS_FOR_ANOMALY
    ):
        self.pct_threshold = pct_threshold
        self.abs_threshold = abs_threshold
        self.zscore_threshold = zscore_threshold
        self.mad_threshold = mad_threshold
        self.min_history_days = min_history_days

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        target_services: Optional[List[str]] = None
    ) -> List[AnomalyRecord]:
        """
        Runs multi-method anomaly detection across daily service expenditures.
        Returns a deduplicated, ranked list of detected anomalies.
        """
        if df.empty or "usage_date" not in df.columns or "cost_amount" not in df.columns:
            return []

        # Prepare daily spend per service
        df_clean = df.copy()
        df_clean["cost_amount"] = pd.to_numeric(df_clean["cost_amount"], errors="coerce").fillna(0.0)
        daily_svc = df_clean.groupby(["usage_date", "service"])["cost_amount"].sum().reset_index()
        daily_svc.sort_values(["service", "usage_date"], inplace=True)

        unique_services = daily_svc["service"].unique()
        if target_services:
            unique_services = [s for s in unique_services if s in target_services]

        anomalies: List[AnomalyRecord] = []

        for service in unique_services:
            svc_df = daily_svc[daily_svc["service"] == service].copy()
            if len(svc_df) < 2:
                # Not enough points for meaningful comparison
                continue

            svc_anomalies = self._detect_service_anomalies(svc_df, df_clean)
            anomalies.extend(svc_anomalies)

        # Sort by largest absolute increase
        anomalies.sort(key=lambda a: a.absolute_increase, reverse=True)
        return anomalies

    def _detect_service_anomalies(
        self,
        svc_df: pd.DataFrame,
        full_df: pd.DataFrame
    ) -> List[AnomalyRecord]:
        """Analyzes a single service's daily cost history for anomalies."""
        anomalies: List[AnomalyRecord] = []
        costs = svc_df["cost_amount"].values
        dates = svc_df["usage_date"].values
        n_days = len(costs)

        # 1. Median Absolute Deviation (MAD) for robust baseline
        if n_days >= self.min_history_days:
            median_cost = float(np.median(costs))
            abs_devs = np.abs(costs - median_cost)
            mad = float(np.median(abs_devs))

            for i in range(n_days):
                curr_cost = float(costs[i])
                curr_date = str(dates[i])
                abs_inc = curr_cost - median_cost

                if abs_inc < self.abs_threshold:
                    continue

                is_anomaly = False
                method = ""
                reason = ""
                evidence = EVIDENCE_CONFIRMED

                if mad > 0.01:
                    # Modified Z-score (Iglewicz and Hoaglin)
                    mod_z = 0.6745 * abs_inc / mad
                    if mod_z >= self.mad_threshold:
                        is_anomaly = True
                        method = "Robust MAD Outlier"
                        reason = (
                            f"Daily cost of ${curr_cost:.2f} exceeded median baseline (${median_cost:.2f}) "
                            f"by ${abs_inc:.2f} (Modified Z-score: {mod_z:.1f} >= {self.mad_threshold})"
                        )
                else:
                    # If MAD is near zero (very flat baseline), check absolute & percentage
                    if median_cost > 0:
                        pct_inc = (abs_inc / median_cost) * 100.0
                        if pct_inc >= self.pct_threshold and abs_inc >= self.abs_threshold:
                            is_anomaly = True
                            method = "Percentage Surge (Flat Baseline)"
                            reason = (
                                f"Daily cost surged by {pct_inc:.1f}% (+${abs_inc:.2f}) over historical flat median (${median_cost:.2f})"
                            )
                    elif curr_cost >= self.abs_threshold:
                        is_anomaly = True
                        method = "New Service Charge"
                        reason = f"New charge of ${curr_cost:.2f} detected where historical baseline was $0.00"

                if is_anomaly:
                    # Count underlying records supporting this day and service
                    supporting_records = len(full_df[
                        (full_df["usage_date"] == curr_date) &
                        (full_df["service"] == svc_df["service"].iloc[0])
                    ])
                    pct = (abs_inc / median_cost * 100.0) if median_cost > 0 else None

                    anomalies.append(AnomalyRecord(
                        detection_date=curr_date,
                        billing_period=curr_date[:7],
                        service=str(svc_df["service"].iloc[0]),
                        resource_id=None,
                        actual_cost=curr_cost,
                        baseline_cost=median_cost,
                        absolute_increase=abs_inc,
                        percentage_increase=pct,
                        detection_method=method,
                        trigger_reason=reason,
                        evidence_level=evidence,
                        supporting_records_count=supporting_records
                    ))

        # 2. Rolling Window Comparison for short-term surges
        if not anomalies and n_days >= 3:
            for i in range(1, n_days):
                curr_cost = float(costs[i])
                curr_date = str(dates[i])
                # Baseline is preceding 1-7 days mean
                window_start = max(0, i - 7)
                baseline_slice = costs[window_start:i]
                window_mean = float(np.mean(baseline_slice))
                abs_inc = curr_cost - window_mean

                if abs_inc >= self.abs_threshold:
                    pct_inc = (abs_inc / window_mean * 100.0) if window_mean > 0 else None
                    if (pct_inc is None or pct_inc >= self.pct_threshold):
                        supporting_records = len(full_df[
                            (full_df["usage_date"] == curr_date) &
                            (full_df["service"] == svc_df["service"].iloc[0])
                        ])
                        reason = (
                            f"Daily cost (${curr_cost:.2f}) increased by ${abs_inc:.2f} "
                            f"({f'{pct_inc:.1f}%' if pct_inc else 'New charge'}) above rolling window baseline (${window_mean:.2f})"
                        )
                        anomalies.append(AnomalyRecord(
                            detection_date=curr_date,
                            billing_period=curr_date[:7],
                            service=str(svc_df["service"].iloc[0]),
                            resource_id=None,
                            actual_cost=curr_cost,
                            baseline_cost=window_mean,
                            absolute_increase=abs_inc,
                            percentage_increase=pct_inc,
                            detection_method="Rolling Baseline Spike",
                            trigger_reason=reason,
                            evidence_level=EVIDENCE_STRONGLY_SUPPORTED,
                            supporting_records_count=supporting_records
                        ))

        return anomalies
