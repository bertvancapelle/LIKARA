# ADR-012 — Addendum B: `PlatformEntiteit.CONTRACTCONFIG`

**Status**: Aanvaard (CD006-sessie)
**Hoort bij**: ADR-012 (tweelaags rollenmodel platform/tenant), ADR-020 (leverancier- en
contractregister), ADR-012 Addendum A (`CHECKLISTCONFIG`, het patroon dat dit Addendum volgt).

## Context

ADR-020 introduceert drie platform-brede, beheerbare classificatie-catalogi (B1, besloten):
**dekking**, **kostenmodel** en **relatie-rol**, samen in één tabel `contractconfig_optie` met een
`dimensie`-discriminator. Net als bij ADR-019/Addendum A is dit platform-referentiedata, beheerd
op het platformniveau (`cd_platform`). Om de beheer-endpoints schoon te kunnen autoriseren is een
nieuwe entiteit in de platform-RBAC-matrix nodig; de bestaande entiteiten (`TENANT`,
`PLATFORMINSTELLINGEN`, `PLATFORMMETADATA`, `CHECKLISTCONFIG`) dekken deze catalogus niet.

## Besluit

1. Nieuwe entiteit **`PlatformEntiteit.CONTRACTCONFIG`** in `core/platform_rbac.py`.
2. Rechtenverdeling:
   - **platformbeheerder**: `L, A, W` (Lezen, Aanmaken, Wijzigen).
   - **platformoperator**: `L` (alleen Lezen).
3. **Geen `V` (Verwijderen)** voor wie dan ook: een optie wordt nooit hard verwijderd maar
   **soft-gedeactiveerd** (ADR-020 Besluit 6, `actief`-vlag) — dat is een `W`-actie, geen `V`.
4. **Eén entiteit voor alle drie de dimensies** (dekking / kostenmodel / relatie-rol). De
   dimensie is een attribuut binnen de catalogus, geen autorisatiegrens: dezelfde platformbeheerder
   beheert alle drie. Fijnmaziger autoriseren per dimensie is niet nodig en zou de RBAC-matrix
   onnodig vergroten.

## Gevolgen

- Alleen de **platformbeheerder** kan dekking-/kostenmodel-/rol-opties toevoegen, label & volgorde
  wijzigen of soft-deactiveren. De **platformoperator** mag de catalogus inzien maar niet wijzigen.
- Consistent met de tweelaags-logica én met Addendum A: alle beheerbare referentiedata-catalogi
  (`CHECKLISTCONFIG`, `CONTRACTCONFIG`) leven op het platformniveau (`cd_platform`); tenant-rollen
  raken ze niet.
- Sluit aan op de grants uit ADR-020 Besluit 8 (`cd_platform` schrijft op `contractconfig_optie`;
  `cd_app` leest alleen).

## Niet in scope

- Per-tenant configuratie of -overrides (ADR-020 B1: platform-breed).
- Autorisatie per dimensie (één entiteit dekt de hele catalogus — Besluit 4).
- De tenant-data uit ADR-020 (`leverancier`, `contract`, koppelingen) — die is RLS-scoped onder
  `cd_app` en valt buiten het platform-RBAC-domein.

## Implementatie

Te realiseren samen met de ADR-020-fase die de platform-beheer-endpoints oplevert:
`PlatformEntiteit.CONTRACTCONFIG` + matrixrij (beheerder `{L,A,W}`, operator `{L}`, geen `V`) in
`core/platform_rbac.py`; de `/platform/contractconfig`-endpoints worden geguard met
`vereist_platform_permissie(CONTRACTCONFIG, …)` op `get_platform_session` (cd_platform). De
RBAC-matrixtest wordt uitgebreid met de nieuwe entiteit (dan 5 entiteiten × 2 rollen × 4 acties).
