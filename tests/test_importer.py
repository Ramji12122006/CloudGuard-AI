"""Automated tests for CSV parsing, column mapping, and data validation."""
import pytest
import pandas as pd

from src.importer.column_mapper import ColumnMapper, SchemaType
from src.importer.validator import DataValidator
from src.importer.parser import BillingParser


def test_column_mapper_cur():
    """Verifies that standard AWS CUR headers map correctly."""
    columns = [
        "identity/LineItemId",
        "lineItem/UsageStartDate",
        "lineItem/ProductCode",
        "lineItem/UsageType",
        "lineItem/ResourceId",
        "lineItem/UnblendedCost",
        "lineItem/NetUnblendedCost",
        "pricing/currency"
    ]
    mapping, schema_type, avail_measures, missing_req = ColumnMapper.detect_mappings(columns)

    assert schema_type == SchemaType.AWS_CUR
    assert mapping["usage_date"] == "lineItem/UsageStartDate"
    assert mapping["service"] == "lineItem/ProductCode"
    assert mapping["cost_amount"] == "lineItem/UnblendedCost"
    assert "UnblendedCost" in avail_measures
    assert "NetUnblendedCost" in avail_measures
    assert len(missing_req) == 0


def test_column_mapper_cost_explorer():
    """Verifies that AWS Cost Explorer export headers map correctly."""
    columns = ["UsageDate", "Service", "UsageType", "Region", "ResourceId", "UnblendedCost", "Currency"]
    mapping, schema_type, avail_measures, missing_req = ColumnMapper.detect_mappings(columns)

    assert schema_type == SchemaType.AWS_COST_EXPLORER
    assert mapping["usage_date"] == "UsageDate"
    assert mapping["service"] == "Service"
    assert mapping["cost_amount"] == "UnblendedCost"
    assert len(missing_req) == 0


def test_column_mapper_missing_required():
    """Verifies detection of missing required columns."""
    columns = ["Service", "Region"]
    mapping, schema_type, avail_measures, missing_req = ColumnMapper.detect_mappings(columns)

    assert "usage_date" in missing_req
    assert "cost_amount" in missing_req


def test_parse_cur_csv(synthetic_cur_csv_text):
    """Verifies full parsing of synthetic CUR CSV."""
    df, summary = BillingParser.parse_file(synthetic_cur_csv_text, filename="test_cur.csv")

    assert summary.is_success is True
    assert summary.valid_rows == 6
    assert summary.service_count == 2
    # 3 days * ($10 EC2 + $20 RDS) = $90 total
    assert pytest.approx(summary.total_cost, 0.01) == 90.0
    assert summary.currency == "USD"
    assert summary.date_min == "2026-09-01"
    assert summary.date_max == "2026-09-03"


def test_cost_measure_selection(synthetic_cur_csv_text):
    """Verifies selection of NetUnblendedCost over UnblendedCost."""
    df, summary = BillingParser.parse_file(
        synthetic_cur_csv_text,
        filename="test_cur.csv",
        selected_cost_measure="NetUnblendedCost"
    )

    assert summary.is_success is True
    assert summary.selected_cost_measure == "NetUnblendedCost"
    # Net costs: 3 days * ($9 + $19) = $84
    assert pytest.approx(summary.total_cost, 0.01) == 84.0


def test_empty_file_handling():
    """Verifies graceful rejection of empty file content."""
    df, summary = BillingParser.parse_file("", filename="empty.csv")

    assert summary.is_success is False
    assert len(summary.errors) > 0
    assert any("empty" in e.lower() for e in summary.errors)


def test_duplicate_record_handling():
    """Verifies identification and de-duplication of duplicate billing rows."""
    csv_with_dups = (
        "usage_date,service,usage_type,region,resource_id,cost_amount,currency\n"
        "2026-09-01,AmazonEC2,BoxUsage,us-east-1,i-1,10.00,USD\n"
        "2026-09-01,AmazonEC2,BoxUsage,us-east-1,i-1,10.00,USD\n"  # Exact duplicate
        "2026-09-02,AmazonEC2,BoxUsage,us-east-1,i-1,15.00,USD\n"
    )
    df, summary = BillingParser.parse_file(csv_with_dups, filename="dups.csv")

    assert summary.is_success is True
    assert summary.valid_rows == 2
    assert summary.duplicate_rows == 1


def test_invalid_dates_and_nonnumeric_costs():
    """Verifies exclusion of malformed dates and invalid numbers."""
    csv_malformed = (
        "usage_date,service,cost_amount\n"
        "2026-09-01,AmazonEC2,10.50\n"
        "NOT_A_DATE,AmazonEC2,20.00\n"      # Invalid date
        "2026-09-02,AmazonEC2,INVALID_COST\n" # Nonnumeric cost
        "2026-09-03,AmazonEC2,$15.25\n"      # Cost with currency symbol
    )
    df, summary = BillingParser.parse_file(csv_malformed, filename="malformed.csv")

    assert summary.is_success is True
    assert summary.valid_rows == 2
    assert pytest.approx(summary.total_cost, 0.01) == 25.75
    assert len(summary.warnings) >= 2


def test_mixed_currency_handling():
    """Verifies detection and warning when multiple currencies are present."""
    csv_mixed = (
        "usage_date,service,cost_amount,currency\n"
        "2026-09-01,AmazonEC2,10.00,USD\n"
        "2026-09-02,AmazonEC2,10.00,EUR\n"
    )
    df, summary = BillingParser.parse_file(csv_mixed, filename="mixed.csv")

    assert summary.is_success is True
    assert any("multiple currencies" in w.lower() for w in summary.warnings)
