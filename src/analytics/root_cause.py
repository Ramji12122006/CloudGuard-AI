"""Root-cause investigation engine using deterministic evidence templates."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd

from src.config import (
    EVIDENCE_CONFIRMED,
    EVIDENCE_STRONGLY_SUPPORTED,
    EVIDENCE_POSSIBLE,
    EVIDENCE_INSUFFICIENT,
)


@dataclass
class RootCauseFinding:
    """Detailed evidence-backed root cause report for a cost increase."""
    service: str
    target_date_or_period: str
    total_cost_increase: float
    top_usage_type_driver: Optional[str] = None
    top_usage_type_increase: float = 0.0
    top_region_driver: Optional[str] = None
    top_region_increase: float = 0.0
    top_resource_driver: Optional[str] = None
    top_resource_increase: float = 0.0
    quantity_change_pct: Optional[float] = None
    unit_rate_change_pct: Optional[float] = None
    data_limitations: List[str] = field(default_factory=list)
    evidence_level: str = EVIDENCE_CONFIRMED
    summary_text: str = ""
    breakdown_tables: Dict[str, pd.DataFrame] = field(default_factory=dict)


class RootCauseAnalyzer:
    """Investigates root causes of cost increases across available dimensions."""

    @classmethod
    def investigate(
        cls,
        df: pd.DataFrame,
        service: str,
        detection_date: str,
        baseline_cost: float,
        actual_cost: float
    ) -> RootCauseFinding:
        """
        Drills down into service records on the anomaly date vs preceding dates
        to identify the exact usage types, regions, and resources driving the increase.
        """
        increase_amount = actual_cost - baseline_cost
        finding = RootCauseFinding(
            service=service,
            target_date_or_period=detection_date,
            total_cost_increase=increase_amount
        )

        svc_records = df[df["service"] == service].copy()
        if svc_records.empty:
            finding.evidence_level = EVIDENCE_INSUFFICIENT
            finding.summary_text = f"No billing records found for service '{service}'."
            return finding

        # Current records on the detection date
        curr_mask = svc_records["usage_date"] == detection_date
        curr_df = svc_records[curr_mask]

        # Baseline records (all preceding dates for this service)
        prev_mask = svc_records["usage_date"] < detection_date
        prev_df = svc_records[prev_mask]

        if curr_df.empty:
            finding.evidence_level = EVIDENCE_INSUFFICIENT
            finding.summary_text = f"No detailed usage records available on {detection_date} for service '{service}'."
            return finding

        # 1. Drill-down: Usage Type analysis
        has_usage_type = "usage_type" in curr_df.columns and curr_df["usage_type"].str.len().sum() > 0
        if has_usage_type:
            curr_ut = curr_df.groupby("usage_type")["cost_amount"].sum().reset_index()
            if not prev_df.empty:
                # Average daily cost per usage type in preceding days
                prev_days_count = max(1, prev_df["usage_date"].nunique())
                prev_ut = prev_df.groupby("usage_type")["cost_amount"].sum() / prev_days_count
                prev_ut = prev_ut.reset_index().rename(columns={"cost_amount": "baseline_daily_cost"})
                merged_ut = curr_ut.merge(prev_ut, on="usage_type", how="left").fillna(0.0)
                merged_ut["increase"] = merged_ut["cost_amount"] - merged_ut["baseline_daily_cost"]
                merged_ut.sort_values("increase", ascending=False, inplace=True)
            else:
                merged_ut = curr_ut.copy()
                merged_ut["baseline_daily_cost"] = 0.0
                merged_ut["increase"] = merged_ut["cost_amount"]
                merged_ut.sort_values("increase", ascending=False, inplace=True)

            if not merged_ut.empty:
                top_row = merged_ut.iloc[0]
                finding.top_usage_type_driver = str(top_row["usage_type"])
                finding.top_usage_type_increase = float(top_row["increase"])
                finding.breakdown_tables["usage_types"] = merged_ut
        else:
            finding.data_limitations.append("Usage type dimension was not present in the billing file.")

        # 2. Drill-down: Region analysis
        has_region = "region" in curr_df.columns and curr_df["region"].nunique() > 1
        if has_region:
            curr_reg = curr_df.groupby("region")["cost_amount"].sum().reset_index()
            if not prev_df.empty:
                prev_days_count = max(1, prev_df["usage_date"].nunique())
                prev_reg = prev_df.groupby("region")["cost_amount"].sum() / prev_days_count
                prev_reg = prev_reg.reset_index().rename(columns={"cost_amount": "baseline_daily_cost"})
                merged_reg = curr_reg.merge(prev_reg, on="region", how="left").fillna(0.0)
                merged_reg["increase"] = merged_reg["cost_amount"] - merged_reg["baseline_daily_cost"]
                merged_reg.sort_values("increase", ascending=False, inplace=True)
            else:
                merged_reg = curr_reg.copy()
                merged_reg["baseline_daily_cost"] = 0.0
                merged_reg["increase"] = merged_reg["cost_amount"]
                merged_reg.sort_values("increase", ascending=False, inplace=True)

            if not merged_reg.empty:
                top_reg_row = merged_reg.iloc[0]
                finding.top_region_driver = str(top_reg_row["region"])
                finding.top_region_increase = float(top_reg_row["increase"])
                finding.breakdown_tables["regions"] = merged_reg
        else:
            finding.data_limitations.append("Regional dimension is uniform or unpopulated in the dataset.")

        # 3. Drill-down: Resource ID analysis
        has_resource_ids = "resource_id" in curr_df.columns and curr_df["resource_id"].dropna().str.len().sum() > 0
        if has_resource_ids:
            curr_res = curr_df.dropna(subset=["resource_id"]).groupby("resource_id")["cost_amount"].sum().reset_index()
            if not curr_res.empty:
                curr_res.sort_values("cost_amount", ascending=False, inplace=True)
                finding.top_resource_driver = str(curr_res.iloc[0]["resource_id"])
                finding.top_resource_increase = float(curr_res.iloc[0]["cost_amount"])
                finding.breakdown_tables["resources"] = curr_res
        else:
            finding.data_limitations.append("Resource identifiers (ARN / ResourceId) are not present in this billing export.")

        # 4. Usage Quantity vs Rate Analysis
        if "usage_quantity" in curr_df.columns and curr_df["usage_quantity"].sum() > 0:
            curr_qty = curr_df["usage_quantity"].sum()
            prev_qty_daily = prev_df["usage_quantity"].sum() / max(1, prev_df["usage_date"].nunique()) if not prev_df.empty else 0.0
            if prev_qty_daily > 0:
                finding.quantity_change_pct = ((curr_qty - prev_qty_daily) / prev_qty_daily) * 100.0

            # Unit rate check
            if curr_qty > 0 and actual_cost > 0:
                curr_rate = actual_cost / curr_qty
                prev_rate = (baseline_cost / prev_qty_daily) if (baseline_cost > 0 and prev_qty_daily > 0) else None
                if prev_rate and prev_rate > 0:
                    finding.unit_rate_change_pct = ((curr_rate - prev_rate) / prev_rate) * 100.0
        else:
            finding.data_limitations.append("Usage quantities are not recorded in this export; cannot separate volume changes from unit rate adjustments.")

        # 5. Deterministic, evidence-backed narrative generation
        finding.summary_text = cls._generate_narrative(finding, baseline_cost, actual_cost)
        return finding

    @classmethod
    def _generate_narrative(
        cls,
        finding: RootCauseFinding,
        baseline_cost: float,
        actual_cost: float
    ) -> str:
        """Constructs an unembellished, mathematically factual narrative."""
        sentences = []
        increase = finding.total_cost_increase

        sentences.append(
            f"{finding.service} expenditures increased by ${increase:,.2f} on {finding.target_date_or_period} "
            f"(actual: ${actual_cost:,.2f} vs baseline: ${baseline_cost:,.2f})."
        )

        if finding.top_usage_type_driver:
            sentences.append(
                f"The largest component of this increase was usage type '{finding.top_usage_type_driver}', "
                f"which accounted for +${finding.top_usage_type_increase:,.2f} of the surge."
            )

        if finding.top_region_driver and finding.top_region_driver != "Global/Unknown":
            sentences.append(
                f"The primary geographic region affected was '{finding.top_region_driver}'."
            )

        if finding.top_resource_driver:
            sentences.append(
                f"Resource identifier '{finding.top_resource_driver}' contributed the highest spend within this service."
            )

        if finding.quantity_change_pct is not None:
            if finding.quantity_change_pct > 15:
                sentences.append(
                    f"Measured usage quantity increased by {finding.quantity_change_pct:.1f}%, indicating higher workload volume."
                )
            elif finding.quantity_change_pct < -15:
                sentences.append(
                    f"Usage quantity decreased by {abs(finding.quantity_change_pct):.1f}% despite higher total cost."
                )

        if finding.data_limitations:
            limit_str = "; ".join(finding.data_limitations)
            sentences.append(
                f"Data limitations note: The uploaded billing export does not establish underlying external business causes ({limit_str})."
            )

        return " ".join(sentences)
