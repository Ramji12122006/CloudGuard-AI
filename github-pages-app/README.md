# CloudGuard AI — Cloud Billing Analysis & Cost Optimization Dashboard

> **A modern, responsive, 100% client-side FinOps web application deployable directly on GitHub Pages without any backend server.**

CloudGuard AI enables engineering and finance teams to upload cloud billing CSV files (AWS CUR, Google Cloud Billing, Azure Cost Management, or custom CSVs), visualize daily spending trends, detect statistical anomalies using rolling baselines and Median Absolute Deviation (MAD), forecast forward-looking expenditures, and receive explainable, evidence-backed cost optimization recommendations.

---

## 🌟 Key Features

1. **Overview Dashboard**
   - 6 high-level KPI summary cards: Total Spend, Average Daily Cost, Highest-Cost Service, Period-over-Period Change (with % and directional indicator), Detected Anomalies count, and Estimated Potential Savings.
   - Interactive Chart.js charts: Daily Spending Trend, Cost by Service doughnut, Cost by Region doughnut.
   - Recent billing records table, recent anomaly alerts, and top optimization opportunities.
   - Reactive updates: All metrics, charts, and tables update instantly as filters or datasets change.

2. **CSV Billing Data Import**
   - Drag-and-drop file upload with progress feedback powered by **Papa Parse**.
   - Automatic column inspection, type detection, and schema validation.
   - Flexible column mapping modal with intelligent auto-detection for common cloud providers (AWS, GCP, Azure).
   - Ambiguous cost field collision detection (alerts user if multiple cost columns such as `unblended_cost` and `blended_cost` exist).
   - Preserves negative adjustments, promotional credits, and enterprise discounts with clear accounting explanations.
   - Downloadable CSV template and one-click "Load Sample Dataset" feature.

3. **Cost Explorer**
   - Multi-dimensional filtering: Date range picker, Cloud Service selector, Region selector, and real-time text search.
   - Granularity toggling: Aggregate costs by Daily, Weekly, or Monthly views.
   - Chart style switching: Bar chart vs. Line chart.
   - Sortable, paginated data table with live row range counts, page size controls, and client-side CSV export of filtered records.

4. **Statistical Anomaly Detection**
   - Robust non-parametric statistical engine based on **Rolling Median** and **Median Absolute Deviation (MAD)**.
   - Resilient against past outliers and non-normal financial distributions.
   - Configurable sensitivity presets: Strict (2.0x MAD), Balanced (3.0x MAD), or Relaxed (4.5x MAD).
   - Safe handling of zero baselines, insufficient data (<5 days), and negative adjustments.
   - Severity classification (Critical, High, Medium, Low) with explainable detection reasons and actionable investigation checklists.

5. **Cost Forecasting**
   - Forward-looking daily cost projections for 7, 14, or 30 days ahead.
   - Method transparency: Applies Weighted Moving Average (EWMA) for baseline workloads or Trend-Adjusted Linear Regression with conservative slope damping when $\ge 14$ days of history are available.
   - Visualizes continuous historical actuals transitioning into dashed forecast projections with shaded 95% confidence interval bands.
   - Data sufficiency enforcement: Refuses to generate misleading forecasts when historical data is under 7 days.

6. **Explainable Cost Optimization Recommendations**
   - Rule-based FinOps recommendation engine inspecting observed billing records:
     - **Commitment Discounts**: Evaluates steady 24/7 compute usage (EC2, EKS, VMs) for 1-year Savings Plans or Reserved Instances (conservative 25% savings estimate).
     - **Storage Lifecycle Transitions**: Detects compounding storage growth (S3, Blobs) and recommends automated transition to Infrequent Access / Glacier.
     - **Network Egress Audit**: Identifies cross-AZ and internet data transfer spikes, recommending VPC Gateway Endpoints and CDN caching.
     - **Period-over-Period Growth**: Alerts on services with >30% sudden growth across consecutive periods.
     - **Tagging Governance**: Identifies untagged spending and recommends policy enforcement.
   - Every recommendation provides: Title, affected service, evidence from uploaded data, rationale, recommended action, defensible savings, and explicit limitations.

