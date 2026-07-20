# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V048 · 2026-07-20
- **Commit:** code `134fd6c` seedherstel + verantwoordingszin · `218b9fd` kopknop + één ingang ·
  `529c122` koppelingen component-breed · `e89a417` open-punten-tabblad · `14e1dbe` `component_id` ·
  `388f3da` ADR-055 gebouwd · `1dfe435` kopstijl + kop-rij; docs/skills `f11fd1c` LI047-patronen ·
  `56aa06f` ADR-055 + register · `e26d150` checkpoint gebruik-component-breed.
- **Tests:** backend **1179 passed, 2 skipped, 0 failed** · frontend **98 files / 1275 passed** ·
  `vite build` ✅ · `test:css-build` ✅ (vier bronscans, elk met zelftest) · 0 kritieken.
- **Migratie-head:** `0073_adr052_klaarverkl_snapshot` (1 head, 0 branches). LI047 raakte **backend én
  frontend** maar leverde **nul migraties**: ADR-055 en de `component_id`-hernoeming bleken allebei
  applicatielaag-restanten — dat het schema níét meebewoog was in beide gevallen het bewijs.
- **TST-rapport:** `docs/TST-V048-Validatierapport.md` (0 kritieken, 0 geaccepteerde afwijkingen).
- **Dev-DB:** volledig opnieuw opgebouwd deze sessie (`down` → `volume rm` → `up` → dev-seed). De seed
  draagt nu álle browsercheck-gevallen: **HR-systeem = SCHOON** (norm-compleet, géén signaal) ·
  Archiefbeheer/DMS/Zaaksysteem = beide soorten afwijking · Klantportaal = pure verschoven lat ·
  drie "bewust geen"-bevindingen · **Shared fileshare mét gebruikersgroep** (het ADR-055-geval, nieuw) ·
  Zaaksysteem mét een nee-checklistscore (de gebundelde regel in "Dit valt op"). ⚠ Het volledige
  gate-3-verhaal (koppelingen, "hier draait niets", noodoplossing) is op een verse DB nog onzichtbaar (L4).
- **⚠ Tellingen in gate-rapporten zijn momentopnamen, geen stand.** Wie ze later overneemt zit ernaast —
  hermeten binnen de tenant-context is de regel. Ging deze sessie drie keer mis (werkprotocol
  §Meet tenant-data binnen de tenant-context).
- **Werktree:** **schoon** — alle LI047-bouw is per opdracht apart geland (één opdracht per commit).

## Deze sessie (LI047 — alles wat dit component nog nodig heeft, op één plek) — AFGEROND

**Kern: de consultant ziet per component wat er nog nodig is met een weg erheen; wat hij bewust heeft beantwoord telt als beantwoord; en registreren kan nu bij élk componenttype.**

- **Open-punten-overzicht per component** (`e89a417`/`218b9fd`). Drie blokken uit ÉÉN afleiding
  (`component_open_punten_service`): "Dit moet nog" (verplichte norm-feiten), "Dit zou netjes zijn"
  (dezelfde bepaling, andere lat) en "Dit valt op" (checklist-nee/deels **gebundeld** tot één regel,
  en "staat los in het landschap"). Per punt een route naar de plek waar je het vastlegt. Ingang =
  **één knop in de kop** met een teller die niet uit de pas kán lopen met de lijst (één laadpunt,
  doorgegeven als prop); bij nul draagt de knop géén getal. Het rode signaleringsbolletje is weg —
  twee tellers met verschillende getallen over hetzelfde component was een tweede waarheid.
  Een bewuste vaststelling dempt óók blok 3, anders sprak het scherm zichzelf tegen op het schone geval.
- **ADR-055 — de gebruik-verfijning is component-breed** (`388f3da`). "Welke afdeling gebruikt dit"
  geldt voor élk componenttype dat werk ondersteunt, niet alleen applicaties. De beperking bleek geen
  domeinregel maar een restant van de opgeheven applicatie-subtabel; ADR-041 had dezelfde herziening
  één laag hoger al gedaan. Grens = de catalogus-vlag `ondersteunt_werk` (nooit een typelijst).
  Geen bepaling verschoof, geen schemawijziging; het signaal ging van 12 naar 11 componenten.
- **Koppelingen bij elk component** (`529c122`). Idem voor de koppelingen — anders droeg het
  open-punten-overzicht een regel die de gebruiker nooit kon wegwerken. Ook de picker en de namenkaart
  verbreed: een tabblad zonder picker en zonder namen is geen plek.
- **`component_id` i.p.v. `applicatie_id`** (`14e1dbe`) + de foutmelding die "applicatie" zei.
  Wat je zelf onwaar maakt, herstel je in dezelfde commit.
