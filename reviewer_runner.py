import argparse
import sys

from agents.reviewer_agent import create_reviewer_agent
from tools.reviewer import get_open_prs, pr_needs_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Reviewer Agent - Automated code review for Pull Requests"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository name (owner/repo)",
    )
    parser.add_argument(
        "--pr",
        type=int,
        help="PR number to review",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Review all open PRs that need review",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force review even if already reviewed",
    )
    return parser.parse_args()


def review_pr(repo_name: str, pr_number: int) -> None:
    """Run the reviewer agent on a specific PR."""
    print(f"\n{'=' * 60}")
    print(f"Reviewing PR #{pr_number} in {repo_name}")
    print("=" * 60)

    agent = create_reviewer_agent()

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

    try:
        response = agent.run(prompt)
        print("\n--- Agent Response ---")
        print(response.content if hasattr(response, "content") else response)
    except Exception as e:
        print(f"Error reviewing PR #{pr_number}: {e}")
        raise


def run(args: argparse.Namespace) -> int:
    """Main entry point."""
    repo_name = args.repo

    if args.pr:
        # Review specific PR
        review_pr(repo_name, args.pr)
        return 0

    if args.all:
        # Review all open PRs that need review
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

    print("Error: Specify --pr <number> or --all")
    return 1


def main() -> None:
    args = parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
