# ADR-025 — Landschapskaart (applicatie-centrische praatplaat)

**Status:** **Superseded door ADR-040** (Kaart-herbouw: twee gerichte weergaven + object-centrische praatplaat-motor). Historisch: Geland — DC013 (V013); doorbouw v4 (diepte/koppelingsdetails/migratieplaatsing) DC013.
**Datum:** 2026-06-16 (voorstel) · bijgewerkt 2026-06-19 (werkelijke bouwstand)
**Relatie:** Leeslaag bovenop het getypeerde relatiemodel (ADR-023). Leunt voor ring 2 op het
partijenregister (ADR-024). **Expliciet onderscheiden van Fase G (Open Exchange export).**
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt.
Puur read-only, afgeleid (lichtgewicht profiel-/blokkade-handle, géén engine-import).

---

## Context / aanleiding

ArchiMate- en EA-tooling is gebouwd voor de architect: formele notatie, alle elementtypen,
technische relatietermen. Wat in veel organisaties juist **mist** is een **begrijpelijke
praatplaat** voor een niet-technisch publiek (teamleider, proceseigenaar, bestuurder): inzage in
de werking van het landschap zonder jargon. Dit ADR vult dat gat.

**Onderscheid met Fase G.** De Open Exchange export (ADR-023, geparkeerd) dient
*architect-interoperabiliteit*: het model naar Archi/een EA-tool. Dat levert juist het technische
beeld dat we hier willen vermijden. De Landschapskaart is een **aparte inzicht-/communicatielaag**
bovenop dezelfde data, met een ander publiek. Beide mogen bestaan; ze zijn niet hetzelfde.

De onderliggende data was er al: getypeerde elementen, getypeerde relaties (waaronder koppelingen
en `draait_op`) en — met ADR-024 — de beheerpartijen. De **Koppelingenkaart** was de kiem; die is
in DC013 **vervangen** door de Landschapskaart.

---

## Wat is gebouwd (werkelijke stand, DC013)

Interactieve kaart op **Cytoscape.js** (`LandschapskaartView.vue`), drie modi:

- **Ego-view** (concentric layout): één centrum, vier ringen — applicaties (flow),
  beheerorganisatie (roltoewijzing), contracten (association), infrastructuur (assignment);
  ringen aan/uit; klik op een node = hercentreren; ArchiMate-laag zichtbaar via het type.
- **Impact-view** (cose layout): migratieset multi-select; blauw = in-set, oranje = raakvlak,
  oranje dikke lijn = grensoverschrijdende koppeling; samenvatting-teller
  ("X in set · Y raakvlakken · Z grensoverschrijdend").
- **Geheel model**: alle applicaties auto-geladen bij activatie; opbouw-/afpel-modus met de filters.

Generiek over de modi:
- **Zoeken** (naam/domein/leverancier) + **vier filters** (domein, leverancier, hosting, lifecycle)
  — alléén over applicaties (ring-nodes verschijnen via de edges).
- **Actieve set**-beheer (toevoegen/verwijderen/"voeg alle gefilterde toe").
- **Node-detail-paneel** + **"Open applicatie →"** doorklik naar het applicatie-detail.
- **Blokkade-icoon (⚠)** op nodes met open blokkades; **lifecycle-kleuren** op nodes;
  **"Kleur op domein"**-toggle; canvas-tools (centreer / verberg niet-verbonden).
- **"Open in Landschapskaart →"** vanuit het applicatie-detail (deep-link `?center=<id>&modus=ego`).

**Doorbouw v4 (DC013):**
- **Koppelingsdetails op flow-edges**: `richting` (een-/tweerichting) + `protocol` uit
  `relatie.kenmerken`; getoond als edge-label ("koppeling · REST · →").
- **Migratieplaatsing op component-nodes**: eerste `plateau_naam` + `plateau_dispositie` via het
  aggregation-lidmaatschap (bron=plateau → doel=component); getoond in het detail-paneel.
- **Diepte-toggle** (ego + geheel): "1 stap (direct)" / "2 stappen" — diepte 2 voegt de indirecte
  *applicatie*-buren toe (partijen/contracten/infra blijven op diepte 1). Toegepast **client-side**
  op de geladen graaf; het endpoint accepteert `?diepte=` forward-compatibel (zie backend).

