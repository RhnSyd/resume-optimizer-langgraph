from pypdf import PdfReader
from docx import Document
from src.graph.state import ResumeState


def extract_pdf(path: str) -> str:
    """Extract raw text from a PDF file."""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx(path: str) -> str:
    """Extract raw text from a .docx file."""
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def ingest_node(state: ResumeState) -> dict:
    """
    LangGraph node: reads state['resume_path'], extracts text,
    returns partial state update.
    """
    path = state["resume_path"]
    ext = path.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        text = extract_pdf(path)
    elif ext == "docx":
        text = extract_docx(path)
    else:
        raise ValueError(f"Unsupported file type: .{ext} (expected .pdf or .docx)")

    if not text.strip():
        raise ValueError(f"No text extracted from {path} — file may be scanned/image-based or empty.")

    return {
        "resume_raw": text,
        "status": "scoring",
    }