# `.agents/references/` — reference implementations for example-RAG

Drop **canonical example files** here and the coder agent will retrieve the most
relevant one(s) into its prompt when it builds a related file. This is opt-in: if
this folder is absent or nothing matches, nothing changes.

## What to put here

Small, **correct, self-contained** example modules that demonstrate a pattern you
want the agent to follow — the shape of an API, the right imports, an idiomatic
async setup, a middleware skeleton. Think "reference", not "library": the agent
reads them as examples to mimic, it does not import them.

Good candidates: a JWT auth module, an async DB service, a router with
dependencies, a middleware class. See the `.py` files already in this folder.

Keep each file focused and under a few hundred lines — only the first ~4000
characters of a matched file are injected.

## How retrieval works

1. **Discovery.** From the workspace, the agent walks *up* to 5 parent directories
   looking for a `.agents/` dir (`CustomizationLoader._find_agents_dir`). So this
   folder can sit in a persistent parent and survive the workspace being recreated
   each run — it does not have to live inside the workspace.
2. **Scoring.** For each file the agent is about to write, it builds a keyword set
   from the target path + the change description, then scores every reference by
   how many of those keywords appear in the reference's name + first 2000 chars
   (`Coder._relevant_references`).
3. **Injection.** The top 1–2 references (score > 0) are placed in the subtask
   prompt under a **REFERENCE IMPLEMENTATION** block. Zero-score references are
   never injected, so an irrelevant example costs nothing.

Because matching is by keyword overlap, **name your files after the domain**
(`fastapi_jwt_auth.py`, `async_sqlalchemy_service.py`) so they surface for the
right target files.

## Related: interface scaffolding (automatic, no setup)

A sibling mechanism, `Coder._required_exports`, reads your **test files** and
extracts the exact classes/functions they import from the module under
construction, then injects them as a **REQUIRED INTERFACE** block. This needs no
files here — it activates whenever tests exist that import from the target module.

## Workspace-file RAG (dynamic, no setup)

Beyond the static references in this folder, the agent now also retrieves **active
workspace files** related to the file being written. This is automatic — no files
to add, no configuration needed.

When writing file X, the agent scans the workspace for other `.py` files and scores
them on three signals:

| Signal | Weight | What it catches |
|--------|--------|-----------------|
| **Import relationship** | +3 | X imports from Y, or Y imports from X — prevents interface mismatches |
| **Test–source pairing** | +2 | ``test_X.py`` for target ``X.py`` (or vice versa) — keeps tests in sync with implementation |
| **Same directory** | +1 | Files in the same package — catches intra-package coupling |

The top 3 matches (up to ~6 KB total) are injected into the subtask prompt as
``# --- related: path/to/file.py ---`` blocks alongside the static references.
Because the retrieval is driven by the actual import graph, it adapts to whatever
the model has already generated in the workspace.

This is implemented in ``src/agent/agents/workspace_rag.py``.

## Related: multi-pass cross-file consistency (post-generation)

A second mechanism runs **after** all milestones complete: the agent statically
analyses every generated file for three classes of structural bug:

1. **Import consistency** — every ``from X import Y`` must have a matching
   ``def Y`` or ``class Y`` in module X.
2. **Route consistency** — every route tested in test files must have a matching
   endpoint in a router file (FastAPI-specific).
3. **Schema consistency** — every field accessed on a model instance in tests
   must exist in the Pydantic schema.

If issues are found, the agent re-runs the milestone loop with them as a
reflexion lesson. This is implemented in ``src/agent/agents/cross_file_checker.py``
and hooked via ``CoderAgent._run_cross_file_pass``.

## What this stack does and does not fix

- **Helps:** correct imports, decorator/framework idioms, boilerplate shape,
  method signatures — the *knowledge* of how a pattern is written.
- **Helps more:** cross-module awareness during generation (workspace RAG brings
  related files into context), and post-generation structural checks (multi-pass
  catches mismatched interfaces, missing routes, missing schema fields).
- **Does not fix:** genuine model reasoning errors — cases where the model
  misunderstands the spec or makes incorrect assumptions about how components
  interact. These are the hardest to automate and require human judgment.
