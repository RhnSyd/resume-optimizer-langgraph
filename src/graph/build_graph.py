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
from src.graph.state import ResumeState


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

# No hardcoded test harness here anymore — run the graph via main.py, which takes
# real resume/JD input and prompts for actual feedback instead of simulating it.