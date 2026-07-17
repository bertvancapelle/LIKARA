# Checkpoint — tenant-norm harde velden + verrijkte klaarverklaring (V044)

**Aard:** read-only feitenopname. Niets gewijzigd/gemigreerd/gecommit.
**Grond:** schone `master`, commit `a335d4d` (V044).
**Discipline:** de code spreekt. Waar het besloten beeld in de opdracht van de gebouwde realiteit afwijkt, staat dat expliciet benoemd; stille keuzes zijn gemarkeerd, niet opgelost.

---

## Blok 1 — De bestaande klaarverklaring (ADR-027): wat is het vandaag?

**Bevinding: volledig gebouwd, engine-gescheiden, en onafhankelijk van de checklist. Er bestaat al een "afwijking"-begrip.**

1. **Waar het leeft + wat het vastlegt.** Tabel `component_klaarverklaring` (`models.py:1403`, migraties 0035/0036/0038), service `component_klaarverklaring_service.py`, route `/klaarverklaringen` (`routes/component_klaarverklaring.py`). Velden: `component_id` (composiet-FK → element, CASCADE), `status` (`klaar`↔`open`, default `klaar`), **verplichte `reden`** (Text), en server-gestempeld `verklaard_door_sub` + `verklaard_door` (e-mail-fallback) + `verklaard_op`. **Eén levende verklaring per component** (`UNIQUE(tenant_id, component_id)` → 409 `KLAARVERKLARING_BESTAAT_AL`). Het klaar→open→klaar-verloop leeft in de append-only audit-trail (geen aparte historie-tabel). RBAC: `Entiteit.KLAARVERKLARING` = `_INHOUD` (Viewer L · Medewerker LAW · Beheerder LAWV · Auditor L); aanmaken=AANMAKEN, statuswissel=WIJZIGEN.

2. **Volledig engine-gescheiden — bevestigd.** De service-docstring (`:11-13`) verklaart geen engine-import; read-only geverifieerd: geen `lifecycle_service`/`herbereken_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore`-import, geen schrijfpad naar lifecycle/score/blokkade. `component_klaarverklaring` staat in `AUDIT_TENANT_ENTITEITEN` (`audit.py:79`) → mutaties worden via de ORM-`flush`-hooks + hash-keten geaudit.

3. **Onafhankelijk van de checklist-status — bevestigd.** `maak_aan` (`service:61`) checkt uitsluitend `_component_bestaat` (404 no-leak) + dubbel (409). **Géén koppeling naar checklist-`%`/lifecycle**; een component kan op elk scoringsniveau klaar verklaard worden (conform ADR-027).

4. **UI vandaag.** De badge/indicator leeft **niet** in `DetailKop #badges`, maar als PrimeVue-`Tag` in **`MigratiegereedheidSectie.vue:125-129`** (`mg-status`; labels `labels.js:314-317`: "Klaar verklaard" / "Nog niet klaar verklaard"), gemount op **ComponentDetail** (`v-if="isChecklistDragend"`, `ComponentDetail.vue:452-458`). De **trigger** staat in de detailkop-`#acties` (`ComponentDetail.vue:319-325`, `klaarverklaar-knop`) en opent een **eigen (bespoke) `Dialog`** met verplichte reden-textarea (`MigratiegereedheidSectie.vue:149-184`). Geen per-rij-badge in de lijst; dashboard toont alleen aggregaat.
   - **Belangrijk precedent:** die dialog toont **nu al een caveat** wanneer nog niet alle vragen beantwoord zijn (`mg-dialog-context`, `:159-165`), en er bestaat al een **"afwijking"-signaal** = *klaar verklaard terwijl de checklist niet compleet is* (`lifecycle ∉ {migratieklaar, geblokkeerd}`) — read-only afgeleid in `dashboard_service` (`klaar_met_afwijking`, `:149-156`) én als lijstfilter (`component_service.py:459-468`) én in-sectie (`mg-afwijking`, `MigratiegereedheidSectie.vue:138-146`). **De nieuwe tenant-norm is een generalisatie van exact dit patroon** — van "checklist compleet" naar "verplichte harde velden bekend".

---

## Blok 2 — De harde velden + hoe LIKARA "leeg" leest

**Bevinding: drie leeg-regimes naast elkaar; de per-component leesbron dekt maar een deel.**

1. **De harde velden op `Component` (`models.py:370-409`) + leeg-semantiek:**

