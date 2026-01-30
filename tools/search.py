from pathlib import Path

from agno.tools import tool


@tool
def search(query: str, root: str = ".", max_results: int = 20) -> list[str]:
    """
    Search for a text fragment in repository files.
    Returns list of matches in the format: 'path:line_number:line_content'.
    Limits results to max_results.
    """
    root_path = Path(root)
    results = []

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            with file_path.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if query in line:
                        # path relative to root, line number, snippet
                        results.append(f"{file_path.relative_to(root_path)}:{i}:{line.strip()}")
                        if len(results) >= max_results:
                            return results
        except Exception:
            continue  # skip files that can't be read

    return results
