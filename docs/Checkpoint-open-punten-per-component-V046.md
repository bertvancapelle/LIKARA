# Checkpoint — "alles wat dít systeem nog nodig heeft" (open punten per component)

**Sessie:** LI046 · **Build:** V046 · **Commit:** 142d1c5 · **Type:** READ-ONLY feitenopname vóór ontwerp
**Datum:** 2026-07-19 · **Aard:** design-heavy → checkpoint-eerst (werkprotocol §Gate-discipline)

> Dit rapport **wijzigt niets** aan code/schema/seed. Het enige geschreven bestand is dit rapport zelf.
> Alle DB-metingen zijn `SELECT` als `lk_admin` (ziet alle tenants). Feiten met vindplaats (bestand:regel).
> Waar iets niet vast te stellen was: **"niet vastgesteld"**.

---

## Kernbevinding vooraf (leest u dit eerst)

Twee dingen die het ontwerp raken, gescheiden gehouden:

1. **Het beeld kán op bestaande feiten rusten.** Er is al één gedeelde afleiding
   (`component_norm_service.norm_status` + `splits_afwijking`) die per component levert wat "op de
   lat" staat en nog niet vastgesteld is, mét de verschoven-lat-nuance. De registratiegaten-badge
   levert de rest. **Geen leeg omhulsel** — de grond bestaat.
2. **⚠ De draaiende dev-database draagt de norm-data NU NIET.** `component_norm` is **leeg (0 rijen)**
   terwijl de seed die tabel hoort te vullen (5 verplichte feiten) en de klaarverklaring-snapshots
   bewijzen dát de tabel bij het seeden gevuld wás. Gevolg: in de huidige browser-stand toont het
   "moet nog"-blok, de norm-afwijking én de verschoven-lat **niets** voor elk component. **Een reseed
   is nodig vóór een browsercheck van dit ontwerp.** Dit is een stop-en-rapporteer-punt (§Blok 6/7) —
   ik heb het **niet** hersteld.

---

## Blok 1 — Wat ziet de consultant vandaag als hij één systeem opent?

Kernbestand: `modules/bwb_ontvlechting/frontend/views/ComponentDetail.vue`. Tabs opgebouwd in
`topTabs` (ComponentDetail.vue:201-225).

### Secties/tabbladen (in volgorde) en of ze iets over een ontbrekend feit tonen

| # | Tab | Conditie | Toont ontbrekend feit? | Vindplaats |
|---|---|---|---|---|
| — | **DetailKop-badge** (`SignaleringBadge`) | altijd | ja — teller 🔴/🟡 + tooltip-namen; **read-only, geen doorklik**; dekt 5 signalen | ComponentDetail.vue:312; SignaleringBadge.vue:29-42 |
| — | **Voortgangsregel** | checklist-dragend | ja — "X/Y vragen gescoord · N open blokkade(s)" | ComponentDetail.vue:347-350 |
| 1 | Overzicht | altijd | ja (gedempt "nog niet vastgelegd/geregistreerd"): BIV `:387-391`, levensfase `:400`, bedoeling `:406`, complexiteit/prioriteit `:413/:418`, eigenaar `:436`, product owner/proceseigenaar `:441/:446` | ComponentDetail.vue |
| 1b | Migratiegereedheid-blok (in Overzicht) | checklist-dragend | ja — status + afwijkingen (zie §3) | ComponentDetail.vue:458-464 |
| 2 | Bedrijfsfunctie ("Waarvoor gebruiken we het") | altijd | ja — lege staat `cbf-leeg` + norm-"i" | ComponentBedrijfsfunctieSectie.vue:267-270,:222 |
| 3 | Checklist | checklist-dragend | indirect — scores ja/deels/nee/nvt; geen expliciet "ontbrekend"-signaal per vraag | ChecklistscoreSectie.vue:6-8 |
| 4 | Datatypes | subtype | niet als open-punt gemarkeerd | ComponentDetail.vue:210 |
| 5 | Gebruikersgroepen | subtype | lege staat | ComponentDetail.vue:211 |
| 6 | Koppelingen | subtype | ja — `BewustGeenControl` + lege staten + norm-"i" | KoppelingSectie.vue:368-372,:399,:428,:361 |
| 7 | Gebruik ("Wie gebruikt dit") | altijd | ja — lege staat + "afdeling onbekend" | OrganisatiegebruikSectie.vue:228-232,:207-214 |
| 8 | Opbouw | altijd | niet als open-punt gemarkeerd | ComponentDetail.vue:218 |
| 9 | Impact | altijd | niet als open-punt gemarkeerd | ComponentDetail.vue:219 |
| 10 | Contracten | altijd | ja — `BewustGeenControl` + "Geen valt-onder-contract geregistreerd." | ContractSectie.vue:250-254,:347,:265 |
| 11 | Verantwoordelijkheden | altijd | ja — lege staat + norm-"i" | VerantwoordelijkheidSectie.vue:175,:147 |
| 12 | Blokkades | checklist-dragend | ja — open blokkades met doorklik naar vraag | ComponentDetail.vue:597-602 |

