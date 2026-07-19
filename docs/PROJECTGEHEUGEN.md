# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V047 · 2026-07-19
- **Commit:** code `6651f1f` relaties op hoedanigheid · `3a72b35` linkerkolom-gate · `9ee6fcb` terugkeer
  landt in de kaart · `61665a4` derde uitgang · `466eb7b`/`4dd1387`/`80d0038` slice 3/2/1; docs `aca7cb1`
  LI046-patronen · `f7929a9` checkpoints · `bf67e67` ADR-054 + register · `3b7941f`/`70f2cbb` skills.
  Afsluitcommit LI046 (TST-V047 + NEXT_SESSION + OPVOLGPUNTEN + PROJECTGEHEUGEN + build) volgt in deze afsluiting.
- **Tests:** backend **1159 passed, 2 skipped, 0 failed** · frontend **97 files / 1248 passed** ·
  `vite build` ✅ · `test:css-build` ✅ · 0 kritieken.
- **Migratie-head:** `0073_adr052_klaarverkl_snapshot` (1 head, 0 branches). LI046 was **puur frontend**
  (kaart-leesbaarheid + één-ingang) — géén schema- of migratiewijziging.
- **TST-rapport:** `docs/TST-V047-Validatierapport.md` (0 kritieken).
- **Dev-DB:** GEMMA-model intact. De dev-seed draagt norm + "bewust geen" + demo-klaarverklaringen die de
  vier normgevallen tonen (Archiefbeheer/DMS/Zaaksysteem = beide; Klantportaal = pure verschoven lat;
  **HR-systeem = SCHOON: norm-compleet → géén signaal**, het ijkbeeld van "in orde" — S1/LI045). ⚠ Het
  volledige gate-3-verhaal (koppelingen, "hier draait niets", noodoplossing) is op een verse DB nog
  onzichtbaar (L4).
- **Werktree:** **schoon** — alle LI046-bouw is per opdracht apart geland (één opdracht per commit).

## Deze sessie (LI046 — de kaart vertelt, het component verandert) — AFGEROND

**Kern: één ingang naar het detailscherm mét aanleiding; een linkerkolom alléén bij een getekende kaart; relaties gescheiden op hoedanigheid.**

- **ADR-054 — één ingang naar het detailscherm** (`80d0038`/`4dd1387`/`466eb7b`/`61665a4`/`9ee6fcb`).
  Gedeelde detail-ingang (`detailRoute`), de aanleiding in de URL, geen route zonder landing, het veld-anker
  (`?veld=`) markeert; per-ring-popup-takken; terugkeer landt bij het bewaarde beeld met een eerlijke melding
  bij een volledig verdwenen selectie (`lk-leeg-verdwenen`). Beginscherm-binnenkomst als één eenmalige regel
  ná de beslisboom (`3b7941f`, "de bezoeker wint").
- **Linkerkolom-gate** (`3a72b35`). De kijkinstellingen-kolom (`aside`) draagt `v-if="heeftData"` — bewust
  níét `!beginschermOpen`; kijken ≠ binnenkomen. Opgeslagen kijken + beheer naar het startpaneel
  (`KaartBeginscherm`, ✎/× + `magViewsBeheren`); Rol/BIV achter een inklap.
- **Relaties gescheiden op hoedanigheid** (`6651f1f`). `kaartBanen.js`: `hoedanigheidVan()`
  (roltoewijzing→beheer, anders relatietype), `baanVerdeling()` waaiert edges per knopenpaar met
  richting-gecorrigeerde `cpd` (`unbundled-bezier`); ná de instance-projectie (Lagen-veilig). Klik op een
  baan levert **alles** onder dat paar (`popupPaarLijst`). Ring-agnostisch — invariant boven afspraak.
- **Borging:** LI046-patronen in vier skills (`aca7cb1`/`70f2cbb`); vier read-only checkpoints (`f7929a9`/
  `bf67e67`); ADR-register 049–054 + statuscorrectie ADR-049/050/051 (kop+body).
- **Open (ontwerpbesluit Bert):** terugweg-fijnslijpen — org-scope/Rol-BIV/weergave/zoom-pan reizen niet mee
  terug; view-verwijderen zonder bevestiging; "selectie bijwerken" onbereikbaar; "bewust geen" niet in het
  gebruiksdata-model (OPVOLGPUNTEN §LI046).

## Sessie LI045 (de gemeente legt haar eigen lat, geen besluit toegeschreven) — AFGEROND

**Kern: de beheerder ziet en verzet de norm nu zelf; een verschoven lat leest niet meer als een keuze van de consultant.**

- **ADR-052 slice 4a/4b/4c.** Verschoven lat (neutraal) onderscheiden van bewuste afwijking (amber, `aaeeb15`);
  norm-beheerscherm met impact-voorspelling vóór opslaan + "wanneer/door wie" uit het audit-spoor (`d748fcf`);
  de lat zichtbaar tijdens invullen — één norm-"i" per feit op het kleinste omvattende element (`f8a9142`).
