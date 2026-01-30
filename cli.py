import argparse
import os


def parse_args() -> argparse.Namespace:
    default_local_path = os.getenv("GITHUB_REPO_LOCAL_PATH", "/tmp/repo_clone")
    default_base_branch = os.getenv("GITHUB_BASE_BRANCH", "main")
    default_max_iterations = int(os.getenv("MAX_ITERATIONS", "1"))

    parser = argparse.ArgumentParser(description="Coding agent runner")
    parser.add_argument(
        "--repo",
        dest="repo_name",
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
        help="Base branch for feature branch",
    )
    parser.add_argument(
        "--issue",
        dest="issue_number",
        type=int,
        default=None,
        help="Issue number to work on (optional)",
    )

    args = parser.parse_args()
    if not args.repo_name:
        parser.error("Repository is required. Use --repo or set GITHUB_REPO_NAME.")

    return args
