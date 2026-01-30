import os
from pathlib import Path

from agno.utils.pprint import pprint_run_response

from agents.coding_agent.agent import create_code_agent
from cli import parse_args
from tools.github import get_open_issues, get_pr_feedback, issue_needs_work

BASE_BRANCH = "main"
MAX_ITERATIONS = 2


def clone_repo(repo_name: str, local_path: Path):
    """
    Клонируем репозиторий локально, если ещё не клонирован
    """
    import subprocess

    if local_path.exists():
        print("Repo already cloned, fetching latest changes...")
        subprocess.run(["git", "fetch"], cwd=local_path)
    else:
        print(f"Cloning repository {repo_name}...")
        subprocess.run(["git", "clone", f"https://github.com/{repo_name}.git", str(local_path)])


def checkout_branch(branch_name: str, local_path: Path, base: str = BASE_BRANCH):
    """
    Переключаемся на ветку для работы агента.
    Если удалённая ветка существует — переключаемся на неё и делаем rebase на свежий base.
    Иначе создаём новую от base.
    """
    import subprocess

    # Fetch всё, чтобы иметь актуальное состояние
    subprocess.run(["git", "fetch", "origin"], cwd=local_path)

    # Проверяем, есть ли удалённая ветка
    result = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch_name],
        cwd=local_path,
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        # Удалённая ветка существует
        print(f"Remote branch '{branch_name}' exists, checking out...")
        subprocess.run(
            ["git", "checkout", "-B", branch_name, f"origin/{branch_name}"],
            cwd=local_path,
        )

        # Rebase на свежий base чтобы подтянуть изменения из main
        print(f"Rebasing '{branch_name}' onto 'origin/{base}'...")
        rebase_result = subprocess.run(
            ["git", "rebase", f"origin/{base}"],
            cwd=local_path,
            capture_output=True,
            text=True,
        )

        if rebase_result.returncode != 0:
            # Конфликт при rebase — abort и пересоздаём ветку
            print(f"Rebase conflict detected, aborting and recreating branch from '{base}'...")
            subprocess.run(["git", "rebase", "--abort"], cwd=local_path)
            subprocess.run(["git", "checkout", "-B", branch_name, f"origin/{base}"], cwd=local_path)
        else:
            print("Rebase successful.")
    else:
        # Удалённой ветки нет — создаём новую от base
        print(f"Creating new branch '{branch_name}' from 'origin/{base}'...")
        subprocess.run(["git", "checkout", "-B", branch_name, f"origin/{base}"], cwd=local_path)


def _run_for_issue(
    repo_name: str,
    local_path: Path,
    base_branch: str,
    issue_number: int,
) -> None:
    """Запустить агента для конкретного issue (один run до завершения)."""
    branch_name = f"code-agent/issue-{issue_number}"

    checkout_branch(branch_name, local_path, base_branch)
    os.chdir(local_path)

    # Получаем feedback из PR если есть
    pr_feedback = get_pr_feedback(repo_name, issue_number)
    feedback_section = ""
    if pr_feedback:
        feedback_section = f"""

## PR Feedback (fix these issues):
{pr_feedback}
"""

    context = f"""
Work on GitHub repository: {repo_name}
Local path: {local_path}
Issue number: {issue_number}
Branch name: {branch_name}
{feedback_section}

Complete the issue fully: read issue, make changes, commit, push, create/update PR, then stop.
"""

    print(f"\n=== Working on Issue #{issue_number} ===\n")

    agent = create_code_agent()
    response = agent.run(context)
    pprint_run_response(response, markdown=True)

    print(f"\n=== Finished Issue #{issue_number} ===")


def run():
    """
    Главный workflow agent coding:
    1. Клонирование/ветка
    2. Проверка открытых issues
    3. Проверка на какие issues нет pull requests
    4. Если нет отрытых issue или на все issue дан pull requests, то ничего делать не надо
    5. Если есть открытые issue и нет на него pull reqests, то запуск агента
    """
    args = parse_args()
    repo_name = args.repo_name
    local_path = Path(args.local_path)
    base_branch = args.base_branch
    issue_number = args.issue_number

    # 1. Клонирование репозитория
    clone_repo(repo_name, local_path)

    # Если указан конкретный issue — работаем только с ним
    if issue_number is not None:
        if not issue_needs_work(repo_name, issue_number):
            print(f"Issue #{issue_number} already has PR without change requests. Nothing to do.")
            return
        _run_for_issue(repo_name, local_path, base_branch, issue_number)
        return

    # 2. Проверка открытых issues
    open_issues = get_open_issues(repo_name)
    if not open_issues:
        print("No open issues found. Nothing to do.")
        return

    # 3. Проверка на какие issues нет PR или есть запрос на доработку
    issues_needing_work = [
        issue for issue in open_issues if issue_needs_work(repo_name, issue.number)
    ]

    # 4. Если на все issue дан PR без замечаний — ничего не делаем
    if not issues_needing_work:
        print("All open issues already have pull requests without change requests. Nothing to do.")
        return

    # 5. Запуск агента для каждого issue без PR или с запросом на доработку
    print(
        f"Found {len(issues_needing_work)} issue(s) needing work: {[i.number for i in issues_needing_work]}"
    )
    for issue in issues_needing_work:
        _run_for_issue(repo_name, local_path, base_branch, issue.number)


if __name__ == "__main__":
    run()
