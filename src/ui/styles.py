"""Enterprise dark navy CSS styling and theme definitions for CloudGuard AI."""
import streamlit as st

CUSTOM_CSS = """
<style>
/* Main container spacing and font */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* Header reduction */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2.0rem !important;
    max-width: 1400px;
}

/* Metric card styling */
.cg-metric-card {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.cg-metric-label {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94A3B8;
    margin-bottom: 0.35rem;
}

.cg-metric-value {
    font-size: 1.65rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.2;
}

.cg-metric-subtext {
    font-size: 0.82rem;
    margin-top: 0.4rem;
    font-weight: 500;
}

.cg-subtext-favorable {
    color: #22C55E;
}

.cg-subtext-unfavorable {
    color: #EF4444;
}

.cg-subtext-neutral {
    color: #94A3B8;
}

/* Alert card styling */
.cg-alert-card {
    background-color: #1E293B;
    border-left: 4px solid #EF4444;
    border-top: 1px solid #334155;
    border-right: 1px solid #334155;
    border-bottom: 1px solid #334155;
    border-radius: 0 8px 8px 0;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
}

.cg-alert-card.neutral {
    border-left-color: #38BDF8;
}

.cg-alert-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #F8FAFC;
    margin-bottom: 0.25rem;
}

.cg-alert-meta {
    font-size: 0.8rem;
    color: #94A3B8;
    margin-bottom: 0.4rem;
}

.cg-alert-reason {
    font-size: 0.85rem;
    color: #CBD5E1;
    line-height: 1.4;
}

.cg-badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-left: 0.5rem;
}

.cg-badge-confirmed {
    background-color: rgba(239, 68, 68, 0.2);
    color: #FCA5A5;
    border: 1px solid rgba(239, 68, 68, 0.4);
}

.cg-badge-inferred {
    background-color: rgba(245, 158, 11, 0.2);
    color: #FCD34D;
    border: 1px solid rgba(245, 158, 11, 0.4);
}

.cg-badge-neutral {
    background-color: rgba(148, 163, 184, 0.2);
    color: #E2E8F0;
    border: 1px solid rgba(148, 163, 184, 0.4);
}

/* Clean sidebar styling */
[data-testid="stSidebar"] {
    background-color: #0B1120;
    border-right: 1px solid #1E293B;
}

/* Compact button styling */
.stButton button {
    border-radius: 6px;
    font-weight: 500;
}
</style>
"""


def apply_custom_styles() -> None:
    """Injects custom CSS into the Streamlit session."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
