"""Anomalies dashboard and root-cause investigation page."""
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.analytics.anomaly_detector import AnomalyDetector
from src.analytics.root_cause import RootCauseAnalyzer
from src.analytics.cost_engine import CostEngine
from src.ui.components import render_metric_card


def render_anomalies_page(
    records_df: pd.DataFrame,
    dataset_info: Dict[str, Any],
    db_manager: Any
) -> None:
    """Renders anomaly detection results, threshold controls, and root cause investigation."""
    st.markdown("### Spend Anomalies & Root-Cause Investigation")
    dataset_id = dataset_info["id"]
    currency = dataset_info.get("currency", "USD")

    # ---------------------------------------------------------
    # 1. Detection Controls & Re-scan
    # ---------------------------------------------------------
    with st.expander("⚙️ Anomaly Detection Thresholds & Settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            pct_thresh = st.slider("Percentage Surge Threshold (%)", min_value=10, max_value=200, value=50, step=5)
        with c2:
            abs_thresh = st.number_input("Absolute Increase Threshold ($)", min_value=5.0, max_value=500.0, value=25.0, step=5.0)
        with c3:
            mad_thresh = st.slider("Modified Z-Score / MAD Multiplier", min_value=1.5, max_value=5.0, value=3.0, step=0.1)

        if st.button("Re-run Anomaly Scanner with Custom Thresholds"):
            detector = AnomalyDetector(
                pct_threshold=float(pct_thresh),
                abs_threshold=float(abs_thresh),
                mad_threshold=float(mad_thresh)
            )
            detected = detector.detect_anomalies(records_df)
            db_manager.save_anomalies(dataset_id, [a.to_dict() for a in detected])
            st.success(f"Scan complete. Identified {len(detected)} potential anomalies.")
            st.rerun()

    # ---------------------------------------------------------
    # 2. Anomaly List & Status Filter
    # ---------------------------------------------------------
    db_anomalies = db_manager.get_anomalies(dataset_id)
    if not db_anomalies:
        # Run initial scan
        detector = AnomalyDetector()
        detected = detector.detect_anomalies(records_df)
        if detected:
            db_manager.save_anomalies(dataset_id, [a.to_dict() for a in detected])
            db_anomalies = db_manager.get_anomalies(dataset_id)

    # Status filter
    f_col1, f_col2 = st.columns([2, 5])
    with f_col1:
        status_filter = st.selectbox("Status Filter", options=["All", "Open", "Reviewed", "Dismissed"], index=0)

    filtered_anomalies = db_anomalies
    if status_filter != "All":
        filtered_anomalies = [a for a in db_anomalies if a.get("status") == status_filter]

    # Metric counts
    total_anomalies = len(db_anomalies)
    open_anomalies = sum(1 for a in db_anomalies if a.get("status") == "Open")
    highest_surge = max([a["absolute_increase"] for a in db_anomalies], default=0.0)

    m1, m2, m3 = st.columns(3)
    with m1:
        render_metric_card("Total Anomalies Detected", str(total_anomalies), subtext="Across full dataset")
    with m2:
        render_metric_card("Open Anomalies", str(open_anomalies), subtext="Requiring investigation", is_favorable=False if open_anomalies > 0 else True)
    with m3:
        render_metric_card("Largest Single Surge", CostEngine.format_currency(highest_surge, currency), subtext="Maximum absolute increase")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if not filtered_anomalies:
        st.info("No anomalies match the current status filter. Spending remained within statistical bounds.")
        return

    # ---------------------------------------------------------
    # 3. Interactive Anomaly Cards with Root Cause Investigation
    # ---------------------------------------------------------
    for anomaly in filtered_anomalies:
        aid = anomaly["id"]
        status = anomaly.get("status", "Open")
        svc = anomaly["service"]
        det_date = anomaly["detection_date"]
        actual = anomaly["actual_cost"]
        baseline = anomaly["baseline_cost"]
        abs_inc = anomaly["absolute_increase"]
        pct_inc = anomaly.get("percentage_increase")
        pct_str = f" (+{pct_inc:.1f}%)" if pct_inc is not None else ""
        evidence = anomaly.get("evidence_level", "Confirmed by billing data")

        with st.expander(f"🚨 {svc} — ${abs_inc:,.2f}{pct_str} on {det_date} [{status}]", expanded=(status == "Open")):
            head_col1, head_col2 = st.columns([3, 1])

            with head_col1:
                st.markdown(f"**Trigger Reason:** {anomaly['trigger_reason']}")
                st.markdown(f"**Method:** `{anomaly['detection_method']}` &bull; **Evidence Level:** `{evidence}`")
                st.markdown(f"**Actual Spend:** ${actual:,.2f} &bull; **Baseline:** ${baseline:,.2f} &bull; **Difference:** +${abs_inc:,.2f}")

            with head_col2:
                # Status updater
                new_status = st.selectbox(
                    "Update Status",
                    options=["Open", "Reviewed", "Dismissed"],
                    index=["Open", "Reviewed", "Dismissed"].index(status),
                    key=f"status_sel_{aid}"
                )
                if new_status != status:
                    db_manager.update_anomaly_status(aid, new_status)
                    st.success(f"Status updated to {new_status}")
                    st.rerun()

            st.divider()

            # Root Cause Investigation Drilldown
            st.markdown("#### Root-Cause Investigation")
            finding = RootCauseAnalyzer.investigate(
                records_df,
                service=svc,
                detection_date=det_date,
                baseline_cost=baseline,
                actual_cost=actual
            )

            # Deterministic Narrative
            st.info(f"**Evidence Finding:** {finding.summary_text}")

            # Dimensional Drilldown tables
            if finding.breakdown_tables:
                rc_tab1, rc_tab2, rc_tab3 = st.tabs(["Usage Type Drivers", "Regional Distribution", "Resource Identifiers"])

                with rc_tab1:
                    if "usage_types" in finding.breakdown_tables:
                        ut_df = finding.breakdown_tables["usage_types"]
                        st.dataframe(ut_df.rename(columns={
                            "usage_type": "Usage Type",
                            "cost_amount": f"Day Cost ({currency})",
                            "baseline_daily_cost": f"Baseline Daily Cost ({currency})",
                            "increase": f"Absolute Surge ({currency})"
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.caption("No usage type breakdown available.")

                with rc_tab2:
                    if "regions" in finding.breakdown_tables:
                        reg_df = finding.breakdown_tables["regions"]
                        st.dataframe(reg_df.rename(columns={
                            "region": "AWS Region",
                            "cost_amount": f"Day Cost ({currency})",
                            "baseline_daily_cost": f"Baseline Daily Cost ({currency})",
                            "increase": f"Absolute Surge ({currency})"
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Regional breakdown is uniform or unpopulated.")

                with rc_tab3:
                    if "resources" in finding.breakdown_tables:
                        res_df = finding.breakdown_tables["resources"]
                        st.dataframe(res_df.rename(columns={
                            "resource_id": "Resource ID",
                            "cost_amount": f"Day Cost ({currency})"
                        }), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Resource identifiers (ARN / ResourceId) are absent in this dataset.")

            if finding.data_limitations:
                st.caption(f"⚠️ **Accounting Disclosures & Data Limitations:** {'; '.join(finding.data_limitations)}")
