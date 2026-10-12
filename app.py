"""CloudGuard AI — Intelligent Cloud Cost Analysis and Optimization Platform.
Main Streamlit application entrypoint.
"""
from pathlib import Path
import os
import streamlit as st

# Configure page metadata first
st.set_page_config(
    page_title="CloudGuard AI — Cloud Cost Optimization",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.config import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    DATA_DIR,
    DEFAULT_COST_MEASURE,
    COST_MEASURES,
)
from src.db.database import get_db
from src.importer.parser import BillingParser
from src.ui.styles import apply_custom_styles
from src.ui.pages.overview import render_overview_page
from src.ui.pages.cost_analysis import render_cost_analysis_page
from src.ui.pages.anomalies import render_anomalies_page
from src.ui.pages.forecast import render_forecast_page
from src.ui.pages.recommendations import render_recommendations_page
from src.ui.pages.reports import render_reports_page
from src.ui.pages.settings import render_settings_page


def initialize_session() -> None:
    """Sets up default session state variables."""
    if "active_dataset_id" not in st.session_state:
        st.session_state["active_dataset_id"] = None
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Overview"


def load_demo_dataset(db_manager, demo_filename: str, dataset_label: str) -> bool:
    """Safely loads synthetic demonstration data from local data directory."""
    demo_path = DATA_DIR / demo_filename
    if not demo_path.exists():
        st.error(f"Sample demonstration file '{demo_filename}' not found.")
        return False

    with open(demo_path, "rb") as f:
        file_bytes = f.read()

    df, summary = BillingParser.parse_file(
        file_bytes,
        filename=demo_filename,
        selected_cost_measure=DEFAULT_COST_MEASURE
    )

    if summary.is_success and df is not None:
        ds_id = db_manager.save_dataset(
            name=f"{dataset_label} (Demo)",
            filename=demo_filename,
            row_count=summary.valid_rows,
            start_date=summary.date_min or "2026-08-01",
            end_date=summary.date_max or "2026-10-07",
            total_cost=summary.total_cost,
            currency=summary.currency,
            cost_measure=summary.selected_cost_measure,
            notes="SYNTHETIC DEMONSTRATION DATA FOR EVALUATION"
        )
        db_manager.save_billing_records(ds_id, df)
        st.session_state["active_dataset_id"] = ds_id
        return True
    else:
        st.error(f"Failed to load demonstration data: {'; '.join(summary.errors)}")
        return False


