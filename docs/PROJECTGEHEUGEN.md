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

## Prioriteiten volgende sessie — bouwvolgorde LI041 (HERZIEN ná de afsluiting; zie NEXT_SESSION.md)

> ⚠ Herzien besluit Bert (naloper op de afsluiting): **de gates van de
> bedrijfsfunctie-as gaan vóór het uitstapspoor** — de eerdere "stuk 3 → 5 → 4"-
> volgorde vervalt. De ADR-045/046-besluiten zelf veranderen niet. Reden: de
> MVP-belofte (*model inlezen → systemen aanhangen → gaten zien*) stopt vandaag na
> stap 1, en het uitstapverhaal wordt pas een bestuurlijk feit (i.p.v. een IT-lijstje)
> zodra componenten aan functies hangen — blok A maakt blok B waardevol.

- **Blok A — MVP afmaken (één verhaal, niet onderbreken):** gate 2 (koppelen
  component ↔ bedrijfsfunctie, grof/fijn — eerste échte waarde) → gate 3 (gap-signaal
  per plaatsing; fileshare-als-drager = GAT, niet groen) → gate 4 (kaart rust op
  functies; procesregister uit beeld; "PROCES"-veld → bedrijfsfunctie).
- **Blok B — uitstapspoor (ADR-046), ná blok A:** stuk 3 (stand per gebruiker +
  Gebruik/Gebruikersgroepen één laag) → stuk 5 (liegend signaal telt op het grove
  feit) → stuk 4 (tranche; geen planningstool).
- **Blok C — leesbaarheid (direct ná A):** diagram links→rechts bij 297 functies;
  beginscherm als enige vertrekpunt.
- **Blok D — opruimwerk:** sentinels (0a) · resultaatregel-uitrol (0) ·
  identiteitskopieën server-side (7) · ADR-047-sweep (8) · aard-hint (11) ·
  spook-gebruik (4) · plaatstaat-herstel · contract-datums (5) ·
  platform_init-lokaal (11a).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