| Veld | Kolom | Leeg-semantiek |
|---|---|---|
| naam / componenttype / **hostingmodel** | NOT NULL | **hostingmodel is NOT NULL-enum mét `onbekend`-waarde** → "leeg" = **sentinel `onbekend`**, niet NULL ⚠ |
| componentrol | NOT NULL, default `interne_applicatie` | nooit leeg (geen gat mogelijk) |
| eigenaar_organisatie_id | nullable | NULL = gat |
| BIV (`biv_beschikbaarheid/integriteit/vertrouwelijkheid`) | nullable | NULL = gat |
| levensfase · bedoeling (`migratiepad`) · complexiteit · prioriteit | nullable, **geen default** (LI040) | NULL = "nog niet vastgelegd" |
| beschrijving | nullable | NULL = leeg |

   Relationele registratie-feiten "over het component" (elders): **verantwoordelijke** (`roltoewijzing.object_id`), **gebruikersgroep** (serving-relatie, bron=component), **bedrijfsfunctie** (`functievervulling.component_id`).

2. **Welke hebben al een registratiegat-signaal** (`registratiegaten_service`): eigenaar (`component_zonder_eigenaar`), verantwoordelijke (`component_zonder_verantwoordelijke` + `object_zonder_roltoewijzing`), BIV (`biv_classificatie_onvolledig`), gebruikersgroep (`component_zonder_gebruikersgroep`), geïsoleerd (`component_geisoleerd`), bedrijfsfunctie (`component_zonder_bedrijfsfunctie`).
   **GEEN signaal:** levensfase · bedoeling · complexiteit · prioriteit · hostingmodel · beschrijving · componentrol. Die vier nullable-oordeelvelden hebben wél een **`*_ontbreekt`-lijstfilter** (LI040, `routes/component.py`), maar **geen per-component badge-detectie**.

3. **Één leesbron per component?** Grotendeels: **`registratiegaten_service.badge_voor_component(session, tid, component_id)`** (`:172-261`) → `{signalen, kritiek, aandacht}`, gebruikt door de frontend via `api.signalering.badgeComponent` (`ComponentDetail.vue:124`, `SignaleringBadge` in de detailkop). **Maar:** (a) die badge **mist de vier nullable-oordeelvelden + de hostingmodel-sentinel** (die zitten er niet in), en (b) `badge_voor_component` en de tenant-brede `registratiegaten()`-`overzicht()` zijn **twee aparte query-paden** die alleen predicaten delen (`_biv_onvolledig`, `_ondersteunt_werk_typen`, `serving_van_component_where`) — geen enkele gedeelde functie. Een norm-toetsing die "welke verplichte velden zijn leeg op dít component" wil, zal **`badge_voor_component` moeten uitbreiden** (met de nu-ongedekte velden) óf een nieuwe per-component afleiding bouwen.

---

## Blok 3 — De tenant-norm: waar zou die leven?

1. **Instelplek.** De **enige** tenant-eigen catalogus vandaag is `checklistvraag` (domeinmodel §5, niet-onderhandelbaar); al het andere is platform-breed. Een per-tenant "verplicht ja/nee per hard veld" is dus **nieuwe tenant-eigen data** en past **niet** op een bestaande config-tabel. Kandidaten (benoemd, niet gekozen):
   - **(a) Nieuwe tenant-scoped tabel** (bv. `component_veld_norm(tenant_id, veld_sleutel, verplicht bool)`), volgens het bestaande RLS-recept — spiegel van `component_klaarverklaring` / `gebruiker_voorkeur`. Consequentie: schema-slice + migratie + RBAC-entiteit + audit-allowlist.
   - **(b) Aanhaken op een generieke per-tenant-settings-laag** — **bestaat niet**: `gebruiker_voorkeur` is per-**gebruiker**, niet per-tenant. Er is geen tenant-brede settings-tabel om op mee te liften. Consequentie: (b) vergt eerst zo'n laag → zwaarder dan (a).
   - **Veld-sleutels** zouden een gesloten code-lijst zijn (de harde velden uit blok 2) — geen catalogus, want het zijn modelvelden, geen tenant-inhoud.

2. **RLS/tenant-isolatie.** Ja, dit is tenant-eigen data → het standaard tenant-tabel-recept dekt het volledig (`ENABLE`+`FORCE ROW LEVEL SECURITY` + `tenant_isolation`-policy + `lk_app`-grants), identiek aan `component_klaarverklaring`. Geen nieuw isolatie-vraagstuk. (Met één tenant nu blijft RLS fundament, geen ontwerponderwerp — likara-ux §DC014.)

