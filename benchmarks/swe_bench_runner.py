import sys
import os
import json
import shutil
import asyncio
import subprocess
from pathlib import Path

# Configure paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agent.orchestrator import Orchestrator

def run_command(cmd: str, cwd: Path) -> subprocess.CompletedProcess:
    print(f"Executing: {cmd} in {cwd}")
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python benchmarks/swe_bench_runner.py <instance_json_path> [model_name]")
        sys.exit(1)
        
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"Error: file not found: {json_path}")
        sys.exit(1)
        
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5:7b"
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    instance_id = data["instance_id"]
    repo = data["repo"]
    base_commit = data["base_commit"]
    problem_statement = data["problem_statement"]
    test_patch = data.get("test_patch", "")
    test_command = data.get("test_command", "pytest")
    
    workspace_dir = PROJECT_ROOT / "workspace" / "swe_bench" / instance_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n==================================================")
    print(f"🎬 Starting SWE-bench Harness: {instance_id}")
    print(f"==================================================")
    
    # 1. Clone repository if not already present
    if not (workspace_dir / ".git").exists():
        github_url = f"https://github.com/{repo}.git"
        print(f"Cloning {github_url} into {workspace_dir}...")
        # Clean any partial directory
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        res = subprocess.run(["git", "clone", github_url, str(workspace_dir)], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error cloning repository: {res.stderr}")
            sys.exit(1)
            
    # 2. Checkout correct base commit and clean workspace
    print(f"Checking out base commit {base_commit}...")
    run_command("git reset --hard", workspace_dir)
    run_command("git clean -fd", workspace_dir)
    res = run_command(f"git checkout {base_commit}", workspace_dir)
    if res.returncode != 0:
        print(f"Error checking out base commit: {res.stderr}")
        sys.exit(1)
        
    # 3. Apply test patch
    if test_patch:
        print("Applying test patch (regression tests)...")
        patch_file = workspace_dir / "temp_test_patch.patch"
        patch_file.write_text(test_patch, encoding="utf-8")
        res = run_command("git apply temp_test_patch.patch", workspace_dir)
        # remove temp file
        if patch_file.exists():
            patch_file.unlink()
        if res.returncode != 0:
            print(f"Warning: git apply failed: {res.stderr}. Attempting fuzzy patch...")
            # fallback to git apply with --reject or --3way
            res = run_command("git apply --3way temp_test_patch.patch", workspace_dir)
            
    # 4. Instantiate Orchestrator and solve problem
    print(f"\n🚀 Launching Agent to solve issue...")
    print(f"Task: {problem_statement}")
    
    orchestrator = Orchestrator(
        workspace=workspace_dir,
        model_name=model,
        interactive=False,
        planner_editor=True,
        max_retries=2
    )
    
    try:
        await orchestrator.run_task(problem_statement, stream=False)
    except Exception as exc:
        print(f"❌ Error during agent execution: {exc}")
        
    # 5. Run test command to evaluate solution
    print(f"\n📊 Evaluating agent solution...")
    res = run_command(test_command, workspace_dir)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
        
    passed = res.returncode == 0
    status = "SUCCESS (PASS)" if passed else "FAILURE (FAIL)"
    print(f"\n==================================================")
    print(f"🏁 SWE-bench Result for {instance_id}: {status}")
    print(f"==================================================")
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    asyncio.run(main())
