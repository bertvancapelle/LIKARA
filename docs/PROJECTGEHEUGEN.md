# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V036 · 2026-07-09
- **Commit:** acht app-commits (`233cc0c` · `9128a24` · `2ff8fa9` · `cc43418` · `ddb7b7a` · `3a65c3b` ·
  `0c4fe60` · `8a76f55`) + afsluit-commit (8 skills + docs + build) volgt.
- **Tests:** backend 997 / 2 skipped / 0 failed · frontend 965 groen (80 files) · 0 kritieken
- **Migratie-head:** `0059_adr042_procesvervulling` (0056 proces-subtype+boom · 0057 RLS/grants ·
  0058 applicatiefunctie-catalogus · 0059 procesvervulling)
- **TST-rapport:** `docs/TST-V036-Validatierapport.md`
- **Bekende ruis:** `LandschapskaartView.test.js` happy-dom teardown-flake (pre-existing, geen testfalen).

## Deze sessie (LI035 — lijststaat + ADR-042 volledig) — AFGEROND
**Kader:** de proceswereld als registratie + read-only inzicht (score blijft de enige lifecycle-driver),
plus het lijststaat-patroon en zes browsercheck-bevindingen die systeembrede patronen werden.
- **Lijststaat (`9128a24`).** `useLijstStaat`: sessionStorage-momentstaat per lijstscherm (route-leave +
  beforeunload; deep-link > bewaard > default; cursor nooit mee) op 4 lijstschermen.
- **ADR-042 (5 slices).** Proces = nestbaar element-subtype (plek=niveau; business_process = 2e
  gemarkeerde behavior-uitzondering); koppelregel = tripel (component, proces, applicatiefunctie),
  component-breed; applicatiefunctie = single-purpose platformcatalogus (GEMMA-startset); schermen met
  regel-acties + MeldingBanner; componentkant met vier-vragen-Overzicht + overlay-formulier; roll-up =
  pure leeslaag (subboom + tak_id-groepering, open-tenzij-groot) + organisatie-proceskijk (eigendom +
  gebruik, dedupe) + succes-toast-standaard (`toastSucces`).
- **Zes patronen uit de browsercheck:** Dialog-primitive (vaste kop/voetbalk, min-h-0, scroll-schaduw
  primair-blauw), breedte-override-borging, MeldingBanner, samengevoegd "Onderliggende processen"-blok,
  succes-toast, regel-acties. Vastgelegd in de acht likara-skills, mét correcties (CD004-scope,
  beheerrol = dimensie, AppLayout-testlocatie, IMPACT_RINGEN afgeschaft).

## Top-5 prioriteiten volgende sessie (LI036)
1. **ADR-034-herbouw lagenweergave** (op de kaart-selectie, mét proces-laan; 3 ontwerpnotities:
   nesting business-laan, selectie-semantiek, roll-up in de laan).
2. **Audit-dekking entiteit-deletes** (systemisch core-execute-gat, pre-existing — hoog).
3. **UI-consistentie-bundel** (11 dialoog-klonen → BevestigVerwijderDialog; 2 warn-banners →
   MeldingBanner; PartijRollenSectie-verwijder-asymmetrie).
4. **Kaart component-breed** (ADR-verkenning).
5. **Beginscherm-/kaartverfijningen** (filterbalk leeg beginscherm, view-scope, filterbalk
   vereenvoudigen, contextvelden-unie). Daarna: GEMMA-procesimport (eigen ADR-spoor, ná ADR-034).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
