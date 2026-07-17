# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V044 · 2026-07-17
- **Commit:** `9b322b6` naam-fix "Beoordelingsstatus" · `6d41dbf` slice B2 · `972df21` slice B1 ·
  `ac9db21` slice A · `bd60085` brok 3 seed · `bae58b2` serving-fix · `095491b` slice 2. Afsluitcommit
  LI043 (TST + NEXT_SESSION + PROJECTGEHEUGEN + build) volgt in deze afsluiting.
- **Tests:** backend **1133 passed, 2 skipped, 0 failed** (80 platform + 1053 module) · frontend
  **95 files / 1222 passed** · `vite build` ✅ · 0 kritieken.
- **Migratie-head:** `0070_adr051_gapsignaal` — **geen schema-wijziging deze sessie** (alle kaart-lezing
  is frontend + read-only afgeleid; head ongewijzigd).
- **TST-rapport:** `docs/TST-V044-Validatierapport.md` (0 kritieken).
- **Dev-DB:** GEMMA-model intact. De dev-seed vertelt nu **wél** het gate-4-verhaal (5 standen, mét/zonder
  gebruikersgroep, meervoud-plek) — brok 3 geland.
- **Audit-keten OPGELOST:** de 2 V043-live-tests (`test_audit_capture_live.py`) **slagen nu** (8 passed);
  de data-conditie in de dev-`audit_log` is weg (reseed). Geen pre-existing failure meer.
- **Werktree:** **schoon** — alle LI043-bouw is per opdracht apart geland (één opdracht per commit).

## Deze sessie (LI043 — gate 4 kaart-lezing + naam-fix + borging) — AFGEROND

**Kern: de bedrijfsfunctie-kaart is nu leesbaar; de beoordelingsstatus heeft een naam.**

- **Gate 4 kaart-lezing compleet (slice 2 → A → B1 → B2).** `095491b` proceslaan → bedrijfsfunctie-plek-
  laan (path-expansie). `ac9db21` slice A: lezing **werk/status/domein** + neutraliseer-model (één kanaal
  actief, rest neutraal) + meebewegende legenda. `972df21` slice B1: gedeelde **`standCodering`** + ernst-
  pills in de lijst. `6d41dbf` slice B2: dezelfde stand-kleuren op de **kaart** + legenda, uit die éne bron
  (optie A — token op tekenmoment geresolved, `standKaartKleur`). Lijst ↔ kaart identiek: amber = werk ·
  groen = draait · blauw = via boven · grijs = besluit. Geen schema.
- **Serving-richting-fix (`bae58b2`).** "Systeem zonder gebruikersgroep" las de serving-relatie
  achterstevoren (`doel_id`) → vlagde vrijwel elk component; nu bron=component (gedeelde richting-bron),
  mét richtingtest. Herstelt het signaal waarop brok 1/2 leunen.
- **Brok 3 dev-seed (`bd60085`).** Verse DB vertelt alle vijf standen (incl. plek mét én zónder
  gebruikersgroep); proces-seed verwijderd.
- **Naam-fix "Beoordelingsstatus" (`9b322b6`).** Het verwarrende "Lifecycle"/"Status"-veld (botste met
  Levensfase) heet overal **Beoordelingsstatus**, structureel uit de `VELD_LABELS`-registry — één bron,
  sentinel-getest (breekt bij herhaald hardcoden).
- **Borging:** `38b02eb` domeinmodel-terminologie (component/type/applicatie; "systeem" geen synoniem) ·
  `d76e06a` gg-signaalrichting · `5c4e479` **zes sessiepatronen** (presentatie-single-source · canvas-token ·
  plek-stand-kleurtaal · bediening · leeg-is-geen-oordeel · aandacht-schaalt-met-gewicht) in frontend/ux +
  LOKAAL-TESTEN. Skills frontend/ux/domeinmodel op V043-frontmatter.
- **Ontwerpspoor verankerd:** `8937e95` **beoordelingsgrondslag + open-punten-overzicht** (groot post-MVP) ·
  `5d9b04f` L1a ijkpunt-wilsbesluit · G4-1d/G4-4/G4-5/0b opvolgpunten.

## Vorige sessie (LI042 — gate 4 brok 1 + skill-vastlegging) — AFGEROND

- **Gate 4 brok 1 (datalaag, `e0ff6d1`):** de leeslaag kent per dekkend systeem `heeft_gebruikersgroep`
  (read-only afgeleid) en de plek een 5e stand `werkvoorraad` (streng criterium). Geen schema, head 0070.
- **Gate 4 slice 1 (vorig sessie-einde):** koppelen vanuit het component, "Bedrijfsfunctie"-tabblad +
  werkvoorraad-gat "systeem zonder bedrijfsfunctie".
- **Skill-vastlegging (7 punten):** kleur = de actieve kaart-lezing · één lezing → één render-kanaal ·
  afgeleide-stand onder het bestaande recept · meebewegende legenda + `kleurOpDomein`-gat · checkpoint-
  vóór-vorm · parallelle read-only worktrees · tool-cadans. Volledig in `TST-V043` + git-historie.
- **Daarvóór:** LI041 (gate 2 koppelen + gate 3 vier standen + rollengrens ADR-050) · LI040 (ADR-045/046).

## Prioriteiten volgende sessie (zie NEXT_SESSION.md)

> Blok A (bedrijfsfunctie-as) is qua kaart-lezing af; het restant is de laatste MVP-laag + het
> post-MVP-ontwerpspoor.

1. **Gate 4 restant / ADR-046-stubs** — levensfase / bedoeling / uitstap-stand (stuk 3) / tranche (stuk 4).
2. **Open-punten-overzicht per component** — kan EERDER ongewogen landen (bronnen zijn al ophaalbaar); mockup eerst.
3. **Beoordelingsgrondslag** — het post-MVP-fundament onder (2); ontwerp/ADR, raakt vermoedelijk schema.
4. **De twee B2-bevindingen** (amber gat/werkvoorraad; niet-symmetrische lezingen) — koppelen aan (3).
5. **Contract-spoor** (ná gate 4) — notitie klaar, besluit open.

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