De norm-"i"-aanduiding (VeldUitleg met `norm-feit`) hangt aan sectiekoppen/velden en toont per feit
één passage *"Dit feit telt mee om dit systeem klaar te kunnen verklaren. Opslaan kan wel zonder."*
(VeldUitleg.vue:37,:45-47,:155-161; ge-provide via `useNormLat`, ComponentDetail.vue:61-62).

### Op hoeveel plekken moet hij kijken?

**Minimaal 6–8 verschillende plekken** om te weten wat er nog mist aan één component: DetailKop-badge
+ Overzicht + Migratiegereedheid-blok + voortgangsregel + Bedrijfsfunctie-tab + Gebruik-tab +
Contracten-tab + Verantwoordelijkheden-tab (+ Koppelingen/Gebruikersgroepen bij subtype, + Checklist/
Blokkades). **Geen enkele plek toont het volledige beeld.**

### Bestaat er al een bundeling?

Twee **deel**-bundelingen, geen navigeerbare wegwijzer:

- **`MigratiegereedheidSectie.vue`** (alleen bij checklist-dragend, ComponentDetail.vue:458-464). Toont
  **wél**: status-Tag klaar/niet-klaar (:206-210), wie/wanneer (:214-216), checklist-afwijking (amber,
  :227-239), **norm-afwijking** "N verplichte feiten nog niet vastgesteld: …" (amber, :242-254),
  **verschoven lat** (neutraal, :286-302), verantwoordingsvenster met bevroren snapshot (:259-280), en
  — **alleen in de klaarverklaar-dialoog** — de volledige lijst nu-open verplichte feiten (:324-340).
  Toont **niet**: een lijst van wat nog mist **zolang niet klaar verklaard is** (het leesblok zelf blijft
  leeg tot klaarverklaring-met-afwijking); **geen navigatie naar het ontbrekende feit** (alleen een
  leesroute naar `norm-beheer`, :338); **niet** voor niet-checklist-dragende componenten.
- **`SignaleringBadge`** — telt registratiegaten (kritiek/aandacht), **read-only, geen doorklik**, dekt
  slechts een deel van de signalen (SignaleringBadge.vue:29-42).

**Conclusie:** er bestaat geen gebundelde, navigeerbare "open punten van dit systeem"-lijst.

---

## Blok 2 — Welke open punten zijn per component al ophaalbaar?

### Per bron

**Registratiegaten** (`registratiegaten_service.py`). 10 signaaltypen (constanten :48-68), ingedeeld
kritiek/aandacht (:435-452). Per-component opvraagbaar via **`badge_voor_component`** (:172-261) →
endpoint `GET /signalering/badges/component/{id}` (routes/signalering.py:32-39, RBAC COMPONENT/LEZEN),
respons `{signalen, kritiek, aandacht}`. **De badge dekt 7 van de 10 signalen** (eigenaar,
verantwoordelijke, biv, gebruikersgroep, isolatie, object_zonder_roltoewijzing, geen_bedrijfsfunctie —
:245-261). **Niet per component in de badge**: `contract_zonder_component`,
`gebruiksfeit_zonder_verfijning`, `antwoord_zonder_verantwoordelijke` (alleen tenant-breed via
`registratiegaten()`).

