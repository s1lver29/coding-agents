from agno.tools import tool
from github import Auth, Github

from config import get_github_token, get_reviewer_username

_gh_client: Github | None = None


def _get_client() -> Github:
    global _gh_client
    if _gh_client is None:
        token = get_github_token()
        if not token:
            raise OSError("GITHUB_TOKEN is not set (config/.env)")
        auth = Auth.Token(token)
        _gh_client = Github(auth=auth)
    return _gh_client


@tool
def get_issue(repo_name: str, issue_number: int) -> str:
    """
    Return the title and body of a GitHub Issue.
    """
    repo = _get_client().get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)
    return f"{issue.title}\n\n{issue.body}"


@tool
def create_pull_request(
    repo_name: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
) -> str:
    """
    Create a Pull Request in GitHub.
    If PR for this branch already exists, returns its URL without creating a new one.
    Returns URL of the PR.
    """
    # Проверяем, существует ли уже PR для этой ветки
    existing_pr = find_pr_for_branch(repo_name, head_branch)
    if existing_pr:
        return f"PR already exists: {existing_pr.html_url}"

    repo = _get_client().get_repo(repo_name)
    pr = repo.create_pull(
        title=title,
        body=body,
        head=head_branch,
        base=base_branch,
    )

    # Auto-request review from configured reviewer
    reviewer_username = get_reviewer_username()
    if reviewer_username:
        try:
            pr.create_review_request(reviewers=[reviewer_username])
        except Exception:
            pass  # Ignore if request fails (e.g., user not found)

    return pr.html_url


@tool
def post_pr_comment_and_request_review(
    repo_name: str,
    issue_number: int,
    comment: str,
) -> str:
    """
    Post a comment to the PR for this issue and request review from those who gave feedback.
    Use this after making changes to notify reviewers.
    """
    branch_name = f"code-agent/issue-{issue_number}"
    pr = find_pr_for_branch(repo_name, branch_name)
    if pr is None:
        return f"No PR found for issue #{issue_number}"

    # Добавляем комментарий
    pr.create_issue_comment(comment)

    # Находим reviewers которые давали CHANGES_REQUESTED
    reviewers_to_request = set()
    try:
        reviews = list(pr.get_reviews())
        for review in reviews:
            if review.state == "CHANGES_REQUESTED":
                reviewers_to_request.add(review.user.login)
    except Exception:
        pass

    # Запрашиваем повторную проверку
    if reviewers_to_request:
        try:
            pr.create_review_request(reviewers=list(reviewers_to_request))
            return f"Comment posted and review requested from: {list(reviewers_to_request)}"
        except Exception as e:
            return f"Comment posted but failed to request review: {e}"

    return "Comment posted. No previous reviewers found to request review from."


@tool
def post_comment(repo_name: str, issue_number: int, comment: str) -> str:
    """
    Post a comment to a GitHub Issue or Pull Request.
    """
    repo = _get_client().get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)
    comment_obj = issue.create_comment(comment)
    return comment_obj.html_url


@tool
def add_labels(repo_name: str, issue_number: int, labels: list[str]) -> str:
    """
    Add labels to a GitHub Issue or Pull Request.
    """
    repo = _get_client().get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)
    issue.add_to_labels(*labels)
    return f"Labels {labels} added to issue #{issue_number}"


# === Helper functions for runner (not tools) ===


def get_open_issues(repo_name: str) -> list:
    """Получить все открытые issues (не PR)."""
    repo = _get_client().get_repo(repo_name)
    issues = repo.get_issues(state="open")
    return [issue for issue in issues if issue.pull_request is None]


def find_pr_for_branch(repo_name: str, branch_name: str):
    """Найти открытый PR по имени ветки. Возвращает None если PR нет или закрыт/смержен."""
    repo = _get_client().get_repo(repo_name)
    owner = repo.full_name.split("/")[0]
    head = f"{owner}:{branch_name}"
    # Ищем только открытые PR
    pulls = repo.get_pulls(state="open", head=head)
    for pr in pulls:
        return pr
    return None


def find_any_pr_for_branch(repo_name: str, branch_name: str):
    """Найти любой PR по имени ветки (включая закрытые и смерженные)."""
    repo = _get_client().get_repo(repo_name)
    owner = repo.full_name.split("/")[0]
    head = f"{owner}:{branch_name}"
    pulls = repo.get_pulls(state="all", head=head)
    for pr in pulls:
        return pr
    return None


def pr_is_closed_or_merged(repo_name: str, issue_number: int) -> bool:
    """Проверить, закрыт или смержен PR для issue."""
    branch_name = f"code-agent/issue-{issue_number}"
    pr = find_any_pr_for_branch(repo_name, branch_name)
    if pr is None:
        return False
    # merged — смержен, closed и не merged — закрыт без мержа
    return pr.merged or pr.state == "closed"


def pr_needs_rework(pr) -> bool:
    """Проверить, есть ли запрос на доработку в PR."""
    if pr is None:
        return False
    # Если PR закрыт или смержен — доработка не нужна
    if pr.merged or pr.state == "closed":
        return False
    try:
        reviews = list(pr.get_reviews())
    except Exception:
        return False
    if not reviews:
        return False
    latest_review = max(reviews, key=lambda r: r.submitted_at or r.id)
    return latest_review.state == "CHANGES_REQUESTED"


def issue_needs_work(repo_name: str, issue_number: int) -> bool:
    """
    Проверить, нужна ли работа по issue:
    - PR закрыт или смержен — работа НЕ нужна
    - Нет открытого PR — работа нужна
    - Есть открытый PR с запросом на доработку — работа нужна
    """
    branch_name = f"code-agent/issue-{issue_number}"

    # Проверяем любой PR (включая закрытые)
    any_pr = find_any_pr_for_branch(repo_name, branch_name)
    if any_pr and (any_pr.merged or any_pr.state == "closed"):
        # PR закрыт или смержен — не трогаем
        return False

    # Ищем открытый PR
    open_pr = find_pr_for_branch(repo_name, branch_name)
    if open_pr is None:
        # Нет открытого PR — нужна работа
        return True

    # Есть открытый PR — проверяем нужна ли доработка
    return pr_needs_rework(open_pr)


def get_pr_feedback(repo_name: str, issue_number: int) -> str | None:
    """
    Получить feedback из PR для issue (reviews и комментарии).
    Возвращает None если PR нет или нет замечаний.
    """
    branch_name = f"code-agent/issue-{issue_number}"
    pr = find_pr_for_branch(repo_name, branch_name)
    if pr is None:
        return None

    result = []

    # Reviews
    try:
        reviews = list(pr.get_reviews())
        for review in reviews:
            if review.state == "CHANGES_REQUESTED" and review.body:
                result.append(f"[Review from {review.user.login}]: {review.body}")
    except Exception:
        pass

    # Review comments (inline comments on code)
    try:
        review_comments = list(pr.get_review_comments())
        for comment in review_comments:
            result.append(
                f"[Code comment from {comment.user.login} on {comment.path} line {comment.line}]: {comment.body}"
            )
    except Exception:
        pass

    # Issue comments (general PR comments)
    try:
        issue_comments = list(pr.get_issue_comments())
        for comment in issue_comments:
            result.append(f"[Comment from {comment.user.login}]: {comment.body}")
    except Exception:
        pass

    if not result:
        return None

    return "\n".join(result)
