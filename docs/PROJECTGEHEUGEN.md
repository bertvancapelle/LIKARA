# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V037 · 2026-07-10
- **Commit:** zeven app-commits (`7b4c00c` · `0b4a5dd` · `d2b07f3` · `5fa5fe0` · `f9a8a6f` ·
  `9914c25` · `a99fe23`) + afsluit-commit (docs + build) volgt.
- **Tests:** backend 1001 / 2 skipped / 0 failed · frontend 1006 groen (80 files) · 0 kritieken ·
  restdata-check expliciet 0
- **Migratie-head:** `0059_adr042_procesvervulling` (ongewijzigd — geen schema-wijziging deze sessie;
  proces-projectie is een pure leeslaag, `herkomst` een additief response-veld)
- **TST-rapport:** `docs/TST-V037-Validatierapport.md`
- **Bekende ruis:** dubbeltap-timer-tests in `LandschapskaartView.test.js` zijn belastinggevoelig
  (timeouts onder CPU-verzadiging bij rug-aan-rug-runs; geen code-regressie — geborgd in likara-tests).

## Deze sessie (LI036 — Lagenweergave mét proceslaan) — AFGEROND
**Kader:** ADR-034-herbouw als derde kaart-weergave op de kaart-selectie, met de proceswereld
(ADR-042) als nieuwe laan. Engine onaangeroerd; geen schema-wijziging.
- **"Lagen" als derde weergave (`7b4c00c`).** Cytoscape preset-baanposities + HTML-band-overlay
  (geen compound-nodes); render-fix eerste frame = meet-stap (`updateStyle` + `layoutDimensions`)
  in de preset-tak; maatwissel = `cy.resize()` + fit, geen re-layout.
- **Rolbanen met rol-accent (`7b4c00c`).** Partij als visuele instance per rolbaan (`id@baan`,
  interactie op `logischId`); rol-tags (gebruikt/levert/beheert/eigenaar) als HTML-pill-overlay
  die de dim-staat van hun knoop delen.
- **"Ring uit wint van gaps" + organisatiebalk model i (`0b4a5dd`).** Gap-knopen respecteren de
  ring-stand; de balk toont alleen in-beeld-organisaties (contrafeitelijk afgeleid — uitgezette
  org blijft zichtbaar-onaangevinkt, dus omkeerbaar).
- **Proceslaan slice 2, stap 1–3.** Backend proces-projectie in de subgraaf: roll-up naar
  hoofdproces, cyclus-veilige `_wortel`-klim, samengetrokken edges met `aantal` + `herkomst[]`,
  één roll-up-definitie (`d2b07f3`) · frontend proceslaan + ring "Processen" + proces-vorm
  afgeronde rechthoek/verloop-pijl (`5fa5fe0`) · aantal-badge + inklapbare herkomst-popup +
  vervul-toggle met exact-ongedaan-maken (`_vervulToegevoegd`-administratie; set-acties wijzigen
  nooit de weergave) (`f9a8a6f`).
- **Borging.** 16 patronen in vijf likara-skills (`9914c25`); ADR-034/040 naar de gebouwde
  realiteit met het diepte-punt "alleen hoofdprocessen = tussenstand" prominent open (`a99fe23`).

## Top-6 prioriteiten volgende sessie (LI037) — zie NEXT_SESSION.md voor de volle tekst
1. **Deelprocessen eerste-klas op de kaart** (besloten top-1; herziet de diepte-tussenstand;
   bevat het geparkeerde "proces als kaart-vertrekpunt" — ProcesDetail-knop + "Via proces"-ingang,
   opent in Lagen met doorgerolde subboom-vervullers, neutraal; start read-only + ontwerpdialoog).
2. **Plaatstaat-herstel na onbedoelde onderbreking** (lk-state overleeft timeout/herlaad zonder
   tijdslimiet; alleen bewuste actie geeft schone start; eerst read-only feitencheck auth/401).
3. **Architectuur-scherm compleet verwijderen** (besluit A; `ARCHITECTUUR.LEZEN` NIET verwijderen —
   de kaart gebruikt die; eerst read-only inventarisatie; eigen slice met gate + browsercheck).
4. **Beginscherm als enige vertrekpunt** (filterkolom verbergen/inklappen bij lege set).
5. **Rapportage & export** (eigen strategisch spoor, eerst doordenken — PDF kaart-selectie:
   plaat + leesbare relatie-beschrijving via de bestaande hertaling).
6. **Bredere ruggengraat** (audit-dekking deletes; UI-consistentiebundel; kaart component-breed;
   contactpersoon uit eigen organisatie (schema-gate); GEMMA-procesimport (eigen ADR-spoor)).

**Losse punten (OPVOLGPUNTEN):** rol-accent beknopt/uitgebreid als ADR-041-kijkvoorkeur;
labelkeuze "Rollen & beheer" → "Partijen & rollen"?; ADR-register-gat (README mist ADR-026..033/035/036).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
