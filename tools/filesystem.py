import subprocess
from pathlib import Path

from agno.tools import tool

from config import get_github_token, get_repo_path


@tool
def list_files(root: str = ".", max_files: int = 200) -> list[str]:
    """
    List repository files up to max_files limit.
    Shows absolute paths.
    """
    root_path = Path(root).resolve()
    files = [str(p.resolve()) for p in root_path.rglob("*") if p.is_file()]
    return files[:max_files]


@tool
def read_file(path: str, max_lines: int = 300) -> str:
    """
    Read content of a file, limited by max_lines.
    Returns string.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    with p.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) > max_lines:
        return "".join(lines[:max_lines]) + "\n...<truncated>..."
    return "".join(lines)


@tool
def create_file(path: str, content: str) -> str:
    """
    Create a new file. Overwrites if file exists.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        f.write(content)
    return f"File '{path}' created/overwritten."


@tool
def rewrite_file(path: str, content: str) -> str:
    """
    Completely rewrite an existing file with new content.
    Use this when you need to make multiple changes - it's more reliable than update_file.
    IMPORTANT: You must provide the COMPLETE file content.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found. Use create_file for new files."

    p.write_text(content, encoding="utf-8")
    return f"File '{path}' completely rewritten."


@tool
def update_file(path: str, old: str, new: str) -> str:
    """
    Replace exact text fragment in a file.
    Fails if fragment not found. Shows context if not found.
    WARNING: For multiple changes, prefer rewrite_file instead.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    text = p.read_text(encoding="utf-8")
    if old not in text:
        # Показываем похожие строки для отладки
        lines = text.split("\n")
        old_first_line = old.strip().split("\n")[0].strip()
        similar = [
            f"Line {i + 1}: {line.strip()}"
            for i, line in enumerate(lines)
            if old_first_line[:30] in line or line.strip()[:30] in old_first_line
        ][:5]
        hint = "\n".join(similar) if similar else "No similar lines found"
        return f"Error: fragment not found. Similar lines:\n{hint}"

    # Проверка на дубликаты - не добавляем если new уже есть в файле
    if new in text and new != old:
        return "Warning: new content already exists in file. Skipping to avoid duplicates."

    updated_text = text.replace(old, new, 1)
    p.write_text(updated_text, encoding="utf-8")
    return f"File '{path}' updated."


@tool
def replace_lines(path: str, start_line: int, end_line: int, new_content: str) -> str:
    """
    Replace lines from start_line to end_line (inclusive, 1-indexed) with new content.
    More reliable than update_file for targeted changes.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    lines = p.read_text(encoding="utf-8").split("\n")
    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        return f"Error: invalid line range {start_line}-{end_line} (file has {len(lines)} lines)"

    new_lines = new_content.split("\n")
    lines[start_line - 1 : end_line] = new_lines
    p.write_text("\n".join(lines), encoding="utf-8")
    return f"Replaced lines {start_line}-{end_line} in '{path}'."


@tool
def delete_lines(path: str, start_line: int, end_line: int) -> str:
    """
    Delete lines from start_line to end_line (inclusive, 1-indexed).
    Use to remove duplicate or unwanted code.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    lines = p.read_text(encoding="utf-8").split("\n")
    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        return f"Error: invalid line range {start_line}-{end_line} (file has {len(lines)} lines)"

    del lines[start_line - 1 : end_line]
    p.write_text("\n".join(lines), encoding="utf-8")
    return f"Deleted lines {start_line}-{end_line} from '{path}'."


@tool
def find_duplicates(path: str) -> str:
    """
    Find duplicate function/class definitions in a Python file.
    Returns list of duplicates with line numbers. Use before committing to catch issues.
    """
    import re

    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    lines = p.read_text(encoding="utf-8").split("\n")
    definitions: dict[str, list[int]] = {}

    # Pattern for function and class definitions
    pattern = re.compile(r"^(\s*)(def|class)\s+(\w+)")

    for i, line in enumerate(lines, 1):
        match = pattern.match(line)
        if match:
            indent, kind, name = match.groups()
            key = f"{kind} {name}"
            if key not in definitions:
                definitions[key] = []
            definitions[key].append(i)

    duplicates = {k: v for k, v in definitions.items() if len(v) > 1}

    if not duplicates:
        return "No duplicate definitions found."

    result = ["Duplicate definitions found:"]
    for name, line_nums in duplicates.items():
        result.append(f"  {name}: lines {', '.join(map(str, line_nums))}")
    return "\n".join(result)


