# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V045 · 2026-07-18
- **Commit:** code `7e2ff25` ADR-052 slice 3 · `626dc76` slice 2 · `fae7593` slice 1 · `c82ad80` gate-4
  sloop; docs `f0fa9bd` LI044-patronen in skills. Afsluitcommit LI044 (ADR-052-update + NEXT_SESSION +
  OPVOLGPUNTEN + build) volgt in deze afsluiting.
- **Tests:** backend **1149 passed, 2 skipped, 0 failed** (80 platform + 1069 module) · frontend
  **92 files / 1175 passed** · `vite build` ✅ · `test:css-build` ✅ · 0 kritieken.
- **Migratie-head:** `0073_adr052_klaarverkl_snapshot` (1 head, 0 branches). ADR-052 slices 1–3 hebben
  schema geraakt: `component_norm` (0071), `component_bevinding` (0072), `component_klaarverklaring.open_feiten` (0073).
- **TST-rapport:** `docs/TST-V045-Validatierapport.md` (0 kritieken).
- **Dev-DB:** GEMMA-model intact. De dev-seed draagt nu norm + "bewust geen" + demo-klaarverklaringen die
  de vier normgevallen tonen (Archiefbeheer = beide: amber + verschoven; DMS/Zaaksysteem = beide;
  Klantportaal = pure verschoven lat na de bedoeling-toggle; **HR-systeem = SCHOON: volledig norm-compleet
  → géén signaal**, het ijkbeeld van "in orde" — S1/LI045). ⚠ Het volledige
  gate-3-verhaal (koppelingen, "hier draait niets", noodoplossing) is op een verse DB nog onzichtbaar (L4).
- **Werktree:** **schoon** — alle LI044-bouw is per opdracht apart geland (één opdracht per commit).

## Deze sessie (LI044 — tenant-norm gebouwd, procesregister-UI gesloopt) — AFGEROND

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
