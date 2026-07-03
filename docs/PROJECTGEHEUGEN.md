# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V031 · 2026-07-03
- **Commit:** `4c8d113` (ADR-037 Pass 2) — sessie-afsluiting V031 volgt
- **Tests:** backend 841 (module) + 80 (platform) / 2 skipped / 0 failed · frontend 772 groen (66 files) · 0 kritieken
- **Migratie-head:** `0051_adr037_verantw`
- **TST-rapport:** `docs/TST-V031-Validatierapport.md`

## Deze sessie (LI030 — ADR-037 verantwoordelijke per checklistantwoord) — AFGEROND
**Kader:** het vrije-tekstveld "Eigenaar" op een checklistantwoord vervangen door een gestructureerde
**verantwoordelijke** (afdeling óf persoon uit het register), met de blokkade-eigenaar afgeleid. Puur
registratie/leeslaag; score blijft de enige lifecycle-driver (dubbele engine-borging).
- **Pass 1 — schema-gate (`e21a28e`, migratie `0051`):** `checklistscore.verantwoordelijke_id`
  (composiet-FK → `element`, ON DELETE SET NULL, kolom-specifiek) vervangt `checklistscore.eigenaar`;
  `blokkade.eigenaar` gedropt (afgeleid in de leeslaag via `checklistscore.verantwoordelijke_id`).
  Aard-validatie 422 `ONGELDIGE_VERANTWOORDELIJKE`; seed-scenario (persoon/afdeling/leeg + blokkerend).
- **Pass 2 — invoer + signaal (`4c8d113`):** verantwoordelijke-picker in `ChecklistscoreSectie`
  (afdeling/persoon in één `ZoekSelect`, `aard_in`), PATCH `verantwoordelijke_id` zonder score;
  aandacht-signaal `antwoord_zonder_verantwoordelijke` (registratiegaten via `table()`-handle,
  engine-veilig) + `SIGNAAL_LABEL` + velduitleg; Opslaan-knop leesbaar (primaire kleur); identiteit
  "afdeling — organisatie" / "persoon — afdeling — organisatie" in lijst, veld én weergave na selectie
  (read-uitbreiding: `verantwoordelijke_organisatie` + partij-lijst `organisatie_naam`/`afdeling_naam`).
- **Incident-lessen (geborgd in skills):** groene tests dekten tweemaal een kapotte UX niet — onleesbare
  Opslaan-knop (wit-op-bijna-wit `--lk-color-accent`) en veld-vs-lijst-identiteit; pas in de browser
  zichtbaar. Vuistregels in `likara-frontend`/`likara-tests`/`likara-ux`.
- **Separaat gezien, buiten scope:** `NIET_GEAUTHENTICEERD` bij opslaan = sessie-/tokenverval + gefaalde
  `/auth/refresh` (een GET faalde óók) — niet de PATCH, niet ADR-037. → auth/sessie-cluster (opvolgpunt).

## Top-5 prioriteiten volgende sessie
1. **Detailpagina's — GebruikersgroepDetail + BlokkadeDetail** (GG verst; BlokkadeDetail eerst de
   conceptuele keuze eigen-pagina-vs-doorklik met Bert; objecthistorie `_TYPES` ontsluiten)
2. **Breder org-context-patroon** — "afdeling — organisatie"-ontdubbeling ook op de leverancier-picker
   + PartijLijst (via `gebruikersgroepIdentiteit`)
3. **Auth/sessie-cluster** — (a) dev-sessie-robuustheid bij reseed, (b) 401→re-login-UX-vangrail,
   (c) auth/refresh-testgat
4. **Impact-verkenner render-herbouw** — deterministische render-eigenaar + echte render-verificatie
5. **ADR-036 "begin grof"-invoerroute** — frontend-formulier voor een los grof gebruiksfeit

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
