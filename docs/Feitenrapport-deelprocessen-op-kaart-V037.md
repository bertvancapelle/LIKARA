# Feitenrapport — Deelprocessen eerste-klas op de kaart (V037)

**Checkpoint:** LI037_checkpoint_deelprocessen_op_kaart · **Datum:** 2026-07-10 ·
**Basis:** commit a99fe23 / build V037 (schone werktree). Read-only — niets gewijzigd behalve dit rapport.

Alle vindplaatsen zijn geverifieerd tegen de code. Waar een skill-aanname afweek van de code is dat
expliciet gemarkeerd (§B5, §C6). Regelnummers zijn de stand van V037.

---

## Blok A — Huidige proceslaan-projectie op de kaart (backend)

### A1. Opbouw van de proces-projectie

**Vindplaats:** `modules/bwb_ontvlechting/backend/services/landschapskaart_service.py`,
functie `haal_grafdata_op`, blok "── Ring — Processen (LI036 slice 2 · stap 1)" (r. 492–588,
het laatste blok vóór de `return`).

**Query's.** Eén query op `Procesvervulling` (component-gescoped), daarna batch-iteratief
`Proces`-info bijladen tot en met alle voorouders:

```python
pv_rijen = (await session.execute(
    select(Procesvervulling.component_id, Procesvervulling.proces_id,
           Procesvervulling.applicatiefunctie)
    .where(Procesvervulling.tenant_id == tid, _sc(Procesvervulling.component_id))
    .order_by(Procesvervulling.component_id, Procesvervulling.id))).all()
```
(r. 502–511). Proces-info-lus (r. 514–528): `te_laden = {r.proces_id …}`; per iteratie worden
alleen **nog-niet-geprobeerde** ids geladen (`geprobeerd |= te_laden`), waarna `ouder_id`'s die
nog onbekend zijn in de volgende ronde meegaan — "Termineert altijd: alleen nog-niet-geprobeerde
ids worden geladen (ook bij een cyclus of een wees-verwijzing)" (r. 513–514, comment).

**Bottom-up klim.** Gememoïseerde, cyclus-veilige klim `_wortel(pid)` (r. 535–554): visited-set
per klim, `wortel_cache` over klimmen heen; bij een (via directe SQL geconstrueerde) ouder-lus
geldt "het eerste her-bezochte proces als pseudo-wortel: deterministisch, geen hang" (r. 532–533).

**Per hoofdproces-met-edge één node; deelprocessen GEEN eigen node — letterlijk bevestigd.**
Nodes worden uitsluitend aangemaakt voor de **wortels** die in de bundel voorkomen:

```python
# Hoofdproces-nodes: alleen wortels die daadwerkelijk een edge dragen (geen dangling nodes);
for wid in sorted({k[1] for k in bundel}, key=str):
    nodes.append(LandschapsNode(
        id=wid, naam=…, element_type="proces", laag="business",
        archimate_element="business_process"))
```
(r. 573–580). `bundel` is gekeyed op `(component_id, wortel_id)` (r. 559–563) — een deelproces-id
komt dus **nooit** als node-id voor; het verschijnt alleen als `ProcesHerkomstItem` in
`herkomst[]` (r. 567–571). De live-test bevestigt dit expliciet:
`test_landschapskaart_proces.py:160` — "(a) Ná de vervullingen: ALLEEN het hoofdproces als node
(deel/subdeel niet), met typing."

**De samengetrokken edge** staat op het paar **component → hoofdproces(wortel)** (r. 581–587):

```python
edges.append(LandschapsEdge(
    bron_id=cid, doel_id=wid, relatietype="procesvervulling",
    label=(af_catalog.resolveer_een(enkel, af_labels) if enkel else None) or "vervult",
    ring="processen", aantal=b["aantal"], herkomst=b["herkomst"]))
```
- `relatietype="procesvervulling"`, `ring="processen"`;
- `aantal` = het aantal onderliggende vervul-regels in de bundel (flow-groeperingsprecedent);
- `label` = het applicatiefunctie-label als **alle** regels in de bundel dezelfde functie dragen,
  anders `"vervult"` (r. 582);
