# Sandbox image for the AI coding agent.
# Build with:  ai-agent build-sandbox      (or: docker build -t ai-agent-sandbox:latest src/agent/sandbox)
FROM python:3.12-slim

# Common tooling plus Node.js so the language-agnostic evaluator can run
# `npm test` for JavaScript/TypeScript projects. Extend this list for other
# ecosystems (Go, Rust, JDK) as needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        curl \
        ca-certificates \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

# Test / lint tooling available to evaluation runs.
#
# Networking is disabled inside the sandbox at runtime, so whatever a project needs
# to import must already be here -- the agent cannot pip install its way out. Two
# failures traced back to exactly that: demo 05's async tests could not collect
# without pytest-asyncio, and running the agent on its own repo failed to collect 18
# modules for want of rich and httpx, so evaluation judged the agent against a suite
# that was red before it started.
#
# pytest-asyncio, rich and httpx are the common cases; a project with heavier
# dependencies still needs either a custom image or --test-command to scope
# evaluation to the tests that matter.
RUN pip install --no-cache-dir pytest pytest-asyncio ruff rich httpx pydantic

# Run as an unprivileged user; the workspace is bind-mounted read-write.
RUN useradd --create-home --uid 1000 agent
USER agent

WORKDIR /workspace

CMD ["sleep", "infinity"]
