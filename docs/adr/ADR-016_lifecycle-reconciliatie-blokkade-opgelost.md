# ADR-016 — Blokkade-`opgelost` volledig afgeleid (amendeert ADR-013 B1)

| | |
|---|---|
| **Status** | Aanvaard |
| **Datum** | 2026-06-07 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-013 (lifecycle-herberekening, Model A) — **amendeert B1** · ADR-014 (foutformaat) |

## Context

ADR-013 B1 stond toe dat een gebruiker de Blokkade-status handmatig op elke waarde
zette, inclusief `opgelost`. De auto-logica (ADR-013 B2,
`checklistscore_service._synchroniseer_blokkade`) handhaaft de invariant
score↔blokkade echter **transitie-gebaseerd**: ze reageert alleen op een
Checklistscore-schrijf die de blokkerende grens kruist.

Daardoor ontstond een reconciliatie-gat: een **handmatige** `opgelost` op de
laatste open blokkade laat `herbereken_lifecycle` de applicatie naar
`migratieklaar` tillen, terwijl de onderliggende score nog `nee`/`deels` is. De
invariant B2 wordt pas bij een volgende Checklistscore-schrijf opnieuw afgedwongen
— tot dan is de lifecycle inconsistent.

## Besluit

ADR-013 B1 wordt geamendeerd:

### B1-a — Handmatig alleen `open ↔ in_behandeling`
De handmatige Blokkade-PATCH accepteert uitsluitend `open ↔ in_behandeling` (plus
`toelichting`/`eigenaar`). Een handmatige `status=opgelost` ⇒ **409
`ONGELDIGE_STATUSOVERGANG`** (canoniek envelope, ADR-014).

### B1-b — `opgelost` uitsluitend auto-afgeleid
`opgelost` ontstaat **alleen** via de auto-logica (Checklistscore `ja`/`nvt` ⇒
auto-`opgelost`; ADR-013 B2 ongewijzigd). Daarmee klopt invariant B2 **per
constructie**: een applicatie kan niet `migratieklaar` worden terwijl een score
nog blokkeert.

### B1-c — Geen datamodel-/enumwijziging
De enumwaarde `opgelost` blijft bestaan; ze is alleen niet langer **handmatig
zetbaar**. Geen migratie. De guard zit in de service (`blokkade_service.werk_bij`),
niet in de DB.

### B1-d — Frontend
De Blokkade-statusdropdown biedt handmatig alleen `open`/`in_behandeling`.
`opgelost` wordt **read-only** getoond (badge), nooit als keuze; een opgeloste
blokkade is niet status-bewerkbaar (toelichting/eigenaar mogen wel, zonder
`status` in de payload).

## Gevolgen

**Positief**
- Invariant B2 klopt per constructie; het reconciliatie-gat is dicht zonder
  ADR-013 B2/B3 te wijzigen.
- Minimale blast radius: één service-guard + één frontend-dropdown; **geen
  migratie, geen enumwijziging**.

**Negatief / aandachtspunten**
- De auto-logica (B2/B3) blijft volledig leidend; de gebruiker kan een blokkade
  niet meer "afvinken" zonder de onderliggende score te corrigeren — wat juist de
  bedoeling is.
- **Bestaande data**: in een gevulde DB kunnen vóór dit besluit handmatig
  `opgelost`-gezette blokkades met een blokkerende score bestaan. Een eenmalige
  `herbereken_lifecycle`/heropen-pass hoort bij **productie-gereedheid (Laag 5)**,
  niet bij dit besluit (dev-DB had 0 gevallen).

## Alternatieven overwogen

- **`herbereken_lifecycle` `migratieklaar` laten weigeren bij een blokkerende
  score, ondanks `opgelost`** — afgewezen: complexer, en het vecht tegen de
  bewuste "score `nee` + blokkade `opgelost` = stabiele eindtoestand"-semantiek
  van ADR-013 B2; de bron van de inconsistentie (handmatige `opgelost`) blijft dan
  bestaan.
- **Niets doen** — afgewezen: laat het B2-gat open (valse `migratieklaar`).

## Niet in scope

- ADR-013 B2 (transitie-logica) en B3/B4 — ongewijzigd.
- Datamodel/enum (`opgelost` blijft bestaan).
- De eenmalige data-pass bij gevulde DB (productie-gereedheid, Laag 5).
