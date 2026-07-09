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
RUN pip install --no-cache-dir pytest ruff

# Run as an unprivileged user; the workspace is bind-mounted read-write.
RUN useradd --create-home --uid 1000 agent
USER agent

WORKDIR /workspace

CMD ["sleep", "infinity"]
