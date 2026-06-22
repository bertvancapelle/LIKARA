# ADR-030 — Contract-dekking per contract↔component-band

**Status:** Voorstel (open subknopen — nog niet besloten, niet gebouwd).
**Datum:** 2026-06-22 (voorstel)
**Relatie:** Bouwt voort op **ADR-023** (unified relatiemodel + relatie-kenmerken als beheerbare
catalogus, OK-2) en de **relatiekenmerk-vocabulaire-catalogus** (`RelatieKenmerkDimensie` /
`relatiekenmerk_optie`, ADR-023 Fase E). Verwant aan **ADR-023a** (meervoudige flow-koppelingen):
hetzelfde "een-kenmerk-hoort-bij-de-relatie, niet bij het ding"-patroon. Raakt **ADR-020**
(leverancier-/contractregister), waar `dekking` nu contract-breed is gemodelleerd.
**Invariant (ongewijzigd):** contract en dekking zijn **registratief** — ze raken de score-/
lifecycle-engine niet. Score blijft de enige lifecycle-driver.

---

## Context / aanleiding

Vanuit de gebruiker: **één contract dekt voor verschillende componenten verschillende zaken.**
Een raamovereenkomst kan voor component A hosting én onderhoud dekken, en voor component B alleen
levering. Dat is geen randgeval maar de normale werkelijkheid van een gedeeld contract over een
landschap.

Vandaag kan dat niet worden vastgelegd. De feitelijke situatie (read-only vastgesteld):

- **Dekking is contract-breed.** `dekking` woont in tabel `ContractDekking`
  (`models.py` — `FK contract_id → contract.id`, `UNIQUE(tenant_id, contract_id, optie_sleutel)`);
  ze wordt contract-breed geladen (`contract_service.py` — `_laad_tag_sleutels(..., contract_id,
  "dekking")`) en als `ContractRead.dekking: list[OptieRef]` getoond. Eén dekkingsset geldt dus voor
  **alle** componenten aan het contract.
- **De band kan al per component verschillen.** De contract↔component-koppeling is een
  `association`-relatie in het unified relatiemodel (bron=component, doel=contract); ze draagt nu
  `relatie_rol` als per-band-kenmerk (in `relatie.kenmerken`). Dat kenmerk verschilt al per component
  — bevestigd in de live data (één contract, drie componenten, drie eigen rollen).
- **Eén contract aan meerdere componenten kan al** (live bevestigd: o.a. "CivData SaaS-overeenkomst"
  → 3 componenten). De partiële uniciteit `UNIQUE(tenant, bron, doel, type) WHERE type <> 'flow'`
  (ADR-023a, migratie 0039) staat dat toe: verschillende `bron_id` (component) op dezelfde
  `doel_id` (contract).

**De beperking is dus puntsgewijs:** dekking hangt aan het contract en niet aan de band, terwijl het
inhoudelijk een eigenschap van de **band** is — net zoals `relatie_rol`. Berts voorbeeld
(A: hosting+onderhoud; B: alleen levering) kan vandaag niet.

**Migratie-relevantie.** Bij een ontvlechting wil je per component weten wát een contract daar dekt —
niet alleen welke rol de band heeft, maar of hosting/onderhoud/levering daar onder dit contract
geregeld is. Dat stuurt overdracht en heronderhandeling per component.

---

## Besluit (kern — voorstel)

**Dekking wordt (ook) een per-band-kenmerk op de `association`-relatie contract↔component**, conform
het bestaande kenmerk-patroon: een beheerbare waardenlijst, gevalideerd tegen de catalogus, gedragen
in `relatie.kenmerken` (jsonb) — net zoals `relatie_rol` dat al doet. **Geen nieuwe losse tabel** als
het kenmerk-patroon structureel volstaat; dekking-per-band is meervoudig (0..n opties per band), wat
in `kenmerken` als lijst past, analoog aan hoe relatie-kenmerken al beheerd worden (ADR-023 OK-2,
`RelatieKenmerkDimensie`).

**Waarom dit structureel juist is.** Dekking beschrijft *wat dit contract bij dit component regelt* —
dat is per definitie een eigenschap van de **relatie** tussen contract en component, niet van het
contract los. Zolang dekking op het contract zit, kan ze niet zeggen wat de gebruiker bedoelt zodra
één contract meerdere componenten raakt. Dit is exact het patroon van ADR-023a (flow-meervoud) en van
`relatie_rol`: een beschrijvend kenmerk dat bij de band hoort. De band bestaat al, draagt al
kenmerken, en heeft al de catalogus-/validatie-machinerie — de uitbreiding sluit aan in plaats van een
nieuw mechanisme te introduceren.

---

## DE centrale open subknoop (te beslissen door Bert — geen keuze geforceerd)

**Blijft de contract-brede dekking (`ContractDekking`) bestaan als "algemene/default dekking" NAAST
de per-band-dekking, of VERVANGT de per-band-dekking die volledig?**

### Optie A — Vervangen (per-band wordt de enige bron)
Alle dekking verhuist naar de banden; een eventueel contract-totaal wordt **afgeleid** (de unie/het
overzicht over alle banden).