3. **Engine-grens (kritiek) — schoon, mits de norm de klaarverklaring gatet, niet de engine.** De norm-toetsing leest componentvelden + de norm en leidt "welke verplichte velden leeg" af → **puur read-only**, precies zoals het bestaande `klaar_met_afwijking` (klaarverklaring × `lifecycle_status`, `dashboard_service:149-156`). De klaarverklaring is zelf al volledig engine-gescheiden (blok 1.2). **`lifecycle_status`/`migratieklaar-de-engine-status` blijft puur checklist-gedreven.** Geen enkele plek waar dit verstrengeld raakt — mits de MVP de norm **niet** aan de score-/lifecycle-herberekening hangt (de norm hangt náást de engine, de consultant beslist). ⚠ Enige oppelet: de engine-borgings-tests (import-afwezigheid) bewegen mee als de norm-service ontstaat.

---

## Blok 4 — De bevestiging + het auditeerbare feit

1. **Bevestig-bouwsteen.** `BevestigVerwijderDialog.vue` bestaat, maar is **danger-only** (rode knop, `severity="danger"`) en wordt uitsluitend voor verwijderen/ontkoppelen gebruikt; er is een **expliciet precedent om 'm NIET te hergebruiken** voor een neutrale/vooruit-bevestiging (`BedrijfsfunctieLijst.vue:1448-1451`: "Bewust GÉÉN BevestigVerwijderDialog"). Voor "deze verplichte velden zijn leeg — toch klaar verklaren?" ligt het **meest voor de hand de bestaande `MigratiegereedheidSectie`-reden-dialog uit te breiden** (die toont nú al een caveat-context bij open checklist-vragen, `:159-165`, plus de verplichte reden) — de norm-gaten worden daar een extra caveat-regel. Een aparte neutrale `Dialog` (het geen-systeem-precedent) is de alternatieve vorm. **Niet** de danger-dialog.

2. **Audit vs. besluit-met-gaten.** De klaarverklaring wordt geaudit (in `AUDIT_TENANT_ENTITEITEN`), maar de centrale audit capture't **uitsluitend mapped columns** (LI035/DC016-mechanisme-feit). De huidige `ComponentKlaarverklaring` heeft **geen veld** voor "welke velden waren open" of "kreeg de gaten voorgelegd en accepteerde toch" — alleen `status`/`reden`/wie/wanneer. Om het rijkere feit te dragen is het **minimale** een **echte kolom** op de klaarverklaring (bv. `open_velden` als `TEXT[]`/`jsonb` + evt. `met_open_velden bool`), die de **snapshot bij verklaren** vastlegt — dan capture't de bestaande audit de kolom automatisch (DC016: "een markering moet een echte kolom zijn"). Géén aparte besluit-tabel nodig; géén tweede audit-mechanisme. De verplichte `reden` blijft.

3. **Één bron voor badge én log — haalbaar, mét één scherpe nuance.** Het gedeelde feit is **(tenant-norm + klaarverklaring)**. Maar badge en log lezen het **verschillend**:
   - **Log/besluit = bevroren snapshot** (`open_velden` op de klaarverklaring op het moment van verklaren) — dit is het historische "consultant X kreeg déze gaten voorgelegd en verklaarde toch klaar".
   - **Badge = live her-afleiding** (norm × de *huidige* veldwaarden). Vult de consultant later een veld aan → de badge dooft **vanzelf** (live), terwijl de bevroren snapshot in de log/het feit **blijft staan**. Dit is precies wat de opdracht in blok 4.3 vraagt, en het is **haalbaar** — maar het betekent dat badge en log **niet dezelfde read** zijn (live vs. frozen). ⚠ **Dit is de belangrijkste ontwerpnuance:** de kernregel "één bron voor badge én log" geldt op het niveau van (norm + feit), niet als "identieke query" — verwar de live-badge niet met de snapshot, anders liegt óf de badge (blijft staan na aanvullen) óf de log (verandert achteraf). Beide moeten uit dezelfde nórm-definitie komen (één norm-leesbron), maar tegen verschillende peildata.

---

## Blok 5 — Verrassingen, breuklijnen, dwarsverbanden

