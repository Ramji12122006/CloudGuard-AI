"""Intelligent column mapping for various AWS billing CSV formats."""
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import re


class SchemaType(str, Enum):
    AWS_CUR = "AWS Cost and Usage Report (CUR)"
    AWS_COST_EXPLORER = "AWS Cost Explorer / Data Export"
    NORMALIZED_CSV = "CloudGuard Normalized Format"
    UNKNOWN = "Unknown / Custom Schema"


class ColumnMapper:
    """Detects and maps CSV column headers to the CloudGuard internal schema."""

    # Canonical internal fields
    REQUIRED_FIELDS = {"usage_date", "service", "cost_amount"}
    OPTIONAL_FIELDS = {"usage_type", "region", "resource_id", "usage_quantity", "currency", "cost_measure"}

    # Pattern definitions for candidate columns
    PATTERNS: Dict[str, List[str]] = {
        "usage_date": [
            r"^lineitem/usagestartdate$",
            r"^line_item_usage_start_date$",
            r"^usagestartdate$",
            r"^usage_start_date$",
            r"^usagedate$",
            r"^usage_date$",
            r"^timeperiod$",
            r"^time_period$",
            r"^date$",
            r"^start_date$",
            r"^startdate$",
            r"^identity/timeinterval$"
        ],
        "service": [
            r"^lineitem/productcode$",
            r"^line_item_product_code$",
            r"^product/productname$",
            r"^product_product_name$",
            r"^productcode$",
            r"^product_code$",
            r"^service$",
            r"^servicename$",
            r"^service_name$",
            r"^product$"
        ],
        "usage_type": [
            r"^lineitem/usagetype$",
            r"^line_item_usage_type$",
            r"^usagetype$",
            r"^usage_type$",
            r"^lineitem/operation$",
            r"^operation$"
        ],
        "region": [
            r"^product/region$",
            r"^product_region$",
            r"^lineitem/availabilityzone$",
            r"^line_item_availability_zone$",
            r"^region$",
            r"^availabilityzone$",
            r"^availability_zone$"
        ],
        "resource_id": [
            r"^lineitem/resourceid$",
            r"^line_item_resource_id$",
            r"^resourceid$",
            r"^resource_id$",
            r"^resource$"
        ],
        "usage_quantity": [
            r"^lineitem/usageamount$",
            r"^line_item_usage_amount$",
            r"^usageamount$",
            r"^usage_amount$",
            r"^usagequantity$",
            r"^usage_quantity$",
            r"^quantity$"
        ],
        "currency": [
            r"^pricing/currency$",
            r"^lineitem/currency$",
            r"^line_item_currency$",
            r"^currency$",
            r"^cost_currency$"
        ],
        # Cost measure patterns
        "cost_unblended": [
            r"^lineitem/unblendedcost$",
            r"^line_item_unblended_cost$",
            r"^unblendedcost$",
            r"^unblended_cost$",
            r"^unblended_cost_amount$",
            r"^cost$",
            r"^cost_amount$",
            r"^totalcost$",
            r"^total_cost$",
            r"^amount$"
        ],
        "cost_net_unblended": [
            r"^lineitem/netunblendedcost$",
            r"^line_item_net_unblended_cost$",
            r"^netunblendedcost$",
            r"^net_unblended_cost$"
        ],
        "cost_blended": [
            r"^lineitem/blendedcost$",
            r"^line_item_blended_cost$",
            r"^blendedcost$",
            r"^blended_cost$"
        ],
    }

    @classmethod
    def clean_header(cls, header: str) -> str:
        """Standardizes column name for pattern matching."""
        return header.strip().lower().replace(" ", "_")

    @classmethod
    def detect_mappings(
        cls,
        columns: List[str],
        selected_cost_measure: str = "UnblendedCost"
    ) -> Tuple[Dict[str, str], SchemaType, List[str], List[str]]:
        """
        Maps CSV columns to canonical schema.
        Returns:
            - mapping: dict from canonical field name -> actual csv column name
            - schema_type: detected SchemaType
            - available_cost_measures: list of cost measures present in the file
            - missing_required: list of required fields that could not be mapped
        """
        cleaned_col_map = {cls.clean_header(c): c for c in columns}
        mapping: Dict[str, str] = {}
        available_cost_measures: List[str] = []

        # Find cost measures available
        for clean_h, original_col in cleaned_col_map.items():
            for pat in cls.PATTERNS["cost_net_unblended"]:
                if re.match(pat, clean_h):
                    if "NetUnblendedCost" not in available_cost_measures:
                        available_cost_measures.append("NetUnblendedCost")
            for pat in cls.PATTERNS["cost_blended"]:
                if re.match(pat, clean_h):
                    if "BlendedCost" not in available_cost_measures:
                        available_cost_measures.append("BlendedCost")
            for pat in cls.PATTERNS["cost_unblended"]:
                if re.match(pat, clean_h):
                    if "UnblendedCost" not in available_cost_measures:
                        available_cost_measures.append("UnblendedCost")

        # Map required and optional non-cost fields
        for canonical, patterns in cls.PATTERNS.items():
            if canonical.startswith("cost_"):
                continue
            for pat in patterns:
                for clean_h, orig_col in cleaned_col_map.items():
                    if re.match(pat, clean_h) and canonical not in mapping:
                        mapping[canonical] = orig_col
                        break
                if canonical in mapping:
                    break

        # Map cost field based on selected measure
        cost_col: Optional[str] = None
        target_cost_patterns: List[str] = []

        if selected_cost_measure == "NetUnblendedCost" and "NetUnblendedCost" in available_cost_measures:
            target_cost_patterns = cls.PATTERNS["cost_net_unblended"]
        elif selected_cost_measure == "BlendedCost" and "BlendedCost" in available_cost_measures:
            target_cost_patterns = cls.PATTERNS["cost_blended"]
        else:
            # Fallback to Unblended or best available
            target_cost_patterns = cls.PATTERNS["cost_unblended"]

        for pat in target_cost_patterns:
            for clean_h, orig_col in cleaned_col_map.items():
                if re.match(pat, clean_h):
                    cost_col = orig_col
                    break
            if cost_col:
                break

        # If selected cost measure pattern wasn't matched, fallback to any available cost column
        if not cost_col:
            for pat_group in [cls.PATTERNS["cost_unblended"], cls.PATTERNS["cost_net_unblended"], cls.PATTERNS["cost_blended"]]:
                for pat in pat_group:
                    for clean_h, orig_col in cleaned_col_map.items():
                        if re.match(pat, clean_h):
                            cost_col = orig_col
                            break
                    if cost_col:
                        break
                if cost_col:
                    break

        if cost_col:
            mapping["cost_amount"] = cost_col

        # Detect schema type
        raw_headers_lower = " ".join(cleaned_col_map.keys())
        if "lineitem/" in raw_headers_lower or "line_item_" in raw_headers_lower:
            schema_type = SchemaType.AWS_CUR
        elif "usage_date" in cleaned_col_map and "service" in cleaned_col_map and "cost" in cleaned_col_map:
            schema_type = SchemaType.NORMALIZED_CSV
        elif "timeperiod" in cleaned_col_map or "usagedate" in cleaned_col_map:
            schema_type = SchemaType.AWS_COST_EXPLORER
        else:
            schema_type = SchemaType.UNKNOWN

        # Missing required check
        missing_required = [f for f in cls.REQUIRED_FIELDS if f not in mapping]

        return mapping, schema_type, available_cost_measures, missing_required
