# ADR-020 — Leverancier- en contractregister (registratief; koppeling applicatie ↔ contract)

**Status**: Aanvaard (CD006-sessie)
**Datum**: juni 2026
**Context-ADR's**: ADR-009 (BWB-ontvlechtingsmodule — applicatie-/checklist-datamodel),
ADR-012 (tweelaags rollenmodel platform/tenant) + Addendum A (`CHECKLISTCONFIG`),
ADR-019 (configureerbare antwoordopties — optie-catalogus-patroon),
ADR-013/016 (lifecycle-/blokkade-engine — wordt door dit ADR **niet** geraakt).

## Context

De applicatie-inventaris kent de checklistcategorie **8 · Contractuele positie** (9 vragen,
score `ja/deels/nee/nvt`). Bij inspectie blijkt die categorie een **gereedheidsoordeel** in de
ontvlechtingscontext: "is splitsing tussen Tiel en BWB contractueel mogelijk?", "stranden er
minimum-afnameverplichtingen bij uittreding?", "is de leverancier bereid mee te werken aan
migratie?". Die scores **voeden de lifecycle-/blokkade-engine** (ADR-013/016) — het is een
meetinstrument, geen feitenadministratie.

Wat ontbreekt is de **feitelijke vastlegging**: welke leveranciers er zijn, welke contracten met
die leveranciers bestaan (incl. mantel-/deelcontracten), wat een contract dekt en op welk
kostenmodel het rust, en onder welk contract een applicatie valt of is aangeschaft. Dit is
**puur registratie**: het legt de primaire uitgangspunten vast en wordt **nooit** gebruikt voor
financiële, juridische, contractuele of besturende verwerking — geen berekening, geen
signalering, geen afgeleide status. Het voedt de engine niet.

Het feitenregister en checklistcategorie 8 zijn dus fundamenteel verschillend van aard
(feit vs. oordeel) en worden gescheiden gehouden (zie Besluit 9).

## Besluit

### Datamodel — drie tenant-scoped entiteiten + één koppeltabel

1. **`leverancier`** (tenant-scoped, RLS via `cd_app`, expliciet `tenant_id`-filter, conform de
   applicatie-CRUD-referentie uit P5/OP-6). Velden:
   - `naam` (verplicht);
   - **minimaal adres**: `straat_huisnummer`, `postcode`, `plaats` (alle optioneel);
   - **contactgegevens** (één set, plat op de leverancier): `contactpersoon`, `telefoon`,
     `mobiel`, `email` (alle optioneel);
   - `omschrijving` (vrije tekst, optioneel).
   Geen aparte contactpersonen-tabel (één contact volstaat; 0..n is een latere uitbreiding).

2. **`contract`** (tenant-scoped). Velden:
   - `leverancier_id` → FK `leverancier` (verplicht);
   - `contracttype` enum **`{mantelcontract, deelcontract, los_contract}`** (verplicht);
   - `mantelcontract_id` → self-FK `contract` (nullable; **verplicht en alleen toegestaan** bij
     `contracttype = deelcontract`);
   - `contractnaam` (verplicht);
   - `extern_contract_id` — ID uit het eigen contractmanagementsysteem (vrije tekst, optioneel;
     geen integratie/validatie);
   - `leverancier_contract_id` — kenmerk dat de leverancier aan het contract geeft (vrije tekst,
     optioneel);
   - `begindatum`, `einddatum`, `vernieuwingsdatum` (datums, **puur registratief — geen afgeleide
     logica, geen signalering**);
   - `omschrijving` (korte omschrijving, optioneel);
   - `toelichting` (vrije tekst, optioneel — o.a. plek voor kostenmodel-context als aantekening).

3. **Hiërarchie-invarianten** (max. **2 lagen**, besloten):
   - alleen een `mantelcontract` mag onderliggende contracten hebben;
   - een `deelcontract` heeft zelf **nooit** deelcontracten (geen recursie/boom — geen
     cyclus-/dieptebewaking nodig, alleen deze 2-laags-regel);
   - een `deelcontract` **erft de leverancier van zijn mantel**: `leverancier_id` is gelijk aan
     dat van `mantelcontract_id` en wordt afgedwongen. Wijzigen van de leverancier op een mantel
     met deelcontracten breekt de invariant en wordt geweigerd/bewaakt.

4. **Dekking en kostenmodel** als **twee orthogonale, classificerende dimensies** op het contract,
   elk **0..n** uit een beheerbare optie-catalogus (zie Besluit 6). Gemodelleerd als
   M:N-koppeltabellen naar de catalogus (`contract_dekking`, `contract_kostenmodel`) i.p.v. een
   jsonb-array, zodat de overzichten relationeel filterbaar zijn ("toon alle per-inwoner-
   contracten"). Het zijn **tags** — er hangen geen waarden/parameters onder (geen p, q, tarief,
   inwoneraantal; zie Niet in scope).

