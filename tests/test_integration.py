"""End-to-end integration test covering the complete CloudGuard AI lifecycle."""
import pytest
from src.importer.parser import BillingParser
from src.analytics.cost_engine import CostEngine
from src.analytics.anomaly_detector import AnomalyDetector
from src.analytics.root_cause import RootCauseAnalyzer
from src.analytics.forecaster import CostForecaster
from src.analytics.recommender import RecommendationEngine
from src.reports.exporter import ReportExporter


def test_full_application_lifecycle(temp_db, synthetic_cur_csv_text):
    """
    Simulates the entire workflow:
    Upload -> Normalize -> Persist -> Analyze -> Detect Anomalies -> Root Cause -> Forecast -> Recommend -> Report -> Clean Up
    """
    # 1. Ingestion & Validation
    df, summary = BillingParser.parse_file(synthetic_cur_csv_text, filename="integration_test.csv")
    assert summary.is_success is True
    assert df is not None
    assert summary.valid_rows == 6

    # 2. SQLite Persistence
    ds_id = temp_db.save_dataset(
        name="Integration Test Dataset",
        filename="integration_test.csv",
        row_count=summary.valid_rows,
        start_date=summary.date_min,
        end_date=summary.date_max,
        total_cost=summary.total_cost,
        currency=summary.currency,
        cost_measure=summary.selected_cost_measure
    )
    assert ds_id > 0
    temp_db.save_billing_records(ds_id, df)

    # 3. Retrieve Records
    retrieved_df = temp_db.get_billing_records_df(ds_id)
    assert len(retrieved_df) == 6

    # 4. Period Metrics Calculation
    metrics = CostEngine.calculate_period_metrics(
        retrieved_df,
        start_date=summary.date_min,
        end_date=summary.date_max,
        currency=summary.currency
    )
    assert metrics.total_cost == summary.total_cost
    assert metrics.highest_cost_service == "AmazonRDS"

    # 5. Anomaly Detection
    detector = AnomalyDetector(pct_threshold=30.0, abs_threshold=10.0)
    anomalies = detector.detect_anomalies(retrieved_df)
    temp_db.save_anomalies(ds_id, [a.to_dict() for a in anomalies])

    # 6. Forecasting
    forecast = CostForecaster.forecast_current_month(retrieved_df)
    assert forecast is not None

    # 7. Recommendations
    recs = RecommendationEngine.generate_recommendations(retrieved_df)
    assert len(recs) > 0
    temp_db.save_recommendations(ds_id, [r.to_dict() for r in recs])

    # 8. Report Generation
    cost_csv = ReportExporter.export_cost_summary_csv(metrics, f"{summary.date_min} to {summary.date_max}")
    assert "Total Cloud Cost" in cost_csv

    summary_md = ReportExporter.generate_executive_summary_markdown(
        dataset_name="Integration Test",
        period_label=f"{summary.date_min} to {summary.date_max}",
        cost_measure=summary.selected_cost_measure,
        currency=summary.currency,
        metrics=metrics,
        top_services_df=CostEngine.get_cost_by_service(retrieved_df),
        anomalies=anomalies,
        forecast=forecast
    )
    assert "# CloudGuard AI Executive Cost Report" in summary_md

    # 9. Clean-up & Cascade Delete
    deleted = temp_db.delete_dataset(ds_id)
    assert deleted is True
    assert temp_db.get_dataset(ds_id) is None
    assert len(temp_db.get_billing_records_df(ds_id)) == 0
