# CloudGuard AI — Test Plan & Quality Assurance Report

## 1. Overview
This test plan validates that the browser-based, client-side implementation of **CloudGuard AI** correctly parses billing files, normalizes alternative data schemas, computes exact financial metrics, detects statistical anomalies, generates damped cost forecasts, and produces explainable cost optimization recommendations without any backend dependencies.

---

## 2. Test Datasets (`tests/test-data/`)

| Test File | Purpose & Edge Cases Covered | Expected Behavior |
|-----------|------------------------------|-------------------|
| `sample-billing.csv` | Full 30-day multi-service, multi-region dataset with credits and spikes | Full dashboard population, $6,000+ spend, 1 major spike detected, storage & compute recommendations |
| `normal-daily-costs.csv` | 10 days of steady EC2 & S3 spend with low variance | Normal baseline established; 0 anomalies flagged |
| `sudden-cost-spike.csv` | 9 days of $50 spend, day 10 spike of $450 | Exactly 1 Critical anomaly detected on day 10 with MAD > 6.0 |
| `missing-required-columns.csv` | CSV missing `service` column | Validation error caught during mapping; prevents corrupted import |
| `invalid-numeric-values.csv` | Non-numeric entries (`$45.00`, `INVALID_COST`, `N/A`, `NaN`, empty) | Skips invalid lines with warnings; sanitizes valid currency strings |
| `negative-credits.csv` | Legitimate cloud provider credits (`-$100.00`, `-$25.00`) | Accurately subtracted from gross spend; credit callout shown |
| `duplicate-rows.csv` | Exactly identical row entries | Fingerprint collision detected and counted as duplicates in import summary |
| `missing-dates.csv` | Blank or null date entries | Invalid rows safely skipped with row-level warnings |
| `zero-cost-services.csv` | $0.00 items (IAM, VPC, CloudTrail free tiers) | Recorded without division-by-zero or NaN in percentage calculations |
| `empty.csv` | 0-byte or blank file | Error banner displayed: "CSV header row appears to be missing or malformed" |
| `alternative-column-names.csv` | AWS CUR names (`line_item_unblended_cost`, `product_service`, `billing_date`) | Column heuristic auto-maps headers to standard schema fields |
| `different-date-formats.csv` | Mixed formats (`YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, ISO 8601) | Normalized to canonical `YYYY-MM-DD` |

---

## 3. Test Cases & Verification Matrix

### Suite 1: Date Normalization
- [x] **TC-DATE-01**: Parse standard ISO 8601 (`YYYY-MM-DD`).
- [x] **TC-DATE-02**: Parse US standard date (`MM/DD/YYYY`).
- [x] **TC-DATE-03**: Parse European standard date (`DD/MM/YYYY`) when day > 12.
- [x] **TC-DATE-04**: Parse ISO datetime strings (`YYYY-MM-DDTHH:mm:ssZ`).
- [x] **TC-DATE-05**: Reject invalid calendar dates (e.g., `2026-02-31`, `invalid-date`, `null`).

### Suite 2: Numeric & Currency Parsing
- [x] **TC-NUM-01**: Parse positive floating point string (`145.25`).
- [x] **TC-NUM-02**: Parse currency string with commas and dollar symbols (`$1,245.80`).
- [x] **TC-NUM-03**: Parse accounting parentheses for negative credit (`(150.00)` -> `-150.00`).
- [x] **TC-NUM-04**: Parse negative prefix strings (`-$45.50` -> `-45.50`).
- [x] **TC-NUM-05**: Reject non-numeric entries (`N/A`, `NaN`, `FREE`, empty).

### Suite 3: Schema Validation & Column Auto-Mapping
- [x] **TC-MAP-01**: Auto-map AWS CUR style column names (`line_item_unblended_cost`, `line_item_product_code`).
- [x] **TC-MAP-02**: Detect ambiguous multiple cost fields (`unblended_cost` and `blended_cost`) and alert user.
- [x] **TC-MAP-03**: Reject import when required fields (`usage_date`, `service`, `cost_amount`) cannot be mapped.

### Suite 4: Cost Aggregation Engine
- [x] **TC-AGG-01**: Accurate net spend calculation (`net = gross - credits`).
- [x] **TC-AGG-02**: Accurate average daily cost calculation (`avg = net / uniqueDays`).
- [x] **TC-AGG-03**: Service cost distribution percentages sum to exactly 100%.
- [x] **TC-AGG-04**: Period-over-period comparison calculates mathematically sound difference and percentage change.

### Suite 5: Anomaly Detection Engine (Rolling Median & MAD)
- [x] **TC-ANOM-01**: Outlier resistance: median and MAD are unaffected by extreme single-day outliers.
- [x] **TC-ANOM-02**: Flag sudden cost spike: detects $450 spike against $50 historical baseline as Critical severity.
- [x] **TC-ANOM-03**: Zero baseline handling: detects sudden activation of previously inactive service without divide-by-zero errors.
- [x] **TC-ANOM-04**: Actionable investigation steps provided for detected anomaly categories.

### Suite 6: Cost Forecasting
- [x] **TC-FCAST-01**: Data sufficiency rule: refuses to generate misleading forecasts when historical data < 7 days.
- [x] **TC-FCAST-02**: Trend projection with damping: linear regression slope is damped into the future to prevent runaway projections.
- [x] **TC-FCAST-03**: Upper and lower confidence bounds calculated at 95% confidence interval ($\pm 1.96 \cdot \text{stdDev}$).

### Suite 7: Optimization Recommendations
- [x] **TC-REC-01**: Commitment Discount recommendation generated for steady, high-spend EC2 compute workloads.
- [x] **TC-REC-02**: S3 Lifecycle transition recommendation generated when storage costs compound steadily over time.
- [x] **TC-REC-03**: Data transfer audit recommendation generated when egress costs are substantial.
- [x] **TC-REC-04**: Tagging governance recommendation generated when > 20% of spend is untagged.

---

## 4. Test Execution
All 18 automated unit and integration tests can be verified by opening [`tests/test-runner.html`](test-runner.html) in any modern browser (Chrome, Edge, Firefox, Safari).