- **Voor:** één plek voor de waarheid, geen dubbele bron, geen "welke is leidend"-vraag. Zuiverste
  uitwerking van "kenmerk hoort bij de relatie".
- **Tegen:** verlies van een **los contract-breed dekkingsoverzicht** dat losstaat van componenten
  (een contract zónder gekoppelde componenten heeft dan nergens dekking). Vereist een **datamigratie**
  van bestaande `ContractDekking`-rijen naar de banden — en een regel voor contracten die (nog) geen
  band hebben (dekking zou dan tijdelijk nergens leven).

### Optie B — Naast elkaar (contract-breed blijft als algemene dekking, band kan specifieker)
Het contract houdt zijn algemene dekking (`ContractDekking`); de band kan een **specifiekere/
afwijkende** dekking dragen.

- **Voor:** rijker; een contract kan een algemene dekking declareren én per component verbijzonderen;
  contract zonder componenten houdt betekenis.
- **Tegen:** **dubbele bron** → expliciete regels nodig (wat is leidend bij conflict; is band-dekking
  een aanvulling op of een vervanging van de contract-dekking; hoe toon je beide zonder de gebruiker
  te verwarren). Risico op interpretatieverschil tussen contractdetail en component→contract-weergave.

> Beide opties zijn eerlijk beschreven; **de keuze maakt Bert later.** Pas ná die keuze is het model
> en de migratie te bepalen.

---

## Overige open subknopen

1. **Migratie van bestaande `ContractDekking`-data.** Bij Optie A: bestaande rijen verdelen over de
   banden van het contract (één set → gekopieerd naar elke band? of vereist menselijke verbijzondering?
   wat met contracten zonder band). Bij Optie B: bestaande rijen blijven staan; geen verplichte migratie.
2. **Catalogus-dimensie.** Dekking is nu de dimensie `dekking` in `ContractConfigDimensie` /
   `contractconfig_optie` (contract-configuratie). Als dekking een **relatie-kenmerk** wordt, hoort de
   waardenlijst conceptueel thuis in de **relatiekenmerk-catalogus** (`RelatieKenmerkDimensie` /
   `relatiekenmerk_optie`, waar `relatie_rol`/`dispositie`/`beheerrol` al leven). Open: de bestaande
   `dekking`-dimensie hergebruiken (geen verhuizing), of de waardenlijst mee laten verhuizen conform
   de consistentie-opruim die `relatie_rol` al doormaakte. **Geen schemabesluit nu** — alleen genoteerd.
3. **UI-impact.** Per-band-dekking moet zichtbaar worden in **twee** weergaven: het contractdetail
   (dekking per gekoppeld component i.p.v. één contract-brede set) en de **component→contract-weergave**
   (`ContractVoorComponent`), die nu wél `relatie_rol` toont maar géén dekking. Vormgeving volgt het
   bestaande kenmerk-/labelpatroon (catalogus-gelabeld, historische sleutels blijven leesbaar).
4. **RBAC/audit.** Conform bestaand patroon: muteren van band-kenmerken via de bestaande
   relatie-/koppeling-entiteit en -rollen; de wijziging wordt geauditeerd via de append-only
   audit-trail (ADR-006-capture-allowlist, zoals bij de andere relatie-kenmerken).

---

## Invarianten

- **Engine onaangeroerd / score blijft enige lifecycle-driver.** Contract en dekking — contract-breed
  óf per band — zijn registratief; ze voeden de engine niet en muteren geen lifecycle/score/blokkade.
- **Relaties expliciet en toerekenbaar** (ADR-023 Besluit 8): dekking-per-band is een expliciet,
  per-koppeling toerekenbaar kenmerk — geen impliciete afleiding.
- **Structureel boven conventioneel:** het kenmerk hoort machinaal bij de band (gevalideerd tegen de
  catalogus in `relatie.kenmerken`), niet alleen bedoeld als losse tag.

---

## Gevolgen + bouw-fasering (indicatief — pas ná besluitvorming)

De ADR-023a flow-meervoud-keten dient als **blauwdruk**: zelfde patroon (kenmerk bij de band,
partiële/relationele uitbreiding, registratief, engine-onaangeroerd, gate-discipline per slice).

Indicatieve fasen (volgorde bevestigen ná de keuze A/B):

1. **Model + catalogus** — dekking als band-kenmerk in `relatie.kenmerken`, gevalideerd tegen de
   (her)gebruikte catalogus-dimensie; bij Optie A inclusief datamigratie van `ContractDekking`.
2. **Service + API** — band-dekking schrijven/lezen op de contract↔component-koppeling; contract-breed
   overzicht afgeleid (Optie A) of naast elkaar met de besloten regel (Optie B).
3. **UI** — per-band-dekking in contractdetail + component→contract-weergave; bestaand label-patroon.
4. **Borging** — engine-onaangeroerd (offline import-afwezigheid + live geen-mutatie), audit, tests.

> **Faseringsdiscipline (n≥2-generalisatie).** Dit wordt **pas opgepakt ná de lopende
> koppeling-keten** (meervoudige koppelingen / ADR-023a Fase 2). Eerst het ene concrete geval volledig
> afmaken; pas daarna deze tweede toepassing van hetzelfde patroon generaliseren — niet midden in de
> lopende werktree invlechten.
