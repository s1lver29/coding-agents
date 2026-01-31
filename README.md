# Coding Agents

AI-powered agents for automated software development and code review.

## Agents

### 1. Coding Agent
Autonomous coding agent that:
- Reads GitHub issues and implements solutions
- Makes code changes, runs linting/tests
- Creates Pull Requests
- Responds to reviewer feedback

```bash
# Run for all open issues
python runner.py --repo owner/repo

# Run for specific issue
python runner.py --repo owner/repo --issue 123
```

### 2. Reviewer Agent
AI code reviewer that:
- Analyzes code changes in Pull Requests
- Checks CI/CD job results
- Compares implementation with issue requirements
- Submits reviews (Approve / Request Changes / Comment)

```bash
# Review specific PR
python reviewer_runner.py --repo owner/repo --pr 123

# Review all open PRs
python reviewer_runner.py --repo owner/repo --all

# Force re-review
python reviewer_runner.py --repo owner/repo --pr 123 --force
```

## Setup

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Configure environment

Create `.env` file:

```env
# GitHub tokens
GITHUB_TOKEN=ghp_your_token_here
GITHUB_TOKEN_REVIEWER=ghp_reviewer_token_here  # Optional: separate token for reviewer agent
GITHUB_REVIEWER_USERNAME=ai-reviewer-bot       # Optional: username to auto-request reviews

# Repository clone path
GITHUB_REPO_PATH=/tmp/clone_repo

# LLM Configuration
LLM_NAME=openai/gpt-4o-mini
URL_LLM=https://api.openai.com/v1
APIKEY_LLM=sk-your-api-key
```

## Docker

Docker Compose uses a single `agent` service and runs only `runner.py` (full coding + review cycle).

### Quick start (docker-compose)

1) Create a `.env` file next to `docker-compose.yml`:

```env
TOKEN_GITHUB=ghp_your_token_here
TOKEN_REVIEWER_GITHUB=ghp_reviewer_token_here  # optional
REVIEWER_USERNAME_GITHUB=ai-reviewer-bot       # optional

LLM_NAME=openai/gpt-4o-mini
URL_LLM=https://api.openai.com/v1
APIKEY_LLM=sk-your-api-key

REPO_NAME=owner/repo
REPO_PATH_GITHUB=/tmp/clone_repo
GITHUB_BASE_BRANCH=main
```

2) Run the full cycle (coding + review):

```bash
docker compose up --build agent
```

3) For running `coding_runner.py` or `reviewer_runner.py` separately, use `docker run`.

### One-off run (docker run)

```bash
docker build -t coding-agents .

docker run --rm \
	-e TOKEN_GITHUB=ghp_your_token_here \
	-e LLM_NAME=openai/gpt-4o-mini \
	-e URL_LLM=https://api.openai.com/v1 \
	-e APIKEY_LLM=sk-your-api-key \
	-e REPO_PATH_GITHUB=/tmp/clone_repo \
	-v coding_agents_repos:/tmp/clone_repo \
	coding-agents \
	python runner.py --repo owner/repo
```

### 3. GitHub Token Permissions

Required scopes:
- `repo` - Full repository access
- `workflow` - For CI status checks

## GitHub Actions Integration

### Reviewer Agent in CI/CD

Add to your repository's `.github/workflows/ai-review.yml`:

### Secrets Required

You need a GitHub token with the following permissions:
- Read access to issues
- Write access to pull requests
- Write access to workflows
Add these secrets to your repository:
- `APIKEY_LLM` - API key for LLM provider
- `LLM_NAME` - Model name
- `URL_LLM` - LLM API URL
- `GITHUB_TOKEN` - Token for general GitHub operations
- `GITHUB_TOKEN_REVIEWER` - Token for reviewer operations
- `GITHUB_REVIEWER_USERNAME` - GitHub username of the reviewer

## Project Structure

```
coding-agents/
├── agents/
│   ├── coding_agent/      # Coding agent
│   │   ├── agent.py       # Agent definition & instructions
│   │   └── llm.py         # LLM configuration
│   └── reviewer_agent/    # Reviewer agent
│       ├── agent.py       # Agent definition & instructions
│       └── llm.py         # LLM configuration
├── tools/
│   ├── filesystem.py      # File operations, git, linting
│   ├── github.py          # GitHub API for coding agent
│   ├── reviewer.py        # GitHub API for reviewer agent
│   └── search.py          # Web search
├── .github/workflows/
│   ├── ai-review.yml      # Standalone workflow
│   └── ai-review-reusable.yml  # Reusable workflow
├── runner.py              # Coding agent runner
├── reviewer_runner.py     # Reviewer agent runner
├── config.py              # Configuration & secrets
├── cli.py                 # CLI argument parsing
└── pyproject.toml         # Dependencies
```

## Review Format

The AI Reviewer produces structured reviews:

```markdown
[AI-Reviewer]

## Summary
Brief overview of the PR changes

## Requirements Check
✅ Requirement 1: Implemented correctly
❌ Requirement 2: Not implemented

## CI Status
✅ All checks passing

## Code Quality
Assessment of code quality

## Issues Found
- Issue 1
- Issue 2

## Suggestions
- Optional improvement 1

## Decision: APPROVE/REQUEST_CHANGES
Reasoning for the decision
```

## Development

```bash
# Run linting
ruff check . --fix

# Run type checking
mypy .

# Run tests
pytest
```
