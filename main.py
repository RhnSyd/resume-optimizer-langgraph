import argparse
import uuid
from dotenv import load_dotenv

load_dotenv()

from src.graph.build_graph import graph


def read_job_description(args) -> str:
    if args.jd_file:
        with open(args.jd_file, "r", encoding="utf-8") as f:
            return f.read()
    return args.jd


def print_draft_summary(result: dict) -> None:
    print("\n--- Draft ready ---")
    print(f"ATS score: {result.get('ats_score_initial')} -> {result.get('ats_score_new')}")
    print(f"Pages: {result.get('page_count')}")
    print(f"PDF: {result.get('pdf_path')}")
    gaps = result.get("gap_report") or []
    if gaps:
        print("\nRemaining gaps identified:")
        for gap in gaps:
            print(f"  - {gap}")


def main():
    parser = argparse.ArgumentParser(description="AI resume optimizer — tailors your resume to a job description.")
    parser.add_argument("--resume", required=True, help="Path to your resume file (.pdf or .docx)")

    jd_group = parser.add_mutually_exclusive_group(required=True)
    jd_group.add_argument("--jd", help="Job description text, provided directly")
    jd_group.add_argument("--jd-file", help="Path to a text file containing the job description")

    args = parser.parse_args()
    job_description = read_job_description(args)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print(f"Optimizing resume against the provided job description...\n")
    result = graph.invoke(
        {
            "resume_path": args.resume,
            "job_description": job_description,
            "iteration": 0,
            "latex_iteration": 0,
            "feedback_history": [],
        },
        config=config,
    )

    while True:
        print_draft_summary(result)
        feedback = input("\nAny feedback? (press Enter to approve and finish, or type what to change): ").strip()

        if not feedback:
            graph.update_state(config, {"user_feedback": None})
            result = graph.invoke(None, config=config)
            break

        graph.update_state(config, {"user_feedback": feedback})
        print("\nRevising based on your feedback...\n")
        result = graph.invoke(None, config=config)

    print(f"\nDone! Final resume saved at: {result.get('pdf_path')}")


if __name__ == "__main__":
    main()