- **Kopstijl + kop-met-uitleg-rij** (`1dfe435`). Eén bron voor de titelmaat (30 h1's kozen zelf, 17 op
  2xl en 13 op xl — het beheer las als een ander product) en één gedeelde rij voor de kop met zijn
  uitleg-icoon (acht keer met de hand nagebouwd, dus overal 6px scheef).
- **Seedherstel** (`134fd6c`). De hernoeming miste twee aanroepen in de dev-seed; die crashte en het
  demolandschap was niet meer op te bouwen — **geen van de 1176 groene tests raakte het**. Hersteld,
  plus een repo-brede scan die élke aanroep van een `extra="forbid"`-schema tegen de schemavelden houdt.
- **Borging:** vier bronscans in `check-css-build.mjs` (elk met zelftest die bewijst dat hij bijt),
  de schema-aanroepscan, en dertien patronen in vier skills (`f11fd1c`).
- **Open (besluit Bert):** de namenkaart zonder paginering en `organisatiegebruik.applicatie_id` — beide
  **vóór productie**; de vrijgekomen `SignaleringBadge`-opruiming; en **consolidatie van het
  werkprotocol** (595 regels, vier nieuwe koppen onder één sectie) — punt 0 in NEXT_SESSION.

## Sessie LI046 (de kaart vertelt, het component verandert) — AFGEROND

**Kern: één ingang naar het detailscherm mét aanleiding; een linkerkolom alléén bij een getekende kaart; relaties gescheiden op hoedanigheid.**

- **ADR-054 — één ingang naar het detailscherm** (`80d0038`/`4dd1387`/`466eb7b`/`61665a4`/`9ee6fcb`).
  Gedeelde detail-ingang (`detailRoute`), de aanleiding in de URL, geen route zonder landing, het veld-anker
  (`?veld=`) markeert; per-ring-popup-takken; terugkeer landt bij het bewaarde beeld met een eerlijke melding
  bij een volledig verdwenen selectie (`lk-leeg-verdwenen`). Beginscherm-binnenkomst als één eenmalige regel
  ná de beslisboom (`3b7941f`, "de bezoeker wint").
- **Linkerkolom-gate** (`3a72b35`). De kijkinstellingen-kolom (`aside`) draagt `v-if="heeftData"` — bewust
  níét `!beginschermOpen`; kijken ≠ binnenkomen. Opgeslagen kijken + beheer naar het startpaneel
  (`KaartBeginscherm`, ✎/× + `magViewsBeheren`); Rol/BIV achter een inklap.
- **Relaties gescheiden op hoedanigheid** (`6651f1f`). `kaartBanen.js`: `hoedanigheidVan()`
  (roltoewijzing→beheer, anders relatietype), `baanVerdeling()` waaiert edges per knopenpaar met
  richting-gecorrigeerde `cpd` (`unbundled-bezier`); ná de instance-projectie (Lagen-veilig). Klik op een
  baan levert **alles** onder dat paar (`popupPaarLijst`). Ring-agnostisch — invariant boven afspraak.
- **Borging:** LI046-patronen in vier skills (`aca7cb1`/`70f2cbb`); vier read-only checkpoints (`f7929a9`/
  `bf67e67`); ADR-register 049–054 + statuscorrectie ADR-049/050/051 (kop+body).
- **Open (ontwerpbesluit Bert):** terugweg-fijnslijpen — org-scope/Rol-BIV/weergave/zoom-pan reizen niet mee
  terug; view-verwijderen zonder bevestiging; "selectie bijwerken" onbereikbaar; "bewust geen" niet in het
  gebruiksdata-model (OPVOLGPUNTEN §LI046).

## Sessie LI045 (de gemeente legt haar eigen lat, geen besluit toegeschreven) — AFGEROND

**Kern: de beheerder ziet en verzet de norm nu zelf; een verschoven lat leest niet meer als een keuze van de consultant.**

- **ADR-052 slice 4a/4b/4c.** Verschoven lat (neutraal) onderscheiden van bewuste afwijking (amber, `aaeeb15`);
  norm-beheerscherm met impact-voorspelling vóór opslaan + "wanneer/door wie" uit het audit-spoor (`d748fcf`);
  de lat zichtbaar tijdens invullen — één norm-"i" per feit op het kleinste omvattende element (`f8a9142`).
- **Integrale testronde** (`docs/TST-Normverhaal-V045.md`): 0 blokkerend · 1 storend (S1, gerepareerd
  `6a0931a` — HR-systeem als schoon ijkbeeld + borgtest) · 2 cosmetisch (C1 gerepareerd `3e74a47`
  — feit-brug; C2 bewust gelaten met reden).
- **ADR-053 (besloten, niet gebouwd):** Archiefwet als hard componentfeit (eigen enum, niet default-verplicht);
  bewaartermijn volgt uit zaaktype × resultaat → géén component-veld (grens vastgelegd).
