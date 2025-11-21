import os
import json
from datetime import datetime
from analyzer.impact_analyzer import analyze
from analyzer.pgvector_rag import search_similar_chunks


def load_changed_files():
    raw = os.getenv("CHANGED_FILES", "").strip()
    return [line.strip() for line in raw.split("\n") if line.strip()] if raw else []


def safe_output(txt):
    if not txt or not txt.strip():
        return (
            "# Impact Analysis Report\n"
            "⚠️ AI engine returned no content.\n"
            "This may occur when no relevant code changes were detected."
        )
    return txt


def build_semantic_graph(changed_files):
    """
    Instead of static dependency scanning, we use pgvector RAG:
      - cluster similar code chunks
      - identify which services appear in results
      - build a synthetic graph for LLM to understand dependencies
    """

    rag_chunks = []
    impacted_services = {}

    for f in changed_files:
        results = search_similar_chunks(f, limit=12)
        rag_chunks.extend(results)

        for r in results:
            svc = r["repo_name"]
            impacted_services.setdefault(svc, 0)
            impacted_services[svc] += 1

    return {
        "impacted_services": impacted_services,
        "rag_chunks": rag_chunks
    }


def run_analysis():
    pr_title = os.getenv("PR_TITLE", "(no PR title)")
    changed_files = load_changed_files()

    report = []
    report.append("# Impact Analysis Report")
    report.append(f"Generated: `{datetime.utcnow()} UTC`")
    report.append(f"**PR Title:** {pr_title}")
    report.append("")

    if not changed_files:
        report.append("### No changed files detected.")
        return "\n".join(report)

    report.append("### Changed Files")
    for c in changed_files:
        report.append(f"- `{c}`")
    report.append("")

    # Build semantic dependency graph
    semantic_graph = build_semantic_graph(changed_files)

    report.append("### Semantic Dependency Summary")
    for svc, count in semantic_graph["impacted_services"].items():
        report.append(f"- **{svc}** → {count} related code hits")
    report.append("")

    # LLM Section
    report.append("## AI Analysis")
    ai_output = analyze(pr_title, changed_files, semantic_graph)
    report.append(ai_output)

    return "\n".join(report)


if __name__ == "__main__":
    final = run_analysis()
    print(safe_output(final))
