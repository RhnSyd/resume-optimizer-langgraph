from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()

from src.nodes.ingest import ingest_node
from src.nodes.stub_nodes import compare_gate
from src.nodes.ats_score import ats_score_node
from src.nodes.rewrite_xyz import rewrite_xyz_node
from src.nodes.generate_latex import generate_latex_node
from src.nodes.compile_outputs import compile_outputs_node, page_length_gate, build_length_feedback
from src.nodes.feedback_loop import await_feedback_node, route_feedback, reset_for_feedback_redo


class ResumeState(TypedDict):
    resume_path: str
    job_description: str
    resume_raw: str
    ats_score_initial: float
    ats_score_new: float
    gap_report: list[str]
    resume_draft: str
    iteration: int
    latex_source: str
    pdf_path: str
    page_count: int
    latex_iteration: int
    length_feedback: Optional[str]
    user_feedback: Optional[str]
    feedback_history: list[str]
    status: str


builder = StateGraph(ResumeState)

builder.add_node("ingest", ingest_node)
builder.add_node("ats_score", ats_score_node)
builder.add_node("rewrite_xyz", rewrite_xyz_node)
builder.add_node("ats_recheck", ats_score_node)
builder.add_node("generate_latex", generate_latex_node)
builder.add_node("compile_outputs", compile_outputs_node)
builder.add_node("build_length_feedback", build_length_feedback)
builder.add_node("await_feedback", await_feedback_node)
builder.add_node("reset_for_feedback_redo", reset_for_feedback_redo)

builder.set_entry_point("ingest")

builder.add_edge("ingest", "ats_score")
builder.add_edge("ats_score", "rewrite_xyz")
builder.add_edge("rewrite_xyz", "ats_recheck")

builder.add_conditional_edges(
    "ats_recheck",
    compare_gate,
    {
        "generate_latex": "generate_latex",
        "rewrite_xyz": "rewrite_xyz",
    },
)

builder.add_edge("generate_latex", "compile_outputs")

builder.add_conditional_edges(
    "compile_outputs",
    page_length_gate,
    {
        "await_feedback": "await_feedback",
        "generate_latex": "build_length_feedback",
    },
)

builder.add_edge("build_length_feedback", "generate_latex")

builder.add_conditional_edges(
    "await_feedback",
    route_feedback,
    {
        "redo": "reset_for_feedback_redo",
        "END": END,
    },
)

builder.add_edge("reset_for_feedback_redo", "rewrite_xyz")

# Checkpointer lets the graph pause and resume across separate .invoke() calls —
# required for interrupt_before to actually hold state between the pause and the
# person supplying feedback.
checkpointer = MemorySaver()

graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["await_feedback"],
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "test-run-1"}}

    print("=== FIRST INVOKE: runs until it pauses before await_feedback ===\n")
    result = graph.invoke(
        {
            "resume_path": "data/samples/Rehan_DataEngineer.pdf",
            "job_description": "Looking for a Senior Data Scientist with cloud + ML experience.",
            "iteration": 0,
            "latex_iteration": 0,
            "feedback_history": [],
        },
        config=config,
    )
    print("\n--- PAUSED. Current state snapshot: ---")
    print("page_count:", result.get("page_count"))
    print("pdf_path:", result.get("pdf_path"))
    print("status:", result.get("status"))

    # Simulate the person reviewing the PDF and giving feedback.
    # In a real interface, this input would come from the user, not be hardcoded.
    feedback_text = "Please make the summary emphasize NLP and LLM work more, less data engineering."
    print(f"\n=== SUPPLYING FEEDBACK: '{feedback_text}' ===\n")
    graph.update_state(config, {"user_feedback": feedback_text})

    print("=== SECOND INVOKE: resumes from the pause and continues ===\n")
    result2 = graph.invoke(None, config=config)

    print("\n=== FINAL STATE ===")
    for k, v in result2.items():
        if k in ("resume_raw", "latex_source"):
            continue  # too long to print usefully here
        print(f"{k}: {v}")