- **Borging:** LI045-patronen in vier skills (`0c7860d`); frontend-skill-drift (VeldUitleg-adoptie) gecorrigeerd.

## Sessie LI044 (tenant-norm gebouwd, procesregister-UI gesloopt) — AFGEROND

**Kern: de gemeente kan nu haar eigen lat voor "migratieklaar" leggen; het procesregister is uit de MVP-UI.**

- **Gate-4 sloop (`c82ad80`).** Procesregister uit de MVP-UI: nav, routes, `ProcesLijst`/`ProcesDetail` +
  secties, `PartijProcessenSectie`, `ComponentProcessenSectie`, de kaart proces-ingang/-inzoom-handoff, de
  chip "Proceslandschap: X" en de doodlopende "Bekijk op kaart" opgeruimd. **Behouden:** datamodel
  (`proces`/`procesvervulling`), bouwstenen (`procesBoom`/`ProcesDiagram`/`useSleepbaar`), slapende
  backend-endpoints, bedrijfsfunctie-plek-machinerie. Concept geparkeerd (ADR-043), niet verwijderd.
- **ADR-052 tenant-norm — slice 1 (`fae7593`).** `component_norm` (tenant-scoped, RLS, migratie 0071);
  `HARDE_FEITEN` (10) + `DEFAULT_VERPLICHT` (eigenaar · verantwoordelijke · BIV · contract · koppelingen);
  `norm_status`-leesbron: "vastgesteld = echt antwoord" (sentinel `hostingmodel=onbekend` telt niet).
- **Slice 2 (`626dc76`).** "Bewust geen" voor koppelingen/contract: eigen `component_bevinding` (0072),
  write-guard (409 `REGISTRATIE_BESTAAT`) + read "real wins"; frontend geconvergeerd → één
  `BewustGeenControl.vue` (2 consumenten); generieke `relatie_service` onaangeroerd.
- **Slice 3 (`7e2ff25`).** Verrijkte klaarverklaring: snapshot-kolom `open_feiten` (0073); drempel alléén
  bij norm-afwijking; live badge vs. bevroren snapshot uit één definitie; klikbaar verantwoordingsvenster
  (3b); reden achter de waarschuwing i.p.v. permanent bij de status (3c); gedeelde `popoverPositie.js`
  (venster valt nooit buiten beeld, rekenkern puur + unit-getest). Engine ongemoeid (dubbele borging groen).
- **Borging (`f0fa9bd`).** LI044-patronen in vijf skills (W4/U1/U2/U3/D1/D2/D4/D5/D6/U4a + tests +
  werkprotocol). ADR-052 teruggevouwen naar de gebouwde realiteit. ADR-045 besluit 2 / "fileshare = gat"
  gemarkeerd verworpen (ADR-051 besluit 3); OPVOLGPUNTEN item 10 vervallen.

## Vorige sessies — AFGEROND
- **LI043** — gate-4 kaart-lezing (slice 2 → A → B1 → B2, `standCodering`), serving-richting-fix,
  brok-3 dev-seed, naam-fix "Beoordelingsstatus", zes sessiepatronen.
- **LI042** — gate 4 brok 1 (datalaag, `heeft_gebruikersgroep` + 5e stand `werkvoorraad`), skill-vastlegging.
- **LI041/LI040** — gate 2 koppelen + gate 3 vier standen + rollengrens ADR-050 · ADR-045/046.

## Prioriteiten volgende sessie (LI048 — zie NEXT_SESSION.md)
0. **Consolideer het werkprotocol vóór je er iets bij zet** — 595 regels, vier nieuwe koppen onder
   §Gate-discipline na LI047. Een protocol dat niemand meer leest geeft schijnzekerheid; elke discipline
   die erop leunt, leunt dan op niets. **Wie er patronen bij wil zetten, consolideert eerst.**
1. **Archiefwet-feit bouwen (ADR-053)** — eigen enum-kolom + migratie, niet default-verplicht (raakt schema → gate).
2. **Laatste MVP-laag functie-as (ADR-046 stuk 3 → 5 → 4)** — uitstap-stand/zwaarte/tranche.
3. **ADR-register bijwerken naar de gebouwde realiteit** — ADR-052/054 verdienen een statusregel die
   klopt met wat LI047 heeft opgeleverd.
4. **Terugweg-fijnslijpen** — wat hoort in `lk-state` (org-scope/filter/weergave/zoom-pan); view-verwijderen + selectie-bijwerken (ontwerpbesluit).
5. **Dev-seed: het gate-3-verhaal (L4-restant)** — koppelingen/"hier draait niets"/noodoplossing; een
   partij die eigenaar én gebruiker is met meerdere beheerrollen; een knooppaar met relaties van meerdere
   hoedanigheden (cross-ring overlap komt 0× voor in de dev-data). *Het schone geval (S1) en het
   fileshare-geval (LI047) staan er inmiddels wél.*

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
