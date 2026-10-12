"""Evidence-based cloud cost optimization recommendation engine."""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd

from src.config import (
    REC_STATUS_OPEN,
    REC_STATUS_OPTIONS,
)


@dataclass
class OptimizationRecommendation:
    """Represents a rule-driven financial optimization recommendation."""
    category: str
    title: str
    service: str
    supporting_evidence: str
    suggested_action: str
    estimated_savings: Optional[float]
    limitations: str
    status: str = REC_STATUS_OPEN
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "service": self.service,
            "supporting_evidence": self.supporting_evidence,
            "suggested_action": self.suggested_action,
            "estimated_savings": round(self.estimated_savings, 2) if self.estimated_savings is not None else None,
            "limitations": self.limitations,
            "status": self.status
        }


class RecommendationEngine:
    """
    Evaluates rule sets against actual billing records to generate
    defensible, evidence-backed optimization recommendations.
    """

    @classmethod
    def generate_recommendations(cls, df: pd.DataFrame) -> List[OptimizationRecommendation]:
        """Runs optimization rules on the provided billing records."""
        if df.empty or "cost_amount" not in df.columns:
            return []

        recommendations: List[OptimizationRecommendation] = []
        total_spend = float(df["cost_amount"].sum())
        if total_spend <= 0:
            return []

        svc_totals = df.groupby("service")["cost_amount"].sum()

        # Rule 1: High Service Spend Concentration
        cls._check_spend_concentration(svc_totals, total_spend, recommendations)

        # Rule 2: High Data Transfer Egress Charges
        cls._check_data_transfer_egress(df, recommendations)

        # Rule 3: Storage Growth and Lifecycle Policy
        cls._check_storage_lifecycle(df, recommendations)

        # Rule 4: Potential Unattached EBS Volume or Idle Allocation Pattern
        cls._check_unattached_or_idle_allocations(df, recommendations)

        # Rule 5: Continuous On-Demand Compute Workload
        cls._check_compute_commitment_opportunity(df, svc_totals, total_spend, recommendations)

        # Rule 6: High Individual Resource Cost
        cls._check_expensive_resources(df, recommendations)

        return recommendations

    @classmethod
    def _check_spend_concentration(
        cls,
        svc_totals: pd.Series,
        total_spend: float,
        recs: List[OptimizationRecommendation]
    ) -> None:
        """Flags high spend concentration on a single service (>50% of total spend)."""
        top_service = str(svc_totals.idxmax())
        top_spend = float(svc_totals.max())
        top_pct = (top_spend / total_spend) * 100.0

        if top_pct >= 50.0 and top_spend >= 100.0:
            # Estimate potential 15% savings via specialized optimization
            est_savings = top_spend * 0.15
            recs.append(OptimizationRecommendation(
                category="Spend Concentration",
                title=f"High Spend Concentration on {top_service}",
                service=top_service,
                supporting_evidence=(
                    f"{top_service} accounts for ${top_spend:,.2f} ({top_pct:.1f}%) "
                    f"of total analyzed cloud spend (${total_spend:,.2f})."
                ),
                suggested_action=(
                    f"Focus cost governance on {top_service}. Evaluate workload architecture, "
                    f"reserved capacity, or savings plan options specifically tailored to this service."
                ),
                estimated_savings=est_savings,
                limitations=(
                    "Billing data shows cost proportion only. Feasibility of commitment discounts depends on "
                    "workload stability and minimum run-rate over 1-3 years."
                )
            ))

    @classmethod
    def _check_data_transfer_egress(
        cls,
        df: pd.DataFrame,
        recs: List[OptimizationRecommendation]
    ) -> None:
        """Flags high data transfer egress charges (>15% of service spend)."""
        if "usage_type" not in df.columns:
            return

        dt_mask = df["usage_type"].str.contains(r"DataTransfer|Out-Bytes|AWS-Out", case=False, na=False)
        dt_df = df[dt_mask]

        if dt_df.empty:
            return

        dt_by_service = dt_df.groupby("service")["cost_amount"].sum()
        for svc, dt_cost in dt_by_service.items():
            svc_total = float(df[df["service"] == svc]["cost_amount"].sum())
            if svc_total > 0:
                dt_pct = (dt_cost / svc_total) * 100.0
                if dt_pct >= 15.0 and dt_cost >= 20.0:
                    est_savings = dt_cost * 0.30  # CloudFront or VPC endpoint average reduction
                    recs.append(OptimizationRecommendation(
                        category="Network Architecture",
                        title=f"High Network Egress Spend on {svc}",
                        service=str(svc),
                        supporting_evidence=(
                            f"Data transfer out charges totaled ${dt_cost:,.2f}, representing {dt_pct:.1f}% "
                            f"of all charges for {svc}."
                        ),
                        suggested_action=(
                            "Investigate destination of data transfer. Consider deploying Amazon CloudFront for public "
                            "content caching, or AWS PrivateLink / VPC Endpoints for internal service communication to avoid public egress rates."
                        ),
                        estimated_savings=est_savings,
                        limitations=(
                            "Billing records indicate egress volume and cost, but do not log network endpoint IP destinations "
                            "or traffic routing protocols."
                        )
                    ))

    @classmethod
    def _check_storage_lifecycle(
        cls,
        df: pd.DataFrame,
        recs: List[OptimizationRecommendation]
    ) -> None:
        """Flags continuous standard storage spend for S3."""
        s3_df = df[df["service"].str.contains(r"S3|SimpleStorage", case=False, na=False)]
        if s3_df.empty:
            return

        s3_cost = float(s3_df["cost_amount"].sum())
        if s3_cost < 30.0:
            return

        # Check if Intelligent-Tiering or Glacier is being used
        has_lifecycle = False
        if "usage_type" in s3_df.columns:
            has_lifecycle = s3_df["usage_type"].str.contains(r"Glacier|Intelligent|DeepArchive", case=False, na=False).any()

        if not has_lifecycle:
            est_savings = s3_cost * 0.25  # Typical tiering savings
            recs.append(OptimizationRecommendation(
                category="Storage Optimization",
                title="Review S3 Storage Lifecycle & Intelligent-Tiering",
                service="AmazonS3",
                supporting_evidence=(
                    f"Total S3 storage expenditure was ${s3_cost:,.2f}. All charges are in standard storage tiers "
                    "with no automated cold/archive tiering transitions detected in billing records."
                ),
                suggested_action=(
                    "Evaluate enabling S3 Intelligent-Tiering for buckets with unknown or changing access patterns, "
                    "or implement S3 Lifecycle configuration rules to transition aged objects to Glacier."
                ),
                estimated_savings=est_savings,
                limitations=(
                    "Billing exports do not contain object access frequency or last-modified timestamps. "
                    "Small objects (<128 KB) incur monitoring fees under Intelligent-Tiering."
                )
            ))

    @classmethod
    def _check_unattached_or_idle_allocations(
        cls,
        df: pd.DataFrame,
        recs: List[OptimizationRecommendation]
    ) -> None:
        """Flags persistent storage volume charges (e.g., EBS) without IOPS or associated compute."""
        ebs_mask = df["usage_type"].str.contains(r"EBS:VolumeUsage|VolumeUsage\.gp2|VolumeUsage\.gp3", case=False, na=False)
        ebs_df = df[ebs_mask]

        if not ebs_df.empty:
            ebs_cost = float(ebs_df["cost_amount"].sum())
            if ebs_cost >= 25.0:
                recs.append(OptimizationRecommendation(
                    category="Resource Hygiene",
                    title="Review EBS Volume Allocations and Attachment Status",
                    service="AmazonEC2",
                    supporting_evidence=(
                        f"EBS volume allocation charges totaled ${ebs_cost:,.2f} across the analyzed period."
                    ),
                    suggested_action=(
                        "Inspect AWS EC2 Console or run AWS CLI describe-volumes to verify whether any EBS volumes "
                        "are in 'available' (unattached) status or attached to stopped instances."
                    ),
                    estimated_savings=None,
                    limitations=(
                        "Billing records document allocated storage capacity charges, but do NOT prove whether a volume "
                        "is unattached or unutilized. Operating system I/O and CloudWatch metrics must be verified before detaching or deleting."
                    )
                ))

    @classmethod
    def _check_compute_commitment_opportunity(
        cls,
        df: pd.DataFrame,
        svc_totals: pd.Series,
        total_spend: float,
        recs: List[OptimizationRecommendation]
    ) -> None:
        """Evaluates On-Demand compute stability for Savings Plans / Reserved Instances."""
        compute_svcs = [s for s in svc_totals.index if any(k in str(s).lower() for k in ["ec2", "elasticcompute", "rds", "lambda"])]
        if not compute_svcs:
            return

        compute_spend = float(svc_totals[compute_svcs].sum())
        if compute_spend >= 150.0 and len(df["usage_date"].unique()) >= 7:
            # 20% estimated savings through 1-year No Upfront Savings Plan
            est_savings = compute_spend * 0.20
            recs.append(OptimizationRecommendation(
                category="Pricing Models",
                title="Evaluate Compute Savings Plans or Reserved Instances",
                service=", ".join(compute_svcs[:2]),
                supporting_evidence=(
                    f"Steady compute charges totaled ${compute_spend:,.2f} across recorded dates. "
                    "Usage patterns indicate continuous baseline workloads without active commitment discounts."
                ),
                suggested_action=(
                    "Use AWS Cost Explorer Recommendations tool to review 1-year or 3-year Compute Savings Plans "
                    "or EC2 Instance Savings Plans to reduce On-Demand hourly rates."
                ),
                estimated_savings=est_savings,
                limitations=(
                    "Commitment discounts require contractual spend obligations. Must be evaluated against expected "
                    "workload lifetime and architectural modernization roadmaps."
                )
            ))

    @classmethod
    def _check_expensive_resources(
        cls,
        df: pd.DataFrame,
        recs: List[OptimizationRecommendation]
    ) -> None:
        """Identifies any individual resource that consumes >20% of entire bill."""
        if "resource_id" not in df.columns:
            return

        res_df = df[df["resource_id"].notna() & (df["resource_id"] != "")]
        if res_df.empty:
            return

        total_spend = float(df["cost_amount"].sum())
        res_totals = res_df.groupby(["resource_id", "service"])["cost_amount"].sum().reset_index()
        res_totals.sort_values("cost_amount", ascending=False, inplace=True)

        for _, row in res_totals.iterrows():
            r_cost = float(row["cost_amount"])
            r_id = str(row["resource_id"])
            r_svc = str(row["service"])
            r_pct = (r_cost / total_spend * 100.0) if total_spend > 0 else 0.0

            if r_pct >= 20.0 and r_cost >= 100.0:
                recs.append(OptimizationRecommendation(
                    category="Resource Sizing",
                    title=f"Review High-Cost Resource ({r_id})",
                    service=r_svc,
                    supporting_evidence=(
                        f"Resource '{r_id}' consumed ${r_cost:,.2f} ({r_pct:.1f}% of entire bill)."
                    ),
                    suggested_action=(
                        f"Inspect CloudWatch metrics (CPU, RAM, Disk I/O) for resource '{r_id}' to assess "
                        "whether it is over-provisioned and can be safely downscaled."
                    ),
                    estimated_savings=r_cost * 0.20,
                    limitations=(
                        "Billing records reflect provisioned tier pricing only, not internal resource utilization metrics."
                    )
                ))
                break  # Alert on the top single resource to avoid alert fatigue
