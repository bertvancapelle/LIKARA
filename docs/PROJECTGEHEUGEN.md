# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V038 · 2026-07-11
- **Commit:** zeventien LI037-commits (feature-koppen: fase 0–4 `ba6f688`·`8904b2a`·`4a29f2a`·
  `932f607`·`a970fac` · seed-fix `ef2421f` · tree-view gate 1 `ca6501a` · gate 2 `ed0799b` ·
  gating-/vorm-fix `d4b7266` · skill-borging `d87aad7`) + afsluit-commit (docs + build) volgt.
- **Tests:** backend zie TST-V038 · frontend 81 files, 1046 groen · 0 kritieken
- **Migratie-head:** `0059_adr042_procesvervulling` (ongewijzigd — geen schema-wijziging deze
  sessie; subboom-projectie is een pure leeslaag, seed-fix raakt alleen dev-seed-data)
- **TST-rapport:** `docs/TST-V038-Validatierapport.md`
- **Bekende ruis:** dubbeltap-timer-tests in `LandschapskaartView.test.js` zijn belastinggevoelig
  (timeouts onder CPU-verzadiging bij rug-aan-rug-runs; geen code-regressie — geborgd in likara-tests).

## Deze sessie (LI037 — Deelprocessen eerste-klas + tree-view-procesbeheer) — AFGEROND
**Kader:** het LI036-diepte-punt ("alleen hoofdprocessen = tussenstand") gesloten; engine
onaangeroerd, geen schema-wijziging. ADR-034 draagt het besluitkader (amendement), ADR-042 de
statusverwijzing.
- **Deelprocessen eerste-klas op de kaart (fase 0–4).** Seed naar 3 niveaus + gap-deelproces →
  backend **subboom-projectie** (élk subboom-lid eerste-klas als knoop, hiërarchie-edges
  `proces_hierarchie`/"onderdeel van", vervult-edges op het **geregistreerde** (deel)proces —
  wortel-bundel vervangen; selectie-schaal: alleen geraakte bomen; één roll-up-bron =
  spiegel van `rollup_voor_proces`) → **boom-layout** in de proceszone (`procesBoomLayout`) +
  "geen ondersteunend systeem"-cue met subboom-semantiek → **twee ingangen** (ProcesDetail-knop
  + "Via proces" op het beginscherm) via één `kaartHandoff`; herkomst = **oranje selectie +
  centrering** (deelproces gedimd-met-focus + "Toon hele landschap"; hoofdproces breed; blauw
  accent afgekeurd) → **dubbelklik-inzoom** (échte set-inperking proces+subboom+vervullers,
  terug via de bestaande history).
- **Seed-idempotentie-fix.** Verantwoordelijken-blok vult op **vaste identiteit**
  (component+vraagcode) i.p.v. eerstvolgende-lege (3 gevuld / 264 leeg, twee-runs-stabiel).
- **Tree-view procesregister.** `ProcesLijst` met **verbindingslijnen** (gedeelde
  `procesBoomStructuur` — kaart én lijst, nooit een derde boom-opbouw; └/├, guides volle
  rijhoogte, wortels zonder connector-kolom) + gap-cue; **beheer**: verwijderen (409 leesbaar)
  + verhangen met kring-preventie-vóóraf, "Geen (maak hoofdproces)" en een bevestiging die de
  N meeverhuizende kinderen benoemt.
- **Gating-/vorm-consistentie (6 plekken).** Destructieve acties gaten vooraf op
  `magVerwijderen = hasRole('beheerder')` (ProcesLijst + Koppeling-/Structuur-/Datatype-/
  Gebruikersgroep-/ContractSectie); rij-acties als Buttons (destructief = danger, nooit
  tekstlink). Procesvervulling/roltoewijzing bewust ongemoeid (WIJZIGEN-guard klopt daar).
- **Borging (`d87aad7`).** Domeinmodel naar de subboom-realiteit; UX: proces-ingang/inzoom/
  boom-vs-netwerk + gap-cue-consistentie; frontend: gedeelde boom-opbouw, VERWIJDEREN-gating,
  danger-norm, cytoscape-hex-aandachtspunt; werkprotocol: AKKOORD-alleen-rechtstreeks,
  rol-gating-browsercheck met beide rollen, reikwijdte-scan vóór een klasse-fix.

## Prioriteiten volgende sessie — zie NEXT_SESSION.md voor de volle tekst
1. **Plaatstaat-herstel na onbedoelde onderbreking** (lk-state overleeft timeout/herlaad zonder
   tijdslimiet; alleen bewuste actie geeft schone start; eerst read-only feitencheck auth/401).
2. **Architectuur-scherm compleet verwijderen** (besluit A; `ARCHITECTUUR.LEZEN` NIET verwijderen —
   de kaart gebruikt die; eerst read-only inventarisatie; eigen slice met gate + browsercheck).
3. **Beginscherm als enige vertrekpunt** (filterkolom verbergen/inklappen bij lege set).
4. **Rapportage & export** (eigen strategisch spoor, eerst doordenken — PDF kaart-selectie).
5. **Bredere ruggengraat** (audit-dekking deletes; UI-consistentiebundel; kaart component-breed;
   contactpersoon uit eigen organisatie (schema-gate); GEMMA-procesimport (eigen ADR-spoor)).

**Zes nieuwe opvolgpunten uit LI037** (detail + status in OPVOLGPUNTEN.md): proces-only diagram
(te ontwerpen); ADR-spoor procesafhankelijkheden/flow; detailscherm-procesbeheer (besluit A: nu
niet); rollenmodel generiek vs. functioneel + proces-toepasbaarheid (te groot voor nu);
proces-ingang-weergave (productie-evaluatie); history-grens hele-landschap-herstel (checkpoint+fix).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