- `herkomst[]` = per onderliggende regel `proces_id` / `proces_naam` /
  `applicatiefunctie_label` — schema `ProcesHerkomstItem`
  (`schemas/landschapskaart.py:50–58`); het veld is nullable en bestaat **alleen** op
  procesvervulling-edges (`schemas/landschapskaart.py:71–74`; additiviteit geborgd in
  `test_landschapskaart_proces.py:24` `test_landschaps_edge_herkomst_veld_additief`).

### A2. Scope + engine-borging

**Scope uit de bestaande component-scope, geen `scope_ids`-verbreding.** Het filter op de
vervulling-query is `_sc(Procesvervulling.component_id)` — hetzelfde scope-mechanisme als de
overige ringen; hoofdproces-nodes komen als **verrijking** mee (zoals `plateau_map`/`lev_map`),
zonder de subgraaf-scope te verbreden. Letterlijk in het blok-comment (r. 497–500):

> "ZELFDE roll-up-bron/-semantiek als `procesvervulling_service.rollup_voor_proces`
> (procesvervulling + `ouder_id`-boom), alleen bottom-up bewandeld (de kaart vertrekt bij de
> componenten). Geen schema, geen scope_ids-verbreding (processen zijn verrijking, zoals
> plateau-info), engine onaangeroerd."

Plus de dangling-guard (P4): `if r.component_id not in comp_node: continue` (r. 560–561) —
alleen componenten die als knoop meekomen krijgen een vervult-edge.

**Engine onaangeroerd.** De module-docstring (r. 1–14) legt vast dat het bestand geen
engine-symbolen importeert en niets schrijft; de imports (r. 17–44) bevatten uitsluitend
`Proces`/`Procesvervulling` als proces-symbolen (lezen). Borging: de engine-import-afwezigheid +
read-only-bronscan zijn **module-breed** geborgd in `test_landschapskaart.py` en "dekken dit blok
automatisch mee" (`test_landschapskaart_proces.py:7–8`); de live-test asserteert bovendien dat
lifecycle `'concept'` blijft na de projectie (`test_landschapskaart_proces.py:193–196`).

---

## Blok B — Procesregister-model + roll-up-definitie

### B3. Modellen

**`Proces`** — `modules/bwb_ontvlechting/backend/models/models.py:634–671`:
- Element-subtype: composiet-FK `(tenant_id, id) → element(tenant_id, id)`
  `ON DELETE CASCADE` (`fk_proces_element`); `UNIQUE(tenant_id, id)` (`uq_proces_tenant_id`)
  als FK-target voor de self-FK.
- Self-FK `ouder_id`: composiet `(tenant_id, ouder_id) → proces(tenant_id, id)`,
  **`ON DELETE RESTRICT`** (`fk_proces_ouder`) — proces met deelprocessen niet verwijderbaar
  (service: 409 `HEEFT_DEELPROCESSEN`; RESTRICT is de DB-backstop).
- `CHECK ouder_id IS NULL OR ouder_id <> id` (`ck_proces_geen_self_parent`); transitieve
  cycluspreventie in de servicelaag (`proces_service._zou_kring_maken`, r. 88).
- Velden: `naam` (String 255, verplicht), `toelichting` (Text, optioneel), `ouder_id` (nullable).
  Geen niveau-label — "de plek in de boom ís het niveau" (docstring).
- RLS: `ENABLE` + `FORCE ROW LEVEL SECURITY` + grant aan `lk_app` in migratie
  `0057_adr042_proces.py:59–66`.
- ArchiMate-typing: `ELEMENT_ARCHIMATE_TYPING[ElementType.proces] =
  {"archimate_element": "business_process", "laag": "business", "aspect": "behavior"}`
  (`services/archimate_typing.py:68`; `business_process` expliciet toegevoegd aan de gesloten
  lijst, r. 37–38). Migratieketen: `0056_adr042_elemtype_proces.py` (enum-waarde) →
  `0057` (tabel) → `0058` (applicatiefunctie-catalogus) → `0059` (procesvervulling).