5. **`applicatie_contract`** — koppeltabel (tenant-scoped). Velden:
   - `applicatie_id` → FK `applicatie`;
   - `contract_id` → FK `contract`;
   - `relatie_rol` → uit de beheerbare rol-catalogus (Besluit 6), **precies één, verplicht**.
   - **`UNIQUE(tenant_id, applicatie_id, contract_id)`**: dezelfde applicatie hangt hoogstens
     één keer aan hetzelfde contract.
   Eén applicatie kan aan **meerdere** contracten hangen. Het "valt-onder"-/aanschafcontract is
   **conventie via een rol-optie** (bv. rol `valt_onder`), niet structureel afgedwongen — geen
   apart `primair_contract_id`, geen harde constraint op één primaire koppeling per app.

### Configuratie — drie beheerbare catalogi (ADR-019-patroon)

6. **Dekking, kostenmodel en relatie-rol** zijn elk een **beheerbare optie-catalogus**, in de
   geest van ADR-019: stabiel `optie_sleutel`, `label`, `volgorde`, `actief`. Bewerken =
   **soft-deactiveren** + nieuwe optie toevoegen; **nooit hard verwijderen of hernummeren**, zodat
   bestaande koppelingen/registraties resolvebaar blijven. Voorstel: **één relationele tabel**
   `contractconfig_optie(dimensie, optie_sleutel, label, volgorde, actief)` met `dimensie`-enum
   `{dekking, kostenmodel, relatie_rol}` — eleganter dan drie aparte tabellen, zelfde patroon.
   De catalogi worden mee-geseed met een redelijke default-set (o.a. dekking: licentie-aanschaf /
   onderhoud-support / hosting; kostenmodel: SaaS p×q / volume / per-inwoner; relatie-rol:
   valt_onder / onderhoud / hosting), uitbreidbaar zonder migratie.

   **Bewuste afwijking t.o.v. ADR-019** (geverifieerd in Fase A): `checklistvraag_optie` heeft één
   optieset *per vraag*; hier is gekozen voor **één tabel `contractconfig_optie` met een
   `dimensie`-discriminator** i.p.v. drie aparte tabellen. De geest is identiek (stabiele sleutel,
   soft-deactivate, identieke grants); alleen de vorm verschilt, omdat de drie dimensies een vaste,
   kleine set zijn (geen per-rij-configuratie zoals bij de 89 checklistvragen).

7. **Beheer is platform-breed** (B1, besloten), conform de hele sessie-lijn ("ADR-019-patroon").
   De catalogi zijn platform-brede referentiedata, beheerd door de **platform-beheerder** via een
   nieuwe `PlatformEntiteit` (analoog aan ADR-012 Addendum A `CHECKLISTCONFIG`):
   **`CONTRACTCONFIG`** (B2, besloten), formeel als **ADR-012 Addendum B** (rechten: beheerder
   `{L,A,W}`, operator `{L}`, geen `V` want deactiveren = `W`). De catalogus kent **geen RLS**;
   `cd_app` SELECT-only, `cd_platform` CRUD (Besluit 8). Tenant-data blijft volledig RLS-scoped.

### Grants / RLS

8. Tenant-data (`leverancier`, `contract`, `contract_dekking`, `contract_kostenmodel`,
   `applicatie_contract`): volledige CRUD voor `cd_app` onder RLS, zelfde patroon als
   `applicatie`. De catalogus (`contractconfig_optie`): `cd_app` **SELECT-only**, `cd_platform`
   CRUD — identiek aan de `checklistvraag_optie`-grants uit ADR-019 fase 2A.

### Relatie tot checklistcategorie 8

9. Het register en checklistcategorie 8 blijven **gescheiden, onafhankelijke entiteiten** (optie
   "b"). **Geen datakoppeling**: het register leidt geen scores af, vult geen checklistvragen
   voor, en **voedt de engine niet**. Het enige toegestane raakvlak is **contextueel en
   eenrichtings op UI-niveau**: een **read-only context-paneel** dat bij een applicatie de
   geregistreerde contracten/leveranciers naast categorie 8 toont. Vragen 8.2 (contractvorm),
   8.3 (looptijd) en 8.6/8.7 (volume/minimum-afname) raken inhoudelijk dezelfde begrippen, maar
   dat is *oordeel vs. feit* — bewust niet automatisch uit het register beantwoorden (dat zou
   besturend worden).

