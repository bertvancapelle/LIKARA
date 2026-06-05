#!/usr/bin/env python3
"""
Genereert SESSIESTART.md — het document dat bovenaan de sessie-ZIP
staat en door CC als eerste wordt gelezen.
Eigenaar: G. van Capelle Beheer B.V.
"""

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "SESSIESTART.md"
SESSIE_BRIEFING = REPO_ROOT / "SESSIE_BRIEFING.md"

def main():
    build_label = sys.argv[1] if len(sys.argv) > 1 else "V???"

    briefing = ""
    if SESSIE_BRIEFING.exists():
        briefing = SESSIE_BRIEFING.read_text()

    inhoud = f"""# SESSIESTART — CompliData {build_label}

**Datum**: {date.today().isoformat()}
**Platform**: CompliData — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/complidata/ bestaat
   - Zo ja: normale modus — lees alle complidata-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — CompliData {build_label} — [N] skills geladen"
5. Wacht op START: [naam] van Bert

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

{briefing}
"""
    OUTPUT.write_text(inhoud)
    print(f"✅ SESSIESTART.md gegenereerd ({build_label})")

if __name__ == "__main__":
    main()