| Signaal | Conditie | Ernst | Vindplaats |
|---|---|---|---|
| `component_zonder_eigenaar` | `eigenaar_organisatie_id IS NULL` | kritiek | :134 |
| `component_zonder_verantwoordelijke` | `¬∃ roltoewijzing(object_id=component)` | kritiek | :142-146 |
| `biv_classificatie_onvolledig` | een van `biv_*` IS NULL | kritiek | :152-158 |
| `component_zonder_gebruikersgroep` | `¬∃ serving(component→gebruikersgroep)` | aandacht | :270-274 |
| `component_geisoleerd` | `¬∃ flow(bron|doel=component)` | aandacht | :286-291 |
| `contract_zonder_component` | `¬∃ association(doel=contract)` | aandacht | :303-307 |
| `object_zonder_roltoewijzing` | `¬∃ roltoewijzing(object_id=id)` (comp/contract/gg) | aandacht | :87-93,:316-340 |
| `gebruiksfeit_zonder_verfijning` | grof gebruik zonder afdeling | aandacht | :60 |
| `antwoord_zonder_verantwoordelijke` | checklist-antwoord zonder rol | aandacht | :63 |
| `component_zonder_bedrijfsfunctie` | type `ondersteunt_werk` ∧ `¬∃ functievervulling(component)` | aandacht | :71-78,:417-422 |

**Checklist** (`checklistscore_service.py`). Score-enum `ja|deels|nee|nvt` (models.py:114-118);
`_BLOKKADE_VEREIST=(nee,deels)` (:69). Per component filterbaar: `lijst(component_id=…)` (:295-296) →
`GET /checklistscores?component_id=` (routes/checklistscore.py:42-73). **Kanttekening:** score-filter
op nee/deels is **client-side** (geen server-side score-filter), en de **vraagcode (het anker) staat
op `ChecklistVraag.code` maar ontbreekt in `ChecklistscoreRead`** (schemas/checklistscore.py:133) — de
code moet apart worden opgehaald.

**Norm-status** (`component_norm_service.py`, ADR-052). `norm_status(session,tid,component_id)` levert
per **verplicht** feit `vastgesteld`/`niet_vastgesteld` (:101-152) → `GET /component-normen/status/{id}`
(routes/component_norm.py:25-33, RBAC COMPONENT_NORM/LEZEN). `HARDE_FEITEN` = 10 sleutels (:38-53):
eigenaar, verantwoordelijke, biv, gebruikersgroep, bedrijfsfunctie, levensfase, bedoeling (=migratiepad),
hosting (=hostingmodel, sentinel `onbekend` telt niet), koppelingen, contract. `DEFAULT_VERPLICHT` =
{eigenaar, verantwoordelijke, biv, contract, koppelingen} (:58-60). Determinatie in één pure functie
`_beslis_vastgesteld` (:155-170), enkelfeit-variant `feit_vastgesteld` (:173-200).

**"Bewust geen"** (`component_bevinding_service.py`). Enum `ComponentBevindingSoort = koppelingen |
contract` — **alleen deze twee** (models.py:1473-1477). `registreer_geen` (409 als er al een echte
registratie is, :120-148), `soorten_van_component` (:91-102), `heeft_echte_registratie` (koppelingen=
flow, contract=association, :62-88). Endpoint `GET /component-bevindingen/component/{id}` (:24-31).

**Component-eigen lege velden** (`models.py`, class `Component` :347): `beschrijving` (nullable, :376),
`migratiepad`/bedoeling (nullable, :381-384), `levensfase` (nullable, :385-389), `hostingmodel` (NOT NULL,
sentinel `onbekend`, :373), `eigenaar_organisatie_id` (nullable, :375). **Bedrijfsfunctie-plaatsing is
geen kolom** — het is de relatie `Functievervulling`; per component leesbaar via de badge (:229-243).

### Slottabel — mockup-punt → bron → ophaalbaar