**`Procesvervulling`** — `models.py:673–714`:
- Het tripel: `component_id` + `proces_id` + `applicatiefunctie` (String 60, tekst-sleutel naar
  de `applicatiefunctie_optie`-catalogus, géén harde FK), plus optionele `toelichting`.
- Uniciteit: `UNIQUE(tenant_id, component_id, proces_id, applicatiefunctie)`
  (`uq_procesvervulling`) — dezelfde functie niet dubbel, wél meerdere functies per
  (component, proces) als losse regels.
- Beide FK's composiet naar `element` **ON DELETE CASCADE**; dat het écht een component resp.
  proces is dwingt de **service** af (`procesvervulling_service._element_type`, 422).
- **Component-breed bevestigd**: "élk componenttype is koppelbaar (ADR-042 besluit 3)"
  (docstring, r. 686–688); de seed bewijst het met een database-component (§E11).
- FORCE RLS + grants: migratie `0059_adr042_procesvervulling.py:54–61`.

### B4. Eén roll-up-definitie — bevestigd

**Rollup-leeslaag:** `procesvervulling_service.rollup_voor_proces` (r. 282–347). Semantiek:
subboom via `proces_service.subboom` (iteratieve BFS per niveau met visited-set, cyclus-veilig,
`niveau` + `pad`; r. 231–268) → één vervulling-query over **alle subboom-ids** + join op
`Component` (geen N+1). Eigen regels van de wortel zitten er bewust NIET in (docstring r. 283–290).
Per regel: herkomst (`proces_naam`, `proces_pad` = namen vanaf het directe deelproces) en
`tak_id` (het **directe** deelproces als stabiele groepeersleutel, lineair afgeleid uit de
BFS-volgorde, r. 300–306).

**Kaart-projectie:** zelfde bron (`Procesvervulling` + de `ouder_id`-boom van `Proces`), alleen
andersom bewandeld — de kaart klimt van vervulling omhoog naar de wortel (`_wortel`, §A1), de
rollup daalt van de wortel af naar de subboom (`subboom`). Het blok-comment in
`landschapskaart_service.py:497–499` legt die één-bron-relatie letterlijk vast (citaat in §A2).
Er bestaat **geen** opgeslagen roll-up-feit; beide zijn pure leespaden.

### B5. Bestaande read-endpoints/servicefuncties

Alle drie de gevraagde leespaden bestaan al:

| Richting | Service (signatuur) | Route | Projectie |
|---|---|---|---|
| component → processen | `procesvervulling_service.lijst_voor_component(session, tenant_id, component_id) -> list[dict]` (r. 240) | `GET /procesvervullingen?component_id=` (`routes/procesvervulling.py:46–60`) | per koppelregel: `vervulling_id`, functie(+label), `toelichting`, `proces_id`, `proces_naam`, **`proces_ouder_naam`** (directe ouder via `aliased(Proces)`-outerjoin — één niveau context, niet het hele pad) |
| proces → directe regels | `procesvervulling_service.lijst_voor_proces(session, tenant_id, proces_id) -> list[dict]` (r. 198) | `GET /procesvervullingen?proces_id=` (zelfde route; precies één van beide filters verplicht, anders 422 `FILTER_VEREIST`) | per regel: component-naam + type(+label) + functie(+label) |
| proces → subboom | `proces_service.subboom(session, tenant_id, proces_id) -> list[dict]` (r. 231) | `GET /processen/{id}/subboom` (`routes/proces.py:79`) | alle deelprocessen, alle niveaus: `id`, `naam`, `ouder_id`, `niveau`, `pad` — **zonder** vervullers |
| proces → subboom-vervullers | `procesvervulling_service.rollup_voor_proces(...)` (r. 282) | `GET /processen/{id}/rollup` (`routes/proces.py:89`) | doorgerolde regels mét herkomst/`tak_id` (§B4) |
| organisatie → processen | `procesvervulling_service.processen_voor_organisatie(...)` (r. 348) | consumer: `PartijProcessenSectie.vue` | afgeleide kijk via eigendom + organisatiegebruik |

