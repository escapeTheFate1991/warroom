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


CATEGORY_PATTERNS = {
    "development": ["code", "developer", "coding", "debug", "refactor", "typescript", "javascript", "python", "react",
                     "next", "angular", "vue", "svelte", "node", "fastapi", "django", "flask", "rust", "go-",
                     "java-", "kotlin", "swift", "flutter", "android", "ios", "mobile", "frontend", "backend",
                     "fullstack", "full-stack", "api-", "graphql", "rest-", "database", "postgres", "mongo",
                     "redis", "prisma", "orm", "sql", "git", "github", "testing", "jest", "pytest", "cypress",
                     "playwright", "webpack", "vite", "tailwind", "css-", "html-", "arm-cortex", "embedded",
                     "firmware", "clean-code", "architecture", "solid-", "design-pattern"],
    "devops": ["docker", "kubernetes", "k8s", "terraform", "aws-", "azure-", "gcp-", "cloud", "ci-cd", "cicd",
               "deploy", "infrastructure", "monitoring", "observability", "nginx", "linux", "server",
               "pipeline", "helm", "ansible", "vagrant"],
    "ai-ml": ["ai-", "ml-", "llm", "agent", "rag", "embedding", "vector", "prompt", "model",
              "openai", "anthropic", "langchain", "langgraph", "crewai", "autogen", "mcp",
              "machine-learning", "deep-learning", "neural", "transformer", "fine-tun"],
    "security": ["security", "pentest", "exploit", "vulnerability", "owasp", "auth-", "hack",
                 "forensic", "malware", "reverse-eng", "crypto-", "encryption", "firewall",
                 "active-directory", "fuzzing", "bug-bounty"],
    "marketing": ["marketing", "seo", "content-", "social-media", "copywrite", "copy-", "brand",
                  "analytics", "campaign", "email-market", "influencer", "audience", "trend",
                  "competitor", "lead-gen", "conversion", "ab-test", "app-store-optim"],
    "design": ["design", "ui-", "ux-", "figma", "accessibility", "responsive", "animation",
               "3d-web", "three-js", "webgl", "illustration", "color", "typography"],
    "data": ["data-", "etl", "airflow", "spark", "dbt", "warehouse", "pipeline", "analytics",
             "visualization", "tableau", "bigquery", "snowflake", "kafka", "streaming"],
    "automation": ["automat", "workflow", "n8n", "zapier", "scraper", "scraping", "apify",
                   "airtable", "notion", "slack-", "discord-", "telegram", "webhook",
                   "cron", "scheduler", "activecampaign", "hubspot", "salesforce", "asana"],
    "documentation": ["document", "docs-", "readme", "changelog", "adr", "wiki", "onboard",
                      "tutorial", "guide", "api-doc", "swagger", "openapi"],
}


