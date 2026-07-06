"""
Stub nodes — pass-through logic so the graph shape can be tested
before real LLM/LaTeX logic is written. Replace one at a time later.
"""
from src.graph.state import ResumeState


def ats_score_node(state: ResumeState) -> dict:
    print(f"[ats_score] iteration={state.get('iteration', 0)}")
    # Fake: score improves after first rewrite, to test the loop+exit both work
    iteration = state.get("iteration", 0)
    score = 55.0 if iteration == 0 else 78.0
    if "ats_score_initial" not in state:
        return {"ats_score_initial": score, "status": "gap_analysis"}
    return {"ats_score_new": score, "status": "verifying"}


def gap_analysis_node(state: ResumeState) -> dict:
    print("[gap_analysis] running")
    return {
        "gap_report": ["missing quantified metrics", "no cloud keywords"],
        "status": "rewriting",
    }


def rewrite_xyz_node(state: ResumeState) -> dict:
    iteration = state.get("iteration", 0)
    print(f"[rewrite_xyz] running, iteration={iteration}")
    return {
        "resume_draft": f"REWRITTEN DRAFT v{iteration + 1}",
        "iteration": iteration + 1,
        "status": "verifying",
    }


def generate_latex_node(state: ResumeState) -> dict:
    print("[generate_latex] running")
    return {"latex_source": "\\documentclass{article}...", "status": "generating_output"}


def compile_outputs_node(state: ResumeState) -> dict:
    print("[compile_outputs] running")
    return {"pdf_path": "output/resume.pdf", "status": "awaiting_feedback"}


def await_feedback_node(state: ResumeState) -> dict:
    print("[await_feedback] running (interrupt will pause here in step 11)")
    return {"user_feedback": None, "status": "done"}


def compare_gate(state: ResumeState) -> str:
    """Conditional edge after ats_recheck: loop back or proceed."""
    score_new = state.get("ats_score_new", 0)
    score_initial = state.get("ats_score_initial", 0)
    iteration = state.get("iteration", 0)

    improved = score_new > score_initial
    maxed_out = iteration >= 3

    print(f"[compare_gate] new={score_new} initial={score_initial} improved={improved} iteration={iteration}")

    if improved or maxed_out:
        return "generate_latex"
    return "rewrite_xyz"


def route_feedback(state: ResumeState) -> str:
    """Conditional edge after await_feedback: redo or end."""
    feedback = state.get("user_feedback")
    if feedback:
        print(f"[route_feedback] negative feedback received: {feedback}")
        return "gap_analysis"
    print("[route_feedback] no feedback / positive — ending")
    return "END"