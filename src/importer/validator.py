"""Validation module for billing files and parsed records."""
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Dict, List, Optional, Set, Tuple
import csv
import io
import re
import pandas as pd


@dataclass
class ValidationResult:
    """Holds outcome of CSV validation checks."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    delimiter: str = ","
    encoding: str = "utf-8"
    row_count: int = 0
    duplicate_count: int = 0
    currencies: List[str] = field(default_factory=list)
    has_mixed_currencies: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class DataValidator:
    """Validates CSV content, file properties, and records for financial analysis integrity."""

    MAX_FILE_BYTES = 250 * 1024 * 1024  # 250 MB
    SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    @classmethod
    def inspect_file(cls, file_content: bytes, filename: str = "file.csv") -> Tuple[bool, str, str, Optional[str]]:
        """
        Inspects file bytes.
        Returns: (is_valid, encoding, delimiter, error_message)
        """
        if len(file_content) == 0:
            return False, "utf-8", ",", "Uploaded file is empty (0 bytes)."

        if len(file_content) > cls.MAX_FILE_BYTES:
            return False, "utf-8", ",", f"File size ({len(file_content) / (1024*1024):.1f} MB) exceeds maximum permitted limit (250 MB)."

        # Determine encoding
        decoded_text: Optional[str] = None
        chosen_encoding: str = "utf-8"
        for enc in cls.SUPPORTED_ENCODINGS:
            try:
                decoded_text = file_content[:65536].decode(enc)
                chosen_encoding = enc
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if decoded_text is None:
            return False, "utf-8", ",", "Unable to decode CSV file with supported encodings (UTF-8, Latin-1, CP1252)."

        # Determine delimiter
        sample = decoded_text[:4096]
        delimiter = ","
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=[",", ";", "\t", "|"])
            delimiter = dialect.delimiter
        except Exception:
            # Fallback delimiter inference
            if "\t" in sample and sample.count("\t") > sample.count(","):
                delimiter = "\t"
            elif ";" in sample and sample.count(";") > sample.count(","):
                delimiter = ";"
            else:
                delimiter = ","

        return True, chosen_encoding, delimiter, None

    @classmethod
    def clean_cost_value(cls, val: Any) -> Optional[float]:
        """Parses cost string to float, stripping currency symbols, whitespace, commas."""
        if pd.isna(val) or val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)

        s = str(val).strip()
        if not s:
            return None

        # Remove currency symbols and formatting commas
        s = re.sub(r"[^\d\.\-+eE]", "", s)
        try:
            return float(s)
        except ValueError:
            return None

    @classmethod
    def parse_usage_date(cls, val: Any) -> Optional[str]:
        """Normalizes date strings into ISO YYYY-MM-DD."""
        if pd.isna(val) or val is None:
            return None

        s = str(val).strip()
        if not s:
            return None

        # Common AWS format: "2026-08-01T00:00:00Z" or "2026-08-01 00:00:00"
        # Match YYYY-MM-DD at start
        m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
        if m:
            year, month, day = m.groups()
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        # Try pandas to_datetime parsing
        try:
            dt = pd.to_datetime(s, errors="coerce")
            if pd.notnull(dt):
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        return None

    @classmethod
    def validate_dataframe(
        cls,
        df: pd.DataFrame,
        mapping: Dict[str, str],
        allow_credits: bool = True
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """
        Validates extracted columns, coerces types, detects duplicates and currencies.
        Returns: (normalized_df, validation_result)
        """
        result = ValidationResult(is_valid=True)
        errors = []
        warnings = []

        if df.empty:
            result.is_valid = False
            result.errors.append("Dataset contains 0 rows of data.")
            return pd.DataFrame(), result

        # Check required columns mapped
        for req in ["usage_date", "service", "cost_amount"]:
            if req not in mapping or mapping[req] not in df.columns:
                errors.append(f"Required field '{req}' could not be identified in the uploaded CSV.")

        if errors:
            result.is_valid = False
            result.errors = errors
            return pd.DataFrame(), result

        normalized = pd.DataFrame()

        # Parse usage dates
        raw_dates = df[mapping["usage_date"]]
        parsed_dates = raw_dates.apply(cls.parse_usage_date)
        invalid_dates_mask = parsed_dates.isna()
        invalid_date_count = invalid_dates_mask.sum()

        if invalid_date_count > 0:
            warnings.append(f"{invalid_date_count} rows contained unparseable dates and were excluded.")

        normalized["usage_date"] = parsed_dates
        normalized["billing_period"] = normalized["usage_date"].str.slice(0, 7)

        # Parse services
        normalized["service"] = df[mapping["service"]].astype(str).str.strip()
        # Clean service names (fallback to 'Unknown Service' if empty)
        normalized["service"] = normalized["service"].replace({"": "Unknown Service", "nan": "Unknown Service"})

        # Parse cost
        raw_costs = df[mapping["cost_amount"]]
        parsed_costs = raw_costs.apply(cls.clean_cost_value)
        invalid_cost_mask = parsed_costs.isna()
        invalid_cost_count = invalid_cost_mask.sum()

        if invalid_cost_count > 0:
            warnings.append(f"{invalid_cost_count} rows contained non-numeric cost values and were excluded.")

        normalized["cost_amount"] = parsed_costs

        # Parse optional fields
        if "usage_type" in mapping and mapping["usage_type"] in df.columns:
            normalized["usage_type"] = df[mapping["usage_type"]].astype(str).str.strip().replace({"nan": ""})
        else:
            normalized["usage_type"] = ""

        if "region" in mapping and mapping["region"] in df.columns:
            normalized["region"] = df[mapping["region"]].astype(str).str.strip().replace({"nan": "Global/Unknown", "": "Global/Unknown"})
        else:
            normalized["region"] = "Global/Unknown"

        if "resource_id" in mapping and mapping["resource_id"] in df.columns:
            normalized["resource_id"] = df[mapping["resource_id"]].astype(str).str.strip().replace({"nan": "", "None": ""})
        else:
            normalized["resource_id"] = None

        if "usage_quantity" in mapping and mapping["usage_quantity"] in df.columns:
            normalized["usage_quantity"] = pd.to_numeric(df[mapping["usage_quantity"]], errors="coerce").fillna(0.0)
        else:
            normalized["usage_quantity"] = 0.0

        # Currency
        if "currency" in mapping and mapping["currency"] in df.columns:
            currencies = df[mapping["currency"]].dropna().astype(str).str.strip().unique()
            currencies = [c for c in currencies if c and c.lower() != "nan"]
            if len(currencies) > 1:
                result.has_mixed_currencies = True
                warnings.append(f"Multiple currencies detected: {', '.join(currencies)}. Calculations assume unified currency.")
                normalized["currency"] = df[mapping["currency"]].astype(str).str.strip().replace({"nan": "USD", "": "USD"})
            elif len(currencies) == 1:
                normalized["currency"] = currencies[0]
            else:
                normalized["currency"] = "USD"
        else:
            normalized["currency"] = "USD"

        result.currencies = list(normalized["currency"].unique())

        # Filter out rows with invalid date or invalid cost
        valid_mask = normalized["usage_date"].notna() & normalized["cost_amount"].notna()
        normalized = normalized[valid_mask].copy()

        # Handle negative costs / credits if requested
        if not allow_credits:
            credits_mask = normalized["cost_amount"] < 0
            credits_count = credits_mask.sum()
            if credits_count > 0:
                warnings.append(f"Filtered out {credits_count} negative credit/refund rows.")
                normalized = normalized[~credits_mask].copy()

        # Duplicate detection: check identical compound tuple
        dedup_keys = ["usage_date", "service", "usage_type", "region", "resource_id", "cost_amount"]
        initial_len = len(normalized)
        normalized = normalized.drop_duplicates(subset=dedup_keys, keep="first")
        duplicate_count = initial_len - len(normalized)

        if duplicate_count > 0:
            warnings.append(f"Identified and removed {duplicate_count} duplicate billing rows.")

        result.row_count = len(normalized)
        result.duplicate_count = duplicate_count
        result.warnings = warnings
        result.errors = errors
        result.is_valid = len(normalized) > 0

        if len(normalized) == 0:
            result.is_valid = False
            result.errors.append("No valid billing records remained after cleaning date and cost fields.")

        return normalized, result
