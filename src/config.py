"""Configuration module for CloudGuard AI."""
from pathlib import Path
import os

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Persistence paths
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = BASE_DIR / "cloudguard.db"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Application metadata
APP_NAME = "CloudGuard AI"
APP_SUBTITLE = "Intelligent Cloud Cost Analysis and Optimization Platform"
APP_VERSION = "1.0.0"

# Supported Cost Measures
COST_MEASURES = {
    "UnblendedCost": "Unblended Cost (Standard cash basis before upfront fee amortization)",
    "NetUnblendedCost": "Net Unblended Cost (After discounts and tiered pricing adjustments)",
    "BlendedCost": "Blended Cost (Average rate across consolidated billing accounts)",
}
DEFAULT_COST_MEASURE = "UnblendedCost"

# Anomaly Detection Defaults
DEFAULT_PCT_THRESHOLD = 50.0       # Alert when cost rises >50% vs baseline
DEFAULT_ABS_THRESHOLD = 25.0       # Alert when cost rises >$25 vs baseline
DEFAULT_ZSCORE_THRESHOLD = 2.5     # Statistical Z-score cutoff
DEFAULT_MAD_THRESHOLD = 3.0        # Median Absolute Deviation multiplier
MIN_HISTORY_DAYS_FOR_ANOMALY = 5   # Minimum days of history to compute baseline

# Forecasting Defaults
MIN_DAYS_FOR_RUN_RATE = 3          # Minimum days required for month-to-date run-rate
MIN_DAYS_FOR_DAILY_FORECAST = 7    # Minimum days required for linear/moving average projection
DEFAULT_FORECAST_DAYS = 30         # Days ahead to project if month boundary is not active

# Evidence Classifications (Strict adherence to prompt specifications)
EVIDENCE_CONFIRMED = "Confirmed by billing data"
EVIDENCE_STRONGLY_SUPPORTED = "Strongly supported inference"
EVIDENCE_POSSIBLE = "Possible explanation"
EVIDENCE_INSUFFICIENT = "Insufficient evidence"

# Recommendation Statuses
REC_STATUS_OPEN = "Open"
REC_STATUS_UNDER_REVIEW = "Under review"
REC_STATUS_ACCEPTED = "Accepted"
REC_STATUS_DISMISSED = "Dismissed"
REC_STATUS_COMPLETED = "Completed"

REC_STATUS_OPTIONS = [
    REC_STATUS_OPEN,
    REC_STATUS_UNDER_REVIEW,
    REC_STATUS_ACCEPTED,
    REC_STATUS_DISMISSED,
    REC_STATUS_COMPLETED,
]

# Color palette for charts & UI
PALETTE = {
    "primary": "#0284C7",        # Sky 600
    "favorable": "#22C55E",      # Emerald 500 (Decrease/Savings)
    "unfavorable": "#EF4444",    # Red 500 (Increase/Anomaly)
    "neutral": "#94A3B8",        # Slate 400
    "background": "#0F172A",     # Slate 900
    "card": "#1E293B",           # Slate 800
    "border": "#334155",         # Slate 700
    "text": "#F8FAFC",           # Slate 50
    "text_muted": "#94A3B8",     # Slate 400
}