**Nuance t.o.v. de vraagstelling:** er is géén *enkele* functie die "per proces de directe
deelprocessen + vervullers" in één respons combineert — dat beeld wordt frontend samengesteld
uit `processen.lijst({ouder_id})` (directe kinderen; `ProcesDetail.vue:57`) + `subboom`/`rollup`.

---

## Blok C — Bestaande "Bekijk op kaart" / kaart-handoff (frontend)

### C6. Kaart-handoff-mechanismen

Er bestaan **twee** inkomende mechanismen, gelezen in `LandschapskaartView.vue` `onMounted`
(r. 2544–2590), met vaste voorrang: **handoff > `?center=`-deeplink > bewaarde staat
(`lk-state`) > server-standaardkijk > kale default** (r. 2566–2586):

1. **`kaartHandoff`-composable** (`frontend/src/composables/kaartHandoff.js`) —
   module-niveau consume-once-payload `{ componentIds, grofOnlyIds?, naam? }` via
   `zetKaartHandoff()` / `neemKaartHandoff()`. Bewust géén route-query (id-lijst te lang voor
   een URL — zelfde reden als de subgraaf-POST). Enige huidige zetter:
   `GebruikteApplicatiesSectie.vue:72`. De kaart zet dan `actieveSet` + `grofOnlyIds` en sluit
   het beginscherm (r. 2568–2571). **De payload draagt géén `weergave`-veld** — de weergave
   blijft wat hij was/default.
2. **`?center=<component-id>`-deeplink** (ADR-033) — zet de component als enige set-lid,
   `egoStartId`, en **hard `weergave = 'praatplaat'`** + kern-4-ringstartstand
   (`_zetPraatplaatRingen()`), beginscherm dicht (r. 2572–2581). Gebruiker:
   `ComponentDetail.vue:157–159` (`bekijkOpKaart()` → `router.push({ name: 'landschapskaart',
   query: { center: component.value.id } })`, knop "Bekijk op kaart" achter `magKaartZien`,
   r. 405–410).

**Er is géén inkomend mechanisme dat de kaart in de Lagen-weergave opent**, en geen mechanisme
dat een *proces* als centrum/ingang accepteert (de set en `?center` zijn component-ids;
`SubgraafRequest.component_ids`, `schemas/landschapskaart.py:82–89`). De oude `?modus`-param is
vervallen en wordt genegeerd (comment r. 2563).

### C7. Procesdetailscherm

`modules/bwb_ontvlechting/frontend/views/ProcesDetail.vue` (178 r.) toont: kop (naam +
toelichting + VeldUitleg), **klikbare broodkruimel** naar boven (voorouders cyclus-veilig langs
`ouder_id` geladen, `_laadVoorouders`, r. 34–47), blok 1 `ProcesComponentenSectie` (registratie
op dít niveau) en blok 2 `OnderliggendeProcessenSectie` (deelproces-kopjes + doorgerolde regels
+ "+ Deelproces toevoegen"-dialog, ouder voorgevuld).

**Er is géén knop richting de kaart** (geen verwijzing naar `landschapskaart` in het bestand).
Logische plek — feitelijke observatie, geen ontwerpkeuze: het scherm heeft een kopblok
(r. 120–141) en volgt hetzelfde detail-patroon als `ComponentDetail`, waar "Bekijk op kaart" als
`Button` in de actiebalk onder de content staat (`ComponentDetail.vue:405–410`); ook de
afdeling-PartijDetail heeft al een "Toon op de landschapskaart"-precedent
(comment `KaartBeginscherm.vue:107`).

### C8. KaartBeginscherm-ingangen

