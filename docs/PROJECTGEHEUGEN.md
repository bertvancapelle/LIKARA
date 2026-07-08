# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V035 · 2026-07-08
- **Commit:** zes app-commits (`9498983` · `b05cc53` · `f5e7afe` · `c8ae3c7` · `33fa485` · `3d889ab`) +
  afsluit-commit (7 skills + docs + build) volgt.
- **Tests:** backend 960 / 2 skipped / 0 failed (880 module + 80 platform) · frontend 869 groen (71 files) · 0 kritieken
- **Migratie-head:** `0055_adr041_gebruiker_voorkeur` (nieuwe tabel `gebruiker_voorkeur`, FORCE RLS)
- **TST-rapport:** `docs/TST-V035-Validatierapport.md`
- **Bekende ruis:** `LandschapskaartView.test.js` happy-dom teardown-flake (theme-css fetch abort; geen
  testfalen).

## Deze sessie (LI034 — ADR-041 persoonlijke voorkeuren + kaart-bugfixes) — AFGEROND
**Kader:** een per-gebruiker voorkeur-mechanisme ("onthoud als mijn standaard") als generieke laag, met
als kernregel: een voorkeur is een **kijkfilter**, nooit een invoerregel. Plus twee geparkeerde kaart-bugs.
- **Voorkeur-laag (`9498983`).** Tabel `gebruiker_voorkeur` (sleutel Keycloak-`sub`, JSONB, FORCE RLS,
  uniek `(tenant,sub,sleutel)`), `voorkeur_service` + route `/voorkeuren`, RBAC eigen-scope
  (`GEBRUIKER_VOORKEUR = _EIGEN_VOORKEUR`, elke rol beheert eigen), migratie 0055. Niet geaudit (bewust).
- **Component-breed schrijf-slot (`b05cc53`).** `valideer_component` — organisatiegebruik is component-
  breed en tenant-gelijk; de voorkeur raakt de schrijf niet. **Sectie-voorkeur teruggedraaid** (`f5e7afe`,
  te versnipperd).
- **Kaart-kijkfilter-standaard + reload-fix (`c8ae3c7`).** Standaardkijk = de kijk-variabelen (ringen/
  filters/diepte/kleur/lane), nooit `actieveSet`; toepassen bij mount + "Begin opnieuw". Reload behoudt
  werk (`beforeunload` → `_bewaarKaartState`, `wisSet` wist `lk-state`); precedentie **in-sessie > standaard
  > default**.
- **Kaart-bugs.** B: doorklik popup↔zijpaneel gelijkgetrokken via `_heeftComponentDetail` (`33fa485`).
  A: relatie-loos set-lid tekenen op Overzicht + "geen relaties in beeld"-cue (`3d889ab`).
- **Skills: 7 LI034-patronen** vastgelegd in de negen likara-skills (incl. ux-drift-correctie doorklik).

## Top-5 prioriteiten volgende sessie
1. **Lijststaat behouden bij terugnavigeren** (1e taak, read-only) — filter/zoek/sortering gaan verloren
   bij terug uit detail (bevestigd op Partijen). Momentkeuze-behoud bij terugkeer, géén voorkeur-laag.
2. **Proces/functie-inzicht** (groot, ADR-waardig) — component "vervult rol in" proces/functie; grof
   beginnen (proces + koppeling eerst).
3. **Kaart component-breed maken** (ADR-spoor) — de kaart is bewust applicatie-centrisch; elk componenttype
   zoekbaar/doorklikbaar/als buur = eigen ADR.
4. **Beginscherm-filterbalk verbergen op leeg beginscherm** + filterbalk vereenvoudigen (BIV/Rol achter
   "geavanceerd").
5. **Opgeslagen-view-scope** (bewaart een view ook kijk-instellingen?) + beginscherm-contextvelden-unie
   (feedback per veld).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
