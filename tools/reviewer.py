"""Tools for AI Reviewer Agent - PR review, CI checks, code analysis."""

from agno.tools import tool
from github import Auth, Github

from config import get_github_reviewer_token

_gh_client: Github | None = None


def _get_client() -> Github:
    """Get GitHub client with reviewer token (separate from coding agent)."""
    global _gh_client
    if _gh_client is None:
        token = get_github_reviewer_token()
        if not token:
            raise OSError("GITHUB_TOKEN_REVIEWER or GITHUB_TOKEN is not set")
        auth = Auth.Token(token)
        _gh_client = Github(auth=auth)
    return _gh_client


@tool
def get_pr_details(repo_name: str, pr_number: int) -> str:
    """
    Get Pull Request details: title, body, author, branch, base branch.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    return f"""## PR #{pr.number}: {pr.title}

**Author**: {pr.user.login}
**Branch**: {pr.head.ref} → {pr.base.ref}
**State**: {pr.state}
**Mergeable**: {pr.mergeable}

### Description:
{pr.body or "(no description)"}
"""


@tool
def get_pr_diff(repo_name: str, pr_number: int) -> str:
    """
    Get the diff (changed files and their content) for a Pull Request.
    Returns unified diff format.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    result = []
    files = pr.get_files()

    for file in files:
        result.append(f"## {file.filename}")
        result.append(f"Status: {file.status} | +{file.additions} -{file.deletions}")
        if file.patch:
            result.append("```diff")
            result.append(file.patch)
            result.append("```")
        result.append("")

    return "\n".join(result) if result else "No file changes found."


@tool
def get_pr_files(repo_name: str, pr_number: int) -> str:
    """
    Get list of files changed in a Pull Request with stats.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    result = ["## Changed Files:"]
    files = pr.get_files()

    for file in files:
        result.append(f"- **{file.filename}** ({file.status}) +{file.additions} -{file.deletions}")

    return "\n".join(result)


@tool
def get_pr_commits(repo_name: str, pr_number: int) -> str:
    """
    Get list of commits in a Pull Request.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    result = ["## Commits:"]
    commits = pr.get_commits()

    for commit in commits:
        sha_short = commit.sha[:7]
        msg = commit.commit.message.split("\n")[0]
        author = commit.commit.author.name
        result.append(f"- `{sha_short}` {msg} ({author})")

    return "\n".join(result)


@tool
def get_linked_issue(repo_name: str, pr_number: int) -> str:
    """
    Get the issue linked to this PR (by branch name pattern or PR body).
    Returns issue title and body, or message if not found.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Try to extract issue number from branch name (e.g., "code-agent/issue-123")
    import re

    branch = pr.head.ref
    match = re.search(r"issue-(\d+)", branch, re.IGNORECASE)
    issue_number = None

    if match:
        issue_number = int(match.group(1))
    else:
        # Try to find in PR body (e.g., "Fixes #123", "Closes #123")
        if pr.body:
            match = re.search(r"(?:fixes|closes|resolves)\s*#(\d+)", pr.body, re.IGNORECASE)
            if match:
                issue_number = int(match.group(1))

    if issue_number is None:
        return "No linked issue found. Check PR body or branch name."

    try:
        issue = repo.get_issue(number=issue_number)
        return f"""## Linked Issue #{issue.number}: {issue.title}

**State**: {issue.state}
**Labels**: {", ".join([l.name for l in issue.labels]) or "none"}

