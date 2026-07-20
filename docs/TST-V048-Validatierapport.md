# TST-Validatierapport — V048

**Build:** V048 · **Datum:** 2026-07-20 · **Sessie:** LI047 · **Commit bij meting:** `218b9fd`
**Uitgevoerd conform:** CONTRIBUTING.md sectie 6 (vier assen)

## Uitkomst

| As | Onderwerp | Resultaat |
|---|---|---|
| 1 | Code-kwaliteit | ✅ geslaagd |
| 2 | Tests | ✅ geslaagd |
| 3 | Database-integriteit | ✅ geslaagd |
| 4 | Veiligheid en conventies | ✅ geslaagd |

**Kritieke bevindingen: 0.**
**Geaccepteerde afwijkingen: 0.** De browsercheck-restdata is via een volledige reseed opgeruimd; het demolandschap komt weer volledig uit de seed.

---

## As 1 — Code-kwaliteit

- **`py_compile`** over alle Python-bestanden (exclusief `node_modules`, `.git`, `__pycache__`): **OK**, 0 syntaxfouten.
- **Hardcoded tenant-id's in code:** 0.
- **`localStorage` voor tokens:** 0.
- **`lk_admin` in applicatiecode:** 5 treffers, **alle vijf commentaar/docstring** die juist vastlegt dat `lk_admin` er níét aan te pas komt (`middleware/tenant.py:60`, `core/database.py:23,38`, `seed_contractconfig.py:8`, `seed_antwoordconfig.py:12`). Geen enkel gebruik. Geen bevinding.

⚠ Eén `SyntaxWarning` (ongeldige escape-sequence) in `.claude/skills/engineering-team/ms365-tenant-manager/scripts/powershell_generator.py` — een **overgenomen framework-skill**, buiten de LIKARA-codebase en buiten de conventie-scope van as 4. Niet gewijzigd.

## As 2 — Tests

| Suite | Uitkomst | Vorige stand (V047) |
|---|---|---|
| Backend (`backend/tests/ modules/`) | **1179 geslaagd · 2 overgeslagen** | 1159 / 2 |
| Frontend (vitest) | **98 bestanden · 1273 geslaagd** | 97 bestanden / 1248 |
| `vite build` | ✅ built in 521 ms | OK |

**Verschil t.o.v. V047: +20 backend, +25 frontend, +2 testbestanden.** Volledig verklaard door deze sessie:

- ADR-055 (gebruik-verfijning component-breed): 5 backend, 3 frontend
- `component_id`-hernoeming: 1 backend
- Open punten snede 1: 9 backend, 12 frontend (nieuw bestand `OpenPuntenSectie.test.js`)
- Koppelingen component-breed: 1 backend, 1 frontend
- Open punten snede 2 + één-ingang: netto 3 frontend
- Kopstijl/kop-rij: 3 frontend
- Seed-herstel + schema-aanroep-scan: 3 backend (nieuw bestand `test_schema_aanroepen_scan.py`)

Geen enkele test overgeslagen of versoepeld. De 2 skips zijn ongewijzigd t.o.v. V047.

### css-build — alle vier de bronscans, elk met zelftest

| Scan | Zelftest | Resultaat |
|---|---|---|
| Veld-bron-scan | 5/5 (bijt) | 0 afwijkingen in **77** views |
| Detailkop-scan | 7/7 (bijt) | 7 detailschermen op de bouwsteen |
| Kopstijl-scan | 7/7 (bijt) | **53** schermen op de gedeelde maat |
| Kop-rij-scan *(nieuw LI047)* | 7/7 (bijt) | **27** schermen, elke kop-met-uitleg op de gedeelde rij |

Plus: **14** kritische interactie-klassen aanwezig (was 13 — `.lk-kop-rij>:is(h1,h2)` toegevoegd), **45** verwezen `--lk-`tokens allemaal gedefinieerd.

## As 3 — Database-integriteit

- **Alembic heads:** exact **1** — `0073_adr052_klaarverkl_snapshot (head)`.
- **Alembic branches:** leeg (geen split).
- **Migraties deze sessie: 0.** ADR-055 en de `component_id`-hernoeming zijn beide zonder schemawijziging gebouwd; dat was in beide gevallen het doorslaggevende argument dat het om een applicatielaag-restant ging.

## As 4 — Veiligheid en conventies

- **Eraneos / compliman / `cm_`-referenties:** 0 treffers.
- **Alle negen likara-skills gevuld** (>200 bytes): backend 41 kB · db 34 kB · domeinmodel 65 kB · frontend 103 kB · resilience 7 kB · security 20 kB · tests 35 kB · ux 62 kB · werkprotocol 32 kB.
- **CLAUDE.md bouwstatus:** wordt bijgewerkt door `gen_build.py` (stap 5 van de afsluiting).

