# Validatie — LI039-patronen tegen de code (fase A, read-only)

| | |
|---|---|
| **Opdracht** | LI039-patronen-valideren (fase A — toets vóór vastleggen; niets gewijzigd) |
| **Datum** | 2026-07-13 |
| **Methode** | Elk patroon geverifieerd tegen de code (bestand:regel), tegen de bestaande skills en ADR's. De code is canoniek; de aangeleverde formulering niet. |
| **Uitkomst in één zin** | 0 harde botsingen · 2 botst-risico's (27, en 3-deelclaim) · 26 kloppen (waarvan 10 al in een skill staan) · 6 besloten-niet-gebouwd · de eerlijke zwakteplek: 12 patronen leven straks alleen als tekst. |

---

## 1. De tabel

Oordelen: **KN** = klopt, nieuw · **KB** = klopt, bestaat al in een skill · **KD** = klopt deels · **NG** = nog niet gebouwd (besloten) · geen enkel patroon kreeg KLOPT NIET of BOTST als geheel.

### likara-ux / likara-frontend (1–12)

| # | Patroon | Oordeel | Bewijs | Bestaande skill-vindplaats | Bouwsteen |
|---|---|---|---|---|---|
| 1 | Vier knopvormen; max één primary | **KB** | `frontend/src/presets/Button.js:37-59` (text/outlined/danger/primary-default, docstring 7-15) | likara-frontend §Knopstandaard, "Wanneer-je-wat (LI039)" — **bestaand is vollediger** (noemt óók `secondary` als vijfde vorm + de pijl-conventie) | **Button.js-preset** (vormen); "max één primary" + pijl = alleen tekst |
| 2 | Rij-acties op de actieve rij; touch permanent; danger houdt vorm | **KB** | `RijActies.vue:1-23`; `main.css:79-88` (hover/`:focus-within`/`@media (hover: none)`); danger-behoud: RijActies-docstring 12-15 + verwijder-knop in `BedrijfsfunctieLijst.vue` | likara-frontend §Knopstandaard (RijActies-bouwsteen) — even scherp | **RijActies.vue + main.css `.lk-rij*`** |
| 3 | Tweelaags rij (scan + lees, 2 regels, woordgrens, **eerste zin intact**) | **KD** | Scan/lees-laag: `main.css:101-123` (`.lk-rij-kop`/`.lk-rij-definitie`, `line-clamp: 2`), `BedrijfsfunctieLijst.vue:800-840` | geen | `.lk-rij-*`-CSS (gedeeld met het processen-scherm) |
| | | | ⚠ **"eerste zin intact" is NIET geborgd**: `line-clamp: 2` kapt na twee regels ongeacht zinsgrens — een lange eerste zin wordt middenin geknipt. De CSS-comment claimt terecht alleen "woordgrens + ellipsis". Deze deelclaim niet opschrijven. | | |
| 4 | Vaste actiekolom rechts — nooit een knop buiten beeld | **KN** | `main.css:96-130` (`.lk-rij { flex-wrap }`, `.lk-rij-acties { flex:0 0 auto; wrap }` + comment "knoppen vallen nooit buiten beeld") | geen | **main.css `.lk-rij`-contract** |
| 5 | Herkomst één keer boven de lijst; rij toont alleen de afwijking | **KN** | `BedrijfsfunctieLijst.vue:118-128` (`modelHerkomst`, data-gedreven) + template `functie-model-herkomst`; rij-badges alleen `eigen`/`vervallen` (:819-831) | geen | geen (schermlogica) |
| 6 | "Wat je zojuist vastlegde, zie je altijd" — alle vijf onderdelen in `useToonNieuweRij`? | **KD** | `useToonNieuweRij.js`: pad open (:93-107), filter wijkt zichtbaar + banner (:108-113, 77-83), aanstip (:43-67), scroll alleen-als-nodig/mét omgeving/zacht (:34-41). **Vier van de vijf zitten in de bouwsteen.** Het vooraan-invoegen-bij-paginering leeft in de consumenten (DatatypeSectie/GebruikersgroepSectie/KoppelingSectie); de composable levert daarvoor alleen de aanstip als drager (:9-12) | geen | **useToonNieuweRij.js** (4/5); invoeg-gedrag = consument |
| 7 | Signalen gescheiden: gap gestippeld · vervallen warning solid · combi gestippeld-warning · eigen kanaal per signaal | **KN** | `ProcesDiagram.vue:45-55` (gescheiden props `gapIds`/`vervallenIds` + combinatieregels in comment), :337 (dashed), :105 (warning-hex); rij-badge kleur+⚠+tekst `BedrijfsfunctieLijst.vue:826-831` ("gestippeld blijft van de gap-familie") | geen | **ProcesDiagram-props** (twee kanalen structureel gescheiden); kleurtaal deels afspraak |
| 8 | Lege uitkomst ≠ fout; nooit beide; één toestandsvariabele | **KN** | `BedrijfsfunctieLijst.vue` (`aanbodStaat`-enum-ref, op één plek per pad gezet; template vertakt exclusief) + gedragstests `BedrijfsfunctieLijst.test.js` §B2 (leeg→geen fout; fout→geen leeg) | geen (P8 in likara-ux gaat over filters — verwant, niet hetzelfde) | enum-ref **per scherm** — géén generieke bouwsteen (zwakteplek: elk volgend scherm moet het patroon zelf herhalen) |
| 9 | Kern-inhoud nooit in een tooltip | **KN** (norm) | `main.css:117-118` ("Geen tooltip, geen uitklap: zichtbaar zonder muisbeweging"); definitie op de rij + in de popup (`functie-popup-definitie`) | geen | geen (norm) |
| 10 | Geen doodlopend pad | **KN** | Vervallen rij houdt "Toon in functiebeeld" (onvoorwaardelijk, `BedrijfsfunctieLijst.vue:866-873`; mutaties wél geguard op `!vervallen`); onvoltooide inlees afrondbaar bij 0 wijzigingen (disabled-conditie met `!inleesOnvoltooid`); popup bestaat op inhoud óók zonder uitgang (test :415-429) | geen | geen (per-scherm-ontwerp) |
| 11 | Geen affordance die faalt — én geen stille filtering; pickers weren vooraf **én leggen uit waarom** | **KD** | Weren vooraf ✓: `zoekPlaatsDoelen` (:399-411) spiegelt PLAATSING_BESTAAT/kring/vervallen; `plaatsZin` (:417-421) legt uit **wat er gebeurt**. ⚠ De picker legt **niet uit wáárom opties ontbreken** — de uitgesloten functies verdwijnen zonder toelichting. De tweede helft van de claim is niet gebouwd. | likara-frontend §ZoekSelect-patronen regel 1 (weren vooraf) — bestaat al, even scherp | consument-filter (geen structurele borging) |
| 12 | Boom-diagram links→rechts + haakse lijnen; meervoud als verwijzing | **NG** (verwacht) | Huidige code doet het **anders**: top-down (`procesBoomLayout` rij=diepte, :88-110) en meervoud = **álle plaatsings-lijnen getekend** (`ProcesDiagram.vue:112-115`). Het besloten ontwerp vervangt die gedraging — als *besloten* markeren mét de huidige staat erbij. | geen | n.v.t. |

