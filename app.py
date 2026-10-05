from __future__ import annotations

from html import escape
import json
from pathlib import Path

import streamlit as st

from src.solution import handle_request

ROOT = Path(__file__).resolve().parent
REQUESTS = json.loads((ROOT / "data" / "requests.json").read_text(encoding="utf-8"))
BY_ID = {request["request_id"]: request for request in REQUESTS}


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def safe(value: object) -> str:
    return escape(str(value))


def readable(value: object) -> str:
    text = str(value).replace("_", " ")
    return text[:1].upper() + text[1:]


def control_card(title: str, items: list[str], empty: str, tone: str) -> None:
    rows = "".join(f'<li>{safe(readable(item))}</li>' for item in items)
    body = f'<ul class="control-list">{rows}</ul>' if rows else f'<p class="muted">{safe(empty)}</p>'
    html(f'<div class="control-card {tone}"><div class="card-label">{safe(title)}</div>{body}</div>')


st.set_page_config(page_title="Procurement Copilot", page_icon="◈", layout="wide")
html("""
<style>
  .block-container {max-width: 1240px; padding-top: 3.8rem; padding-bottom: 3rem;}
  [data-testid="stSidebar"] {border-right: 1px solid #80808025;}
  [data-testid="stSidebar"] .block-container {padding-top: 2rem;}
  h1, h2, h3 {letter-spacing: -.035em;}
  h3 {font-size: 1.25rem !important;}
  .brand {display: flex; align-items: center; gap: 12px; margin-bottom: 28px;}
  .brand-icon {display: grid; place-items: center; width: 42px; height: 42px; border-radius: 12px; background: #163f40; color: #9de4c9; font-size: 25px;}
  .brand-name {font-weight: 700; font-size: 17px; letter-spacing: -.025em;}
  .brand-sub {font-size: 11px; opacity: .6; letter-spacing: .12em; text-transform: uppercase; margin-top: 3px;}
  .section-label, .card-label {font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; opacity: .65; margin-bottom: 12px;}
  .sidebar-note {font-size: 13px; line-height: 1.7; opacity: .65;}
  .hero {background: linear-gradient(115deg, #142b35, #164a46); border: 1px solid #35615d; border-radius: 20px; padding: 32px 36px; color: #fff; margin-bottom: 26px; position: relative; overflow: hidden;}
  .hero:after {content: '◈'; position: absolute; right: 30px; top: -48px; font-size: 220px; color: #a3ead1; opacity: .07; pointer-events: none;}
  .hero-kicker {font-size: 11px; font-weight: 700; letter-spacing: .16em; color: #a3ead1; text-transform: uppercase;}
  .hero h1 {color: #fff; font-size: clamp(28px, 3.4vw, 42px); line-height: 1.15; margin: 12px 0; padding: 0; max-width: 750px;}
  .hero p {color: #c6dcd8; font-size: 15px; line-height: 1.7; margin: 0; max-width: 680px;}
  .hero-footer {display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px;}
  .hero-pill {border: 1px solid #ffffff30; background: #ffffff08; color: #d8eae5; padding: 5px 11px; border-radius: 100px; font-size: 11px;}
  .request-heading {display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; margin: 8px 0 18px;}
  .request-heading h2 {font-size: 24px; padding: 0; margin: 4px 0 0;}
  .request-id {font-size: 12px; opacity: .6;}
  .badge {display: inline-block; background: #80808012; border: 1px solid #80808030; padding: 6px 12px; border-radius: 100px; font-size: 12px;}
  [data-testid="stMetric"] {background: var(--secondary-background-color); color: var(--text-color); border: 1px solid #80808025; padding: 18px 20px; border-radius: 14px;}
  [data-testid="stMetricLabel"] {opacity: .65; font-size: 12px;}
  [data-testid="stMetricValue"] {font-size: 26px; font-weight: 600; letter-spacing: -.03em;}
  [data-testid="stExpander"] {border-radius: 14px; border-color: #80808030;}
  [data-testid="stBaseButton-primary"] {background: #16745d; border-color: #16745d; border-radius: 10px; font-weight: 600; min-height: 44px;}
  [data-testid="stBaseButton-primary"]:hover {background: #125d4b; border-color: #125d4b;}
  .detail-grid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 8px 0 20px;}
  .detail-label {font-size: 11px; opacity: .6; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 5px;}
  .detail-value {font-size: 14px; line-height: 1.6; overflow-wrap: anywhere;}
  .purpose {background: var(--secondary-background-color); color: var(--text-color); border-radius: 10px; padding: 16px 20px;}
  .purpose p {margin: 0; font-size: 14px; line-height: 1.7;}
  .empty-state {border: 1px dashed #80808045; border-radius: 18px; padding: 34px; text-align: center; margin-top: 16px;}
  .empty-icon {color: #269879; font-size: 32px; margin-bottom: 8px;}
  .empty-state h3 {margin: 0 0 8px; padding: 0;}
  .muted {opacity: .65; font-size: 14px; line-height: 1.7;}
  .steps {display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; margin-top: 22px; font-size: 12px; opacity: .65;}
  .step-number {display: inline-grid; place-items: center; width: 22px; height: 22px; border: 1px solid #80808050; border-radius: 50%; margin-right: 7px; font-size: 10px;}
  .decision {border: 1px solid #26987965; border-left: 4px solid #269879; border-radius: 14px; padding: 22px 26px; margin: 18px 0; background: var(--secondary-background-color); color: var(--text-color);}
  .decision h3 {margin: 5px 0 10px; padding: 0; font-size: 22px !important;}
  .decision p {margin: 0; line-height: 1.7; font-size: 14px;}
  .human-note {display: flex; align-items: center; gap: 10px; margin: 14px 0 22px; font-size: 13px;}
  .human-dot {width: 8px; height: 8px; border-radius: 50%; background: #d99b35; flex-shrink: 0;}
  .evidence-card {border: 1px solid #80808025; border-radius: 12px; padding: 18px 22px; margin-bottom: 12px;}
  .evidence-top {display: flex; align-items: center; gap: 12px; margin-bottom: 9px;}
  .evidence-index {font-size: 11px; opacity: .5; font-variant-numeric: tabular-nums;}
  .evidence-title {font-size: 13px; font-weight: 600;}
  .evidence-card p {font-size: 14px; line-height: 1.7; margin: 0; overflow-wrap: anywhere;}
  .evidence-ref {font-size: 11px; opacity: .6; margin-top: 10px; overflow-wrap: anywhere;}
  .control-card {border: 1px solid #80808025; border-top: 3px solid #269879; border-radius: 12px; padding: 20px; height: 100%;}
  .control-card.amber {border-top-color: #d99b35;}
  .control-card.blue {border-top-color: #679acc;}
  .control-list {padding-left: 18px; margin: 0; font-size: 14px; line-height: 2;}
  .footer {border-top: 1px solid #80808025; margin-top: 32px; padding-top: 16px; font-size: 11px; opacity: .55;}
  @media (max-width: 700px) {.hero {padding: 25px;} .detail-grid {grid-template-columns: 1fr 1fr;} .steps {gap: 12px;} .block-container {padding-top: 3rem;}}
</style>
""")

