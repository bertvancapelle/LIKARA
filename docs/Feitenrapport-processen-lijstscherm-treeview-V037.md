# Feitenrapport — Processen-lijstscherm naar tree-view (V037/LI037)

**Checkpoint:** LI037_checkpoint_processen_lijstscherm_treeview · **Datum:** 2026-07-11 ·
**Basis:** commit ef2421f (schone werktree). Read-only — niets gewijzigd behalve dit rapport.

**Kern in één zin:** het scherm is al een uitklapbare boom (inspring + ▸/▾, client-side uit een
platte `ouder_id`-lijst), met zoeken-dat-openklapt, doorklik, en beperkt beheer (top-level aanmaken
+ hernoemen); de tree-view-omzetting is dus een presentatie-slag (verbindingslijnen) — het
scharnierpunt voor de scope is dat de **API** verhangen én verwijderen al kan, maar **geen enkel
scherm** die aanbiedt.

---

## Blok A — Wat kan de gebruiker nu op dit scherm?

**Scherm:** `modules/bwb_ontvlechting/frontend/views/ProcesLijst.vue` (272 r., ADR-042 slice 4a) ·
route `/processen`, name `proces-lijst`, lazy child onder AppLayout (`frontend/src/router/index.js:34,136`) ·
nav-link "Processen" in `AppLayout.vue:123`.

### A1. Feitelijke mogelijkheden

- **Lezen/overzien** — de hiërarchie is een client-side boom, gerenderd als **platte `<ul>`-rijen
  met inspring + driehoekjes**: per rij een expand-toggle (`▸`/`▾`, alleen bij kinderen, met
  `aria-expanded` + sprekend `aria-label`; r. 216–224), de procesnaam als link, en de
  **toelichting** getrunceerd ernaast (r. 231). Inspring = `paddingLeft: … + diepte * 1.5rem`
  (r. 213). Velden per rij: **naam + toelichting** — geen soort/type-veld (bestaat niet op het
  model: de plek in de boom ís het niveau, ADR-042). De zichtbare rijen komen uit een
  diepte-eerst-loop over een `kinderenVan`-map (`ouder_id` → kinderen, per tak **gesorteerd op
  naam**, `localeCompare('nl')`; r. 71–80, 112–126).
- **Zoeken** — één zoekveld (r. 193–201), **client-side**, uitsluitend op **naam** (`_matcht`,
  r. 82: partieel + hoofdletter-ongevoelig, conform de zoekveld-norm; **toelichting doet niet
  mee**). Het zoeken is **boom-behoudend**: getoond worden treffers + hun voorouder-paden, en die
  paden worden **automatisch opengeklapt** (`matchOfNazaatMatcht`, r. 84–100; `isOpen` gebruikt
  bij een actieve term die set i.p.v. `openTakken`, r. 102–105). Niet-relevante takken verdwijnen
  (r. 117–118). Lege uitkomst → eigen melding (`lijst-geen-match`, r. 242).
- **Doorklikken** — de naam is een `router-link` naar `proces-detail` (r. 226–230); vandaar het
  volledige procesdetail (broodkruimel, componenten-sectie, onderliggende processen, "Bekijk op
  kaart" sinds fase 3).
- **Beheer op dít scherm** (het scharnierpunt — precies):
  - **"Nieuw proces"** (kop-knop, r. 184): maakt een **top-level** proces (dialog naam +
    toelichting; `api.processen.maak` zonder ouder, r. 155–157). Gated op
    `hasRole('medewerker','beheerder')` (r. 25).
  - **"Hernoemen"** per rij (r. 232–239): dialog voorgevuld, `api.processen.werkBij` met **alleen
    naam + toelichting** (r. 156).
  - **Deelproces toevoegen: NIET hier** — bewust op de proces-detailpagina (context voorgevuld;
    kop-comment r. 9–10 + lege-staat-tekst r. 247 verwijzen ernaar).
  - **Verwijderen: NERGENS in de UI.** De api-client heeft `processen.verwijder`
    (`frontend/src/api.js:397`) en de backend-route bestaat (DELETE met 409
    `HEEFT_DEELPROCESSEN`-pre-check), maar **geen enkel scherm roept 'm aan** (grep
    `processen.verwijder` over views/src: 0 hits buiten de client).
  - **Verhangen/herordenen: NERGENS in de UI**, maar de **API kan het al**:
    `ProcesUpdate.ouder_id` = "verplaatsen (incl. expliciet `null` = loskoppelen tot top-level)"
    (`schemas/proces.py:43–50`), met service-side kring-preventie (`_zou_kring_maken`). Geen
    scherm stuurt `ouder_id` mee. Handmatige volgorde-herordening binnen een tak bestaat niet
    (sortering is vast op naam).

### A2. Expand/collapse-staat