### likara-domeinmodel (13–19)

| # | Patroon | Oordeel | Bewijs | Bestaande vindplaats | Bouwsteen |
|---|---|---|---|---|---|
| 13 | Plaatsing = eerste-klas feit; meervoud tonen | **KN** | `models.py:762-806` (geen ouder-kolom; ADR-044-docstring), `bedrijfsfunctie_service.py:114-180` (plaatsings-facade), migratie 0063; meervoud getoond: "staat ook onder" (`BedrijfsfunctieLijst.vue:840-860`) + alle diagram-lijnen | likara-domeinmodel is t/m V038 — **ADR-044 ontbreekt er nog** | **schema** (partial UNIQUE op `relatie`) + service-facade |
| 14 | Verfijnen vervángt grof op die plek; "erbij" = meerdere componenten op één plaatsing | **NG** | Besloten: **ADR-044 besluit 2** (:75-110). Geen koppel-code (geen functie-vervulling-tabel — geverifieerd afwezig) | ADR-044 | n.v.t. (gate 2) |
| 15 | "Hier gebruiken we niets" = bevinding ≠ "nooit naar gekeken" | **NG** | Besloten: **ADR-044 besluit 3** (:111-126) | ADR-044 | n.v.t. |
| 16 | Gap-signaal hangt aan de plaatsing | **NG** | Besloten: **ADR-044 besluit 4** (:127-140) | ADR-044 | n.v.t. (gate 3) |
| 17 | "Ondersteunt werk" = eigenschap van het componenttype, geen lijst in code | **NG** — besloten, **ADR ontbreekt** | Geen vindplaats in ADR-043/044 (grep leeg) — alleen sessie-besluit. Precedent voor het mechanisme bestaat wél: `checklist_dragend` op `componentconfig_optie` (eigenschap van het type) | geen | n.v.t.; markeren als *besloten, ADR nog te schrijven* |
| 18 | Referentiemodel: bronsleutel=identiteit · read-only · vervallen≠verwijderen · aanbod gesloten/motor generiek | **KB** (als *besloten*; nu **gebouwd**) | Identiteit: `uq_bedrijfsfunctie_bron` (models.py:778-780) + `_bepaal_plan` matcht op sleutel; read-only: `MODELINHOUD_BESCHERMD` (`bedrijfsfunctie_service.py:278-300, 344-351`); vervallen: `voer_uit` stap 3 + verwijder-weigering (:295-300); gesloten/generiek: `ameff.py` (modelonafhankelijk) + `_AANBOD_BESTANDEN` + `referentiemodelconfig`-route zonder POST + `HERKOMST.md` | likara-domeinmodel §LI038 ("Modelinhoud lees je…") — als **besloten** tekst; formulering klopt, mist nu de gebouwde vindplaatsen + de repo-route | **CHECK/UNIQUE + service-sloten** (via_import als enig legitiem pad) |
| 19 | Koppel-UX bij meervoud (één zoekresultaat, "geldt overal" voorop, …) | **NG** | Besloten (ADR-044 besluit 2, UX-tabel); geen code | ADR-044 | n.v.t. (gate 2) |

