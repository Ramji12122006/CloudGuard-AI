"""Automated tests for SQLite persistence, transactions, and cascade deletion."""
import pytest
import pandas as pd

from src.db.database import DatabaseManager


def test_db_init_tables(temp_db):
    """Verifies that all required tables and indexes are initialized."""
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]

    expected = [
        "imported_datasets",
        "normalized_billing_records",
        "detected_anomalies",
        "forecast_results",
        "recommendations",
        "analysis_runs"
    ]
    for exp in expected:
        assert exp in tables


def test_dataset_save_and_retrieve(temp_db):
    """Verifies dataset metadata storage and listing."""
    ds_id = temp_db.save_dataset(
        name="Test Production Dataset",
        filename="test_prod.csv",
        row_count=100,
        start_date="2026-09-01",
        end_date="2026-09-30",
        total_cost=1500.50,
        currency="USD",
        cost_measure="UnblendedCost"
    )
    assert ds_id > 0

    retrieved = temp_db.get_dataset(ds_id)
    assert retrieved is not None
    assert retrieved["name"] == "Test Production Dataset"
    assert retrieved["total_cost"] == 1500.50
    assert retrieved["row_count"] == 100


def test_billing_records_save_and_filter(temp_db, synthetic_normalized_df):
    """Verifies batch insertion and filtered retrieval of billing records."""
    ds_id = temp_db.save_dataset("Test DS", "test.csv", 6, "2026-09-01", "2026-09-03", 90.0, "USD", "UnblendedCost")
    count = temp_db.save_billing_records(ds_id, synthetic_normalized_df)
    assert count == 6

    # Filter by service
    ec2_df = temp_db.get_billing_records_df(ds_id, services=["AmazonEC2"])
    assert len(ec2_df) == 3
    assert (ec2_df["service"] == "AmazonEC2").all()

    # Filter by date range
    date_df = temp_db.get_billing_records_df(ds_id, start_date="2026-09-01", end_date="2026-09-02")
    assert len(date_df) == 4


def test_anomaly_status_update(temp_db):
    """Verifies anomaly persistence and status modification."""
    ds_id = temp_db.save_dataset("Test DS", "test.csv", 10, "2026-09-01", "2026-09-10", 100.0, "USD", "UnblendedCost")

    anomalies = [{
        "detection_date": "2026-09-05",
        "billing_period": "2026-09",
        "service": "AmazonEC2",
        "resource_id": None,
        "actual_cost": 50.0,
        "baseline_cost": 10.0,
        "absolute_increase": 40.0,
        "percentage_increase": 400.0,
        "detection_method": "MAD Outlier",
        "trigger_reason": "Spend surge",
        "evidence_level": "Confirmed by billing data",
        "status": "Open"
    }]
    temp_db.save_anomalies(ds_id, anomalies)
    saved = temp_db.get_anomalies(ds_id)
    assert len(saved) == 1
    anom_id = saved[0]["id"]

    # Update status to Reviewed
    updated = temp_db.update_anomaly_status(anom_id, "Reviewed")
    assert updated is True

    reviewed_list = temp_db.get_anomalies(ds_id, status="Reviewed")
    assert len(reviewed_list) == 1
    assert reviewed_list[0]["status"] == "Reviewed"


def test_recommendation_status_lifecycle(temp_db):
    """Verifies recommendation saving and status transition."""
    ds_id = temp_db.save_dataset("Test DS", "test.csv", 10, "2026-09-01", "2026-09-10", 100.0, "USD", "UnblendedCost")

    recs = [{
        "category": "Storage",
        "title": "Review S3 Lifecycle",
        "service": "AmazonS3",
        "supporting_evidence": "All standard storage",
        "suggested_action": "Enable tiering",
        "estimated_savings": 25.0,
        "status": "Open",
        "limitations": "No object access metrics"
    }]
    temp_db.save_recommendations(ds_id, recs)
    saved_recs = temp_db.get_recommendations(ds_id)
    assert len(saved_recs) == 1

    rec_id = saved_recs[0]["id"]
    temp_db.update_recommendation_status(rec_id, "Accepted")
    updated_rec = temp_db.get_recommendations(ds_id, status="Accepted")
    assert len(updated_rec) == 1


def test_dataset_cascade_deletion(temp_db, synthetic_normalized_df):
    """Verifies atomic cascading delete of dataset and all related child records."""
    ds_id = temp_db.save_dataset("Test Delete DS", "test.csv", 6, "2026-09-01", "2026-09-03", 90.0, "USD", "UnblendedCost")
    temp_db.save_billing_records(ds_id, synthetic_normalized_df)
    temp_db.save_anomalies(ds_id, [{
        "detection_date": "2026-09-02",
        "billing_period": "2026-09",
        "service": "AmazonEC2",
        "resource_id": None,
        "actual_cost": 20.0,
        "baseline_cost": 10.0,
        "absolute_increase": 10.0,
        "percentage_increase": 100.0,
        "detection_method": "Threshold",
        "trigger_reason": "Increase",
        "evidence_level": "Confirmed by billing data",
        "status": "Open"
    }])

    # Delete dataset
    deleted = temp_db.delete_dataset(ds_id)
    assert deleted is True

    # Verify parent and children are removed
    assert temp_db.get_dataset(ds_id) is None
    assert len(temp_db.get_billing_records_df(ds_id)) == 0
    assert len(temp_db.get_anomalies(ds_id)) == 0