SUBCATEGORY_PATTERNS = {
    "development": {
        "React": ["react", "next.js", "nextjs", "next-", "remix", "gatsby"],
        "Angular": ["angular"],
        "Vue": ["vue", "nuxt"],
        "Python": ["python", "fastapi", "django", "flask", "async-python"],
        "Node.js": ["node", "express", "nestjs"],
        "TypeScript": ["typescript", "ts-"],
        "Mobile": ["android", "ios", "flutter", "react-native", "mobile", "jetpack-compose"],
        "Database": ["postgres", "mongo", "redis", "prisma", "sql", "orm", "database", "cosmos", "data-tables"],
        "API": ["api-", "graphql", "rest-", "grpc", "trpc"],
        "Architecture": ["architecture", "clean-code", "solid", "design-pattern", "hexagonal", "ddd"],
        "Testing": ["testing", "jest", "pytest", "cypress", "playwright", "test-"],
        "Embedded": ["arm-cortex", "embedded", "firmware", "stm32"],
    },
    "devops": {
        "AWS": ["aws-"],
        "Azure": ["azure-"],
        "Docker": ["docker", "container", "compose"],
        "Kubernetes": ["kubernetes", "k8s", "helm"],
        "CI/CD": ["ci-cd", "cicd", "pipeline", "actions", "deploy"],
        "Monitoring": ["monitoring", "observability", "opentelemetry", "monitor-"],
        "Terraform": ["terraform", "infrastructure"],
    },
    "ai-ml": {
        "Agents": ["agent", "swarm", "orchestrat", "multi-agent", "autonomous"],
        "RAG": ["rag", "embedding", "vector", "search-doc", "retrieval"],
        "LLM": ["llm", "prompt", "openai", "anthropic", "model"],
        "Vision": ["vision", "image-analysis", "imageanalysis"],
        "NLP": ["text-analytics", "translation", "transcription", "speech"],
        "Tools": ["tool-builder", "mcp", "function-call"],
    },
    "security": {
        "Penetration Testing": ["pentest", "penetration", "exploit", "bug-bounty", "fuzzing"],
        "API Security": ["api-security", "api-fuzzing"],
        "Authentication": ["auth-", "oauth", "jwt", "identity", "keyvault"],
        "Threat Modeling": ["threat", "attack-tree", "vulnerability"],
        "Cloud Security": ["aws-penetration", "active-directory"],
        "Reverse Engineering": ["reverse-eng", "anti-reversing", "malware"],
    },
    "marketing": {
        "SEO": ["seo", "schema-markup", "site-architect", "programmatic-seo"],
        "CRO": ["cro", "page-cro", "signup-flow", "form-cro", "popup-cro", "onboarding-cro", "paywall"],
        "Copywriting": ["copywrite", "copy-edit", "cold-email", "email-seq"],
        "Social Media": ["social-media", "social-content", "influencer", "tiktok", "instagram"],
        "Analytics": ["analytics-track", "amplitude", "ab-test"],
        "Paid Ads": ["paid-ads", "ad-creative"],
        "Content Strategy": ["content-strat", "brand", "marketing-idea", "marketing-psych"],
        "Growth": ["referral", "churn", "free-tool", "launch-strat", "pricing-strat"],
        "Email": ["email-market", "email-seq", "activecampaign", "cold-email"],
        "Sales": ["sales-enable", "revops", "competitor"],
    },
    "design": {
        "UI/UX": ["ui-", "ux-", "ui-ux"],
        "Accessibility": ["accessibility", "wcag", "a11y"],
        "3D/WebGL": ["3d-web", "three-js", "webgl", "spline"],
        "CSS/Layout": ["tailwind", "css-", "responsive", "layout"],
    },
    "data": {
        "Pipelines": ["airflow", "etl", "pipeline", "kafka", "streaming"],
        "Analytics": ["data-", "visualization", "tableau", "bigquery"],
        "Databases": ["warehouse", "snowflake", "dbt"],
    },
    "automation": {
        "Web Scraping": ["scraper", "scraping", "apify"],
        "Workflow": ["workflow", "n8n", "zapier", "automat"],
        "Integrations": ["airtable", "notion", "slack-", "discord-", "asana", "hubspot", "whatsapp"],
    },
    "documentation": {
        "API Docs": ["api-doc", "swagger", "openapi"],
        "Technical Writing": ["document", "readme", "changelog", "adr", "wiki"],
    },
}


def _categorize_skill(skill_id: str, description: str) -> list[str]:
    """Infer categories from skill name and description."""
    text = f"{skill_id} {description}".lower()
    cats = []
    for cat, patterns in CATEGORY_PATTERNS.items():
        if any(p in text for p in patterns):
            cats.append(cat)
    return cats or ["other"]


def _subcategorize_skill(skill_id: str, description: str, categories: list[str]) -> list[str]:
    """Infer sub-categories from skill name and description."""
    text = f"{skill_id} {description}".lower()
    subcats = []
    for cat in categories:
        if cat in SUBCATEGORY_PATTERNS:
            for subcat, patterns in SUBCATEGORY_PATTERNS[cat].items():
                if any(p in text for p in patterns):
                    subcats.append(subcat)
    return list(dict.fromkeys(subcats))  # dedupe, preserve order


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
                cats = _categorize_skill(d.name, meta["description"])
                subcats = _subcategorize_skill(d.name, meta["description"], cats)
                skills.append({
                    "id": d.name,
                    "name": meta["name"],
                    "description": meta["description"],
                    "categories": cats,
                    "subcategories": subcats,
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
                cats = _categorize_skill(d.name, meta["description"])
                subcats = _subcategorize_skill(d.name, meta["description"], cats)
                skills.append({
                    "id": d.name,
                    "name": meta["name"],
                    "description": meta["description"],
                    "categories": cats,
                    "subcategories": subcats,
                    "source": "bundled",
                    "enabled": enabled,
                    "path": str(d),
                })
    
    return skills


@router.get("/skills")
async def list_skills():
    return _scan_skills()


@router.get("/skills/categories")
async def list_categories():
    """Return full category tree with subcategory counts."""
    skills = _scan_skills()
    tree = {}
    for cat in CATEGORY_PATTERNS:
        tree[cat] = {}
    tree["other"] = {}

    for s in skills:
        for cat in s["categories"]:
            if cat not in tree:
                tree[cat] = {}
            for subcat in s.get("subcategories", []):
                tree[cat][subcat] = tree[cat].get(subcat, 0) + 1
            if not s.get("subcategories"):
                tree[cat]["General"] = tree[cat].get("General", 0) + 1

    result = []
    for cat, subcats in tree.items():
        if subcats:
            result.append({
                "category": cat,
                "total": sum(subcats.values()),
                "subcategories": [{"name": n, "count": c} for n, c in sorted(subcats.items(), key=lambda x: -x[1])],
            })
    return sorted(result, key=lambda x: -x["total"])


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