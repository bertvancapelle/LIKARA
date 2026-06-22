# ADR-028 — Componentclassificatie: componentrol en BIV-classificatie

**Status:** Voorstel (geparkeerd — te bouwen na ADR-027)
**Datum:** 2026-06-19
**Relatie:** Bouwt voort op ADR-023 (componentmodel), ADR-026
(componenttype-typering). Voegt twee instance-eigenschappen toe
aan het component, los van het componenttype.
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver —
de engine wordt niet geraakt. Classificatie is puur registratief.

---

## Context / aanleiding

Voor een volledige migratie-analyse zijn twee eigenschappen van een
component essentieel die nu ontbreken:

1. **Componentrol** — is dit een intern systeem, een interne
   dataprovider, een externe dataprovider (basisregistratie,
   landelijke voorziening, ketenpartner), of een koppelvlak/adapter?
   Dit bepaalt of koppelingen zelfstandig omgehangen kunnen worden
   of afhankelijk zijn van externe ketenafspraken.

2. **BIV-classificatie** — Beschikbaarheid, Integriteit,
   Vertrouwelijkheid (internationaal: CIA). Standaard
   risicobeoordelingsmodel voor overheidsorganisaties. Bepaalt
   beveiligingsmaatregelen, migratiekritikaliteit en
   uitvalimpact.

Beide zijn **instance-eigenschappen** (op het individuele component),
niet type-eigenschappen (op het componenttype via ADR-026).
Een Zaaksysteem van leverancier A kan een andere BIV-score hebben
dan een Zaaksysteem van leverancier B.

---

## Besluit (kern)

### Componentrol (platform-breed catalogusveld)

Een nieuw platform-breed catalogusveld `componentrol` op het
component, met vaste opties:

| Rol | Beschrijving |
|---|---|
| `interne_applicatie` | Standaard — eigen systeem (default) |
| `interne_dataprovider` | Levert data aan andere interne systemen |
| `externe_dataprovider` | Basisregistratie, landelijke voorziening, ketenpartner |
| `koppelvlak` | Technische tussenlaag / adapter |

- Platform-breed (niet tenant-scoped) — zelfde patroon als
  componenttype-catalogus.
- Optioneel op het component; default = `interne_applicatie`.
- Zichtbaar in de Landschapskaart als visueel onderscheid
  (node-vorm of randkleur voor externe dataproviders).
- Filterbaar in de Landschapskaart en componentlijst.

### BIV-classificatie (tenant-scoped schaal + velden op component)

Drie nieuwe velden op het component:
- `biv_beschikbaarheid` — score op de tenant-eigen BIV-schaal
- `biv_integriteit` — idem
- `biv_vertrouwelijkheid` — idem

Tenant-eigen BIV-schaal: configureerbare opties per tenant
(3-punts: Laag/Midden/Hoog of 5-punts: Zeer laag t/m Zeer hoog).
Zelfde patroon als checklistvraag-catalogus (tenant-scoped,
beheerbaar via beheerscherm).

Toepassingen in LIKARA:
- Filteren op BIV in de Landschapskaart
- Migratieset-risicobeoordeling ("set bevat X componenten
  met hoge vertrouwelijkheid")
- Kleurcodering op BIV naast lifecycle in de Landschapskaart

---

## Invarianten

- **Engine onaangeroerd** — BIV en componentrol voeden de
  score-engine niet. Classificatie is puur registratief.
- **Structureel boven conventioneel** — BIV-schaal als
  tenant-scoped catalogus (eigen tabel + RLS), niet als
  hardcoded enum.
- **Instance, niet type** — classificatie zit op het component,
  niet op het componenttype (ADR-026).

---

## Gevolgen

- Nieuwe platformbrede catalogus `componentrol_optie`
- Nieuwe tenant-scoped catalogus `biv_schaal_optie`
- Drie nieuwe nullable kolommen op `component`
- Uitbreiding beheerscherm component + componentdetail
- Uitbreiding Landschapskaart (filter + kleurcodering)
- RBAC: componentrol bewerkbaar door medewerker/beheerder
  (zelfde als andere componentvelden)
- Audit: drie BIV-velden + componentrol op de audit-allowlist

---

## Open subknopen (te beslissen vóór de bouw)

1. **Componentrol: vaste enum of beheerbare catalogus?**
   *Default: vaste enum in code (klein, stabiel, ArchiMate-gebaseerd)
   — niet tenant-configureerbaar.*
2. **BIV-schaal: 3-punts of 5-punts als platform-default?**
   *Default: 3-punts als baseline-seed; tenant kan uitbreiden naar 5.*
3. **BIV verplicht of optioneel?**
   *Default: optioneel — registratiegat zichtbaar via signalerings-ADR.*
4. **Landschapskaart-kleurcodering BIV: welke dimensie dominant?**
   *Default: Vertrouwelijkheid (meest risico-relevant voor overheid).*
5. **Componentrol in de Landschapskaart: node-vorm of randkleur?**
   *Default: randkleur (stippel voor externe dataprovider).*

---

## Bouw-fasering (indicatief, ná ADR-027)

1. Schema: componentrol-enum + BIV-schaal-catalogus + drie
   component-kolommen (gate — schema-wijziging)
2. Beheerscherm component uitbreiden (doorloop)
3. Landschapskaart-uitbreiding: filter + kleurcodering (doorloop)
