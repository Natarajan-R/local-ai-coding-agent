from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML-like frontmatter between leading '---' lines."""
    metadata = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2].strip()
            # Simple key-value parser for metadata
            for line in frontmatter.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip().lower()] = val.strip().strip('"').strip("'")
    return metadata, body


class CustomizationLoader:
    """Discovers and loads agent skills and rules from workspace customizations."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace)

    def _find_agents_dir(self) -> Path | None:
        curr = self.workspace.resolve()
        for _ in range(5):
            agents_dir = curr / ".agents"
            if agents_dir.is_dir():
                return agents_dir
            if curr.parent == curr:
                break
            curr = curr.parent
        return None

    def load_skills(self, task: str) -> list[str]:
        """Scans workspace/.agents/skills/*/SKILL.md and returns matching instruction bodies."""
        agents_dir = self._find_agents_dir()
        if not agents_dir:
            return []
        skills_dir = agents_dir / "skills"
        if not skills_dir.is_dir():
            return []

        matched_skills = []
        try:
            for subdir in skills_dir.iterdir():
                if not subdir.is_dir():
                    continue
                skill_file = subdir / "SKILL.md"
                if not skill_file.is_file():
                    continue

                try:
                    content = skill_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    logger.warning("Failed to read skill file %s: %s", skill_file, exc)
                    continue

                metadata, body = parse_frontmatter(content)
                name = metadata.get("name", "").lower() or subdir.name.lower()
                triggers_str = metadata.get("triggers", "")
                triggers = [t.strip().lower() for t in triggers_str.split(",") if t.strip()]

                # Match if name or trigger keyword is in the task description
                matched = False
                if name and name in task.lower():
                    matched = True
                elif any(trigger in task.lower() for trigger in triggers):
                    matched = True

                if matched:
                    logger.info("Triggered skill customization: %s", name)
                    matched_skills.append(body)
        except Exception as exc:
            logger.warning("Error scanning workspace skills: %s", exc)

        return matched_skills

    def load_rules(self) -> list[str]:
        """Loads workspace-level instructions from workspace/.agents/AGENTS.md."""
        agents_dir = self._find_agents_dir()
        if not agents_dir:
            return []
        rules_file = agents_dir / "AGENTS.md"
        if not rules_file.is_file():
            return []

        try:
            content = rules_file.read_text(encoding="utf-8")
            logger.info("Loaded workspace-level instructions from AGENTS.md")
            return [content]
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed to read rules file %s: %s", rules_file, exc)
            return []