| # | Mockup-punt | Bron (functie / vindplaats) | Per component ophaalbaar |
|---|---|---|---|
| 1 | geen eigenaar | `badge_voor_component` (`_SIG_EIGENAAR`) :186-194,:247 | **ja** (badge) |
| 2 | BIV niet geclassificeerd | `badge` (`_SIG_BIV`) :219-227,:251 | **ja** (badge) |
| 3 | checklist op "nee"/"deels" | `checklistscore_service.lijst(component_id=…)` :269-323 | **deels** (per component filterbaar; score-filter + vraagcode client-side; code niet in Read-schema) |
| 4 | geen contract | per component via `norm_status` (feit `contract`, echte-reg/bevinding :131-143); tenant-breed via `contract_zonder_component` | **deels** (per component alleen via norm-status, niet via badge) |
| 5 | geen bedrijfsfunctie | `badge` (`_SIG_GEEN_BF`) :229-243,:259 | **ja** (badge) — alleen werk-ondersteunende typen |
| 6 | geen gebruikersgroep | `badge` (`_SIG_GG`) :204-210,:253; óók norm-feit `gebruikersgroep` | **ja** (badge + norm) |
| 7 | geïsoleerd | `badge` (`_SIG_ISOLATIE`) :211-218,:255 | **ja** (badge) |
| 8 | levensfase onbekend | `Component.levensfase` nullable; `norm_status` feit `levensfase` :166-167 | **ja** (via norm-status, mits verplicht gesteld) |
| 9 | bedoeling niet vastgelegd | `Component.migratiepad` nullable; `norm_status` feit `bedoeling` :168-169 | **ja** (via norm-status, mits verplicht gesteld) |

**Belangrijkste les:** punten 1,2,5,6,7 komen uit één per-component call (`/signalering/badges/component/{id}`);
punten 4,8,9 uitsluitend uit `/component-normen/status/{id}`; punt 3 uit de checklist-lijst. Het overzicht
zou dus vandaag **drie bronnen** moeten samenvoegen (badge + norm-status + checklist).

---

## Blok 3 — Kan de splitsing "moet / netjes" op de norm rusten?

**Ja, de lat is per component leesbaar.** `haal_norm(session,tid)` = de lat (`{feit: verplicht}` over de
volledige `HARDE_FEITEN`-set, :84-98); `norm_status` = per component welke **verplichte** feiten nog open
staan (alleen verplichte feiten komen in `feiten`, :120,:152). De niet-verplichte `HARDE_FEITEN` = het
"netjes"-domein dat de norm bewust niet meetelt.

**Dekt de norm de negen mockup-punten? — 7 van 9 zit in de norm; 2 vallen er principieel buiten.**

| Mockup-punt | In norm (`HARDE_FEITEN`)? | Laag |
|---|---|---|
| geen eigenaar | ja (default-verplicht) | norm + signaal |
| BIV niet geclassificeerd | ja (default-verplicht) | norm + signaal |
| **checklist op "nee"** | **nee** | engine/lifecycle-beoordeling (norm raakt de engine bewust nooit) |
| geen contract | ja (default-verplicht) | norm (echte-reg OF bewust-geen) |
| geen bedrijfsfunctie | ja (niet default-verplicht) | norm + signaal |
| geen gebruikersgroep | ja (niet default-verplicht) | norm + signaal |
| **geïsoleerd** | **nee** | alleen signalering (`component_geisoleerd`, geen `HARDE_FEIT`) |
| levensfase onbekend | ja (niet default-verplicht) | norm |
| bedoeling niet vastgelegd | ja (niet default-verplicht) | norm |

De norm kent bovendien 3 feiten die **niet** in de negen mockup-punten zitten: `verantwoordelijke`,
`hosting`, `koppelingen`. (`koppelingen` in de norm ≈ het signaal `geïsoleerd`, maar via `heeft_echte_
registratie` mét bevinding-uitsluiting — dus niet identiek.)

**Geen norm / lege lat → alles valt in "netjes".** `haal_norm` degradeert netjes: `opgeslagen.get(feit,
False)` (:98) — een feit zonder rij telt als niet-verplicht; `norm_status` retourneert dan `feiten: {}`
(:120,:152). Component buiten tenant/onbestaand → expliciet leeg (:117-118). **Dit is exact de huidige
live-stand** (component_norm leeg, zie Blok 6).

**Verschoven lat (LI045): ja, per component onderscheiden.** `splits_afwijking(live, snapshot)`
(:223-233) → `{"bewust": [...], "verschoven": [...]}`: `bewust` (amber) = feit stónd in de bevroren
snapshot (afgewogen bij verklaren); `verschoven` (neutraal) = feit stond er níét in (lat verschoof ná
verklaren). Herkomst: `ComponentKlaarverklaring.open_feiten` (bevroren snapshot, models.py:1444-1446) vs
`_live_niet_vastgesteld` (:236-240, hergebruikt `norm_status`). Het audit-log voedt **alleen** de
metadata "wanneer/door wie", niet de classificatie (:218,:312-343). Per component: `afwijking_voor_
component` (:259-268) → `GET /component-normen/afwijking/{id}` (routes/component_norm.py:49-58).
**Kanttekening:** de bewust/verschoven-splitsing bestaat **alleen bij een levende klaarverklaring** (geen
snapshot ⇒ geen onderscheid). Voor een nog-niet-klaar-verklaard component zijn alle open verplichte
feiten simpelweg "moet nog" (neutraal, geen amber/neutraal-onderscheid).

