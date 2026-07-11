import os
import shutil
import subprocess
import uuid
from pypdf import PdfReader
from src.graph.state import ResumeState

# resume.cls must live here — compile_outputs copies it next to the .tex file before compiling.
TEMPLATE_CLS_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "resume.cls")
OUTPUT_DIR = os.path.join(os.getcwd(), "output")

TARGET_PAGES = 2
MAX_LATEX_ITERATIONS = 3


def compile_latex(latex_source: str, output_dir: str = OUTPUT_DIR) -> tuple[str, int]:
    """
    Writes latex_source to a .tex file, compiles it with pdflatex, and returns
    (pdf_path, page_count). Raises RuntimeError with the log tail if compilation fails.
    """
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(TEMPLATE_CLS_PATH):
        raise FileNotFoundError(
            f"resume.cls not found at {TEMPLATE_CLS_PATH} — copy it there from your template zip."
        )
    shutil.copy(TEMPLATE_CLS_PATH, output_dir)

    pdflatex_path = shutil.which("pdflatex")
    if not pdflatex_path:
        raise FileNotFoundError(
            "pdflatex executable not found on PATH. Confirm your LaTeX distribution "
            "(MiKTeX/TeX Live) is installed and pdflatex is accessible from a terminal."
        )

    job_id = uuid.uuid4().hex[:8]
    tex_filename = f"resume_{job_id}.tex"
    tex_path = os.path.join(output_dir, tex_filename)

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_source)

    # Run pdflatex twice — hyperref/link references sometimes need a second pass to settle.
    for _ in range(2):
        result = subprocess.run(
            [pdflatex_path, "-interaction=nonstopmode", tex_filename],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=180,
        )

    pdf_path = os.path.join(output_dir, f"resume_{job_id}.pdf")

    if not os.path.exists(pdf_path):
        log_path = os.path.join(output_dir, f"resume_{job_id}.log")
        log_tail = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                log_tail = "".join(f.readlines()[-30:])
        raise RuntimeError(f"pdflatex failed to produce a PDF. Log tail:\n{log_tail}")

    page_count = len(PdfReader(pdf_path).pages)
    return pdf_path, page_count


def compile_outputs_node(state: ResumeState) -> dict:
    latex_iteration = state.get("latex_iteration", 1)
    print(f"[compile_outputs] compiling LaTeX (latex_iteration={latex_iteration})...")

    pdf_path, page_count = compile_latex(state["latex_source"])
    print(f"[compile_outputs] produced {page_count}-page PDF at {pdf_path}")

    return {
        "pdf_path": pdf_path,
        "page_count": page_count,
        "status": "awaiting_feedback" if _length_ok(page_count, latex_iteration) else "generating_output",
    }


def _length_ok(page_count: int, latex_iteration: int) -> bool:
    return page_count == TARGET_PAGES or latex_iteration >= MAX_LATEX_ITERATIONS


def page_length_gate(state: ResumeState) -> str:
    """Conditional edge after compile_outputs: retry generation with length feedback, or proceed."""
    page_count = state.get("page_count", TARGET_PAGES)
    latex_iteration = state.get("latex_iteration", 1)

    if _length_ok(page_count, latex_iteration):
        print(f"[page_length_gate] {page_count} page(s), acceptable — proceeding")
        return "await_feedback"

    print(f"[page_length_gate] {page_count} page(s), not {TARGET_PAGES} — regenerating with length feedback")
    return "generate_latex"


def build_length_feedback(state: ResumeState) -> dict:
    """
    Prepares the length_feedback instruction for the next generate_latex pass,
    based on how far off the last compile was from the target.
    """
    page_count = state.get("page_count", TARGET_PAGES)

    if page_count > TARGET_PAGES:
        feedback = (
            f"IMPORTANT — LENGTH CONSTRAINT: the previous version compiled to {page_count} pages, "
            f"but the target is exactly {TARGET_PAGES} pages. Condense the content: shorten verbose "
            f"bullets, remove the least impactful 1-2 bullets per role if needed, tighten the summary. "
            f"Do not remove entire roles or fabricate that experience didn't happen — only tighten wording."
        )
    else:
        feedback = (
            f"IMPORTANT — LENGTH CONSTRAINT: the previous version compiled to only {page_count} page(s), "
            f"but the target is exactly {TARGET_PAGES} pages. Expand slightly: add a bit more detail to "
            f"existing bullets (context, approach, scope) to fill the space naturally. Do not fabricate "
            f"new achievements, metrics, or projects that aren't in the original resume."
        )

    return {"length_feedback": feedback}