`KaartBeginscherm.vue` (355 r., kop-comment r. 3–11) — het "4-ingangen-vertrekpunt":
1. **Zoeken op component** (hoofdroute; server-side `/componenten`, type + zoekterm + filters);
2. **Via context** — drie symmetrische ZoekSelect-secties (r. 94–140): **leverancier**
   (`aard='externe_partij'` → `api.partijen.componentenViaContract`), **contract**
   (`api.contracten.componenten`), **organisatie** (LI033: `api.organisatiegebruik.
   lijstVoorOrganisatie` → volledige applicatieset incl. grof-only-markering);
3. **Opgeslagen views** (gelijkwaardige instap);
4. **"Toon het hele landschap"** (bescheiden ontsnapping onderaan).

**Een "Via proces"-ingang bestaat niet** — die zou nieuw zijn. Het woord "proces" komt in het
bestand niet voor.

---

## Blok D — Component ↔ proces in de schermen (frontend)

### D9. Detailschermen

**ComponentDetail** (`ComponentDetail.vue`) volgt het vier-vragen-Overzicht; vraag 3
"Waarvoor gebruiken we het" is de **registrerende** `ComponentProcessenSectie` (gemount op
r. 398–403, comment "de procesinzet, direct registreerbaar").

**`ComponentProcessenSectie.vue`** (kop-comment r. 1–15): regels als leesbare zinnen
("*registreren* in Aanvraag behandelen — Vergunningverlening", proces klikbaar,
`proces_ouder_naam` als identiteitscontext); regel-acties conform LI035 (Bewerken = dialog op
kenmerk-velden, ankers read-only; Verwijderen = gedeelde `BevestigVerwijderDialog`); toevoegregel
= proces-ZoekSelect over de hele boom (`procesZoek.js`) + functie-select + toelichting; 409 →
MeldingBanner; lege staat verwijst naar de Processen-pagina (bewust géén ter-plekke-proces-
aanmaak). Data via `api` op `GET /procesvervullingen?component_id=` (§B5).

**`ProcesComponentenSectie.vue`** (364 r.): de spiegel op de proces-pagina — zelfde koppelregel,
registrerend op dít procesniveau ("Componenten in dit proces"). Daarnaast
**`OnderliggendeProcessenSectie.vue`** (196 r.): read-only doorgerolde regels per deelproces-kopje
(rollup, `tak_id`-groepering) en **`PartijProcessenSectie.vue`**: de afgeleide organisatie-kijk
(read-only, §B5).

### D10. Kaart-rendering van proces-knoop en proceslaan (alles in `LandschapskaartView.vue`)

- **Vorm**: `_vormVoorType` → `element_type === 'proces'` ⇒ `'round-rectangle'` (r. 1755);
  onderscheid met de component-rechthoek is de **verloop-pijl-marker**: SVG-data-URI
  (`_pijlDataUri`, r. 1748; `_PROCES_PIJL` r. 1750) als node-achtergrond via de CY_STYLE-selector
  `node[element_type = "proces"]` (geborgd in `LandschapskaartView.test.js:996`); legenda-glyph
  "Proces" (r. 1786).
