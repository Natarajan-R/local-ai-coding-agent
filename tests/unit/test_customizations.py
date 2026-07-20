import pytest
from pathlib import Path
from agent.customizations import CustomizationLoader, parse_frontmatter


def test_parse_frontmatter():
    content = """---
name: my_skill
triggers: hello, world
description: "A simple test skill"
---
Instruction content goes here.
Multi-line instruction content.
"""
    metadata, body = parse_frontmatter(content)
    assert metadata == {
        "name": "my_skill",
        "triggers": "hello, world",
        "description": "A simple test skill"
    }
    assert body == "Instruction content goes here.\nMulti-line instruction content."


def test_parse_frontmatter_no_frontmatter():
    content = "Some regular text content without frontmatter."
    metadata, body = parse_frontmatter(content)
    assert metadata == {}
    assert body == content


def test_load_rules_missing(workspace):
    loader = CustomizationLoader(workspace)
    assert loader.load_rules() == []


def test_load_rules_present(workspace):
    agents_dir = workspace / ".agents"
    agents_dir.mkdir()
    agents_file = agents_dir / "AGENTS.md"
    agents_file.write_text("Rule 1: Always write tests.\nRule 2: Keep it clean.", encoding="utf-8")

    loader = CustomizationLoader(workspace)
    rules = loader.load_rules()
    assert len(rules) == 1
    assert "Rule 1: Always write tests." in rules[0]


def test_load_skills(workspace):
    skills_dir = workspace / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    
    # Skill 1 (Matched by name)
    skill1_dir = skills_dir / "deploy"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text("""---
name: deploy_service
triggers: deployment, staging
---
Instructions for deploying the service.
""", encoding="utf-8")

    # Skill 2 (Matched by trigger)
    skill2_dir = skills_dir / "lint"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text("""---
name: check_syntax
triggers: run ruff, check code syntax
---
Instructions for running syntax check.
""", encoding="utf-8")

    # Skill 3 (Not matched)
    skill3_dir = skills_dir / "db"
    skill3_dir.mkdir()
    (skill3_dir / "SKILL.md").write_text("""---
name: database_migration
triggers: migration, schema
---
Instructions for db migration.
""", encoding="utf-8")

    loader = CustomizationLoader(workspace)
    
    # 1. Match by name
    skills = loader.load_skills("deploy_service and setup logs")
    assert len(skills) == 1
    assert "Instructions for deploying the service." in skills[0]

    # 2. Match by trigger
    skills = loader.load_skills("Please run ruff on my files")
    assert len(skills) == 1
    assert "Instructions for running syntax check." in skills[0]

    # 3. Match both
    skills = loader.load_skills("deploy_service and run ruff")
    assert len(skills) == 2
    assert any("Instructions for deploying the service." in s for s in skills)
    assert any("Instructions for running syntax check." in s for s in skills)

    # 4. No matches
    skills = loader.load_skills("Do a git commit")
    assert len(skills) == 0