### Grondprincipe

10. **Puur registratie, nooit besturend.** Geen contractstatus (afgeleid of handmatig), geen
    bedragen/valuta/looptijd-als-getal, geen signalering, geen berekening, geen afgeleide
    lifecycle/blokkade. Dit ADR is daarmee **volledig additief**: nieuwe tabellen + één additieve
    migratie, geen wijziging aan bestaande tabellen, logica of de gevalideerde engine.

## Gevolgen

- De inventaris krijgt een **feitenlaag** naast het gereedheidsoordeel: leverancier → contracten
  (mantel/deel) → applicaties, met dekking, kostenmodel en koppelrol.
- Overzichten (afgeleide views, read-only): app → gekoppelde contracten (met rol); mantel →
  deelcontracten; contract → welke apps; leverancier → contracten → apps.
- De engine en alle bestaande scores blijven ongemoeid; **nul regressierisico** op
  blokkade/lifecycle.
- Catalogi zijn uitbreidbaar zonder migratie; nieuwe dekking-/kostenmodel-/rol-opties zijn
  beheerderswerk, geen release.

## Beslissingen (alle besloten — CD006-sessie)

- **B1 · Reikwijdte catalogi — BESLOTEN: platform-breed.** `contractconfig_optie` is
  platform-referentiedata (geen RLS op de catalogus; `cd_app` SELECT-only, `cd_platform` CRUD).
  Tenant-data (leverancier/contract/koppelingen) blijft volledig RLS-scoped. Zie Besluit 6/7/8.
  Een eventuele per-tenant-override is een latere uitbreiding bovenop deze platform-brede basis.
- **B2 · Nieuwe `PlatformEntiteit` — BESLOTEN: `CONTRACTCONFIG`** als ADR-012 Addendum B
  (beheerder `{L,A,W}` / operator `{L}` / geen `V`). Eén entiteit dekt alle drie de dimensies
  (dezelfde platformbeheerder beheert dekking/kostenmodel/relatie-rol).
- **B3 · Adresvelden — BESLOTEN: `straat_huisnummer`, `postcode`, `plaats`** (geen `land`;
  leveranciers NL-only binnen BWB-ontvlechting).
- **B4 · Datumvalidatie — BESLOTEN: géén validatie.** Begin-/eind-/vernieuwingsdatum vrij
  invulbaar; geen afgeleide of blokkerende logica, ook geen `einddatum ≥ begindatum`-hint
  (strikt registratief).

## Niet in scope

- Elke **financiële, juridische, contractuele of besturende verwerking** — voorgoed uitgesloten.
- **Parameterwaarden** onder een kostenmodel (p, q, tarief, inwoneraantal, bedragen,
  staffeltabellen).
- **Contractstatus** (afgeleid of handmatig) en elke vorm van **aflopen-/verlengingssignalering**.
- **>2 lagen** mantel/deel; recursieve contractboom.
- **Meerdere contactpersonen** per leverancier (0..n contacttabel — latere uitbreiding).
- **Kostenmodel per dekkingsregel** (kostenmodel hangt op contractniveau, 0..n).
- **Datakoppeling** tussen register en checklistcategorie 8 (alleen read-only UI-context).
- Een structureel afgedwongen **primair contract** per applicatie ("valt-onder" = rol-conventie).

## Alternatieven overwogen

- **Twee aparte tabellen voor hoofd- en deelcontract.** Verworpen: één `contract`-tabel met
  `contracttype` + self-FK is eenvoudiger, dwingt de leverancier-invariant op één plek af en houdt
  de overzichten uniform.
- **Kostenmodel als gestructureerde parameters (jsonb schema-per-model).** Verworpen op basis van
  de scope-begrenzing: puur registratie, nooit rekenen. Parameters bestaan alleen als je ermee
  wilt rekenen/sturen.
- **Dekking en kostenmodel als één vinkjeslijst.** Verworpen: het zijn orthogonale assen; samen­
  voegen maakt filteren ("alle per-inwoner-contracten") onmogelijk.
- **Relatie-rol als 0..n per koppeling.** Verworpen: rol is een eigenschap van de koppeling; één
  rol per koppeling houdt het "valt-onder"-overzicht eenduidig (twee rollen = twee koppelingen,
  hier uitgesloten door de uniciteit).
- **Register koppelen aan / laten voeden van checklistcategorie 8.** Verworpen: breekt het
  "nooit besturend"-principe en vermengt feit met oordeel.
- **Eén contract per applicatie.** Verworpen: in de praktijk hangen aanschaf-, onderhouds- en
  hostingcontracten aan dezelfde app.
