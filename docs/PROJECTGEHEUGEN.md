# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V032 · 2026-07-04
- **Commit:** `6702bd2` (Slice 2c) — sessie-afsluiting V032 volgt
- **Tests:** backend 851 (module) + 80 (platform) / 2 skipped / 0 failed · frontend 780 groen (66 files) · 0 kritieken
- **Migratie-head:** `0053_adr038_consolidatie`
- **TST-rapport:** `docs/TST-V032-Validatierapport.md`

## Deze sessie (LI031 — ADR-038 gebruikersgroep-consolidatie + intern/extern) — AFGEROND
**Kader:** één consistent model — een gebruikersgroep hoort **altijd** bij een organisatie; burger-
doelgroepen zijn gewone **externe organisaties met afdelingen**. Intern/extern wordt een expliciet
kenmerk op partijen. Puur registratie/structuur/read; score blijft de enige lifecycle-driver (dubbele
engine-borging).
- **ADR-038 geschreven** (`1d9ab3a`).
- **Slice 1a — `partij.scope`, additief (`2f1c816`, migratie `0052`):** `partij_scope_enum`
  (intern/extern), nullable + twee CHECKs (gezet iff organisatie/externe_partij; externe_partij vast
  extern; afdeling/persoon leiden af). Default extern op organisatie; seed BvoWB=intern.
- **Slice 1b — consolidatie (`195c489`, migratie `0053`):** `gebruikersgroep.gebruik_id` **NOT NULL**
  (FK → RESTRICT); `burger`-aard uit `partij_aard_enum` (type-recreate met drop/herbouw aard-CHECKs).
  Organisatie verplicht in Create + service-422; werk_bij weigert org=null; `_valideer_afdeling`-tak
  gesnoeid. Dode resten weg: kaart-veld `gebruikt_door_organisatieloos` + signaal
  `gebruikersgroep_zonder_organisatie`. Seed: burger-doelgroepen = 3 externe organisaties + 6 segment-
  afdelingen + 5 groepen; dev-only defensieve migratie-opruiming (no-op op verse DB).
- **Slice 2a — groep-dialoog org verplicht (`edb4eb8`):** client-side inline-melding + `*`-markering;
  org-loze payload-tak weg; dode `orgAard`-state opgeruimd.
- **Slice 2b — intern/extern-UI (`3ec3320`):** kiesbaar in `PartijFormulier` (radio-kaartjes, default
  Extern; vast "Extern" bij externe partij; niet bij afdeling/persoon), leesbaar in `PartijDetail`.
- **Slice 2c — kaart-opruiming (`6702bd2`):** dood burger-silhouet/label/legenda/predicate weg.
- **Runtime-restpunt:** verse reseed vóór browserverificatie (BvoWB=intern + burger-doelgroepen zichtbaar)
  via stack-reset (`down` → `volume rm likara_lk_postgres_data` → `up -d` → `dev_seed_testdata.py`; `down -v` = deny).

## Top-5 prioriteiten volgende sessie
1. **Contactpersoon als keuze uit personen van de eigen organisatie — SCHEMA-GATE (ADR-waardig),
   vóór GebruikersgroepDetail (besluit Bert).** Vrije tekst → persoon-verwijzing; sjabloon ADR-036a/037;
   5 open ontwerpvragen (ter-plekke-aanmaken; aarden-scope; vervangen-vs-additief; telefoon/mobiel/email
   buiten scope; migratie-landing defensief/reseed). Bouwstenen klaar.
2. **GebruikersgroepDetail** op het schone model (applicatie-kant-ingang eerst; groep-eigen signalen;
   objecthistorie `_TYPES` uitbreiden met `gebruikersgroep` — `haal_op` bestaat al)
3. **BlokkadeDetail** — conceptuele keuze eerst (eigen pagina vs. doorklik naar checklisttab)
4. **Breder org-context-patroon** — leverancier-picker + PartijLijst (+ intern/extern-kolom)
5. **Auth/sessie-cluster** — (a) dev-sessie-robuustheid bij reseed, (b) 401→re-login-UX-vangrail,
   (c) auth/refresh-testgat

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