### Requirements:
{issue.body or "(no description)"}
"""
    except Exception as e:
        return f"Failed to fetch issue #{issue_number}: {e}"


@tool
def get_ci_status(repo_name: str, pr_number: int) -> str:
    """
    Get CI/CD check status for a Pull Request.
    Returns status of all checks (GitHub Actions, etc.).
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    result = ["## CI/CD Status:"]

    # Get commit statuses
    head_sha = pr.head.sha
    commit = repo.get_commit(head_sha)

    has_ci = False

    # Combined status
    combined = commit.get_combined_status()

    # Individual statuses
    if combined.statuses:
        has_ci = True
        result.append(f"\n**Overall Status**: {combined.state}")
        result.append("\n### Statuses:")
        for status in combined.statuses:
            emoji = (
                "✅" if status.state == "success" else "❌" if status.state == "failure" else "⏳"
            )
            result.append(f"- {emoji} **{status.context}**: {status.state}")
            if status.description:
                result.append(f"  {status.description}")

    # Check runs (GitHub Actions)
    try:
        check_runs = commit.get_check_runs()
        if check_runs.totalCount > 0:
            has_ci = True
            result.append("\n### Check Runs (GitHub Actions):")
            for run in check_runs:
                if run.conclusion:
                    emoji = (
                        "✅"
                        if run.conclusion == "success"
                        else "❌"
                        if run.conclusion == "failure"
                        else "⏳"
                    )
                    result.append(f"- {emoji} **{run.name}**: {run.conclusion}")
                else:
                    result.append(f"- ⏳ **{run.name}**: {run.status}")

                # If failed, try to get details
                if run.conclusion == "failure" and run.output:  # noqa: SIM102
                    if run.output.summary:
                        result.append(f"  Summary: {run.output.summary[:200]}")
    except Exception as e:
        result.append(f"\n(Could not fetch check runs: {e})")

    if not has_ci:
        return "## CI/CD Status:\n\n⚠️ **No CI/CD configured for this repository.**\n\nNo GitHub Actions workflows or status checks found. Skip CI verification in your review."

    return "\n".join(result)


@tool
def get_ci_logs(repo_name: str, pr_number: int, job_name: str | None = None) -> str:
    """
    Get CI job logs for failed jobs in a Pull Request.
    If job_name is provided, get logs for that specific job.
    Returns last 100 lines of logs.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    head_sha = pr.head.sha
    commit = repo.get_commit(head_sha)

    try:
        check_runs = commit.get_check_runs()
        result = []

        for run in check_runs:
            if job_name and run.name != job_name:
                continue

            # Only show failed or specifically requested
            if run.conclusion == "failure" or job_name:
                result.append(f"## Job: {run.name}")
                result.append(f"Status: {run.conclusion or run.status}")

                if run.output:
                    if run.output.title:
                        result.append(f"Title: {run.output.title}")
                    if run.output.summary:
                        result.append(f"Summary: {run.output.summary}")
                    if run.output.text:
                        # Truncate to last 100 lines
                        lines = run.output.text.split("\n")
                        if len(lines) > 100:
                            result.append("...(truncated)...")
                            lines = lines[-100:]
                        result.append("\n".join(lines))

                result.append("")

        return "\n".join(result) if result else "No failed jobs found or job not found."
    except Exception as e:
        return f"Failed to get CI logs: {e}"


@tool
def submit_review(
    repo_name: str,
    pr_number: int,
    decision: str,
    summary: str,
) -> str:
    """
    Submit a review to a Pull Request.

    Args:
        repo_name: Repository name (owner/repo)
        pr_number: Pull Request number
        decision: "APPROVE", "REQUEST_CHANGES", or "COMMENT"
        summary: Overall review summary (include [AI-Reviewer] marker)

    Returns:
        URL of the review or error message.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Map decision to GitHub API event
    event_map = {
        "APPROVE": "APPROVE",
        "REQUEST_CHANGES": "REQUEST_CHANGES",
        "COMMENT": "COMMENT",
    }

    decision_upper = decision.upper()
    if decision_upper not in event_map:
        return f"Invalid decision: {decision}. Use APPROVE, REQUEST_CHANGES, or COMMENT."

    event = event_map[decision_upper]

    try:
        review = pr.create_review(body=summary, event=event)
        return f"Review submitted: {event}\nURL: {review.html_url}"
    except Exception as e:
        # Detailed error info
        error_msg = repr(e)
        if hasattr(e, "data"):
            error_msg = f"{error_msg} | data: {e.data}"  # type: ignore
        if hasattr(e, "status"):
            error_msg = f"HTTP {e.status}: {error_msg}"  # type: ignore

        # Fallback: post as regular comment if review fails
        try:
            comment = pr.create_issue_comment(f"**Review ({decision_upper}):**\n\n{summary}")
            return f"Review failed, posted as comment instead: {comment.html_url}\nOriginal error: {error_msg}"
        except Exception as e2:
            return f"Failed to submit review: {error_msg}\nAlso failed to post comment: {repr(e2)}"


