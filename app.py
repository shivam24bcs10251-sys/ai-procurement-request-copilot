from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.solution import handle_request


ROOT = Path(__file__).resolve().parent
REQUESTS = json.loads((ROOT / "data" / "requests.json").read_text(encoding="utf-8"))
BY_ID = {request["request_id"]: request for request in REQUESTS}

st.set_page_config(page_title="Procurement Copilot", page_icon="✓", layout="wide")
st.markdown(
    """
    <style>
      .block-container {max-width: 1180px; padding-top: 4rem;}
      [data-testid="stMetric"] {background: var(--secondary-background-color); color: var(--text-color); border: 1px solid #80808055; padding: 12px; border-radius: 10px;}
      .eyebrow {color: #0b9b83; font-weight: 700; letter-spacing: .08em; font-size: .8rem;}
      .notice {background: #effaf7; color: #134e43; border-left: 4px solid #0b9b83; padding: 12px 16px; border-radius: 4px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="eyebrow">INTERNAL PROCUREMENT</div>', unsafe_allow_html=True)
st.title("AI Procurement Request Copilot")
st.caption("Grounded recommendations for faster review. Final authority remains with human approvers.")

with st.sidebar:
    st.header("Analysis settings")
    request_id = st.selectbox(
        "Purchase request",
        list(BY_ID),
        format_func=lambda rid: f"{rid} · {BY_ID[rid]['product_name']}",
    )
    architecture = st.radio(
        "Architecture",
        ["single", "staged"],
        format_func=lambda value: "Single agent" if value == "single" else "Staged reviewer",
    )
    run = st.button("Analyze request", type="primary", use_container_width=True)
    st.divider()
    st.caption("Policy version 2026.09")
    st.caption("Evidence reference date: 30 Sep 2026")

request = BY_ID[request_id]
st.subheader("Request overview")
metrics = st.columns(4)
metrics[0].metric("Request", request_id)
metrics[1].metric(
    "Annual cost",
    "Missing" if request["annual_cost_usd"] is None else f"${request['annual_cost_usd']:,.0f}",
)
metrics[2].metric("Users", request["user_count"] or "Missing")
metrics[3].metric("Urgency", str(request["urgency"]).title())

with st.expander("View submitted request", expanded=False):
    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.write(f"**Product:** {request['product_name']}")
        st.write(f"**Vendor:** {request['vendor_name']}")
        st.write(f"**Category:** {request['category']}")
        st.write(f"**Requester ID:** {request['requester_id']}")
    with detail_right:
        st.write(f"**Data access:** {request['data_access_level']}")
        st.write(f"**Integrations:** {', '.join(request['requested_integrations']) or 'None declared'}")
        st.write(f"**Business purpose:** {request['business_justification']}")

if not run:
    st.markdown(
        '<div class="notice">Choose a request and run the analysis to gather current evidence and prepare a human review package.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

try:
    decision = handle_request(request_id, architecture=architecture)
except Exception as exc:
    st.error("The request could not be analyzed. No approval recommendation was produced.")
    st.exception(exc)
    st.stop()

st.divider()
status_col, approval_col = st.columns([1.3, 0.7])
with status_col:
    st.subheader("Recommendation")
    st.info(decision.recommendation)
    st.write(decision.next_step)
with approval_col:
    st.subheader("Human control")
    st.error("Human review required" if decision.human_review_required else "No human review recorded")
    st.caption("The copilot cannot approve spend, purchase software, or override control functions.")

evidence_tab, controls_tab, telemetry_tab = st.tabs(["Evidence", "Approvals & risks", "Run details"])
with evidence_tab:
    st.subheader(f"Evidence gathered · {len(decision.evidence)} items")
    for item in decision.evidence:
        with st.container(border=True):
            st.markdown(f"**{item.source.replace('_', ' ').title()}**")
            st.write(item.finding)
            if item.reference:
                st.caption(f"Reference: {item.reference}")

with controls_tab:
    approvals_col, risk_col, missing_col = st.columns(3)
    with approvals_col:
        st.markdown("#### Required approvals")
        if decision.required_approvals:
            for approval in decision.required_approvals:
                st.write(f"✓ {approval}")
        else:
            st.write("Pending complete request data")
    with risk_col:
        st.markdown("#### Risk flags")
        if decision.risk_flags:
            for flag in decision.risk_flags:
                st.write(f"• {flag}")
        else:
            st.write("No policy risk flags found")
    with missing_col:
        st.markdown("#### Missing information")
        if decision.missing_information:
            for item in decision.missing_information:
                st.write(f"• {item}")
        else:
            st.write("Request fields are complete")

with telemetry_tab:
    telemetry = decision.telemetry
    run_cols = st.columns(3)
    run_cols[0].metric("Architecture", "Single" if architecture == "single" else "Staged")
    run_cols[1].metric("Tool calls", telemetry.tool_calls if telemetry else "Not recorded")
    run_cols[2].metric("LLM calls", telemetry.llm_calls if telemetry else "Not recorded")
    if telemetry:
        st.write("**Tools called:** " + " → ".join(telemetry.tool_names))
    if not telemetry or telemetry.llm_calls == 0:
        st.caption("This run used the deterministic safety fallback; no successful model call was recorded.")
