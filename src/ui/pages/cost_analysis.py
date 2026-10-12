"""In-depth cost analysis page with multi-dimensional filtering."""
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.cost_engine import CostEngine
from src.config import PALETTE
from src.ui.components import render_metric_card


def render_cost_analysis_page(
    records_df: pd.DataFrame,
    dataset_info: Dict[str, Any]
) -> None:
    """Renders multi-dimensional cost exploration with dynamic interactive filters."""
    st.markdown("### Cost Analysis & Dimension Breakdown")
    currency = dataset_info.get("currency", "USD")

    if records_df.empty:
        st.warning("No records available in dataset.")
        return

    # ---------------------------------------------------------
    # 1. Interactive Filters Bar
    # ---------------------------------------------------------
    with st.expander("🔍 Filter Controls", expanded=True):
        f_col1, f_col2, f_col3 = st.columns(3)

        with f_col1:
            all_services = sorted(list(records_df["service"].unique()))
            selected_services = st.multiselect(
                "Filter by AWS Service",
                options=all_services,
                default=[]
            )

        with f_col2:
            all_regions = sorted(list(records_df["region"].dropna().unique()))
            selected_regions = st.multiselect(
                "Filter by Region",
                options=all_regions,
                default=[]
            )

        with f_col3:
            resource_query = st.text_input("Search Resource ID", placeholder="e.g. i-0a1b or bucket-corp")

        date_col1, date_col2 = st.columns(2)
        min_date = str(records_df["usage_date"].min())
        max_date = str(records_df["usage_date"].max())

        with date_col1:
            start_date_val = st.date_input("Start Date", value=pd.to_datetime(min_date).date())
        with date_col2:
            end_date_val = st.date_input("End Date", value=pd.to_datetime(max_date).date())

    # Apply filters
    filtered_df = records_df.copy()
    filtered_df["usage_date_dt"] = pd.to_datetime(filtered_df["usage_date"]).dt.date

    filtered_df = filtered_df[
        (filtered_df["usage_date_dt"] >= start_date_val) &
        (filtered_df["usage_date_dt"] <= end_date_val)
    ]

    if selected_services:
        filtered_df = filtered_df[filtered_df["service"].isin(selected_services)]
    if selected_regions:
        filtered_df = filtered_df[filtered_df["region"].isin(selected_regions)]
    if resource_query.strip():
        filtered_df = filtered_df[
            filtered_df["resource_id"].astype(str).str.contains(resource_query.strip(), case=False, na=False)
        ]

    # ---------------------------------------------------------
    # 2. Filtered Summary Metrics
    # ---------------------------------------------------------
    filtered_total = float(filtered_df["cost_amount"].sum()) if not filtered_df.empty else 0.0
    total_unfiltered = float(records_df["cost_amount"].sum())
    pct_of_total = (filtered_total / total_unfiltered * 100.0) if total_unfiltered > 0 else 0.0

    sm_col1, sm_col2, sm_col3 = st.columns(3)
    with sm_col1:
        render_metric_card(
            label="Filtered Total Spend",
            value=CostEngine.format_currency(filtered_total, currency),
            subtext=f"{pct_of_total:.1f}% of entire dataset"
        )
    with sm_col2:
        render_metric_card(
            label="Filtered Row Count",
            value=f"{len(filtered_df):,}",
            subtext=f"{len(records_df):,} total rows in dataset"
        )
    with sm_col3:
        distinct_svc_count = filtered_df["service"].nunique() if not filtered_df.empty else 0
        render_metric_card(
            label="Active Services",
            value=str(distinct_svc_count),
            subtext="Within current filter scope"
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    if filtered_df.empty:
        st.info("No records match the selected filter criteria. Adjust your filters above.")
        return

    # ---------------------------------------------------------
    # 3. Dimensional Breakdown Tabs
    # ---------------------------------------------------------
    tab_svc, tab_reg, tab_ut, tab_res, tab_conc = st.tabs([
        "By Service", "By Region", "By Usage Type", "By Resource ID", "Spend Concentration"
    ])

    with tab_svc:
        st.markdown("##### Service Expenditure Breakdown")
        svc_table = CostEngine.get_cost_by_service(filtered_df)
        svc_table["cost_formatted"] = svc_table["cost_amount"].apply(lambda c: CostEngine.format_currency(c, currency))
        svc_table["pct_formatted"] = svc_table["percentage"].apply(lambda p: f"{p:.2f}%")

        display_svc = svc_table[["service", "cost_formatted", "pct_formatted"]].rename(columns={
            "service": "AWS Service",
            "cost_formatted": f"Total Cost ({currency})",
            "pct_formatted": "% of Filtered Spend"
        })
        st.dataframe(display_svc, use_container_width=True, hide_index=True)

    with tab_reg:
        st.markdown("##### Geographic Regional Breakdown")
        reg_table = CostEngine.get_cost_by_region(filtered_df)
        reg_table["cost_formatted"] = reg_table["cost_amount"].apply(lambda c: CostEngine.format_currency(c, currency))
        reg_table["pct_formatted"] = reg_table["percentage"].apply(lambda p: f"{p:.2f}%")

        display_reg = reg_table[["region", "cost_formatted", "pct_formatted"]].rename(columns={
            "region": "Region / Zone",
            "cost_formatted": f"Total Cost ({currency})",
            "pct_formatted": "% of Spend"
        })
        st.dataframe(display_reg, use_container_width=True, hide_index=True)

    with tab_ut:
        st.markdown("##### Usage Type Breakdown")
        svc_pick = st.selectbox("Select Service to Drill Into Usage Types", options=["All Services"] + sorted(list(filtered_df["service"].unique())))
        target_svc = None if svc_pick == "All Services" else svc_pick
        ut_table = CostEngine.get_cost_by_usage_type(filtered_df, service=target_svc, top_n=20)

        if not ut_table.empty:
            ut_table["cost_formatted"] = ut_table["cost_amount"].apply(lambda c: CostEngine.format_currency(c, currency))
            ut_table["pct_formatted"] = ut_table["percentage"].apply(lambda p: f"{p:.2f}%")
            display_ut = ut_table[["usage_type", "cost_formatted", "pct_formatted"]].rename(columns={
                "usage_type": "Usage Type / API Operation",
                "cost_formatted": f"Total Cost ({currency})",
                "pct_formatted": "% of Service Spend"
            })
            st.dataframe(display_ut, use_container_width=True, hide_index=True)
        else:
            st.info("No usage type entries available for this selection.")

    with tab_res:
        st.markdown("##### Resource-Level Spend")
        has_res = "resource_id" in filtered_df.columns and filtered_df["resource_id"].dropna().str.len().sum() > 0
        if has_res:
            res_table = CostEngine.get_cost_by_resource(filtered_df, top_n=25)
            if not res_table.empty:
                res_table["cost_formatted"] = res_table["cost_amount"].apply(lambda c: CostEngine.format_currency(c, currency))
                res_table["pct_formatted"] = res_table["percentage"].apply(lambda p: f"{p:.2f}%")
                display_res = res_table[["resource_id", "service", "cost_formatted", "pct_formatted"]].rename(columns={
                    "resource_id": "Resource Identifier",
                    "service": "Service",
                    "cost_formatted": f"Cost ({currency})",
                    "pct_formatted": "% of Total"
                })
                st.dataframe(display_res, use_container_width=True, hide_index=True)
            else:
                st.info("No resource identifiers found in the filtered records.")
        else:
            st.info("ℹ️ Resource IDs (Resource ARN/Id) are not present in this billing export format. To inspect resource-level costs, enable 'Resource IDs' in AWS CUR / Cost Explorer settings.")

    with tab_conc:
        st.markdown("##### Spend Concentration Analysis")
        conc = CostEngine.get_cost_concentration(filtered_df)

        c_col1, c_col2, c_col3 = st.columns(3)
        with c_col1:
            render_metric_card("Top 3 Services Share", f"{conc['top3_pct']}%", subtext="Percentage of total bill")
        with c_col2:
            render_metric_card("Herfindahl Index (HHI)", f"{conc['hhi']:,.0f}", subtext="Market concentration standard")
        with c_col3:
            render_metric_card("Concentration Status", conc["tier"], subtext="Cost concentration profile")

        st.caption(
            "Economic Reference: Herfindahl-Hirschman Index (HHI) measures portfolio diversification. "
            "Scores > 2,500 indicate high concentration where budget risk is heavily tied to 1-2 cloud services."
        )
