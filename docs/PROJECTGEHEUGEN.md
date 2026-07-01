# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V027 · 2026-07-01
- **Commit:** 73413d7 (LI058 Slice 2) — sessie-afsluiting LI057+LI058 volgt
- **Tests:** backend 944 / 2 skipped / 0 failed · frontend 745 groen (65 files) · 0 kritieken
- **Migratie-head:** `0046_database_beoordeeld`
- **TST-rapport:** `docs/TST-V027-Validatierapport.md`

## Deze sessie (LI057 + LI058) — component-focus-herfundering Slice 1 + 2
**Besloten kader (Variant A):** applicatie wordt één van de componenttypen; beheer blijft
tenant-scoped; engine blijft generiek; score = enige lifecycle-driver.
- **Slice 1 (LI057, migratie 0045):** `migratiepad`/`complexiteit`/`prioriteit` **component-breed**
  (basis-`component`, NOT NULL + defaults); enum `tijdelijk_gedeeld → gedeeld`. **Expand** met
  dual-write naar de behouden applicatie-subtabel (drop = contract-slice).
- **Slice 2 (LI058, migratie 0046):** scoren **per type** via de `checklist_dragend`-vlag; `database`
  beoordeeld + 6-vragen startset; **profiel-backfill** bij False→True (platform-toggle → per-tenant
  RLS-scoped worker-sessie, idempotent; True→False = profielen **inert**). Engine al generiek.
- **OP-30:** env-afhankelijke auth-cookie-test deterministisch gemaakt.
- **Engine-invariant dubbel geborgd** (offline `test_engine_borging_li057`/`test_backfill…li058` +
  live lifecycle/backfill-tests).
- **Docdrift rechtgezet:** dagre → fcose/concentric (frontend-skill); `ChecklistVraag` = **tenant-scoped**
  (niet platform-referentiedata; likara-db-skill); `LOKAAL-TESTEN.md` gemoderniseerd (reset zonder `down -v`).

## Top-5 prioriteiten volgende sessie (LI059)
1. **Slice 3 (contract)** — applicatie-subtabel droppen + `applicatie_service`/routes/schemas opheffen
2. **Slice 4 (frontend)** — één `ComponentFormulier`; `ApplicatieFormulier`/`ApplicatieDetail` retireren
3. **Slice 5** — tests + TST + ADR-021/022 afronding
4. **Componenttype-catalogus uitbreiden** (config + ArchiMate-typering); daarna fileshare→SaaS beoordeelbaar
5. **Impact-verkenner render-herbouw** — deterministische render-eigenaar + echte render-verificatie

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
