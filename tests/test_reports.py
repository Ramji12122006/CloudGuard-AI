"""Automated tests for report export generation and executive summaries."""
import pytest
import pandas as pd

from src.analytics.cost_engine import PeriodMetrics
from src.analytics.anomaly_detector import AnomalyRecord
from src.analytics.forecaster import ForecastResult
from src.analytics.recommender import OptimizationRecommendation
from src.reports.exporter import ReportExporter


def test_export_cost_summary_csv():
    """Verifies that cost summary CSV exports correctly."""
    metrics = PeriodMetrics(
        total_cost=1500.0,
        previous_cost=1200.0,
        absolute_change=300.0,
        percentage_change=25.0,
        change_description="+$300.00 (+25.0%)",
        highest_cost_service="AmazonEC2",
        highest_cost_service_amount=900.0,
        currency="USD"
    )
    csv_str = ReportExporter.export_cost_summary_csv(metrics, "2026-09-01 to 2026-09-30")

    assert "Total Cloud Cost" in csv_str
    assert "1500.00" in csv_str
    assert "AmazonEC2" in csv_str
    assert "Actual Spend" in csv_str


def test_export_anomalies_csv():
    """Verifies that anomalies CSV exports properly."""
    anomalies = [
        AnomalyRecord(
            detection_date="2026-09-11",
            billing_period="2026-09",
            service="AmazonEC2",
            resource_id="i-12345",
            actual_cost=100.0,
            baseline_cost=20.0,
            absolute_increase=80.0,
            percentage_increase=400.0,
            detection_method="MAD Outlier",
            trigger_reason="Spike",
            evidence_level="Confirmed by billing data"
        )
    ]
    csv_str = ReportExporter.export_anomalies_csv(anomalies)

    assert "detection_date" in csv_str
    assert "AmazonEC2" in csv_str
    assert "MAD Outlier" in csv_str
    assert "80.0" in csv_str


def test_executive_summary_markdown():
    """Verifies executive markdown audit report generation."""
    metrics = PeriodMetrics(
        total_cost=2500.0,
        previous_cost=2000.0,
        absolute_change=500.0,
        percentage_change=25.0,
        change_description="+$500.00 (+25.0%)",
        highest_cost_service="AmazonEC2",
        highest_cost_service_amount=1500.0,
        currency="USD"
    )
    svc_df = pd.DataFrame([
        {"service": "AmazonEC2", "cost_amount": 1500.0, "percentage": 60.0},
        {"service": "AmazonRDS", "cost_amount": 1000.0, "percentage": 40.0},
    ])
    md = ReportExporter.generate_executive_summary_markdown(
        dataset_name="Production Q3",
        period_label="2026-09-01 to 2026-09-30",
        cost_measure="UnblendedCost",
        currency="USD",
        metrics=metrics,
        top_services_df=svc_df,
        anomalies=[],
        forecast=None
    )

    assert "# CloudGuard AI Executive Cost Report" in md
    assert "Production Q3" in md
    assert "$2,500.00" in md
    assert "AmazonEC2" in md
    assert "Important Data Limitations" in md
