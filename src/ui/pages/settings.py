"""Settings, dataset lifecycle management, and privacy transparency page."""
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.config import DATABASE_PATH, COST_MEASURES
from src.analytics.cost_engine import CostEngine


def render_settings_page(
    dataset_info: Optional[Dict[str, Any]],
    db_manager: Any
) -> None:
    """Renders dataset lifecycle management, database administration, and privacy settings."""
    st.markdown("### Settings & Dataset Management")

    tab_mgmt, tab_accounting, tab_privacy = st.tabs([
        "Dataset Lifecycle & Deletion", "Accounting & Cost Measures", "Security & Local Privacy"
    ])

    # ---------------------------------------------------------
    # 1. Dataset Management
    # ---------------------------------------------------------
    with tab_mgmt:
        st.markdown("##### Stored Datasets in Local SQLite Database")
        datasets = db_manager.list_datasets()

        if not datasets:
            st.info("No datasets currently saved in local SQLite storage.")
        else:
            table_data = []
            for d in datasets:
                is_active = dataset_info and d["id"] == dataset_info.get("id")
                table_data.append({
                    "ID": d["id"],
                    "Status": "Active" if is_active else "Stored",
                    "Dataset Name": d["name"],
                    "Filename": d["filename"],
                    "Row Count": f"{d['row_count']:,}",
                    "Date Range": f"{d['start_date']} to {d['end_date']}",
                    "Total Cost": CostEngine.format_currency(d["total_cost"], d.get("currency", "USD")),
                    "Cost Measure": d["cost_measure"],
                    "Imported (UTC)": d["imported_at"][:19]
                })

            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

            st.divider()

            # Dataset removal
            st.markdown("##### Delete Dataset")
            st.caption("Permanently removes a dataset and all associated records, anomalies, and recommendations from the local SQLite database.")

            del_target = st.selectbox(
                "Select Dataset to Remove",
                options=[f"ID {d['id']}: {d['name']} ({d['filename']})" for d in datasets]
            )

            target_id = int(del_target.split(":")[0].replace("ID", "").strip())

            if st.button("🗑️ Permanently Delete Selected Dataset", type="primary"):
                success = db_manager.delete_dataset(target_id)
                if success:
                    st.success(f"Dataset ID {target_id} and all associated records were successfully deleted.")
                    if dataset_info and dataset_info.get("id") == target_id:
                        st.session_state["active_dataset_id"] = None
                    st.rerun()
                else:
                    st.error("Failed to delete dataset.")

    # ---------------------------------------------------------
    # 2. Accounting & Cost Measures
    # ---------------------------------------------------------
    with tab_accounting:
        st.markdown("##### Supported AWS Cost Measures")
        for key, desc in COST_MEASURES.items():
            st.markdown(f"- **{key}:** {desc}")

        st.markdown("##### Accounting Assumptions")
        st.markdown(
            "1. **Credits and Refunds:** AWS billing exports frequently contain promotional credits, "
            "enterprise discounts, and tax refunds as negative line items. By default, CloudGuard AI preserves "
            "these items to reflect actual cash expense.\n"
            "2. **Currency Uniformity:** If an export contains mixed currencies (e.g. USD and EUR), "
            "CloudGuard AI warns the user and evaluates amounts under the dominant currency tag to prevent mixing rates.\n"
            "3. **Zero-Baseline Changes:** When a service had $0.00 spend in the prior period, percentage growth is mathematically "
            "undefined and labeled as a new baseline rather than an artificial percentage."
        )

    # ---------------------------------------------------------
    # 3. Security & Privacy Disclosure
    # ---------------------------------------------------------
    with tab_privacy:
        st.markdown("##### Local Processing & Data Privacy Guarantee")
        st.info(
            f"🔒 **Zero Cloud Transmission:** CloudGuard AI processes all billing files entirely locally. "
            f"No data is transmitted to external servers, cloud AI providers, or third-party telemetry."
        )
        st.markdown(
            f"**Local Database Path:** `{DATABASE_PATH}`\n\n"
            "**Key Security Safeguards:**\n"
            "- **No AWS Credentials:** This application never requires AWS IAM keys, access tokens, or account permissions.\n"
            "- **Parameterized Queries:** All database interactions use parameterized SQL statements to eliminate injection risks.\n"
            "- **Memory Hygiene:** Uploaded raw files are read into memory buffers, normalized, and not left as unsecured temporary files on disk.\n"
            "- **Sensitive Data Handling:** AWS billing CSVs may contain internal account IDs, project names, and financial figures. "
            "CloudGuard AI includes `.gitignore` rules preventing local databases and uploads from being committed to version control."
        )