---

## Blok 4 — Twee gaten die stil dubbel of stil verkeerd kunnen tellen

**1. Dubbeltelling — bevestigd.** `component_zonder_verantwoordelijke` (kritiek, :142-146) en de
component-tak van `object_zonder_roltoewijzing` (aandacht, `_geen_roltoewijzing` :87-93 toegepast :320-325)
vuren op **exact dezelfde** conditie `¬∃ roltoewijzing(object_id=component)`. Expliciet zo in de badge:
`if geen_rol: kritiek.append(_SIG_VERANTWOORDELIJKE)` (:249-250) **én** `if geen_rol:
aandacht.append(_SIG_OBJ_ROL)` (:257-258, met comment "telt óók als object zonder roltoewijzing, ADR-035").
Netto verhoogt één ontbrekende roltoewijzing zowel de kritiek- als de aandacht-teller. **Geen andere
paren gevonden**: de contract-/gg-takken van `object_zonder_roltoewijzing` hebben geen gepaard
kritiek-signaal; `antwoord_zonder_verantwoordelijke` is een andere entiteit (checklistscore, niet component)
en telt niet dubbel. → **Ontwerpregel: geen_rol telt in het overzicht één keer** (als `verantwoordelijke`;
`object_zonder_roltoewijzing` laten vallen voor de component-weergave).

