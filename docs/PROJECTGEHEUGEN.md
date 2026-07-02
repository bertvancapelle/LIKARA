# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V028 · 2026-07-02
- **Commit:** 1c40814 (LI059 FacadeOpruiming) — sessie-afsluiting V028 volgt
- **Tests:** backend 865 / 2 skipped / 0 failed · frontend 717 groen (63 files) · 0 kritieken
- **Migratie-head:** `0047_li059_drop_applicatie`
- **TST-rapport:** `docs/TST-V028-Validatierapport.md`

## Deze sessie (LI059) — component-focus-herfundering AFGEROND (`component` = enige bron)
**Kader:** applicatie is één van de componenttypen; er is **geen** `applicatie`-subtype/-facade meer —
een component met `componenttype='applicatie'` ÍS de applicatie. Engine generiek; score = enige driver.
- **Slice 3 (0047, `03360ea`):** `applicatie`-subtabel gedropt; `applicatie_service` als dunne facade;
  dual-write weg; byte-compat behouden; dubbele engine-borging + verse reseed.
- **Slice 4 (`6fa655e`):** frontend-cutover — één `ComponentFormulier` (3 transitie-velden voor élk type)
  + één rijk `ComponentDetail` (tab-IA, conditioneel per type); `ApplicatieFormulier`/`ApplicatieDetail`
  geretireerd; `/applicaties*` → redirects. Geen functie verloren.
- **FacadeOpruiming (`1c40814`):** volledige purge — routes/service/schema + `api.applicaties` weg;
  `Entiteit.APPLICATIE` (RBAC 23→22 = 352), audit-allowlist, objecthistorie-tak weg; validators →
  `schemas/_validators.py`; creatie-kern `maak_applicatie_component` → `component_service`.
- **Slice 5:** ADR-021/022 slotsecties "Eindstaat" + ADR-register-notitie + `likara-domeinmodel §1`
  bijgetrokken (applicatie = componenttype, geen eigen element_type).
- **Engine-invariant dubbel geborgd** (`test_engine_borging_li057`/`_li059` + live).

## Top-5 prioriteiten volgende sessie
1. **Componenttype-catalogus uitbreiden** (config + ArchiMate-typering); daarna fileshare→SaaS beoordeelbaar
2. **Impact-verkenner render-herbouw** — deterministische render-eigenaar + echte render-verificatie
   (incl. het losse Cytoscape-mock-console­ruispunt in `LandschapskaartView.test.js`)
3. **ADR-035 Slice 3** — "Registratie onvolledig" (configureerbare score-drempelwaarde)
4. **ADR-029 Fase 5** (`gereedmeld_recht`) + **ADR-023 Fase F-rest**
5. **OP-30** env-auth-test (omgevingsgebonden) — resterend administratief punt

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
