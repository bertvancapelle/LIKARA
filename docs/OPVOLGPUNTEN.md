# LIKARA — Opvolgpunten (backlog)

Bijgehouden met de hand. Niet door `gen_build.py` gegenereerd.
Bron: sessie 2–3 (P1–P5, OP-9 t/m OP-12). Status per punt expliciet vermeld.

---

## OPEN

### Nieuwe opvolgpunten uit LI037 (2026-07-11)

1. **Proces-only diagram — eigen slice.** De kaart-proceszone met een **proces-only filter**
   (hergebruikt de bestaande Lagen-inzoom/doorwandel-mechaniek). Bestaansrecht bevestigd
   (structuur zien/presenteren), ook zonder afhankelijkheden. Status: **nog te ontwerpen**
   (eigen ontwerpdialoog) + bouwen.
2. **ADR-spoor procesafhankelijkheden/flow.** Proces→proces bestaat NIET als feature
   (`ouder_id` = enige band; ADR-042 parkeerde flow). Ze registreerbaar maken = domeinbesluit
   langs de Facade-over-Relatie-lijn (flow hergebruiken of triggering als 9e type +
   typeborging/registratie/projectie). Bepaalt hoe rijk het proces-diagram (punt 1) kan worden.
   Status: **open, ADR-waardig**.
3. **Detailscherm-procesbeheer.** Verwijderen/verhangen óók op het proces-detailscherm (nu
   alleen op de lijst). **Besluit A: nu niet** — de taakverdeling (structuur = lijst, inhoud =
   detail) is bewust. Status: **kandidaat-slice**.
4. **Rollenmodel: generieke matrix vs. functionele rollen.** Bv. een "Procesbeheerder" die de
   processtructuur en -toepasbaarheid beheert, los van de technische platformbeheerder.
   Strategisch ADR (raakt RBAC/Keycloak/seed platformbreed); + aanpalend concept
   **proces-toepasbaarheid** (wel/niet van toepassing, mogelijk per tenant — bestaat nu niet).
   Status: **te groot voor nu, bewust geparkeerd**.
5. **Productie-evaluatiepunt: proces-ingang-weergave.** Slimme default + wisselen achteraf
   (geen keuzevraag vooraf). Met echte gebruikers toetsen of een expliciete keuze of een
   voorkeur-laag (ADR-041) gemist wordt. Status: **evaluatie in productiegebruik**.
6. **History-grens hele-landschap-herstel** (bestaand punt, herbevestigd LI037). "← Terug"
   over de set→hele-landschap-vlag-grens herstelt de vlag niet (`_herstelToestand`); de
   inzoom-terugweg set↔set werkt volledig. Status: **read-only checkpoint + fix in een
   volgende sessie**.

---

### Stand V037 (sluitprotocol LI036 — Lagenweergave mét proceslaan, 2026-07-10)

Build **V036 → V037**. Geland: **"Lagen" als derde kaart-weergave** (preset-baanposities +
HTML-band-overlay, meet-stap-render-fix, maatwissel = resize+fit, `7b4c00c`), **rolbanen met
rol-accent** (partij als instance per rolbaan, rol-tags delen dim-staat, `7b4c00c`), **"ring uit
wint van gaps" + organisatiebalk in-beeld model i** (`0b4a5dd`), **proceslaan slice 2 stap 1–3**:
backend proces-projectie (roll-up naar hoofdproces, cyclus-veilig, één roll-up-definitie, engine
onaangeroerd, `d2b07f3`) + proceslaan/ring "Processen"/proces-vorm (`5fa5fe0`) + aantal-badge/
herkomst-popup/vervul-toggle met exact-ongedaan-maken (`f9a8a6f`). 16 patronen geborgd in vijf
likara-skills (`9914c25`); ADR-034/040 bijgewerkt naar de gebouwde realiteit — diepte-punt "alleen
hoofdprocessen" prominent als tussenstand (`a99fe23`). Tests: backend 1001/2 skipped, frontend
80 files/1006. Migratie-head **0059** (geen schema-wijziging).

**Top-6 volgende sessies: zie NEXT_SESSION.md** (deelprocessen eerste-klas op de kaart incl.
proces-als-vertrekpunt; plaatstaat-herstel na onderbreking; Architectuur-scherm verwijderen;
beginscherm als enige vertrekpunt; rapportage & export; bredere ruggengraat).

**Losse/kleinere punten uit LI036 (niet in de top-6):**

1. **Rol-accent beknopt/uitgebreid als persoonlijke kijkvoorkeur via ADR-041** — ná
   browserbevestiging van de uitgebreide vorm.
2. **Labelkeuze "Rollen & beheer" → "Partijen & rollen"?** — de baan verzamelt alle
   partij-rollen (gebruikt/levert/beheert/eigenaar), niet alleen beheer.
3. **ADR-register aanvullen** — `docs/adr/README.md` mist de rijen ADR-026 t/m 033, 035 en 036
   (ouder gat, door CC gemeld deze sessie; ADR-034/040-rijen zijn wél bijgewerkt).

---

### Stand V036 (sluitprotocol LI035 — lijststaat + ADR-042 volledig, 2026-07-09)

Build **V035 → V036**. Geland: lijststaat-patroon (`useLijstStaat`, 4 lijstschermen, `9128a24`) en
**ADR-042 volledig** — procesregister (nestbare boom, migraties 0056/0057), applicatiefunctie-catalogus +
koppelregel (0058/0059, `ddb7b7a`), proces-schermen + regel-acties + MeldingBanner (`3a65c3b`),
componentkant met vier-vragen-Overzicht + overlay-formulier (`0c4fe60`), en roll-up-inzicht +
organisatie-proceskijk + succes-toast-standaard (`8a76f55`). Zes browsercheck-bevindingen zijn als
systeembrede patronen geland (Dialog-primitive incl. scroll-schaduw, breedte-override-borging,
MeldingBanner, samengevoegd "Onderliggende processen"-blok, succes-toast, regel-acties) en met de
correcties vastgelegd in de acht likara-skills. Tests: backend 997/2 skipped, frontend 80 files/965.
Migratie-head **0059**.

**Nieuwe/geactualiseerde opvolgpunten uit LI035 (volgorde-advies):**

1. **ADR-034-herbouw lagenweergave (mét proces-laan).** De lagenweergave opnieuw opbouwen op de
   kaart-selectie, nu inclusief een proces-laan. Drie LI035-ontwerpnotities meenemen: (a) nesting van de
   procesboom binnen de business-laan (hoe diep tonen), (b) selectie-semantiek (wat betekent een
   proces-klik voor de kaart-set), (c) roll-up in de laan (toont een hoofdproces de doorgerolde
   componenten of alleen de directe).
2. **Audit-dekking entiteit-deletes (systemisch, pre-existing) — HOOG.** De centrale audit hangt op
   ORM-flush-hooks; een delete via het element-supertype (core-execute) audit de subtype-rij niet.
   Structurele oplossing kiezen (ORM-delete-norm, expliciete audit-regel bij element-delete, of
   DB-level vangnet). Zie likara-backend/-security (LI035).
3. **UI-consistentie-bundel.** (a) 11 bevestigingsdialoog-klonen migreren naar de gedeelde
   `BevestigVerwijderDialog`; (b) 2 bestaande warn-banners (ChecklistscoreSectie, MigratiegereedheidSectie
   e.o.) naar `MeldingBanner`; (c) `PartijRollenSectie` mist de verwijder-symmetrie (regel-acties-patroon).
4. **Kaart component-breed maken (ADR-spoor, herbevestigd).** IJkpunt: een database is nu niet
   zoekbaar/doorklikbaar op de kaart.
5. **Beginscherm-/kaartverfijningen (herbevestigd, was 3–6 in LI034):** filterbalk verbergen op leeg
   beginscherm; opgeslagen view + organisatie-scope (ADR-033-vervolg); filterbalk vereenvoudigen
   (BIV/Rol achter "geavanceerd"); beginscherm-contextvelden unie-feedback.
6. **GEMMA-procesimport/startset (eigen ADR-spoor, ná ADR-034).** Startset processen importeren
   (GEMMA-geënt); notitie: sturend/primair/ondersteunend als filter-/typeringsvraag meenemen; de
   LI035-validatie dat het GEMMA-landschap 1-op-1 op het model past is de basis.
7. **LandschapskaartView: historische "LI036"-commentlabels rechtzetten** (mislabeld — die wijzigingen
   waren LI034; klein, alleen comments).

**Reeds afgerond in LI035 (uit de actieve lijst):** lijststaat-terugnavigatie (was 1e taak);
proces/functie-inzicht punt 1 (ADR-042, volledig — het "koppel aan het directe ondersteunende
component, erf de rest"-uitgangspunt is in de ADR verwerkt; component-breed als vangnet gerealiseerd).

**Herbevestigd (blijft open, uit eerdere sessies):** ADR-035 slice 3 (signalering-vervolg); ADR-036
UI-restpunt (coarse organisatiegebruik-form); `VerantwoordelijkheidSectie` partij-picker-scope
(ADR-024-domeinvraag); LI032-restpunten (username≠e-mail post-check, 404-friendly display,
reseed-ergonomie, auth #5c end-to-end); LI033b-stash `stash@{0}` (beslissing Bert: droppen of houden);
ADR-040-vervolgfasen (terug/vooruit-navigatie = verplichte terugbouw, interactie-basis, 4 ringen,
overige objecttypes centreerbaar, scope-B).

---

### Stand V035 (sluitprotocol LI034 — ADR-041 voorkeuren + kaart-bugfixes, 2026-07-08)

Build **V034 → V035**. Geland: ADR-041 persoonlijke voorkeur-laag (`gebruiker_voorkeur`, migratie **0055**,
RBAC eigen-scope, `9498983`), component-breed organisatiegebruik-schrijf-slot (`b05cc53`), terugrol
sectie-voorkeur (`f5e7afe`), kaart-kijkfilter-standaard + reload-fix (`c8ae3c7`), kaart-bug B doorklik
(`33fa485`), kaart-bug A leeg canvas (`3d889ab`), + 7 skillpatronen. Tests: backend 960/2 skipped,
frontend 71 files/869. Migratie-head **0055**.

**Eerste taak volgende sessie (read-only):** lijststaat (filter/zoek/sortering) behouden bij terugnavigeren
vanuit een detailscherm — bevestigd op Partijen. Momentkeuze-behoud bij terugkeer, géén voorkeur-laag.
Zie NEXT_SESSION.md.

**Nieuwe/geactualiseerde opvolgpunten uit LI034 (volgorde-advies):**

1. **Proces/functie-inzicht (groot, ADR-waardig — VERDER VERDIEPEN).** Component "vervult een rol in" een
   proces/functie; proces/functie als één hiërarchische laag (proces boven, functie eronder); impact rolt
   omhoog (functie-raakvlak telt mee op procesniveau); rol als beheerbaar catalogus-kenmerk; **begin grof**
   (proces + koppeling eerst, functie later); flow/volgorde tussen stappen bewust buiten scope.
   **Kern-uitgangspunt (LI034, nog te verdiepen):** een proces koppelt aan het **component dat het
   functioneel ondersteunt** (in de praktijk vrijwel altijd de applicatie/dienst — het "loket"). De
   **onderliggende afhankelijkheden (database, infra, contract, leverancier) worden geërfd via de al-
   geregistreerde component-ketens** — niet dubbel vastleggen. De impactvraag "wat raakt dit proces" volgt
   dan automatisch de bestaande keten (proces → applicatie → …). **Component-breed blijft als vangnet
   mogelijk** (koppeling mág aan elk componenttype als een proces rechtstreeks op iets zonder applicatie-
   tussenlaag steunt), maar de norm is: koppel aan het directe ondersteunende component, erf de rest.
   Sluit aan op LIKARA's principe "relatie één keer vastleggen, impact volgt de keten" (geen dubbele/
   afgeleide registratie). **Dit uitgangspunt expliciet verder verdiepen in de uitwerking** — de grens
   tussen directe koppeling en geërfde keten, en wanneer een directe niet-applicatie-koppeling terecht is.
   Aanpak: read-only verkenning (element-familie-subtypes, hiërarchie-constructie, relatiekenmerk-
   catalogus) → concept-ADR.
2. **Kaart component-breed maken (ADR-spoor).** De kaart is bewust applicatie-centrisch (`appNodes`/
   zoeklijst, `componentBuren`, buren/context-set-acties, diepte-2-ego). Elk componenttype zoekbaar/
   doorklikbaar/als buur maken raakt die ontwerpkeuze → eigen ADR. IJkpunt: een technology-component
   (database) is nu niet zoekbaar en heeft geen doorklik.
3. **Beginscherm-filterbalk verbergen op het lege beginscherm.** De linker filterbalk dubbelt met "Begin
   je verkenning" zolang de kaart leeg is; balk pas tonen zodra de kaart getekend is. (Apart: horen de
   start-filters Laag/Hosting/Eigenaar achter "+ Filters" daar wel?)
