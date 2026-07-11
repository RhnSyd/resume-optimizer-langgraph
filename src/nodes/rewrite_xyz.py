from langchain_google_genai import ChatGoogleGenerativeAI
from src.graph.state import ResumeState
from src.utils.llm_helpers import normalize_content

REWRITE_PROMPT = """You are a resume writer who has gotten candidates into FAANG-level Data Science and ML roles.
Rewrite the resume below to fix the specific issues listed.

BULLET QUALITY BAR:
Use Google's XYZ thinking ("Accomplished [X], as measured by [Y], by doing [Z]") as a guide for WHAT
information a strong bullet includes — result, metric, method — not as a sentence template. Vary
structure the way real senior-level resumes do. Never start more than one bullet in the same section
with the same word. Ban these openers if overused: "Accomplished", "Responsible for", "Helped",
"Worked on". Lead with strong, specific verbs instead — Architected, Engineered, Reduced, Automated,
Scaled, Diagnosed, Owned, Shipped, Optimized, Cut, Built, Led, Drove.

Example of what NOT to do (repetitive template):
- "Accomplished a 34% improvement, as measured by model precision, by engineering pipelines."
- "Accomplished a 25% reduction, as measured by MTTD, by applying feature engineering."

Example of what TO do (varied, natural, still metric-driven):
- "Engineered Hadoop-to-GCP migration pipelines that lifted downstream model precision 34%."
- "Cut MTTD 25% by applying time-series feature engineering to surface failure lead-lag patterns."

Every bullet should read like a specific, technical decision a senior engineer made — not a vague
achievement. Favor precision over flowery language ("optimized," "scaled," "cut" over "significantly
enhanced," "drove strategic impact," "leveraged"). Avoid corporate filler words entirely: "synergy,"
"leverage," "spearheaded," "cutting-edge," "dynamic," "passionate," "results-driven."

CRITICAL — NEVER FABRICATE (this rule overrides everything else, including the issues list below):
- Do not invent, change, or embellish: job titles, seniority level, team size, leadership scope,
  employment dates, or any metric not present in the original text.
- Do not add ANY claim of "leading," "managing," "mentoring," or "guiding" others unless the original
  text already explicitly states this. This applies even if an issue below asks you to add leadership/
  mentorship signals — if the original resume has no evidence of it, SKIP that specific instruction
  entirely rather than inventing something to satisfy it. Do not reframe an individual-contributor
  bullet as a leadership bullet just because the issues list asked for more seniority signal.
- Never write two bullets describing the same underlying achievement from different angles just to
  pad a section (e.g. do not add a "leadership" version of a bullet that already exists elsewhere).
  Each bullet must describe a distinct piece of work.
- When in doubt, prefer being factually conservative and leaving a gap unaddressed over fabricating
  content to close it.

Other rules:
- Only rewrite bullets/sections tied to the issues listed below. Leave already-strong parts untouched.
- Preserve all factual details (company names, dates, technologies, degrees) exactly as given.
- Keep the same overall resume structure and section order.
- Output ONLY the full rewritten resume text. No preamble, no explanation, no markdown formatting.

Issues to fix:
{issues}

{feedback_section}

Original Resume:
{resume}

Job Description (for context on what to emphasize):
{jd}
"""


def rewrite_resume(resume_text: str, gap_report: list[str], job_description: str, user_feedback: str | None = None) -> str:
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0.3)

    issues = "\n".join(f"- {g}" for g in gap_report) if gap_report else "- General improvement pass, no specific issues flagged."

    feedback_section = ""
    if user_feedback:
        feedback_section = f"IMPORTANT — user feedback on the previous version (prioritize addressing this):\n{user_feedback}\n"

    prompt = REWRITE_PROMPT.format(
        issues=issues,
        feedback_section=feedback_section,
        resume=resume_text,
        jd=job_description,
    )

    response = llm.invoke(prompt)
    return normalize_content(response.content).strip()


def rewrite_xyz_node(state: ResumeState) -> dict:
    """
    LangGraph node. Rewrites the resume based on gap_report (and user_feedback if
    this is a redo-loop pass). Source text is resume_raw on the first pass,
    resume_draft on subsequent passes (so each rewrite builds on the last).
    """
    iteration = state.get("iteration", 0)
    # Use resume_draft if one already exists (from a prior rewrite pass or feedback redo),
    # regardless of the iteration count — iteration is just the retry-budget counter,
    # not an indicator of whether a draft exists yet.
    source_text = state.get("resume_draft") or state["resume_raw"]

    print(f"[rewrite_xyz] rewriting, iteration={iteration}")
    new_draft = rewrite_resume(
        resume_text=source_text,
        gap_report=state.get("gap_report", []),
        job_description=state["job_description"],
        user_feedback=state.get("user_feedback"),
    )

    return {
        "resume_draft": new_draft,
        "iteration": iteration + 1,
        "status": "verifying",
    }