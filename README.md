# CloudGuard AI — Intelligent Cloud Cost Analysis and Optimization Platform

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-5.22+-purple.svg)](https://plotly.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-green.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-gray.svg)](LICENSE)

A complete, production-grade, locally-running financial analysis and cost optimization platform for AWS cloud billing data. 

CloudGuard AI runs **entirely offline on Windows 11**, without requiring cloud credentials, paid APIs, or cloud hosting. It accepts standard AWS Cost and Usage Reports (CUR) and AWS Cost Explorer CSV exports, verifies accounting integrity, detects statistical spending anomalies, explains cost increases using deterministic root-cause calculations, forecasts future expenditures, and delivers actionable, defensible optimization recommendations.

---

## 🎯 Key Capabilities

- **100% Local Execution:** Operates on your Windows 11 desktop. Zero billing data or telemetry leaves your machine.
- **No AWS Credentials Required:** Evaluates exported billing CSVs directly without requiring IAM keys or cloud access.
- **Multi-Format Ingestion:** Intelligently maps AWS Cost and Usage Reports (CUR), AWS Cost Explorer exports, and normalized CSV formats.
- **Explainable Anomaly Detection:** Employs Median Absolute Deviation (MAD), modified Z-scores, and rolling baselines with strict evidence classification.
- **Deterministic Root-Cause Analysis:** Breaks down cost increases by usage type, region, resource ARN, and unit quantity vs. price shifts.
- **Transparent Forecasting:** Extrapolates month-to-date run-rates and OLS linear trends with 95% confidence intervals and explicit uncertainty disclosures.
- **Evidence-Backed Recommendations:** Recommends concrete actions (Savings Plans, unattached EBS volume review, S3 Intelligent-Tiering, network egress caching) with status tracking (`Open`, `Under review`, `Accepted`, `Dismissed`, `Completed`).
- **Audit-Ready Reports:** Exports 5 standardized CSV reports and an Executive Markdown Cost Audit Summary.

---

## 📁 Project Architecture

```
cloudguard-ai/
├── .streamlit/
│   └── config.toml                  # Enterprise dark navy theme & server settings
├── data/
│   ├── sample_aws_cur.csv           # Synthetic AWS CUR demonstration dataset
│   └── sample_aws_cost_explorer.csv    # Synthetic AWS Cost Explorer demonstration dataset
├── src/
│   ├── config.py                    # Constants, default thresholds, evidence classifications
│   ├── db/
│   │   └── database.py              # SQLite connection manager, schema initialization, queries
│   ├── importer/
│   │   ├── column_mapper.py         # Pattern matcher for CUR, Cost Explorer, & normalized CSVs
│   │   ├── validator.py             # Delimiter detection, encoding, data types, deduplication
│   │   └── parser.py                # CSV ingestion orchestrator and ImportSummary generator
│   ├── analytics/
│   │   ├── cost_engine.py           # Period-over-period comparisons, aggregations, HHI concentration
│   │   ├── anomaly_detector.py      # MAD, rolling baselines, threshold surge detection
│   │   ├── root_cause.py            # Evidence-backed multi-dimensional drilldowns
│   │   ├── forecaster.py            # MTD run-rate & OLS linear regression forecasting
│   │   └── recommender.py           # Rule-based cloud cost optimization engine
│   ├── reports/
│   │   └── exporter.py              # CSV exporters & executive markdown report generator
│   └── ui/
│       ├── styles.py                # Enterprise typography, CSS cards, responsive layout
│       ├── components.py            # Metric cards, alert cards, Plotly dark charts
│       └── pages/
│           ├── overview.py          # Primary dashboard (4 metric cards, trend chart, top 5, alerts)
│           ├── cost_analysis.py     # Multi-dimensional filtering (Service, Region, Resource)
│           ├── anomalies.py         # Anomaly review board with root-cause drilldown
│           ├── forecast.py          # Run-rate & trend projections with confidence envelopes
│           ├── recommendations.py   # Optimization workflow & tracking
│           ├── reports.py           # CSV downloads and Executive Summary report viewer
│           └── settings.py          # Stored dataset management, deletion, & privacy info
├── tests/
│   ├── conftest.py                  # Pytest fixtures and synthetic test datasets
│   ├── test_importer.py             # CSV parsing, mapping, edge case tests
│   ├── test_db.py                   # SQLite persistence and cascade deletion tests
│   ├── test_cost_analysis.py        # Cost aggregation & zero-division tests
│   ├── test_anomaly_detection.py    # Statistical anomaly detection algorithm tests
│   ├── test_forecaster.py           # Forecasting models & eligibility tests
│   ├── test_recommender.py          # Recommendation rules & evidence tests
│   ├── test_reports.py              # CSV and markdown report generation tests
│   └── test_integration.py          # Full end-to-end application lifecycle test
├── app.py                           # Streamlit application entrypoint
├── run_tests.py                     # Standalone automated test runner
├── requirements.txt                 # Python package dependencies
├── .gitignore                       # Protects databases, uploads, and logs from Git
└── README.md                        # Documentation and Windows setup guide
```

---

## 🛠️ Windows 11 Installation & Setup

### Prerequisites
- Windows 11 (64-bit)
- Python 3.13 (or Python 3.11+) installed with "Add Python to PATH" enabled

### Step 1: Open PowerShell
Open Windows Terminal or PowerShell and navigate to the project directory:
```powershell
cd "C:\Users\Ramji S\.gemini\antigravity\scratch\cloudguard-ai"
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell blocks script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🚀 Running the Live Server

You can launch the live server using any of the following methods:

### Method 1: Double-Click Launcher (Easiest)
Simply double-click the included batch script in File Explorer:
- **`run_live_server.bat`**
*(This script automatically sets up the virtual environment, installs dependencies if missing, and launches the server).*

### Method 2: Via PowerShell
```powershell
.\run_live_server.ps1
```

### Method 3: Via Python Runner
```powershell
python run_server.py
```

### Method 4: Manual Command
```powershell
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

The application will open automatically in your web browser at:
**`http://localhost:8501`**

> **Live Reloading:** Any edits to the source code or configurations will automatically trigger a hot reload in the browser without requiring a server restart.

---

## 🧪 Running Automated Tests

Run the full automated test suite containing 25+ comprehensive tests:

### Option A: Using the Standalone Runner
```powershell
python run_tests.py
```

### Option B: Using Pytest
```powershell
pytest -v
```

---

## 📊 Modules & Implementation Guide

### 1. Data Import Module (`src/importer/`)
- **Safe Ingestion:** Supports UTF-8, UTF-8-BOM, Latin-1, and CP1252 encodings with automatic delimiter detection (comma, semicolon, tab).
- **Flexible Schema Mapping:** Automatically identifies AWS CUR headers (`lineItem/UnblendedCost`, `lineItem/ProductCode`, etc.) and AWS Cost Explorer exports (`UsageDate`, `Service`, `UnblendedCost`).
- **Cost Measure Selection:** Allows users to choose between `UnblendedCost` (cash basis), `NetUnblendedCost` (discounted basis), and `BlendedCost`.
- **Validation & Hygiene:** Detects unparseable dates, strips currency formatting, flags mixed currencies, and removes duplicate billing rows.

### 2. Internal Persistence Module (`src/db/`)
- Built on local SQLite with foreign-key constraints (`PRAGMA foreign_keys = ON;`).
- Separate relational tables for:
  - `imported_datasets`: Master records of uploaded datasets.
  - `normalized_billing_records`: High-performance indexed rows (`(dataset_id, usage_date)`, `(dataset_id, service)`).
  - `detected_anomalies`: Anomaly findings with review states (`Open`, `Reviewed`, `Dismissed`).
  - `forecast_results`: Projection runs with bounds and methodology metadata.
  - `recommendations`: Optimization items with workflow status.
- **Cascade Deletion:** Permanently and cleanly removes any dataset and all child records atomically.

### 3. Cost Analysis Engine (`src/analytics/cost_engine.py`)
- Calculates total period cost, prior-period matched duration comparison, absolute and percentage change.
- **Zero-Division Handling:** Correctly handles cases where prior-period spend was zero without arithmetic error, labeling findings as new baseline charges.
- **Concentration Analysis:** Computes the Herfindahl-Hirschman Index (HHI) and top-3 service spend ratio to classify budget risk into Diversified, Moderate, or High Concentration.

### 4. Anomaly Detection Engine (`src/analytics/anomaly_detector.py`)
- **Robust Statistics:** Employs Median Absolute Deviation (MAD) and modified Z-scores (Iglewicz & Hoaglin) to detect spikes even when previous anomalies exist in history.
- **Rolling Baselines:** Computes 7-day moving averages and standard deviation thresholds for short-term surges.
- **Traceable Evidence:** Every anomaly records the detection date, baseline cost, actual cost, trigger reason, and supporting raw record count.

### 5. Root-Cause Investigation Engine (`src/analytics/root_cause.py`)
- Analyzes anomalous surges across 4 distinct dimensions:
  1. Usage Type driver (e.g. `BoxUsage:c5.2xlarge` vs. `DataTransfer-Out-Bytes`).
  2. Geographic AWS Region.
  3. Resource Identifier (ARN / instance ID, when present).
  4. Workload quantity vs. unit rate change.
- **Deterministic Narrative:** Generates factual explanations without speculative claims.
- **Disclosures:** Explicitly lists dimensions that cannot be evaluated if optional fields are absent from the export.

### 6. Forecasting Engine (`src/analytics/forecaster.py`)
- **Month-to-Date (MTD) Run-Rate:** Blends recent 7-day velocity with month-to-date average to extrapolate remaining calendar days.
- **Ordinary Least Squares (OLS) Regression:** Evaluates daily expenditure trajectory over time with 95% prediction intervals.
- **Strict Data Gates:** Refuses projections when data points are insufficient (minimum 3 days for MTD, 7 days for trend).

### 7. Recommendation Engine (`src/analytics/recommender.py`)
- Rules evaluate actual billing facts to generate defensible recommendations:
  - High Service Concentration (>50% spend).
  - High Network Egress Charges (>15% service cost).
  - Unattached EBS Storage Allocation patterns.
  - S3 Storage Lifecycle & Intelligent-Tiering opportunities.
  - Compute Savings Plans for continuous On-Demand baselines.
- Workflow management allows team members to update statuses from `Open` to `Under review`, `Accepted`, `Dismissed`, or `Completed`.

### 8. Reports & Audit Summary (`src/reports/`)
- Export 5 clean CSVs: Cost Summary, Anomalies, Service Breakdown, Forecast, Recommendations.
- Generates an Executive Markdown Summary detailing actuals, calculated baselines, statistical findings, and accounting assumptions.

---

## 🔒 Security & Privacy Notice

- **Local Storage:** All imported data is saved directly in `./cloudguard.db` on your local disk.
- **Zero Telemetry:** No third-party analytical trackers, cloud API calls, or remote servers are contacted.
- **Credential Freedom:** CloudGuard AI never asks for or stores AWS Access Keys or Secret Keys.
- **Repository Safety:** The included `.gitignore` prevents database files, uploaded CSVs, and logs from being committed to source control.

---

## 📄 License

MIT License. Designed and engineered for transparent enterprise cloud financial management.
