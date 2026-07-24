# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V052 · 2026-07-24
- **Commit:** `319b606` (zoekterm opschonen — categorie-regel + import) + de LI051-afsluitcommit.
  Kern-commits LI051: `6007c2f` invoer-weerbaarheid + accent-ongevoelig zoeken · `319b606`
  zoekterm-opschoning (onzichtbare tekens weg, spatie blijft spatie); daarvóór in LI051 o.a.
  ADR-056 snede 1 (vraag bevroren) + de LI051-ADR-056-aanscherping.
- **Tests:** backend **1297 passed / 2 skipped** (repo-root, incl. kopverwijzingen-scan) ·
  frontend **107 files / 1460 passed** · `vite build` ✅ · `test:css-build` ✅ (14 scans) ·
  0 kritieken.
- **Migratie-head:** `0077_li051_unaccent` (1 head, 0 branches). **Migraties in LI051:**
  `0076_adr056_vraag_bevroren` (bevroren formulering + stille notitie + nulpunt-backfill) ·
  `0077_li051_unaccent` (installeert de `unaccent`-extensie voor accent-ongevoelig zoeken).
- **RLS:** 38× ENABLE ROW LEVEL SECURITY in de offline upgrade-SQL (TST-V052-telling).
- **TST-rapport:** `docs/TST-V052-Validatierapport.md` (0 kritieken; 4/4 assen geslaagd).
- **Werktree:** afsluitcommit LI051 loopt (NEXT_SESSION/OPVOLGPUNTEN/PROJECTGEHEUGEN + skill-lessen
  + TST-V052 + de gen_build-output).
- **⚠ KOERS blijft: productieversie.** Scherpste punt (OPVOLGPUNTEN N50-2 / L51-3):
  **`changeme_dev`-defaults + testaccounts vallen in productie stil door — niets houdt dit tegen**
  (`validate_startup_config` checkt alleen aanwezigheid). Harde deploy-voorwaarde vóór de eerste
  echte tenant.
- **ADR-056 (vraagevolutie): snede 1 GEBOUWD** (formulering bevroren, sein, opnieuw antwoorden,
  vraag-geschiedenis, tabbladgetal telt beide, stille notitie, nulpunt). **Nog open (eerste
  LI052-besluit, vóór nieuw werk):** snede 2 (opties onder dezelfde regel/sein + optie-moment +
  heractiveren + antwoordtype-slot-frontend; schemastap), snede 3 (verouderd-teller per vraag/
  categorie; schemaloos), en de vier resterende subknopen. Gemeten reststand: NEXT_SESSION.md.
- Skill-opschoning blijft uitgesteld (`docs/Opschoonplan-zeven-skills.md`).

## Deze sessie (LI051 — wat een gebruiker intypt komt terug zoals bedoeld, en vragen mogen evolueren) — AFGEROND

**Eén draad:** de tekst die een gebruiker intypt of plakt wordt betrouwbaar behandeld — bij zoeken,
bij vastleggen en bij het importeren — en de checklist-vraag mag evolueren zonder een uitspraak toe
te schrijven aan wie haar niet zag.

**Wat er is gebouwd:**
- **Invoer-weerbaarheid + accent-ongevoelig zoeken** (`6007c2f`): nul-/stuurtekens geweigerd bij het
  vastleggen (gedeelde plek, NFC); zoeken negeert accenten over alle tien zoekpaden via één gedeelde
  bron; de app **weigert op te starten** als de `unaccent`-DB-functie ontbreekt (migratie 0077 +
  startcontrole `app/core/zoekfunctie.py`).
- **Zoekterm-opschoning — de categorie-regel** (`319b606`): onzichtbare tekens (NBSP, brede spaties,
  zero-width, BOM, stuurtekens) worden per **Unicode-categorie** afgehandeld (Zs→spatie zodat de
  woordgrens blijft, Cf/Cc weg, samenvouwen+trimmen) — niet als lijst codes. Eén gedeelde regel
  (`schemas/tekstschoning`) voor zoeken, vastleggen én de GEMMA-import (bij de parser-uitvoer,
  `services/ameff` — dichtte een idempotentie-bug: aanmaken schoonde op, bijwerken niet). Melding
  "onzichtbare tekens weggehaald" op alle acht zoekvelden, alleen als er iets verdween.
- **ADR-056 snede 1** (eerder in LI051): formulering bevroren bij het antwoord (migratie 0076), één
  neutraal sein per vraag, opnieuw antwoorden dooft het sein, vraag-geschiedenis als leesingang voor
  de consultant, tabbladgetal telt beide soorten werk, stille notitie bij verduidelijking, nulpunt bij
  invoering. ADR-056 zelf aangescherpt (18 besluiten).

**Borging (de scherpste les):** een groene toets op een te smalle voorbeeldenreeks bewijst niets —
de opschoning kende eerst alleen de leerboek-stuurtekens en de suite bleef groen terwijl NBSP/
zero-width door de hele keten liepen. Nu: een categorie-toets over het hele Unicode-bereik, en een
gedeelde voorbeeldenreeks die voor- én achterkant draaien. **Vier skill-lessen** vastgelegd
(likara-tests/ux/resilience/backend).

