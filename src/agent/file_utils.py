"""Workspace file-system helpers (test/source discovery, target guessing)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional


class FileSystemHelper:
    """Helper for file system operations."""

    TEST_PATTERNS = ("test_*.py", "*_test.py", "*.spec.js", "*.test.js")
    EXCLUDED_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", "target", "dist", "build"}
    SOURCE_EXTENSIONS = (".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".rb")
    CONFIG_EXTENSIONS = (".json", ".yaml", ".yml", ".toml", ".cfg", ".ini")
    DOC_EXTENSIONS = (".md", ".txt", ".rst")
    ALL_EXTENSIONS = SOURCE_EXTENSIONS + CONFIG_EXTENSIONS + DOC_EXTENSIONS

    @staticmethod
    def find_test_files(workspace: Path) -> List[str]:
        """Find test files in the workspace."""
        test_files = []
        for pattern in FileSystemHelper.TEST_PATTERNS:
            for p in workspace.rglob(pattern):
                if FileSystemHelper._is_excluded(p, workspace):
                    continue
                test_files.append(p.relative_to(workspace).as_posix())
        return sorted(test_files)

    @staticmethod
    def find_source_files(workspace: Path) -> List[Path]:
        """Find source files in the workspace."""
        candidates = []
        for ext in FileSystemHelper.SOURCE_EXTENSIONS:
            pattern = f"*{ext}"
            for p in workspace.rglob(pattern):
                if FileSystemHelper._is_excluded(p, workspace):
                    continue
                name_lower = p.name.lower()
                if "test" in name_lower or "spec" in name_lower:
                    continue
                candidates.append(p)
        return candidates

    @staticmethod
    def find_target_file(workspace: Path) -> Optional[str]:
        """Guess the single file an edit should target."""
        solution_path = workspace / "solution.py"
        if solution_path.exists():
            return "solution.py"

        candidates = FileSystemHelper.find_source_files(workspace)

        if len(candidates) == 1:
            return candidates[0].relative_to(workspace).as_posix()
        return None

    @staticmethod
    def find_relevant_test(workspace: Path, target_path: str) -> Optional[Path]:
        """Find the test file relevant to a given source file."""
        try:
            path_obj = Path(target_path)
            stem = path_obj.stem

            possible_tests = [
                workspace / f"{stem}_test.py",
                workspace / f"test_{stem}.py",
                workspace / f"{stem}.test.py",
                workspace / f"{stem}.spec.js",
                workspace / f"{stem}.test.js",
            ]

            for candidate in possible_tests:
                if candidate.exists():
                    return candidate

            parent = path_obj.parent
            for test_file in FileSystemHelper.find_test_files(workspace):
                test_path = workspace / test_file
                if test_path.parent == parent:
                    return test_path

            return None

        except Exception:
            return None

    @staticmethod
    def _is_excluded(path: Path, workspace: Path) -> bool:
        """Check if a path should be excluded."""
        try:
            parts = path.relative_to(workspace).parts
            return any(excl in parts for excl in FileSystemHelper.EXCLUDED_DIRS)
        except ValueError:
            return True
