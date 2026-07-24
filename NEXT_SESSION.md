# NEXT_SESSION.md — LIKARA V051

**Gegenereerd**: 2026-07-23
**Vorige build**: V050 → **V051**
**Branch**: master
**Laatste commits (LI050)**: `9d6adfc` werkprotocol bronplicht+afsluitregel · `2dc5592` checkpoint
productie-gereedheid · `181fa75` vraagbeheer beheerder-only (ADR-022 W2) · `4a452d8` categorie als
entiteit + indeling + code systeem-toegekend (W3/W4, migratie 0074) · `ca6b063` engine: uitgezette
vraag telt niet mee (actieve_vraag) · `ac3b92f` vraag-volgorde + sleep-bouwsteen (W5, migratie
0075) · `e304955` ADR-056 vraagevolutie + checkpoint-grond · `6ab1960` vraagbeheer-UX
(leesbaar/bedienbaar + optie-sleep-fix + wachters) · `e6c4cec` rechtenanalyse-rapport

> **Sessie LI050 — het vraagbeheer is van de beheerder, leesbaar, en bedienbaar met slepen; en
> ADR-056 legt vast hoe vragen mogen evolueren.**
>
> Wat er ná LI050 anders is:
> - **Vraagbeheer is beheerder-only** (lezen blijft breed) en de **categorie is een eigen
>   tenant-entiteit** met composiet-FK; de **vraagcode is van het scherm** (systeem-toegekend);
>   vragen en categorieën hebben een **sleep-volgorde** (migraties 0074+0075).
> - **De engine negeert uitgezette vragen** ("een uitgezette vraag bestaat voor de beoordeling
>   niet") via één gedeelde afleiding `services/actieve_vraag.py` — dit dichtte de
>   checkpoint-gaten G2-1/G2-2 (scores op gedeactiveerde vragen telden mee; dode routes in
>   "Dit valt op").
> - **Het beheerscherm is leesbaar**: één regel per vraag (kop van een omrand blok,
>   `lk-inhoudskader`), onderbouwing achter één klik, één vraag tegelijk open, selectie met een
>   eigen kanaal; **optie-slepen gerepareerd** (tabelrijen droegen HTML5-drag niet — audit-bewijs).
> - **Drie nieuwe wachters met bijt-bewijs**: sleep-bronscan + tabel-element-verbod ·
>   werkvlakgrens-scan (geen card-in-card) · precies-één-selectie.
> - **ADR-056 (vraagevolutie) is beslist, niet gebouwd** — 16 besluiten incl. mockup-ronde.

---

## Top-5 prioriteiten LI051

1. **EERSTE BESLUIT LI052 — ADR-056 wordt geheel afgerond vóór er nieuw werk bij komt.**
   Snede 1 (formulering bevroren, sein, opnieuw antwoorden, geschiedenis, tabbladgetal,
   stille notitie, nulpunt) is **gebouwd** in LI051. Af te maken, in deze volgorde:
   **snede 2** (opties onder dezelfde regel/sein + optie-moment + heractiveren +
   antwoordtype-slot-frontend; schemastap), **snede 3** (verouderd-teller per vraag/
   categorie; schemaloos), én de **vier resterende subknopen** (de twee consultant-drempels,
   het gedeactiveerde-vraag-antwoordgedrag, en het contextpaneel aan categorie-volgorde acht).
   Zie de gemeten reststand hieronder. Pas daarná nieuw werk (P50-2/3, hardening, …).
2. **P50-2 Namenkaart zonder paginering** — gemeten (checkpoint §2B: 1 echte treffer + 2
   verwante); nu de fix-vorm kiezen (niet de limiet ophogen).
3. **P50-3 `organisatiegebruik.applicatie_id`** — Berts schemabesluit op het laatste goedkope
   moment (gate); checkpoint §2C somt de 7 verwante "applicatie"-namen op.
4. **Productie-hardening (OP-14/OP-28, scherpste punt van het checkpoint):** 31
   `changeme_dev`-vindplaatsen + 9 testaccounts + drie code-defaults die in productie stil
   doorvallen — **niets houdt dit tegen** (`validate_startup_config` checkt alleen aanwezigheid).
   Let op: de voorwaarden-zin bij OP-28 is gecorrigeerd (ADR-006 en gebruikersbeheer zijn al
   gebouwd).
5. **Consultant-drempels + P50-4-besluit.** De twee drempels (Bevinding/Verantwoordelijke/Actie
   achter "eerst scoren" + uitklap; Antwoord-veld ontbreekt bij 71/98 vragen zonder antwoordtype)
   — benoemd vervolgpunt uit de meting; en het functionele besluit welke keuzelijsten beheerbaar
   horen (meting klaar, checkpoint §2D: 31 lijsten, protocol drievoudig code-vast).

---

## ADR-056 — reststand (gemeten V051, read-only tegen de code)

De 18 besluiten, geteld tegen de code (niet uit het hoofd):

**Gebouwd in LI051 (snede 1) — 13 van de 18:**
1 vraagtekst wijzigt mét antwoorden (`checklistconfig_service.werk_vraag_bij:327`) · 2 verduidelijking/
echte-wijziging, verplicht, geen default (`WijzigingsAard`-enum + venster `ChecklistConfigBeheer.vue:1001`) ·
4 formulering bevroren bij het antwoord (`checklistscore.vraag_bevroren`; sein = vergelijking
`_zet_vraag_gewijzigd:77`, geen kolom) · 6 stille notitie + doving (`vraag_verduidelijkt_op`,
`checklistscore_service:451`) · 7 één neutraal sein per vraag (`ChecklistscoreSectie.vue:485`) · 8 opnieuw
antwoorden dooft het sein, toelichting blijft (`werk_bij:452`) · 9+17 oude formulering in de
vraag-geschiedenis, leesbaar voor de consultant (`objecthistorie.py:53` + `ObjectHistoriePaneel`) · 10
tabbladgetal telt beide, geen poort (`tabblad_aantal:252`, `OpenPuntenSectie` blok "dit valt op") · 11
blokkeert niets (lifecycle/score onaangeraakt, geborgd) · 16 geen voorselectie (radios leeg) · 18 nulpunt:
backfill bij invoering (migratie 0076). *(laatste_wijzigingsaard: 98× NULL = nulpunt bevestigd.)*

**Nog te bouwen — het hart:**
- **Snede 2 — middelgroot + schemastap.** Besluit 3: optie toevoegen/hernoemen door dezelfde keuze/sein
  (`voeg_optie_toe:586`/`wijzig_optie:621` kennen die niet) · besluit 5: een optie krijgt een moment van
  ontstaan (géén `created_at` op `ChecklistVraagOptie`, `models.py:1055` — dít is de schemastap) · besluit
  15: uitgezette optie **heractiveren** (`OptieUpdate` kent alleen label+volgorde; wel `deactiveer_optie`,
  géén reactiveer-service/route) · besluit 14: antwoordtype-veld **dicht mét reden** — de serverregel bestaat
  al (`zet_antwoordtype:541`), alleen de frontend-presentatie ontbreekt (nu nog de grijze regel
  `ChecklistConfigBeheer.vue:854`) · besluit 13 afronden: opties **bundelen** in het ene opslaan-moment
  (lopen nu via aparte endpoints). De machinerie van snede 1 (keuze → fan-out over `vraag_bevroren`) draagt
  dit; nieuw is dat het optie-pad erdoorheen gaat + de optie-drager (besluit 5) + heractiveren (besluit 15).
- **Snede 3 — klein, schemaloos.** Besluit 12: teller "N verouderde antwoorden" per vraag én per categorie
  in het beheerscherm, uit **dezelfde** afleiding als de voorspelling vooraf. De per-component verouderd-
  telling bestaat al (`component_open_punten_service._vraag_gewijzigd:124`); wat ontbreekt is de per-vraag/
  per-categorie som op de beheerplek. Geen schemastap.

**Nog te bouwen — buiten het hart: de vier resterende subknopen (allemaal in LI052, ná 2+3):**
1. **De twee consultant-drempels — het mechanisme bestaat al; open is een BESLUIT, geen bouw.**
   Bevinding/Verantwoordelijke/Actie zitten achter "eerst scoren" + uitklap (`ChecklistscoreSectie.vue:530-552`),
   en **71 van de 98** actieve vragen hebben antwoordtype `geen` → geen keuzelijst (gemeten: 71 geen · 18
   enkelvoudig · 8 meerkeuze · 1 getal). Vraag: is de eerst-scoren-drempel gewenst, en horen die 71 vragen
   een antwoordveld?
2. **Het gedeactiveerde-vraag-antwoordgedrag.** De engine negeert een uitgezette vraag voor de beoordeling
   (LI050, `actieve_vraag.py`), maar hoe bestaande antwoorden op zo'n vraag zich gedragen — leesbaar blijven,
   uit de scorelijst verdwijnen — is nog een open subknoop.
3. **Het contextpaneel aan categorie-volgorde acht** (`ComponentDetail.vue:754`, `ContractSectie.vue:236`) —
   zie ook onder Openstaande beslissingen; urgenter sinds de beheerder de volgorde kan verslepen.

*"Vijf teksten worden onwaar":* #5 (tabblad-toelichting) is met besluit 10 geland; #4 (grijze regel) en #2
(optie-docstring soft-deactiveren) lopen mee met snede 2 (besluit 14/15); #1 (VraagUpdate-docstring) en #3
(ADR-022-passage) zijn docs-opruiming.

**Sluiten 2+3 het ADR? (stap 2):** Ja — snede 2 (besluiten 3, 5, 13-afronding, 14-frontend, 15) + snede 3
(besluit 12) bouwen de laatste van de **18 besluiten**. De vier subknopen hierboven vallen bewust buiten die
18, maar horen (besluit Bert) in dezelfde LI052-afronding vóór er nieuw werk bij komt.

---

## Openstaande beslissingen

- **ADR-056 subknopen** (bij de bouw): invoerings-vulling, opslag-vorm in detail, plek stille
  notitie, meerkeuze-zonder-envelope.
- **P50-3**: kolom-hernoeming — eigen gate, eigen besluit.
- **P50-4**: welke keuzelijsten hóren beheerbaar (meting klaar; functionele keuze).
- **G2-3 tenant-registry**: provisioning-afspraak vóór de eerste echte tenant (registry is leeg
  terwijl er tenant-data bestaat — platform-brede backfills raken 0 tenants).
- **L7 css-poort**: de css-build-controle draait pas bij de afsluiting — deze sessie mét bewijs
  (kopstijl-afwijking landde in `6ab1960`, pas bij de TST gevangen). Proceskeuze Bert.
- **Contextpaneel hangt hard aan categorie-volgorde 8** (`ComponentDetail.vue:754-788`
  `v-if="actieveCategorieVolgorde === 8"`; ook `ContractSectie.vue:236`). **Urgenter sinds LI051:**
  de beheerder kan de categorie-volgorde nu verslepen (ADR-022 W5) — versleept hij, dan verschijnt
  "Geregistreerde contracten" bij de verkeerde categorie of verdwijnt het. Betekenis-markering op de
  categorie (niet het volgnummer) is de echte vorm. Niet-ADR-056, wél op de reststand-lijst.
- **Import-lijn Tiel** (persoonsnamen) — geparkeerd. **Opschoonplan 7 skills** — uitgesteld
  (route in `docs/Opschoonplan-zeven-skills.md`). **Demostand uittredende deelnemer** — kan
  onafhankelijk ingepland.

---

## Bekende risico's en aandachtspunten

- **Suites groen (TST-V051, 0 kritieken):** backend **1236 passed / 2 skipped** (incl.
  kopverwijzingen-scan) · frontend **1404 passed / 104 files** · vite build OK · css-build
  14 scans OK · alembic **1 head** (`0075`), 0 branches, 38× RLS.
- **Migraties deze sessie: 2** (0074 checklist_categorie · 0075 vraag-volgorde) — beide
  toegepast én reseed-consistent bewezen (0 verspringingen).
- **Auditlog toont `categorie_id` als kale id** in wijzigingsregels (sinds W3) — leesbaarheid.
- **Restdata-les:** een actieve testvraag van een browsercheck maakt lifecycle-tests rood;
  opruimen + herbereken vóór de suite-uitslag telt (2× gebeurd deze sessie).
- De **dev-server-herstart met cache-leging**: `rm` staat in de deny-lijst — `npm run dev --
  --force` is de werkende weg (of `find … -delete`, zie werkprotocol).

---

## Geleerde patronen deze sessie (verankerd in de skills)

- **Welke laag bewijst deze toets** (likara-tests): handler-tests bewijzen de JS-keten, niet de
  browser-mechaniek — 1394 groen terwijl het optie-slepen nergens werkte; borg op de renderlaag
  (tabel-element-verbod) en benoem de browsercheck expliciet als sluitpunt.
- **Lees de definitie, niet de naam** (likara-frontend §werkvlak-rand): `card` draagt geen rand —
  wachter `werkvlakGrens.scan.test.js` (geen card-in-card).
- **Selectie · aanwijzen · aanstip zijn drie kanalen** (likara-frontend §Signaal-kanalen): twee
  bijna gelijke tinten op één kanaal maken selectie onleesbaar.
- **De audit-trail is het meetinstrument** voor "bereikte de browserhandeling de opslag"
  (likara-werkprotocol §Browsercheck): 12 categorie-updates, 0 optie-updates = bewijs in één blik.