### likara-werkprotocol (20–27)

| # | Patroon | Oordeel | Bewijs | Bestaande vindplaats | Bouwsteen |
|---|---|---|---|---|---|
| 20 | Claude/PNA besluit nooit autonoom dat een sessie sluit | **KB** | — (procesregel) | CLAUDE.md §Sessiebewaking (DC016: "de gebruiker beslist") + likara-tests §Afsluitprotocol ("Claude bepaalt nooit zelf…") — even scherp | geen |
| 21 | Hypothese van de PNA ≠ bouwopdracht; valideer/falsificeer eerst | **KB** | Vandaag 2× herbewezen: leeg-aanbod-hypothese ("dev-seed vult aanbod") weerlegd — `platform_init.py:80` + migratie 0061 vullen het | likara-werkprotocol §Read-only-eerst (ADR-040) — even scherp; LI039-bewijzen zijn toevoegbaar | geen |
| 22 | Reikwijdte-scan vóór afbakening; **telling vóór besluit** | **KD→KB** | Scan bestaat al (werkprotocol §Reikwijdte-scan LI037). De **telling-helft is nieuw** en feitelijk toegepast: de 7 meervoudige functies zijn geteld vóór het ADR-044-besluit (Verkenning §B1) | werkprotocol LI037 (eerste helft) | geen |
| 23 | Bouwsteen-convergentie: tweede export in dezelfde module, consument byte-compatibel | **KB** + nieuwe verfijning | `procesBoom.js:26` (`procesBoomStructuur`) + `:62` (`meervoudBoomStructuur`) in één module; `ProcesLijst.vue:27,101` ongewijzigd op de oude export | werkprotocol §KERNLES LI038 + likara-frontend LI037 ("nooit een derde boom-opbouw") — de tweede-export-vorm is de nieuwe, concretere invulling | **procesBoom.js** zelf |
| 24 | Groene tests ≠ sign-off; UI-pad zonder openende test = structureel testgat | **KB** + aanscherping | — | werkprotocol §Browsercheck (LI032) + likara-tests LI030 — eerste helft bestaat; de testgat-formulering is nieuw (→ 28) | geen |
| 25 | Nieuwe dependency → image herbouwen (in het gate-rapport) | **KN** | `requirements.txt:14` (defusedxml) + het incident: api-500 tot `docker compose build api` (verse-herstart stap 1) | geen | geen (procesregel) |
| 26 | Migratie hoort bij de slice — mismatch legt de API plat | **KD** (kern klopt; formulering behoeft precisering) | Incident-log: `GET /api/v1/referentiemodellen → 500`, `UndefinedColumnError: inlees_voltooid` (migratie 0064 wel gebouwd, niet toegepast). ⚠ Precisering: model + migratie wáren samen gebouwd — het gat was dat de slice onderbroken werd vóór het **toepassen**. De regel moet dus zijn: bouw én toepassing landen samen, vóór de code actief wordt | geen | deels: lk-migrate past bij stackstart automatisch toe; het gat is lokaal draaiende code zonder upgrade |
| 27 | Testdata in een eigen test-tenant, nooit in de dev-tenant | **KD — botst-risico, zie §2** | Nieuwe import-tests: eigen tenant `9999…` mét motivering (`test_referentiemodel_import_gate1b.py:30-33`) | likara-tests: "nieuwe live-DB-tests altijd self-contained (WT-fixtures + finally)" — de bestaande norm | test-harnas per bestand |

