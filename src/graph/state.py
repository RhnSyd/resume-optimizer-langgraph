from typing import TypedDict, Literal, Optional


class ResumeState(TypedDict):
    # Inputs
    resume_path: str
    job_description: str

    # Ingest output
    resume_raw: str

    # Scoring
    ats_score_initial: float
    ats_score_new: float

    # Analysis
    gap_report: list[str]

    # Rewrite
    resume_draft: str
    iteration: int

    # Output artifacts
    latex_source: str
    pdf_path: str
    page_count: int
    latex_iteration: int
    length_feedback: Optional[str]

    # Feedback loop
    user_feedback: Optional[str]
    feedback_history: list[str]

    # Control
    status: Literal[
        "ingesting",
        "scoring",
        "gap_analysis",
        "rewriting",
        "verifying",
        "generating_output",
        "awaiting_feedback",
        "done",
    ]