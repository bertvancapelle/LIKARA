# LIKARA Changelog V050

**Datum**: 2026-07-23

## Wijzigingen

Sessie LI049 — skill-consolidatie en de borging die haar bewaakt. Geen applicatiecode-gedrag
gewijzigd; de suites bleven identiek op de nieuwe scan na.

- **Kopverwijzingen-scan** (`backend/tests/test_kopverwijzingen_scan.py`, `a225a63`/`6ccdd53`):
  bewaakt repo-breed dat elke `skill §kop`-verwijzing op een bestaand anker landt; 5 beperkingen
  + werking gedocumenteerd, zelftest bijt. Ving tijdens de sessie 3× echt werk.
- **Verhuizing 1** (`ae3f9ca`): de vijf sessiekoppen in `likara-werkprotocol` opgeheven; 80
  regels verbatim onder onderwerpskoppen, nieuwe kop §Sessiecapaciteit, sessiemarkers toegevoegd.
- **Verhuizing 2** (`94c5625`): P8-subreeks in `likara-ux` op leesvolgorde (byte-verbatim,
  multiset-geborgd); P8a-telling later verhelderd (`ff754eb`, git-archeologie: twee wáre
  tellingen).
- **Tests-consolidatie** (`201092d`, `558f39d`, `87ab572`): 15 chronologische koppen naar
  onderwerp (273=273 verbatim, 35 markers), dubbelingen naar één bron (gate, baseline,
  allowlist-samenvoeging), parkeeritems geland (gate-meting/OPVOLGPUNTEN-staging → werkprotocol,
  psql-recept → LOKAAL-TESTEN).
- **Verhuizing 3** (`3c7268a`): bronscan-eisen canoniek in `likara-tests §Bronscans`;
  frontend houdt de lijstkop-casussen als toepassing met bewaakte kruisverwijzingen.
- **Kleinere besluiten**: LI036-kaartregel voluit naar likara-ux + achterhaalde
  ADR-onderhoudszin geschrapt (`049c4c9`) · mjs-driftkopie → bewaakte verwijzing (`cc93de3`) ·
  UX-first binnen-kop-dubbeling opgeruimd, drie momenten behouden (`5c4879a`) · zes
  verwijzingsreparaties incl. twee dode verwijzingen in code/skill.
- **Documenten**: negen checkpoint-/metingsrapporten + `docs/Opschoonplan-zeven-skills.md`
  (gemeten kaart: 7 skills, 82 chronologische koppen, 37%; recept; vijf blokken;
  hygiëneborging in drie verankeringen) — **uitgesteld** ten gunste van het
  productie-gereedheidsspoor LI050.

Teststand: backend 1221 passed / 2 skipped · frontend 102 files / 1374 passed · vite build OK ·
css-build 14× OK · alembic 1 head (`0073`) · TST-V050: 0 kritieken.
