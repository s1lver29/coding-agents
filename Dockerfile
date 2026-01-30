FROM python:3.12-slim

WORKDIR /app

# Install git (needed for cloning repos and git operations)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configure git for commits
RUN git config --global user.email "coding-agent@example.com" \
    && git config --global user.name "Coding Agent"

# Copy project files
COPY pyproject.toml README.md ./
COPY agents/ ./agents/
COPY tools/ ./tools/
COPY *.py ./

# Install dependencies
RUN pip install --no-cache-dir -e .

# Default command - show help
CMD ["python", "runner.py", "--help"]
