# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V040 · 2026-07-13
- **Commit:** drie LI039-commits (gate 1a-bis ADR-044 `85b9cf5` · gate 1b compleet
  `cf0f046` — incl. browsercheck-fixes + de drie V040-marktverkenningsrapporten) +
  afsluit-commit (skills fase B + docs + build) volgt.
- **Tests:** backend 1040 (2 skipped) · frontend 88 files, 1146 groen · 0 kritieken
- **Migratie-head:** `0064_gate1b_inlees_voltooid` (0063 = ADR-044 plaatsing-omslag;
  0064 = inlees-markering)
- **TST-rapport:** `docs/TST-V040-Validatierapport.md`
- **Dev-DB:** het échte GEMMA-model (299 functies · 304 plaatsingen · 1 vervallen · 1 eigen;
  `inlees_voltooid = true`; restdata 0).
- **Bekende ruis:** dubbeltap-timer-tests in `LandschapskaartView.test.js` blijven
  belastinggevoelig (geen code-regressie — geborgd in likara-tests).

## Deze sessie (LI039 — de bedrijfsfunctie-as op het échte GEMMA-model) — AFGEROND

**Kern: de logische kaart rust nu op de werkelijkheid.** ADR-044 (herijking van gate 1a):
de functieboom is geen ouder-kolom maar **plaatsingen** — aggregation-relaties, exact wat de
GEMMA-bron levert (302 aggregaties; **7 functies met 2–4 ouders**, geteld vóór het besluit).
Meervoud wordt getóónd ("staat ook onder …"), nooit stil opgelost: "Toezicht wordt in vier
domeinen uitgeoefend" is het impact-inzicht waarvoor de kaart bestaat.

- **Gate 1b — referentiemodel inlezen (gebouwd, geland):** veilige AMEFF-lezer (defusedxml,
  hard `xsi:type`-filter, XXE-weigering, eerlijke overgeslagen-telling) · dry-run en
  uitvoering op ÉÉN plan (`_bepaal_plan`) · bronsleutel = identiteit · vervallen = markeren
  (rij + historische plaatsingen bevroren; herleven kan) · eigen functies ongemoeid ·
  gecureerd bestand in de repo (release 1 juli 2026, commit-gepind `de0984717e69`, EUPL,
  SHA-256 in `referentiemodellen/HERKOMST.md`) · dev-seed = de echte import (297/302/2455) ·
  voorbeeld-vóór-bevestigen-dialoog + platform-aanbodscherm (gesloten aanbod) · RBAC:
  **inlezen = beheerder** (correctie op het inhoud-patroon). Import duurt 13–25 s
  (facade-pad, per-call-commits — bewust; bezig-indicatie in de UI).
- **Browsercheck-bevindingen → structurele fixes:** (1) leeg aanbod ≠ fout — de
  `aanbodStaat`-enum sluit 'fout' (rood) en 'leeg' (rustig) structureel uit; de oorzaak
  bleek overigens een 500 (model↔schema-mismatch), niet de gehypothetiseerde lege seed —
  hypothese-validatie loont, twee keer deze sessie. (2) Een **onvoltooide inlees blijft
  nooit stil**: begin-/eindmarkering `inlees_voltooid` (migratie 0064), waarschuwing voor
  iedereen, hervat-route voor de beheerder, geen auto-herstart; het randgeval
  "afgebroken vóór de vervallen-markering" is gedragsgetest.
- **Verse-installatie bewezen:** schone DB + migraties + platform_init (zónder dev-seed) →
  aanbod gevuld, inlezen werkt — het pad van een echte gemeente.
- **Patronen-validatie fase A+B:** 32 sessie-patronen read-only tegen de code getoetst
  (`docs/Validatie-patronen-LI039.md`): 0 botsingen; 3 correcties door Bert besloten
  (test-tenant-regel afgebakend i.p.v. absoluut · picker-uitleg = besloten-te-bouwen ·
  "eerste zin intact" geschrapt — klopte niet). Vastgelegd in **7 skills** mét
  status-markering (*gebouwd / besloten / tekst-regel zonder bouwsteen*) en de
  12-tekst-regels-lijst. Gevaarlijkste tekst-regel: de leeg≠fout-toestand is per scherm
  gebouwd — converge bij n≥2 (opvolgpunt).

## Prioriteiten volgende sessie — TOP-5 (zie NEXT_SESSION.md)
1. **ADR-026-afronding: "ondersteunt werk" als eigenschap van het componenttype**
   *(voorwaarde voor gate 2; opdracht ligt klaar; picker-uitleg meenemen)*.
2. **Gate 2 — koppelen grof/fijn op de plaatsing** (ADR-044 besluit 2; meerdere plekken
   tegelijk verfijnen; vult de in-gebruik-telling van het voorbeeld).
3. **Diagram-layout links→rechts + haakse lijnen, meervoud als verwijzing** (besloten,
   opdracht ligt klaar) + **leesbaarheids-ontwerpronde boom bij 297** (nog te doen).
4. **Gate 3 — gap-signaal per plaatsing** (ADR-044 besluit 4; besluit 3: "hier gebruiken
   we niets" = bevinding).
5. **Gate 4 — kaart op functies + procesregister uit beeld** (hergebruik LI038-bouw).

**Positionering:** de ketting **functie → systeem → partij → contract** — zie de drie
V040-marktverkenningsrapporten (concurrenten · ketting · GEMMA-context).

**Open sporen** (detail in OPVOLGPUNTEN.md): toestandsbouwsteen leeg≠fout (n≥2) ·
picker-uitleg (→ TOP-1) · Toelichting-property · zinsgrens-afkapping (laag) · ADR-spoor
registratie-feiten op objecten · beginscherm · plaatstaat-herstel · architectuur-scherm
verwijderen (`ARCHITECTUUR.LEZEN` behouden).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
