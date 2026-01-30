import os
from pathlib import Path

from agno.utils.pprint import pprint_run_response

from agents.coding_agent.agent import create_code_agent
from agents.reviewer_agent.agent import create_reviewer_agent
from cli import parse_args
from tools.github import get_open_issues, get_pr_feedback, issue_needs_work
from tools.reviewer import (
    find_pr_number_for_issue,
    get_reviewer_feedback,
    is_pr_approved,
)

BASE_BRANCH = "main"
MAX_ITERATIONS = 3  # Maximum coding → review cycles


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
    """
    Запустить цикл coding agent → reviewer agent для issue.
    Повторяется до APPROVE или достижения MAX_ITERATIONS.
    """
    branch_name = f"code-agent/issue-{issue_number}"

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'=' * 60}")
        print(f"=== Issue #{issue_number} - Iteration {iteration}/{MAX_ITERATIONS} ===")
        print("=" * 60)

        # === CODING AGENT ===
        checkout_branch(branch_name, local_path, base_branch)
        os.chdir(local_path)

        # Собираем feedback: из PR comments + из AI reviewer
        pr_feedback = get_pr_feedback(repo_name, issue_number)
        pr_number = find_pr_number_for_issue(repo_name, issue_number)
        reviewer_feedback = None
        if pr_number:
            reviewer_feedback = get_reviewer_feedback(repo_name, pr_number)

        feedback_section = ""
        if pr_feedback or reviewer_feedback:
            feedback_section = "\n## Feedback to address:\n"
            if reviewer_feedback:
                feedback_section += f"\n### AI Reviewer feedback:\n{reviewer_feedback}\n"
            if pr_feedback:
                feedback_section += f"\n### PR comments:\n{pr_feedback}\n"

        context = f"""
Work on GitHub repository: {repo_name}
Local path: {local_path}
Issue number: {issue_number}
Branch name: {branch_name}
Iteration: {iteration}/{MAX_ITERATIONS}
{feedback_section}

Complete the issue fully: read issue, make changes, commit, push, create/update PR, then stop.
"""

        print("\n--- Running Coding Agent ---")
        coding_agent = create_code_agent()
        response = coding_agent.run(context)
        pprint_run_response(response, markdown=True)

        # === REVIEWER AGENT ===
        # Ищем PR после работы coding agent
        pr_number = find_pr_number_for_issue(repo_name, issue_number)
        if not pr_number:
            print("\nNo PR found after coding agent run. Skipping review.")
            continue

        print(f"\n--- Running Reviewer Agent on PR #{pr_number} ---")
        reviewer_agent = create_reviewer_agent()
        review_prompt = f"""
Review Pull Request #{pr_number} in repository {repo_name}.

This is iteration {iteration}/{MAX_ITERATIONS} of the coding-review cycle.
The coding agent just made changes based on previous feedback (if any).

Follow your review workflow:
1. Get PR details
2. Get linked issue requirements  
3. Check CI status
4. Review the code diff
5. Submit your review with a decision (APPROVE, REQUEST_CHANGES, or COMMENT)

Be thorough but fair. If the implementation meets requirements and CI passes, APPROVE.
If there are issues, REQUEST_CHANGES with specific feedback.

Repository: {repo_name}
PR Number: {pr_number}
"""
        review_response = reviewer_agent.run(review_prompt)
        pprint_run_response(review_response, markdown=True)

        # Проверяем результат review
        if is_pr_approved(repo_name, pr_number):
            print(f"\n✅ PR #{pr_number} APPROVED! Cycle complete.")
            return

        if iteration < MAX_ITERATIONS:
            print(f"\n⚠️ Changes requested. Starting iteration {iteration + 1}...")
        else:
            print(f"\n❌ Max iterations ({MAX_ITERATIONS}) reached. Manual review required.")

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
