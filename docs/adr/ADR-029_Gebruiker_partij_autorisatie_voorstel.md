# ADR-029 — Gebruikersbeheer en identiteitsresolutie

**Status:** Geaccepteerd (herzien DC015)
**Datum:** 2026-06-19 (voorstel) · herzien 2026-06-20 (DC015)
**Relatie:** Bouwt op ADR-010/012 (Keycloak, tweelaags rollenmodel), ADR-024
(partijenregister + persoon-partij), ADR-027 (component-klaarverklaring).
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt.

---

## Context / aanleiding

LIKARA kent inloggers nu alleen als email-adres. Er is geen brug tussen de login en de persoon
in het partijenregister. Daardoor toont de audit-trail een email in plaats van een naam; is
niet per naam herleidbaar wie een checklist-antwoord heeft aangepast of een component gereed
heeft verklaard; en heeft het systeem geen fundament voor gerichte autorisatie per persoon.

De kern van dit ADR is één vraag: **weet LIKARA wie jij bent?** Zodra de koppeling er is,
werken attributie (naam in registraties), verantwoording (wie deed wat) en autorisatie (wie
mag wat) allemaal tegelijk — dat zijn drie uitingen van hetzelfde fundament, niet drie losse
features.

---

## Besluit (kern)

1. **LIKARA is de primaire ingang voor gebruikersbeheer.** Nieuwe gebruikers (medewerker /
   viewer) worden aangemaakt via LIKARA — niet via Keycloak. LIKARA maakt tegelijk het
   persoon-record in het partijenregister én het Keycloak-account aan via de Keycloak Admin
   REST API. De koppeling login ↔ persoon ontstaat bij aanmaak, niet als aparte handmatige
   stap achteraf.

2. **Keycloak is een provisioning-detail van LIKARA.** De beheerder opent nooit Keycloak.
   Keycloak blijft de technische IAM-laag; LIKARA is de beheersinterface. Rol-toewijzing
   in Keycloak (medewerker / viewer) loopt via LIKARA.

3. **Beheerders zijn buiten het register.** Bootstrap-accounts met de beheerder-rol worden
   direct in Keycloak aangemaakt — buiten LIKARA. Beheerders hebben geen persoon-record in
   het partijenregister. De audit-trail toont hun email als fallback. Dit is bewust: een
   beheerder is een technisch account, geen organisatorische actor.

4. **Naam-attributie als primair doel.** Overal waar LIKARA nu email toont (audit-trail,
   checklist-wijzigingen, gereedmeldingen, roltoewijzingen) toont het straks de naam — via
   de koppeling sub → persoon.naam. Email blijft fallback voor accounts zonder koppeling
   (beheerders, historische accounts).

5. **Per-type gereedmeld-recht als uitbreiding op hetzelfde fundament.** Een persoon krijgt
   het recht een component gereed te melden per componenttype. Dit bouwt op de koppeling;
   de grove KLAARVERKLARING-rol blijft de toegangspoort.

6. **Autorisatiebeheer via de bestaande GEBRUIKERSBEHEER-entiteit** (placeholder in de
   RBAC-matrix, Beheerder LAWV) — geen nieuwe entiteit nodig.

---

## Model in detail

### Gebruiker-aanmaak flow (beheerder via LIKARA)

1. Beheerder opent "Gebruikersbeheer" in LIKARA.
2. Vult in: naam, afdeling, functie, email, rol (standaard: medewerker).
3. LIKARA maakt in één reeks:
   - Persoon-record in het partijenregister (aard=persoon, naam/afdeling/functie — ADR-024)
   - Keycloak-account (email, tijdelijk wachtwoord, rol) via de Keycloak Admin REST API
   - Koppelrij `keycloak_sub ↔ persoon_id` in de nieuwe koppeltabel
4. Gebruiker logt in met het tijdelijk wachtwoord en wijzigt dit bij de eerste login
   (Keycloak-standaard).

### Koppeltabel `gebruiker_persoon`
- Tenant-scoped, FORCE RLS, audit op de allowlist
- Velden: `tenant_id`, `keycloak_sub` (UNIQUE per tenant), `persoon_id` (UNIQUE per tenant)
  → composiet-FK naar `element(tenant_id, id)` ON DELETE CASCADE
- `sub` komt uit de Keycloak Admin API response bij account-aanmaak — geen extra stap
- Geen handmatige koppelingsstap nodig (koppeling = registratiefeit bij aanmaak)