`openTakken` (array van proces-ids, r. 32) met expliciete toggle per rij. **Onthouden** via het
lijststaat-patroon (`useLijstStaat('proces-lijst', { zoekterm, openTakken }, …)`, r. 36–45):
zoekterm + open takken overleven detailbezoek-en-terug én F5 (route-leave + beforeunload); bij
herladen worden **onbekende ids gepruned** (r. 62–63). Tijdens zoeken wordt de open-staat
**niet vernietigd** — de zoek-open-stand is een afgeleide laag óver `openTakken` (r. 102–105);
zoekterm wissen = terug naar de handmatige stand. Default zonder bewaarde staat: **alles dicht**
(alleen hoofdprocessen zichtbaar).

## Blok B — Databron & vorm

### B3. Leespad

`api.processen.lijst` (`GET /processen`, keyset-gepagineerd) — het scherm haalt **alle pagina's**
op in een lus (`limit: 100`, `volgende_cursor`; r. 53–59, met de motivatie "de boom heeft de
volledige set nodig") en vormt de boom **client-side** uit de **platte lijst met `ouder_id`**.
Er is géén genest lijst-endpoint; wel bestaat server-side `GET /processen/{id}/subboom`
(`ProcesBoomItem`: id/naam/ouder_id/niveau/pad — per wortel, niet register-breed). **Diepte:
onbegrensd** in het mechanisme (de rijen-loop recursief over `ouder_id`); geverifieerd tegen het
fase-0-scenario: Vergunningverlening → Aanvraag behandelen → **Besluit vastleggen** (3 niveaus)
rendert via twee keer uitklappen.

### B4. Draagt de bron wat de tree-view nodig heeft?

- **Naam + toelichting + ouder_id: ja** (`ProcesRead`, `schemas/proces.py:63–69` — id, naam,
  toelichting, ouder_id, created_at, updated_at). Een soort/type-veld bestaat niet (geen gemis:
  het model kent er geen).
- **"Geen ondersteunend systeem"-conditie: NIET in deze bron, wél afleidbaar.** Het
  lijst-endpoint draagt geen vervulling-informatie. De kaart-gap-cue leidt hem af uit de
  subgraaf-edges (`_procesZonderSysteem`: een vervulling dekt óók de voorouders). Voor dít scherm
  is dezelfde subboom-dekkings-semantiek bereikbaar met bestaande leespaden — bv. per proces-set
  één `procesvervullingen.lijst`-dekking is er niet, maar per wortel `processen.rollup(wortel)` +
  `procesvervullingen.lijst({proces_id})` (exact de fase-3/4-combinatie) levert de gevulde
  processen, waarna dezelfde gedekt-klim client-side kan. **Constatering: het kán met bestaande
  endpoints (N calls = 2 per wortel), er is niets voor gebouwd; of de cue hier gewenst is, is een
  open vraag (D7).**

## Blok C — Herbruikbare boom-bouwstenen

### C5. Wat is er al?

- **`procesBoom.js` (`procesBoomLayout`) is puur en NIET cytoscape-gebonden** (geen enkele
  cytoscape-import; het is bewust een gedeelde pure module). Herbruikbaar los van rendering:
  de **ouder-/kinderen-opbouw uit hiërarchie-paren, wortelbepaling, deterministische sortering
  (naam→id, `localeCompare('nl')`), diepte per knoop (`rij`) en de cyclus-guard**. Layout-specifiek
  (voor een DOM-tree onnodig maar onschadelijk): de **kolom**-toewijzing (x-positie per boom).
  Kanttekening: de input is `Set(ids)` + edges `{bron, doel}` — het lijstscherm heeft een platte
  `ouder_id`-lijst; de mapping (`ouder_id` → één edge per kind) is triviaal. NB: het lijstscherm
  heeft vandaag zijn **eigen** boom-opbouw (`kinderenVan` + recursieve `rijen`, zelfde
  naam-sortering) — er bestaan dus feitelijk **twee** boom-opbouwtjes naast elkaar
  (kaart-module vs. lijst-computed), functioneel gelijkgericht.
- **Een generieke DOM-tree-component (boom met verbindingslijnen) bestaat NIET.** Grep over
  views/src: ProcesLijst is de **enige** inspring-hiërarchie-weergave. Verwante maar andere
  vormen: `OnderliggendeProcessenSectie` (deelproces-**kopjes** + pad-bijschrift "via › …" —
  geen boomlijnen), `ProcesDetail`-broodkruimel (keten-tekst), de work-package-hiërarchie heeft
  géén boomweergave in de UI. Er is dus geen bestaande basis om te hergebruiken; wél het
  ArchitectuurLagen-precedent dat "tabel/lijst + visuele lens" naast elkaar kunnen bestaan.
- **Stijltokens rond hiërarchie (bestaand):** inspring `diepte * 1.5rem` (r. 213); expand-
  affordance = tekst-driehoekjes `▸/▾` in `--lk-color-text-muted` met hover naar
  `--lk-color-primary` + focus-outline (r. 222); rij-scheiding `divide-[var(--lk-color-border)]`;
  kaart-container `--lk-radius-card`/`--lk-shadow-sm`/`--lk-color-surface`. **Een
  verbindingslijn-token bestaat niet** — de natuurlijkste bestaande kandidaat is
  `--lk-color-border` (de bestaande scheidingslijn-kleur); dat is een constatering, geen keuze.
  Let op de bestaande Tailwind-vangrail: module-views onder `modules/` worden via `@source`
  gescand — nieuwe arbitrary-classes voor lijnen vallen daar al onder (geen extra config), maar
  de CSS-build-check-norm (kritische klassen in de dist-CSS) geldt wel.

## Blok D — Raakvlakken & risico's (feitelijk)

### D6. Wat raakt een tree-view-omzetting?

| Raakvlak | Feit | Aandachtspunt? |
|---|---|---|
| Zoekgedrag | Is al **boom-behoudend met auto-open** (pad naar treffer); een tree-view verandert daar niets aan tenzij gewenst | Alleen als Bert plat-zoeken wil (D7) |
| Bestaande tests | `ProcesLijst.test.js`: 9 tests op rijen/testids (`proces-rij-*`, `proces-toggle-*`), paginering-lus, zoek-open, doorklik, dialogs, gating, lijststaat | Ja — testids/structuur bewegen mee met de nieuwe markup; de gedrags-asserties kunnen blijven |
| Lege staat | Twee teksten (`lijst-geen-match`, `lijst-leeg` met route-naar-actie) | Behouden — UX-norm (lege staat met route) |
| Lijststaat | `openTakken`-ids + zoekterm via `useLijstStaat` | Serialisatie ongemoeid laten; een ander default-open-gedrag (D7) raakt de herstel-semantiek |
| Performance | Volledige set client-side (100/pagina-lus); boom + zoek zijn O(n)-computeds; processen = "begrensd organisatie-vocabulaire" (bewuste keuze, r. 51–52) | Nee voor de huidige schaal; het laadpad hoeft niet te veranderen |
| A11y | Nu `aria-expanded` + labels op de toggles; een echte tree-view kent ook een `role="tree"`-grammatica | Ja — vormkeuze (lijst-met-lijnen vs. ARIA-tree) bepaalt de test-/toetsenbord-eisen |
| CSS/rendering | Verbindingslijnen = nieuwe klassen in een module-view; dist-CSS-check-norm + browsercheck vóór commit (render-wijziging) | Ja — standaard LI032/ADR-040-vangrails |
| Beheer-affordances | Nieuw/Hernoemen zitten in de kop/rij; een tree-view herplaatst rij-acties mogelijk | Alleen presentatie; gedrag mag niet wegvallen (besloten uitgangspunt) |

### D7. Open ontwerpvragen voor Bert (gemarkeerd, niet beantwoord)

1. **Zoeken**: boom-behoudend met auto-open houden (huidig gedrag), of plat resultaat tijdens
   zoeken? En: moet zoeken ook op **toelichting** matchen (nu alleen naam)?
2. **Expand/collapse-default**: alles dicht (huidig), alles open, of niveau-1 open — en wat doet
   dat met de onthouden `openTakken`-staat?
3. **"Geen ondersteunend systeem"-cue** ook op dit scherm (kan met bestaande leespaden, 2 calls
   per wortel — B4), of blijft die kaart-only?
4. **Scharnierpunt — beheer op de boom**: hoort bij deze slice of een vervolgslice? Feitelijke
   stand: hier = top-level aanmaken + hernoemen; deelproces-aanmaak = detailpagina;
   **verwijderen = nergens in de UI** (API klaar); **verhangen = nergens in de UI** (API klaar,
   incl. kring-preventie en loskoppelen-naar-top-level). Kandidaat-scope-vragen: verwijderen-knop,
   verhangen (drag-drop of kies-nieuwe-ouder), deelproces-toevoegen-op-de-rij.
5. **Vorm/a11y**: lijst-met-verbindingslijnen (huidige `<ul>`-grammatica behouden) of een echte
   ARIA-`tree` (roving tabindex, pijltjesnavigatie — zwaarder, wel de formele tree-semantiek)?
6. **Bouwsteen-convergentie**: de boom-opbouw van dit scherm en `procesBoomLayout` (kaart) delen
   dezelfde semantiek maar zijn twee implementaties — bij de tree-view-slice convergeren naar één
   gedeelde opbouw (n=2 is bereikt), of bewust gescheiden laten?

---

*Einde feitenrapport. Read-only; geen code, tests of data gewijzigd.*
