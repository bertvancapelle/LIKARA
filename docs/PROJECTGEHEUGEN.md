# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V041 · 2026-07-14
- **Commit:** acht LI040-commits (`7148672` veldbouwsteen · `87dc120` ADR-045 ·
  `05e8a93` ADR-046 stuk 2 + identiteit · `b027095` stuk 1 levensfase/bedoeling ·
  `39eb2ef` filterbalk/resultaatregel/BIV · `feb27f9` leeg-vindbaar 0067 ·
  `3349905` geen-oordeel 0068 · `6cc7db0` detailkop) + afsluitcommit (skills + docs +
  build) volgt.
- **Tests:** backend 1095 (2 skipped) · frontend 92 files, 1199 groen · 0 kritieken
- **Migratie-head:** `0068_li040_geen_oordeel` (0066 levensfase + uitfaseren-recreate ·
  0067 onbekend→NULL · 0068 midden-defaults→NULL)
- **TST-rapport:** `docs/TST-V041-Validatierapport.md` (migratieketen 0001→0068 vanaf
  schoon bewezen op een scratch-DB; seed vertelt de user story — geen verzonnen defaults)
- **Dev-DB:** GEMMA-model intact; levensfasen gezaaid (Zaaksysteem=uitfaseren,
  ZAC=in ontwikkeling, 4× in productie, 13× leeg); bedoeling/complexiteit/prioriteit
  overal NULL ("nog niet vastgelegd").
- **Bekende ruis:** dubbeltap-timer-tests blijven belastinggevoelig (geen regressie).

## Deze sessie (LI040 — vier vragen, vier plekken; LIKARA verzint niets meer) — AFGEROND

**Kern: ADR-046** (levensfase · bedoeling · uitstap per gebruiker · tranche) vastgelegd
en de stukken 1+2 gebouwd; plus een consequente leegte-lijn en vier gedeelde bouwstenen.

- **ADR-045** (`87dc120`): "ondersteunt werk" = catalogus-eigenschap (geen lijst in code);
  422-fix maakte componenttype-toevoegen weer mogelijk; lijstfilter.
- **ADR-046 stuk 2** (`05e8a93`): invoerroute grof organisatiegebruik (tab "Gebruik",
  sorteerbare tabel die Stand/Tranche al draagt); verwijderen met verfijning eronder =
  409 mét telling (*"verdwijnt nooit stil"*). Identiteit geconvergeerd
  (`IdentiteitLabel.vue` + `partijIdentiteit`, faalt luid; 6 consumenten).
- **Stuk 1** (`b027095`): `Levensfase`-enum (vaste drie — vormkeuze A) nullable zonder
  default (vormkeuze B) op het component; `uitfaseren` uit `migratiepad` (0066,
  enum-recreate incl. default-drop-valkuil); plateau-dispositie afgebouwd
  (soft-deactivate, historie leesbaar); kaart leest levensfase — eerste-wint weg
  (alle plateaunamen, alfabetisch).
- **Leegte-lijn** (`feb27f9`/`3349905`): sentinel "onbekend" (0067) en de gratis
  "midden"-oordelen (0068) → échte NULL; overal gedempt "nog niet vastgelegd";
  ontbreekt-filters maken het gat vindbaar (de werkvoorraad); complementariteit getest
  (gat ∪ waarden = totaal). Vóór/ná gemeten bij elke migratie.
- **Filterbalk** (`39eb2ef`): resultaatregel ("3 van 19" + chips, los wisbaar,
  bouwsteen `FilterResultaatRegel`); Bedoeling-filter+kolom; BIV drie-per-as → één
  hoogste-as-filter (catalogus-gedreven) + "nog niet vastgelegd"; **één filterwaarheid**
  (`_pas_filters_toe` gedeeld door lijst én `tel`, bronscan-geborgd).
- **Detailkop** (`6cc7db0`): `DetailKop`-bouwsteen — acties bij het object (primair /
  statusovergang-alleen-als-kan / navigatie / destructief gescheiden); 8 detailschermen
  omgezet; detailkop-bron-scan met zelftest (naast de veld-scan).
- **Gemeten**: 0 verhangen plaatsingen in 9 maanden; 25/32 gebruiksfeiten grof-only
  (→ uitstap-stand op organisatiegebruik); signaal vuurt onterecht op 4 componenten
  (stuk 5 repareert).
- **38 patronen gevalideerd → 7 skills** (vindplaatsen + redenen; 2 expliciet als
  ontwerpbesluit gemarkeerd: bewust aanvinken · amber/neutrale taal).

## Prioriteiten volgende sessie — TOP-3 (zie NEXT_SESSION.md)
1. **ADR-046 stuk 3 — stand per gebruiker + Gebruik/Gebruikersgroepen één laag**
   (stand op de gebruiksrelatie; ⚠ grof+fijn niet in twee tabs laten staan; zwaarte
   geteld, amber, nooit rood).
2. **Stuk 5 — het liegende signaal** (`component_zonder_gebruikersgroep` telt voortaan
   op het grove feit; vuurt nu onterecht op 4 componenten).
3. **Stuk 4 — tranche** (naam + volgorde; periode optioneel; "nog niet ingedeeld" =
   signaal; geen planningstool).

**Daarna:** sentinel-besluiten (0a) · resultaatregel-uitrol (0) · gate 2/3-ontwerpeisen
(bedrijfsfunctie-doorwerking, fileshare-als-drager=gat, koppelen grof/fijn,
gap-per-plaatsing) · diagram-layout · gate 4 · klein: identiteitskopieën server-side (7),
ADR-047-sweep (8), spook-gebruik (4), contract-datums (5), aard-hint (11),
platform_init-lokaal (11a).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
