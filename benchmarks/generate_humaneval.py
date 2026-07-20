import gzip
import json
import urllib.request
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent / "tasks"

TEMPLATE = """\"\"\"HumanEval task {task_id}\"\"\"
from pathlib import Path

TASK = \"\"\"Implement the function '{entry_point}' defined in solution.py. Make the tests pass.

Here is the function signature and docstring:
{prompt}
\"\"\"

FILES = {
    "solution.py": {prompt_repr},
    "test_solution.py": {test_repr}
}

def check(workspace: Path) -> bool:
    import subprocess
    test_code = {test_repr}
    (workspace / "test_solution.py").write_text(test_code, encoding="utf-8")
    res = subprocess.run(["python", "-m", "pytest", "-q", str(workspace / "test_solution.py")])
    return res.returncode == 0
"""

def generate_file(task_id: str, prompt: str, test: str, entry_point: str):
    prompt_str = prompt.replace('"""', '\\"\\"\\"')
    
    content = TEMPLATE.replace("{task_id}", task_id)
    content = content.replace("{entry_point}", entry_point)
    content = content.replace("{prompt}", prompt_str)
    content = content.replace("{prompt_repr}", repr(prompt))
    
    test_code = f"from solution import {entry_point}\n" + test + f"\n\ndef test_candidate():\n    check({entry_point})\n"
    content = content.replace("{test_repr}", repr(test_code))
    
    (TASKS_DIR / f"{task_id}.py").write_text(content, encoding="utf-8")

def download_and_generate():
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    
    url = "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"
    temp_file = Path("HumanEval.jsonl.gz")
    
    print(f"Downloading HumanEval dataset from {url}...")
    try:
        urllib.request.urlretrieve(url, temp_file)
    except Exception as e:
        print(f"Failed to download from GitHub: {e}")
        # Try Hugging Face fallback using the datasets library if installed
        try:
            print("Trying fallback via Hugging Face datasets library...")
            from datasets import load_dataset
            ds = load_dataset("openai_humaneval", split="test")
            count = 0
            for item in ds:
                task_id = item["task_id"].replace("/", "_")
                generate_file(task_id, item["prompt"], item["test"], item["entry_point"])
                count += 1
            print(f"Successfully generated {count} HumanEval tasks using Hugging Face datasets.")
            return
        except Exception as fallback_err:
            print(f"Hugging Face fallback also failed: {fallback_err}")
            return

    print("Generating benchmark files...")
    count = 0
    try:
        with gzip.open(temp_file, "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                task_id = item["task_id"].replace("/", "_")
                generate_file(task_id, item["prompt"], item["test"], item["entry_point"])
                count += 1
        print(f"Successfully generated {count} HumanEval tasks under {TASKS_DIR}")
    finally:
        if temp_file.exists():
            temp_file.unlink()

if __name__ == "__main__":
    download_and_generate()

