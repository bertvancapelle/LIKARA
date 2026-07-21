# TST-Validatierapport — V049

**Build:** V049 · **Datum:** 21 juli 2026 · **Sessie:** LI048
**Gevalideerde commit:** `44ef3f8` · **Werktree:** schoon

---

## Uitslag per as

| As | Onderwerp | Resultaat |
|---|---|---|
| 1 | Code-kwaliteit | ✅ geslaagd |
| 2 | Tests | ✅ geslaagd |
| 3 | Database-integriteit | ✅ geslaagd |
| 4 | Veiligheid en conventies | ✅ geslaagd |

**Kritieke bevindingen: 0**

---

## As 1 — Code-kwaliteit

| Controle | Uitslag |
|---|---|
| `py_compile` op alle Python-bestanden | OK, 0 syntaxfouten |
| Hardcoded tenant-ID's in applicatiecode | 0 |
| `localStorage` voor tokens | 0 |
| `lk_admin` in applicatiecode | 0 (zie hieronder) |

**Nagekeken, niet aangenomen:** de grep op `lk_admin` gaf vijf treffers. Alle vijf zijn
**commentaar dat juist uitlegt dat `lk_admin` er niet in zit** — `database.py:23,38`,
`tenant.py:60` (OP-11), en twee seed-services die vastleggen dat ze uitsluitend via de
init-container draaien. Geen enkele treffer is een connectiestring of een aanroep.

**Geaccepteerde afwijking:** `py_compile` meldt een `SyntaxWarning` (ongeldige escape-sequence) in
`.claude/skills/engineering-team/ms365-tenant-manager/scripts/powershell_generator.py`. Dat is een
**overgenomen framework-skill**, geen LIKARA-code, en valt buiten de scanreikwijdte van as 4 om
dezelfde reden.

## As 2 — Tests

| Poort | Uitslag |
|---|---|
| Backend platform (`backend/tests`) | **80 passed** |
| Backend module (`modules/bwb_ontvlechting/backend`) | **1136 passed, 2 skipped** |
| Frontend (`vitest run`) | **102 bestanden, 1374 passed** |
| `vite build` | ✓ |
| `check-css-build.mjs` | **14 scans groen** |

De 2 skips zijn de bekende live-DB-tests die overslaan als de database niet bereikbaar is; bij deze
run wás hij bereikbaar, dus het zijn de twee structurele skips.

**Groei deze sessie:** frontend van 98 bestanden / 1275 tests naar 102 / 1374 (**+99 tests**),
backend-module van 1179 naar 1136 + 80 platform = **1216 totaal** (de telling in de vorige
bouwstatus voegde beide backendpoorten samen; hier staan ze apart).

**Nieuwe bronscans deze sessie:** lijstkop-scan (bereik afgeleid uit het hoofdmenu, 14 schermen) en
icoon-scan (78 views, 0 dode verwijzingen). Beide met een zelftest die bij elke run bewijst dat de
scan bijt — 10/10 respectievelijk 5/5.

## As 3 — Database-integriteit

| Controle | Uitslag |
|---|---|
| Alembic heads | **1** (`0073_adr052_klaarverkl_snapshot`) |
| Alembic branches | leeg |
| `alembic current` | gelijk aan head |
| Tenant-scoped tabellen zónder RLS-policy | **0** |
| Tenant-scoped tabellen mét policy | **34** |
| Tabellen met RLS maar zónder FORCE | **0** |

Geen migraties toegevoegd deze sessie; het schema is onaangeroerd gebleven.

## As 4 — Veiligheid en conventies

| Controle | Uitslag |
|---|---|
| Legacy-referenties (`Eraneos`, `compliman`, `cm_`) | **0** |
| Alle negen `likara`-skills gevuld (>200 bytes) | ✅ |
| `CLAUDE.md` bouwstatus actueel | wordt door `gen_build` bijgewerkt naar V049 |

Scanreikwijdte conform CONTRIBUTING sectie 6: `.claude/`, `docs/_generators/` en `docs/_skills/`
blijven uitgesloten (overgenomen framework-materiaal en de patroondefinities zelf).

---

## Bevinding buiten de assen — de integriteitscheck toetst bestaan, geen actualiteit

Punt 0b van deze sessie vroeg dit te meten. Gemeten in `gen_build.py:106-139`: de check gebruikt
uitsluitend `is_file()`, `is_dir()`, `st_size < 200` en een `glob`-telling. Nergens wordt inhoud
tegen de huidige build gelegd. Gevolgen:

- **Het TST-rapport staat niet in `REQUIRED_FILES`.** Alleen `sluit_acties.py` controleert erop, en
  die accepteerde bij deze sessiestart het rapport van **V048** — een build oud.
- **`NEXT_SESSION.md` en `docs/PROJECTGEHEUGEN.md`** hoeven alleen te bestaan. Een bestand dat nog
  het bouwnummer van drie sessies terug draagt, passeert.
- **De changelog-eis is `minimaal 1 bestand` dat `*_Changelog_V*.md` matcht** — niet: een changelog
  vóór déze build.

Niet opgelost; dit rapport meet alleen. Staat als punt in `NEXT_SESSION`.

---

## Geaccepteerde afwijkingen

1. **Zes browsercheck-draaiboeken zijn nog niet gelopen** (lijstkop snede 1/1b en 2, vier
   auditlog-draaiboeken, detailkop-tekens, objecthistorie). De suites dekken de structuur; wat een
   mens in de browser moet zien — uitlijning, tooltips, toetsenbordvolgorde — is niet machinaal
   vast te stellen. Conform `likara-werkprotocol` is de browsercheck het sluitpunt, niet de suite.
2. **Eén flaky toets**, `ComponentLijst.test.js` → *"een chip wegklikken werkt zonder het venster te
   openen"*: viel om in één van drie volledige runs, geïsoleerd en in de andere runs groen. Oorzaak
   staat in de toets zelf (`mock.calls.at(-1)` terwijl debounce-timers doorlopen), niet in het
   product. Vastgelegd in OPVOLGPUNTEN; niet gerepareerd omdat het buiten elke opdracht van deze
   sessie viel.