### likara-tests (28–29)

| # | Patroon | Oordeel | Bewijs | Bestaande vindplaats | Bouwsteen |
|---|---|---|---|---|---|
| 28 | Elk UI-pad dat de gebruiker opent heeft ≥1 test die hem opent | **KN** (norm; voor LI039-paden nageleefd) | Popup-tests (`BedrijfsfunctieLijst.test.js:415-432`), inlees-dialog-tests (§gate 1b + §B2 + §onvoltooid), plaats-dialog-tests | geen | geen — blijft discipline |
| 29 | Gedragstests boven payload-tests (assert de vorm) | **KB** + aanscherping | Vorm-asserts bestaan feitelijk: `expect(…).props('outlined')).toBe(true)` (:325-329) | likara-tests LI030 ("toets ook de visuele/interactie-staat") — de vorm-assert (doorklik vs. mutatie) is de nieuwe concretisering | geen |

### likara-backend / likara-db / likara-resilience (30–32)

| # | Patroon | Oordeel | Bewijs | Bestaande vindplaats | Bouwsteen |
|---|---|---|---|---|---|
| 30 | Bulk-schrijven ORM-matig, nooit SQL-upsert (audit) | **KB** | `referentiemodel_import_service.py` docstring + `voer_uit` via de facade; audit-bewijs: creates/updates/deletes in `audit_log` | likara-backend §LI035 "Audit-dekking is ORM-dekking" — **al even scherp**; hooguit de import als voorbeeld toevoegen | audit-flush-hooks (`app/core/audit.py`) |
| 31 | De generieke relatie-facade valideert géén elementtypen | **KB** | Nieuw voorbeeld: `bedrijfsfunctie_service._vereis_bedrijfsfunctie` (:101-111) — typeborging in de **specifieke** facade | likara-domeinmodel §"Type-validatie bron/doel — LEEFT NIET in de relatie-facade (V030)" — **al exact**; voorbeeld toevoegbaar | specifieke facades |
| 32 | Langlopende actie met deel-commits: zichtbaar begin/eind · markering + eerlijke melding + hervat-route · geen auto-herstart | **KN** | `models.py` (`inlees_voltooid` + docstring); `voer_uit` begin-markering (False vóór eerste schrijf) + eind (True in de snapshot-commit); banner + "Inlezen afronden"-knop (beheerder-only), medewerker signaal-zonder-actie; geen automatische herstart (alleen de knop); migratie 0064; gedragstest `test_afgebroken_inlees_herkend_en_hervat_live` (incl. crash-vóór-vervallen-randgeval) | geen (likara-resilience kent niets vergelijkbaars) | **kolom + service-markering** (server-side afgedwongen); de melding zelf = consument |

---

## 2. Botsingen en botst-risico's — het belangrijkste deel

**Harde botsingen (strijdig met skill/ADR): geen.**

**Botst-risico 1 — patroon 27 in absolute vorm.** "Testdata **nooit** in de dev-tenant" is strijdig met de bestaande, door likara-tests gedekte praktijk: vrijwel de hele live-suite draait in de dev-tenant met self-contained WT-fixtures (o.a. `test_bedrijfsfunctie_adr043.py`, `_TID = 1111…`). De werkelijke les van deze sessie is scherper afgebakend: **een eigen test-tenant is verplicht zodra de teardown breder veegt dan de eigen fixtures** (de import-teardown ruimt álle functies van het model op — die at de geseede dev-boom op); waar de teardown zich tot eigen WT-rijen beperkt, volstaat de bestaande self-contained-norm. In de absolute vorm zou het patroon een herbouw van tientallen bestaande tests impliceren zonder aanleiding. **Niet zelf verzoend — besluit aan Bert:** absolute regel (met migratie-consequentie) of de afgebakende vorm.

