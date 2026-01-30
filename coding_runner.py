import os
from pathlib import Path

from agno.utils.pprint import pprint_run_response

from agents.coding_agent.agent import create_code_agent
from cli import parse_args
from tools.filesystem import checkout_branch, clone_repo
from tools.github import get_open_issues, get_pr_feedback, issue_needs_work

MAX_ITERATIONS = 2


def run_coding_agent(
    repo_name: str,
    local_path: Path,
    base_branch: str,
    issue_number: int,
) -> None:
    """Run coding agent for a specific issue (single iteration)."""
    branch_name = f"code-agent/issue-{issue_number}"

    checkout_branch(branch_name, local_path, base_branch)
    os.chdir(local_path)

    # Get PR feedback if exists
    pr_feedback = get_pr_feedback(repo_name, issue_number)
    feedback_section = ""
    if pr_feedback:
        feedback_section = f"\n## PR Feedback (fix these issues):\n{pr_feedback}\n"

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
    Coding agent workflow:
    1. Clone repository
    2. Find issues needing work
    3. Run agent for each issue
    """
    args = parse_args()
    repo_name = args.repo_name
    local_path = Path(args.local_path)
    base_branch = args.base_branch
    issue_number = args.issue_number

    clone_repo(repo_name, local_path, base_branch)

    # If specific issue provided - work on it only
    if issue_number is not None:
        if not issue_needs_work(repo_name, issue_number):
            print(f"Issue #{issue_number} already has PR without change requests. Nothing to do.")
            return
        run_coding_agent(repo_name, local_path, base_branch, issue_number)
        return

    # Find all issues needing work
    open_issues = get_open_issues(repo_name)
    if not open_issues:
        print("No open issues found. Nothing to do.")
        return

    issues_needing_work = [
        issue for issue in open_issues if issue_needs_work(repo_name, issue.number)
    ]

    if not issues_needing_work:
        print("All open issues already have pull requests without change requests. Nothing to do.")
        return

    print(
        f"Found {len(issues_needing_work)} issue(s) needing work: {[i.number for i in issues_needing_work]}"
    )
    for issue in issues_needing_work:
        run_coding_agent(repo_name, local_path, base_branch, issue.number)


if __name__ == "__main__":
    run()