**Reststand ADR-056 (gemeten):** snede 2 + 3 + vier subknopen open — eerste LI052-besluit is deze
geheel afronden vóór nieuw werk (NEXT_SESSION.md).

## Sessie LI050 (het vraagbeheer van de beheerder, en vragen mogen evolueren) — AFGEROND

**Eén draad door alle opdrachten:** de checklist-vragenset werd van een seed-gegeven een
beheerbaar tenant-instrument — wie erover gaat (beheerder-only), hoe hij is ingedeeld (categorie
als entiteit, sleep-volgorde), wat de consultant ervan merkt (uitgezette vraag telt niet mee),
en hoe hij mag evolueren (ADR-056). Elke bouwstap op gemeten grond (vijf read-only
checkpoints/metingen), elk besluit van Bert.

**Wat er is gebouwd:**
- **ADR-022 W2-W5** (`181fa75`/`4a452d8`/`ac3b92f`): vraagbeheer beheerder-only (lezen breed);
  `checklist_categorie` als eigen tenant-entiteit (composiet-FK RESTRICT, migratie 0074, weigering
  mét telling bij verwijderen); vraagcode van het scherm (systeem-toegekend, `volgende_code`);
  sleep-volgorde voor categorieën, vragen én antwoordopties via ÉÉN bouwsteen (`useSleepLijst`,
  migratie 0075) — getalvelden weg (besluit: slepen is de enige bediening).
- **Engine-regel** (`ca6b063`): "een uitgezette vraag bestaat voor de beoordeling niet" —
  gedeelde afleiding `services/actieve_vraag.py` (5 consumenten, bronscan); dichtte de
  checkpoint-gaten G2-1/G2-2 (migratieklaar-terwijl-checklist-leeg; onafsluitbare open punten).
- **Vraagbeheer-UX** (`6ab1960`): één regel per vraag (kop van een omrand `lk-inhoudskader`-blok,
  één tegelijk open), onderbouwing achter één klik, veldenrijen breken af, verwijderen in eigen
  zone, selectie met eigen kanaal (accent + linkermarkering; hover neutraal), hernoemen als
  handeling. **Optie-sleep-fix**: `<tr>`-rijen droegen HTML5-drag niet (audit-bewijs: 12
  categorie-updates, 0 optie-updates) → lijstvorm.
- **ADR-056 vraagevolutie** (`e304955`, beslist niet gebouwd): formulering bevroren bij het
  antwoord; beheerder kiest verduidelijking vs. wijziging (nooit afgeleid; ook opties/labels);
  verouderd = neutraal + wegwerkbaar per formulering; telt mee in Open punten (niet-blokkerend);
  invariant: nooit blok "dit moet nog", nooit de score legen; verworpen: vraagversies, audit als
  leeslaag; 16 besluiten incl. mockup-ronde (één opslaan-moment, geen voorselectie,
  antwoordtype-slot, optie-heractiveren).
- **Werkprotocol** (`9d6adfc`): bronplicht per bewering + afsluiten is Berts besluit.
- **Drie nieuwe wachters met bijt-bewijs**: tabel-element-verbod op drag-gedrag ·
  werkvlakgrens-scan (geen card-in-card + kader-klassen behouden hun rand) · precies-één-selectie.
- **Vier skill-lessen** (na read-only validatie): welke-laag-bewijst-deze-toets (tests) ·
  lees-de-definitie-niet-de-naam (frontend §werkvlak-rand) · selectie/aanwijzen/aanstip-kanalen
  (frontend §Signaal-kanalen) · audit-trail-als-meetinstrument (werkprotocol §Browsercheck).

**Werkwijze die zich bewees:** meten vóór bouwen (audit-trail als bewijs dat een browserhandeling
de opslag nooit bereikte); stapelen alleen op expliciet besluit mét vangnet-stash; restdata-
opruiming + herbereken vóór een suite-uitslag telt (2×); de code wint van het rapport (de
"card = omrand werkvlak"-claim uit het eigen gate-rapport gecorrigeerd door meting).

## Sessie LI049 (de skills weer één waarheid, met een wachter erbij) — AFGEROND

**Eén draad door alle opdrachten:** negen skills waren op sessievolgorde gegroeid in plaats van op
onderwerp, en verwijzingen ertussen waren onbewaakte beloften. LI049 bracht de twee drukst gelezen
skills op onderwerp en zette er een machinale wachter naast.

**Wat er is gebouwd:**
- **De kopverwijzingen-scan** (`backend/tests/test_kopverwijzingen_scan.py`) — bewaakt repo-breed
  (691 bestanden) dat elke `skill §kop`-verwijzing op een bestaand anker landt (koppen én
  vet-lead-ins); 5 gedocumenteerde beperkingen, zelftest die bijt. **Bewees zich 3× op nieuw werk**
  nog binnen de sessie.
