"""Billing parser that ingests CSV content and transforms it into the normalized schema."""
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional, Tuple, Union
import io
import pandas as pd

from .column_mapper import ColumnMapper, SchemaType
from .validator import DataValidator, ValidationResult


@dataclass
class ImportSummary:
    """Concise, explainable summary of the import operation."""
    filename: str
    schema_type: str
    selected_cost_measure: str
    total_raw_rows: int = 0
    valid_rows: int = 0
    duplicate_rows: int = 0
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    total_cost: float = 0.0
    currency: str = "USD"
    service_count: int = 0
    top_services: List[Tuple[str, float]] = field(default_factory=list)
    available_cost_measures: List[str] = field(default_factory=list)
    missing_optional_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    is_success: bool = False


class BillingParser:
    """Parses and normalizes AWS billing CSV files."""

    @classmethod
    def parse_file(
        cls,
        file_input: Union[bytes, str, io.BytesIO, io.StringIO],
        filename: str = "uploaded_billing.csv",
        selected_cost_measure: str = "UnblendedCost",
        allow_credits: bool = True
    ) -> Tuple[Optional[pd.DataFrame], ImportSummary]:
        """
        Parses an uploaded file into a normalized billing DataFrame and an ImportSummary.
        """
        summary = ImportSummary(
            filename=filename,
            schema_type=SchemaType.UNKNOWN.value,
            selected_cost_measure=selected_cost_measure
        )

        # 1. Convert input into bytes
        if isinstance(file_input, str):
            content_bytes = file_input.encode("utf-8")
        elif isinstance(file_input, io.BytesIO):
            content_bytes = file_input.getvalue()
        elif isinstance(file_input, io.StringIO):
            content_bytes = file_input.getvalue().encode("utf-8")
        elif isinstance(file_input, bytes):
            content_bytes = file_input
        else:
            summary.errors.append(f"Unsupported file input type: {type(file_input)}")
            return None, summary

        # 2. Inspect file encoding and delimiter
        is_ok, encoding, delimiter, err_msg = DataValidator.inspect_file(content_bytes, filename)
        if not is_ok:
            summary.errors.append(err_msg or "File inspection failed.")
            return None, summary

        # 3. Read CSV into DataFrame
        try:
            raw_text = content_bytes.decode(encoding)
            raw_df = pd.read_csv(
                StringIO(raw_text),
                delimiter=delimiter,
                dtype=str,
                keep_default_na=False,
                low_memory=False
            )
            summary.total_raw_rows = len(raw_df)
        except Exception as e:
            summary.errors.append(f"Failed to read CSV structure: {str(e)}")
            return None, summary

        if raw_df.empty:
            summary.errors.append("Uploaded file contains no rows.")
            return None, summary

        # 4. Map columns to internal schema
        mapping, schema_type, avail_measures, missing_required = ColumnMapper.detect_mappings(
            list(raw_df.columns),
            selected_cost_measure=selected_cost_measure
        )
        summary.schema_type = schema_type.value
        summary.available_cost_measures = avail_measures

        if missing_required:
            summary.errors.append(
                f"Missing required billing columns: {', '.join(missing_required)}. "
                f"Available columns in file: {', '.join(list(raw_df.columns)[:8])}..."
            )
            return None, summary

        # Identify missing optional fields
        all_optional = ["usage_type", "region", "resource_id", "usage_quantity"]
        missing_optional = [f for f in all_optional if f not in mapping]
        summary.missing_optional_fields = missing_optional

        # 5. Clean, validate, and normalize records
        normalized_df, val_result = DataValidator.validate_dataframe(
            raw_df,
            mapping=mapping,
            allow_credits=allow_credits
        )

        summary.warnings.extend(val_result.warnings)
        summary.errors.extend(val_result.errors)

        if not val_result.is_valid or normalized_df.empty:
            return None, summary

        # 6. Populate final summary stats
        normalized_df["cloud_provider"] = "AWS"
        normalized_df["cost_measure"] = selected_cost_measure

        summary.valid_rows = len(normalized_df)
        summary.duplicate_rows = val_result.duplicate_count
        summary.date_min = str(normalized_df["usage_date"].min())
        summary.date_max = str(normalized_df["usage_date"].max())
        summary.total_cost = float(normalized_df["cost_amount"].sum())
        summary.currency = str(normalized_df["currency"].iloc[0]) if not normalized_df.empty else "USD"

        # Service breakdown
        service_totals = normalized_df.groupby("service")["cost_amount"].sum().sort_values(ascending=False)
        summary.service_count = len(service_totals)
        summary.top_services = [(str(s), float(c)) for s, c in service_totals.head(5).items()]
        summary.is_success = True

        return normalized_df, summary