**2. Bewust leeg ≠ gat — hier zit een echt gevaar.** Feiten met "bewust geen": **alleen `koppelingen` en
`contract`**. De **registratiegaten-signalering houdt daar géén rekening mee**: `registratiegaten_service`
importeert `component_bevinding_service` niet, en `component_geisoleerd` (:286-291) resp.
`contract_zonder_component` (:303-307) blijven vuren óók als er een "bewust geen"-bevinding is. De
uitsluiting bestaat **alleen** in de norm-laag: `norm_status` telt `koppelingen`/`contract` als vastgesteld
zodra er een bevinding is óf een echte registratie (:131-143). → **Ontwerpregel: bron `contract` en
`koppelingen` (geïsoleerd) voor het overzicht uit `norm_status`, NIET uit de badge/registratiegaten** —
anders komt een bewust-geen-antwoord alsnog als gat terug (schending van "een bewust leeg antwoord is een
antwoord").

---

## Blok 5 — Heeft elk punt een route?

Vanaf het componentdetailscherm. (a) route naar het punt · (b) route naar het scherm/formulier, niet naar
het punt · (c) geen route.

| Punt | Klasse | Affordance |
|---|---|---|
| geen eigenaar | **(b)** | gat zichtbaar op Overzicht (`eigenaar-gat` :436); invullen alleen via **Bewerken**-overlay (heel formulier, :315→:629) |
| BIV niet geclassificeerd | **(b)** | gat op Overzicht (:387-391); fix via Bewerken-overlay; badge niet klikbaar |
| checklist op "nee" | **(a)** | `onNaarVraag` zet tab=checklist + categorie + `markeerVraagCode` (:277-281); deep-link `?markeer=` (:250-253); jump vanuit Blokkades (:601) |
| geen contract | **(a)** | Contracten-tab: `BewustGeenControl` "Vastleggen: geen contract" + "Contract koppelen" (ContractSectie.vue:250-254); ook vanuit checklist-context "Naar de Contracten-sectie" (:536-543) |
| geen bedrijfsfunctie | **(a)** | Bedrijfsfunctie-tab: `cbf-leeg` + "Koppelen"-toevoegregel (ComponentBedrijfsfunctieSectie.vue:267-270,:317) |
| geen gebruikersgroep | **(a) bij subtype, anders (c)** | Gebruikersgroepen-tab bestaat **alleen** bij `isSubtype` (:211,:564-566); niet-subtype → geen tab/route |
| geïsoleerd (geen koppelingen) | **(a) bij subtype, anders (c)** | Koppelingen-tab alleen bij `isSubtype` (:212,:567-569); `BewustGeenControl` (KoppelingSectie.vue:368-372) |
| levensfase onbekend | **(b)** | gat op Overzicht (`levensfase-leeg` :400); fix alleen via Bewerken-overlay |
| bedoeling niet vastgelegd | **(b)** | gat op Overzicht (`bedoeling-leeg` :406); fix alleen via Bewerken-overlay |

**Samenvatting:** 3 punten (a) altijd (checklist-nee, contract, bedrijfsfunctie) · 2 punten (a) alleen bij
subtype anders (c) (gebruikersgroep, koppelingen) · 4 punten (b) (eigenaar, BIV, levensfase, bedoeling —
zichtbaar op Overzicht, fix alleen via het complete Bewerken-formulier). **Geen enkel punt heeft een
affordance die naar het exacte veld binnen het bewerkformulier springt** (veld-focus/deep-link in
`ComponentFormulier` **niet vastgesteld**). Dode punten (route c) ontstaan uitsluitend voor niet-subtype
componenten bij gebruikersgroep/koppelingen — een ontwerpbevinding, geen bouwtaak.

---

## Blok 6 — Tellingen uit de dev-database (read-only)

**Dev-tenant:** één tenant `11111111-1111-1111-1111-111111111111`, **19 componenten**.
```sql
SELECT tenant_id, count(*) FROM component GROUP BY tenant_id;
-- 11111111-…-111111111111 | 19
```

### ⚠ Stale-DB-bevinding (stop-en-rapporteer)

```sql
SELECT count(*) FROM tenant;          -- 0
SELECT count(*) FROM component_norm;  -- 0
SELECT count(*) FROM component_klaarverklaring;  -- 5
SELECT count(*) FROM component_bevinding;        -- 3
```
- **`component_norm` is leeg (0 rijen)** terwijl `main()` de norm seedt vóór het scenario
  (`dev_seed_testdata.py:1890` `seed_component_norm`, dan `:1905` `_seed_bvowb_scenario`) en de norm 5
  verplichte feiten hoort te dragen (`services/seed.py:179-199`, `DEFAULT_VERPLICHT`).
- De klaarverklaring-**snapshots zijn wél gevuld** — bewijs dat de norm bij het seeden bestónd:
  ```sql
  SELECT c.naam, k.open_feiten FROM component_klaarverklaring k JOIN component c ON c.id=k.component_id;
  -- Archiefbeheer | {biv,eigenaar,verantwoordelijke}
  -- DMS          | {biv}
  -- Zaaksysteem  | {biv}
  -- HR-systeem   | {}     (schoon geval — klaar met 0 open feiten)
  -- Klantportaal | {}
  ```
- **Gevolg:** `norm_status`/`haal_norm` geven nu voor élk component "niets verplicht" → het live "moet
  nog"-blok, de norm-afwijking (MigratiegereedheidSectie) én de verschoven-lat tonen **niets** in de
  browser. **Oorzaak niet read-only vast te stellen** (norm bestond, is sindsdien geleegd — mogelijk een
  test-teardown of handmatige ingreep tegen de dev-tenant; niet gediagnosticeerd, niet hersteld).
- **`tenant`-registry is óók leeg** (0 rijen; geen rij voor `1111…`) — de dev-fixture gebruikt de
  hardcoded tenant-id zonder registratie-rij. Vermoedelijk normaal voor de fixture, maar meldenswaardig
  naast het norm-gat.

**Advies (niet uitgevoerd):** reseed de dev-tenant vóór een browsercheck van dit ontwerp
(`docs/LOKAAL-TESTEN.md` / dev_seed). Beslissing aan Bert.

### Open punten per component (berekend uit de defaults, want norm nu leeg)

Onderstaande "moet nog" gebruikt `DEFAULT_VERPLICHT` = {eigenaar, verantwoordelijke(rol), biv, contract,
koppelingen}, mét bevinding-uitsluiting voor contract/koppelingen — dus wat het overzicht ná een reseed
zou tonen. "netjes" = open niet-verplichte `HARDE_FEITEN` (gebruikersgroep, bedrijfsfunctie, levensfase,
bedoeling). Vlaggen via één `SELECT` (zie voetnoot). ✓ = feit vastgesteld/aanwezig.

| Component | type | moet nog (default) | netjes | klaar? | opmerking |
|---|---|---:|---:|---|---|
| **Extern SaaS-platform** | saas_dienst | **5** | 4 | nee | eig+biv+rol+contract+koppel |
| **Shared fileshare** | fileshare | **5** | 4 | nee | idem |
| Aangiften | applicatie | 4 | 4 | nee | |
| Reisdocumenten | applicatie | 4 | 3 | nee | |
| Shared DB-server | database | 4 | 3 | nee | checklist-dragend |
| Verkiezingen | applicatie | 4 | 3 | nee | |
| **Archiefbeheer** | applicatie | **3** | 4 | **ja** | bevinding koppelingen+contract → uitgesloten (bewust-geen werkt) |
| Omgevingsloket | applicatie | 2 | 2 | nee | |
| Vergunningensysteem | applicatie | 2 | 3 | nee | |
| BRP · Burgerzaken-suite · DMS · Financieel systeem · Gegevensmakelaar · Sociaal domein suite · Zaakafhandelcomponent · Zaaksysteem | applicatie | 1 (biv) | 1–2 | DMS/Zaaksysteem ja | biv-only gat (bijna alle componenten missen BIV) |
| **Klantportaal** | applicatie | **0** | 1 (bedoeling) | ja | norm-compleet → leeg "moet"-blok, 1 netjes |
| **HR-systeem** | applicatie | **0** | 3 | ja | het schone geval |

- **Schoon geval (HR-systeem):** draagt **0 punten in "moet nog"** ✓ (BIV/eigenaar/rol/contract compleet;
  "koppelingen" bewust-geen → uitgesloten; snapshot `{}` bevestigt). Wél 3 "netjes"-punten (gebruikersgroep,
  bedrijfsfunctie, levensfase nog niet vastgelegd). → **goed ijkbeeld** dat het moet-blok leeg is terwijl
  netjes gevuld is.
- **Rijk geval:** de méeste "moet nog" dragen **Extern SaaS-platform** en **Shared fileshare** (elk 5) —
  maar dat zijn **niet-checklist-dragende** typen (MigratiegereedheidSectie verschijnt daar niet). Het
  **beste checklist-dragende demonstratiegeval is Archiefbeheer**: klaar verklaard, 3 open verplichte feiten
  (biv/eigenaar/verantwoordelijke) én bevindingen die de bewust-geen-uitsluiting aantonen — precies de
  "klaar mét afwijking"-showcase uit de seed.
- **Alleen "netjes":** **Klantportaal** (0 moet, 1 netjes = bedoeling) — toont dat een leeg "moet"-blok er
  rustig uitziet. (HR-systeem is óók 0 moet, maar met 3 netjes.)

> Voetnoot — de per-component-vlaggen zijn berekend met één query (eigenaar/BIV/levensfase/migratiepad uit
> `component`; roltoewijzing/flow/association/serving uit `relatie`+`roltoewijzing`; bedrijfsfunctie uit
> `functievervulling` × `ondersteunt_werk`; bevinding uit `component_bevinding`; `ondersteunt_werk`-set =
> applicatie/client_software/fileshare/saas_dienst/landelijke_voorziening). Volledige query beschikbaar in
> het sessie-transcript; niet in dit rapport ingekort weergegeven om leesbaarheid te bewaren.

---

## Blok 7 — Verrassingen en risico's

1. **⚠ Stale dev-DB (zie Blok 6).** De norm-data die dit ontwerp demonstreerbaar maakt, staat nu niet in de
   draaiende DB. Een browsercheck vóór reseed zou een vals-leeg beeld geven. **Reseed nodig; niet
   uitgevoerd.**

2. **De gedeelde leeslaag bestáát — maar het overzicht overspant twee bronnen met verschillende semantiek.**
   `norm_status` + `splits_afwijking` is één afleiding met bestaande consumenten (MigratiegereedheidSectie
   via `/component-normen/afwijking`; SignaleringView via `/component-normen/verschoven-lat`;
   `component_klaarverklaring_service` bevriest eruit; `component_norm_beheer_service` voorspelt ermee). **Maar**
   het "open punten per component"-beeld heeft óók de badge (registratiegaten) én de checklist nodig, en die
   drie bronnen zijn **niet** geharmoniseerd: registratiegaten honoreert "bewust geen" niet, norm_status wél
   (Blok 4.2); registratiegaten dubbeltelt geen_rol (Blok 4.1). Een naïeve samenvoeging telt stil verkeerd.
   Er is **geen bestaande per-component "alle open punten"-functie** — die zou netjes op `norm_status` (+
   badge voor het niet-genormeerde deel) kunnen landen, maar bestaat nog niet.

3. **Norm-aanduiding is per-scherm geborgd, geen globale scan** (OPVOLGPUNTEN LI045-2/3). Een nieuw scherm dat
   norm-feiten toont moet zélf `useNormLat` mounten, `provide('normVerplicht', …)` doen en per veld de juiste
   `norm-feit`-sleutel zetten (VeldUitleg.vue:33,:45); er is **geen vangnet** dat afdwingt dat de "telt
   mee"-aanduiding verschijnt. Een "open punten"-overzicht dat norm-feiten toont vergt dus een **eigen
   tellende test** per scherm, anders valt de aanduiding stil weg.

4. **Taal botst op meerdere plekken** (§5 Terminologie / LI045-brug):
   - **bedoeling/migratiepad**: `NORM_FEIT_LABEL.bedoeling` = "Bedoeling (migratiepad)" (labels.js:333),
     Overzicht-label "Bedoeling" (ComponentDetail.vue:402), veld-uitleg-sleutel `migratiepad` — **drie namen,
     één feit**.
   - **verantwoordelijke** (norm-feit) vs **Verantwoordelijkheden** (tabkop) — enkelvoud/meervoud.
   - **bedrijfsfunctie** (norm-feit) vs sectiekop **"Waarvoor gebruiken we het"** (bewust, mét feit-ondertitel,
     LI045-brug).
   - **Gebruik**-tab (organisatiegebruik) ≠ norm-feit **gebruikersgroep** — verwarringsrisico: de "Gebruik"-tab
     dekt het norm-feit gebruikersgroep níét af.
   Een overzicht dat feiten benoemt moet consequent uit `NORM_FEIT_LABEL` putten (LI045-brugregel).

5. **Stille keuzes die dit ontwerp maakt en die niemand expliciet genomen heeft** — als **vragen** (Blok
   "open ontwerpvragen"), niet door mij beslist: welke lat voedt "moet"; waar landen de 2 punten buiten de
   norm (checklist, geïsoleerd); hoe telt geen_rol; bron voor contract/koppelingen; wat met niet-subtype en
   niet-checklist-dragende componenten; en of "moet" zonder klaarverklaring wel/geen amber-onderscheid kent.

---

## Open ontwerpvragen voor Bert

1. Welke lat voedt "dit moet nog" — de **tenant-norm** (`norm_status`, wat de gemeente op de lat legde) of een vaste set? (De code biedt de tenant-norm; ik heb geen keuze gemaakt.)
2. De twee punten die **buiten de norm** vallen — **checklist op "nee"** (voedt de lifecycle/beoordeling) en **geïsoleerd** (alleen signalering) — vallen die in "netjes", in "moet", of in een eigen derde categorie?
3. **geen_rol dubbeltelt** (kritiek `verantwoordelijke` + aandacht `object_zonder_roltoewijzing`): tellen als één punt "verantwoordelijke", akkoord?
4. **Contract en koppelingen uit `norm_status` halen** (honoreert "bewust geen"), niet uit de badge/registratiegaten (die honoreert het niet) — akkoord dat dat de bron is?
5. Geldt het overzicht óók voor **niet-checklist-dragende** componenten (saas_dienst/fileshare — daar toont MigratiegereedheidSectie nu niets) en voor **niet-subtype** componenten (waar de gebruikersgroep-/koppelingen-tab en dus de route ontbreken)?
6. Voor een component **zonder klaarverklaring** bestaat er nog geen bevroren snapshot, dus geen bewust/verschoven-onderscheid: is "moet nog" daar simpelweg neutraal (alle open verplichte feiten), of wil je daar een andere behandeling?
7. Moeten de vier **(b)-punten** (eigenaar, BIV, levensfase, bedoeling) een route naar het **exacte veld** krijgen (nu bestaat alleen "open het hele Bewerken-formulier"), of volstaat "breng me naar het scherm"?
8. De **stale dev-DB** (component_norm leeg): een reseed uitvoeren vóór het bouwen/de browsercheck — akkoord, en wanneer?

*(STOP na dit rapport. Geen vervolgstap gebouwd. Niet gecommit.)*
