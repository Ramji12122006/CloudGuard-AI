"""Automated tests for statistical anomaly detection and evidence classification."""
import pytest
import pandas as pd

from src.analytics.anomaly_detector import AnomalyDetector
from src.config import EVIDENCE_CONFIRMED


def test_mad_anomaly_detection_spike():
    """Verifies that a significant surge above historical median is detected via MAD."""
    dates = [f"2026-09-{i:02d}" for i in range(1, 10)]
    # 8 days at $10.00, then day 9 jumps to $80.00 (+70.00 surge)
    data = []
    for d in dates[:8]:
        data.append({"usage_date": d, "service": "AmazonEC2", "cost_amount": 10.0})
    data.append({"usage_date": dates[8], "service": "AmazonEC2", "cost_amount": 80.0})

    df = pd.DataFrame(data)
    detector = AnomalyDetector(pct_threshold=50.0, abs_threshold=25.0)
    anomalies = detector.detect_anomalies(df)

    assert len(anomalies) >= 1
    target = anomalies[0]
    assert target.service == "AmazonEC2"
    assert target.detection_date == "2026-09-09"
    assert target.actual_cost == 80.0
    assert target.baseline_cost == 10.0
    assert target.absolute_increase == 70.0
    assert target.evidence_level == EVIDENCE_CONFIRMED


def test_no_false_positives_on_normal_spend():
    """Verifies that stable, consistent daily spending produces zero anomalies."""
    dates = [f"2026-09-{i:02d}" for i in range(1, 15)]
    data = [{"usage_date": d, "service": "AmazonRDS", "cost_amount": 25.0} for d in dates]
    df = pd.DataFrame(data)

    detector = AnomalyDetector(pct_threshold=50.0, abs_threshold=25.0)
    anomalies = detector.detect_anomalies(df)

    assert len(anomalies) == 0


def test_small_increase_below_threshold_ignored():
    """Verifies that an increase below absolute threshold ($25) is not flagged as an anomaly."""
    dates = [f"2026-09-{i:02d}" for i in range(1, 8)]
    data = [{"usage_date": d, "service": "AmazonS3", "cost_amount": 10.0} for d in dates[:6]]
    # Increase of $5.00 (+50%, but only $5.00 absolute increase)
    data.append({"usage_date": dates[6], "service": "AmazonS3", "cost_amount": 15.0})

    df = pd.DataFrame(data)
    detector = AnomalyDetector(pct_threshold=40.0, abs_threshold=25.0)
    anomalies = detector.detect_anomalies(df)

    assert len(anomalies) == 0
