"""Automated tests for evidence-based cost optimization recommendations."""
import pytest
import pandas as pd

from src.analytics.recommender import RecommendationEngine


def test_spend_concentration_recommendation():
    """Verifies that high single-service concentration triggers an advisory."""
    df = pd.DataFrame([
        {"service": "AmazonEC2", "cost_amount": 800.0, "usage_type": "BoxUsage", "usage_date": "2026-09-01"},
        {"service": "AmazonS3", "cost_amount": 200.0, "usage_type": "StandardStorage", "usage_date": "2026-09-01"},
    ])
    recs = RecommendationEngine.generate_recommendations(df)

    conc_recs = [r for r in recs if r.category == "Spend Concentration"]
    assert len(conc_recs) == 1
    rec = conc_recs[0]
    assert "AmazonEC2" in rec.title
    assert "80.0%" in rec.supporting_evidence
    assert rec.estimated_savings is not None
    assert rec.limitations != ""


def test_data_transfer_egress_recommendation():
    """Verifies that high data transfer egress generates an architectural advisory."""
    df = pd.DataFrame([
        {"service": "AmazonCloudFront", "cost_amount": 100.0, "usage_type": "DataTransfer-Out-Bytes", "usage_date": "2026-09-01"},
        {"service": "AmazonCloudFront", "cost_amount": 50.0, "usage_type": "Requests", "usage_date": "2026-09-01"},
    ])
    recs = RecommendationEngine.generate_recommendations(df)

    dt_recs = [r for r in recs if r.category == "Network Architecture"]
    assert len(dt_recs) == 1
    rec = dt_recs[0]
    assert "Data transfer out" in rec.supporting_evidence
    assert "CloudFront" in rec.suggested_action


def test_storage_lifecycle_recommendation():
    """Verifies that continuous standard S3 spend triggers lifecycle evaluation."""
    df = pd.DataFrame([
        {"service": "AmazonS3", "cost_amount": 120.0, "usage_type": "TimedStorage-ByteHrs", "usage_date": "2026-09-01"},
    ])
    recs = RecommendationEngine.generate_recommendations(df)

    storage_recs = [r for r in recs if r.category == "Storage Optimization"]
    assert len(storage_recs) == 1
    rec = storage_recs[0]
    assert "Intelligent-Tiering" in rec.suggested_action
    assert rec.limitations != ""


def test_unattached_ebs_volume_recommendation():
    """Verifies that persistent EBS volume allocations trigger hygiene review."""
    df = pd.DataFrame([
        {"service": "AmazonEC2", "cost_amount": 50.0, "usage_type": "EBS:VolumeUsage.gp3", "usage_date": "2026-09-01"},
    ])
    recs = RecommendationEngine.generate_recommendations(df)

    ebs_recs = [r for r in recs if r.category == "Resource Hygiene"]
    assert len(ebs_recs) == 1
    rec = ebs_recs[0]
    assert "EBS" in rec.title
    assert "describe-volumes" in rec.suggested_action
    assert "do NOT prove" in rec.limitations
