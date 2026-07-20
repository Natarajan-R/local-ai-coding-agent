import sys
from pathlib import Path

# Paths
WORKSPACE = Path(__file__).resolve().parent.parent
TASKS_DIR = WORKSPACE / "benchmarks" / "tasks"
POLYGLOT_DIR = Path("/home/natarajan/book04/aider_bench/aider/tmp.benchmarks/polyglot-benchmark/python/exercises/practice")

TEMPLATE = """\"\"\"Exercism task {task_name}\"\"\"
from pathlib import Path

TASK = \"\"\"Implement the solution defined in {stub_name}. Make the tests pass.

Instructions:
{instructions}
\"\"\"

FILES = {{
    "{stub_name}": {stub_repr},
    "{test_name}": {test_repr}
}}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = {test_repr}
    (workspace / "{test_name}").write_text(test_code, encoding="utf-8")
    try:
        res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "{test_name}")], timeout=15)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
"""

def generate_tasks():
    if not POLYGLOT_DIR.exists():
        print(f"Error: polyglot-benchmark practice directory not found at {POLYGLOT_DIR}")
        return

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for item in sorted(POLYGLOT_DIR.iterdir()):
        if not item.is_dir():
            continue
        task_name = item.name
        
        # Read instructions
        instructions_file = item / ".docs" / "instructions.md"
        instructions = ""
        if instructions_file.exists():
            instructions = instructions_file.read_text(encoding="utf-8")
            
        # Find stub and test files
        stub_file = None
        test_file = None
        
        for p in item.glob("*.py"):
            if p.name.endswith("_test.py") or p.name.startswith("test_"):
                test_file = p
            else:
                stub_file = p
                
        if not stub_file or not test_file:
            continue
            
        stub_name = stub_file.name
        test_name = test_file.name
        
        stub_content = stub_file.read_text(encoding="utf-8")
        test_content = test_file.read_text(encoding="utf-8")
        
        # Format code to avoid escaping issues
        content = TEMPLATE.format(
            task_name=f"Exercism_{task_name}",
            stub_name=stub_name,
            test_name=test_name,
            instructions=instructions,
            stub_repr=repr(stub_content),
            test_repr=repr(test_content)
        )
        
        target_path = TASKS_DIR / f"Exercism_{task_name}.py"
        target_path.write_text(content, encoding="utf-8")
        count += 1
        
    print(f"Successfully generated {count} Exercism tasks under {TASKS_DIR}")

if __name__ == "__main__":
    generate_tasks()
