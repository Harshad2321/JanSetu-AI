"""
JanSetu AI — Adaptive Civic Incident Resolution
Streamlit Companion Interface (CA-3 Compliance Deliverable).

Acts strictly as a client to the FastAPI backend service.
Does not replicate or duplicate agent orchestration, LLM calls,
priority algorithms, or simulation state machines.
"""

import io
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

for p in (str(ROOT_DIR), str(APP_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st
from PIL import Image

try:
    from streamlit_app.api_client import (
        BackendAPIError,
        BackendConnectionError,
        JanSetuAPIClient,
    )
    from streamlit_app.config import API_BASE_URL
except ImportError:
    from api_client import (
        BackendAPIError,
        BackendConnectionError,
        JanSetuAPIClient,
    )
    from config import API_BASE_URL

# Page setup
st.set_page_config(
    page_title="JanSetu AI — Incident Operations",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom civic command center styling
st.markdown(
    """
    <style>
    .main { background-color: #0b0f19; }
    .stMetric {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px;
    }
    .status-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 11px;
        font-weight: bold;
    }
    .badge-sim {
        background-color: #064e3b;
        color: #34d399;
        border: 1px solid #059669;
    }
    .badge-warn {
        background-color: #78350f;
        color: #fbbf24;
        border: 1px solid #d97706;
    }
    .badge-blocked {
        background-color: #4c0519;
        color: #fb7185;
        border: 1px solid #e11d48;
    }
    .agent-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_client() -> JanSetuAPIClient:
    return JanSetuAPIClient(base_url=API_BASE_URL)


client = get_client()


# ============================================================================
# Sidebar: Navigation & Diagnostics
# ============================================================================

st.sidebar.markdown("### 🏛️ JANSETU AI")
st.sidebar.caption("Adaptive Civic Incident Resolution (Streamlit PoC)")
st.sidebar.markdown("---")

# Health check
backend_live = False
health_data = {}
try:
    health_data = client.get_health()
    backend_live = True
    st.sidebar.success(f"● Backend Live (`{health_data.get('environment', 'dev')}`)")
except BackendConnectionError:
    st.sidebar.error("○ Backend Offline")
    st.sidebar.warning(
        f"Cannot connect to FastAPI at `{API_BASE_URL}`.\n\n"
        "Run `uvicorn app.main:app --port 8000` in the backend directory."
    )

# Demonstration Seeder
if backend_live:
    if st.sidebar.button("🔄 Seed Demonstration Data", use_container_width=True):
        try:
            seed_res = client.seed_demonstration_data()
            st.sidebar.success(seed_res.get("message", "Demonstration cases seeded!"))
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Seed failed: {str(e)}")

st.sidebar.markdown("---")
nav_choice = st.sidebar.radio(
    "Navigation",
    [
        "📊 Operations Dashboard",
        "📝 Citizen Incident Intake",
        "🤖 Multi-Agent Execution",
        "🧪 Failure Simulation Lab",
        "🔍 Audit & Provenance Timeline",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Demonstration Disclaimer:** All field dispatches, contractor allocations, "
    "and completion records are deterministic simulations. No real crews are dispatched."
)


# ============================================================================
# Helper: Format Badges
# ============================================================================

def format_op_badge(status: str) -> str:
    color_map = {
        "SIMULATED_RESOLVED": "badge-sim",
        "RECORDED_PENDING_REVIEW": "badge-warn",
        "AWAITING_CLARIFICATION": "badge-warn",
        "AWAITING_HUMAN_REVIEW": "badge-warn",
        "CLOSURE_BLOCKED": "badge-blocked",
        "ESCALATED": "badge-blocked",
    }
    css_class = color_map.get(status, "badge-warn")
    return f'<span class="status-badge {css_class}">{status}</span>'


def format_evidence_badge(outcome: str) -> str:
    color_map = {
        "MATCHED": "badge-sim",
        "MISMATCH": "badge-blocked",
        "LOW_QUALITY": "badge-warn",
        "INCONCLUSIVE": "badge-warn",
        "NOT_PROVIDED": "badge-warn",
    }
    css_class = color_map.get(outcome, "badge-warn")
    return f'<span class="status-badge {css_class}">{outcome}</span>'


# ============================================================================
# Screen 1: Operations Dashboard
# ============================================================================

if nav_choice == "📊 Operations Dashboard":
    st.title("Civic Operations Command Dashboard")
    st.caption("Live incident aggregation from municipal persistence engine")

    if not backend_live:
        st.error("FastAPI Backend is currently unreachable. Please start the backend service.")
        st.stop()

    try:
        summary = client.get_dashboard_summary()
        incidents_data = client.get_incidents(limit=100)
        items = incidents_data.get("items", [])
    except Exception as e:
        st.error(f"Failed to fetch dashboard data: {str(e)}")
        st.stop()

    # Metric summary row
    col1, col2, col3, col4, col5 = st.columns(5)
    total_inc = summary.get("total_incidents", 0)
    op_statuses = summary.get("operational_statuses", {})
    prio_bands = summary.get("priority_bands", {})
    ev_statuses = summary.get("evidence_statuses", {})

    col1.metric("Total Recorded", total_inc)
    pending_count = (
        op_statuses.get("RECORDED_PENDING_REVIEW", 0)
        + op_statuses.get("AWAITING_CLARIFICATION", 0)
        + op_statuses.get("AWAITING_HUMAN_REVIEW", 0)
        + op_statuses.get("NEW", 0)
    )
    col2.metric("Active / Pending", pending_count)
    col3.metric("High / Critical Priority", prio_bands.get("Critical", 0) + prio_bands.get("High", 0))
    col4.metric("Photos Matched", ev_statuses.get("MATCHED", 0))
    col5.metric("Simulated Resolved", op_statuses.get("SIMULATED_RESOLVED", 0))

    st.markdown("---")

    # Layout: Analytics & Incident Roster
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("Category Distribution")
        cat_counts = summary.get("categories", {})
        if cat_counts:
            st.bar_chart(cat_counts)
        else:
            st.info("No categorical data available.")

    with right_col:
        st.subheader("Priority Distribution")
        if prio_bands:
            st.bar_chart(prio_bands)
        else:
            st.info("No priority data available.")

    st.subheader("Recent Municipal Incidents")
    if not items:
        st.info("No incidents found in registry. Click 'Seed Demonstration Data' in sidebar to populate.")
    else:
        # Table view
        table_rows = []
        for inc in items:
            loc = inc.get("location") or {}
            table_rows.append({
                "ID": inc.get("incident_id"),
                "Category": inc.get("category"),
                "Complaint": inc.get("complaint", "")[:60] + ("..." if len(inc.get("complaint", "")) > 60 else ""),
                "Operational Status": inc.get("operational_status"),
                "Evidence Status": inc.get("evidence_status"),
                "Priority Score": (inc.get("priority") or {}).get("priority_score", "—"),
                "Latitude": loc.get("latitude") or "—",
                "Longitude": loc.get("longitude") or "—",
            })
        st.dataframe(table_rows, use_container_width=True)


# ============================================================================
# Screen 2: Citizen Incident Intake
# ============================================================================

elif nav_choice == "📝 Citizen Incident Intake":
    st.title("Citizen Incident Reporting Intake")
    st.caption("Submit civic complaints with optional photographic evidence and GPS coordinates")

    if not backend_live:
        st.error("FastAPI Backend is currently unreachable.")
        st.stop()

    with st.form("citizen_intake_form"):
        col_cat, col_src = st.columns([1, 1])
        with col_cat:
            category = st.selectbox(
                "Incident Category",
                ["pothole", "waterlogging", "garbage", "uncertain_other"],
                format_func=lambda x: {
                    "pothole": "🕳️ Pothole & Road Crater",
                    "waterlogging": "🌊 Waterlogging & Drainage Blockage",
                    "garbage": "🗑️ Garbage & Waste Accumulation",
                    "uncertain_other": "❓ Uncertain / Other Hazard",
                }.get(x, x),
            )
        with col_src:
            loc_source = st.selectbox(
                "Location Source",
                ["MANUAL_ENTRY", "USER_PIN_ADJUSTED", "DEVICE_GPS"],
                help="Geolocation provenance source",
            )

        complaint_text = st.text_area(
            "Complaint Description *",
            placeholder="Describe the hazard in detail (minimum 10 characters)...",
            help="Provide specific clues regarding physical depth, road lane, or pedestrian hazards.",
        )

        st.markdown("**Public Exposure & Severity Indicators (Clues)**")
        c1, c2, c3, c4 = st.columns(4)
        c1.checkbox("Arterial Road / High Traffic")
        c2.checkbox("Skid Hazard for Two-Wheelers")
        c3.checkbox("Standing Water Depth > 15cm")
        c4.checkbox("Overflowing Waste Dump")

        col_lat, col_lon, col_acc = st.columns(3)
        with col_lat:
            latitude = st.number_input("Latitude", value=19.0760, format="%.6f", help="Mumbai default: 19.0760")
        with col_lon:
            longitude = st.number_input("Longitude", value=72.8777, format="%.6f", help="Mumbai default: 72.8777")
        with col_acc:
            accuracy = st.number_input("Accuracy (meters)", value=10.0, min_value=0.0, format="%.1f")

        st.markdown("**Photographic Evidence (Optional)**")
        st.info("Photographs help verify the report. A complaint without a photo remains recorded and scheduled for field review.")
        uploaded_file = st.file_uploader(
            "Upload Evidence Image (JPEG, PNG, WebP)",
            type=["jpg", "jpeg", "png", "webp"],
        )

        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()
            st.image(image_bytes, caption="Uploaded Photograph Preview", width=300)
        else:
            image_bytes = None

        submitted = st.form_submit_button("Submit Incident to JanSetu AI", use_container_width=True)

    if submitted:
        if len(complaint_text.strip()) < 10:
            st.error("Complaint description must be at least 10 characters long.")
        else:
            with st.spinner("Submitting incident and processing sanitization pipeline..."):
                try:
                    res = client.submit_incident(
                        complaint=complaint_text.strip(),
                        category=category,
                        latitude=latitude,
                        longitude=longitude,
                        accuracy_meters=accuracy,
                        location_source=loc_source,
                        is_user_confirmed=True,
                        image_bytes=image_bytes,
                        image_filename=uploaded_file.name if uploaded_file else None,
                    )
                    st.success(f"Incident Created Successfully: `{res.get('incident_id')}`")

                    # Display returned triage details
                    res_col1, res_col2, res_col3 = st.columns(3)
                    res_col1.metric("Assigned ID", res.get("incident_id"))
                    res_col2.metric("Operational Status", res.get("operational_status"))
                    res_col3.metric("Evidence Status", res.get("evidence_status"))

                    if res.get("has_photograph"):
                        st.info("Photograph successfully sanitized (EXIF metadata stripped, re-encoded).")
                    else:
                        st.warning("No photograph attached. Complaint preserved as pending human inspection.")

                except BackendAPIError as e:
                    st.error(f"Submission Error: {e.detail}")
                except Exception as e:
                    st.error(f"Unexpected Error: {str(e)}")


# ============================================================================
# Screen 3: Multi-Agent Execution
# ============================================================================

elif nav_choice == "🤖 Multi-Agent Execution":
    st.title("Multi-Agent Orchestration Telemetry")
    st.caption("Inspect live execution across the 6 specialist agents and deterministic workflow gates")

    if not backend_live:
        st.error("FastAPI Backend is currently unreachable.")
        st.stop()

    try:
        incidents_data = client.get_incidents(limit=50)
        items = incidents_data.get("items", [])
    except Exception as e:
        st.error(f"Failed to fetch incidents: {str(e)}")
        st.stop()

    if not items:
        st.warning("No incidents available. Seed demonstration data first.")
        st.stop()

    # Incident selector
    inc_options = {
        f"{inc['incident_id']} — {inc['category']} ({inc['operational_status']})": inc['incident_id']
        for inc in items
    }
    selected_label = st.selectbox("Select Incident Case File", list(inc_options.keys()))
    selected_id = inc_options[selected_label]

    # Retrieve full incident details
    inc_detail = client.get_incident(selected_id)

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        run_clicked = st.button("▶ Run Multi-Agent Mesh", type="primary", use_container_width=True)

    if run_clicked:
        with st.spinner("Invoking LangGraph 6-Agent Mesh on FastAPI backend..."):
            try:
                run_res = client.run_workflow(selected_id)
                st.success(run_res.get("message", "Workflow execution completed."))
                inc_detail = client.get_incident(selected_id)
            except BackendAPIError as e:
                st.error(f"Execution Error: {e.detail}")
            except Exception as e:
                st.error(f"Unexpected Error: {str(e)}")

    # Agent Mesh Visual Hierarchy
    st.markdown("### Agent Orchestration Flow")
    st.markdown(
        """
        ```
        [ Citizen Intake / Image Sanitizer ]
                        │
                        ▼
           [ Incident Intelligence Agent ] ──── (Multimodal Groq Vision / Fact Extraction)
                 ┌──────┴──────┐
                 ▼             ▼
          [ GeoCivic ]   [ Priority ]  ◀─── PARALLEL EXECUTION BRANCHES
                 └──────┬──────┘
                        ▼
          [ Resolution Planning Agent ] ──── (Bifurcated Temporary / Permanent Plan)
                        │
                        ▼
             [ Critic & Verification ] ──── (Safety & Resource Validation)
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
      [ Approved ]             [ Rejection ] ──► [ Adaptive Recovery ]
           │                                            │
           ▼                                            ▼
    [ Deterministic Gate ]                       [ Plan Revision ]
           │
           ▼
    [ SIMULATED_RESOLVED ]
        ```
        """
    )

    st.markdown("### Specialist Agent Outputs & Telemetry")

    # 1. Incident Intelligence
    with st.expander("1. Incident Intelligence Agent", expanded=True):
        extracted = inc_detail.get("extracted_facts") or {}
        ev_analysis = inc_detail.get("evidence_analysis") or {}
        st.markdown(f"**Detected Category:** `{extracted.get('category', '—')}` (Confidence: {extracted.get('confidence_score', '—')})")
        st.markdown(f"**Severity Indicators:** {', '.join(extracted.get('severity_indicators', [])) or 'None'}")
        st.markdown(f"**Evidence Assessment:** {ev_analysis.get('visible_evidence', 'No photographic analysis')}")
        st.markdown(f"**Evidence Outcome:** `{inc_detail.get('evidence_status', '—')}` | **Provenance:** `{ev_analysis.get('provenance', 'UNVERIFIED')}`")

    # 2. Parallel GeoCivic & Priority Branches
    col_geo, col_prio = st.columns(2)
    with col_geo:
        with st.expander("2A. GeoCivic Agent (Parallel Branch)", expanded=True):
            geo = inc_detail.get("geo_context") or {}
            is_dup = geo.get("is_duplicate", False)
            if is_dup:
                st.warning(f"Duplicate Flagged: Matches `{geo.get('duplicate_of_id')}` ({geo.get('distance_meters', '—')}m away)")
            else:
                st.success("Unique Incident Confirmed (No spatial duplicate found within threshold)")
            st.caption("Calculated using Haversine spherical distance against municipal incident registry.")

    with col_prio:
        with st.expander("2B. Priority Intelligence Agent (Parallel Branch)", expanded=True):
            prio = inc_detail.get("priority") or {}
            score = prio.get("priority_score", 0)
            band = prio.get("priority_band", "—")
            st.metric("Priority Score", f"{score} / 100", f"Band: {band}")
            st.caption(prio.get("reasoning", "Multi-factor evaluation"))

    # 3. Resolution Planning
    with st.expander("3. Resolution Planning Specialist", expanded=True):
        plan = inc_detail.get("current_plan") or {}
        if plan:
            st.markdown(f"**Action Category:** `{plan.get('action_category', '—')}`")
            st.markdown("**Mitigation Steps (Temporary):**")
            for step in plan.get("mitigation_steps", []):
                st.markdown(f"- {step}")
            st.markdown("**Permanent Repair Plan:**")
            for step in plan.get("permanent_steps", []):
                st.markdown(f"- {step}")
            st.markdown(f"**Required Crew / Resources:** `{', '.join(plan.get('required_resources', []))}`")
            if plan.get("is_revised"):
                st.info("⚡ Plan was revised by Adaptive Recovery agent during execution.")
        else:
            st.info("No plan formulated yet. Run the workflow mesh above.")

    # 4. Critic & Verification Gatekeeper
    with st.expander("4. Critic & Verification Gatekeeper", expanded=True):
        val = inc_detail.get("validation") or {}
        if val:
            verdict = val.get("verdict", "—")
            if verdict == "APPROVE":
                st.success(f"Critic Verdict: **APPROVED** — {val.get('feedback', '')}")
            elif verdict == "REJECT":
                st.error(f"Critic Verdict: **REJECTED** — {val.get('feedback', '')}")
            else:
                st.warning(f"Critic Verdict: **{verdict}** — {val.get('feedback', '')}")
            st.caption(f"Closure criteria checked: {len(val.get('required_closure_criteria', []))} rules enforced.")
        else:
            st.info("Validation not yet recorded.")


# ============================================================================
# Screen 4: Failure Simulation Lab
# ============================================================================

elif nav_choice == "🧪 Failure Simulation Lab":
    st.title("Deterministic Failure Simulation Lab")
    st.caption("Demonstrate adaptive recovery, replanning, and deterministic closure gates under resource obstacles")

    if not backend_live:
        st.error("FastAPI Backend is currently unreachable.")
        st.stop()

    try:
        incidents_data = client.get_incidents(limit=50)
        items = incidents_data.get("items", [])
    except Exception as e:
        st.error(f"Failed to fetch incidents: {str(e)}")
        st.stop()

    if not items:
        st.warning("No incidents available. Seed demonstration data first.")
        st.stop()

    inc_options = {f"{inc['incident_id']} — {inc['category']}": inc['incident_id'] for inc in items}
    target_id = st.selectbox("Select Target Incident", list(inc_options.keys()))
    incident_id = inc_options[target_id]

    scenarios = {
        "normal": "Normal Execution (Standard repair with verified closure evidence)",
        "crew_unavailable": "Crew Unavailable (Internal crew shortage -> Adaptive contractor dispatch)",
        "materials_unavailable": "Materials Unavailable (Asphalt supply shortage -> Cold mix patch)",
        "critic_rejection": "Critic Rejection (Safety check failure -> Injected replanning cycle)",
        "insufficient_closure_evidence": "Insufficient Closure Evidence (Closure verification blocked)",
        "retry_exhaustion": "Retry Exhaustion (Repeated execution failures -> Escalated to Supervisor)",
    }

    selected_scenario = st.selectbox(
        "Choose Simulation Scenario",
        list(scenarios.keys()),
        format_func=lambda x: f"{x.upper()}: {scenarios[x]}",
    )

    if st.button("🚀 Run Deterministic Simulation", type="primary", use_container_width=True):
        with st.spinner(f"Executing scenario '{selected_scenario}' against LangGraph workflow..."):
            try:
                sim_res = client.simulate_scenario(incident_id, selected_scenario)
                st.success("Simulation Execution Completed!")

                # Status Banner
                op_status = sim_res.get("operational_status", "")
                is_sim = sim_res.get("is_simulated_resolution", False)

                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("Final Status", op_status)
                col_res2.metric("Evidence Status", sim_res.get("evidence_status", "—"))
                col_res3.metric("Simulated Resolution", "YES" if is_sim else "NO (Blocked/Escalated)")

                if is_sim:
                    st.markdown(
                        '<div class="status-badge badge-sim" style="font-size:14px; padding:8px 12px;">'
                        '✓ SIMULATED_RESOLVED [Explicit Simulation Marker — Verified via Synthetic Evidence]'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="status-badge badge-blocked" style="font-size:14px; padding:8px 12px;">'
                        f'⚠ {op_status}: Deterministic Gate Prevented Closure'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("#### Scenario Outcomes & Plan Telemetry")
                plan = sim_res.get("current_plan") or {}
                if plan:
                    st.markdown(f"**Action Category:** `{plan.get('action_category', '—')}`")
                    st.markdown(f"**Plan Mutated / Revised:** `{'YES' if plan.get('is_revised') else 'NO'}`")
                    st.markdown(f"**Resources Allocated:** `{', '.join(plan.get('required_resources', []))}`")

                val = sim_res.get("validation") or {}
                if val:
                    st.markdown(f"**Critic Verdict:** `{val.get('verdict')}` — {val.get('feedback')}")

            except BackendAPIError as e:
                st.error(f"Simulation Error: {e.detail}")
            except Exception as e:
                st.error(f"Unexpected Error: {str(e)}")


# ============================================================================
# Screen 5: Audit & Provenance Timeline
# ============================================================================

elif nav_choice == "🔍 Audit & Provenance Timeline":
    st.title("Audit Trail & Provenance Timeline")
    st.caption("Immutable chronological record with model inference provenance and tool execution telemetry")

    if not backend_live:
        st.error("FastAPI Backend is currently unreachable.")
        st.stop()

    try:
        incidents_data = client.get_incidents(limit=50)
        items = incidents_data.get("items", [])
    except Exception as e:
        st.error(f"Failed to fetch incidents: {str(e)}")
        st.stop()

    if not items:
        st.warning("No incidents available. Seed demonstration data first.")
        st.stop()

    inc_options = {f"{inc['incident_id']} — {inc['category']}": inc['incident_id'] for inc in items}
    target_id = st.selectbox("Select Case to Audit", list(inc_options.keys()))
    incident_id = inc_options[target_id]

    try:
        audit_events = client.get_audit(incident_id)
    except Exception as e:
        st.error(f"Failed to fetch audit events: {str(e)}")
        st.stop()

    if not audit_events:
        st.info("No audit events recorded for this incident yet.")
    else:
        st.markdown(f"**Total Audit Records:** `{len(audit_events)}` events logged")

        for idx, ev in enumerate(audit_events):
            with st.container():
                agent = ev.get("agent", "Unknown Agent")
                action = ev.get("action", "Action")
                res_text = ev.get("result", "")
                ts = ev.get("timestamp", "—")

                # Provenance badges
                prov_badge = ""
                if "Groq Vision" in res_text:
                    prov_badge = "🟢 Groq Vision"
                elif "Fallback" in res_text or "fallback" in res_text:
                    prov_badge = "🟡 Deterministic Fallback"
                elif "Simulated" in res_text or "Demo" in res_text:
                    prov_badge = "🔵 Seeded Simulation"

                st.markdown(
                    f"""
                    <div class="agent-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong style="color:#2dd4bf; font-size:13px;">#{idx+1} — {agent}</strong>
                            <span style="color:#94a3b8; font-size:11px; font-family:monospace;">{ts}</span>
                        </div>
                        <div style="color:#f1f5f9; font-weight:600; margin-top:4px; font-size:13px;">
                            {action} {f'<span style="font-size:11px; margin-left:8px; color:#38bdf8;">[{prov_badge}]</span>' if prov_badge else ''}
                        </div>
                        <div style="color:#cbd5e1; font-size:12px; margin-top:6px; font-family:monospace; background-color:#030712; padding:8px; border-radius:6px;">
                            {res_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
