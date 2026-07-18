# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V046 · 2026-07-18
- **Commit:** code `f8a9142` ADR-052 slice 4c · `d748fcf` 4b · `aaeeb15` 4a · `6a0931a` S1 (schoon geval) ·
  `3e74a47` C1 (feit-brug); docs `0c7860d` LI045-patronen in skills. Afsluitcommit LI045 (TST-V046 +
  NEXT_SESSION + OPVOLGPUNTEN + PROJECTGEHEUGEN + build) volgt in deze afsluiting.
- **Tests:** backend **1159 passed, 2 skipped, 0 failed** · frontend **93 files / 1202 passed** ·
  `vite build` ✅ · `test:css-build` ✅ · 0 kritieken.
- **Migratie-head:** `0073_adr052_klaarverkl_snapshot` (1 head, 0 branches). Slice 4 was **sleutelgestuurd**
  (nieuw feit = nieuwe sleutel in `component_norm`) — géén nieuwe migratie deze sessie.
- **TST-rapport:** `docs/TST-V046-Validatierapport.md` (0 kritieken).
- **Dev-DB:** GEMMA-model intact. De dev-seed draagt nu norm + "bewust geen" + demo-klaarverklaringen die
  de vier normgevallen tonen (Archiefbeheer = beide: amber + verschoven; DMS/Zaaksysteem = beide;
  Klantportaal = pure verschoven lat na de bedoeling-toggle; **HR-systeem = SCHOON: volledig norm-compleet
  → géén signaal**, het ijkbeeld van "in orde" — S1/LI045). ⚠ Het volledige
  gate-3-verhaal (koppelingen, "hier draait niets", noodoplossing) is op een verse DB nog onzichtbaar (L4).
- **Werktree:** **schoon** — alle LI045-bouw is per opdracht apart geland (één opdracht per commit).

## Deze sessie (LI045 — de gemeente legt haar eigen lat, geen besluit toegeschreven) — AFGEROND

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

## Prioriteiten volgende sessie (LI045 — zie NEXT_SESSION.md)
1. **Slice 4 — norm-beheerscherm** (maakt ADR-052 af; elke tenant zit vast aan de default tot dit er is).
2. **Open-punten-overzicht per component** (fundament staat nu de norm per component leesbaar is).
3. **Laatste MVP-laag functie-as (ADR-046 stuk 3 → 5 → 4)** — uitstap-stand/zwaarte/tranche.
4. **Dev-seed vertelt het volledige gate-3-verhaal (L4).**
5. **VeldUitleg adopteert `popoverPositie.js`** (borging niet af tot 75 views hem dragen).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
