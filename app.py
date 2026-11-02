
import uuid
from base64 import b64encode
from html import escape
from mimetypes import guess_type
from pathlib import Path

import streamlit as st
from langgraph.types import Command

from src.graph.workflow import build_workflow
from src.visualization.relationship_map import show_relationship_map
from src.visualization.research_conclusion import research_conclusion, review_policy_answer
from src.observability import graph_config, research_trace
from src.visualization.reliability_studio import show_reliability_studio


@st.cache_data
def image_data_uri(filename):
    """Embed bundled illustrations without requiring a separate asset server."""
    path = Path(__file__).resolve().parent / "assets" / "images" / filename
    mime_type = guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime_type};base64," + b64encode(path.read_bytes()).decode("ascii")


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="GeneScope AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# DASHBOARD STYLING
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7fb;
        color: #14264d;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
    }

    h1, h2, h3 {
        color: #10245a !important;
        letter-spacing: -0.4px;
    }
    h3 { font-size: 1.4rem !important; font-weight: 650 !important; }
    h4 { font-size: 1.15rem !important; }
    [data-testid="stMarkdownContainer"] p { font-size: 1.0625rem; }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p { color: #596b85; font-size: .95rem; line-height: 1.65; }
    [data-testid="stWidgetLabel"] p, .stButton > button p { font-size: 1rem; }

    section[data-testid="stSidebar"] {
        background: #fdfefe;
        border-right: 1px solid #e3eaf6;
    }
    .sidebar-brand { position: relative; width: 100%; aspect-ratio: 4 / 1; overflow: hidden; margin: 8px 0 12px; }
    .sidebar-brand img {
        position: absolute; top: 50%; left: -20%; width: 140%; max-width: none;
        height: auto; transform: translateY(-50%);
    }

    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        min-height: 42px;
        transition: background-color .15s ease, box-shadow .15s ease;
    }

    .stButton > button[kind="primary"] {
        background: #1763f3;
        border-color: #1763f3;
        color: white;
        box-shadow: 0 3px 8px rgba(23, 99, 243, .15);
    }
    .stButton > button[kind="primary"]:hover { background: #124fc4; border-color: #124fc4; }
    .stButton > button:focus-visible { outline: 3px solid #8db7ff; outline-offset: 3px; }
    .st-key-continue_research button:disabled,
    .st-key-continue_research button:disabled:hover {
        background: #e8edf4;
        border-color: #d5dfed;
        color: #69788e;
        box-shadow: none;
        cursor: not-allowed;
        opacity: 1;
    }

    .stTextInput input,
    .stTextArea textarea {
        background: #ffffff;
        color: #14264d;
        border-radius: 9px;
        font-size: 1.0625rem;
    }

    div[data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e3eaf6;
        border-radius: 12px;
    }

    hr { border-color: #e3eaf6; }
    .header-panels {
        display: grid;
        grid-template-columns: minmax(0, 2.35fr) minmax(0, 1fr);
        gap: 2rem;
        margin-bottom: 16px;
    }
    .hero {
        container-type: inline-size;
        background: linear-gradient(125deg, #ffffff 15%, #edf4ff 100%);
        border: 1px solid #dce7fa;
        border-radius: 18px;
        padding: 20px 24px;
        box-shadow: 0 4px 20px rgba(25, 68, 140, 0.035);
    }
    .hero-content { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); align-items: center; gap: 20px; }
    .hero-art { width: 100%; height: auto; max-height: 180px; object-fit: contain; border-radius: 14px; display: block; }
    .eyebrow { color: #315fba; font-size: .85rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
    .hero h1 { margin: 6px 0 8px; padding: 0; font-size: clamp(2.3rem, 3vw, 3rem); font-weight: 750; letter-spacing: -1.3px; line-height: 1.15; }
    .hero .tagline { font-size: 1.15rem; color: #233e66; font-weight: 650; line-height: 1.4; margin: 0 0 8px; }
    .hero .description { color: #52647e; font-size: 1rem; line-height: 1.55; max-width: 65ch; margin: 0; }
    .scope-pill { display: inline-block; padding: 5px 10px; background: #e5edfc; color: #234c98; border: 1px solid #d6e3fb; border-radius: 30px; font-size: .85rem; font-weight: 600; margin-top: 12px; }
    @container (max-width: 650px) {
        .hero-content { grid-template-columns: minmax(0, 1fr); }
        .hero-art { max-height: 150px; }
    }
    .research-guide {
        container-type: inline-size;
        display: flex;
        flex-direction: column;
        background: #ffffff;
        border: 1px solid #dce7fa;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(25, 68, 140, 0.035);
    }
    .research-guide h2 { font-size: 1rem !important; line-height: 1.4; margin: 0 0 10px; padding: 0; }
    .workflow-steps { list-style: none; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; padding: 0; margin: 0; }
    .research-guide .workflow-steps li {
        display: flex; align-items: center; justify-content: center; gap: 6px;
        min-width: 0; padding: 8px 6px; border-radius: 10px; border: 1px solid #ccdbf5;
        color: #31527f; background: #f1f6ff; font-size: .8rem !important; font-weight: 600;
    }
    .workflow-step-number {
        display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
        width: 1.2rem; height: 1.2rem; border-radius: 50%; background: rgba(255, 255, 255, .8);
        font-size: .7rem; font-weight: 700;
    }
    .workflow-steps li:nth-child(2) { background: #f6f3ff; border-color: #ddd5f6; color: #65528a; }
    .workflow-steps li:nth-child(3) { background: #eef8f6; border-color: #cce5df; color: #34675e; }
    .workflow-steps li:nth-child(4) { background: #fff7eb; border-color: #f0dfbf; color: #805c25; }
    .workflow-steps li:nth-child(5) { background: #fdf0f5; border-color: #efcfdd; color: #8a4663; }
    @container (max-width: 320px) {
        .research-guide .workflow-steps li { flex-direction: column; gap: 4px; padding: 8px 4px; font-size: .75rem !important; }
    }
    .research-guide .guide-note { color: #596b85; font-size: .95rem !important; line-height: 1.65; margin: 16px 0 0; }
    @media (max-width: 900px) {
        .header-panels { grid-template-columns: minmax(0, 1fr); gap: 1rem; }
    }
    @media (max-width: 600px) {
        .hero, .research-guide { padding: 18px; }
        .map-preview { flex-direction: column; }
        .map-connector { transform: rotate(90deg); }
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
    [data-testid="stVerticalBlockBorderWrapper"]:has(> div[style*="border"]) { background: #fff; }
    .st-key-research-form { background: #fff; border-color: #dce5f2; border-radius: 16px; }
    .st-key-research-form [data-testid="stTextInput"] [data-testid="stWidgetLabel"] p {
        color: #10245a; font-size: 1.1rem; font-weight: 700;
    }
    .st-key-research-form [data-testid="stTextInput"] [data-baseweb="input"] {
        background: #f0f6ff; border: 1px solid #bfd3f4; border-radius: 9px;
    }
    .st-key-research-form [data-testid="stTextInput"] input {
        background: #f0f6ff; font-size: 1rem;
    }
    .st-key-research-form [data-testid="stTextInput"] input::placeholder {
        font-size: .9rem; color: #627694; opacity: 1;
    }
    .st-key-research-form [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
        border-color: #1763f3; box-shadow: 0 0 0 2px rgba(23, 99, 243, .12);
    }
    div[data-testid="stMetric"] {
        background: #fff; border: 1px solid #e0e9f6; border-radius: 13px;
        padding: 13px 17px; box-shadow: 0 3px 15px rgba(16, 36, 90, .035);
    }
    div[data-testid="stMetricLabel"] { color: #52678b; }
    div[data-testid="stTabs"] [role="tablist"] { gap: 20px; border-bottom: 1px solid #dce5f2; }
    div[data-testid="stTabs"] button[role="tab"] { font-weight: 600; font-size: 1rem; padding: 10px 0 12px; }
    div[data-testid="stTabs"] button[role="tab"] p { font-size: 1rem; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color: #155eef; }
    div[data-testid="stTabs"] [role="tabpanel"] { padding-top: 18px; }
    .agent-card { display:flex; gap:10px; align-items:center; padding:11px 0;
        background:transparent; border-bottom:1px solid #edf1f7; }
    .agent-card:last-child { border-bottom: 0; }
    .agent-icon { display:flex; justify-content:center; align-items:center;
        width:30px; height:30px; flex-shrink:0; border-radius:9px;
        background:#edf2fa; color:#4c6285; font-size:.85rem; font-weight:700; }
    .agent-copy { flex:1; min-width:0; }
    .agent-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
    .agent-name { font-weight:600; color:#233b60; font-size: 1rem; overflow-wrap: anywhere; }
    .agent-desc { color:#596b85; font-size:.9rem; line-height:1.5; margin-top:5px; }
    .agent-status { font-size:.8rem; white-space:nowrap; border-radius:20px; padding:3px 8px; color:#586980; background:#f0f3f8; }
    .agent-working .agent-status { color:#174db0; background:#e4edff; }
    .agent-done .agent-status { color:#166344; background:#e4f5ec; }
    .agent-done .agent-icon { color:#166344; background:#e4f5ec; }
    .activity-row { display:flex; gap:12px; min-height:48px; }
    .activity-track { display:flex; flex-direction:column; align-items:center; width:14px; flex-shrink:0; }
    .activity-dot { width:12px; height:12px; border-radius:50%; background:#22a968;
        box-shadow:0 0 0 3px #e4f8ed; margin-top:5px; }
    .activity-dot.active { background:#2563eb; box-shadow:0 0 0 3px #dceafe; }
    .activity-line { width:2px; flex:1; background:#b9d7fa; min-height:22px; }
    .activity-copy { font-size:1rem; color:#253b61; padding-bottom:16px; line-height:1.55; }
    .activity-copy small { display:block; font-size:.9rem; color:#596b85; margin-top:3px; }
    .section-intro { color:#607392; font-size:1rem; margin:-3px 0 10px; }
    .activity-empty { border: 1px dashed #d5dfed; border-radius: 12px; padding: 18px 14px; margin-top: 10px; background: #f8faff; }
    .activity-empty p { color: #52647e; font-size: 1rem; line-height: 1.65; margin: 8px 0 0; }
    .empty-state { background: #fff; border: 1px dashed #cedaeb; border-radius: 16px; padding: 38px 24px; text-align: center; margin-top: 14px; }
    .empty-state h4 { color: #233b60; font-size: 1.25rem !important; margin: 24px 0 8px; padding: 0; }
    .empty-state p { color: #596b85; font-size: 1rem; line-height: 1.7; max-width: 45ch; margin: 0 auto; }
    .evidence-art { display: block; width: min(100%, 320px); height: auto; margin: 0 auto; }
    .map-preview { display: flex; align-items: center; justify-content: center; gap: 12px; }
    .map-node { padding: 11px 18px; border-radius: 10px; border: 1px solid #ccdbf5; color: #31527f; background: #f1f6ff; font-size: 1rem; font-weight: 600; }
    .map-node.variant { background: #f6f3ff; border-color: #ddd5f6; color: #65528a; }
    .map-node.disease { background: #eef8f6; border-color: #cce5df; color: #34675e; }
    .map-connector { color: #9aaecb; font-size: 1.1rem; }
    .app-footer { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; color: #596b85; font-size: .9rem; padding: 4px 0 10px; }
    .app-footer strong { color: #30466d; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# LANGGRAPH WORKFLOW
# =========================================================

@st.cache_resource
def get_workflow():
    """
    Preserve the compiled graph and its in-memory
    checkpointer across Streamlit reruns.
    """
    return build_workflow()


graph = get_workflow()


# =========================================================
# SESSION STATE
# =========================================================

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "research_result" not in st.session_state:
    st.session_state.research_result = None

if "research_question" not in st.session_state:
    st.session_state.research_question = ""


def get_config(phase="research"):
    return graph_config(st.session_state.thread_id, phase)


# =========================================================
# EVIDENCE HELPERS
# =========================================================

def evidence_title(item, index):
    metadata = item.get("metadata") or {}
    return item.get("title") or metadata.get("title") or f"Scientific Evidence {index + 1}"


def show_evidence_details(item):
    metadata = item.get("metadata") or {}
    document_id = str(item.get("document_id") or "")
    pmid = metadata.get("pmid")
    if not pmid and document_id.startswith("pubmed_"):
        pmid = document_id.replace("pubmed_", "")

    st.markdown("#### " + evidence_title(item, 0))
    st.write("**Journal:**", metadata.get("journal") or "Not specified")
    st.write("**Publication year:**", metadata.get("publication_year") or "Not available")
    if pmid:
        st.write("**PubMed ID:**", pmid)
    st.markdown("**Retrieved scientific excerpt**")
    st.write(item.get("content") or "No excerpt available.")
    source_url = metadata.get("source_url")
    if source_url and str(source_url).startswith(("https://", "http://")):
        st.link_button("View original source", source_url)
    distance = item.get("distance")
    if distance is not None:
        try:
            st.caption(
                f"Vector retrieval distance: {float(distance):.3f}. "
                "This measures retrieval similarity, not scientific confidence."
            )
        except (ValueError, TypeError):
            pass


def research_outcome_message(result):
    """Describe why a run has no candidate relationships."""
    if result.get("needs_clarification"):
        return "Research has not started. Please clarify your question to continue."
    if result.get("out_of_scope"):
        return "This topic is outside the current indexed research collection."
    if result.get("errors"):
        return "The research workflow could not complete. See the reported errors."
    if not result.get("retrieved_evidence") or not result.get("findings"):
        return "The available evidence is insufficient to establish a candidate relationship."
    return "No candidate relationship met the extraction criteria."


def show_human_review(result):
    if result.get("needs_clarification") or result.get("out_of_scope"):
        return

    interrupts = result.get("__interrupt__", [])
    if interrupts:
        st.subheader(
            "Human Researcher Review"
        )

        st.info(
            "The workflow is paused. Review the candidate "
            "relationships before approving or rejecting them."
        )

        review_feedback = st.text_area(
            "Reviewer comments",
            key="review_feedback",
        )

        approve_col, reject_col = st.columns(2)

        with approve_col:
            if st.button(
                "Approve Relationships",
                type="primary",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "Resuming workflow..."
                    ), research_trace():
                        resumed = graph.invoke(
                            Command(
                                resume={
                                    "approved": True,
                                    "feedback": review_feedback,
                                }
                            ),
                            config=get_config("review_resume"),
                        )

                    st.session_state.research_result = resumed
                    if "human_review_agent" not in st.session_state.get("completed_nodes", []):
                        st.session_state.completed_nodes = st.session_state.get("completed_nodes", []) + ["human_review_agent"]
                    st.session_state.activity_events = st.session_state.get("activity_events", []) + ["Human review decision recorded"]
                    st.rerun()

                except Exception as exc:
                    st.error(
                        f"Approval failed: {exc}"
                    )

        with reject_col:
            if st.button(
                "Reject Relationships",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "Resuming workflow..."
                    ), research_trace():
                        resumed = graph.invoke(
                            Command(
                                resume={
                                    "approved": False,
                                    "feedback": review_feedback,
                                }
                            ),
                            config=get_config("review_resume"),
                        )

                    st.session_state.research_result = resumed
                    if "human_review_agent" not in st.session_state.get("completed_nodes", []):
                        st.session_state.completed_nodes = st.session_state.get("completed_nodes", []) + ["human_review_agent"]
                    st.session_state.activity_events = st.session_state.get("activity_events", []) + ["Human review decision recorded"]
                    st.rerun()

                except Exception as exc:
                    st.error(
                        f"Rejection failed: {exc}"
                    )

    elif result.get("review_status") in {"approved", "rejected"}:
        rejected = result["review_status"] == "rejected"
        approved_count = 0 if rejected else len(result.get("approved_relationships") or [])
        with st.container(border=True, key="review-result"):
            st.markdown("#### Human review decision")
            status_col, count_col = st.columns([2, 1], gap="small", vertical_alignment="center")
            with status_col:
                if rejected:
                    st.warning("Rejected by researcher")
                else:
                    st.success("Researcher approved the candidate relationships.")
            with count_col:
                st.markdown("**Approved relationships**")
                st.write(approved_count)

            if rejected:
                feedback = result.get("review_feedback") or ""
                if feedback.strip():
                    st.markdown("**Rejection reason**")
                    st.text(feedback)
                st.caption("Rejected candidates remain visible for traceability.")
            else:
                st.caption(
                    "Human approval records a review decision; "
                    "it does not independently establish scientific validity."
                )

    elif result.get("review_status") == "not_required":
        st.caption(
            "Human review was skipped because there are no candidate relationships."
        )




# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown(
        f'<div class="sidebar-brand"><img src="{image_data_uri("genescope-logo.png")}" '
        'alt="GeneScope AI — Genetic research workspace"></div>',
        unsafe_allow_html=True,
    )

# =========================================================
# PAGE HEADER
# =========================================================
st.markdown(
    f"""<div class="header-panels">
    <div class="hero">
      <div class="hero-content">
      <div class="hero-copy">
      <div class="eyebrow">Evidence-led genetic research</div>
      <h1>GeneScope AI</h1>
      <div class="tagline">From scattered genetic research to connected insights.</div>
      <div class="description">Find relevant studies, explore candidate genetic relationships, and examine the supporting evidence in one workspace.</div>
      <span class="scope-pill">Current collection: APOE · Alzheimer's disease</span>
      </div>
      <img class="hero-art" src="{image_data_uri('genetics-network.webp')}"
           alt="Conceptual illustration of a DNA double helix connecting to a network of research nodes"
           width="1536" height="1024" decoding="async">
      </div>
    </div>
    <aside class="research-guide" aria-label="Research guide">
      <h2>How it works</h2>
      <ol class="workflow-steps">
        <li><span class="workflow-step-number">1</span>Ask</li>
        <li><span class="workflow-step-number">2</span>Retrieve</li>
        <li><span class="workflow-step-number">3</span>Summarize</li>
        <li><span class="workflow-step-number">4</span>Analyze</li>
        <li><span class="workflow-step-number">5</span>Review</li>
      </ol>
      <p class="guide-note">Educational research prototype. Not for clinical diagnosis.</p>
    </aside>
    </div>""",
    unsafe_allow_html=True,
)

# Node names must match src/graph/workflow.py. Only completed
# LangGraph nodes receive checkmarks; no simulated progress.
WORKFLOW_STEPS = [
    ("clarification_agent", "Question Clarification", "Checks research intent and collection scope", "❓"),
    ("research_agent", "Research Agent", "Retrieves relevant research passages", "🔎"),
    ("summarize_evidence", "Evidence Summary", "Summarizes retrieved evidence", "📝"),
    ("validation_agent", "Claim Assessment", "Assesses the retrieved research", "🔍"),
    ("evidence_validator", "Evidence Validator", "Checks support for claims", "🛡️"),
    ("verified_findings_agent", "Findings Agent", "Organizes assessed findings", "📋"),
    ("analysis_agent", "Relationship Analysis", "Extracts candidate relationships", "🧬"),
    ("human_review_agent", "Human Review", "Waits for a researcher decision", "👤"),
]


def display_agent_panels(completed, current=None, activity=None, result=None, show_team=True, show_activity=True):
    """Render the agent summary and/or live activity timeline."""
    completed = list(dict.fromkeys(completed or []))
    activity = list(activity or [])
    result = result or {}

    if show_team:
        with st.container(border=True):
            st.markdown("### AI Agent Team")
            st.caption("Completed steps are highlighted. Conditional steps may be skipped.")
            cards = []
            for index, (node, name, description, _) in enumerate(WORKFLOW_STEPS, 1):
                if node in completed:
                    status, state_class, status_title = "Done", "agent-done", "Completed"
                elif node == current:
                    status, state_class, status_title = "Next", "agent-working", "Next expected step; may be skipped"
                else:
                    status, state_class, status_title = "Idle", "", "Waiting or skipped"
                cards.append(
                    f'<div class="agent-card {state_class}">'
                    f'<div class="agent-icon" aria-hidden="true">{index:02d}</div>'
                    f'<div class="agent-copy"><div class="agent-heading"><span class="agent-name">{escape(name)}</span>'
                    f'<span class="agent-status" title="{status_title}">{status}</span></div>'
                    f'<div class="agent-desc">{escape(description)}</div></div></div>'
                )
            st.markdown("".join(cards), unsafe_allow_html=True)

    if show_activity:
        with st.container(border=True):
            st.markdown("### Agent Activity")
            st.caption("Live updates from your research workflow.")
            if not activity and not current:
                st.markdown(
                    '<div class="activity-empty"><span class="eyebrow">Ready when you are</span>'
                    '<p>Run a research question to follow each step here as it completes.</p></div>',
                    unsafe_allow_html=True,
                )
            timeline = []
            for index, entry in enumerate(activity):
                timeline.append(
                    '<div class="activity-row"><div class="activity-track">'
                    '<div class="activity-dot"></div>'
                    + ('<div class="activity-line"></div>' if index < len(activity)-1 or current else '')
                    + '</div><div class="activity-copy">'
                    + escape(str(entry)) + '<small>Step completed</small></div></div>'
                )
            if current:
                name = next((name for node, name, _, _ in WORKFLOW_STEPS if node == current), current)
                timeline.append(
                    '<div class="activity-row"><div class="activity-track">'
                    '<div class="activity-dot active"></div></div>'
                    f'<div class="activity-copy">{escape(name)}<small>Next expected step; may be skipped</small></div></div>'
                )
            if timeline:
                st.markdown("".join(timeline), unsafe_allow_html=True)
            if result.get("__interrupt__"):
                st.warning("Awaiting researcher decision — open Knowledge Graph.")
            elif result.get("review_status") == "approved":
                st.success("Researcher approved the candidates.")
            elif result.get("review_status") == "rejected":
                st.warning("Researcher rejected the candidates.")

def completed_nodes_from_result(result):
    # Stored separately because a final graph state does not contain
    # the names of all nodes that executed.
    return st.session_state.get("completed_nodes", [])


def run_research_stream(initial_state, activity_panel, agent_panel):
    """Stream node-completion updates and preserve LangGraph interrupt state."""
    completed = []
    activity = []
    current = WORKFLOW_STEPS[0][0]

    def refresh_panels():
        with activity_panel.container():
            display_agent_panels(completed, current, activity, show_team=False)
        with agent_panel.container():
            display_agent_panels(completed, current, activity, show_activity=False)

    refresh_panels()

    # 'updates' emits a dict keyed by the node that just finished.
    with research_trace():
        for update in graph.stream(initial_state, config=get_config(), stream_mode="updates"):
            if not isinstance(update, dict):
                continue
            for node, payload in update.items():
                if node == "__interrupt__":
                    continue
                if node not in completed:
                    completed.append(node)
                    display_name = next(
                        (name for step, name, _, _ in WORKFLOW_STEPS if step == node), node
                    )
                    activity.append(f"{display_name} completed")
                # The next expected node is a visual indication only.
                # It is not marked completed until a real update arrives.
                next_step = next(
                    (step for step, _, _, _ in WORKFLOW_STEPS if step not in completed),
                    None,
                )
                current = next_step
                refresh_panels()
    snapshot = graph.get_state(get_config())
    state = dict(snapshot.values or {})
    interrupts = [
        interrupt
        for task in (snapshot.tasks or [])
        for interrupt in (getattr(task, "interrupts", None) or [])
    ]
    if interrupts:
        state["__interrupt__"] = interrupts
    st.session_state.completed_nodes = completed
    st.session_state.activity_events = activity
    return state


def start_research(question, activity_panel, agent_panel):
    """Start an isolated run for either an original or clarified question."""
    question = question.strip()
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.research_question = question
    # Update the input before its widget is created on the next rerun.
    st.session_state.pending_research_question = question
    st.session_state.research_result = None
    st.session_state.selected_evidence = 0
    st.session_state.completed_nodes = []
    st.session_state.activity_events = []
    st.session_state.pop("review_feedback", None)
    initial_state = {
        "question": question,
        "gene": "APOE",
        "agent_log": [],
        "errors": [],
    }
    try:
        st.session_state.research_result = run_research_stream(
            initial_state, activity_panel, agent_panel
        )
        st.rerun()
    except Exception as exc:
        st.error("The research workflow could not complete: " + str(exc))


CLARIFICATION_OPTIONS = {
    "Genetic risk associated with APOE variants": (
        "What does the indexed research say about APOE variants and Alzheimer's disease risk?"
    ),
    "Biological mechanisms involving APOE": (
        "What biological mechanisms link APOE variants to Alzheimer's disease?"
    ),
    "Therapeutic approaches related to APOE and Alzheimer's disease": (
        "What therapeutic approaches targeting APOE have been studied in Alzheimer's disease?"
    ),
}
CUSTOM_QUESTION_OPTION = "Other — specify my research question"


def use_example_question():
    # Streamlit runs callbacks before recreating the question widget.
    st.session_state.question_input = "Does APOE epsilon 4 guarantee Alzheimer's disease?"


def show_clarification(activity_panel, agent_panel):
    """Require an explicit research objective before starting a new run."""
    with st.container(border=True):
        st.markdown("#### Help us refine your research question")
        # Each stopped run gets fresh controls with no previous selection.
        thread_id = st.session_state.thread_id
        selection = st.radio(
            "Which aspect of APOE research would you like to investigate?",
            options=[*CLARIFICATION_OPTIONS, CUSTOM_QUESTION_OPTION],
            index=None,
            key=f"clarification_choice_{thread_id}",
        )
        if selection == CUSTOM_QUESTION_OPTION:
            clarified_question = st.text_input(
                "Your specific research question",
                key=f"clarification_custom_{thread_id}",
                placeholder="Ask about APOE and Alzheimer's disease",
            ).strip()
        else:
            clarified_question = CLARIFICATION_OPTIONS.get(selection, "")
            if clarified_question:
                st.caption("Research question: " + clarified_question)
        if st.button(
            "Continue Research",
            key="continue_research",
            type="primary",
            disabled=not clarified_question,
        ):
            if clarified_question:
                start_research(clarified_question, activity_panel, agent_panel)


# =========================================================
# LIVE ACTIVITY IN THE LEFT SIDEBAR
# =========================================================
with st.sidebar:
    st.divider()
    activity_panel = st.empty()
    with activity_panel.container():
        display_agent_panels(
            st.session_state.get("completed_nodes", []),
            None,
            st.session_state.get("activity_events", []),
            st.session_state.research_result,
            show_team=False,
            show_activity=True,
        )

# =========================================================
# TWO-COLUMN DASHBOARD: SEARCH/TABS + AI AGENT TEAM
# =========================================================
main_col, agent_col = st.columns([2.35, 1], gap="medium")
with agent_col:
    agent_panel = st.empty()

with main_col:
    with st.container(border=True, key="research-form"):
        st.markdown("### Research workspace")
        st.caption(
            "Explore a question. Trace the evidence. Review the connections. "
            "Ask about the indexed APOE collection. Include a variant, disease, or relationship for a more focused question."
        )
        if "pending_research_question" in st.session_state:
            st.session_state.question_input = st.session_state.pop("pending_research_question")
        elif "question_input" not in st.session_state:
            st.session_state.question_input = st.session_state.research_question
        question = st.text_input(
            "Research question",
            placeholder="How do APOE epsilon 4 and epsilon 2 relate to Alzheimer's disease risk?",
            key="question_input",
        )
        if st.button("Run research", type="primary"):
            if not question.strip():
                st.warning("Please enter a research question.")
            else:
                start_research(question, activity_panel, agent_panel)
        st.button("Try an example question", on_click=use_example_question, key="use_example_question")
        st.caption("Try: Does APOE epsilon 4 guarantee Alzheimer's disease? Select the example, then Run research.")
        st.caption("Current scope: indexed APOE and Alzheimer's disease research. This is a limited evidence snapshot, not a comprehensive or current clinical review.")

    result = st.session_state.research_result
    if result and result.get("needs_clarification"):
        st.warning("Please clarify your research objective before continuing.")
        show_clarification(activity_panel, agent_panel)
        result = st.session_state.research_result
    if result:
        if result.get("out_of_scope"):
            st.warning(research_outcome_message(result))
            st.info(result.get("scope_message"))
        evidence_count = 0 if result.get("out_of_scope") else len(result.get("retrieved_evidence") or [])
        relationship_count = 0 if result.get("out_of_scope") else len(result.get("relationships") or [])
        finding_count = 0 if result.get("out_of_scope") else len(result.get("findings") or [])
        a, b, c = st.columns(3, gap="small")
        a.metric("Evidence excerpts", evidence_count)
        b.metric("Candidate links", relationship_count)
        c.metric("AI-assessed findings", finding_count)

    tab_graph, tab_summary, tab_evidence, tab_agents, tab_reliability = st.tabs(
        ["Knowledge Graph", "Summary", "Evidence", "Agent Insights", "Reliability Studio"],
        key="workspace_tabs", on_change="rerun",
    )

    with tab_reliability:
        if tab_reliability.open:
            show_reliability_studio()

    with tab_graph:
        st.subheader("Gene–variant–disease relationships")
        st.caption(
            "Interactive map of AI-extracted candidate relationships. "
            "Human approval is a review decision, not independent scientific verification."
        )
        if not result:
            st.markdown(
                '<div class="empty-state">'
                '<div class="map-preview" role="img" aria-label="Illustration of a gene, variant, and disease relationship">'
                '<span class="map-node">Gene</span><span class="map-connector" aria-hidden="true">→</span>'
                '<span class="map-node variant">Variant</span><span class="map-connector" aria-hidden="true">→</span>'
                '<span class="map-node disease">Disease</span></div>'
                '<h4>Your relationship map starts here</h4>'
                '<p>Enter a research question above to explore candidate connections and the evidence behind them.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
        elif result.get("out_of_scope"):
            st.info("No relationships available for this question.")
        else:
            relationships = result.get("relationships") or []
            if relationships:
                show_relationship_map(relationships, review_status=result.get("review_status"))
                st.markdown("#### Candidate genetic relationships")
                for index, relationship in enumerate(relationships, 1):
                    allele = relationship.get("allele", "Unknown variant")
                    disease = relationship.get("disease", "Unknown disease")
                    kind = str(relationship.get("relationship_type", "associated")).replace("_", " ")
                    with st.expander(f"{index}. {allele} → {kind} → {disease}"):
                        st.write(relationship.get("statement") or "AI-extracted candidate relationship")
                        citations = relationship.get("citations") or []
                        if citations:
                            st.write("**Supporting citations:**", ", ".join(map(str, citations)))
            else:
                st.info(research_outcome_message(result))
            if result.get("review_status") not in {"approved", "rejected"}:
                st.divider()
            show_human_review(result)

    with tab_summary:
        if result:
            conclusion = research_conclusion(result)
            if conclusion is not None:
                with st.container(border=True, key="research-conclusion"):
                    policy_answer = review_policy_answer(result.get("question", ""))
                    st.subheader("Review policy" if policy_answer else "Research Conclusion")
                    st.write(conclusion)
                    st.caption(
                        "Application workflow rule; not a scientific finding."
                        if policy_answer else
                        "Based on model-assessed findings from the indexed evidence; not independent scientific verification."
                    )
        st.subheader("Research Summary")
        if not result:
            st.info("Run a research question to view the summary and findings.")
        elif result.get("out_of_scope"):
            st.info("No research summary available because this topic is outside the indexed collection.")
        else:
            if result.get("errors"):
                for error in result["errors"]:
                    st.error(str(error))
            summary = result.get("research_summary")
            if summary:
                st.write(summary)
                st.caption("AI-generated summary of the indexed research collection; not a comprehensive literature review.")
            else:
                st.info(research_outcome_message(result))
            findings = result.get("findings") or []
            if findings:
                st.markdown("#### Model-assessed findings")
                for index, finding in enumerate(findings, 1):
                    st.markdown(f"**Finding {index}**")
                    st.write(finding.get("statement") or "No statement available")
                    citations = finding.get("citations") or []
                    if citations:
                        st.caption("Citations: " + ", ".join(map(str, citations)))
                st.caption("Model-assessed findings are not independently verified scientific facts.")

    with tab_evidence:
        st.subheader("Scientific Evidence")
        st.caption("Select a retrieved source to inspect its publication details and relevant excerpt.")
        evidence = (result or {}).get("retrieved_evidence") or []
        if result and result.get("out_of_scope"):
            st.info("No indexed scientific evidence available for this question.")
        elif not evidence and result:
            st.info(research_outcome_message(result))
        elif not evidence:
            st.markdown(
                '<div class="empty-state">'
                f'<img class="evidence-art" src="{image_data_uri("evidence-review.webp")}" '
                'alt="Conceptual illustration of scientific papers and a magnifying glass connected to research nodes" '
                'width="1536" height="1024" loading="lazy" decoding="async">'
                '<h4>Explore the research behind each connection</h4>'
                '<p>Run a research question to retrieve supporting studies, publication details, and relevant excerpts from the indexed collection.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            source_col, detail_col = st.columns([1, 1.35], gap="large")
            with source_col:
                st.markdown("#### Evidence from Sources")
                st.caption(f"{len(evidence)} retrieved excerpts")
                selection = st.radio(
                    "Select a source",
                    options=list(range(len(evidence))),
                    format_func=lambda i: f"{i + 1}. {evidence_title(evidence[i], i)}",
                    key="selected_evidence",
                )
            with detail_col:
                st.markdown("#### Evidence Details")
                show_evidence_details(evidence[selection])

    with tab_agents:
        st.subheader("AI Agent Insights")
        st.caption("Recorded activity from the most recent research run.")
        if result:
            if result.get("needs_clarification"):
                st.info(research_outcome_message(result))
            if result.get("agent_log"):
                for entry in result["agent_log"]:
                    st.write("•", entry)
            else:
                st.info("No agent log entries were recorded for this run.")
            if result.get("errors"):
                for error in result["errors"]:
                    st.error(str(error))
            if result.get("__interrupt__"):
                st.warning("The workflow is paused for human review in the Knowledge Graph tab.")
        else:
            st.info("Run a research question to view agent insights.")

with agent_col:
    with agent_panel.container():
        display_agent_panels(
            st.session_state.get("completed_nodes", []),
            None,
            st.session_state.get("activity_events", []),
            st.session_state.research_result,
            show_team=True,
            show_activity=False,
        )
        if result and result.get("__interrupt__"):
            st.info("👤 Researcher review is required. Open the Knowledge Graph tab to approve or reject candidate relationships.")

st.divider()
st.markdown(
    '<footer class="app-footer"><strong>GeneScope AI · Research workspace</strong>'
    '<span>APOE-focused educational prototype · Not for clinical diagnosis</span></footer>',
    unsafe_allow_html=True,
)