---

## Backend

- **`GET /landschapskaart`** — één respons (geen paginering; een graaf is pas betekenisvol als
  geheel). Levert nodes + edges:
  - nodes: componenten (incl. applicaties; catalogus-typing + lifecycle-kleur), partijen, contracten;
    verrijkt met `domein`, `leverancier_naam`, `hosting_model`, `blokkades_open`,
    `plateau_naam`, `plateau_dispositie`.
  - edges: vier ringen; flow-edges dragen `richting` + `protocol`.
  - query-param `diepte` (1–2): forward-compatibel; server-side momenteel een no-op (volledige
    graaf), de stap-diepte wordt client-side toegepast.
- **RBAC**: `ARCHITECTUUR.LEZEN` (hergebruik — geen nieuwe entiteit).
- **Engine onaangeroerd**: read-only via lichtgewicht `table()`-handles op `component_profiel`
  en `blokkade` (géén `ComponentProfiel`/`Blokkade`-import); geen schrijfpad. Geborgd door de
  import-afwezigheids- + read-only-bronscan-tests.

---

## Invarianten (ongewijzigd t.o.v. het voorstel)

- **Read-only / engine onaangeroerd.** Afgeleide inzicht-/communicatielaag; voedt de engine niet.
- **Geen afgeleide relaties** (ADR-023 besluit 7): de kaart *toont* bestaande, expliciet
  geregistreerde relaties; verzint er geen.
- **Een kaart is zo goed als de registratie.** Lege relaties → lege kaart; maakt registratiegaten
  zichtbaar (bv. ontbrekende eigenaar/leverancier/plateau).

---

## Open / roadmap

- **Diepte server-side** — echte ego-subgraaf met `center` + `diepte` op het endpoint, i.p.v. de
  huidige client-side stap-diepte op de volledige graaf.
- **Vervangingsrelatie** (welke component vervangt welke) — ADR nog te ontwerpen.
- **Externe ketenkoppelingen / componentrol** (interne/externe dataprovider/koppelvlak) — ADR-028.
- **BIV-classificatie** (beschikbaarheid/integriteit/vertrouwelijkheid) als filter + kleurcodering — ADR-028.
- **Export** PNG/PDF van de kaart.
- **Cytoscape verder**: pad-inzicht (impactketen tussen twee nodes), clustering per domein/laag.

---

## Nadere besluiten (LI023)

Dit ADR is al geland (DC013/V013). De onderstaande punten zijn **aanvullende productbesluiten**
bovenop de gelande basis — geen herziening van de bestaande inhoud, maar een aanscherping van de
praatplaat-aanpak. Enkele ervan zijn nieuw beleid (1, 2) en sturen een geplande bouw-slice.

1. **Renderingtechniek + plek.** De praatplaat is een vooringestelde ego-view op de Landschapskaart,
   bereikbaar via een "Bekijk op kaart"-knop op de componentdetailpagina. Geen aparte
   renderingtechniek; de bestaande Landschapskaart-infrastructuur wordt hergebruikt.
2. **Verhouding tot de Koppelingenkaart.** De Koppelingenkaart als visuele weergave vervalt — de
   "Bekijk op kaart"-knop is de betere vervanger. De Koppelingen-tab (tabel, bewerken/toevoegen)
   blijft volledig intact.
3. **Centrum-scope.** De "Bekijk op kaart"-knop staat op alle componentdetailpagina's. Het centrum is
   altijd het component waar de gebruiker op dat moment naar kijkt, ongeacht het type. Lege ringen
   worden niet getoond.
4. **Label-/taalmapping per ring:**
   - Koppelingen → "werkt samen met" / "levert aan" / "ontvangt van"
   - Gebruikersgroepen → "wordt gebruikt door"
   - Contracten → "valt onder contract"
   - Infrastructuur → "draait op"
   - Eigenaarschap → "is in beheer bij"
   - Samenstelling → "bestaat uit" / "is onderdeel van"
5. **RBAC.** Hergebruik de bestaande `ARCHITECTUUR.LEZEN`-permissie.
6. **Export/print.** Niet in v1; onderdeel van een breder export/import/rapportage-thema dat apart
   wordt opgepakt.