---

## Demolandschap — gemeten BINNEN de tenant-context, ná een volledige reseed

Gemeten met de app-rol `lk_app` in tenant `11111111-…-111111111111`, **ná** de volledige reset
(`docker compose down` → `docker volume rm likara_lk_postgres_data` → `up -d` → dev-seed).

| Tabel | Rijen |
|---|---:|
| component | 19 |
| component_norm | 10 (**6 verplicht**) |
| component_klaarverklaring | 5 |
| component_bevinding | 3 |
| organisatiegebruik | 35 |
| gebruikersgroep | 12 |
| checklistscore | 267 (**1 op nee/deels**) |
| relatie | 366 (waarvan 29 flow) |

### De reseed nam méér drift weg dan de browsercheck-restdata

De aanleiding was restdata uit de browserchecks (een gebruikersgroep op de Shared fileshare, een
"bewust geen"-bevinding op de Shared DB-server). Die is opgeruimd — maar de reseed herstelde óók twee
eerdere driftgevallen die ik als vaststaand had gerapporteerd:

| Wat ik meldde | Werkelijke stand ná reseed |
|---|---|
| "nul nee/deels-scores; de gebundelde checklistregel is niet te bekijken" | **1 nee-score.** Zaaksysteem draagt een `valt op`-punt — de bundeling **is** in de browser te zien. De blokkade bestond niet; het was drift. |
| Archiefbeheer: snapshot `{}`, 0 open feiten | **bewust `{biv, eigenaar, verantwoordelijke}` + verschoven `{bedoeling}`** — het rijkste klaarverklaring-geval, zoals het LI046-checkpoint beschreef. |

**De regel die hierbij hoort:** de tellingen in de slice-gate-rapporten van deze sessie zijn
**momentopnamen**, geen stand. Wie ze later overneemt zit ernaast — hermeten binnen de tenant-context
is de regel. Dezelfde les trad deze sessie drie keer op: een verouderd checkpoint als meting
gepresenteerd, een meting als platformrol, en nu drift die als feit was gerapporteerd.

### De browsercheck-gevallen — alle aanwezig

| Geval | Component | moet · netjes · valt op | Klaarverklaring |
|---|---|---|---|
| **Schoon** | HR-systeem | 0 · 3 · 0 | bewust `[]`, verschoven `[]` |
| **Beide soorten afwijking** | Archiefbeheer | 4 · 3 · 0 | bewust `{biv, eigenaar, verantwoordelijke}` · verschoven `{bedoeling}` |
| idem, kleiner | DMS · Zaaksysteem | 2 · 0 · 0/1 | bewust `{biv}` · verschoven `{bedoeling}` |
| **Alleen verschoven** | Klantportaal | 1 · 0 · 0 | verschoven `{bedoeling}` |
| **Bewuste vaststelling** | 3 bevindingen | — | Archiefbeheer (koppelingen + contract) · HR-systeem (koppelingen) |
| **ADR-055-geval (nieuw)** | Shared fileshare | 6 · 2 · 1 | 1 gebruikersgroep (afdeling Burgerzaken) |
| **Gebundelde checklistregel** | Zaaksysteem | valt op = 1 | de nee-score |

De twee andere niet-applicaties (Shared DB-server, Extern SaaS-platform) dragen bewust **géén**
gebruikersgroep — het landschap toont dus zowel een geval dát de verbreding gebruikt als gevallen die
hem terecht niet gebruiken (werkprotocol §LI044).

### Seed-defect gevonden en hersteld

De hernoeming `applicatie_id` → `component_id` (commit `14e1dbe`) miste **twee aanroepen** in
`backend/dev_seed_testdata.py`. De dev-seed crashte daardoor op de gebruikersgroep-stap: het
demolandschap was niet meer op te bouwen. **Geen van de 1176 groene tests raakte het.**

Hersteld, plus een repo-brede bron-scan (`test_schema_aanroepen_scan.py`) die élke aanroep van een
`extra="forbid"`-schema tegen de schemavelden houdt — afgeleid uit de schema's zelf, zonder
onderhouden uitzonderingslijst. Bewezen bijtend: tegen de kapotte stand wijst hij exact de twee
regels aan, met bestandsnaam en regelnummer.

## Conclusie

**Alle vier de assen geslaagd. 0 kritieke bevindingen, 0 geaccepteerde afwijkingen.**

Eén defect gevonden én hersteld tijdens de validatie: de dev-seed was gebroken door een gemiste
hernoeming. Dat het pas hier opviel — en niet door 1176 groene tests — is de belangrijkste bevinding
van deze cyclus; de nieuwe bron-scan vangt de volgende.
