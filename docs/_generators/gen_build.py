#!/usr/bin/env python3
"""
CompliData gen_build.py
Sessie-afsluiting en sessie-start ZIP generatie.
Eigenaar: G. van Capelle Beheer B.V.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATORS_DIR = REPO_ROOT / "docs" / "_generators"
COUNTER_FILE = GENERATORS_DIR / "build_counter.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
NEXT_SESSION = REPO_ROOT / "NEXT_SESSION.md"
SESSIE_BRIEFING = REPO_ROOT / "SESSIE_BRIEFING.md"
SESSIESTART_MD = REPO_ROOT / "SESSIESTART.md"
CHANGELOG_DIR = REPO_ROOT / "docs" / "changelog"
STAGE_DIR = REPO_ROOT / "stage"
OUTPUT_DIR = REPO_ROOT / "docs" / "_output"

# ── Backup (lokale dump + iCloud-kopie) ──────────────────────────────────────
# De DB-backup loopt structureel mee als laatste afsluitstap, zodat de
# iCloud-kopie nooit een vergeetbare handmatige stap is (CD013-A).
PG_CONTAINER = "cd-postgres"
BACKUPS_DIR = Path.home() / "complidata" / "backups"
# Configureerbaar pad; default = lokaal gemounte iCloud-Drive-map.
# (~/Library/Mobile Documents/com~apple~CloudDocs/CompliData-backups/)
ICLOUD_BACKUP_DIR = Path(
    os.environ.get(
        "ICLOUD_BACKUP_DIR",
        str(
            Path.home()
            / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "CompliData-backups"
        ),
    )
)

# ── Verplichte integriteitscheck ─────────────────────────────────────────────
REQUIRED_DIRS = [
    "docs/adr",
    "docs/_generators",
    "docs/_skills",
    ".claude/skills/complidata",
    ".claude/skills/engineering-team",
    ".claude/skills/security",
    "modules",
]

REQUIRED_FILES = [
    "CLAUDE.md",
    "NEXT_SESSION.md",
    "SESSIE_BRIEFING.md",
    "docs/_generators/build_counter.json",
    "docs/_generators/gen_build.py",
    "docs/_generators/gen_next_session.py",
    "docs/_generators/gen_sessiestart.py",
    "docs/_generators/gen_sessie_briefing.py",
    "docs/_generators/sluit_acties.py",
]

REQUIRED_SKILLS = [
    ".claude/skills/complidata/complidata-backend/SKILL.md",
    ".claude/skills/complidata/complidata-db/SKILL.md",
    ".claude/skills/complidata/complidata-frontend/SKILL.md",
    ".claude/skills/complidata/complidata-security/SKILL.md",
    ".claude/skills/complidata/complidata-tests/SKILL.md",
    ".claude/skills/complidata/complidata-resilience/SKILL.md",
]

REQUIRED_PATTERNS = [
    ("docs/adr", "ADR-*.md", 1, "Minimaal 1 ADR vereist"),
    ("docs/changelog", "CompliData_Changelog_V*.md", 1,
     "Changelog voor huidige build vereist"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def lees_counter():
    with open(COUNTER_FILE) as f:
        return json.load(f)

def schrijf_counter(data):
    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f, indent=2)

def verhoog_build():
    data = lees_counter()
    data["build"] += 1
    data["sessie_datum"] = date.today().isoformat()
    schrijf_counter(data)
    return data

def bouw_label(data):
    return f"V{data['build']:03d}"

def integriteitscheck(build_label):
    """Blokkeert de build bij ontbrekende verplichte onderdelen."""
    fouten = []

    for d in REQUIRED_DIRS:
        if not (REPO_ROOT / d).is_dir():
            fouten.append(f"ONTBREEKT map: {d}")

    for f in REQUIRED_FILES:
        if not (REPO_ROOT / f).is_file():
            fouten.append(f"ONTBREEKT bestand: {f}")

    for f in REQUIRED_SKILLS:
        p = REPO_ROOT / f
        if not p.is_file():
            fouten.append(f"ONTBREEKT skill: {f}")
        elif p.stat().st_size < 200:
            fouten.append(f"SKILL LEEG (<200 bytes): {f}")

    for dirname, pattern, minimum, msg in REQUIRED_PATTERNS:
        d = REPO_ROOT / dirname
        if d.is_dir():
            gevonden = list(d.glob(pattern))
            if len(gevonden) < minimum:
                fouten.append(f"{msg} (gevonden: {len(gevonden)})")

    if fouten:
        print(f"\n❌ INTEGRITEITSCHECK GEFAALD — build {build_label} geblokkeerd\n")
        for f in fouten:
            print(f"   • {f}")
        print()
        sys.exit(1)

    print(f"✅ Integriteitscheck geslaagd ({build_label})")

def update_claude_bouwstatus(build_label, test_status, kritieken):
    """Werkt de BOUWSTATUS_START/END sectie in CLAUDE.md bij."""
    tekst = CLAUDE_MD.read_text()
    vandaag = date.today().strftime("%B %Y")

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        commit = result.stdout.strip() if result.returncode == 0 else "—"
    except Exception:
        commit = "—"

    nieuw_blok = f"""<!-- BOUWSTATUS_START -->
## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | {build_label} |
| Datum | {vandaag} |
| Commit | {commit} |
| Tests | {test_status} |
| TST-rapport | TST-{build_label}-Validatierapport.md |
| Kritieke bevindingen | {kritieken} |

<!-- BOUWSTATUS_END -->"""

    tekst = re.sub(
        r"<!-- BOUWSTATUS_START -->.*?<!-- BOUWSTATUS_END -->",
        nieuw_blok,
        tekst,
        flags=re.DOTALL
    )
    CLAUDE_MD.write_text(tekst)
    print(f"✅ CLAUDE.md bouwstatus bijgewerkt ({build_label})")

def maak_changelog(build_label):
    """Maakt een lege changelog-entry voor de huidige build."""
    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    pad = CHANGELOG_DIR / f"CompliData_Changelog_{build_label}.md"
    if not pad.exists():
        pad.write_text(
            f"# CompliData Changelog {build_label}\n\n"
            f"**Datum**: {date.today().isoformat()}\n\n"
            f"## Wijzigingen\n\n_Vul aan tijdens sessie-afsluiting._\n"
        )
        print(f"✅ Changelog aangemaakt: {pad.name}")
    else:
        print(f"ℹ️  Changelog bestaat al: {pad.name}")
    return pad

def roep_generator_aan(script_naam, extra_args=None):
    """Roept een generator-script aan."""
    script = GENERATORS_DIR / script_naam
    cmd = [sys.executable, str(script)] + (extra_args or [])
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        print(f"❌ {script_naam} gefaald (exit {result.returncode})")
        sys.exit(result.returncode)
    print(f"✅ {script_naam} succesvol")

# ── Backup-stap ────────────────────────────────────────────────────────────────

def maak_db_dump():
    """Lokale PostgreSQL-dump via de cd-postgres container. Faalt ZACHT (warn).

    Retourneert het pad naar de `.sql` of None als de dump niet gemaakt kon worden
    (docker/container afwezig) — de build breekt hier nooit op.
    """
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    doel = BACKUPS_DIR / f"complidata_{datetime.now().strftime('%Y%m%d_%H%M')}.sql"
    try:
        with open(doel, "wb") as fh:
            r = subprocess.run(
                ["docker", "exec", PG_CONTAINER, "pg_dump", "-U", "cd_admin", "complidata"],
                stdout=fh, stderr=subprocess.PIPE,
            )
        if r.returncode != 0:
            doel.unlink(missing_ok=True)
            print(f"⚠️  DB-dump overgeslagen (pg_dump exit {r.returncode}).")
            return None
        print(f"✅ Lokale DB-dump: {doel}")
        return doel
    except FileNotFoundError:
        doel.unlink(missing_ok=True)
        print("⚠️  DB-dump overgeslagen (docker niet beschikbaar).")
        return None


def kopieer_naar_icloud(dump_path, icloud_dir=ICLOUD_BACKUP_DIR):
    """Kopieer UITSLUITEND de `.sql`-dump naar de iCloud-map.

    Secrets (`~/complidata/secrets/`, `.env`) worden NOOIT meegenomen — er wordt
    één specifiek `.sql`-bestand gekopieerd, geen wildcard/map. Faalt ZACHT: een
    ontbrekende/niet-gemounte iCloud-map waarschuwt en breekt de build niet (de
    lokale dump is dan al veilig). Er wordt geen niet-bestaand iCloud-pad geforceerd.
    """
    if dump_path is None:
        print("⚠️  iCloud-kopie overgeslagen (geen lokale dump).")
        return False
    dump_path = Path(dump_path)
    if not dump_path.is_file() or dump_path.suffix != ".sql":
        print("⚠️  iCloud-kopie overgeslagen (geen geldige .sql-dump).")
        return False
    icloud_dir = Path(icloud_dir)
    if not icloud_dir.parent.exists():
        print(f"⚠️  iCloud-map niet gemount ({icloud_dir.parent}); lokale dump is veilig, build gaat door.")
        return False
    icloud_dir.mkdir(parents=True, exist_ok=True)
    doel = icloud_dir / dump_path.name
    shutil.copy2(dump_path, doel)  # alleen dit ene .sql-bestand — nooit secrets
    print(f"✅ iCloud-kopie: {doel}")
    return True


def backup_stap():
    """Laatste afsluitstap: lokale DB-dump, dáárna de iCloud-kopie."""
    dump = maak_db_dump()
    kopieer_naar_icloud(dump)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n═══ CompliData gen_build.py ═══\n")

    # 1. Bouwnummer ophogen
    data = verhoog_build()
    build_label = bouw_label(data)
    print(f"🔢 Build: {build_label} ({data['sessie_datum']})\n")

    # 2. CLAUDE.md bouwstatus bijwerken — MOET vóór de generators (CD018/OP-18):
    #    gen_sessie_briefing.py leest het BOUWSTATUS-blok uit CLAUDE.md. Stond deze
    #    update ná de briefing, dan kreeg de briefing een stale blok (titel = nieuw
    #    build_label, body = vorige build).
    #    Trade-off: de update draait nu óók vóór de integriteitscheck (stap 7). Dat is
    #    geen regressie — build_counter.json wordt in beide volgordes al vóór die check
    #    gebumpt; bij een abnormale afbreking wordt hooguit CLAUDE.md toegevoegd aan de
    #    set die toch al gewijzigd is. Het normale, geslaagde pad wijzigt niet.
    #    Test-status wordt als argument meegegeven of gelezen uit TST-rapport.
    test_status = sys.argv[1] if len(sys.argv) > 1 else "zie TST-rapport"
    kritieken = sys.argv[2] if len(sys.argv) > 2 else "0"
    update_claude_bouwstatus(build_label, test_status, kritieken)

    # 3. Changelog aanmaken
    maak_changelog(build_label)

    # 4. NEXT_SESSION.md genereren
    roep_generator_aan("gen_next_session.py", [build_label])

    # 5. SESSIE_BRIEFING.md genereren
    roep_generator_aan("gen_sessie_briefing.py", [build_label])

    # 6. SESSIESTART.md genereren
    roep_generator_aan("gen_sessiestart_md.py", [build_label])

    # 7. Integriteitscheck (blokkeert bij falen)
    integriteitscheck(build_label)

    # 8. Sessie-start ZIP assembleren
    roep_generator_aan("gen_sessiestart.py", [build_label])

    # 9. Backup: lokale DB-dump + iCloud-kopie (structureel, secrets uitgesloten)
    backup_stap()

    print(f"\n✅ Build {build_label} voltooid.\n")

if __name__ == "__main__":
    main()
