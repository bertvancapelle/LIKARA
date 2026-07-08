# NEXT_SESSION.md — LIKARA V035

**Gegenereerd**: 2026-07-08
**Vorige build**: V035
**Branch**: master

> **Sessie LI034 — ADR-041 persoonlijke voorkeuren + kaart-bugfixes. Volledig geland (V035).**
>
> Afgerond in LI034:
> - **ADR-041 persoonlijke voorkeur-laag** — generieke per-gebruiker key/value-tabel `gebruiker_voorkeur`
>   (sleutel = Keycloak-`sub`, JSONB, FORCE RLS), `voorkeur_service` + route `/voorkeuren` + RBAC eigen-
>   scope (`GEBRUIKER_VOORKEUR = _EIGEN_VOORKEUR`), migratie **0055** (`9498983`).
> - **Component-breed organisatiegebruik-schrijf-slot** (`valideer_component`) — de voorkeur is een
>   kijkfilter, nooit een invoerregel (`b05cc53`); sectie-voorkeur teruggedraaid (`f5e7afe`).
> - **Kaart-kijkfilter als persoonlijke standaardkijk** (`kaart_kijkfilter`) + **reload-fix** (herladen
>   behoudt werk: `beforeunload`/`wisSet`/`lk-state`; precedentie in-sessie > standaardkijk > default) —
>   `c8ae3c7`.
> - **Kaart-bug B** (doorklik popup↔zijpaneel gelijkgetrokken via `_heeftComponentDetail`, `33fa485`) en
>   **bug A** (relatie-loos set-lid tekenen op Overzicht + "geen relaties in beeld"-cue, `3d889ab`).
> - **Zeven skillpatronen** vastgelegd in de negen likara-skills (deze afsluit-commit).
>
> Tests: backend **960** (2 skipped) / frontend **71 files, 869** groen. Migratie-head **0055**.

---

## Volgende stappen

### 1e taak — READ-ONLY analyse: lijststaat behouden bij terugnavigeren

Lijstschermen verliezen hun **filter/zoek/sortering** bij terugnavigeren vanuit een detailscherm.
Bevestigd op **Partijen** (aard-filter "Organisatie" is weg na "Terug naar Partijen"). Uitzoeken:
- welke lijstschermen dit gedrag hebben (Partijen, Componenten, Contracten, Gebruikersgroepen, e.a.);
- of ze de lijststaat **niet** bewaren of **verkeerd**;
- de schoonste **generieke** route om lijststaat (filter/zoek/sortering) over een detail-bezoek heen te
  behouden.

**Kader:** dit is een **momentkeuze die bij terugnavigeren behouden moet blijven** — **géén** persoonlijke
voorkeur-laag; het is navigatie-/terugkeergedrag, in de geest van de kaart-reload-fix (LI034). **Read-only
eerst, dan pas ontwerp/bouw.**

### Daarna — zie OPVOLGPUNTEN.md (geprioriteerd)
Grote/ADR-waardige sporen: proces/functie-inzicht (rol "vervult in"), kaart component-breed maken.
Kleinere kaart-verfijningen: beginscherm-filterbalk verbergen op leeg beginscherm, filterbalk
vereenvoudigen (BIV/Rol achter "geavanceerd"), opgeslagen-view-scope, beginscherm-contextvelden-unie.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V035 |
| Datum | 2026-07-08 |
| Tests | backend 960 (2 skipped) / frontend 71 files, 869 groen |
| Migratie-head | 0055_adr041_gebruiker_voorkeur |
| TST-rapport | TST-V035-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | negen likara-skills bijgewerkt (LI034-patronen) |