with st.sidebar:
    html('<div class="brand"><div class="brand-icon">◈</div><div><div class="brand-name">Procurement Copilot</div><div class="brand-sub">Review workspace</div></div></div>')
    html('<div class="section-label">01 / Select a request</div>')
    request_id = st.selectbox("Purchase request", list(BY_ID), format_func=lambda rid: f"{rid} · {BY_ID[rid]['product_name']}")
    st.divider()
    html('<div class="section-label">02 / Choose analysis</div>')
    architecture = st.radio("Architecture", ["single", "staged"], format_func=lambda value: "Single agent" if value == "single" else "Staged reviewer")
    st.caption("One evidence pass" if architecture == "single" else "Evidence pass + separate policy review")
    run = st.button("Analyze request →", type="primary", use_container_width=True)
    st.divider()
    html('<div class="section-label">Human authority, always</div><p class="sidebar-note">Every recommendation goes to the required human reviewers. The copilot never approves spending.</p>')
    st.caption("Policy version 2026.09 · USD")
    st.caption("Evidence snapshot: 30 Sep 2026")

html('<div class="hero"><div class="hero-kicker">AI Procurement Request Copilot</div><h1>A clearer path from request<br>to human review.</h1><p>Bring the evidence, policy checks, and next action together in one procurement review workspace.</p><div class="hero-footer"><span class="hero-pill">Source-referenced evidence</span><span class="hero-pill">Deterministic policy checks</span><span class="hero-pill">Human approval required</span></div></div>')