1. **Verhouding tot de backlog — dit is de smalle MVP-voorloper van LI043-1, met een expliciete spanning.**
   - **Beoordelingsgrondslag (OPVOLGPUNTEN LI043-1, ⭐ post-MVP):** dit checkpoint bouwt daar een **smal voorstuk** van — de tenant-norm "verplicht ja/nee per veld" is de kiem van de "tenant-configureerbare grondslag + open-punten-overzicht". **Breuklijn:** de backlog-grondslag is nadrukkelijk een **waarde-norm, geen aanwezigheids-lat** (OPVOLGPUNTEN `:19-23`): *"niet 'is het veld gevuld', maar bv. BIV moet geclassificeerd zijn (niet 'niet geclassificeerd')"* — met de waarschuwing dat een aanwezigheids-lat "het gevaarlijkste geval doorlaat (een placeholder oogt in orde)". De MVP "ja/nee bekend" is precies zo'n aanwezigheids-lat, en **botst op de hostingmodel-sentinel** (`onbekend` is "aanwezig" maar niet "juist"). → De ADR moet expliciet kiezen: scope de MVP bewust op aanwezigheid (en accepteer/benoem de `hostingmodel=onbekend`-doorlaat), of neem de sentinel-uitzondering nu al mee.
   - **L1a ijkpunt (OPVOLGPUNTEN `:89-115`):** het ijkpunt-spoor geldt bewust voor **werk-terugzettende/vernietigende** handelingen; **vooruitgang (afronden) blijft licht, géén ijkpunt**. Klaar verklaren mét open velden is een **vooruit-handeling** → valt volgens L1a in de "lichte" categorie. **Maar** het besloten beeld wil er een **rijk auditeerbaar wilsbesluit** van maken (wélke velden + wie + wanneer + bewust akkoord) — dat is ijkpunt-graad audit op een vooruit-handeling. → Bewuste uitbreiding van L1a's lijn; benoem in de ADR dat dit een uitzondering is op "afronden = licht" (gerechtvaardigd omdat je hier bewust een gat accepteert, niet louter afrondt).

2. **Stille keuzes die zich als besluit voordoen (benoemd, niet opgelost):**
   - **Welke velden "hard" heten** — de code kent geen "hard veld"-begrip; de lijst in de opdracht mengt component-kolommen én relationele feiten (rol/gebruikersgroep/bedrijfsfunctie). Welke velden de norm mág dekken is een ontwerpkeuze, geen gegeven.
   - **Wat "leeg" is voor `hostingmodel`** — NOT NULL-enum met sentinel `onbekend`: een ja/nee-aanwezigheidsnorm ziet `onbekend` als "gevuld". Stille keuze of dat een gat is.
   - **`componentrol`** — NOT NULL met default → nooit leeg; een norm erop is per constructie moot. Stille keuze of het in de veldenlijst thuishoort.
   - **Default-norm meesturen?** — de backlog oppert een "verstandige default-grondslag" (eigenaar/verantwoordelijke/BIV, uit de bestaande kritiek-splitsing). Het besloten beeld zegt hier niets over; komt er een default-norm mee voor een nieuwe tenant, of start die leeg?
   - **Snapshot vs. live** (blok 4.3) — of het badge live her-afleidt of de snapshot toont, is een keuze die de betekenis bepaalt; niet stilzwijgend één van beide nemen.

3. **Wat de ADR anders zou moeten insteken dan het besloten beeld suggereert:**
   - **Waarde-norm vs. aanwezigheid** (breuklijn 1): het besloten beeld zegt "MVP: geen weging, alleen ja/nee". Dat is verdedigbaar als bewuste versimpeling, maar de ADR moet de **sentinel-doorlaat** (`hostingmodel=onbekend`, en later een eventueel BIV-"niet geclassificeerd"-analoog) expliciet benoemen als geaccepteerde MVP-beperking — anders sluipt de "placeholder oogt in orde"-val binnen die LI043-1 juist wil voorkomen.
   - **Leesbron-consolidatie:** de norm-toetsing wil één per-component leesbron, maar `badge_voor_component` dekt de vier oordeelvelden + hostingmodel niet. De ADR moet kiezen: `badge_voor_component` uitbreiden (dan bewegen de signalering-consumenten mee) of een aparte norm-afleiding naast de badge (twee bronnen — spanning met "één bron").
   - **Snapshot-kolom** (blok 4.2) als het minimale schema-anker; badge = live her-afleiding tegen dezelfde norm.

---

*Einde rapport. Niets gewijzigd/gemigreerd/gecommit. Wacht op de PNA.*