- **Drie verhuizingen**: werkprotocol-sessiekoppen → onderwerpskoppen (5 koppen opgeheven, verbatim);
  P8-subreeks in likara-ux op leesvolgorde (byte-verbatim, multiset-geborgd); bronscan-eisen canoniek
  in `likara-tests §Bronscans` met de frontend-casussen als toepassing.
- **Tests-consolidatie in drie rondes**: 15 chronologische koppen → onderwerp (273=273 regels
  verbatim), dubbelingen naar één bron, allowlist-synctests samengevoegd (Berts besluit).
- **Parkeeritems geland**: gate-meting + OPVOLGPUNTEN-staging → werkprotocol; psql-recept →
  LOKAAL-TESTEN; rm/find-drievoud bewust gelaten (keuze i).
- **Vier eigen-besluit-gevallen** elk met read-only checkpoint vooraf: P8a-telling (git-archeologie:
  twee wáre tellingen), LI036-kaartregel (samengevoegd naar ux), mjs-driftkopie (→ bewaakte
  verwijzing), UX-first-binnenkopdubbeling (opgeruimd, drie momenten behouden).
- **Negen checkpoint-/metingsrapporten** + de gemeten kaart van het restwerk:
  `docs/Opschoonplan-zeven-skills.md` (7 skills, 82 chronologische koppen, 37% van de skill-tekst;
  recept, vijf blokken, hygiëneborging in drie verankeringen).

**Werkwijze die zich bewees:** verbatim = multiset-bewijs; de code wint van het rapport (drie eigen
rapportfouten expliciet gecorrigeerd); "waar zoekt de gebruiker de regel" besliste élke
dubbeling-keuze; herformuleren bleef overal Berts expliciete besluit.

## Sessie LI048 (het scherm zegt wat het doet) — AFGEROND

**Eén draad door alle opdrachten:** een scherm dat een antwoord geeft dat formeel klopt en de
consultant niets vertelt. Vier keer in verschillende gedaanten, telkens met een groene suite ernaast.

**Wat er is gebouwd:**
- **De lijstkop** — 4 → **14 hoofdmenu-schermen** op één gedeelde bouwsteen; het scan-bereik wordt
  afgeleid uit het menu, niet uit bestandsnamen. En passant een defect verholpen dat niemand had
  gemeld: vier schermen hadden **twee zoekvelden** met elk een eigen binding.
- **Het auditlog bruikbaar gemaakt** in vier stappen: zoeken vond niemand (het veld doorzocht
  persoonsnamen terwijl de kolom e-mailadressen toont — in de demo dus 7.242 onvindbare regels); de
  regel benoemde zichzelf niet (`Element — 9f1282d4…`, 14.398 keer); waarden stonden in opslagtaal;
  en het filter loog over zijn bereik én miste de koppelingen (0 van 9.291 relatieregels vindbaar).
- **De objecthistorie compleet** — sub-entiteiten horen in de geschiedenis van hun ouder.
- **Vorm:** tabvorm, lijntaal (drie gewichten), het amber-onderscheid in beide vensters, en twee
  wegwijzers als teken terwijl handelingen woorden blijven.

**Achttien patronen gevalideerd** (10 stonden er al, 6 half, 1 dubbeling, **0 nieuw**) en
weggeschreven — elk naast zijn concrete geval, zodat de consolidatie van LI049 ze als blok meeneemt.

**Twee dingen die deze sessie zichzelf aandeed en herstelde:** een kernzin die over twee regels was
afgebroken en daardoor onvindbaar met `grep` (drie keer voorgekomen, drie keer hersteld — dezelfde
faalmodus als de null-byte-besmetting van LI047), en een bijt-bewijs dat groen bleef omdat de keuze
inline in een lus stond en geen enkele toets hem oefende.

## Sessie LI047 (alles wat dit component nog nodig heeft, op één plek) — AFGEROND

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

## Prioriteiten volgende sessie (LI052 — zie NEXT_SESSION.md)

1. **EERSTE BESLUIT: ADR-056 geheel afronden vóór nieuw werk** — snede 2 (opties onder dezelfde
   regel/sein + optie-moment + heractiveren + antwoordtype-slot-frontend; schemastap), snede 3
   (verouderd-teller per vraag/categorie; schemaloos), en de vier resterende subknopen (twee
   consultant-drempels, gedeactiveerde-vraag-antwoordgedrag, contextpaneel aan volgorde 8).
2. **P50-2 Namenkaart zonder paginering** — meting klaar (checkpoint §2B); fix-vorm kiezen.
3. **P50-3 `organisatiegebruik.applicatie_id`** — Berts schemabesluit, laatste goedkope moment.
4. **Productie-hardening N50-2 / L51-3 (OP-14/OP-28)** — dev-secrets/testaccounts/code-defaults:
   niets houdt ze tegen; harde deploy-voorwaarde vóór livegang.
5. **Vervolgpunten LI051:** L51-1 index accentloos zoeken (meten vóór productie) · L51-2 Engelse
   veldmeldingen (eigen ronde).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