request = BY_ID[request_id]
html(f'<div class="request-heading"><div><div class="request-id">REQUEST / {safe(request_id)}</div><h2>{safe(request["product_name"])}</h2></div><span class="badge">{safe(request["category"])}</span></div>')
metrics = st.columns(4)
metrics[0].metric("Annual investment", "Missing" if request["annual_cost_usd"] is None else f"${request['annual_cost_usd']:,.0f}")
metrics[1].metric("Requested users", request["user_count"] or "Missing")
metrics[2].metric("Priority", str(request["urgency"]).title())
metrics[3].metric("Vendor", request["vendor_name"])

st.write("")
with st.expander("Request details & business purpose", expanded=True):
    fields = [("Requester", request["requester_id"]), ("Data access", readable(request["data_access_level"])), ("Integrations", ", ".join(request["requested_integrations"]) or "None declared")]
    html('<div class="detail-grid">' + "".join(f'<div><div class="detail-label">{safe(label)}</div><div class="detail-value">{safe(value)}</div></div>' for label, value in fields) + '</div>')
    html(f'<div class="purpose"><div class="detail-label">Business purpose</div><p>{safe(request["business_justification"])}</p></div>')

# Keep a completed review visible across tab clicks and other Streamlit reruns.
# A different request or architecture gets its own result, avoiding stale reviews.
review_key = (request_id, architecture)
if run:
    try:
        with st.spinner("Gathering evidence and checking procurement policy…"):
            st.session_state["review"] = (review_key, handle_request(request_id, architecture=architecture))
    except Exception:
        st.session_state.pop("review", None)
        st.error("Analysis could not be completed. Please check the local services and try again.")

saved_review = st.session_state.get("review")
if not saved_review or saved_review[0] != review_key:
    html('<div class="empty-state"><div class="empty-icon">◈</div><h3>Your review starts here</h3><div class="muted">Select an analysis in the sidebar, then click <strong>Analyze request</strong><br>to prepare a grounded recommendation and human handoff.</div><div class="steps"><span><span class="step-number">1</span>Gather evidence</span><span><span class="step-number">2</span>Check policy</span><span><span class="step-number">3</span>Prepare human review</span></div></div>')
else:
    decision = saved_review[1]
    html(f'<div class="decision"><div class="card-label">Recommended next action</div><h3>{safe(decision.recommendation)}</h3><p>{safe(decision.next_step)}</p></div>')
    html('<div class="human-note"><span class="human-dot"></span><span><strong>Human review required.</strong> Final decisions remain with the named approval owners.</span></div>')
    evidence_tab, controls_tab, telemetry_tab = st.tabs([f"Evidence · {len(decision.evidence)}", "Approvals & risks", "Run details"])
    with evidence_tab:
        st.write("")
        st.caption("Review the source behind each finding before moving the request forward.")
        for index, item in enumerate(decision.evidence, start=1):
            reference = f'<div class="evidence-ref">SOURCE / {safe(item.reference)}</div>' if item.reference else ""
            html(f'<div class="evidence-card"><div class="evidence-top"><span class="evidence-index">{index:02d}</span><span class="evidence-title">{safe(readable(item.source))}</span></div><p>{safe(item.finding)}</p>{reference}</div>')
    with controls_tab:
        st.write("")
        columns = st.columns(3)
        with columns[0]:
            control_card("Required approvals", decision.required_approvals, "Pending complete request data", "green")
        with columns[1]:
            control_card("Risk flags", decision.risk_flags, "No policy risk flags found", "amber")
        with columns[2]:
            control_card("Missing information", decision.missing_information, "Request fields are complete", "blue")
    with telemetry_tab:
        st.write("")
        telemetry = decision.telemetry
        columns = st.columns(3)
        columns[0].metric("Architecture", "Single" if architecture == "single" else "Staged")
        columns[1].metric("Tool calls", telemetry.tool_calls if telemetry else "Not recorded")
        columns[2].metric("LLM calls", telemetry.llm_calls if telemetry else "Not recorded")
        if telemetry:
            with st.expander("View execution sequence"):
                for index, tool in enumerate(telemetry.tool_names, 1):
                    st.text(f"{index:02d}  {tool}")
        if not telemetry or telemetry.llm_calls == 0:
            st.caption("This run used the deterministic safety fallback; no successful model call was recorded.")
    st.write("")
    st.download_button("Download review package", data=decision.model_dump_json(indent=2), file_name=f"{request_id}_{architecture}_review.json", mime="application/json")

html('<div class="footer">PROCUREMENT COPILOT · Evidence snapshot 30 Sep 2026 · Recommendations are advisory; approval authority remains with humans.</div>')
