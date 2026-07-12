# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V039 · 2026-07-12
- **Commit:** zes LI038-commits (checkpoint `97d5b69` · gate 1+v2 `82806ff` · gate 2+v2
  `e91f2a2` · gate 3 `f1d3270` · ADR-043 + feitenrapport `6c49ed3` · skill-review `d7df7e3`)
  + afsluit-commit (docs + build) volgt.
- **Tests:** backend 1001 (2 skipped) · frontend 84 files, 1089 groen · 0 kritieken
- **Migratie-head:** `0059_adr042_procesvervulling` (ongewijzigd — geen schema deze sessie;
  alles frontend + read-side + docs)
- **TST-rapport:** `docs/TST-V039-Validatierapport.md`
- **Bekende ruis:** dubbeltap-timer-tests in `LandschapskaartView.test.js` zijn belastinggevoelig
  (timeouts onder CPU-verzadiging bij rug-aan-rug-runs; geen code-regressie — geborgd in likara-tests).

## Deze sessie (LI038 — Proces-only structuurbeeld + ADR-043) — AFGEROND

**Strategische kern: ADR-043 herijkt ADR-042.** De "waarvoor"-as van de logische kaart
verschuift van **proces** naar **bedrijfsfunctie**. LIKARA = **Logische ICT Kaart** → rust op
de stabiele as (bedrijfsfunctie, GEMMA Basisarchitectuur — wijzigt in jaren), niet op wat met
elke reorganisatie schuift (proces). Het procesregister wordt in de MVP **verborgen, niet
verwijderd** — verdieping zonder trap: de LI038-bouw (boom, diagram, inzoom/history, gap-cue)
wordt door de functie-as **hergebruikt** (n≥2-abstractie); terugkeer later als detaillering
ónder de functie, nooit ernaast.

- **MVP-verhaal:** model inlezen → applicaties aan functies hangen → kaart. Een verse tenant is
  **dag één** waardevol (i.p.v. na maanden processen uitschrijven); gaten (functie zonder
  ondersteunende applicatie) zijn meteen zichtbaar — tegelijk de sterkste demo.
- **Referentiemodel = eerste-klas begrip** (naam, herkomst, versie; GEMMA = instantie 1).
  **Motor generiek** (ArchiMate/AMEFF), **aanbod gesloten**: alleen door LIKARA gevalideerde
  modellen; de open "eigen bestand"-route is later een schakelaar, geen herbouw —
  verdienmodel-optie (gecureerde referentiemodellen). Bronsleutel = identiteit (nooit op naam
  matchen); modelinhoud lees je, wijzig je niet; vervallen ≠ verwijderen (CASCADE zou eigen
  registratie meeslepen); geen synchronisatiemachine (herinlees = zeldzame, bewuste handeling
  met voorbeeldscherm). Grond: `Feitenrapport-referentiemodel-bedrijfsfuncties-V038.md`
  (zes lege slots feitelijk vastgesteld).
- **Proces-only structuurbeeld geland (3 gates).** Boom|Diagram in het processen-scherm;
  api-vrij `ProcesDiagram` (props-gevoed — vervuller-call structureel onmogelijk) op de pure
  afleidingen `procesFocusSet`/`procesSubboomSet`; klik-popup met drie gescheiden uitgangen;
  dubbelklik-inzoom op **proces-ids** + snapshot+cursor-history ("← Terug"); "Toon in
  procesbeeld" vanuit de Boom. ZoekSelect-bouwsteen-fix (picker-regel 4: gekozen waarde =
  label + ×-wis, platform-breed geërfd) en `useSleepbaar` geconvergeerd (kaart-legenda en
  -popup draaien er nu ook op).
- **Kernles LI038:** *een regel in de skills is geen borging — hij houdt pas als een gedeelde
  bouwsteen hem afdwingt.* Picker-regel 4 stond er sinds LI032 en werd geschonden; het
  sleep-recept leefde twee keer inline. **Beide gaten kwamen uit de browser, niet uit 1089
  groene tests.** Werkregels geborgd in likara-werkprotocol (verifieer regel-naleving
  read-only; regel → bouwsteen; fix in de bouwsteen; structureel onmogelijk = sterkste borging).

## Prioriteiten volgende sessie — HERZIENE TOP-5 (zie NEXT_SESSION.md; oude top-5 vervallen door ADR-043)
1. **Bedrijfsfunctie-as + gevalideerde GEMMA-import** *(= de MVP)* — start: 8 ADR-043-subknopen
   beslissen + read-only bouw-validatie (AMEFF, subtype-recept, soft-vervallen); samen ontwerpen
   met het registratie-feiten-spoor.
2. **Kaart op functies + procesregister verbergen** (koppelregel component↔functie,
   gap-signalering; hergebruik LI038-bouw; model blijft intact).
3. **Beginscherm als enige vertrekpunt** (rustige lege start, filterkolom pas bij selectie).
4. **Plaatstaat-herstel na onbedoelde onderbreking** (kwaliteitspunt — kan wachten tot de kaart klopt).
5. **Architectuur-scherm compleet verwijderen** (klein; **`ARCHITECTUUR.LEZEN` NIET verwijderen** —
   de kaart gebruikt het).

**Gezakt (backlog):** rapportage & export; bredere ruggengraat. **Open sporen** (detail in
OPVOLGPUNTEN.md): ADR-043-subknopen (8) · ADR-spoor registratie-feiten op objecten (twee
ankers: element + `relatie.id`; document = benoemde verwijzing) · spoor 2 proces→proces-flow
(urgentie gedaald; facade vergt type-borging) · rollenmodel · history-grens.

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