- **Ring `'processen'`**: eerste in `RINGEN` (r. 51); **default aan in alle weergaven** — niet in
  `RING_DEFAULT_UIT` (dat bevat alleen `organisatiestructuur`, r. 54) én opgenomen in
  `RING_PRAATPLAAT_KERN` (r. 64, comment r. 62–63: "de ring is besloten standaard-aan in álle
  weergaven"). Label "Processen" (`RING_LABELS`, r. 67).
- **Baan-indeling**: `_laneVan` → `element_type === 'proces'` ⇒ `'processen'`, vóór de rest-tak
  (r. 1940–1948). `LANE_DEF.processen = { label: 'Processen', bg: '#fff7ed' }` (r. 81–82,
  comment: "de 'waarvoor'-laag, bovenaan"); `DEFAULT_LANE_VOLGORDE = ['processen', 'rollen',
  'gebruikers', 'componenten', 'infrastructuur', 'contracten', 'overig']` (r. 90) — de proceslaan
  staat **bovenaan** en blijft daar ook na herschikken/legacy-herstel
  (tests r. 607–610, 655–660).
- **Vervult-edges**: edge-label op de kaart = `label` + `aantal`-badge bij ≥2
  (`[e.label || 'vervult', e.aantal >= 2 ? `${e.aantal}×` : null]`, r. 2032–2035). Edge-klik →
  popup "Vervult" met Component/Hoofdproces/Koppelingen + de herkomst-uitsplitsing
  (r. 1629–1637).
- **Herkomst-popup**: `_herkomstVelden` groepeert `edge.herkomst` per deelproces-naam →
  "deelproces · functies" (r. 1350–1359). Op de **proces-node-popup** de "Vervuld door"-sectie:
  scanbare componentnamen, herkomst per component **inklapbaar** via native `<details>`
  (standaard dicht — detail op aanvraag; `popupVervuldDoor` r. 1369–1383, template
  r. 3188–3196).
- **Vervul-toggle** (set-actie op de proces-popup): `_vervulToegevoegd` (Map proces-id →
  door-de-knop-toegevoegde component-ids, r. 1388) + `popupVervulActie` als reactieve toggle
  (r. 1390–1409): "+ Voeg vervullende componenten toe (N)" / "− Verwijder vervullende
  componenten" — verwijderen maakt **alleen de eigen toevoeging** ongedaan (vóór-bestaand werk
  blijft; r. 1425–1434); toevoegen licht het vervul-web op via het bestaande selectie-pad;
  set-acties wijzigen nooit de weergave. Reset bij "Begin opnieuw" (r. 857).
- **Instance-projectie**: processen zijn **tagloos** en krijgen géén rol-instance-expansie
  (geborgd in `LandschapskaartView.test.js:958–959`).

---

## Blok E — Testdata (canoniek scenario)

### E11. Wat de seed aanmaakt

`backend/dev_seed_testdata.py`, sectie 15 (r. 1592–1645), binnen `_seed_bvowb_scenario`
(idempotent: skip-op-naam voor proces, skip-op-tripel voor vervulling):

**Processen — twee boompjes, nesting-diepte exact 2 niveaus (hoofdproces → deelproces):**
- `Vergunningverlening` (wortel) → `Aanvraag behandelen` (deelproces)
- `Burgerzaken` (wortel) → `Verhuizing verwerken` (deelproces)

Er is **géén derde niveau** (geen processtap onder een werkproces).

**Procesvervullingen — 7 regels** (r. 1623–1633):

| Component | Proces (niveau) | Functie |
|---|---|---|
| Zaaksysteem | Aanvraag behandelen (deel) | registreren |
| Zaaksysteem | Aanvraag behandelen (deel) | raadplegen *(tweede functie, zelfde paar)* |
| DMS | Aanvraag behandelen (deel) | archiveren |
| Vergunningensysteem | Vergunningverlening (**hoofd**) | ondersteunen |
| Burgerzaken-suite | Verhuizing verwerken (deel) | registreren |
| BRP | Verhuizing verwerken (deel) | gegevens_leveren |
| Shared DB-server *(componenttype database — component-breed-bewijs)* | Vergunningverlening (**hoofd**) | ondersteunen |

**Voorbeeldketen component → deelproces → hoofdproces:**
Zaaksysteem → *Aanvraag behandelen* → *Vergunningverlening* (op de huidige kaart samengetrokken
tot één edge Zaaksysteem → Vergunningverlening met `aantal=2` en herkomst
"Aanvraag behandelen · Registreren, Raadplegen").

### E12. Feitelijke toereikendheid (alleen constatering)

- **Component → deelproces**: aanwezig — 5 van de 7 regels koppelen op deelproces-niveau, naast
  2 regels direct op een hoofdproces (het onderscheid deel- vs. hoofdproces-koppeling is dus
  zichtbaar te maken).
