# ADR-018 — Relatievisualisatie: gefocuste ego-graaf, geen graaf-dependency

**Status**: Aanvaard (CD023, openstaand punt #13)
**Datum**: juni 2026
**Context-ADR's**: ADR-009 (Koppeling-datamodel), ADR-017/CD020 (sorteerbare,
per-richting koppelingenlijst met `tegenpartij_naam`).

## Context

Openstaand punt #13 vraagt een visuele weergave van applicatie-relaties: een
tenant-brede kaart van applicaties (knopen) en koppelingen (gerichte randen,
bron → doel). Een tenant heeft realistisch **honderden applicaties**; een
ongefilterde, volledige force-directed graaf wordt bij dat volume een
onleesbare "hairball" en vergt een zware visualisatie-library (cytoscape /
vis-network / d3-force) met bijbehorende bundle-, licentie- en onderhoudslast.

## Besluit

1. **Gefocuste ego-graaf, niet de volledige graaf.** De visualisatie toont één
   **geselecteerde applicatie + haar directe buren**: inkomende koppelingen
   (leveranciers, bron → deze) links, uitgaande (ontvangers, deze → doel)
   rechts, met de geselecteerde applicatie centraal. Een buur aanklikken
   **hercentreert** de graaf op die applicatie → tenant-brede verkenning zonder
   hairball. De renderomvang is altijd klein, ongeacht tenantgrootte.

2. **Hand-rolled SVG, geen graaf-library.** De ego-layout is met eenvoudige
   coördinaten te berekenen (twee kolommen, verticaal gestapeld) — geen
   force-simulatie nodig. Dus **geen nieuwe (zware) dependency**; geen
   bundle-/licentie-/onderhoudslast. `--cd-`-tokens, geen `<style>`.

3. **Bovenop bestaande endpoints.** De data komt uit de bestaande, tenant-scoped
   per-richting koppelingenlijst (`?bron_applicatie_id=` / `?doel_applicatie_id=`,
   CD020) die `tegenpartij_naam` direct levert, plus de applicatielijst voor de
   kiezer/knoop-metadata. **Geen backend-/datamodelwijziging.**

4. **Toegankelijk alternatief is verplicht.** Een puur-visuele kaart is niet
   toetsenbord-/screenreader-toegankelijk. Naast de SVG (die `role="img"` +
   samenvattende `aria-label` krijgt) staat een **toetsenbord-navigeerbare
   relatietabel** (Inkomend/Uitgaand, herbruik `AppTabs` uit CD022) die dezelfde
   informatie ontsluit — tegenpartij (link naar detail), richting, protocol,
   impact, en hercentreren. De tabel is de toegankelijke waarheidsbron; de SVG is
   visuele verrijking.

## Gevolgen

- Schaalt naar honderden applicaties zonder performance- of leesbaarheidsval.
- Geen dependency-risico; volledig binnen de Vue + Vite + SVG-stack.
- Toegankelijkheid is structureel geborgd (tabel-alternatief).

## Niet in scope

- Een **tenant-brede force-directed graaf** (alle knopen ineens). Dat zou een
  aparte, expliciete dependency-beslissing vergen en valt buiten dit besluit.

## Alternatieven overwogen

- **Volledige force-directed graaf met een graaf-library** (cytoscape /
  vis-network / d3-force): de mooiste demo, maar bij honderden applicaties een
  hairball, en het voegt een zware dependency toe (bundle/licentie/onderhoud).
  Verworpen voor V004; mogelijk later als aparte dependency-beslissing.
- **Hiërarchische/gelaagde layout** (bv. dagre): nuttig bij een duidelijke
  laagstructuur, maar applicatie-koppelingen vormen geen DAG (cycli mogelijk) en
  het vergt eveneens een library. Verworpen.
- **Alleen een tabel, geen visualisatie**: maximaal toegankelijk maar levert niet
  de gevraagde visuele relatie-weergave (#13). De gekozen aanpak combineert beide:
  visuele ego-graaf + de tabel als toegankelijke waarheidsbron.
