"""Shared pytest fixtures and synthetic billing data fixtures."""
import os
import tempfile
from pathlib import Path
from typing import Generator
import pytest
import pandas as pd

from src.db.database import DatabaseManager


@pytest.fixture
def temp_db() -> Generator[DatabaseManager, None, None]:
    """Provides a temporary, isolated SQLite DatabaseManager."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)

    db = DatabaseManager(temp_path)
    yield db

    try:
        if temp_path.exists():
            os.remove(temp_path)
    except OSError:
        pass


@pytest.fixture
def synthetic_cur_csv_text() -> str:
    """Synthetic AWS CUR CSV data with known values for testing."""
    return (
        "identity/LineItemId,lineItem/UsageStartDate,lineItem/ProductCode,lineItem/UsageType,lineItem/ResourceId,lineItem/UsageAmount,lineItem/UnblendedCost,lineItem/NetUnblendedCost,pricing/currency\n"
        "id-1,2026-09-01T00:00:00Z,AmazonEC2,BoxUsage:t3.medium,i-01234,24.0,10.00,9.00,USD\n"
        "id-2,2026-09-01T00:00:00Z,AmazonRDS,InstanceUsage:db.m5,db-1,24.0,20.00,19.00,USD\n"
        "id-3,2026-09-02T00:00:00Z,AmazonEC2,BoxUsage:t3.medium,i-01234,24.0,10.00,9.00,USD\n"
        "id-4,2026-09-02T00:00:00Z,AmazonRDS,InstanceUsage:db.m5,db-1,24.0,20.00,19.00,USD\n"
        "id-5,2026-09-03T00:00:00Z,AmazonEC2,BoxUsage:t3.medium,i-01234,24.0,10.00,9.00,USD\n"
        "id-6,2026-09-03T00:00:00Z,AmazonRDS,InstanceUsage:db.m5,db-1,24.0,20.00,19.00,USD\n"
    )


@pytest.fixture
def synthetic_cost_explorer_csv_text() -> str:
    """Synthetic AWS Cost Explorer export CSV data."""
    return (
        "UsageDate,Service,UsageType,Region,ResourceId,UsageQuantity,UnblendedCost,Currency\n"
        "2026-10-01,AmazonEC2,BoxUsage:m5.large,us-east-1,i-abcde,24,15.50,USD\n"
        "2026-10-01,AmazonS3,StandardStorage,us-east-1,bucket-a,100,2.50,USD\n"
        "2026-10-02,AmazonEC2,BoxUsage:m5.large,us-east-1,i-abcde,24,15.50,USD\n"
        "2026-10-02,AmazonS3,StandardStorage,us-east-1,bucket-a,100,2.50,USD\n"
    )


@pytest.fixture
def synthetic_normalized_df() -> pd.DataFrame:
    """Pre-built normalized dataframe with known values."""
    data = [
        {"usage_date": "2026-09-01", "billing_period": "2026-09", "cloud_provider": "AWS", "service": "AmazonEC2", "usage_type": "BoxUsage:t3.medium", "region": "us-east-1", "resource_id": "i-1", "usage_quantity": 24.0, "cost_amount": 10.0, "currency": "USD", "cost_measure": "UnblendedCost"},
        {"usage_date": "2026-09-01", "billing_period": "2026-09", "cloud_provider": "AWS", "service": "AmazonRDS", "usage_type": "InstanceUsage:db.m5", "region": "us-east-1", "resource_id": "db-1", "usage_quantity": 24.0, "cost_amount": 20.0, "currency": "USD", "cost_measure": "UnblendedCost"},
        {"usage_date": "2026-09-02", "billing_period": "2026-09", "cloud_provider": "AWS", "service": "AmazonEC2", "usage_type": "BoxUsage:t3.medium", "region": "us-east-1", "resource_id": "i-1", "usage_quantity": 24.0, "cost_amount": 10.0, "currency": "USD", "cost_measure": "UnblendedCost"},
        {"usage_date": "2026-09-02", "billing_period": "2026-09", "cloud_provider": "AWS", "service": "AmazonRDS", "usage_type": "InstanceUsage:db.m5", "region": "us-east-1", "resource_id": "db-1", "usage_quantity": 24.0, "cost_amount": 20.0, "currency": "USD", "cost_measure": "UnblendedCost"},
        {"usage_date": "2026-09-03", "billing_period": "2026-09", "cloud_provider": "AWS", "service": "AmazonEC2", "usage_type": "BoxUsage:t3.medium", "region": "us-east-1", "resource_id": "i-1", "usage_quantity": 24.0, "cost_amount": 10.0, "currency": "USD", "cost_measure": "UnblendedCost"},
        {"usage_date": "2026-09-03", "billing_period": "2026-09", "cloud_provider": "AWS", "service": "AmazonRDS", "usage_type": "InstanceUsage:db.m5", "region": "us-east-1", "resource_id": "db-1", "usage_quantity": 24.0, "cost_amount": 20.0, "currency": "USD", "cost_measure": "UnblendedCost"},
    ]
    return pd.DataFrame(data)