@tool
def insert_after_line(path: str, line_number: int, content: str) -> str:
    """
    Insert content after a specific line number (1-indexed).
    Use this when you need to add new code at a specific location.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    lines = p.read_text(encoding="utf-8").split("\n")
    if line_number < 1 or line_number > len(lines):
        return f"Error: line {line_number} out of range (file has {len(lines)} lines)"

    lines.insert(line_number, content)
    p.write_text("\n".join(lines), encoding="utf-8")
    return f"Inserted content after line {line_number} in '{path}'."


@tool
def append_to_file(path: str, content: str) -> str:
    """
    Append content to the end of a file.
    Use this to add new functions, classes, or imports at the end.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    with p.open("a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended content to '{path}'."


@tool
def read_file_lines(path: str, start_line: int, end_line: int) -> str:
    """
    Read specific lines from a file (1-indexed, inclusive).
    Use this to get exact content for update_file old parameter.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    lines = p.read_text(encoding="utf-8").split("\n")
    if start_line < 1:
        start_line = 1
    if end_line > len(lines):
        end_line = len(lines)

    selected = lines[start_line - 1 : end_line]
    result = "\n".join(selected)
    return f"Lines {start_line}-{end_line}:\n{result}"


@tool
def git_diff() -> str:
    """
    Return current staged changes as unified diff.
    Assumes agent runs in git repo.
    """
    try:
        diff = subprocess.check_output(["git", "diff", "--cached"], text=True)
        return diff if diff else "No staged changes."
    except subprocess.CalledProcessError as e:
        return f"Error running git diff: {e}"


@tool
def git_status(repo_path: str = ".") -> str:
    """
    Return git status for the repository.
    """
    try:
        status = subprocess.check_output(["git", "status", "-sb"], text=True, cwd=repo_path)
        return status.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running git status: {e}"


@tool
def git_add(pathspec: str = ".", repo_path: str = ".") -> str:
    """
    Stage files for commit.
    """
    try:
        subprocess.check_output(["git", "add", pathspec], text=True, cwd=repo_path)
        return f"Staged: {pathspec}"
    except subprocess.CalledProcessError as e:
        return f"Error running git add: {e}"


@tool
def git_commit(message: str, repo_path: str = ".") -> str:
    """
    Commit staged changes. Sets default local user.name/email if missing.
    """
    try:
        name = subprocess.check_output(
            ["git", "config", "--get", "user.name"], text=True, cwd=repo_path
        ).strip()
        email = subprocess.check_output(
            ["git", "config", "--get", "user.email"], text=True, cwd=repo_path
        ).strip()
    except subprocess.CalledProcessError:
        name = ""
        email = ""

    try:
        if not name:
            subprocess.check_output(
                ["git", "config", "user.name", "coding-agent"], text=True, cwd=repo_path
            )
        if not email:
            subprocess.check_output(
                ["git", "config", "user.email", "coding-agent@local"],
                text=True,
                cwd=repo_path,
            )

        output = subprocess.check_output(["git", "commit", "-m", message], text=True, cwd=repo_path)
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running git commit: {e}"


@tool
def push_branch(
    branch_name: str,
    repo_path: str | None = None,
    repo_name: str | None = None,
) -> str:
    """
    Push branch to GitHub using HTTPS token auth.
    Secrets are loaded from config/.env.
    """
    token = get_github_token()
    if not token:
        return "Error: missing GITHUB_TOKEN in config/.env."

    resolved_repo_name = repo_name
    if not resolved_repo_name:
        return "Error: missing GITHUB_REPO_NAME in config/.env."

    resolved_repo_path = repo_path or get_repo_path()
    repo_url = f"https://x-access-token:{token}@github.com/{resolved_repo_name}.git"

    try:
        subprocess.run(
            ["git", "remote", "set-url", "origin", repo_url],
            cwd=resolved_repo_path,
            check=True,
        )

        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=resolved_repo_path,
            check=True,
        )
        return f"Pushed branch '{branch_name}' to {resolved_repo_name}."
    except subprocess.CalledProcessError as e:
        return f"Error running git push: {e}"


# === Code Quality Tools ===


@tool
def run_ruff(path: str = ".", fix: bool = False) -> str:
    """
    Run ruff linter on Python files.
    If fix=True, automatically fix fixable issues.
    Returns list of issues or success message.
    """
    cmd = ["ruff", "check", path]
    if fix:
        cmd.append("--fix")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return "Ruff: No issues found."
        return f"Ruff issues:\n{result.stdout}{result.stderr}"
    except FileNotFoundError:
        return "Error: ruff not installed. Run: pip install ruff"


@tool
def run_mypy(path: str = ".") -> str:
    """
    Run mypy type checker on Python files.
    Returns type errors or success message.
    """
    try:
        result = subprocess.run(
            ["mypy", path, "--no-error-summary"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "Mypy: No type errors found."
        return f"Mypy errors:\n{result.stdout}{result.stderr}"
    except FileNotFoundError:
        return "Error: mypy not installed. Run: pip install mypy"


@tool
def run_pytest(path: str = "tests", verbose: bool = True) -> str:
    """
    Run pytest on test files.
    Returns test results.
    """
    cmd = ["pytest", path]
    if verbose:
        cmd.append("-v")
    cmd.append("--tb=short")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            return f"All tests passed:\n{output}"
        return f"Test failures:\n{output}"
    except FileNotFoundError:
        return "Error: pytest not installed. Run: pip install pytest"


@tool
def check_python_syntax(path: str) -> str:
    """
    Check Python file for syntax errors.
    Use after modifying a Python file to ensure it's valid.
    """
    p = Path(path)
    if not p.is_file():
        return f"Error: file '{path}' not found"

    try:
        code = p.read_text(encoding="utf-8")
        compile(code, path, "exec")
        return f"Syntax OK: '{path}'"
    except SyntaxError as e:
        return f"Syntax error in '{path}' line {e.lineno}: {e.msg}"
