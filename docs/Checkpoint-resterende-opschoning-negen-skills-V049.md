# Checkpoint — de resterende opschoning over de negen skills (READ-ONLY meting)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `5c4879a` · werktree schoon
**Datum meting:** 2026-07-22 · Niets gewijzigd behalve dit rapport. Scan groen (5 passed).

**Kernuitkomst:** **7 van de 9 skills dragen de chronologie-kwaal nog** — samen **82
chronologische koppen met 2.539 regels beslag (37% van alle 6.805 skill-regels)**. Zwaarst:
backend (66%), db (54%), ux (51%), frontend (43%); licht: security (33%), domeinmodel (31%),
resilience (15%). `werkprotocol` en `tests` staan op **0** — de consolidatie van deze sessie is
beklijfd. Daarnaast resteren **2 duidelijke cross-skill-dubbelingen** (vitest-testrecept
frontend↔tests; de KIJKFILTER-regel domeinmodel↔ux), 2 grensgevallen, **5 kop-naam-collisions
binnen skills**, en **1 dode bestandsverwijzing** (backend → `schemas/applicatie.py`, 2×).

---

## Blok 1 — de chronologie-kwaal per skill

Criterium (objectief, zelfde als bij werkprotocol/tests): een `##`-/`###`-kop die **begint**
met `LI0xx` of `V0xx`. Koppen met een onderwerpstitel en slechts een sessie-suffix — zoals
tests' hernoemde "Mock-reset … (LI047)" of werkprotocols "KERNLES LI038 — …" — tellen niet.