### Naam-resolutie
- Bij elke UI-weergave van een actor: `actor_sub` (al in audit_log) → koppeltabel →
  `persoon.naam`
- Geen koppeling gevonden (beheerder, historisch account): toon email als fallback —
  nooit leeg
- Implementatiepatroon: join als transient attribuut op bestaande responses (conform
  `eigenaar_organisatie_naam` — ADR-023/ADR-013 patroon)

### Per-type gereedmeld-recht
- Eigen tabel `gereedmeld_recht` (tenant_id, persoon_id, componenttype)
- `UNIQUE(tenant_id, persoon_id, componenttype)`; composiet-FK persoon_id → element
  ON DELETE CASCADE; componenttype = platform-vaste sleutel (geen FK naar tabel)
- Handhaving: `component_klaarverklaring_service` checkt sub → persoon_id → recht op
  het componenttype van het component
- Fallback: geen koppeling (beheerder) → grove KLAARVERKLARING-rol is voldoende

---

## Invarianten

- **Engine onaangeroerd** — koppeling, provisioning en attributie voeden de score-engine
  niet. Dubbele borging per slice (import-afwezigheid + live geen-mutatie).
- **Backend blijft enige handhaver** — frontend verbergt affordances (`v-if`), backend
  handhaaft altijd.
- **Keycloak als IAM-bron** — LIKARA beheert gebruikers, Keycloak authenticeert; nooit
  omgekeerd.
- **Beheerder buiten het register** — geen persoon-record, geen per-type rechten,
  email-fallback in de audit-trail.
- **Structureel boven conventioneel** — schema dwingt koppeling-/toewijzingsinvarianten
  af (FK/UNIQUE/RLS), niet alleen app-side.

---

## Gevolgen

- Nieuw: gebruikersbeheer-scherm (beheerder-only, GEBRUIKERSBEHEER-entiteit)
- Nieuw: Keycloak Admin API-client in de backend
- Nieuw: tabel `gebruiker_persoon` (schema, RLS, audit)
- Nieuw: tabel `gereedmeld_recht` (schema, RLS, audit)
- Naam-resolutie: bestaande API's die een actor tonen krijgen een naam-join (transient
  attribuut, geen schema-wijziging op die tabellen)
- ADR-027 klaarverklaring-service uitgebreid met per-type check (na slice 3)
- RBAC-teltest beweegt mee bij elke nieuwe entiteit/actie

---

## Open subknopen (te beslissen vóór of tijdens de bouw)

1. **Keycloak Admin API-credentials.** Aparte service-account of bestaande admin-credentials?
   *Default: aparte, minimaal-geprivilegieerde service-account voor user-provisioning.*
2. **Tijdelijk wachtwoord vs. e-mailverificatieflow.** Keycloak-standaard (tijdelijk wachtwoord
   + verplicht wijzigen bij eerste login) of een e-maillink-flow?
   *Default: Keycloak-standaard — eenvoudig, geen extra e-mailinfrastructuur.*
3. **Naam-resolutie: join in response of aparte lookup-endpoint?**
   *Default: transient attribuut via join op bestaande responses — geen nieuw endpoint.*
4. **Historische accounts (vóór ADR-029).** Email-fallback accepteren, of eenmalige handmatige
   koppeling aanbieden?
   *Default: email-fallback accepteren; optionele handmatige koppeling als beheer-tool later.*

---

## Bouwfasering (indicatief, ná besluitvorming)

1. **Keycloak Admin API-feitenrapport** (read-only) — beschikbare endpoints, credentials,
   user-provisioning flow bevestigen.
2. **Koppeltabel `gebruiker_persoon` + gebruiker-aanmaak** (gate — schema + Keycloak
   provisioning): tabel, RLS, audit, service, endpoint, beheer-UI basis.
3. **Naam-resolutie in audit-trail en bestaande UI** (doorloop — join op bestaande responses).
4. **Gebruikersbeheer-scherm compleet** (doorloop — frontend lijst/aanmaken/deactiveren).
5. **`gereedmeld_recht`-tabel + per-type check in klaarverklaring-service** (gate — schema).
6. **Frontend gereedmeld-affordance per type** (doorloop — `v-if` op knop).

Elke slice met engine-onaangeroerd-borging en de gangbare gate-discipline.
