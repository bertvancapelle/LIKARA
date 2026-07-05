# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V033 · 2026-07-05
- **Commit:** `ca8c999` (gebruiker bewerken + fixes) — sessie-afsluiting V033 (skills + docs) volgt
- **Tests:** backend 866 (module) + 80 (platform) / 2 skipped / 0 failed · frontend 825 groen (69 files) · 0 kritieken
- **Migratie-head:** `0054_contactpersoon_ref`
- **TST-rapport:** `docs/TST-V033-Validatierapport.md`
- **Bekende ruis:** `LandschapskaartView.test.js` / `LandschapskaartPopups` cytoscape-teardown-flake
  (unhandled-rejections; geen testfalen).

## Deze sessie (LI032 — gebruiker-cluster) — AFGEROND
**Kader:** de gebruiker/persoon-registratie volwassen maken — aanspreekpunt als echte verwijzing,
een gebruiker altijd bij een organisatie + afdeling, ter-plekke-aanmaken zonder de flow te verlaten,
en het accountsysteem alleen raken wanneer het moet. Puur registratie/structuur/read + provisioning;
engine onaangeroerd.
- **Contactpersoon = verwijzing (ADR-039, migratie `0054`, `0b91493`).** `partij.contactpersoon_id`
  FK (SET NULL kolom-specifiek) vervangt het vrije-tekstveld; alleen organisatie-achtige aarden;
  persoon-binnen-partij-validatie; read-verrijking `contactpersoon_naam`.
- **Centrale verlopen-sessie-vangrail + zoek-fout-norm (`5d007b4`).** Eén afhandelpunt in `api.js` op
  het bewezen-gefaalde-refresh-punt → redirect `login?sessie_verlopen=1&next=<pad>`; framework-loze
  callback-bedrading; nooit rauwe `NIET_GEAUTHENTICEERD`.
- **Ter-plekke-aanmaken afdeling via gedeelde `AfdelingSelect`** (4 plekken; `bebf658`, `4534533`).
- **Gebruiker aanmaken** org intern-only + gescoopte afdeling (`b1fde48`); **gebruiker bewerken**
  org/afdeling + picker-voorvul-fix + accountsysteem-fix (conditionele Keycloak-aanroep, PUT zonder
  username) + 2e interne testorganisatie (RID Rivierenland) + stale-label-`:key` + param-filterende
  picker-integratie-testhelper (`ca8c999`).
- **Skills: 18 LI032-patronen** vastgelegd over domeinmodel/ux/frontend/security/resilience/tests/
  werkprotocol (deze afsluit-commit).

## Top-5 prioriteiten volgende sessie
1. **GebruikersgroepDetail** op het schone model (applicatie-kant-ingang eerst; groep-eigen signalen;
   objecthistorie `_TYPES` uitbreiden met `gebruikersgroep` — `haal_op` bestaat al).
2. **BlokkadeDetail** — conceptuele keuze eerst met Bert (eigen pagina vs. doorklik naar checklisttab).
3. **Breder org-context-patroon** — leverancier-picker + PartijLijst (+ intern/extern-kolom/badge).
4. **Impact-verkenner render-herbouw** (zwaarste los item; edges-onzichtbaar-bug in echte render).
5. **Backlog** — ADR-035 slice 3; partij-picker-scope-domeinvraag; ADR-036 coarse-UI.

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