| Skill | Regels | Koppen (##+###) | Chronologische ## | Beslag (regels) | % van skill |
|---|---:|---:|---:|---:|---:|
| **backend** | 714 | 32+6 | **17** | 473 | **66%** |
| **db** | 492 | 27+0 | **11** | 266 | **54%** |
| **ux** | 1.086 | 27+40 | **14** | 554 | **51%** |
| **frontend** | 1.860 | 57+29 | **23** | 799 | **43%** |
| **security** | 332 | 25+0 | **5** | 109 | **33%** |
| **domeinmodel** | 1.008 | 24+48 | **11** | 316 | **31%** |
| **resilience** | 151 | 8+2 | **1** | 22 | **15%** |
| **tests** | 525 | 18+1 | **0** | 0 | **0%** ✓ |
| **werkprotocol** | 637 | 18+13 | **0** | 0 | **0%** ✓ |
| **Totaal** | **6.805** | 236+139 | **82** | **2.539** | **37%** |

Chronologische `###`-koppen: 0 in alle skills (de kwaal zit op `##`-niveau). De volledige
per-skill-koppenlijst met regelnummers en omvang is machinaal gemeten; de zwaarste brokken:
backend §V016-patronen-DC015 (116 regels), frontend §LI040-patronen (77), §LI023 (67),
§LI039-patronen (62), ux §LI045/ADR-052 (67), §LI035 (65), db §V013-patronen (50),
domeinmodel §LI038/ADR-043 (56), §LI039/ADR-044 (50), security §V016-patronen (43).

**Controle consolidatie (1.4):** werkprotocol en tests dragen 0 chronologische koppen — de
behandeling van deze sessie is beklijfd. Nuance zoals bij tests destijds: een deel van de 82 is
geen grabbelzak maar één-onderwerp-met-prefix (bv. domeinmodel "LI041/… — de vorm bepaalt nooit
de betekenis (KERNREGEL)", ux "LI046 — de kaart vertelt…") — daar is hernoemen het werk, niet
uiteenrafelen; de verhouding per skill is bij een eigen checkpoint per skill te meten, zoals bij
tests gebeurde.

---

## Blok 2 — cross-skill-dubbelingen (duidelijke gevallen; niet uitputtend)

Machinale eerste zeef: slechts **2 woordelijk-identieke regels (≥60 tekens)** komen in ≥2
skills voor — beide in hetzelfde blok. Daaromheen inhoudelijk gelezen:

| # | Regel | Skills + vindplaats | Oordeel |
|---|---|---|---|
| 1 | **het vitest-testrecept** (module-tests onder `frontend/tests/`, AppLayout-colocated-uitzondering, mock-`@/api`, mount-array, teleport-stub, `stubGlobal('location')`) | frontend §Testopzet (vitest) r625–637 ↔ tests §Frontend-testpatroon r153 e.v. — 2 regels woordelijk identiek, de rest parallel | **echte dubbeling** — zelfde recept voluit op twee plekken; wie er één bijwerkt, laat de ander driften |
| 2 | **"een persoonlijke voorkeur is een KIJKFILTER, nooit een invoerregel"** | domeinmodel §LI034 r714–725 ↔ ux §LI034/Voorkeur=KIJKFILTER r651–656 — beide voluit, met eigen accent (schrijf-slot-anti-patroon resp. UX-kern) | **echte dubbeling** met accentverschil — samenvoegen is herformuleren; de accenten zouden expliciet mee moeten |
| 3 | **"de kaart is bewust applicatie-centrisch"** | domeinmodel r727–734 ↔ frontend r1436–1452 ↔ ux r229–234 — drie plekken, elk met kruisverwijzing naar de ander en eigen laag (domein/vindplaatsen/UX) | **grensgeval** — bewust verdeeld feit met verwijzingen; eerder drie ingangen dan drift, maar drie plekken die bij een wijziging alle drie mee moeten |
| 4 | **de beginschermOpen-vlag** | ux §LI023 r507–519 ↔ frontend §LI023 r1275–1284 — beide voluit (UX-regel resp. code-hoe), beide "aangescherpt LI046" | **grensgeval/twijfel** — de UX-/HOE-splitsing is het huispatroon, maar beide kanten dragen de volledige regel i.p.v. één kant + verwijzing |
| 5 | force-recreate ↔ resilience §P10 | tests r243 ↔ resilience r105 | **gedeeld feit, geen dubbeling** — al beslist deze sessie (stap 2.3) |

Expliciet: dit is een tekstovereenkomst-zeef plus sessie-kennis, **niet uitputtend** — een
volledige inhoudelijke paarsgewijze lezing van 9 skills viel buiten deze meting.

---

## Blok 3 — losse eenduidigheids-signalen (alleen gemeld)

### 3.1 Binnen-skill-signalen

- **Kop-naam-collisions (5):** dezelfde chronologische kopnaam komt 2× voor binnen één skill —
  backend "V016-patronen" (r370, r486) · frontend "LI034 —" (r1420, r1436) · frontend
  "LI046-patronen" (r1777, r1824) · ux "LI023 —" (r478, r521) · ux "LI046 —" (r1021, r1053).
  ⚠ Relevant voor de scan: een `§LI046`-verwijzing naar zo'n skill is **ambigu** — het
  fragment matcht op béíde koppen en de scan kan het verschil niet zien.
- **Norm-echo in ux:** §Kernprincipe (r9) en §"Functioneel beschrijven is de NORM" (r19)
  dragen allebei de UX-first-norm — dezelfde familie als de zojuist opgeruimde
  werkprotocol-binnendubbeling; komt vanzelf op tafel bij een ux-consolidatie.

### 3.2 Dode vindplaats-verwijzingen (steekproef: álle 165 bestandsverwijzingen gecheckt)

165 bestandsverwijzingen over de 9 skills, machinaal op bestaan getoetst: **164 bestaan, 1
niet** — `schemas/applicatie.py`, genoemd in **likara-backend r151 én r342** (de
validatie-helpers `_verplichte_tekst`/`_optionele_tekst`). Het bestand bestaat niet meer
(LI059 hief het applicatie-subtype op); de schemas-map draagt nu wél een `_validators.py` —
**vermoedelijk** de nieuwe woonplaats van die helpers, niet geverifieerd (dat is een
inhoudscheck voor de reparatie, geen meting).

### 3.3 Frontmatters (bevestigd, ongewijzigd sinds de vorige meting)

Alle 9 verouderd t.o.v. build V049: db **V015** (−34) · backend/resilience **V040** (−9) ·
security/tests/werkprotocol **V042** (−7) · domeinmodel/frontend/ux **V043** (−6). Vijf ervan
zijn deze sessie inhoudelijk gewijzigd zonder bump. Afsluitwerk.

---

## Blok 4 — bewaking

1. `git status` schoon · branch `master` · HEAD `5c4879a` · scan **5 passed**.
2. **De chronologie-kwaal ligt principieel buiten het scanbereik:** de scan toetst uitsluitend
   of een `skill §kop`-verwijzing op een bestaand anker landt — hij kent geen kop-sóórt en geen
   dubbeling. Een ux-consolidatie krijgt van de scan alléén de verwijzings-bewaking cadeau
   (zoals bij verhuizing 1, die domeinmodel:996 ving); wil Bert de kop-vorm zelf bewaken, dan is
   dat een nieuwe, aparte controle — of gewoon een menselijke ronde per skill, zoals nu.

## Wat je tegenkwam (buiten de vragen)

1. **De kwaal is groter dan de twee gesignaleerde skills deden vermoeden**: ux was tweemaal
   genoemd, maar backend (66%) en db (54%) zijn zwaarder — en db's frontmatter (V015) suggereert
   dat die skill het langst niet integraal is herzien.
2. **De woordelijke overlap tussen skills is verrassend klein** (2 regels): de cross-skill-
   dubbelingen zijn vrijwel allemaal inhoudelijk-met-eigen-bewoording — precies de soort die
   alleen een leesronde vindt, geen tekstscan.
3. **De kop-naam-collisions (3.1) zijn een scan-zwakte die nu pas zichtbaar wordt**: beperking 4
   dekte "geen skillnaam"; dit is een nieuwe variant — skillnaam mét kop, maar de kop bestaat
   2×. Geen van de huidige verwijzingen raakt er een (anders was iets al misgegaan), maar bij
   consolidatie van die skills verdient dit een plek in de afweging.
4. De dode `schemas/applicatie.py`-verwijzing (2×) is een klein, scherp reparatiegeval voor
   LI050 — zelfde familie als dev_seed §LI044 destijds: de verwijzing leeft, het doel niet meer.

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