- **Zichtbare proceshiërarchie ≥2 niveaus**: aanwezig, maar **precies** 2 niveaus in beide bomen.
  Wil de eindstaat "uitvouwbaar, detail-op-aanvraag over meerdere lagen" ook een dieper geval
  (3 niveaus, bv. een processtap) demonstreren, dan ontbreekt die nesting in de huidige seed.
  De backend-live-test bouwt zelf wél een 3-laags fixture ("koppeling op een diep deelproces",
  `test_landschapskaart_proces.py:105–106`), dus de techniek is getest — alleen de canonieke
  seed toont het niet.
- Verder ontbreekt niets essentieels: meerdere functies per paar, component-breed (database) en
  meerdere componenten per boom zijn alle geseed. *(Niets aangepast.)*

---

## Blok F — Raakvlakken & risico's (feitelijk, geen ontwerp)

### F13. Geraakte gedragingen/tests (feit + aandachtspunt, geen oplossing)

1. **Backend-samentrekking + tests.** De projectie bundelt per (component, **wortel**) en de
   tests asserteren dat expliciet: "ALLEEN het hoofdproces als node"
   (`test_landschapskaart_proces.py:105–168`), "geen proces-nodes zonder vervulling" (docstring
   r. 6), herkomst-additiviteit (r. 24). Deelprocessen eerste-klas verandert precies deze
   asserties en de bundel-sleutel. Aandachtspunt: ook de proceshiërarchie-edge
   (deelproces → hoofdproces) bestaat vandaag nérgens als `LandschapsEdge`.
2. **"Ring uit wint van gaps".** `_BAAN_RING` mapt `processen → 'processen'` (r. 2053) en
   `getekendeNodes`/`gapZichtbaar` (r. 2098–2100) werkt op relatie-bezit per node. Een
   deelproces-node met alléén een hiërarchie-edge naar zijn hoofdproces valt onder dezelfde
   regel; de frontend-test r. 964–977 (ring uit → proces-knoop weg) beweegt mee. Aandachtspunt:
   onder welke ring de hiërarchie-lijnen vallen raakt deze regel direct.
3. **Instance-projectie / rolbanen.** Processen zijn tagloos en 1-op-1 (geen expansie; test
   r. 958–959); alle proces-knopen landen in één baan `'processen'` (r. 1942). Meerdere
   niveaus binnen één baan is een nieuw geval voor `_swimlanePositions` (nu een plat grid per
   baan, `MAX_LANE_W`/`NODE_W`/`NODE_H`, r. 91–95).
4. **Layout/meet-stap preset-tak.** Nieuwe node-soorten/aantallen in de Lagen-weergave lopen
   door de verplichte meet-stap (`cy.nodes().updateStyle()` + `layoutDimensions`, r. 2362–2373)
   — bestaand mechanisme, maar de "geen twee nodes op dezelfde positie"-testnorm
   (`kaartLayout.test.js:78–90`, met een proces-node in de fixture) moet blijven gelden bij
   deelproces-knopen.
5. **Detail-op-aanvraag-gelaagdheid.** De huidige gelaagdheid (badge → inklap-`<details>` →
   popup) hangt aan de samengetrokken edge + `herkomst[]` (r. 1350–1383, 3188–3196). Worden
   deelprocessen eigen knopen, dan verschuift wat "herkomst" betekent (de popup-uitsplitsing
   bestaat dán mogelijk al als zichtbare structuur).
6. **Set-acties wijzigen nooit de weergave / vervul-toggle.** `popupVervulActie` +
   `_vervulToegevoegd` werken per **hoofdproces-id** op `_vervulEdgesVan(procesId)`
   (doel-match, r. 1361). Eerste-klas deelprocessen introduceren meerdere proces-ids per boom
   waarop deze administratie kan aangrijpen.