4. **Opgeslagen view onthoudt de organisatie-scope niet (ADR-033-vervolg).** Een view bewaart bewust
   alleen de set, geen kijk-instellingen. Weging: wil je dat een view ook de organisatie-scope (en evt.
   andere kijk-instellingen) bewaart, tegen de "view = startpunt"-intentie in?
5. **Filterbalk vereenvoudigen.** BIV-drempels + Rol zijn specialistisch (audit-/risicolens, alleen op
   geclassificeerde componenten) — kandidaat voor een "geavanceerd"-inklap; op beide weergaven of alleen
   Overzicht?
6. **Beginscherm-contextvelden (unie-gedrag).** Leverancier/Contract/Organisatie stapelen additief (unie
   met dedup). Wenselijk? Feedback per veld ("N toegevoegd")?

**Reeds afgerond in LI034 (uit de actieve lijst):** ADR-041 (persoonlijke voorkeuren + kaart-kijkfilter-
standaard + reload-fix); kaart-bugs A (leeg canvas) en B (doorklik gelijkgetrokken); component-breed
organisatiegebruik-schrijf-slot.

---

### Stand V034 (sluitprotocol LI033 — ADR-040 kaart-herbouw, 2026-07-07)

Build **V033 → V034**. Geland (ADR-040 Fase 1): deterministische render-eigenaar / fcose weg
(`bf5c287`), tweedeling Overzicht/Praatplaat + expliciete weergave-state + schakelaar, Impact-verkenner
afgeschaft (2a, `e8fe7d3`), voorspelbare organisatie-scope (eenmalige seed, balk alleen op Overzicht,
2b, `e7f74ef`), afgeleide gebruikt-lijn org→app + gebruikt-ring + afdeling-sub-picker weg (3-1,
`559a34c`), layout-herziening (samenval-fix `animate:false`, Overzicht=grid centrumloos, Praatplaat=
concentric+ellips, grotere knopen; `559a34c`), en 12 skillpatronen (`ef17fed`). Tests: backend 951/2
skipped, frontend 71 files/840. Geen schema-wijziging (migratie-head **0054** ongewijzigd); enig
backend-raakvlak = de afgeleide read-only gebruikt-edge.

**Vervolgfasen ADR-040 (open, geprioriteerd):**
- **Terug/vooruit-navigatie — VERPLICHTE terugbouw (uitgesteld, niet geschrapt).** De render-eigenaar is
  ontvlochten zodat history als **losse laag** terug kan. Hoog: het is bestaand gedrag dat tijdelijk niet
  door de nieuwe weergave-state loopt.
- **Interactie-basis: klik = highlight + rest dimmen + verplaatsbare popup** (kern-details + relaties in
  leesbare taal + link naar de volledige pagina). Dubbelklik = hercentreren (bestaat al). Fase 2.
- **De 4 component-ringen volledig inrichten** (gebruikt door · beheer · contracten & leveranciers ·
  infra & koppelingen) — fase 2; de praatplaat toont nu de ego-kring (skelet).
- **Overige objecttypes centreerbaar** (contract, leverancier, afdeling, persoon/rol, infra) — elk een
  ring-definitie op de praatplaat-motor (ADR-040 open subknoop 1).
- **Scope-B-verfijning** (toggles onthouden over set-wijzigingen) — later, samen met history-/scope-werk
  (nu A: elke set-wijziging → alle orgs aan).
- **LI033b-stash `stash@{0}`** — handoff/org-bron/`toonImpactVoor`/grof-only bleken al geland vóór de
  herbouw; alleen gebruikt-edge + gebruikt-ring + sub-picker waren nieuw (geland in 3-1). **Beslissing
  Bert:** stash droppen of als referentie houden — niet zelf droppen.

**Herbevestigd (blijft open, uit eerdere sessies):**
- ADR-036 UI-restpunt (coarse `organisatiegebruik`-form).
- `VerantwoordelijkheidSectie` partij-picker-scope (ADR-024-domeinvraag).
- LI032-restpunten: gebruikersnaam≠e-mail post-check, 404-friendly display, reseed-ergonomie.

### Stand V033 (sluitprotocol LI032 — gebruiker-cluster, 2026-07-05)

Build **V032 → V033**. Geland: contactpersoon uit register (ADR-039, migratie 0054), centrale
sessie-vangrail, ter-plekke-aanmaken afdeling (gedeelde `AfdelingSelect`, 4 plekken), gebruiker
aanmaken + bewerken (organisatie intern-only + gescoopte afdeling), account-/picker-reparaties
(conditionele Keycloak-aanroep, PUT zonder username, 2e interne testorganisatie, stale-label-`:key`,
param-filterende picker-integratie-testhelper), en 18 LI032-skillpatronen. Tests: backend 866+80,
frontend 825; migratie-head 0054.

**Nieuw geparkeerd deze sluiting:**
- **Provisioning username==email-aannames.** De update-PUT stuurt geen `username` meer (opgelost in
  `ca8c999`); controleer of elders in de provisioning-flow nog impliciete `username==email`-aannames
  zitten. Laag, auth.
- **404 op een verdwenen bewerk-/detailitem** vriendelijker tonen — inline "bestaat niet (meer)"
  i.p.v. een toast op een leeg formulier. Laag, UX (kwam op bij de reseed-stale-id-casus).
- **`LandschapskaartView.test.js` / `LandschapskaartPopups` parallel-flake** (cytoscape
  unhandled-rejections bij teardown) — geen falende test; mee te nemen bij de impact-verkenner-
  render-herbouw.

### Auth-cluster (LI032 — na de verlopen-sessie-vangrail)

- **#5c — echte end-to-end auth-keten-test (eerste vervolg binnen het auth-cluster).** De 401→refresh→
  retry-logica is nu **structureel** gedekt (offline, gemockt): frontend `api.test.js` (3 refresh-takken +
  vangrail-handler), backend `test_auth_pkce.py` (`/auth/refresh` happy + 3 faalpaden). **Het gat:** geen
  test die de seams samen bewijst — een kortlevende `lk_session` → echte `/auth/refresh` → echte Keycloak
  refresh-grant → echte Redis-handle-rotatie → geslaagde retry, plus een écht-verlopen refresh die naar
  login leidt. Vergt de volledige stack + een manier om access-token-expiry te forceren (korte TTL).
- **Reseed/herstart doodt sessies stil (dev-ergonomie).** Een stack-reset (Redis/Keycloak weg) →
  `auth_refresh:{sessie_id}` verdwijnt → refresh faalt → 401. De centrale vangrail (LI032) vangt het
  symptoom nu **netjes** af (redirect naar login i.p.v. rauwe code). Resteren: na een reseed opnieuw
  inloggen is verwacht gedrag; Redis/Keycloak-persistentie over een reset heen is een aparte,
  lager-geprioriteerde afweging.

### Stand V032 (sessie-afsluiting LI031 — ADR-038 gebruikersgroep-consolidatie + intern/extern, 2026-07-04)

Build **V031 → V032**. Eén consistent model: een gebruikersgroep hoort **altijd** bij een organisatie;
burger-doelgroepen zijn gewone **externe organisaties met afdelingen**. Intern/extern is een expliciet
kenmerk op partijen (kiesbaar + zichtbaar). Dode resten opgeruimd.

**Geland deze sessie:**

| Commit | Slice |
|---|---|
| `1d9ab3a` | ADR-038 geschreven (register bijgewerkt) |
| `2f1c816` | Slice 1a — `partij.scope` (`partij_scope_enum` intern/extern, additief), migratie `0052`: nullable + 2 CHECKs (gezet iff organisatie/externe_partij; externe_partij vast extern; afdeling/persoon leiden af); default extern op organisatie; seed BvoWB=intern; dubbele engine-borging |
| `195c489` | Slice 1b — consolidatie, migratie `0053`: `gebruikersgroep.gebruik_id` NOT NULL (FK → RESTRICT); `burger`-aard uit `partij_aard_enum` (type-recreate); organisatie verplicht (Create + service-422; werk_bij weigert null); dode resten weg (kaart-veld `gebruikt_door_organisatieloos` + signaal `gebruikersgroep_zonder_organisatie`); seed: burger-doelgroepen = 3 externe organisaties + 6 segment-afdelingen + 5 groepen |
| `edb4eb8` | Slice 2a — groep-dialoog organisatie verplicht (client-side inline-melding + `*`-markering; org-loze payload-tak weg; dode `orgAard`-state opgeruimd) |
| `3ec3320` | Slice 2b — intern/extern-UI: kiesbaar in `PartijFormulier` (radio-kaartjes, default Extern; vast "Extern" bij externe partij; niet bij afdeling/persoon), leesbaar in `PartijDetail` |
| `6702bd2` | Slice 2c — kaart: dood burger-silhouet/label/legenda/predicate opgeruimd |

**Nieuw opvolgpunt uit LI031 — top-prioriteit LI032:**

1. **Contactpersoon als keuze uit personen van de eigen organisatie — SCHEMA-GATE (ADR-waardig).**
   **Expliciet vóór GebruikersgroepDetail (besluit Bert).** Vrije tekst → verwijzing naar een
   **persoon-partij van de organisatie zelf**. Sjabloon = ADR-036a/037 (FK-kolom `partij.contactpersoon_id`
   + validator "persoon binnen deze organisatie" + read-verrijking `contactpersoon_naam` + migratie +
   dev-reseed). Bouwstenen klaar: read `api.partijen.lijst({aard:'persoon', organisatie_id})`, `ZoekSelect`,
   identiteit "persoon — afdeling — organisatie" (`_verrijk_context`). Beslist: optioneel; keuze uitsluitend
   uit personen met `organisatie_id = deze partij`; geen vrije tekst meer. **Vijf open ontwerpvragen vóór bouw:**
   (a) VOORAAN — contactpersoon ter plekke aanmaken bij nog-geen-personen (zoals de afdeling-picker), of
   alleen kiezen uit bestaande? (b) op welke aarden het veld — alleen organisatie-achtig (organisatie +
   externe_partij) i.p.v. alle? (c) vervangen vs. additief (aanbeveling: vervangen, met reseed);
   (d) `telefoon`/`mobiel`/`email`-vrijvelden bewust buiten scope; (e) migratie-landing defensief/reseed
   zoals `0053`.

**Runtime-restpunt:** verse reseed vóór browserverificatie (BvoWB=intern + burger-doelgroepen zichtbaar):
`docker compose down` → `docker volume rm likara_lk_postgres_data` → `up -d` → `dev_seed_testdata.py`
(`down -v` = deny).

**Doorgeschoven (ongewijzigd geldig):** GebruikersgroepDetail (opzet + signaal-scope beslist) + BlokkadeDetail
(conceptuele keuze eerst); org-context-patroon naar leverancier-picker + PartijLijst (+ intern/extern-kolom);
auth/sessie-cluster; Impact-verkenner render-herbouw; ADR-036 begin-grof-invoerroute.

Tests: backend **851** (module) + **80** (platform), 2 skipped · frontend **780**. Migratie-head **0053**.
ADR-register: **ADR-038** opgenomen.

---

### Stand V031 (sessie-afsluiting LI030 — ADR-037 verantwoordelijke per checklistantwoord, 2026-07-03)

Build **V030 → V031**. Het vrije-tekstveld "Eigenaar" op een checklistantwoord vervangen door een
gestructureerde **verantwoordelijke** (afdeling óf persoon uit het register); blokkade-eigenaar afgeleid.