- **Integrale testronde** (`docs/TST-Normverhaal-V045.md`): 0 blokkerend · 1 storend (S1, gerepareerd
  `6a0931a` — HR-systeem als schoon ijkbeeld + borgtest) · 2 cosmetisch (C1 gerepareerd `3e74a47`
  — feit-brug; C2 bewust gelaten met reden).
- **ADR-053 (besloten, niet gebouwd):** Archiefwet als hard componentfeit (eigen enum, niet default-verplicht);
  bewaartermijn volgt uit zaaktype × resultaat → géén component-veld (grens vastgelegd).
- **Borging:** LI045-patronen in vier skills (`0c7860d`); frontend-skill-drift (VeldUitleg-adoptie) gecorrigeerd.

## Sessie LI044 (tenant-norm gebouwd, procesregister-UI gesloopt) — AFGEROND

**Kern: de gemeente kan nu haar eigen lat voor "migratieklaar" leggen; het procesregister is uit de MVP-UI.**

- **Gate-4 sloop (`c82ad80`).** Procesregister uit de MVP-UI: nav, routes, `ProcesLijst`/`ProcesDetail` +
  secties, `PartijProcessenSectie`, `ComponentProcessenSectie`, de kaart proces-ingang/-inzoom-handoff, de
  chip "Proceslandschap: X" en de doodlopende "Bekijk op kaart" opgeruimd. **Behouden:** datamodel
  (`proces`/`procesvervulling`), bouwstenen (`procesBoom`/`ProcesDiagram`/`useSleepbaar`), slapende
  backend-endpoints, bedrijfsfunctie-plek-machinerie. Concept geparkeerd (ADR-043), niet verwijderd.
- **ADR-052 tenant-norm — slice 1 (`fae7593`).** `component_norm` (tenant-scoped, RLS, migratie 0071);
  `HARDE_FEITEN` (10) + `DEFAULT_VERPLICHT` (eigenaar · verantwoordelijke · BIV · contract · koppelingen);
  `norm_status`-leesbron: "vastgesteld = echt antwoord" (sentinel `hostingmodel=onbekend` telt niet).
- **Slice 2 (`626dc76`).** "Bewust geen" voor koppelingen/contract: eigen `component_bevinding` (0072),
  write-guard (409 `REGISTRATIE_BESTAAT`) + read "real wins"; frontend geconvergeerd → één
  `BewustGeenControl.vue` (2 consumenten); generieke `relatie_service` onaangeroerd.
- **Slice 3 (`7e2ff25`).** Verrijkte klaarverklaring: snapshot-kolom `open_feiten` (0073); drempel alléén
  bij norm-afwijking; live badge vs. bevroren snapshot uit één definitie; klikbaar verantwoordingsvenster
  (3b); reden achter de waarschuwing i.p.v. permanent bij de status (3c); gedeelde `popoverPositie.js`
  (venster valt nooit buiten beeld, rekenkern puur + unit-getest). Engine ongemoeid (dubbele borging groen).
- **Borging (`f0fa9bd`).** LI044-patronen in vijf skills (W4/U1/U2/U3/D1/D2/D4/D5/D6/U4a + tests +
  werkprotocol). ADR-052 teruggevouwen naar de gebouwde realiteit. ADR-045 besluit 2 / "fileshare = gat"
  gemarkeerd verworpen (ADR-051 besluit 3); OPVOLGPUNTEN item 10 vervallen.

## Vorige sessies — AFGEROND
- **LI043** — gate-4 kaart-lezing (slice 2 → A → B1 → B2, `standCodering`), serving-richting-fix,
  brok-3 dev-seed, naam-fix "Beoordelingsstatus", zes sessiepatronen.
- **LI042** — gate 4 brok 1 (datalaag, `heeft_gebruikersgroep` + 5e stand `werkvoorraad`), skill-vastlegging.
- **LI041/LI040** — gate 2 koppelen + gate 3 vier standen + rollengrens ADR-050 · ADR-045/046.

## Prioriteiten volgende sessie (LI047 — zie NEXT_SESSION.md)
1. **Open-punten-overzicht per component** (fundament staat nu de norm per component leesbaar is; start met mockup).
2. **Dev-seed vertelt het volledige verhaal (L4)** — *randvoorwaarde: een seed die het geval niet kent maakt
   van elke browsercheck een gok.* Naast het gate-3-verhaal ook: partij die eigenaar én gebruiker is met
   meerdere beheerrollen (baan-scheiding op hoedanigheid), en een knooppaar met relaties van meerdere
   hoedanigheden (cross-ring overlap komt 0× voor in de dev-data).
3. **Archiefwet-feit bouwen (ADR-053)** — eigen enum-kolom + migratie, niet default-verplicht (raakt schema → gate).
4. **Laatste MVP-laag functie-as (ADR-046 stuk 3 → 5 → 4)** — uitstap-stand/zwaarte/tranche.
5. **Terugweg-fijnslijpen** — wat hoort in `lk-state` (org-scope/filter/weergave/zoom-pan); view-verwijderen + selectie-bijwerken (ontwerpbesluit).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
