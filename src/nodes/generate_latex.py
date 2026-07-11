import re
from langchain_google_genai import ChatGoogleGenerativeAI
from src.graph.state import ResumeState
from src.utils.llm_helpers import normalize_content

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d[\d\-\.\s\(\)]{8,}\d)")
GITHUB_RE = re.compile(r"github\.com/([A-Za-z0-9_-]+)", re.IGNORECASE)
LINKEDIN_RE = re.compile(r"linkedin\.com/in/([A-Za-z0-9_-]+)", re.IGNORECASE)

HEADER_TEMPLATE = r"""\documentclass[25pt]{resume}
\usepackage[hidelinks]{hyperref}
\usepackage{lipsum}
\usepackage{fontawesome}
\usepackage{mathptmx}
\pagestyle{empty}
\usepackage[15pt]{moresize}
\usepackage{graphicx}
\newgeometry{left=0.4in, top=0.4in, right=0.4in, bottom=0.5in}

\begin{document}
\fontsize{11.5pt}{15.5pt}\selectfont

\begin{center}
    {\Huge \textbf{%(name)s}}\\[4pt]
    \scalebox{0.95}{
        %(contact_line)s
    }
\end{center}
"""

FOOTER = r"""
\end{document}
"""


def _guess_name(resume_text: str) -> str:
    """Heuristic: the name is almost always the first non-empty line of a resume."""
    for line in resume_text.strip().splitlines():
        line = line.strip()
        if line:
            return line
    return "Name Not Found"


def extract_contact_info(resume_text: str) -> dict:
    """Deterministic regex extraction — no LLM call, no risk of mistranscribing exact values."""
    email_match = EMAIL_RE.search(resume_text)
    phone_match = PHONE_RE.search(resume_text)
    github_match = GITHUB_RE.search(resume_text)
    linkedin_match = LINKEDIN_RE.search(resume_text)

    phone = None
    if phone_match:
        # Strip everything except digits for a clean, consistent format
        digits = re.sub(r"\D", "", phone_match.group(0))
        phone = digits

    return {
        "name": _guess_name(resume_text),
        "phone": phone,
        "email": email_match.group(0) if email_match else None,
        "github": github_match.group(1) if github_match else None,
        "linkedin": linkedin_match.group(1) if linkedin_match else None,
    }


def _build_header(contact: dict) -> str:
    parts = []
    if contact.get("phone"):
        parts.append(rf"\faPhone\ {contact['phone']}")
    if contact.get("email"):
        parts.append(rf"\faEnvelope\ \href{{mailto:{contact['email']}}}{{{contact['email']}}}")
    if contact.get("github"):
        handle = contact["github"]
        parts.append(rf"\faGithub\ \href{{https://github.com/{handle}}}{{github.com/{handle}}}")
    if contact.get("linkedin"):
        handle = contact["linkedin"]
        parts.append(rf"\faLinkedin\ \href{{https://linkedin.com/in/{handle}}}{{linkedin.com/in/{handle}}}")

    contact_line = r" \;\textbar\; ".join(parts)
    name = contact.get("name") or "Name Not Found"

    return HEADER_TEMPLATE % {"name": name, "contact_line": contact_line}

LATEX_BODY_PROMPT = r"""You are converting a resume's plain text into LaTeX, using a specific custom
resume class. Output ONLY the LaTeX body content described below — no \documentclass, no \begin{document},
no header/contact info (that's handled separately), no \end{document}, no markdown code fences, no
commentary. Just the raw LaTeX body.

TEMPLATE STRUCTURE TO FOLLOW EXACTLY (this is the custom "resume" class's syntax):

1. Summary paragraph, centered:
\begin{center}
<summary text, 2-4 sentences>
\end{center}

2. Experience section:
\begin{ResumeSection}{experience}
    \textbf{\fontsize{13pt}{15pt}\selectfont <Company Name> }

    \textbf{<Job Title>} \hfill <Start> -- <End>
    \begin{itemize}
        \item <bullet 1>
        \item <bullet 2>
        ...

        \vspace{0.3\baselineskip}
        {\underline{\textbf{Tools \& Technologies:}} <comma-separated tools for this role>}
    \end{itemize}
    \vspace{0.5\baselineskip}

    <repeat the above block for each additional company, most recent first>
\end{ResumeSection}

3. Projects section (only if the resume has a projects section):
\begin{ResumeSection}{Projects}
    \begin{itemize}
        \item \textbf{<Project Name>} - <one-line description with any metrics>
        ...
    \end{itemize}
\end{ResumeSection}

4. Education section:
\begin{ResumeSection}{Education}
    \textbf{<Degree>} - <Field> \hfill \textit{<Institution>} \\
    <repeat for each degree, most recent first>
\end{ResumeSection}

5. Skills section, as a table:
\begin{ResumeSection}{Skills}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}} l p{0.75\textwidth}}
\textbf{<Category>} & <comma-separated skills> \\
<repeat per category>
\end{tabular*}
\end{ResumeSection}

LATEX ESCAPING RULES (critical — unescaped special characters will break compilation):
- Escape every: % as \%, & as \&, $ as \$, # as \#, _ as \_
- Do NOT escape characters already inside a \textbf{}, \textit{}, or \href{} command's braces if they're
  part of LaTeX syntax itself — only escape literal special characters that appear IN THE TEXT content.
- Use \% for any percentage sign in the resume text (e.g. "34%" becomes "34\%").
- Use -- (double hyphen) for date ranges like "Aug 2022 -- Present", not an em-dash character.

CONTENT RULES:
- Preserve every fact from the source resume exactly — do not add, remove, or alter any bullet's
  meaning, metric, company name, or date.
- Bold key metrics or technology names within bullets where it aids scannability, using \textbf{}, but
  don't overdo it — 1-2 bolded phrases per bullet at most, not the whole bullet.
- Group each role's listed tools into the "Tools & Technologies" line as shown above.

{length_feedback}

Resume text to convert:
{resume}
"""


def generate_latex_body(resume_text: str, length_feedback: str = "") -> str:
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)
    prompt = LATEX_BODY_PROMPT.replace("{resume}", resume_text).replace("{length_feedback}", length_feedback)
    response = llm.invoke(prompt)
    body = normalize_content(response.content).strip()
    # Strip accidental markdown fences if the model added them despite instructions
    if body.startswith("```"):
        body = body.split("\n", 1)[1] if "\n" in body else body
        body = body.rsplit("```", 1)[0].strip()
    return body


def generate_latex_node(state: ResumeState) -> dict:
    print("[generate_latex] extracting contact info...")
    contact = extract_contact_info(state["resume_raw"])

    length_feedback = state.get("length_feedback") or ""
    latex_iteration = state.get("latex_iteration", 0)

    print(f"[generate_latex] converting resume draft to LaTeX (latex_iteration={latex_iteration})...")
    body = generate_latex_body(state["resume_draft"], length_feedback=length_feedback)

    full_source = _build_header(contact) + "\n" + body + "\n" + FOOTER

    return {
        "latex_source": full_source,
        "latex_iteration": latex_iteration + 1,
        "status": "generating_output",
    }