**Geland deze sessie:**

| Commit | Slice |
|---|---|
| `e21a28e` | ADR-037 Pass 1 — schema-gate (migratie `0051`): `checklistscore.verantwoordelijke_id` (composiet-FK, SET NULL) vervangt `eigenaar`; `blokkade.eigenaar` gedropt (afgeleid); aard-validatie 422; dubbele engine-borging; seed-scenario |
| `4c8d113` | ADR-037 Pass 2 — verantwoordelijke-picker (afdeling/persoon, `aard_in`); aandacht-signaal `antwoord_zonder_verantwoordelijke` (engine-veilig via `table()`-handle) + velduitleg; Opslaan-knop leesbaar; identiteit "afdeling — organisatie" / "persoon — afdeling — organisatie" in lijst/veld/na-selectie |

**Nieuwe opvolgpunten uit LI030 (van meest naar minst gebruikerswaarde):**

1. **Detailpagina's — GebruikersgroepDetail + BlokkadeDetail.** GebruikersgroepDetail verst (grounding
   gedaan; scherm + identiteit-/applicatie-weergave + signalen-ter-plekke + objecthistorie-ontsluiting
   ontbreken). BlokkadeDetail: **open conceptuele keuze** (eigen pagina vs. doorklik naar de component-
   checklisttab) — eerst met Bert uitdenken vóór bouw; detail-read verrijken met herkomst.

2. **Breder org-context-patroon** — "afdeling — organisatie"-ontdubbeling (via `gebruikersgroepIdentiteit`)
   ook toepassen op de **ContractFormulier-leverancier-picker** + **PartijLijst** (de resterende niet-org-
   gescoopte afdeling/persoon-lijsten). ADR-037 paste het toe op de verantwoordelijke-picker.

3. **Auth/sessie-cluster** (uit het `NIET_GEAUTHENTICEERD`-onderzoek): (a) dev-sessie-robuustheid bij
   reseed — een stack-herstart (Redis/Keycloak) doodt levende sessies stil; persistentie of
   gedocumenteerde re-login; (b) UX-vangrail — 401 na gefaalde refresh → gebruiker naar opnieuw inloggen
   leiden i.p.v. een kale rode `NIET_GEAUTHENTICEERD`-toast; (c) auth/refresh-testgat — nu overal gemockt,
   geen echte 401→refresh→retry-dekking.

**Incident-lessen LI030 (geborgd in skills):** groene tests dekten tweemaal een kapotte UX niet (pas in
de browser zichtbaar): onleesbare Opslaan-knop (`--lk-color-accent` #E8F0FB + `text-white` = wit-op-
bijna-wit) en veld-vs-lijst-identiteit. Vuistregels toegevoegd aan `likara-frontend` (knop-leesbaarheid),
`likara-tests` (toets visuele/interactie-staat, niet alleen payload; browser-check vóór commit) en
`likara-ux` (identiteit-patroon voor niet-org-gescoopte afdeling/persoon-lijsten).

---

### Stand V030 (sessie-afsluiting ADR-036 + Velduitleg + ADR-036a, 2026-07-03)

Build **V029 → V030**. Organisatiegebruik van applicaties **end-to-end** gebouwd, veld-uitleg op alle
formulieren, afdeling structureel gemaakt, plus drie gerichte UI-fixes.

**Geland deze sessie:**

| Commit | Slice |
|---|---|
| `8e7e419` | ADR-036 pass 1 — grof gebruiksfeit + gebruikersgroep-verfijning (schema) |
| `bff1254` | ADR-036 pass 2 — kaart-afleiding + signaal + identiteit (read-only) |
| `889fc4d` | ADR-036 invariant-test "afdeling-met-org ⟹ grof feit" |
| `7cc6e24` | Velduitleg slice 1 — `VeldUitleg`-component + centrale `velduitleg.js` |
| `8ea87be` | Velduitleg slice 2 — content-uitrol (popover-'i') over alle formulieren |
| `480fa84` | ADR-036a pass 1 — gebruikersgroep-afdeling structureel (schema+service+seed, migratie 0050) |
| `a09a8cb` | ADR-036a pass 2 — afdeling-picker (search-first create-in-lege-zoekstaat) |
| `929435e` | Fix — bewerken-voorvulling gebruikersgroep (organisatie voorvullen uit grof feit) |
| `0e439d3` | Fix — contract-leverancier-picker versmald (`aard_in`) + seed geverifieerd geldig |

- **ADR-036 (compleet):** grof "organisatie gebruikt applicatie"-feit (`organisatiegebruik`) +
  gebruikersgroep als fijne verfijning (`gebruik_id`); kaart-afleiding "gebruikt door", read-only signaal
  "gebruik bekend, detaillering ontbreekt", identiteit "afdeling — organisatie". Invariant geborgd.
- **Velduitleg-slice:** alle formulieren voorzien van popover-'i'; ADR-036a-identiteit partij-verankerd.
- **ADR-036a (afdeling structureel):** `gebruikersgroep.afdeling` (vrije tekst) → `afdeling_id` →
  organisatie_eenheid-partij binnen de grove-feit-organisatie (migratie **0050**).
- **Drie UI-fixes:** bewerken-voorvulling (organisatie uit grof feit); contract-leverancier-picker
  versmald; (+ search-first afdeling-picker uit ADR-036a pass 2).

**Afgevinkt / opgelost deze sessie:**
- **Eigenaar-organisatie-picker** — onderzocht, **geen defect**: filter is correct (`aard=organisatie`),
  seed compleet (4 orgs), query levert alle 4. "Alleen BvoWB" was **stale seed-data** (reseed lost het op).
- **Afdeling-structureel** (ADR-036a) — gebouwd.
- **Contract-leverancier picker-scope** — versmald naar `aard_in=[organisatie, organisatie_eenheid,
  externe_partij]`; **seed geverifieerd geldig** (12 externe_partij + 3 organisatie voor de BvoWB-DVO's;
  nul persoon/burger). Geen seed-wijziging nodig.

**Nieuw open (verwerkt in de top-5):**
- **GebruikersgroepDetail + BlokkadeDetail** — nu ontgrendeld (betekenislaag is er). BlokkadeDetail-
  restpunten: `BlokkadeRead` verrijken met herkomst; eigenaar = vrij tekstveld; `objecthistorie._TYPES`
  uitbreiden met `gebruikersgroep` + `blokkade`.
- **ADR-036 "begin grof"-invoerroute** — frontend-formulier om een grof feit los vast te leggen
  (backend bestaat al). Zonder dit vuurt "detaillering ontbreekt" alleen op seed-data.
- **Verantwoordelijkheid-/roltoewijzing-partij-picker** — eerst de **domeinvraag** (welke aarden mogen een
  beheerrol dragen?), dán de scoping. Bewust niet blind versmald.

**Klein / parked toegevoegd:** RelatieKenmerk-dimensie-velduitleg (content klaar in `velduitleg.js`;
wacht op een invoerveld — nu sectie-gedreven).

**Nog open (ongewijzigd):** Impact-verkenner render-herbouw (top-5, echte cytoscape-render); ADR-035
Slice 3 (configureerbare score-drempel); ADR-029 Fase 5; ADR-023 Fase F-rest; OP-30. **Test-hygiëne:**
~30–33 Cytoscape-mock-consoleruis in `LandschapskaartView.test.js` (geen falende test) — bij render-herbouw.

Tests: backend **914/0** (2 skipped) · frontend **763**. Migratie-head **0050**.
ADR-register: **ADR-036** + **ADR-036a** opgenomen.

---

### Stand V029 (sessie-afsluiting LI060 + ADR-028, 2026-07-02)