@tool
def post_review_comment(repo_name: str, pr_number: int, comment: str) -> str:
    """
    Post a general comment to a Pull Request (not a review).
    Use for additional notes or questions.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    comment_obj = pr.create_issue_comment(comment)
    return f"Comment posted: {comment_obj.html_url}"


# === Helper functions for runner (not tools) ===


def get_open_prs(repo_name: str) -> list:
    """Get all open Pull Requests."""
    repo = _get_client().get_repo(repo_name)
    return list(repo.get_pulls(state="open"))


def get_pr_by_number(repo_name: str, pr_number: int):
    """Get PR by number."""
    repo = _get_client().get_repo(repo_name)
    return repo.get_pull(pr_number)


def pr_needs_review(repo_name: str, pr_number: int) -> bool:
    """
    Check if PR needs AI review.
    Returns True if:
    - No reviews yet, or
    - Last review is not from the bot
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    # Check if draft
    if pr.draft:
        return False

    # Check if already has AI review
    try:
        reviews = list(pr.get_reviews())
        if not reviews:
            return True

        # Check if last review was from us (by checking for marker in body)
        for review in reversed(reviews):
            if review.body and "[AI-Reviewer]" in review.body:
                # AI already reviewed this version
                # Check if there are new commits since review
                review_time = review.submitted_at
                commits = list(pr.get_commits())
                if commits:
                    last_commit_time = commits[-1].commit.author.date
                    if last_commit_time > review_time:
                        # New commits since last AI review
                        return True
                return False
        return True
    except Exception:
        return True


def get_last_ai_review(repo_name: str, pr_number: int) -> dict | None:
    """
    Get the last AI review for a PR.
    Returns dict with 'state' (APPROVED/CHANGES_REQUESTED/COMMENTED) and 'body'.
    """
    repo = _get_client().get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    try:
        reviews = list(pr.get_reviews())
        for review in reversed(reviews):
            if review.body and "[AI-Reviewer]" in review.body:
                return {
                    "state": review.state,
                    "body": review.body,
                    "submitted_at": review.submitted_at,
                }
        return None
    except Exception:
        return None


def is_pr_approved(repo_name: str, pr_number: int) -> bool:
    """Check if PR has been approved by AI reviewer."""
    review = get_last_ai_review(repo_name, pr_number)
    if review is None:
        return False
    return review["state"] == "APPROVED"


def get_reviewer_feedback(repo_name: str, pr_number: int) -> str | None:
    """
    Get feedback from the last AI review if it requested changes.
    Returns None if approved or no review.
    """
    review = get_last_ai_review(repo_name, pr_number)
    if review is None:
        return None
    if review["state"] != "CHANGES_REQUESTED":
        return None
    return review["body"]


def find_pr_number_for_issue(repo_name: str, issue_number: int) -> int | None:
    """Find PR number for a given issue (by branch name pattern)."""
    branch_name = f"code-agent/issue-{issue_number}"
    repo = _get_client().get_repo(repo_name)
    owner = repo.full_name.split("/")[0]
    head = f"{owner}:{branch_name}"

    pulls = repo.get_pulls(state="open", head=head)
    for pr in pulls:
        return pr.number
    return None
