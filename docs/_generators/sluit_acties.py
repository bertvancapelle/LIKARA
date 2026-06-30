#!/usr/bin/env python3
"""
Sessie-afsluitacties voor LIKARA.
Voert de verplichte checks uit vóór gen_build.py wordt aangeroepen.
Eigenaar: G. van Capelle Beheer B.V.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

def check_tst():
    """Controleert of een TST-rapport aanwezig is voor de huidige sessie."""
    tst_dir = REPO_ROOT / "docs"
    rapporten = list(tst_dir.rglob("TST-*Validatierapport*.md"))
    if not rapporten:
        print("⚠️  Geen TST-validatierapport gevonden in docs/")
        print("   Draai eerst de TST-validatiecyclus (CONTRIBUTING.md sectie 6)")
        return False
    meest_recent = max(rapporten, key=lambda p: p.stat().st_mtime)
    print(f"✅ TST-rapport gevonden: {meest_recent.name}")
    return True

def check_skills_gevuld():
    """Controleert of de likara-skills niet meer leeg zijn."""
    skills_dir = REPO_ROOT / ".claude" / "skills" / "likara"
    lege = []
    for skill in skills_dir.rglob("SKILL.md"):
        if skill.stat().st_size < 200:
            lege.append(str(skill.relative_to(REPO_ROOT)))
    if lege:
        print("⚠️  Lege likara-skills gevonden:")
        for s in lege:
            print(f"   • {s}")
        print("   Vul de relevante skills bij voordat je afsluit (skill-review stap)")
        return False
    print("✅ Alle likara-skills gevuld")
    return True

def check_next_session():
    """Controleert of NEXT_SESSION.md is ingevuld (niet alleen placeholders)."""
    ns = REPO_ROOT / "NEXT_SESSION.md"
    if not ns.exists():
        print("⚠️  NEXT_SESSION.md ontbreekt")
        return False
    tekst = ns.read_text()

    # Detecteer zowel gen_next_session.py placeholder als handmatige placeholder
    PLACEHOLDERS = [
        "_[Vul in tijdens sessie-afsluiting]_",
        "_Dit bestand wordt gegenereerd door gen_build.py._",
    ]
    for placeholder in PLACEHOLDERS:
        if placeholder in tekst:
            print("⚠️  NEXT_SESSION.md bevat nog niet-ingevulde placeholders")
            print("   Vul de top-5 prioriteiten en openstaande punten in")
            print("   (of draai gen_build.py om een nieuw template te genereren)")
            return False

    print("✅ NEXT_SESSION.md ingevuld")
    return True

def check_git_status():
    """Controleert of er uncommitted wijzigingen zijn."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if result.stdout.strip():
        print("⚠️  Uncommitted wijzigingen aanwezig:")
        print(result.stdout)
        print("   Commit alle wijzigingen vóór sessie-afsluiting")
        return False
    print("✅ Working tree clean")
    return True

def main():
    print("\n═══ LIKARA sluit_acties.py ═══\n")

    checks = [
        ("TST-rapport", check_tst),
        ("Skills gevuld", check_skills_gevuld),
        ("NEXT_SESSION.md", check_next_session),
        ("Git status", check_git_status),
    ]

    resultaten = []
    for naam, check in checks:
        print(f"\n▶ {naam}")
        ok = check()
        resultaten.append((naam, ok))

    print("\n── Samenvatting ──")
    alles_ok = True
    for naam, ok in resultaten:
        status = "✅" if ok else "❌"
        print(f"  {status} {naam}")
        if not ok:
            alles_ok = False

    if not alles_ok:
        print("\n❌ Niet alle checks geslaagd — los bovenstaande punten op\n")
        sys.exit(1)

    print("\n✅ Alle checks geslaagd — ga door met gen_build.py\n")

if __name__ == "__main__":
    main()