Build **V028 → V029**. Componenttype-catalogus uitgebreid (top-5 #1 geland) én
**componentclassificatie (ADR-028) end-to-end** — rol + BIV door data/API/beheer/formulier/
detail/lijst/kaart/signalering.

**Geland:**
- **LI060 (`7c36b33`):** componenttype-catalogus **8 typen** — `applicatieserver`→`server_compute`,
  `middleware`→`integratievoorziening` (nu system_software/technology), nieuw `landelijke_voorziening`;
  drie extra beoordeelbaar (elk 1 tenant-startvraag). Geen migratie (seed = single source; reseed).
- **ADR-028 slice 1 (0048, `d61bddf`):** schema-fundament — 2 platform-catalogi (`componentrol_optie`,
  `biv_schaal_optie`) + 4 component-kolommen (rol NOT NULL default `interne_applicatie`; 3× BIV nullable)
  + RBAC (2 `PlatformEntiteit`) + audit. Engine-borging dubbel.
- **ADR-028 slice 2 (`939dbf2`):** componentformulier + detail (rol + BIV) + `RolConfigBeheer`/
  `BivConfigBeheer` + additief `/componenten/opties` (rol-opties + ordinale BIV-niveaus).
- **ADR-028 slice 3 (`131b674`):** rol/BIV-filter in lijst (server-side, drempel op `volgorde`) + kaart
  (client-side, filter-exemptie context-nodes) + gestippelde rand voor `externe_dataprovider`.
- **ADR-028 slice 4 (`b351b59`):** kritiek signaal "BIV-classificatie onvolledig" (≥1 BIV-veld leeg) —
  signalering nu **11 signaaltypen** (6 kritiek / 5 aandacht). ADR-035 bijgewerkt.

**ADR-036 (nieuw — functioneel besloten, bouw uitgesteld):** organisatiegebruik van applicaties —
grof "organisatie gebruikt applicatie"-feit + de gebruikersgroep als fijne verfijning (identiteit =
afdeling + organisatie) + read-only signaal "gebruik bekend, detaillering ontbreekt". Schema-rakend,
meerdere gate-slices; **design-checkpoint first** (open bouwknopen in `docs/adr/ADR-036`).

**Detailpagina's (gebruikersgroep + blokkade) — grounding gedaan, geparkeerd tot ADR-036 beslist**
(de groep-pagina hangt aan de nieuwe betekenislaag). BlokkadeDetail-restpunten: detail-read
(`BlokkadeRead`) verrijken met **herkomst** (checklist-item `vraag_code`/`vraag`/score — zit nu alleen
in het lijst-/overzicht-item); **eigenaar = vrij tekstveld** (bestaat + bewerkbaar; géén structurele/
roltoewijzing-afgeleide verantwoordelijke — dat is geparkeerd); **objecthistorie-route-allowlist
(`objecthistorie._TYPES`) uitbreiden** met `gebruikersgroep` + `blokkade` voor het 'i'-paneel
(audit-data bestaat al; alleen de route-allowlist + `haal_op`-resolutie ontbreekt).

**Nog open (ongewijzigd):** Impact-verkenner render-herbouw (top-5, echte cytoscape-render); ADR-035
Slice 3 (configureerbare score-drempel); ADR-029 Fase 5; ADR-023 Fase F-rest; OP-30. **Test-hygiëne:**
~30 Cytoscape-mock-consoleruis in `LandschapskaartView.test.js` (geen falende test) — bij render-herbouw.

Tests: backend **898/0** (2 skipped) · frontend **742**. Migratie-head **0048**.

---

### Stand V028 (sessie-afsluiting LI059, 2026-07-02)

Build **V027 → V028**. Component-focus-herfundering **volledig afgerond** — `component` is de enige
bron in data/API/RBAC/audit. (Slice 3/4/5 uit de V027-backlog zijn hiermee geland.)

**Geland:**
- **LI059 Slice 3 (0047, `03360ea`):** `applicatie`-subtabel gedropt; `applicatie_service` als dunne
  facade over `component`; dual-write weg; byte-compat behouden; dubbele engine-borging + verse reseed.
- **LI059 Slice 4 (`6fa655e`):** frontend-cutover — één `ComponentFormulier` (3 transitie-velden voor
  élk type) + één rijk `ComponentDetail` (tab-IA, conditioneel); `ApplicatieFormulier`/`ApplicatieDetail`
  geretireerd; `/applicaties*` → redirects. Geen functie verloren.
- **LI059 FacadeOpruiming (`1c40814`):** volledige purge — `routes/applicatie.py`/`schemas/applicatie.py`/
  `applicatie_service.py` + `api.applicaties` weg; `Entiteit.APPLICATIE`/audit-allowlist/objecthistorie-tak
  weg (RBAC-matrix 23→22 = 352); validators → `schemas/_validators.py`; creatie-kern → `component_service`.
- **LI059 Slice 5:** ADR-021/022 slotsecties "Eindstaat" + ADR-register + `likara-domeinmodel §1` bijgetrokken.

**Nog open (niet-LI059, ongewijzigd):** componenttype-catalogus uitbreiden (top-5 #1); Impact-verkenner
render-herbouw (top-5 #2; edges-onzichtbaar-bug zit in de echte cytoscape-render); ADR-035 Slice 3
(configureerbare score-drempel); ADR-029 Fase 5 (`gereedmeld_recht`); ADR-023 Fase F-rest; OP-30 (env-
auth-test, omgevingsgebonden). **Los test-hygiëne-punt:** ~29 Cytoscape-mock-console­ruis in
`LandschapskaartView.test.js` (geen falende test) — bij de render-herbouw meenemen.

Tests: backend **865/0** (2 skipped) · frontend **717**. Migratie-head **0047**.

---

### Stand V027 (sessie-afsluiting LI057+LI058, 2026-07-01)

Build **V026 → V027**. Component-focus-herfundering **Slice 1 + Slice 2** geland (+ OP-30 afgerond).

**Geland:**
- **LI057 (Slice 1, 0045):** `migratiepad/complexiteit/prioriteit` component-breed (basis-`component`,
  NOT NULL + defaults); enum `tijdelijk_gedeeld → gedeeld`. Expand met dual-write naar de behouden
  applicatie-subtabel. Dubbele engine-borging.
- **LI058 (Slice 2, 0046):** scoren per type via `checklist_dragend`; `database` beoordeeld + 6-vragen
  startset; **profiel-backfill** bij False→True (platform-toggle → per-tenant RLS-scoped backfill,
  idempotent; True→False inert). Engine al generiek.
- **OP-30:** env-afhankelijke auth-cookie-test deterministisch (afgerond, `b99b901`).

**Backlog (component-focus, volgende sessies):**
- **Slice 3 (contract):** applicatie-subtabel droppen + `applicatie_service`/routes/schemas opheffen.
- **Slice 4 (frontend):** één `ComponentFormulier`; `ApplicatieFormulier`/`ApplicatieDetail` retireren.
- **Slice 5:** tests + TST + ADR-021/022 afronding.
- **Componenttype-catalogus uitbreiden** (integratie/koppel, landelijke voorziening, server/compute;
  consolidatie applicatieserver+middleware); daarna fileshare → SaaS beoordeelbaar maken.
- **Impact-verkenner render-herbouw** (deterministische render-eigenaar; edges-onzichtbaar-bug zit in
  de echte cytoscape-render, niet in de logica).

Tests: backend **944/0** (2 skipped) · frontend **745**. Migratie-head **0046**.

---

### Stand V026 (sessie-afsluiting LI051, 2026-06-30)

Build **V025 → V026**. Deze sessie ging volledig over de **code-rebrand
`cd_`/`complidata`/`CompliData`/`CompliMan` → `lk`/`likara`/`LIKARA`** (LI038–LI050).
De oorspronkelijke V025-prioriteiten zijn NIET opgepakt en blijven de top-5 (zie
NEXT_SESSION).

**Geland in LI038–LI050:**
- LI038–040: skills/docs (senior-architect ADR-conventie + V691-legacy-banner, db-naam, naamhistorie)
- LI042: bugfix `sluit_acties.py` (scande niet-bestaande `skills/complidata`)
- S1+S8 (fd82626): cosmetische code-namen + role-prefix
- S2 (27066a1): CSS-tokens `--cd-` → `--lk-` (frontend-breed incl. module-frontend)
- S3 (84e2ce7): cookies `lk_session`/`lk_refresh`
- S4 (e9e4835): env-flags `LIKARA_TEST_MODE`/`LIKARA_FIXTURE_SET`
- S5 (4e0f6a0): localStorage `lk-sidebar-ingeklapt` + backup-basisnaam `likara_*.sql`
- LI049 (28e421c): migratie-revisie-id ≤32 (deploy-blocker) + handhavingstest
- S6 (d67e968): infra `lk_rabbit`, vhost `lk-{slug}`, MinIO `likara_admin`, paden `~/likara/`
- S7 (f7ecd7c): DB-triggerfunctie `lk_audit_append_only` (forward-migratie 0044, append-only LIVE geborgd)

**Resterend uit de rebrand (geen code meer):**
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL;
  lokale map `~/complidata/` opruimen (stack draait al op `~/likara/`). Berts GitHub-actie.
- **Deploy-side (andere omgevingen)** — `.env`/secrets bijwerken: `RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-namen `lk_session`/`lk_refresh`,
  env `LIKARA_TEST_MODE`/`LIKARA_FIXTURE_SET`; re-provision vereist.
- **Procesgat secrets-backup** — `~/complidata/secrets/.env` heeft nooit bestaan;
  CLAUDE.md documenteert nu `~/likara/secrets/` als backuplocatie die feitelijk niet
  gevuld werd → verzoenen.
- **env-test-robuustheid** — zie OP-30 (`test_callback_succes_zet_lk_session_cookie`
  laat `cookie_secure` van de omgeving afhangen; expliciet zetten).
- **Optioneel** — vangrail-greps uitbreiden met live `cd_`/`complidata` (scoped, excl. historie).

### Stand V025 (sessie-afsluiting LI024, 2026-06-29)

Build **V024 → V025**. LI024 = volledige prioriteitenlijst afgewerkt +
uitgebreide UX-verbeteringen Landschapskaart.

**Geland in LI024:**
- Skills aangemaakt: likara-werkprotocol, likara-domeinmodel, likara-ux (33ded4f)
- ADR-035 Slice 1: 2 kritieke signalen + Signalering-scherm 2 tabs (1903f14)
- ADR-035 Slice 2: 5 aandacht-signalen + centraal overzicht (0247506)
- ADR-025 "Bekijk op kaart"-knop + beginscherm-fix (f87182e)
- ADR-026 ArchiMate typering: al gerealiseerd V013 — geen bouw nodig
- ADR-030 Contract coverage per-band: migratie 0043 + service + UI (0953857)
- Klaarverklaring-blok ComponentDetail: al gerealiseerd — geen bouw nodig
- Interactieve legenda: dim/spotlight + draggable (533ec94 + 537941f)
- Zoekbalk bug fix + resultaten in kaart-modus LI028/029 (740aae3 / commit LI029)
- fcose layout-optimalisatie LI030 (537941f)
- Dubbele nodes fix LI031 (fe9873c)
- Positie-stabiele re-render LI032 (013d240)
- Detail-popup draggable + overlap-fix LI033/034 (commit LI033)
- LIKARA tagline fix LI035 (commit LI035)
- Eigenaar-ring fix LI036 (f8e735e)
- Ring-reactivity regressietest LI037 (144ecd9)

**Nieuw open (prioriteitsvolgorde voor LI025):**
1. ADR-035 Slice 3 — Registratie onvolledig (configureerbare drempelwaarde)
2. Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie)
3. GebruikersgroepDetail standalone pagina
4. BlokkadeDetail standalone pagina
5. Zoekbalk contextlabel "Component toevoegen aan beeld"

**Structureel onmogelijk / uitgesteld:**
- blokkade_zonder_eigenaar — schema-/semantiekherziening vereist
- badges GebruikersgroepDetail/BlokkadeDetail — wacht op detail-pagina's

### Stand V024 (sessie-afsluiting LI023, 2026-06-29)

Build **V023 → V024**. LI023 = Landschapskaart Fase B compleet + UX-fixes +
ADR-besluiten + PRODUCTVISIE.md.

**Geland in LI023:**
- Werkprotocol herbevestigd + geborgd in likara-werkprotocol skill (a367d3d)
- Slice 2b: 4-ingangen-beginscherm + chips (b5a6e33, cab0988)
- Slice 2b UX-fixes: z-index blokkade (94aa12e), actieknop bovenaan (ef68c40),
  zoekterm reset na aanvinken (a4979fa)
- Slice 5: detail-paneel set-acties — buren erbij + context-componenten (0b018bd)
- Slice 6: cytoscape-dagre dependency verwijderd (776ab38)
- Scope-balk fix: filtert org/gg-nodes in subgraaf-modus (097d1e9)
- Generieke re-layout watcher op getekendeNodes-compositie (1019d8f)
- PRODUCTVISIE.md toegevoegd aan projectroot (3fc3414)
- ADR-025/026 nadere besluiten + ADR-030 besloten + ADR-035 Signalering (ac4afb7)
- root-OPVOLGPUNTEN.md verwijderd — docs/OPVOLGPUNTEN.md is enige bron (0e16999)

**Nieuw besloten, nog te bouwen (prioriteitsvolgorde):**
1. ADR-035 Signalering registratiegaten
2. ADR-025 "Bekijk op kaart"-knop (praatplaat ego-view)
3. ADR-026 ArchiMate typering verplicht in componenttype-formulier
4. ADR-030 Contract coverage per-band
5. Klaarverklaring-blok op ComponentDetail (triviale gap, ADR-027 compleet)
6. Interactieve legenda als type-filter

**Landschapskaart uitgesteld na live testing:**
- Scope-balk gedrag in subgraaf-modus (bewust uitgesteld)
- Impact-modus semantiek op een set (bewust uitgesteld)
- Swimlane implementatie (ADR-034, geparkeerd)
- Saved views als permanente hoofdingang (Fase D)
- "Zoek-erop-dan-toon-het" principe

**Nieuw strategisch thema (parked):**
- Export/import/rapportage — scope en fasering apart te bepalen

### Stand V023 (sessie-afsluiting LI022, 2026-06-27)

Build **V022 → V023**. LI022 = Landschapskaart Fase B (set-gestuurd) + hygiëne/rename.

**Geland/afgerond in LI022:**
- **Fase B slice 0+1 — set-gestuurd laadpad** (`10bb35e`): de kaart opent leeg; niet-lege set →
  `POST /landschapskaart/subgraaf`; bewuste "Toon hele landschap" met "X van N"-teller; "Begin opnieuw"
  = harde reset. `api.landschapskaart.subgraaf` bedraad. **AFGEROND.**
- **Fase B slice 2a — context-routes naar componenten** (`509e9ca`): `GET /contracten/{id}/componenten`
  (incl. kale componenten; engine-ontkoppeld) + `GET /gebruikersgroepen/contexten(/componenten)`
  (distinct (org, afdeling)-picker + nullable-veilige context→componenten). **AFGEROND.**
- **Stale live-DB-tests herijkt op de verrijkte seed** (`d6cd59f`); **skill-laag hernoemd
  complidata→likara + nieuwe `likara-werkprotocol`** (`8b8a8b2`); **Laag-2 identifier-rename geborgd**
  (`6043094`); **generators-skill-paden meegerenamed** (deze afsluiting — gen_build/gen_sessiestart
  verwezen nog naar `.claude/skills/complidata/`).
- **Oude slice-3 (Typen server-side) + slice-4 (Bladeren) worden door slice 2b geabsorbeerd** — niet
  apart gebouwd (zie NEXT_SESSION voor het slice-2b-ontwerp + de herziene slice-planning).

**Nieuw klein/optioneel vervolgpunt:**
- `GET /gebruikersgroepen/contexten` is **bewust ongepagineerd** (begrensde distinct-afgeleide lijst, met
  zoek + telling). Keyset alleen nodig als een tenant extreem veel distinct (organisatie, afdeling)-
  contexten krijgt → dan een kleine eigen slice (keyset over een 2-nullable-koloms-distinct).

### Nieuwe bouwpunten besloten LI023

**ADR-025 (Praatplaat) — BESLOTEN, bouw gepland:**
"Bekijk op kaart"-knop op alle componentdetailpagina's → vooringestelde
ego-view op de Landschapskaart. Koppelingenkaart visuele weergave vervalt.
Read-API per component + frontend-integratie.

**ADR-026 (ArchiMate typering beheerbaar) — BESLOTEN, bouw gepland:**
Drie verplichte typeringsvelden in componenttype-formulier. Gesloten lijsten
(code-constanten). Seed compliant maken bij de bouw-slice.

**ADR-030 (Contract coverage) — BESLOTEN, bouw gepland:**
Per-band dekking naast contract-brede dekking (Optie B).

**ADR-035 (Signalering registratiegaten) — BESLOTEN, bouw gepland:**
Zie ADR-035 (hernummerd; ADR-031 was reeds vergeven). Coherent Signalering-scherm
(absorbeert Plaatsingssignalen). 10 signaaltypen, 2 niveaus, badges op entiteiten
+ centraal overzicht.

**Klaarverklaring op ComponentDetail — BESLOTEN, bouw gepland:**
MigratiegereedheidSectie-blok + knop plaatsen op ComponentDetail.
ADR-027 is compleet; triviale implementatiegap.

**Interactieve legenda als type-filter — BESLOTEN, bouw gepland:**
Klik op type in legenda → filtert graaf op dat type.

**Export/import/rapportage — NIEUW STRATEGISCH THEMA (parked):**
Breder thema dan alleen praatplaat-export. Scope en fasering apart te bepalen.

### Subgraaf-semantiek: filter/scope/impact/swimlane op een opgebouwde set (eigen ontwerpslice)

Fase B (LI022) maakt de kaart set-gestuurd. De rijke verkenmechaniek
(impact-ringen, scope-balk, swimlane, ego/impact-modus) is gedefinieerd óver de
volledige graaf en is in Fase B verhuisd naar de "hele landschap"-modus (waar de
volledige graaf nog bestaat). Wat deze mechaniek betekent op een **opgebouwde set
(subgraaf = set + 1-hop)** is bewust nog niet ontworpen — een set ís al focus, dus
mogelijk is een deel ervan daar overbodig of anders gedefinieerd.

Te beslissen in een eigen ontwerpslice (rond het interactiemodel, Fase B slice 5):
welke van filter/scope/impact/swimlane zinvol zijn op een subgraaf, en hoe ze zich
daar gedragen. Pas dán de set-tests inhoudelijk herijken (nu dekken die alleen de
bedrading). Geen workaround vooruit; structureel definiëren wanneer de beslissing valt.

### Stand V022 (sessie-afsluiting LI021, 2026-06-25)

Build **V022**. LI021 = test-hygiëne + seed-verrijking + Landschapskaart-vertrekpunt **fase A** (achterkant-kern).

**Geland in LI021:**
- **Test-hygiëne** (`0c4371b`) — twee live-DB-tests zelf-opruimend via `finally`
  (`test_component_contract_op_niet_applicatie_component`, `test_score_write_driver_plus_afgeleide_delen_correlatie`);
  cleanup draait ook bij falen → geen residu-lek meer (vervuilings-cirkel gebroken).
- **Seed-verrijking** (`ae905c1`, data-only/idempotent in `_seed_bvowb_scenario`): infrastructuur
  (technology-laag: Shared DB-server/fileshare/extern SaaS-platform) + draait-op-relaties;
  component-samenstelling (Burgerzaken-suite → Aangiften/Reisdocumenten/Verkiezingen); bewuste
  scope-gaten (Archiefbeheer zonder eigenaar; Klantportaal uitsluitend organisatieloos gebruikt).
- **Kaart-vertrekpunt fase A** (`fec08d5`, additief/read-only): POST `/landschapskaart/subgraaf`
  (set-scoped S+1-hop; `component_ids=None` = volledige graaf, back-compat); leverancier-filter op
  `/componenten` (afgeleide EXISTS, beide paden); eigenaar-edge "is eigendom van" (context, **niet**
  in `IMPACT_RINGEN`).
- **Geparkeerd "scopebalk-tekent-organisaties"-spoor is AFGEDEKT** door de eigenaar-edge (zelfde
  "is eigendom van"-projectie) — geen apart vervolgpunt meer nodig.

**Vervolg LI022 (in deze volgorde, leunt op elkaar):**
1. **Reset + seed-herijking** — de 8 pre-existing live-DB-failures groen krijgen in CC's omgeving:
   `docker compose down -v` → reseed (**handmatige dev-seed!** — `docker compose exec <api> python dev_seed_testdata.py`)
   + de stale tests herijken op `_seed_bvowb_scenario` (ze verwachten dode-seed-rijen — `GeoWorks
   Licentieovereenkomst`/`Oracle FIN-DB`/3 `client_software`-vragen — die de verrijkte seed niet maakt).
2. **Kaart-vertrekpunt fase B** — leeg openen + zoek-vertrekpunt via `/componenten`
   (naam/type/laag/hosting/eigenaar/leverancier) → set-opbouw → POST subgraaf, met accumulerende
   sub-graaf-cache. **Besloten keuzes:** selectie = alléén component-ids (org/leverancier = criterium +
   context); **cache weggooien** bij "begin opnieuw"; **1-hop norm, dieper alleen via doorklikken**;
   endpoint = POST.
3. **Fase C** — defaults omdraaien (leeg openen consistent: scopebalk niets-aan→alles + startscherm
   geen-views→hele model wég) + "zoek-erop-dan-toon-het" (auto-ring-activering op zoek, handmatig wint).
4. **Fase D** — opgeslagen views permanent náást het zoekveld (hoofdingang).

**8 pre-existing live-DB-failures — seed-drift (NIET als opgelost markeren):**
architectuur_f2, audit_capture, 4× component_fase_b_cd052, lifecycle_pertype, vraagbeheer. De
`finally`-hygiëne (`0c4371b`) brak de residu-cirkel, maar de 8 blijven rood door **seed-drift** (tests
asserteren op rijen die `_seed_bvowb_scenario` niet maakt). Opgelost door vervolgstap 1. Zie
`docs/TST-V022-Validatierapport.md`.

**Overige open punten (ongewijzigd):** ADR-034 open subknopen; interactieve legenda als type-filter;
ADR-030 contract-dekking; ADR-029 Fase 5; klaarverklaring-blok op ComponentDetail; signalerings-ADR;
dode-code-opschoning (frontend/backend); cytoscape-dagre opruimen.

---

### Stand V021 (sessie-afsluiting LI020, 2026-06-25)

Build **V021**. LI020 = ADR-033 (volledig), gebruikersbeheer-acties (ADR-029 Fase 2b),
en de Landschapskaart-reeks.

**Geland in LI020:**
- **ADR-033 (volledig)** — adaptieve Landschapskaart + Impact-verkenner (graph op canvas),
  samenstelling-edge, opgeslagen & deelbare views (entiteit + rechten + API + voorkant + startscherm).
- **Gebruikersbeheer-acties (ADR-029 Fase 2b, achter + voorkant)** — wachtwoord opnieuw instellen,
  rol wijzigen, in-/uitschakelen (sessie-afkap), gegevens corrigeren; self-lockout-guards; expliciete audit; beheer-paneel.
- **Landschapskaart-reeks** (frontend, engine onaangeroerd): selectie-highlight (enkelklik = incidente
  lijnen oranje; dubbelklik = dieper); organisatiestructuur-ring (persoon-met-rol → afdeling → organisatie,
  context, buiten `IMPACT_RINGEN`); toestand-geschiedenis (terug/vooruit) + hang-fix + auto-centreren;
  vorm-per-type + uitklapbare legenda; organisatie-scopebalk slice 1 (backend read-projectie) + slice 2 (balk).
- **ADR-034 (swimlane-herwrite)** — staat als **Voorstel** (nog niet gebouwd).

**Eerste blok LI021 (in volgorde, leunt op elkaar):**
1. **Test-hygiëne-fix** — twee lekkende live-DB-tests zelf-opruimend maken (`finally`):
   `test_component_contract_op_niet_applicatie_component` (test_component_fase_b_cd052) en
   `test_score_write_driver_plus_afgeleide_delen_correlatie` (test_audit_capture_live). Breekt de
   vervuilings-cirkel → maakt de 8 falers vermoedelijk groen.
2. **Schone reset** — `docker compose down -v` → reseed → 32 artefacten (`CD052-db-*`/`AUDIT-SRV-*`) weg.
3. **Gerichte seed-verrijking** (geen "meer data" — drie ontbrekende variaties):
   - **infrastructuur** (technology-laag) onder componenten → barrel-vorm + "draait-op"/assignment-impactrelatie zichtbaar;
   - **component-samenstelling** (component↔component, onderdeel-van) → samenstelling-ring + "onderdeel-van"-impactrelatie zichtbaar;
   - **bewuste scope-gaten** — ≥1 component zonder eigenaar + ≥1 app uitsluitend door de organisatieloze "Burgers"-groep geserved → scopebalk-gap-tellers aantoonbaar.

**8 pre-existing live-DB-failures — oorzaak nu bekend (NIET als opgelost markeren):**
Test-residu van niet-zelf-opruimende live-DB-tests (inline cleanup i.p.v. `finally`) → 32 wees-componenten
(`CD052-db-*`/`AUDIT-SRV-*`) vervuilen lijst-/sort-asserts van ándere tests → vicieuze cirkel (verklaart
"reseed lost het op"). Structureel opgelost door LI021-startpunt 1 + reseed. Zie `docs/TST-V021-Validatierapport.md`.

**Overige open punten (ongewijzigd):** ADR-034 open subknopen; interactieve legenda als type-filter
(besproken vervolg); ADR-030 contract-dekking; ADR-029 Fase 5; klaarverklaring-blok op ComponentDetail;
signalerings-ADR; dode-code-opschoning (frontend/backend); cytoscape-dagre opruimen.

**Parkeer-items (ongemoeid):** gebruikersbeheer-vervolg (self-service / MFA / AVG-anonimisering /
inactieve accounts); contract-leverancier verbreding; soort-catalogus; per-tenant catalogus-zichtbaarheid;
tenant-eigen partijsoort; friendly STATE_ONGELDIG; child-section-staleness.

---

### Stand V020 (sessie-afsluiting LI019, 2026-06-24)

Build **V020**. LI019 = Landschapskaart-filters/UI, auditlog-UI, leverancier via contract-keten,
radiaal-layout + swimlane geparkeerd.

**Nieuw in LI019:**
- **ADR-034 Swimlane herwrite** — pure HTML/CSS div-lanes + SVG-overlay voor edges (NIET Cytoscape
  compound-nodes). Lane-drag, edges tussen lanes, nodes aanklikbaar.
- **ADR-033 Impact-verkenner bouwen** — besloten, klaar voor bouw (zie `ADR-033_Impact_verkenner.md`).
- **Codebase cleanup** (inventarisatie klaar) — frontend 11 items + backend 28 items (zie
  LI019-cleanup-inventarisatie rapport).
- **8 pre-existing live-test failures skip-robuust maken** — seed-afhankelijk.
- **dagre dependency opruimen** — ongebruikt na de radiaal-overstap.
- **Per-tenant catalog optie-zichtbaarheid** (ADR-026 edge case) — geparkeerd.
- **Tenant-eigen partijsoort** — geparkeerd.
- **Contract-leverancier verbreding** — `aard=externe_partij`-constraint verbreden.
- **Signalerings-ADR registratiegaten** — object zonder rol, lege eigenaar-organisatie, contract
  zonder leverancier, lege eigenaar-blokkadelijst. **→ opgenomen in ADR-035 (Signalering registratiegaten), besloten LI023.**
- **Browser-verificatie radiaal auto-centrering na dubbelklik** (commit 0cf8559).

### Stand V018 (sessie-afsluiting DC017, 2026-06-22)

Build **V018**. DC017 = LIKARA-rebranding (Laag 1) + canoniek BvoWB-seed + Keycloak login-theme +
dev-gebruikers + kaart-edge-groepering/master-detail (ADR-023a Fase 3+4).

**Nieuw (DC017):**
1. **LIKARA Laag 2 rename** — technische identifiers: realm-ID `complidata` → `likara`,
   container-namen `cd-*`, DB-rol `lk_app`, image `complidata-api:local`, ENV `KEYCLOAK_REALM`,
   clientId `complidata-api`/`complidata-ui`. Bewuste keuze: **eigen sprint DC018** (raakt compose,
   .env, init-db, conftest, RLS-rol → reseed vereist).
2. **Reseed-verificatie (`down -v`)** verplicht na de Laag 2 rename.
3. **Dode seed-functies opruimen** in `dev_seed_testdata.py` (`_seed_applicatie`,
   `seed_landschapskaart_demo`, `_seed_koppelingen` e.a. — ongebruikt sinds `_seed_bvowb_scenario`).
4. **Child-secties stale bij detail→detail-hop** — child-secties in ComponentDetail/ApplicatieDetail
   laden zelf in `onMounted` zonder `:key`; bij een hop binnen hetzelfde type kunnen ze stale zijn.
5. **soort-catalogus uitbreiden** — "Dienstenprovider" en "Samenwerkende gemeente" bestaan niet als
   partijsoort → BvoWB + gemeenten krijgen nu `soort=None` in de seed; catalogus kan uitgebreid worden.
6. **STATE_ONGELDIG-foutmelding** — ruwe JSON tonen → vriendelijke "sessie verlopen"-pagina.
7. **Stale root `OPVOLGPUNTEN.md`** (staat nog op V012) — consolideren met `docs/OPVOLGPUNTEN.md` of verwijderen.

**Herbevestigd (blijft open):** ADR-029 Fase 5 (`gereedmeld_recht`), ADR-023 Fase F-rest (E-8 +
RBAC/audit), landschapskaart server-side ego-subgraaf, objecthistorie-diff id→naam-resolutie,
OP-30 `test_auth_pkce` Secure-cookie env-test (omgevingsgebonden).

### Stand V017 (sessie-afsluiting DC016, 2026-06-22)

Build **V017**, migratie head **`0040`**. Tests: **859** backend + **534** frontend groen +
`test:css-build` groen. Deze sessie: UI-standaardisatie (knop/tab/interactie-borging),
api-client-filterconventie, Landschapskaart popups/fullscreen, ADR-023a meervoudige
flow-koppelingen Fase 1+2.

**Nieuwe/geactualiseerde opvolgpunten (DC016)**:
- **ADR-023a Fase 3** (read/contract, geen migratie) — kaart-edge-groepering: meerdere flows per
  `(bron,doel)` → één lijn + **telling vanaf 2**; popup-fetch op het **ongeordende paar**, gegroepeerd
  naar richting (uitgaand bij bron / inkomend bij doel).
- **ADR-023a Fase 4** (frontend) — naam-veld (verplicht) + overrulebare **KOPPELING_DUBBEL**-
  waarschuwingsdialoog; `KoppelingSectie` naam-kolom (sorteerbaar); kaart-telling vanaf 2; en de
  popup ombouwen naar **universeel master-detail** (links sorteerbare interface-lijst op naam/richting,
  pijl-buiten-groen=uitgaand / pijl-binnen-rood=inkomend met **pijlrichting als hoofdsignaal**; rechts
  detail; eerste regel geselecteerd; ook bij n=1). Vervangt de enkelvoudige popup uit `8de3451`.
- **NIEUW SEED-TRAJECT (groot)** — volledige testdataset opnieuw opzetten zodat hij het **hele
  LIKARA-landschap** representeert en alle functionaliteit raakt (besloten DC016). Moet **flow-namen**
  + **meervoudige benoemde koppelingen** bevatten. Volgt ná de ADR-023a-koppeling-keten.
- **Reseed gebroken op flow-namen** — `dev_seed_testdata._seed_koppelingen` maakt flows **zonder naam**
  → faalt onder de naam-eis (ADR-023a Fase 2). Wordt opgelost in het nieuwe seed-traject; tot dan is
  een reseed van de koppelingen gebroken (testdata-kwestie, géén migratievraagstuk).
- **`test:css-build` nog niet in CI** — los script; een CI-stap of pre-push-hook is de logische
  vervolgstap (aparte slice).
- **ADR-030 contract-dekking per contract↔component-band** (voorstel, `3e28481`) — dekking als
  per-band-kenmerk op de association i.p.v. uitsluitend contract-breed. Centrale open subknoop:
  contract-brede dekking **behouden NAAST** per-band of **vervangen**. Op te pakken ná de
  koppeling-keten (n≥2: de koppeling-uitbreiding als blauwdruk). Read-only verkenning is gedaan.

### Stand V016 (sessie-afsluiting DC015, 2026-06-20)

Build **V016**, migratie head **`0038`**. Tests: **856** backend + **500** frontend groen
(1 pre-existing env-auth-test, OP-30). Deze sessie: ADR-029 (gebruikersbeheer als primaire ingang)
grotendeels gerealiseerd + objecthistorie ('i'-knop).

**AF deze sessie (DC015)**:
- Drie kleine opvolgpunten (DC014): dode `<dl>`-rijen op ApplicatieDetail + ComponentDetail
  opgeruimd; `MigratiegereedheidSectie` ook op ComponentDetail; CLAUDE.md interactie-secties
  geconsolideerd.
- **ADR-029 herschreven** (gebruikersbeheer als primaire ingang; LIKARA als bron van waarheid).
- **ADR-029 Fase 2** — backend gebruikersaanmaak: `gebruiker_persoon`-koppeltabel (migratie 0037),
  Keycloak Admin API-provisioning via dedicated service-account `likara-user-provisioning`
  (least-privilege manage-users/view-users), server-gegenereerd eenmalig wachtwoord,
  orphan-cleanup. Live-geverifieerd na realm-herimport.
- **ADR-029 Fase 4** — gebruikersbeheer-scherm (beheerder-only nav + lijst + aanmaak-dialog +
  eenmalig-wachtwoord-weergave).
- **ADR-029 Fase 3b** — sub-stempeling: `verklaard_door_sub` (klaarverklaring, migratie 0038) +
  plateau `bevestigd_door` {sub,email}; gedeelde `actor_resolutie`-helper (sub→naam, e-mail-fallback);
  read-side `verklaard_door_naam`/`bevestigd_door_naam`. ADR-027 wijzigingshistorie bijgewerkt.
- **ADR-029 Fase 3a** — audit-view + `actor_naam`-batchverrijking + actie-filter + naam-filter
  (naam→sub).
- **Objecthistorie** — `GET /objecthistorie/{type}/{id}` (toegang-volgt-object, geen AUDITLOG-gate)
  + herbruikbaar `ObjectHistoriePaneel` ('i'-knop) op 8 detailschermen, per-record diff met
  NL-veldlabels, "Meer laden".
- **Dev-seed-fix**: `dev_seed_testdata.py` crashte bij reseed op de met migratie 0034 verwijderde
  `eigenaar_naam`/`leverancier`-kwargs (pre-existing DC015-vondst).

**Volgende prioriteiten (DC015 → DC016)**:
1. **ADR-029 Fase 5** — `gereedmeld_recht` (per-type persoon × componenttype) + per-type check in
   de klaarverklaring-service. **Laatste open ADR-029-fase.**
2. **ADR-023 Fase F-rest** — checklist-consistentiecheck technische plaatsing (E-8) + resterende
   RBAC/audit nieuwe entiteiten.
3. **Landschapskaart server-side ego-subgraaf** (`?center=<id>&diepte=1|2`).
4. **LIKARA codebase-rename** (geparkeerd, DC013).

**Nieuwe opvolgpunten (DC015)**:
- **Dode backend-proxy-properties** `Applicatie.eigenaar_naam` / `.leverancier` (`models.py:382/386`)
  lezen een sinds migratie 0034 niet-bestaande kolom — inert (niet in Read-schema's), opruimbaar in
  een aparte backend-taak.
- **Naam-filter audit-view** eventueel als ZoekSelect-op-personen (nu vrije-tekst; bewuste
  search-semantiek — alleen als de praktijk een pick verkiest).
- **id→naam-resolutie in objecthistorie-diff** (`*_id`-velden tonen nu de gelogde id-waarde;
  per-veld id→naam zou een lookup per type vergen).

### Stand V014 (sessie-afsluiting DC013, 2026-06-19)

Build **V014**, migratie head **`0034`**.
Tests: **810** backend + **440** frontend groen (52 files).

**AF deze sessie (DC013)**:
- complidata-domeinmodel skill aangemaakt (CC + claude.ai)
- ADR-024 volledig geland: contract-leverancier verbreed
  (organisatie/afdeling/externe_partij; persoon geblokkeerd);
  roltoewijzing toevoegbaar vanuit partij-detail;
  ADR-024-document bijgewerkt naar werkelijke stand;
  functietitel (persoon-only, migratie 0033);
  eigenaar_naam/leverancier vrije tekst verwijderd (migratie 0034);
  9 beheerrollen (Account Manager + Service Delivery Manager)
- ADR-025 volledig geland (Landschapskaart v4, Cytoscape.js):
  Ego/Impact/Geheel model; zoeken + 4 filters; actieve set;
  node-detail + "Open applicatie →"; blokkade-icoon;
  lifecycle-kleuren; koppelingsdetails (protocol/richting) op edges;
  migratieplaatsing (plateau/dispositie) in detail-paneel;
  diepte-toggle; Koppelingenkaart vervangen; ADR-025-document bijgewerkt
- ZoekSelect-standaard vastgelegd in complidata-frontend skill
- PartijFormulier organisatie-/afdelingskiezer naar ZoekSelect
- LIKARA productnaam besloten (Logische ICT Kaart Afhankelijkheden Relaties Analyse)
- ADR-028 voorstel geland (componentrol + BIV-classificatie, geparkeerd na ADR-027)
- complidata-domeinmodel/-frontend/-ux skills bijgewerkt (DC013-patronen)

**Volgende prioriteiten (DC013 → DC014)**:

1. **ADR-027 — Component-klaarverklaring. ✅ COMPLEET** (DC014): slice 1 model
   (`component_klaarverklaring`, migratie 0036, niet-scorend, herroepbaar, engine-gescheiden) →
   slice 2 UI (Migratiegereedheid-blok + klaar verklaren/heropenen met reden op ApplicatieDetail,
   commit 979a646) → slice 3 dashboard (tellingen `klaar_verklaard` + `klaar_met_afwijking` +
   lijstfilter `klaarverklaring=klaar`/`afwijking=1`, commit 6ffd7e6). Per-categorie + werkverdeling
   bewust vervallen. **Restpunten (nieuw, zie hieronder):** klaarverklaring-blok ook op ComponentDetail.

2. **ADR-029 — Gebruiker-partij-koppeling + per-type gereedmeld-autorisatie** (geparkeerd voorstel,
   fundament voor eerste implementatie). Brug Keycloak-login ↔ persoon-partij (ADR-024) + per-type
   gereedmeld-recht aan de persoon + apart beheerder-autorisatierecht (gescheiden van PARTIJ) +
   gescheiden verantwoordingsketen. Verfijnt het grove ADR-027-recht (per-persoon/per-type,
   preventief); ADR-027 hangt er niet op. Zie docs/adr/ADR-029_Gebruiker_partij_autorisatie_voorstel.md.

3. **ADR-023 Fase F**: checklist-consistentiecheck technische plaatsing (E-8, deferred),
   platform-beheer relatie-kenmerk-catalogus, RBAC/audit nieuwe entiteiten.

4. **Landschapskaart server-side ego-subgraaf** (aparte slice): `?center=<id>&diepte=1|2`
   voor een gereduceerde graaf i.p.v. de volledige tenant-graaf. Vereist nieuw endpoint-contract.

5. **ADR-025 overige roadmap**: vervangingsrelatie, export PNG/PDF, pad-inzicht (kortste route
   A→B), clustering op domein.

**Nieuwe opvolgpunten (DC014)**:
- **Klaarverklaring-blok ook op ComponentDetail** (niet-applicatie checklist-dragende
  componenten). Het model is component-generiek; alleen ApplicatieDetail heeft nu de
  Migratiegereedheid-UI. Triviale follow-up: het herbruikbare `MigratiegereedheidSectie`-blok
  + de knop op ComponentDetail plaatsen.
- **Dode `<dl>`-rijen op ApplicatieDetail Overzicht** opruimen: "Eigenaar (naam)" + "Leverancier"
  tonen sinds migratie 0034 (velden uit schema/form verwijderd) altijd "—".
- **CLAUDE.md interactie-secties consolideren**: deels overlappende blokken (Werkprotocol +
  "Werkwijze CC + claude.ai"); samenvoegen tot één gezaghebbende bron.

**Nog open uit eerdere sessies (doorgeschoven, ongewijzigd geldig)**:
- **Signalerings-ADR / registratiegaten ("bolletjes")** — (1) object zonder toegewezen rol;
  (2) lege eigenaar-organisatie/gebruikersgroep-organisatie (geparkeerd); (3) contract zonder
  leverancier (indicator + statusfilter + dashboard-ratio); (4) lege 'Eigenaar'-kolom blokkadelijst.
  Generalisatie-discipline n≥2; read-only, geen engine-poort.
  **→ opgenomen in ADR-035 (Signalering registratiegaten), besloten LI023.**
- **Architectuuroverzicht-sortering volgt codewaarde, niet NL-label** — geaccepteerd randgeval (B2/B6-a).
- Tenant-eigen partijsoort (geparkeerd); per-tenant zichtbaarheid catalogus-opties; OP-29 label-rename;
  `SUBTYPE_HEEFT_DATA` 422↔409-heroverweging.

---

### Stand V013 (sessie-afsluiting DC012, 2026-06-18) — ADR-024-vervolg + UX-doorlichting

Build **V013**, migratie head **`0032`**. Tests: **799** backend + **429** frontend groen
(1 pre-existing env-auth-test, OP-30). Deze sessie: rol-toewijzing (eigen tabel), volledige
UX-doorlichting gedicht, migratielaag-CRUD compleet, organisatie overal als verwijzing naar
het partijenregister.

**AF deze sessie (DC012)**: UX-doorlichting **volledig gedicht** (A1–A4, B1–B6); **rol-toewijzing**
(`roltoewijzing`, slice 2b — eigen tabel bij tegengestelde uniciteit); **migratielaag-CRUD compleet**
(plateau/werkpakket/deliverable/gap beheerbaar in de UI); **`complidata-ux`-skill geland**;
architectuuroverzicht server-side sorteerbaar; B6 organisatie-uit-partijenregister (gebruikersgroep +
applicatie/component).

*(De DC012→DC013-prioriteiten zijn afgehandeld of doorgeschoven naar het V014-blok hierboven —
ADR-024-document is bijgewerkt; signalerings-ADR + sorteer-randgeval staan nu onder "Nog open uit
eerdere sessies" bij V014; ADR-025 is geland.)*

### Stand V008 (sessie-afsluiting 2026-06-13) — ADR-022 volledig afgerond

Build **V008**, migratie head **`0009`** (3 ADR-022-migraties: `0007` profiel, `0008` tenant-vragenset,
`0009` `checklist_dragend`-vlag). Tests: **567** module + **72** platform (1 pre-existing env-auth-test,
zie OP-30) + **255** frontend groen. ADR-022 (Fase A–F + W1) compleet: een componenttype kan een
eigen, **tenant-eigen** checklist dragen — profiel, scoring, lifecycle, toestand-gebaseerde type-lock,
per-type readiness — losgekoppeld van `applicatie`.

**Volgende prioriteiten**:
1. **ADR-006 — hash-chained audit-trail (#17)**: volgende grote prioriteit. ADR-022 ging er bewust
   vóór, zodat de audit-trail het definitieve besturingsmodel logt (append-only, nooit verwijderen).
2. **Tenant-onboarding (#16)**: automatische **baseline-kopie** van de vragenset bij `POST /tenants`
   (de #16-knip uit W1) — vandaag seedt alléén `dev_seed` per tenant; de platform-onboarding-hook
   ontbreekt. De seed schrijft tenant-scoped data → `lk_app` met de nieuwe tenant-RLS-context.

**Bewust vastgelegde foutcode-keuzes (ADR-022)**: `SUBTYPE_HEEFT_DATA` = HTTP **422** (Fase C
type-lock, via `OngeldigeRegistratie`; heroverweging naar 409 is open); checklistvraag type-mismatch
= HTTP **404** (`NietGevonden`, Fase B/E; OP-6-stijl, geen nieuwe code).

**Afgehandeld deze sessie**: lokale CC-settings (`settings.local.json`) nu **durable in-repo**
genegeerd via `.claude/.gitignore` (`*.org.json`, `.DS_Store`) — voorheen enkel via de globale
`~/.config/git/ignore`; het stray-bestand `settings.local.json.org.json` is opgeruimd.

### OP-29 — Impact-/graaf-lens veldlabel `aantal_applicaties` (naamsmell sinds Fase E) — OPEN (nice-to-have)

`component_service.impact_analyse` / `schemas.component.ImpactSamenvatting.aantal_applicaties` telt
sinds ADR-022 Fase E **alle** profiel-dragende geraakte componenten, niet alleen `applicatie`. De
lens is functioneel correct (profiel-generiek sinds Fase A); alleen het veldlabel is misleidend.
Verheldering = rename (bv. `aantal_beoordeeld`) — bewust buiten Fase E/F gehouden.

### OP-30 — `test_auth_pkce` Secure-cookie env-test faalt omgevingsgebonden — OPEN

`test_auth_pkce.py::test_callback_succes_zet_cd_session_cookie` faalt op de Secure-cookievlag in
test/dev; faalt identiek op een schone `HEAD` (los van ADR-022). Te onderzoeken: de Secure-cookie-
assertie omgevings-onafhankelijk maken (bv. `cookie_secure` expliciet in de testconfig forceren).

### OP-3 — Refresh-token-subsysteem (uit P2) — OPEN

P2 zet bewust geen refresh-token; sessie verloopt na 15 min en vereist
opnieuw inloggen. Bouwen: `/auth/refresh`, veilige server-side opslag van de
refresh-token gekoppeld aan een sessie-id, rotatie/intrekking, koppeling aan
de 8-uurs refresh-grens (CLAUDE.md). Geen token client-leesbaar.

### OP-4 — RP-initiated logout via Keycloak (uit P2) — AFGEROND (geverifieerd CD038)

Al geïmplementeerd (CD008/CD010): `POST /auth/logout` trekt het Redis-refresh-handle in
(haalt `id_token_hint`), wist `cd_session`+`cd_refresh`, en geeft de Keycloak
end-session-URL terug; de store (`auth.logout()`) navigeert ernaartoe zodat ook de
SSO-sessie eindigt. Werkt identiek voor tenant- én platform-accounts (gedeelde
login-/logout-infra). Gedekt door `logout.test.js` (redirect naar end-session-URL +
`/login`-fallback). In CD038 is de stale `AppLayout.vue`-comment (die nog "buiten scope"
beweerde) rechtgezet.

### OP-6 — Resource-ownership binnen tenant (P5/ADR-010) — AFGEDEKT (fase 1, P5)

Afgedekt voor fase 1 — tenant-scoped record-resolutie (kruis-tenant → 404) +
rol + RLS volstaan; per-gebruiker-eigenaarschap niet nodig in fase 1
(collaboratief register, ADR-009).

Geïmplementeerd in P5 (Applicatie-CRUD, referentie voor de overige entiteiten):
record-resolutie strikt binnen de tenant-sessie (RLS + expliciete
`tenant_id`-filter); een id buiten de tenant is niet vindbaar ⇒ HTTP 404
`NIET_GEVONDEN` (geen 403, geen onderscheid "bestaat niet" vs "andere tenant",
dus geen lek). Binnen de tenant geldt rol-gebaseerde autorisatie via
`vereist_permissie`; elke Medewerker/Beheerder mag elk record in de eigen tenant
bewerken. Fijnmazig per-gebruiker-eigenaarschap is bewust uitgesteld en pas te
heroverwegen als een toekomstige eis daarom vraagt.

### OP-7 — 401 en 403 in hetzelfde foutformaat (uit P3) — AFGEROND (geverifieerd CD037)

401 is al canoniek `{"fout":{...}}` (CD005): `NietGeauthenticeerd` +
`niet_geauthenticeerd_handler`, en `auth.py`-`_fout` levert hetzelfde envelope.
Live bevestigd op tenant-endpoint, `/auth/me`, `/auth/platform/me` en bij decode-fout;
de frontend (`api.js`) keyt op de **statuscode** en leest `body.fout.code`. 422 blijft
bewust native (ADR-014). In CD037 zijn nog twee stale route-docstrings
(`applicatie.py`/`dashboard.py`) rechtgezet en is een test toegevoegd die het
canonieke 401-envelope op een guarded tenant-route vastlegt.

### OP-13 — Platform-tabel-grants Platforminstellingen/Platformmetadata — OPEN

Het platform-permissiedomein (ADR-012) kent `Platforminstellingen` en
`Platformmetadata`, maar alleen de `tenant`-tabel bestaat. Bij het bouwen van
die endpoints: tabellen + migratie + `GRANT … TO lk_platform` /
`REVOKE … FROM lk_app` (zelfde patroon als `tenant`).

### OP-14 — Dev-credentials vervangen vóór productie — OPEN

`changeme_dev` staat als dev-default in realm (client-secret + testgebruikers)
en DB-rollen (lk_app/lk_platform/lk_admin via `POSTGRES_PASSWORD`). Vóór
productie vervangen door secrets; testgebruikers verwijderen of scheiden van
productie-realm.

### OP-16 — `tenantSlug`-getter leest verkeerd veld — AFGEROND (geverifieerd CD036)

De getter is al gecorrigeerd: `frontend/src/store/auth.js` kent **geen** `tenantSlug`
meer — de getter heet `tenantId` en leest `user.tenant_id` (de werkelijke `/auth/me`-
payload). `useTheme` gebruikt `auth.tenantId`; gedekt door `tenantId.test.js`
(`OP-16: tenantId-getter leest tenant_id`). De oorspronkelijke "leest verkeerd veld"-
bug bestaat niet meer (gefixt in een eerdere sessie, hier tegen de code bevestigd).

**Resterende testrand (CD019, minor)**: na het afhandelen van de `useTheme`-promise (`.catch` in
`tenantId.test.js`) resteert nog één pre-existing happy-dom `DOMException` (interne
resource-`fetch` van de thema-stylesheet, afgebroken bij window-teardown) op stderr —
telt niet als test-fout. Op te ruimen zodra `useTheme` echte call-sites + een
default-thema-fallback krijgt en de test wordt herontworpen met een expliciete
`onerror`-trigger i.p.v. happy-dom's toevallige `fetch`.

### OP-18 — Stale V001-docs (IMPLEMENTATIEPLAN / SESSIE_BRIEFING) — AFGEROND (CD018)

`IMPLEMENTATIEPLAN.md` is voorzien van een *HISTORISCH — V001-snapshot*-banner die naar
de live bronnen verwijst (CD013). De stale `SESSIE_BRIEFING.md`-bouwstatus is opgelost
in **CD018**: `update_claude_bouwstatus` draait nu vóór de generators (i.p.v. ná de
briefing-generatie), zodat `gen_sessie_briefing.py` het nieuwe `BOUWSTATUS`-blok leest.
Geborgd met `backend/tests/test_gen_build_volgorde.py` (functionele write-then-read +
statische volgorde-guard via `inspect.getsource`).

### OP-19 — Frontend bundle >500 kB — AFGEROND/gemitigeerd (geverifieerd CD038-sweep)

`vite build`: géén ">500 kB"-waarschuwing meer; de grootste chunk is `column-*.js`
(PrimeVue DataTable) op **384 kB** (<500 kB), geïsoleerd in een eigen chunk die alleen met
`ApplicatieDetail` laadt. **6 route-level lazy-imports** (CD012) verkleinen de initiële bundle
(`index` ≈ 164 kB). Het oorspronkelijke symptoom doet zich niet meer voor; verdere reductie is
optioneel (geen verplichting).

### OP-21 — Eigenaar-filter als distinct-dropdown (UX, optioneel) — AFGEROND (B6-b, DC012)

Ingehaald door **UX-B6-b**: `eigenaar_organisatie` is geen vrije tekst meer maar een
**verwijzing naar een organisatie-partij**. Het lijstfilter is daarmee een **zoekbare
organisatie-keuze** (`ZoekSelect` op `eigenaar_organisatie_id`, server-side), en sortering loopt
op de gejoinde organisatie-naam (v2n-keyset). De vrije-tekst-`ilike` bestaat niet meer.

### OP-20 — Live-DB-verificatie NULLS-LAST-paginering blokkadesoverzicht (#23) — OPEN

De NULLS-LAST-keyset van het tenant-brede blokkadesoverzicht (CD016, ADR-017 B5:
`encode/decode_sort_cursor_nullable` + `keyset_seek_nulls_last`) is offline
**structureel** getest (cursor-roundtrip met null-vlag, `.nulls_last()` in de
ORDER BY, IS NULL-takken in de seek), maar nog niet **empirisch** tegen Postgres.
Bevestig tijdens de **live-DB-run (#23 / Laag 5)** dat het over de NULL-grens
correct pagineert op de nullable kolommen (`toelichting`, `eigenaar`, `opgelost_op`),
in zowel `asc` als `desc`, zonder duplicaten of overgeslagen rijen.

### OP-23 — Cyclus-padbewaking bij invoer van structuurrelaties (B3) — OPEN

`component_structuur` staat cycli toe (B3): `ZELFVERWIJZING` (self) wordt geweigerd, maar een
indirecte cyclus (A→B, B→A, …) niet. De **leeskant is al cyclus-veilig** (visited-set in elke
traversal, o.a. de impactanalyse CD056). Open vraag: willen we cycli **bij invoer** detecteren/
waarschuwen (pad-bewaking in `component_structuur_service.maak_aan`), of blijft de data-laag
cycli toestaan en bewaakt alleen het leeswerk? Geen verplichting; oppakken als de praktijk
verwarrende cycli oplevert.

### OP-24 — C-drempel: catalogus-keuzevelden zoekbaar boven ~10 opties — OPEN

Catalogus-gedreven keuzevelden (componenttype, relatietype, contract-rol) zijn nu native
`<select>`. Zodra een dimensie structureel **>~10 actieve opties** krijgt, heroverwegen naar een
`ZoekSelect` (zelfde regel als entiteit-referenties, zie complidata-frontend). Geen verplichting;
drempel-gedreven. [CD049]

### OP-25 — Uvicorn-accesslog zonder timestamps — OPEN

De Uvicorn-accesslog mist timestamps, wat live-debugging bemoeilijkt. Logformat configureren
(timestamp + niveau) bij een logging-/observability-pass. Klein, nice-to-have. [CD048]

### OP-26 — `component.eigenaar_organisatie` NOT NULL vs. optionele eigenaar — AFGEROND (B6-b, DC012)

Ingehaald door **UX-B6-b** (migratie 0032): de NOT NULL-vrije-tekstkolom `eigenaar_organisatie` is
vervangen door een **optionele** composiet-FK `eigenaar_organisatie_id → element` (partij,
aard=organisatie). De `""`-workaround is verdwenen; schema's/API dragen nu `None` (echt optioneel).

### OP-27 — Dev-seed in een dev-guarded init-stap — OPEN (nice-to-have)

De dev-testdata (`dev_seed_testdata.py`) is een **handmatige** fixture (niet in de init-container,
bewust dev-only/prod-veilig). Na een reset (`down -v && up -d`) moet hij apart gedraaid worden.
Optioneel: een **dev-guarded** init-stap (bv. env-flag `SEED_DEV=true`) die de dev-seed
automatisch draait in lokale/dev-omgevingen, zodat `down -v && up -d` direct de volledige baseline
geeft — zonder risico op prod-seeding. Raakt de seed-pipeline → eigen besluit. [CD055]

### OP-28 — VPS-deployment — OPEN (roadmap-kandidaat, t.z.t.)

Besluit Bert: in een volgende sessie oppakken. Doel nog te bepalen (demo/test vs. productie).
Raakt: **OP-14** (secrets-hardening — overal `changeme_dev` vervangen door echte secrets); een
**productie-compose-variant** + reverse proxy/HTTPS (alleen 80/443 open); **Keycloak
production-mode** (`KC_HOSTNAME`, redirect-URI's/CORS op het echte domein i.p.v. localhost);
**offsite backups** (de pg_dump-keten bestaat al en is sinds CD055 Keycloak-vrij). Bij een
**productie**-doel zijn **ADR-006** (audit-trail) en **#16** (user-/tenantmanagement)
voorwaarden. EU-jurisdictie-VPS conform de platform-uitgangspunten.

### OP-22 — Backup-scope / secops: Keycloak-secrets in de DB-dump — AFGEROND (geverifieerd CD055)

Opgelost via de tweede optie: **Keycloak draait op een eigen database** `keycloak` (rol
`kc_user`, `init-db/02_keycloak.sql`), losgekoppeld van de app-DB `likara`. De backup
(`gen_build.py` → `pg_dump likara`) bevat daardoor **geen** Keycloak-auth-schema meer
(`credential`/`client`/…); geverifieerd in CD055: `pg_dump --schema-only` van `likara` levert
**0** Keycloak-tabellen. Loste tegelijk de `COMPONENT`-naamruimte-collision op (onze ADR-021-tabel
schaduwde Keycloak's interne `COMPONENT` in het gedeelde `public`-schema → Keycloak startte niet).
Zie complidata-db "V007-patronen" en `docs/LOKAAL-TESTEN.md` (named volume + reset).

---

### ADR-028 — Componentclassificatie (geparkeerd, na ADR-027)

Voorstel geland (DC013). Twee uitbreidingen op het componentmodel:
(1) **Componentrol** (platform-breed): interne_applicatie /
interne_dataprovider / externe_dataprovider / koppelvlak —
bepaalt of koppelingen zelfstandig omgehangen kunnen worden of
afhankelijk zijn van externe ketenafspraken; zichtbaar in
Landschapskaart als visueel onderscheid.
(2) **BIV-classificatie** (tenant-scoped schaal): Beschikbaarheid,
Integriteit, Vertrouwelijkheid — drie velden op component met
tenant-eigen 3- of 5-punts schaal; filterbaar in Landschapskaart,
basis voor migratieset-risicobeoordeling.
Zie docs/adr/ADR-028_componentclassificatie_voorstel.md.

---

### LIKARA — naamswijziging codebase — AFGEROND (LI038–LI050, sessie LI051)

Code-rebrand compleet: skills, docs, generators én alle gedragsbepalende identifiers
(`cd_`/`complidata` → `lk`/`likara`). Zie de V026-stand bovenaan voor de slice-uitsplitsing.
Live geverifieerd via verse provisioning + smoke + RLS-isolatie; backend 931/2/0, frontend 745/745.
**Resteert uitsluitend DC013** (GitHub-repo/remote-naam + lokale `~/complidata/`-map) — Berts
GitHub-actie, zie V026-stand.

---

### Laag-2 identifier-rename: complidata/cd_ → likara — AFGEROND (LI041–LI050)

Feitenrapport (LI041) + uitvoering in slices S1–S8 + de DB-triggerfunctie (S7, gate+migratie 0044):
- cookies `lk_session`/`lk_refresh` (S3); env `LIKARA_TEST_MODE`/`LIKARA_FIXTURE_SET` (S4);
  CSS-tokens `--lk-` (S2); infra `lk_rabbit`/vhost `lk-{slug}`/MinIO `likara_admin`/paden `~/likara/` (S6);
  audit-triggerfunctie `lk_audit_append_only` (S7).
- **`cd_`-tabelprefix bestond niet** (geverifieerd LI041) → geen tabel-migratie nodig; de enige
  schema-rakende rename was de audit-triggerfunctie (S7).
- DB-rol `cd_admin` **bewust niet hernoemd** (geen runtime-gebruik; alleen var-naam in fixtures, opgeschoond in S1).
- Vangrail-greps (`compliman|cm_|Eraneos`) en historie (migratie 0010, changelog) ongemoeid gebleven.

---

## AFGEROND (sessie 2–3)

- **O2** — 7.5 BIO2-classificatie → BBN (CD035): de default-optieset van vraag 7.5 is
  **BBN1/BBN2/BBN3** i.p.v. Laag/Midden/Hoog. Expand/contract: `seed_antwoordconfig`
  levert fresh deploys direct BBN; migratie **0004_bio2_bbn** soft-deactiveert de legacy
  `laag/midden/hoog`-opties op bestaande deploys (incl. dev-DB). Bestaande
  `antwoord_waarde` blijft resolvebaar (inactieve sleutels mét `actief`-vlag). Idempotent;
  engine-tellingen (1·4·3·4 / 7·1·2) ongewijzigd. O3/O4 blijven open observaties.
- **OP-15** — CLAUDE.md test-mode-comment (CD013): de comment was al rechtgezet in
  V004 — `COMPLIDATA_TEST_MODE` versoepelt alleen de Origin-check + rate-limit, geen
  auth-stub, seedt niets, inloggen vereist Keycloak. Punt afgesloten.
- **OP-17** — ADR-009 enum-voetnoten ↔ code (CD013): ADR-009 bijgewerkt naar de
  werkelijke code-waarden (`models.py` als single source, == migratie): hostingmodel 7,
  migratiepad 6 (incl. `tijdelijk_gedeeld`), datatype 6 (incl. `combinatie`),
  protocol = vaste enum, `eigenaar_organisatie`/`organisatie` = vrije tekst,
  `checklist_compleet` transient (ADR-013 B4).
- **OP-1** — platform_init-seed als deploystap → vervangen door de
  init-container (ADR-011): `lk-migrate` migreert (lk_admin) → `platform_init`
  → sluit af, met gating vóór de app. CLAUDE.md Commands bijgewerkt.
- **OP-2** — plantekst + skills bijgewerkt → §Architectuurcorrectie in
  `IMPLEMENTATIEPLAN.md` gecorrigeerd; `platform_init`/deploypatroon in
  complidata-db/-security/-tests vastgelegd.
- **OP-5** — cookie-attributen settings-driven (`cookie_secure`/`samesite`/
  `domain`) bevestigd; `COOKIE_SECURE=false` voor lokaal http (P4).
- **OP-8** — CONTRIBUTING §6 As 2 gecorrigeerd naar
  `python3 -m pytest backend/tests/ modules/` (groen geverifieerd).
- **OP-9** — deploy-/migratiestrategie vastgelegd in **ADR-011** (init-container).
- **OP-10** — OIDC `redirect_uri` gelijkgetrokken (realm ↔ backend) +
  realm-import (`--import-realm`); login-round-trip werkt.
- **OP-11** — `lk_admin` volledig uit de app-laag; `lk_platform` (non-superuser)
  voor platform-endpoints (ADR-012).
- **OP-12** — rol-mapping/tweelaags rollenmodel → opgegaan in **ADR-012**
  (realm-rollen → `realm_access.roles`, platform- + tenant-domein).

## LI018 — Openstaande punten

### Besloten, nog niet gebouwd
- **UI-hernoeming "Applicatie → Component"** — overal in de UI waar "Applicatie" de
  generieke component-entiteit bedoelt: menu, lijstpagina, detailpagina, knoppen.
  Pure frontend-hernoeming, geen datamodel-wijziging.
- **Type-indicator op graph-nodes** — klein type-label of icoon op de node zelf
  zodat het componenttype zichtbaar is zonder klikken.
- **"Resultaten" → "Componenten"** hernoemen in de Landschapskaart-zijbalk.
- **ADR-032 "Start vanuit..."-wijzer** — scope besloten (5 ingangen), open subknopen
  nog te beslissen vóór de bouw.

### Parkeer-items (geen actie tot opgepakt)
- Dedicated vitest-tests voor edge-popup-per-ring + groepeer-toggle Landschapskaart.
- Aardsortering "Afdeling" sorteert op enum-positie i.p.v. label-alfabetisch.
- COMPLIDATA_TEST_MODE → LIKARA_TEST_MODE (optioneel, feature-flag geen identifier).
- Pre-existing failing integratietest: `test_component_contract_op_niet_applicatie_component`
  (DB-state afhankelijk, faalt op schone reseed — niet door LI018).
- Skill-directorynamen `complidata-*` en `.claude/skills/complidata/` hernoeming
  (Laag 2 Fase 3 — bewust uitgesteld).
- Markdown-prose in session-docs (NEXT_SESSION/SESSIE_BRIEFING etc.) bevatten
  nog cd_app/cd-* in tekst — doc-pass indien gewenst.
