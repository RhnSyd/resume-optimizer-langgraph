from src.graph.state import ResumeState


def await_feedback_node(state: ResumeState) -> dict:
    """
    This node's body only runs AFTER the graph resumes from the interrupt.
    The actual 'pausing' is handled by LangGraph's interrupt_before mechanism at
    compile time, not by this function — by the time this code executes, the
    person has already supplied (or declined to supply) feedback via update_state().
    """
    feedback = state.get("user_feedback")
    if feedback:
        print(f"[await_feedback] received feedback: {feedback}")
    else:
        print("[await_feedback] no feedback provided — treating as approval")
    return {"status": "awaiting_feedback"}


def route_feedback(state: ResumeState) -> str:
    """Conditional edge after await_feedback: redo or end."""
    feedback = state.get("user_feedback")
    if feedback:
        print(f"[route_feedback] negative/constructive feedback — redoing")
        return "redo"
    print("[route_feedback] no feedback — ending")
    return "END"


def reset_for_feedback_redo(state: ResumeState) -> dict:
    """
    Runs between await_feedback and rewrite_xyz on the redo path. Gives the redo
    cycle a fresh retry budget (iteration/latex_iteration back to 0) and records
    the feedback in history, WITHOUT touching resume_draft — rewrite_xyz will
    build on the existing draft, not restart from resume_raw.
    """
    feedback = state.get("user_feedback", "")
    history = state.get("feedback_history", [])

    print(f"[reset_for_feedback_redo] resetting iteration counters for redo pass")

    return {
        "iteration": 0,
        "latex_iteration": 0,
        "feedback_history": history + [feedback],
        "length_feedback": None,
    }