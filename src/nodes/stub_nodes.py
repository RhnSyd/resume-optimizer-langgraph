"""
Only compare_gate remains here — it's real, tested routing logic (not a stub),
just still living in this file from earlier scaffolding. Every other stub that
used to be here (ats_score, generate_latex, compile_outputs, await_feedback,
route_feedback) has been replaced by its real implementation in a dedicated file.
"""
from src.graph.state import ResumeState


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