**Botst-risico 2 — patroon 3, deelclaim "eerste zin intact".** De implementatie kapt op twee regels met `line-clamp` (woordgrens + ellipsis); een zinsgrens-garantie bestaat niet en is met pure CSS ook niet te leveren. De deelclaim hoort niet in de skill; de rest van het patroon wel.

Geen botsing maar vervangings-markering: **patroon 12** — de huidige code doet aantoonbaar iets anders (top-down; meervoud = alle lijnen). Het besloten ontwerp vervangt dat; bij vastleggen expliciet als *besloten, vervangt huidige gedraging* markeren, anders lijkt de skill de code te beschrijven.

## 3. "Klopt niet" — wat de code werkelijk doet

Geen enkel patroon is als geheel KLOPT NIET. De drie deel-afwijkingen: §2 (3-deelclaim), patroon 11 (de picker **legt niet uit waarom** opties ontbreken — alleen wat er gaat gebeuren), en patroon 26 (het incident was een *toepassings*-gat, geen bouw-gat — formulering preciseren).

## 4. Regels zonder bouwsteen — de eerlijke zwakteplek

Deze patronen leven na fase B **alleen als tekst** (LI038-kernles: dat is de zwakke vorm):

| Patroon | Zwakteplek |
|---|---|
| 1 (deels) | "max één primary per scherm" + pijl-op-doorklik: alleen afspraak |
| 5 | herkomst-één-keer: schermlogica, geen gedeelde drager |
| **8** | **de aanbodStaat-enum is per scherm herbouwd** — een generieke "laad-toestand"-bouwsteen bestaat niet; het volgende scherm kan de overlap-bug opnieuw maken |
| 9, 10 | normen zonder structurele drager |
| 11 | weren = consument-filter per picker; de uitleg-helft bestaat niet |
| 20–22, 24–26, 28 | procesregels — per definitie tekst; 26 heeft wél de lk-migrate-keten als gedeeltelijk vangnet |
| 29 | vorm-asserts zijn per test een keuze |
| 32 (deels) | de banner/melding is per consument; alleen de markering zelf is afgedwongen |

Sterk geborgd (bouwsteen aanwezig): 2, 3-kern, 4, 6 (4/5), 7, 13, 18, 23, 30, 31, 32-kern.

## 5. Voorstel per patroon — plek (fase B; nog niets geschreven)

- **likara-frontend**: 3 (zónder eerste-zin-claim, §nieuwe LI039-sectie bij het rij-contract), 4 (zelfde sectie), 6 (§bouwstenen — useToonNieuweRij, incl. de consument-grens), 7 (§ProcesDiagram-kanalen), 8 (aanbodStaat-patroon + de zwakteplek benoemen), 12 (als *besloten, vervangt huidige gedraging*). 1–2: bestaan al — alleen desgewenst de pijl-conventie expliciteren.
- **likara-ux**: 5 ("informatie die overal hetzelfde is…"), 9, 10, 11 (bestaande picker-regel aanvullen met: de uitleg-helft is **niet gebouwd** — besloten of laten vallen, aan Bert), 19 (besloten, gate 2).
- **likara-domeinmodel**: 13 (ADR-044-sectie), 14–16 (als *besloten* met ADR-044-besluitnummers), 17 (als *besloten, ADR nog te schrijven*, met het checklist_dragend-precedent), 18 (status besloten→gebouwd + vindplaatsen/repo-route).
- **likara-werkprotocol**: 21–22 (LI039-bewijzen + telling-aanscherping), 23 (tweede-export-vorm), 25, 26 (in de gepreciseerde vorm), 20+24: bestaan al — niets doen.
- **likara-tests**: 27 (in de **afgebakende** vorm, na Berts besluit), 28, 29 (vorm-assert-concretisering).
- **likara-backend**: 30 (alleen het import-voorbeeld bij de bestaande regel). **likara-domeinmodel**: 31 (alleen het nieuwe voorbeeld).
- **likara-resilience**: 32 (nieuwe sectie "langlopende actie met deel-commits").

---

**Open besluiten voor Bert vóór fase B:** (a) patroon 27 — absoluut of afgebakend; (b) patroon 11 — de uitleg-helft als *te bouwen* vastleggen of laten vallen; (c) patroon 3 — akkoord dat de eerste-zin-claim vervalt.
