# Architecture Decision Records — LIKARA

ADR's leggen significante architectuur- en scope-beslissingen vast. Eén bestand
per beslissing, oplopend genummerd, nooit hergebruikt of verwijderd (vervallen
beslissingen krijgen status `Vervallen` met verwijzing naar de opvolger).

## Conventie

- Bestandsnaam: `ADR-NNN_kebab-case-titel.md`
- Status: `Voorgesteld` → `Aanvaard` → (`Vervangen door ADR-XXX` | `Vervallen`)
- Vaste secties: **Status/metadata**, **Context**, **Besluit**, **Gevolgen**,
  **Alternatieven overwogen**
- Operator en platformnaam nooit hardcoden in code — ADR's mogen ze
  uiteraard benoemen.

## Register

| ADR | Titel | Status |
|---|---|---|
| ADR-001 | Platform-architectuur en module-structuur | Aanvaard |
| ADR-006 | Audit-trail: append-only wijzigingsspoor, app-niveau capture, per-tenant hash-keten | Aanvaard, geïmplementeerd (Fase A–E) |
| ADR-009 | BWB-ontvlechtingsmodule — scope en datamodel | Aanvaard |
| ADR-011 | Deploy- en migratiestrategie: aparte init-container | Aanvaard |
| ADR-012 | Tweelaags rollenmodel: platform- en tenant-rollen met strikte scheiding | Aanvaard |
| ADR-013 | Lifecycle-herberekening (Model A): afgeleide blokkades + deterministische status | Aanvaard |
| ADR-014 | Canoniek foutformaat: 401 gelijktrekken, 422 bewust native | Aanvaard |
| ADR-015 | Refresh-token-subsysteem: Keycloak-gedelegeerd, Redis-opslag | Aanvaard |
| ADR-016 | Blokkade-`opgelost` volledig afgeleid (amendeert ADR-013 B1) | Aanvaard |
| ADR-017 | Server-side sorteerbare keyset-paginering (allowlist + zelfbeschrijvende cursor) | Aanvaard |
| ADR-018 | Relatievisualisatie: gefocuste ego-graaf, geen graaf-dependency | Aanvaard |
| ADR-019 | Configureerbare antwoordopties per checklistvraag (additioneel veld, score behouden) | Aanvaard |
| ADR-012 Addendum A | `PlatformEntiteit.CHECKLISTCONFIG` | Aanvaard |
| ADR-020 | Leverancier- en contractregister (registratief; koppeling applicatie ↔ contract) | Aanvaard |
| ADR-012 Addendum B | `PlatformEntiteit.CONTRACTCONFIG` | Aanvaard |
| ADR-021 | Component-herfundering: supertype Component + landschapsgraaf (subtype `Applicatie` ontbonden in LI059 — applicatie = componenttype) | Aanvaard — gerealiseerd t/m LI059 |
| ADR-012 Addendum C | `PlatformEntiteit.COMPONENTCONFIG` | Aanvaard |
| ADR-022 | Beoordelingsprofiel / checklist per componenttype (incl. Wijziging W1 — tenant-eigendom vragenset) | Aanvaard — gerealiseerd t/m LI059 |
| ADR-023 | ArchiMate-uitlijning: element-identiteit, getypeerd relatiemodel, migratielaag | Aanvaard (besluit), implementatie in deze opdracht |
| ADR-037 | Verantwoordelijke per checklistantwoord (afdeling-dan-persoon; vervangt vrije-tekst `eigenaar`, blokkade-eigenaar afgeleid) | Aanvaard — Pass 1 gerealiseerd (schema-gate), Pass 2 volgt |
| ADR-038 | Gebruikersgroep-consolidatie: groep hoort altijd bij een organisatie; intern/extern-kenmerk op organisaties; `burger` partij-aard verwijderd (herziet ADR-036/036a) | Besloten — bouw in slices |
| ADR-039 | Aanspreekpunt van een partij als verwijzing naar een geregistreerde persoon (vervangt vrije-tekst `contactpersoon`; alleen op organisatie/externe partij; search-first ter-plekke-aanmaken) | Besloten — gerealiseerd (schema-gate) |
| ADR-025 | Landschapskaart (applicatie-centrische praatplaat) | Superseded door ADR-040 |
| ADR-034 | Lagenweergave (swimlane) als architectuur-lens — Lagen als derde kaart-weergave incl. rolbanen + proceslaan | Geland (LI036) — besluit 1 herzien (Cytoscape preset i.p.v. HTML/CSS), besluit 4 buiten scope; proces-diepte bewust open |
| ADR-040 | Kaart-herbouw: twee gerichte weergaven + object-centrische praatplaat-motor | Deels geland — Fase 1 (V034) + V035-correcties + LI036 (derde weergave Lagen, interactie-basis, set-actie-herziening, organisatiebalk); vervolgfasen open |
| ADR-041 | Persoonlijke voorkeuren: "onthoud als mijn standaard" (per-gebruiker voorkeur-laag; kijkfilter, nooit invoerregel) | Gerealiseerd (V035) |
| ADR-042 | Procesregister en component-in-proces-koppeling (nestbare procesboom; koppelregel component/proces/applicatiefunctie; roll-up als kijklaag) | Gerealiseerd (V036) — alle 5 slices; herijkt door ADR-043 (procesregister geparkeerd/verborgen in MVP) |
| ADR-043 | Bedrijfsfunctie als logische ruggengraat (herijking ADR-042): eigen functie-as (ArchiMate BusinessFunction), referentiemodel als eerste-klas begrip (GEMMA = instantie 1), bronsleutel als identiteit, vervallen ≠ verwijderen | Besloten (LI038; acht subknopen beslist LI039 — o.a. kale koppeling zonder applicatiefunctie, koppelen op elk niveau, vervallen = zichtbaar + niet-koppelbaar, procesregister volledig uit beeld in MVP) — gate 1a geland; deels herijkt door ADR-044 (plaatsing als eerste-klas feit) |
| ADR-044 | Plaatsing als eerste-klas feit (herijking ADR-043): functieboom = aggregation-plaatsingen (meerdere ouders mogelijk, geen rangorde), koppeling → (component, plaatsing) met grof-vervangt-door-fijn, "geen systeem — vastgesteld" als bevinding, gap-signaal per plaatsing | Besloten (LI039) — bouw volgt (gate 1b import leest plaatsingen 1-op-1) |
| ADR-045 | "Ondersteunt werk" als eigenschap van het componenttype: beheerbare catalogus-vlag `ondersteunt_werk` (ruim: incl. fileshare/client_software), picker weert vooraf + scope-regel (uitleg-bouwsteen verworpen), flip = zichtbaarheid nooit veldwerk, werkvoorraad i.p.v. speurtocht, afgeleid signaal; incl. 422-bugfix componenttype-aanmaak | Besloten (LI040) — slice 1 gerealiseerd (`87dc120`); besluiten 7–8 landen in gate 2/3 |
| ADR-046 | Levensfase, bedoeling en uitstap per gebruiker: levensfase op het component (nooit afgeleid), bedoeling = één plek (migratiepad; `uitfaseren` eruit, plateau-dispositie vervalt — Weg B), stand per gebruiksrelatie op het grove organisatiegebruik (incl. de ontbrekende invoerroute), tranche = naam+volgorde (geen planningstool; plateau ≠ tranche), zwaarte afgeleid ("geen gebruikers meer", amber, nooit rood), liegend gebruik-signaal mee-gerepareerd | Besloten (LI040) — bouw volgt |
| ADR-049 | De component-functie-koppeling: het adres van de plek + verdringing als leesregel (grof-vervangt-door-fijn bij het lezen; één gedeelde afleiding `dekking_overzicht`) | Gerealiseerd (LI041; borging `test_functievervulling_adr049`) |
| ADR-050 | Wie registreert, corrigeert: de rollengrens knipt op het onderwerp — registratie-feit → `WIJZIGEN` (medewerker), landschapsobject → `VERWIJDEREN` (beheerder); classificatie in `rbac.py`, geen per-route-regel | Gerealiseerd (LI041; borging `test_rollengrens_adr050`) |
| ADR-051 | Het gap-signaal per plek: wat draagt deze plek? (plek-standen `plek_standen`, "fijn verdringt grof bij lezen"; het noodgreep-oordeel zit op de plek, niet in het componenttype) | Gerealiseerd (LI041–LI044; borging `test_gapsignaal_adr051`) |
| ADR-052 | Tenant-norm voor harde componentfeiten + verrijkte migratieklaar-verklaring: per hard feit verplicht-ja/nee (MVP, geen weging), "compleet = vastgesteld ≠ gevuld" (sentinel telt niet mee), "bewust geen" voor koppelingen/contract, norm = lat niet poort, bevestiging + auditeerbaar akkoord alléén bij afwijking, badge (live) + log (snapshot) uit één norm-definitie; engine ongemoeid (smalle MVP-voorloper van de beoordelingsgrondslag LI043-1) | Aanvaard — slices 1–4c gebouwd (LI044/LI045); 4a/4b/beheerscherm zie ADR |
| ADR-053 | Archiefwet als hard componentfeit: eigen component-enum `{ja, bewust_geen}` (null = nog niet gekeken), gebruikerstaal "Archiefwet"; bewaartermijn bewust buiten scope (volgt uit zaaktype × resultaat) | Voorstel — vorm besloten, bouw ná ADR-052 slice 4a/4b (MVP) |
| ADR-054 | Eén ingang naar een detailscherm: de kaart vertelt, het component verandert — gedeelde `detailRoute` + dekkingsscan, aanleiding in de URL (deelbaar/herstelbaar), geen route zonder landing, veld-anker markeert (geen bewerk-modus), "de bezoeker wint", binnenkomst-regel beginscherm + eerlijke verdwenen-selectie | Aanvaard — gebouwd (LI046) |
| ADR-055 | De gebruik-verfijning ("welke afdeling gebruikt dit") is component-breed: `ondersteunt_werk` (ADR-045) is de grens, niet het type `applicatie` — herziet een ongegronde applicatie-binding die een overblijfsel bleek van de opgeheven `applicatie`-subtabel; geen bepaling verandert (signaal/norm/snapshot/contracttoets ongewijzigd), alleen wie de vraag kán beantwoorden; geen schemawijziging; signaal 12 → 11 componenten (de databaseserver valt af — die stond open terwijl er niets te doen viel) | Besloten (LI047) — **gebouwd (LI047)** |

> **Component-focus-herfundering (LI057–LI059, migraties 0045–0047):** `migratiepad/complexiteit/prioriteit`
> zijn component-breed, de `applicatie`-subtabel is gedropt en de applicatie-**facade** (routes/service/
> schema + `Entiteit.APPLICATIE`/audit-allowlist/objecthistorie-tak) is volledig opgeheven. Een component
> met `componenttype='applicatie'` ÍS de applicatie — `component` is de enige bron in data/API/RBAC/audit.
> Zie de slotsecties "Eindstaat" in ADR-021 en ADR-022.

ADR-002 t/m ADR-005, ADR-007, ADR-008 en ADR-010 zijn gereserveerd (zie `CLAUDE.md` →
ADR-referentie) en worden geschreven wanneer de betreffende beslissing speelt.
