import asyncio
import sys
import time
from pathlib import Path

# Insert project paths
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent.cli.bench import _load_tasks
from agent.orchestrator import Orchestrator

# Configuration
MODEL = "gemma4:31b-cloud"
MAX_RETRIES = 4
BATCH_SIZE = 5
WORKSPACE = Path(__file__).resolve().parents[1] / "workspace"

async def run_single_task(name, module):
    task_ws = WORKSPACE / "bench" / name
    task_ws.mkdir(parents=True, exist_ok=True)
    
    # Write initial files
    for fname, content in getattr(module, "FILES", {}).items():
        (task_ws / fname).write_text(content, encoding="utf-8")
        
    print(f"\n🚀 Running task: {name}...")
    orchestrator = Orchestrator(
        workspace=task_ws,
        model_name=MODEL,
        interactive=False,
        planner_editor=True,
        max_retries=MAX_RETRIES
    )
    
    try:
        # Run orchestrator task
        await orchestrator.run_task(module.TASK, stream=False)
        # Check result
        passed = bool(module.check(task_ws))
    except Exception as exc:
        print(f"❌ Error during execution of {name}: {exc}")
        passed = False
        
    status = "PASS" if passed else "FAIL"
    print(f"📊 Task {name} Result: {status}")
    return passed

async def main():
    # Load tasks and filter only Exercism tasks
    all_tasks = _load_tasks()
    exercism_tasks = [t for t in all_tasks if t[0].startswith("Exercism_")]
    
    if not exercism_tasks:
        print("No Exercism tasks found in benchmarks/tasks/")
        return
        
    total_tasks = len(exercism_tasks)
    print(f"Total Exercism Tasks loaded: {total_tasks}")
    print(f"Running in batches of {BATCH_SIZE} using model '{MODEL}' (Max Retries: {MAX_RETRIES})")
    
    completed_results = {
        "Exercism_affine-cipher": False,
        "Exercism_beer-song": False,
        "Exercism_book-store": True,
        "Exercism_bottle-song": True,
        "Exercism_bowling": False,
        "Exercism_connect": False,
        "Exercism_dominoes": True,
        "Exercism_dot-dsl": False,
        "Exercism_food-chain": False,
        "Exercism_forth": False
    }
    
    results = dict(completed_results)
    
    # Split into batches
    for i in range(0, total_tasks, BATCH_SIZE):
        batch = exercism_tasks[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
        # Check if entire batch is already completed
        if all(name in completed_results for name, _ in batch):
            print(f"\n⏭️ Skipping Batch {batch_num} (all tasks completed)")
            continue
            
        print(f"\n==================================================")
        print(f"🔔 STARTING BATCH {batch_num} ({len(batch)} tasks)")
        print(f"==================================================")
        
        for name, module in batch:
            if name in completed_results:
                print(f"⏭️ Skipping completed task: {name}")
                continue
            passed = await run_single_task(name, module)
            results[name] = passed
            
        # Cooling down between batches
        if i + BATCH_SIZE < total_tasks:
            print("\n⏳ Batch complete. Cooling down for 10 seconds before next batch...")
            time.sleep(10)
            
    # Print Grand Summary
    print("\n==================================================")
    print("🏆 FINAL BENCHMARK SUMMARY")
    print("==================================================")
    passed_count = sum(1 for k, v in results.items() if v)
    failed_count = total_tasks - passed_count
    
    for name, passed in sorted(results.items()):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
        
    pass_rate = (passed_count / total_tasks) * 100
    print(f"\n⭐ Pass Rate: {passed_count}/{total_tasks} ({pass_rate:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
