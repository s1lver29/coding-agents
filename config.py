import os

from dotenv import load_dotenv

load_dotenv()


def get_github_token() -> str | None:
    return os.getenv("TOKEN_GITHUB")


def get_github_reviewer_token() -> str | None:
    """Get reviewer token, falls back to main token if not set."""
    return os.getenv("TOKEN_REVIEWER_GITHUB") or os.getenv("TOKEN_GITHUB")


def get_reviewer_username() -> str | None:
    """Get username of the reviewer to request reviews from."""
    return os.getenv("REVIEWER_USERNAME_GITHUB")


def get_repo_path() -> str:
    return os.getenv("REPO_PATH_GITHUB", "/tmp/clone_repo")


def get_llm_info() -> dict[str, str]:
    info_llm = {
        "id": os.getenv("LLM_NAME", "LLM_NAME"),
        "base_url": os.getenv("URL_LLM", "URL_LLM"),
        "api_key": os.getenv("APIKEY_LLM", "APIKEY_LLM"),
    }

    return info_llm
