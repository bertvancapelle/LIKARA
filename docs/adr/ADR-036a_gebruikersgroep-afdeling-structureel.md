# ADR-036a — Gebruikersgroep-afdeling structureel

**Status:** Aangenomen
**Datum:** 2026-07-03
**Relatie:** vervolg op ADR-024 (partijenregister) en ADR-036 (organisatiegebruik +
"afdeling — organisatie"-identiteit).

## Context

De afdeling op een gebruikersgroep was een **vrije tekstkolom** (`gebruikersgroep.afdeling`,
`String(255)`) — een impliciet gegroeid gat, nergens als bewuste deviatie vastgelegd. De
persoon→afdeling-koppeling is daarentegen al **structureel**: `partij.afdeling_id` is een composiet-FK
naar een `organisatie_eenheid`-partij, en `partij_service._valideer_lidmaatschap` dwingt bestaan +
de juiste organisatie af (`ONGELDIGE_AFDELING`).

Daardoor hing de ADR-036-identiteit **"afdeling — organisatie"** aan losse tekst. Schijn-afdelingen,
spelvarianten en ontkoppelde hernoemingen waren mogelijk; de seed schreef gebruikersgroep-afdelingen
("Burgerzaken", "Publiekszaken", "Documentbeheer") als tekst **zonder** afdeling-partijen onder de
gemeentes aan te maken.

## Besluit

De gebruikersgroep-afdeling wordt gelijkgetrokken op het persoon-patroon: een **structurele
referentie** (`gebruikersgroep.afdeling_id`) naar een bestaande `organisatie_eenheid`-partij **binnen
de organisatie van het grove feit** (ADR-036 `gebruik_id` → `organisatiegebruik` → organisatie).

- **Optioneel.** Een groep mét organisatie mag een afdeling dragen, maar hoeft niet — leeg is geldig,
  het "detaillering ontbreekt"-signaal blijft dan staan.
- **Organisatie-loze groep draagt geen afdeling** (geen grof feit ⇒ geen organisatie om tegen te
  toetsen).
- **Identiteit partij-verankerd.** De "afdeling — organisatie"-identiteit leest voortaan de naam van
  de afdeling-partij, niet een tekstkolom. Vorm blijft gelijk.
- De **picker** (bestaande afdeling kiezen of ter plekke een volwaardige afdeling-partij aanmaken) is
  frontend-werk (pass 2). De **seed** maakt afdeling-partijen aan onder de organisaties.

## Invarianten / borging

- **Schema dwingt de structuur af**: `afdeling_id` = composiet-FK `(tenant_id, afdeling_id) → element`
  ON DELETE **RESTRICT** (een afdeling met groepen verdwijnt niet stil), nullable. De tekstkolom
  vervalt.
- **Service-cross-row** (spiegelt `_valideer_lidmaatschap`): `afdeling_id` moet een bestaande
  `organisatie_eenheid` zijn binnen de grove-feit-organisatie → 422 `ONGELDIGE_AFDELING`; een
  organisatie-loze groep met afdeling → 422.
- De partij-tabel-CHECK `afdeling_id IS NULL OR aard = 'persoon'` is **niet geraakt** — dat is een
  constraint op de `partij`-tabel; de gebruikersgroep-`afdeling_id` staat op de `gebruikersgroep`-tabel.
- **Engine onaangeroerd** (registratief): geen lifecycle/score/blokkade; dubbel geborgd.

## Gevolg

Eén afdeling is één ding: herbruikbaar over applicaties én personen, hernoemen werkt overal door, geen
schijn-afdelingen meer. Ontwikkelmodus: bestaande vrije-tekst-afdelingen (alleen testdata) verdwijnen
via reseed; geen databehoud-migratie.
