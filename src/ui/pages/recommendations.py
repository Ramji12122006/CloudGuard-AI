"""Cost optimization recommendations management page."""
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.analytics.recommender import RecommendationEngine
from src.analytics.cost_engine import CostEngine
from src.config import REC_STATUS_OPTIONS, REC_STATUS_OPEN
from src.ui.components import render_metric_card


def render_recommendations_page(
    records_df: pd.DataFrame,
    dataset_info: Dict[str, Any],
    db_manager: Any
) -> None:
    """Renders rule-based cost recommendations with status workflow management."""
    st.markdown("### Cost Optimization Recommendations")
    dataset_id = dataset_info["id"]
    currency = dataset_info.get("currency", "USD")

    # ---------------------------------------------------------
    # 1. Fetch or Generate Recommendations
    # ---------------------------------------------------------
    db_recs = db_manager.get_recommendations(dataset_id)
    if not db_recs:
        generated = RecommendationEngine.generate_recommendations(records_df)
        if generated:
            db_manager.save_recommendations(dataset_id, [r.to_dict() for r in generated])
            db_recs = db_manager.get_recommendations(dataset_id)

    # Status filter
    filter_col, _ = st.columns([2, 5])
    with filter_col:
        status_sel = st.selectbox("Status Filter", options=["All"] + REC_STATUS_OPTIONS, index=0)

    filtered_recs = db_recs
    if status_sel != "All":
        filtered_recs = [r for r in db_recs if r.get("status") == status_sel]

    # Metrics
    total_recs = len(db_recs)
    open_recs = sum(1 for r in db_recs if r.get("status") == REC_STATUS_OPEN)
    total_est_savings = sum(r["estimated_savings"] for r in db_recs if r.get("estimated_savings"))

    m1, m2, m3 = st.columns(3)
    with m1:
        render_metric_card("Total Recommendations", str(total_recs), subtext="Generated from billing rules")
    with m2:
        render_metric_card("Open Recommendations", str(open_recs), subtext="Awaiting review", is_favorable=False if open_recs > 0 else True)
    with m3:
        render_metric_card("Potential Estimated Benefit", CostEngine.format_currency(total_est_savings, currency), subtext="Estimated pending architecture review", is_favorable=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    if not filtered_recs:
        st.info("No recommendations match the current status filter. Your cloud architecture adheres to current baseline rules.")
        return

    # ---------------------------------------------------------
    # 2. Recommendations List
    # ---------------------------------------------------------
    for rec in filtered_recs:
        rid = rec["id"]
        status = rec.get("status", REC_STATUS_OPEN)
        title = rec["title"]
        category = rec["category"]
        service = rec["service"]
        evidence = rec["supporting_evidence"]
        action = rec["suggested_action"]
        savings = rec.get("estimated_savings")
        limitations = rec.get("limitations", "")

        savings_badge = f"+${savings:,.2f}/period est." if savings else "Subject to workload review"

        with st.expander(f"💡 [{category}] {title} — {savings_badge} [{status}]", expanded=(status == REC_STATUS_OPEN)):
            card_col1, card_col2 = st.columns([3, 1])

            with card_col1:
                st.markdown(f"**Target Service:** `{service}` &bull; **Category:** `{category}`")
                st.markdown(f"**Supporting Evidence:**\n> {evidence}")
                st.markdown(f"**Suggested Next Action:**\n> {action}")

                if savings:
                    st.markdown(f"**Estimated Benefit:** **${savings:,.2f}** (Subject to workload commitments)")
                else:
                    st.markdown("**Estimated Benefit:** Dependent on operational utilization analysis.")

                if limitations:
                    st.caption(f"⚠️ **Important Caveats & Limitations:** {limitations}")

            with card_col2:
                current_idx = REC_STATUS_OPTIONS.index(status) if status in REC_STATUS_OPTIONS else 0
                new_status = st.selectbox(
                    "Workflow Status",
                    options=REC_STATUS_OPTIONS,
                    index=current_idx,
                    key=f"rec_status_{rid}"
                )
                if new_status != status:
                    db_manager.update_recommendation_status(rid, new_status)
                    st.success(f"Updated status to {new_status}")
                    st.rerun()
