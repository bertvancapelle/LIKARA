#!/usr/bin/env python3
"""
Assembleert de CompliData sessie-start ZIP.
CompliData sessie-start ZIP assemblage.
Eigenaar: G. van Capelle Beheer B.V.
"""

import json
import os
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "docs" / "_output"

# Curated skills die altijd in de ZIP gaan
CURATED_SKILLS = [
    ".claude/skills/complidata/complidata-backend/SKILL.md",
    ".claude/skills/complidata/complidata-db/SKILL.md",
    ".claude/skills/complidata/complidata-frontend/SKILL.md",
    ".claude/skills/complidata/complidata-security/SKILL.md",
    ".claude/skills/complidata/complidata-tests/SKILL.md",
    ".claude/skills/complidata/complidata-resilience/SKILL.md",
    ".claude/skills/engineering-team/senior-architect/SKILL.md",
    ".claude/skills/engineering-team/senior-backend/SKILL.md",
    ".claude/skills/engineering-team/senior-frontend/SKILL.md",
    ".claude/skills/engineering-team/senior-qa/SKILL.md",
    ".claude/skills/engineering-team/tdd-guide/SKILL.md",
    ".claude/skills/engineering-team/senior-security/SKILL.md",
    ".claude/skills/engineering-team/senior-secops/SKILL.md",
    ".claude/skills/engineering-team/senior-devops/SKILL.md",
    ".claude/skills/engineering-team/code-reviewer/SKILL.md",
    ".claude/skills/engineering-advanced/database-designer/SKILL.md",
    ".claude/skills/security/security-overview/SKILL.md",
    ".claude/skills/security/security-testing/SKILL.md",
    ".claude/skills/security/input-validation/SKILL.md",
]

# Uitgesloten patronen
EXCLUDE_DIRS = {
    "node_modules", "__pycache__", ".git", "dist", "build",
    ".cache", "stage", "docs/_output"
}

EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".exe", ".zip"}

def moet_uitsluiten(pad: Path) -> bool:
    for deel in pad.parts:
        if deel in EXCLUDE_DIRS:
            return True
    if pad.suffix in EXCLUDE_EXTENSIONS:
        return True
    return False

def verzamel_bestanden():
    """Verzamelt alle bestanden die in de ZIP gaan."""
    bestanden = []

    # Root-bestanden
    for naam in ["CLAUDE.md", "NEXT_SESSION.md", "SESSIE_BRIEFING.md",
                 "SESSIESTART.md", "CONTRIBUTING.md", "README.md"]:
        p = REPO_ROOT / naam
        if p.exists():
            bestanden.append(p)

    # docs/ — markdown en JSON, geen binaries
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.exists():
        for p in docs_dir.rglob("*"):
            if p.is_file() and not moet_uitsluiten(p.relative_to(REPO_ROOT)):
                if p.suffix in {".md", ".json", ".html"}:
                    bestanden.append(p)

    # modules/ — alleen .md bestanden (structuur, geen code)
    modules_dir = REPO_ROOT / "modules"
    if modules_dir.exists():
        for p in modules_dir.rglob("*.md"):
            if not moet_uitsluiten(p.relative_to(REPO_ROOT)):
                bestanden.append(p)

    # Curated skills
    for skill_pad in CURATED_SKILLS:
        p = REPO_ROOT / skill_pad
        if p.exists():
            bestanden.append(p)

    return bestanden

def maak_zip(build_label: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_naam = f"CompliData_Sessiestart_{build_label}.zip"
    zip_pad = OUTPUT_DIR / zip_naam

    bestanden = verzamel_bestanden()

    with zipfile.ZipFile(zip_pad, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in bestanden:
            arcnaam = str(p.relative_to(REPO_ROOT))
            zf.write(p, arcnaam)

    print(f"✅ ZIP aangemaakt: {zip_pad}")
    print(f"   {len(bestanden)} bestanden, "
          f"{zip_pad.stat().st_size / 1024:.1f} kB")
    return zip_pad

def valideer_zip(zip_pad: Path, build_label: str):
    """Controleert of verplichte bestanden in de ZIP aanwezig zijn."""
    verplicht = [
        "CLAUDE.md",
        "NEXT_SESSION.md",
        "SESSIE_BRIEFING.md",
        "SESSIESTART.md",
    ]
    with zipfile.ZipFile(zip_pad) as zf:
        namen = set(zf.namelist())

    fouten = [v for v in verplicht if v not in namen]
    if fouten:
        print(f"❌ ZIP-validatie gefaald — ontbrekende bestanden:")
        for f in fouten:
            print(f"   • {f}")
        raise SystemExit(1)

    print(f"✅ ZIP-validatie geslaagd ({len(namen)} bestanden)")

def main():
    build_label = sys.argv[1] if len(sys.argv) > 1 else "V???"
    zip_pad = maak_zip(build_label)
    valideer_zip(zip_pad, build_label)

if __name__ == "__main__":
    main()
