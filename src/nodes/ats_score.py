import json
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from src.graph.state import ResumeState

SCORING_PROMPT = """You are an ATS specialist evaluating resumes for tech, software, and data science roles.

Return ONLY valid JSON. No markdown, no code fences, no preamble, no explanation — just the raw JSON object.

Score the resume against the job description using this exact structure:

{{
  "overall_score": <number 0-100>,
  "keyword_match": {{
    "jd_keywords": [<list of key technical/skill terms found in the job description>],
    "resume_keywords": [<list of key technical/skill terms found in the resume>],
    "missing": [<jd_keywords not present in resume_keywords>]
  }},
  "checklist": {{
    "quantified_achievements": {{"score": <0-10>, "issues": [<specific bullets lacking metrics>]}},
    "skills_match": {{"score": <0-10>, "issues": [<gaps between JD required skills and resume>]}},
    "customization": {{"score": <0-10>, "issues": [<signs resume is generic vs tailored to this JD>]}},
    "action_verbs_grammar": {{"score": <0-10>, "issues": [<weak verbs, passive voice, grammar issues>]}},
    "length_conciseness": {{"score": <0-10>, "issues": [<if too long/short for experience level>]}},
    "consistency": {{"score": <0-10>, "issues": [<tense/formatting inconsistencies>]}}
  }},
  "top_gaps": [<3-5 specific, actionable fixes ranked by impact on ATS score, each referencing a specific bullet or section>]
}}

Resume:
{resume}

Job Description:
{jd}
"""


def _extract_json(text: str) -> dict:
    """Strip markdown fences if present and parse JSON, with a fallback regex grab."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def score_resume(resume_text: str, job_description: str) -> dict:
    """Call Gemini to score a resume against a JD. Returns parsed JSON dict."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    prompt = SCORING_PROMPT.format(resume=resume_text, jd=job_description)

    response = llm.invoke(prompt)
    return _extract_json(response.content)


def ats_score_node(state: ResumeState) -> dict:
    """
    LangGraph node. Scores state['resume_raw'] (first pass) or
    state['resume_draft'] (after a rewrite) against the job description.
    """
    is_recheck = "ats_score_initial" in state
    resume_text = state["resume_draft"] if is_recheck else state["resume_raw"]

    print(f"[ats_score] scoring {'draft' if is_recheck else 'original'}...")
    result = score_resume(resume_text, state["job_description"])
    score = result["overall_score"]

    if is_recheck:
        return {
            "ats_score_new": score,
            "gap_report": result["top_gaps"],  # refreshed gaps if another loop is needed
            "status": "verifying",
        }
    return {
        "ats_score_initial": score,
        "gap_report": result["top_gaps"],
        "status": "gap_analysis",
    }