7. **Set-/ingang-model is component-gebaseerd.** `SubgraafRequest.component_ids`
   (schema r. 82–89), `actieveSet`, `?center=` en de handoff-payload zijn allemaal
   component-ids; `appNodes`/`_isApp` (r. 379, 418) maken alleen applicaties + organisaties
   zoekbaar. "Plotbaar vanuit een (deel)proces" heeft vandaag geen ingang — noch in
   `KaartBeginscherm` (§C8), noch als deeplink (§C6), noch server-side (de proces-projectie
   vertrekt uitsluitend uit de component-scope, §A2).
8. **Frontend-kaarttests LI036.** Het `describe`-blok "LI036 slice 2 — proceslaan + ring
   Processen" (`LandschapskaartView.test.js:932–996`) fixeert het huidige één-node-per-
   hoofdproces-beeld (fixture r. 938–942: één proces-node + één gebundelde edge met herkomst).
9. **Eén-roll-up-bron-invariant.** `rollup_voor_proces`/`subboom` en de kaartprojectie delen nu
   aantoonbaar één semantiek (§B4). Elke nieuwe kaart-uitbreiding raakt de plicht die ene bron
   te blijven bewandelen (comment r. 497–499; skill likara-domeinmodel LI036-sectie zegt
   hetzelfde — geen afwijking gevonden).

### F14. Open ontwerpvragen voor Bert (gemarkeerd, niet beantwoord)

1. **Standaard-diepte**: tot welk niveau tonen we deelprocessen standaard op de kaart —
   alles, alleen niveau 1 onder het hoofdproces, of hoofdprocessen-met-uitvouw (detail-op-
   aanvraag per knoop)?
2. **Uitvouw-mechaniek**: is "uitvouwen" een set-/graafmutatie (deelproces-knopen bijladen)
   of een pure weergave-toestand — en hoe verhoudt dat zich tot "set-acties wijzigen nooit
   de weergave"?
3. **Klik-gedrag**: wat doet een klik (en dubbelklik) op een deelproces-knoop met de kaart-set
   — inspecteren, uitvouwen, hercentreren, niets?
4. **Baan/laag-plaatsing**: krijgen deelprocessen een plek **binnen** de bestaande proceslaan
   (genest/ingesprongen), en zo ja hoe toont de laan hiërarchie in een plat banen-grid; of iets
   anders?
5. **Edge-semantiek**: blijft de samengetrokken component→hoofdproces-edge bestaan náást
   fijnmazige component→deelproces-edges (dubbele lijnen zoals eigenaar+gebruikt), of vervangt
   fijnmazig de bundel (en wat betekent `aantal`/`herkomst` dan nog)?
6. **Hiërarchie-lijnen en de ring**: vallen deelproces→hoofdproces-lijnen onder de ring
   `'processen'` (alles togglet samen) of onder een eigen ring/toggle?
7. **Ingang "via proces"**: komt er een "Via proces"-ingang op het KaartBeginscherm, een
   "Bekijk op kaart" op ProcesDetail, of beide — en opent die in Lagen, Overzicht of Praatplaat
   (er is nu géén mechanisme dat de kaart in Lagen opent, §C6)?
8. **Set-semantiek bij proces-ingang**: een proces kan geen set-lid zijn (component-ids); wordt
   "plot vanuit proces" dan "zet de vervullende componenten in de set" (zoals de
   leverancier-/contract-ingang), of iets nieuws?
9. **Vervul-toggle op deelproces-niveau**: geldt "+ Voeg vervullende componenten toe" straks per
   (deel)proces-knoop (subboom-scope per knoop?) of alleen op het hoofdproces?
10. **Popup/detail-op-aanvraag**: wat blijft er van de herkomst-`<details>`-uitsplitsing als
    deelprocessen zichtbaar zijn — en verschuift de uitsplitsing naar de deelproces-popup?
11. **Testdata**: is een derde nestingsniveau (processtap) in de canonieke seed gewenst om de
    uitvouw-mechaniek demonstreerbaar te maken (§E12)?

---

*Einde feitenrapport. Read-only checkpoint; geen code, tests, migraties of seeds gewijzigd.*
