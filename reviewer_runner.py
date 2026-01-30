"""
Reviewer Agent Runner - Standalone PR review.
"""

import sys

from agno.utils.pprint import pprint_run_response

from agents.reviewer_agent import create_reviewer_agent
from cli import parse_reviewer_args
from tools.reviewer import get_open_prs, pr_needs_review


def review_pr(repo_name: str, pr_number: int) -> None:
    """Run the reviewer agent on a specific PR."""
    print(f"\n{'=' * 60}")
    print(f"Reviewing PR #{pr_number} in {repo_name}")
    print("=" * 60)

    prompt = f"""
Review Pull Request #{pr_number} in repository {repo_name}.

Follow your review workflow:
1. Get PR details
2. Get linked issue requirements
3. Check CI status
4. Review the code diff
5. Submit your review with a decision (APPROVE, REQUEST_CHANGES, or COMMENT)

Repository: {repo_name}
PR Number: {pr_number}
"""

    agent = create_reviewer_agent()
    response = agent.run(prompt)
    pprint_run_response(response, markdown=True)


def run() -> int:
    """Main entry point."""
    args = parse_reviewer_args()
    repo_name = args.repo_name

    # Review specific PR
    if args.pr_number:
        review_pr(repo_name, args.pr_number)
        return 0

    # Review all open PRs
    print(f"Fetching open PRs for {repo_name}...")
    prs = get_open_prs(repo_name)

    if not prs:
        print("No open PRs found.")
        return 0

    print(f"Found {len(prs)} open PR(s)")

    reviewed_count = 0
    for pr in prs:
        if args.force or pr_needs_review(repo_name, pr.number):
            print(f"\nPR #{pr.number}: {pr.title}")
            review_pr(repo_name, pr.number)
            reviewed_count += 1
        else:
            print(f"\nPR #{pr.number}: Already reviewed (skipping)")

    print(f"\n{'=' * 60}")
    print(f"Reviewed {reviewed_count} PR(s)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
