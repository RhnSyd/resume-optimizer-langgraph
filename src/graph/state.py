from typing import TypedDict, Literal, Optional

# TypedDict stores a dictionary that has a preset keys and the data types for the values. Works like a regular Dict but good to know the exact key and data type for it
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

    # Feedback loop -- Optional because user_feedback may also be Null and Optional sets it to either Null or a str
    user_feedback: Optional[str]
    feedback_history: list[str]

    # Control -- Literal sets the status to any 1 of the calues in that list. Meaning the status can only be either verifying or rewriting at a time, etc.
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