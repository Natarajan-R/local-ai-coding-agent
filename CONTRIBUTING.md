# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

## Running the checks

```bash
make test      # pytest (unit tests need neither Ollama nor Docker)
make lint      # ruff
```

Integration tests that require a running Ollama server are marked and skipped
automatically when it is not reachable.

## Guidelines

- Keep the guardrails strict: any new tool that touches the filesystem must go
  through `SecurityPolicy.validate_path`; anything that runs a shell command must
  go through `SecurityPolicy.approve_command`.
- New tools are registered in `ToolRegistry._register_core_tools` with a JSON
  schema and must return a `ToolResult`.
- Add a unit test for every new pure component (parser, guardrail, patcher).
- Prefer the smallest change that solves the problem; match the surrounding style.

## Adding a benchmark

Drop a module in `benchmarks/tasks/` that exposes:

```python
TASK = "natural-language task description"
FILES = {"path.py": "initial content"}   # optional seed files

def check(workspace) -> bool:
    ...  # return True if solved
```

Run it with `ai-agent bench`.