def main() -> None:
    """Main application loop."""
    apply_custom_styles()
    initialize_session()
    db_manager = get_db()

    # ---------------------------------------------------------
    # Sidebar Navigation & Dataset Selector
    # ---------------------------------------------------------
    with st.sidebar:
        st.markdown(f"### 🛡️ {APP_NAME}")
        st.caption(f"{APP_SUBTITLE} &bull; v{APP_VERSION}")

        st.divider()

        # Datasets list
        datasets = db_manager.list_datasets()
        active_dataset = None

        if datasets:
            dataset_options = {d["id"]: f"{d['name']} ({d['start_date'][:7]} to {d['end_date'][:7]})" for d in datasets}
            current_id = st.session_state.get("active_dataset_id")
            if current_id not in dataset_options:
                current_id = datasets[0]["id"]
                st.session_state["active_dataset_id"] = current_id

            selected_id = st.selectbox(
                "Active Dataset",
                options=list(dataset_options.keys()),
                format_func=lambda x: dataset_options[x],
                index=list(dataset_options.keys()).index(current_id)
            )
            st.session_state["active_dataset_id"] = selected_id
            active_dataset = db_manager.get_dataset(selected_id)

            # Compact dataset status badge
            if active_dataset:
                is_demo = "demo" in active_dataset.get("name", "").lower()
                status_color = "#38BDF8" if not is_demo else "#F59E0B"
                badge_text = "DEMO DATA" if is_demo else "USER DATA"

                st.markdown(
                    f"""
                    <div style="background:#1E293B; border:1px solid #334155; border-radius:6px; padding:0.6rem; font-size:0.78rem; color:#94A3B8;">
                        <span style="color:{status_color}; font-weight:700;">● {badge_text}</span><br>
                        <strong>Rows:</strong> {active_dataset['row_count']:,} &bull; <strong>Currency:</strong> {active_dataset.get('currency', 'USD')}<br>
                        <strong>Span:</strong> {active_dataset['start_date']} to {active_dataset['end_date']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No datasets loaded yet.")

        st.divider()

        # 7 Sidebar Navigation Pages
        pages = [
            "Overview",
            "Cost Analysis",
            "Anomalies",
            "Forecast",
            "Recommendations",
            "Reports",
            "Settings"
        ]

        selected_page = st.radio(
            "Navigation",
            options=pages,
            index=pages.index(st.session_state.get("current_page", "Overview")),
            label_visibility="collapsed"
        )
        st.session_state["current_page"] = selected_page

        st.divider()

        # Upload or Replace Billing File
        with st.expander("📤 Import Billing File", expanded=not bool(datasets)):
            uploaded_file = st.file_uploader(
                "Upload AWS Billing CSV",
                type=["csv"],
                help="Accepts AWS Cost and Usage Report (CUR), AWS Cost Explorer exports, or normalized CSVs."
            )

            chosen_measure = st.selectbox(
                "Cost Measure",
                options=list(COST_MEASURES.keys()),
                index=0,
                help="Select accounting cost basis."
            )

            dataset_custom_name = st.text_input("Dataset Label (Optional)", placeholder="e.g. AWS Production Q3")

            if uploaded_file is not None:
                if st.button("Process & Import CSV", type="primary", use_container_width=True):
                    with st.spinner("Validating and parsing billing records locally..."):
                        content_bytes = uploaded_file.getvalue()
                        df_norm, summary = BillingParser.parse_file(
                            content_bytes,
                            filename=uploaded_file.name,
                            selected_cost_measure=chosen_measure
                        )

                        if summary.is_success and df_norm is not None:
                            ds_name = dataset_custom_name.strip() or uploaded_file.name.replace(".csv", "")
                            new_id = db_manager.save_dataset(
                                name=ds_name,
                                filename=uploaded_file.name,
                                row_count=summary.valid_rows,
                                start_date=summary.date_min or "2026-01-01",
                                end_date=summary.date_max or "2026-01-01",
                                total_cost=summary.total_cost,
                                currency=summary.currency,
                                cost_measure=summary.selected_cost_measure,
                                notes="Uploaded user billing dataset"
                            )
                            db_manager.save_billing_records(new_id, df_norm)
                            st.session_state["active_dataset_id"] = new_id

                            st.success(f"Successfully imported {summary.valid_rows:,} rows (${summary.total_cost:,.2f})!")
                            if summary.warnings:
                                for w in summary.warnings[:3]:
                                    st.warning(f"⚠️ {w}")
                            st.rerun()
                        else:
                            st.error(f"Import failed: {'; '.join(summary.errors)}")

            # Quick demo loader button
            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Load Synthetic Demo Data", use_container_width=True):
                with st.spinner("Loading synthetic AWS demonstration dataset..."):
                    if load_demo_dataset(db_manager, "sample_aws_cur.csv", "AWS Demo CUR"):
                        st.success("Loaded synthetic demonstration dataset!")
                        st.rerun()

    # ---------------------------------------------------------
    # Main Content Area
    # ---------------------------------------------------------
    if not active_dataset:
        st.markdown("## Welcome to CloudGuard AI")
        st.markdown(
            "An intelligent, privacy-first local platform for AWS cloud cost analysis, anomaly detection, "
            "explainable forecasting, and optimization."
        )

        st.info("👋 No dataset is currently loaded. To get started:")
        col_start1, col_start2 = st.columns(2)
        with col_start1:
            st.markdown("### 📤 Upload Your AWS Billing CSV")
            st.markdown(
                "Upload an AWS Cost and Usage Report (CUR) or Cost Explorer export via the sidebar. "
                "Data is processed and stored 100% locally on your machine."
            )
        with col_start2:
            st.markdown("### 🧪 Explore Demonstration Data")
            st.markdown(
                "Load our verified synthetic AWS billing dataset (clearly marked as demo data) "
                "to explore features immediately."
            )
            if st.button("Load Synthetic Demo Data Now", type="primary"):
                if load_demo_dataset(db_manager, "sample_aws_cur.csv", "AWS Demo CUR"):
                    st.rerun()
        return

    # Fetch billing records for active dataset
    records_df = db_manager.get_billing_records_df(active_dataset["id"])

    # Page Routing
    current_page = st.session_state.get("current_page", "Overview")

    try:
        if current_page == "Overview":
            render_overview_page(records_df, active_dataset, db_manager)
        elif current_page == "Cost Analysis":
            render_cost_analysis_page(records_df, active_dataset)
        elif current_page == "Anomalies":
            render_anomalies_page(records_df, active_dataset, db_manager)
        elif current_page == "Forecast":
            render_forecast_page(records_df, active_dataset)
        elif current_page == "Recommendations":
            render_recommendations_page(records_df, active_dataset, db_manager)
        elif current_page == "Reports":
            render_reports_page(records_df, active_dataset, db_manager)
        elif current_page == "Settings":
            render_settings_page(active_dataset, db_manager)
        else:
            st.error(f"Unknown page: {current_page}")
    except Exception as e:
        st.error(f"An unexpected error occurred while rendering the page: {str(e)}")
        st.caption("Please check application logs or retry. Your data remains safely persisted in SQLite.")


if __name__ == "__main__":
    main()
