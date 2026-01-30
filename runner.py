"""
Combined runner: Coding Agent → Reviewer Agent cycle.
Iterates until APPROVE or max iterations reached.
"""

import os
from pathlib import Path

from agno.utils.pprint import pprint_run_response

from agents.coding_agent.agent import create_code_agent
from agents.reviewer_agent.agent import create_reviewer_agent
from cli import parse_args
from tools.filesystem import checkout_branch, clone_repo
from tools.github import get_open_issues, get_pr_feedback, issue_needs_work
from tools.reviewer import (
    find_pr_number_for_issue,
    get_reviewer_feedback,
    is_pr_approved,
)

MAX_ITERATIONS = 3


def run_coding_agent(
    repo_name: str,
    local_path: Path,
    base_branch: str,
    issue_number: int,
    iteration: int,
) -> None:
    """Run coding agent for one iteration."""
    branch_name = f"code-agent/issue-{issue_number}"

    checkout_branch(branch_name, local_path, base_branch)
    os.chdir(local_path)

    # Collect feedback from PR comments and AI reviewer
    pr_feedback = get_pr_feedback(repo_name, issue_number)
    pr_number = find_pr_number_for_issue(repo_name, issue_number)
    reviewer_feedback = get_reviewer_feedback(repo_name, pr_number) if pr_number else None

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
    agent = create_code_agent()
    response = agent.run(context)
    pprint_run_response(response, markdown=True)


def run_reviewer_agent(repo_name: str, pr_number: int, iteration: int) -> None:
    """Run reviewer agent on a PR."""
    print(f"\n--- Running Reviewer Agent on PR #{pr_number} ---")

    prompt = f"""
Review Pull Request #{pr_number} in repository {repo_name}.

This is iteration {iteration}/{MAX_ITERATIONS} of the coding-review cycle.

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

    agent = create_reviewer_agent()
    response = agent.run(prompt)
    pprint_run_response(response, markdown=True)


def run_cycle_for_issue(
    repo_name: str,
    local_path: Path,
    base_branch: str,
    issue_number: int,
) -> None:
    """Run coding → review cycle until APPROVE or max iterations."""
    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n{'=' * 60}")
        print(f"=== Issue #{issue_number} - Iteration {iteration}/{MAX_ITERATIONS} ===")
        print("=" * 60)

        # Coding phase
        run_coding_agent(repo_name, local_path, base_branch, issue_number, iteration)

        # Review phase
        pr_number = find_pr_number_for_issue(repo_name, issue_number)
        if not pr_number:
            print("\nNo PR found after coding agent run. Skipping review.")
            continue

        run_reviewer_agent(repo_name, pr_number, iteration)

        # Check result
        if is_pr_approved(repo_name, pr_number):
            print(f"\n✅ PR #{pr_number} APPROVED! Cycle complete.")
            return

        if iteration < MAX_ITERATIONS:
            print(f"\n⚠️ Changes requested. Starting iteration {iteration + 1}...")
        else:
            print(f"\n❌ Max iterations ({MAX_ITERATIONS}) reached. Manual review required.")

    print(f"\n=== Finished Issue #{issue_number} ===")


def run():
    """Main entry point: clone repo and run cycle for issues."""
    args = parse_args()
    repo_name = args.repo_name
    local_path = Path(args.local_path)
    base_branch = args.base_branch
    issue_number = args.issue_number

    clone_repo(repo_name, local_path, base_branch)

    # Specific issue
    if issue_number is not None:
        if not issue_needs_work(repo_name, issue_number):
            print(f"Issue #{issue_number} already has PR without change requests. Nothing to do.")
            return
        run_cycle_for_issue(repo_name, local_path, base_branch, issue_number)
        return

    # All issues needing work
    open_issues = get_open_issues(repo_name)
    if not open_issues:
        print("No open issues found. Nothing to do.")
        return

    issues_needing_work = [
        issue for issue in open_issues if issue_needs_work(repo_name, issue.number)
    ]

    if not issues_needing_work:
        print("All open issues already have PRs without change requests. Nothing to do.")
        return

    print(
        f"Found {len(issues_needing_work)} issue(s) needing work: {[i.number for i in issues_needing_work]}"
    )
    for issue in issues_needing_work:
        run_cycle_for_issue(repo_name, local_path, base_branch, issue.number)


if __name__ == "__main__":
    run()