7. **Executive Reports & Export**
   - Comprehensive executive billing summary report.
   - Client-side export to CSV (filtered records) and JSON (full structured analysis).
   - Professional `@media print` styling for clean, paper-ready printing or Save to PDF via browser print dialog (`Ctrl+P` / `Cmd+P`).

8. **Settings & Zero-Backend Privacy**
   - Multi-currency support: USD (`$`), EUR (`€`), GBP (`£`), INR (`₹`), CAD (`C$`), AUD (`A$`), JPY (`¥`).
   - 100% Client-Side Privacy: All CSV parsing and calculations execute exclusively in local browser memory. Zero external server uploads, zero telemetry, zero cookies.

---

## 🛠️ Technology Stack

- **HTML5:** Semantic markup, accessible labels, ARIA landmarks.
- **CSS3:** Custom responsive design system, dark navy and slate theme, CSS variables, print stylesheet.
- **Vanilla JavaScript (ES6+):** Pure modular JavaScript without bundlers or heavy frameworks.
- **Papa Parse (CDN):** Fast, in-browser CSV parsing.
- **Chart.js (CDN):** Responsive canvas-based data visualizations.
- **GitHub Pages:** Static site hosting and deployment.

---

## 📂 Project Structure

```text
github-pages-app/
├── index.html              # Main application entry point
├── 404.html                # Single-page fallback for GitHub Pages
├── README.md               # App documentation
├── assets/
│   ├── css/
│   │   ├── styles.css      # Core design tokens, typography, utilities, print styles
│   │   ├── dashboard.css   # Sidebar, layout, KPI cards, charts, dropzone
│   │   └── responsive.css  # Tablet & mobile breakpoints, collapsible navigation
│   ├── js/
│   │   ├── app.js          # App orchestrator, event binding, routing
│   │   ├── state.js        # Pub/Sub reactive state management
│   │   ├── validation.js   # Date, numeric, and schema validation
│   │   ├── dataNormalizer.js# Column mapping heuristics & record normalization
│   │   ├── csvImporter.js  # Papa Parse integration, file handling, templates
│   │   ├── costEngine.js   # Financial aggregations, filtering, pagination
│   │   ├── anomalyDetector.js# Rolling median & MAD statistical anomaly engine
│   │   ├── forecaster.js   # 7/14/30 day trend-adjusted forecasting
│   │   ├── recommendations.js# Rule-based explainable FinOps recommendations
│   │   ├── charts.js       # Chart.js wrappers & lifecycle management
│   │   ├── reports.js      # CSV, JSON export & print formatting
│   │   └── ui.js           # View controller, DOM renderers, modals, toasts
│   └── images/
│       └── logo.svg        # Scalable vector logo
├── sample-data/
│   └── sample-billing.csv  # Realistic 30-day multi-cloud sample dataset
└── tests/
    ├── test-data/          # 11 specialized test datasets
    ├── test-suite.js       # 18 automated unit and integration tests
    ├── test-runner.html    # In-browser test runner
    └── test-plan.md        # Test matrix & validation methodology
```

---

## 🧪 Running Automated Tests

To execute the automated test suite:
1. Open [`tests/test-runner.html`](tests/test-runner.html) in any modern browser (Google Chrome, Microsoft Edge, Mozilla Firefox, or Safari).
2. The suite executes 18 assertions across date normalization, numeric validation, credit accounting, MAD anomaly detection, linear regression forecasting, and recommendation rules.
3. Review the live test results, durations, and pass/fail indicators.

---

## 🚀 GitHub Pages Deployment Steps

1. Commit and push the repository to your GitHub account on branch `main`.
2. Go to your repository **Settings** on GitHub.
3. In the left sidebar, click **Pages** (under the "Code and automation" section).
4. Under **Build and deployment**:
   - **Source**: Select **GitHub Actions** (recommended, as configured in `.github/workflows/deploy.yml`), OR
   - **Source**: Select **Deploy from a branch**, choose `main`, and select `/github-pages-app` folder if supported, or deploy from the root.
5. With the included GitHub Actions workflow, deployment is automated:
   - On every push to `main`, GitHub Actions automatically packages and deploys `github-pages-app/`.
6. Once deployed, GitHub will report the live website URL (e.g. `https://<username>.github.io/<repo-name>/`).
