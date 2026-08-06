"""Offline Distillation pipeline (Map-Reduce) for massive codebases."""
import asyncio
import json
import logging
from pathlib import Path
from typing import List

from rich.console import Console
from rich.progress import Progress

from ..model.client import OllamaClient

logger = logging.getLogger(__name__)
console = Console()

# The prompt used for mapping an individual file.
MAP_PROMPT = (
    "You are an expert code reviewer. Read the following file and provide a concise, "
    "3-bullet-point review highlighting its primary responsibility, any architectural "
    "flaws, and potential bugs. Do not include introductory text or markdown wrappers, "
    "just the 3 bullet points."
)

# The prompt used for reducing the aggregated summaries.
REDUCE_PROMPT = (
    "You are a Principal Engineer. Review the following file-level summaries and "
    "synthesize them into a single, comprehensive Project Code Review Document. "
    "Structure it with an Executive Summary, Key Responsibilities by Module, "
    "Architectural Flaws, and Security/Bug Risks. Format as Markdown."
)


async def _process_file(
    file_path: Path,
    workspace: Path,
    client: OllamaClient,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Read a single file and generate its 3-bullet summary via LLM."""
    async with semaphore:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return {"file": str(file_path.relative_to(workspace)), "summary": f"Failed to read: {e}"}

        if not content.strip():
            return {"file": str(file_path.relative_to(workspace)), "summary": "Empty file."}

        messages = [
            {"role": "system", "content": MAP_PROMPT},
            {"role": "user", "content": f"File: {file_path.name}\n\n```\n{content}\n```"}
        ]
        
        try:
            # We don't need large context for the output, just 3 bullets.
            client.options["num_predict"] = 256
            resp = await client.chat(messages=messages)
            summary = resp.content.strip()
        except Exception as e:
            summary = f"LLM error: {e}"

        return {"file": str(file_path.relative_to(workspace)), "summary": summary}


async def run_distillation(
    workspace: Path,
    model: str,
    host: str,
    output_file: str,
    concurrency: int = 5
) -> None:
    """Execute the Map-Reduce distillation pipeline."""
    # 1. Discover target files (exclude hidden, .venv, sandbox, tests)
    target_files: List[Path] = []
    for path in workspace.rglob("*.py"):
        parts = path.parts
        if any(p.startswith(".") for p in parts) or "sandbox" in parts or "tests" in parts:
            continue
        if path.name == "__init__.py":
            continue
        target_files.append(path)

    if not target_files:
        console.print("[red]No Python files found for distillation.[/red]")
        return

    console.print(f"[bold green]Starting Map Phase on {len(target_files)} files...[/bold green]")
    
    # 2. Map Phase
    results = []
    semaphore = asyncio.Semaphore(concurrency)
    
    async with OllamaClient(model_name=model, host=host, timeout=120.0) as client:
        # Increase the context slightly for reading files during map phase
        client.options["num_ctx"] = 8192
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Distilling files...", total=len(target_files))
            
            # Create tasks
            coros = [_process_file(p, workspace, client, semaphore) for p in target_files]
            
            for coro in asyncio.as_completed(coros):
                res = await coro
                results.append(res)
                progress.advance(task)

    # Save intermediate map state
    map_output = workspace / "distillation_map.json"
    map_output.write_text(json.dumps(results, indent=2))
    console.print(f"[green]Map phase complete. Saved to {map_output}[/green]")

    # 3. Reduce Phase
    console.print("[bold green]Starting Reduce Phase...[/bold green]")
    aggregated_text = ""
    for r in results:
        aggregated_text += f"### {r['file']}\n{r['summary']}\n\n"

    async with OllamaClient(model_name=model, host=host, timeout=1800.0) as client:
        # Maximize context for the reduce phase
        client.options["num_ctx"] = 32768
        client.options["num_predict"] = 2048
        
        messages = [
            {"role": "system", "content": REDUCE_PROMPT},
            {"role": "user", "content": f"Aggregated Summaries:\n\n{aggregated_text}"}
        ]
        
        try:
            resp = await client.chat(messages=messages)
            final_review = resp.content.strip()
        except Exception as e:
            console.print(f"[red]Reduce phase failed: {e}[/red]")
            return

    # 4. Output
    out_path = workspace / output_file
    out_path.write_text(final_review, encoding="utf-8")
    console.print(f"[bold green]Success! Code Review Document saved to {out_path}[/bold green]")
