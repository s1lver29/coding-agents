import argparse
import os


def parse_coding_args() -> argparse.Namespace:
    """Parse arguments for coding agent runner."""
    default_local_path = os.getenv("REPO_PATH_GITHUB", "/tmp/repo_clone")
    default_base_branch = os.getenv("GITHUB_BASE_BRANCH", "main")

    parser = argparse.ArgumentParser(description="Coding Agent - Automated issue implementation")
    parser.add_argument(
        "--repo",
        dest="repo_name",
        required=True,
        help="GitHub repository in owner/repo format",
    )
    parser.add_argument(
        "--local-path",
        dest="local_path",
        default=default_local_path,
        help="Local path for repository clone",
    )
    parser.add_argument(
        "--base-branch",
        dest="base_branch",
        default=default_base_branch,
        help="Base branch for feature branches",
    )
    parser.add_argument(
        "--issue",
        dest="issue_number",
        type=int,
        default=None,
        help="Specific issue number to work on (optional, defaults to all open issues)",
    )

    return parser.parse_args()


def parse_reviewer_args() -> argparse.Namespace:
    """Parse arguments for reviewer agent runner."""
    parser = argparse.ArgumentParser(
        description="Reviewer Agent - Automated code review for Pull Requests"
    )
    parser.add_argument(
        "--repo",
        dest="repo_name",
        required=True,
        help="GitHub repository in owner/repo format",
    )
    parser.add_argument(
        "--pr",
        dest="pr_number",
        type=int,
        help="Specific PR number to review",
    )
    parser.add_argument(
        "--all",
        dest="review_all",
        action="store_true",
        help="Review all open PRs that need review",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force review even if already reviewed",
    )

    args = parser.parse_args()

    if not args.pr_number and not args.review_all:
        parser.error("Specify --pr <number> or --all")

    return args


# Backward compatibility alias
parse_args = parse_coding_args
