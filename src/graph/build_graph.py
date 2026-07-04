from langgraph.graph import StateGraph, END

from src.graph.state import ResumeState
from src.nodes.ingest import ingest_node
from src.nodes.stub_nodes import (
    ats_score_node,
    gap_analysis_node,
    rewrite_xyz_node,
    generate_latex_node,
    compile_outputs_node,
    await_feedback_node,
    compare_gate,
    route_feedback,
)


builder = StateGraph(ResumeState)

builder.add_node("ingest", ingest_node)
builder.add_node("ats_score", ats_score_node)
builder.add_node("gap_analysis", gap_analysis_node)
builder.add_node("rewrite_xyz", rewrite_xyz_node)
builder.add_node("ats_recheck", ats_score_node)  # reuse same function, called on resume_draft
builder.add_node("generate_latex", generate_latex_node)
builder.add_node("compile_outputs", compile_outputs_node)
builder.add_node("await_feedback", await_feedback_node)

builder.set_entry_point("ingest")

builder.add_edge("ingest", "ats_score")
builder.add_edge("ats_score", "gap_analysis")
builder.add_edge("gap_analysis", "rewrite_xyz")
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
builder.add_edge("compile_outputs", "await_feedback")

builder.add_conditional_edges(
    "await_feedback",
    route_feedback,
    {
        "gap_analysis": "gap_analysis",
        "END": END,
    },
)

graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({
        "resume_path": "data/samples/Rehan_DataEngineer.pdf",
        "job_description": "Looking for a Senior Data Scientist with cloud + ML experience.",
        "iteration": 0,
        "feedback_history": [],
    })
    print("\n=== FINAL STATE ===")
    for k, v in result.items():
        print(f"{k}: {v}")