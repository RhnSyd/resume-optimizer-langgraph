import os
import uuid
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.graph.build_graph import graph

st.set_page_config(page_title="Resume Optimizer", page_icon="📄")
st.title("📄 AI Resume Optimizer")
st.write("Upload your resume and paste a job description — get back a tailored, ATS-scored resume.")


def save_uploaded_file(uploaded_file) -> str:
    """Writes the Streamlit-uploaded file to a temp path, preserving its extension
    so ingest_node's .pdf/.docx branching works correctly."""
    suffix = os.path.splitext(uploaded_file.name)[1]
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, f"resume{suffix}")
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return tmp_path


def show_draft(result: dict) -> None:
    st.subheader("Draft ready")

    col1, col2 = st.columns(2)
    col1.metric("ATS Score", f"{result.get('ats_score_new', result.get('ats_score_initial'))}",
                delta=result.get("ats_score_new", 0) - result.get("ats_score_initial", 0))
    col2.metric("Pages", result.get("page_count"))

    gaps = result.get("gap_report") or []
    if gaps:
        with st.expander("Remaining gaps identified"):
            for gap in gaps:
                st.write(f"- {gap}")

    pdf_path = result.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        tex_path = os.path.join(os.path.dirname(pdf_path), "resume.tex")

        col1, col2 = st.columns(2)
        with open(pdf_path, "rb") as f:
            col1.download_button("⬇️ Download resume.pdf", f, file_name="resume.pdf", mime="application/pdf")
        if os.path.exists(tex_path):
            with open(tex_path, "r", encoding="utf-8") as f:
                col2.download_button("⬇️ Download resume.tex", f, file_name="resume.tex", mime="text/plain")


# --- Session state setup ---
# Streamlit reruns this whole script on every interaction, so anything that needs
# to persist across button clicks (thread_id, the graph's paused state) must live
# in st.session_state rather than as a plain local variable.
if "stage" not in st.session_state:
    st.session_state.stage = "input"  # input -> awaiting_feedback -> done
    st.session_state.config = None
    st.session_state.result = None


# --- Stage 1: input form ---
if st.session_state.stage == "input":
    uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
    job_description = st.text_area("Paste the job description", height=250)

    if st.button("Optimize Resume", type="primary", disabled=not (uploaded_file and job_description)):
        resume_path = save_uploaded_file(uploaded_file)
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        with st.spinner("Scoring, rewriting, and compiling your resume — this can take a minute..."):
            result = graph.invoke(
                {
                    "resume_path": resume_path,
                    "job_description": job_description,
                    "iteration": 0,
                    "latex_iteration": 0,
                    "feedback_history": [],
                },
                config=config,
            )

        st.session_state.config = config
        st.session_state.result = result
        st.session_state.stage = "awaiting_feedback"
        st.rerun()


# --- Stage 2: show draft, collect feedback or approve ---
elif st.session_state.stage == "awaiting_feedback":
    show_draft(st.session_state.result)

    feedback = st.text_area("Anything you'd like changed? (leave blank to approve and finish)")

    col1, col2 = st.columns(2)
    if col1.button("Submit Feedback", disabled=not feedback):
        st.session_state.graph_last_action = "feedback"
        graph.update_state(st.session_state.config, {"user_feedback": feedback})
        with st.spinner("Revising based on your feedback..."):
            st.session_state.result = graph.invoke(None, config=st.session_state.config)
        st.rerun()

    if col2.button("Approve & Finish", type="primary"):
        graph.update_state(st.session_state.config, {"user_feedback": None})
        st.session_state.result = graph.invoke(None, config=st.session_state.config)
        st.session_state.stage = "done"
        st.rerun()


# --- Stage 3: done ---
elif st.session_state.stage == "done":
    st.success("Resume finalized!")
    show_draft(st.session_state.result)

    if st.button("Start a new resume"):
        st.session_state.stage = "input"
        st.session_state.config = None
        st.session_state.result = None
        st.rerun()