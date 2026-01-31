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
# Simple mode: coding only
python coding_runner.py --repo owner/repo --issue 123

# Full cycle: coding + review loop (until APPROVE or max iterations)
python runner.py --repo owner/repo --issue 123

# Process all open issues
python runner.py --repo owner/repo
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
TOKEN_GITHUB=ghp_your_token_here
TOKEN_REVIEWER_GITHUB=ghp_reviewer_token_here  # Optional: separate token for reviewer
REVIEWER_USERNAME_GITHUB=ai-reviewer-bot       # Optional: auto-request reviews

# Repository clone path
REPO_PATH_GITHUB=/tmp/clone_repo

# LLM Configuration
LLM_NAME=openai/gpt-4o-mini
URL_LLM=https://api.openai.com/v1
APIKEY_LLM=sk-your-api-key
```

### 3. GitHub Token Permissions

Required scopes:
- `repo` - Full repository access
- `workflow` - For CI status checks

## GitHub Actions Integration

### Reviewer Agent in CI/CD

Add to your repository's `.github/workflows/ai-coding-cycle.yml`:



### Secrets Required

Add these secrets to your repository:
- `TOKEN_GITHUB` - GitHub token with repo access
- `APIKEY_LLM` - API key for LLM provider
- `LLM_NAME` (optional) - Model name (e.g., `openai/gpt-4o-mini`)
- `URL_LLM` (optional) - LLM API URL

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
│   ├── filesystem.py      # File ops, git, linting, clone_repo, checkout_branch
│   ├── github.py          # GitHub API for coding agent
│   ├── reviewer.py        # GitHub API for reviewer agent
│   └── search.py          # Web search
├── .github/workflows/
│   └── *.yml.example      # Example workflows for other repos
├── runner.py              # Full cycle: coding + review loop
├── coding_runner.py       # Coding agent only
├── reviewer_runner.py     # Reviewer agent only
├── config.py              # Configuration & secrets
├── cli.py                 # CLI: parse_coding_args, parse_reviewer_args
├── Dockerfile             # Docker image
├── docker-compose.yml     # Docker compose
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