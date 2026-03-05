"""Skills Manager — browse, toggle, create, delete OpenClaw skills."""
import os
import re
import json
import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)
router = APIRouter()

WORKSPACE_SKILLS = Path("/openclaw-workspace/skills")
BUNDLED_SKILLS = Path("/openclaw-bundled-skills")
CONFIG_PATH = Path("/openclaw/openclaw.json")


def _read_config():
    try:
        return json.loads(CONFIG_PATH.read_text())
    except:
        return {}


def _write_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def _parse_skill_md(skill_path: Path):
    """Parse SKILL.md frontmatter for name, description."""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.exists():
        return {"name": skill_path.name, "description": ""}
    
    content = skill_file.read_text(errors="replace")
    name = skill_path.name
    description = ""
    
    # Parse YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            frontmatter = content[3:end]
            for line in frontmatter.split("\n"):
                if line.strip().startswith("name:"):
                    name = line.split(":", 1)[1].strip().strip("'\"")
                elif line.strip().startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip("'\"")
                    if desc:
                        description = desc[:200]
    
    if not description:
        # Get first non-empty line after frontmatter
        body = content.split("---", 2)[-1].strip() if "---" in content else content
        for line in body.split("\n"):
            line = line.strip().lstrip("#").strip()
            if line and len(line) > 10:
                description = line[:200]
                break
    
    return {"name": name, "description": description}


def _scan_skills():
    config = _read_config()
    entries = config.get("skills", {}).get("entries", {})
    skills = []
    
    # Scan workspace skills
    if WORKSPACE_SKILLS.exists():
        for d in sorted(WORKSPACE_SKILLS.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                meta = _parse_skill_md(d)
                enabled = entries.get(d.name, {}).get("enabled", True) if d.name in entries else True
                skills.append({
                    "id": d.name,
                    "name": meta["name"],
                    "description": meta["description"],
                    "source": "workspace",
                    "enabled": enabled,
                    "path": str(d),
                })
    
    # Scan bundled skills
    if BUNDLED_SKILLS.exists():
        for d in sorted(BUNDLED_SKILLS.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                meta = _parse_skill_md(d)
                enabled = entries.get(d.name, {}).get("enabled", True) if d.name in entries else True
                skills.append({
                    "id": d.name,
                    "name": meta["name"],
                    "description": meta["description"],
                    "source": "bundled",
                    "enabled": enabled,
                    "path": str(d),
                })
    
    return skills


@router.get("/skills")
async def list_skills():
    return _scan_skills()


@router.post("/skills/{skill_id}/toggle")
async def toggle_skill(skill_id: str, body: dict = {}):
    config = _read_config()
    config.setdefault("skills", {}).setdefault("entries", {})
    current = config["skills"]["entries"].get(skill_id, {}).get("enabled", True)
    new_state = body.get("enabled", not current)
    config["skills"]["entries"][skill_id] = {**config["skills"]["entries"].get(skill_id, {}), "enabled": new_state}
    _write_config(config)
    skill = next((s for s in _scan_skills() if s["id"] == skill_id), None)
    return skill or {"id": skill_id, "enabled": new_state}


class CreateSkillRequest(BaseModel):
    name: str
    description: str = ""
    instructions: str = ""

@router.post("/skills/create")
async def create_skill(req: CreateSkillRequest):
    if not req.name:
        raise HTTPException(status_code=400, detail="Name required")
    skill_dir = WORKSPACE_SKILLS / req.name
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = f"---\nname: {req.name}\ndescription: {req.description}\n---\n\n{req.instructions}"
    (skill_dir / "SKILL.md").write_text(md)
    skill = next((s for s in _scan_skills() if s["id"] == req.name and s["source"] == "workspace"), None)
    return skill or {"id": req.name, "name": req.name, "source": "workspace"}


@router.get("/skills/{skill_id}/content")
async def get_skill_content(skill_id: str):
    all_skills = _scan_skills()
    skill = next((s for s in all_skills if s["id"] == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill_file = Path(skill["path"]) / "SKILL.md"
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail="No SKILL.md")
    return {"content": skill_file.read_text(errors="replace")}


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str):
    all_skills = _scan_skills()
    skill = next((s for s in all_skills if s["id"] == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill["source"] != "workspace":
        raise HTTPException(status_code=403, detail="Can only delete workspace skills")
    shutil.rmtree(skill["path"], ignore_errors=True)
    return {"ok": True}