# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V043 · 2026-07-16
- **Commit:** `e0ff6d1` gate 4 brok 1 (leeslaag `heeft_gebruikersgroep` + 5e stand `werkvoorraad`) ·
  daarvóór `254f905` sessie-afsluiting LI041 · `6d1b3fc` veldnorm-fix. Afsluitcommit LI042 (skills
  7-punts + afsluit-docs + build) volgt in deze afsluiting.
- **Tests:** backend **1130 passed, 2 skipped, 2 failed** (de 2 failures zijn pre-existing
  audit-keten-tests over de dev-`audit_log` — geen regressie) · 0 kritieken.
- **Migratie-head:** `0070_adr051_gapsignaal` — **geen schema-wijziging deze sessie** (brok 1 is
  read-only afgeleid; head ongewijzigd).
- **TST-rapport:** `docs/TST-V043-Validatierapport.md` (0 kritieken).
- **Dev-DB:** GEMMA-model intact. ⚠ De dev-seed vertelt het gate-4-verhaal (5 standen, mét/zonder
  gebruikersgroep, meervoud-plek) nog NIET → gepland als **gate 4 brok 3** (seed-verhaal).
- **Bekende ruis:** dev-`audit_log`-ketenbreuk (rij 2026-07-14) laat 2 live-tests falen (data,
  geen code); dubbeltap-timer-tests belastinggevoelig (geen regressie).
- **Werktree:** gate 4 slice 2 (kaart-swap) blijft **bewust ongecommit** — ontwarren is stap 1
  volgende sessie (DC016).

## Deze sessie (LI042 — gate 4 brok 1 + skill-vastlegging) — AFGEROND

**Kern: het fundament onder de bedrijfsfunctie-kaart, plus de patronen verankerd.**

- **Gate 4 brok 1 (datalaag, `e0ff6d1`):** de leeslaag kent per dekkend systeem `heeft_gebruikersgroep`
  (afgeleid uit de bestaande serving-relatie component→gebruikersgroep, batch, read-only — géén tweede
  query-conventie) en de plek een **5e stand `werkvoorraad`**: systeem bekend, gebruiker nog niet.
  **Streng criterium** — één dekkend systeem zonder gebruikersgroep maakt de plek al werkvoorraad. Geen
  schema, head 0070. Borging `test_gapsignaal_adr051.py` (split + leeslaag-vlag).
- **Gate 4 slice 1 + herstel (vorig sessie-einde gecommit):** koppelen vanuit het component,
  "Bedrijfsfunctie" als eigen tabblad + werkvoorraad-gat "systeem zonder bedrijfsfunctie".
- **Gate 4 slice 2 (kaart-swap — GEBOUWD, ongecommit):** proceslaan → bedrijfsfunctie-plek-laan met
  path-expansie. Tests groen. Blijft staan voor de ontwarring volgende sessie.
- **Skill-vastlegging (7 punten, deze afsluiting gecommit):** kleur = de *actieve* kaart-lezing (niet
  absoluut status — herziening) · één lezing → één render-kanaal (P1) · afgeleide-stand-exemplaren
  onder het bestaande recept (P2) · meebewegende legenda + `kleurOpDomein`-gat (P3) · checkpoint-vóór-
  vorm (P4) · parallelle read-only worktrees (P5) · tool-cadans `/doctor`·`/security-review`·
  `/code-review ultra` (P7). Geverifieerd tegen de echte CC-setup; geen dubbele waarheid.
- **Read-only geverifieerd (voor brok 2/3):** kanaal-isolatie werk/status/domein; sloop-grens; 8
  organisaties in de seed (feitenrapport gate-4 slice-3). Serving-richting-bug in `registratiegaten`
  ontdekt en gemeld (fix = stap 2 volgende sessie).

## Vorige sessie (LI041 — koppelen, gap-signaal, rollengrens) — AFGEROND

**Kern: blok A voor tweederde af** — de consultant kan nu een systeem aan een bedrijfsfunctie
hangen (gate 2) en per plek zijn werkvoorraad zien (gate 3); onderweg verschoof de rollengrens.

- **Gate 2 (ADR-049, `980587b`):** koppelen grof (*"geldt overal"*) of fijn (*"alleen hier"*,
  per plek — geadresseerd via functie + ouder-functie, niet `relatie.id`). Fijn verdringt grof
  **bij het lezen** (leeslaag, nooit opgeslagen); het grove blijft bestaan en wordt weer leesbaar
  bij weghalen. Eén gedeelde afleiding `dekking_overzicht`, bronscan-geborgd tegen een tweede
  implementatie. Tabel `functievervulling` (migratie 0069).
- **Gate 3 (ADR-051, `78ffd5e`):** vier standen per plek (nog geen · via-boven-cue · hier draait
  dit · niets vastgesteld) + een oordeel op de koppeling (naar behoren / noodoplossing / leeg).
  `functievervulling` draagt nu óók "geen systeem — vastgesteld" (component_id nullable +
  geen_systeem, **XOR-CHECK**; migratie 0070). Twee vensters (boom-cue + centrale werkvoorraad)
  uit één afleiding `plek_standen`. De omhoog-cue **telt** dragende voorouders i.p.v. er stil één
  te kiezen (`_dichtstbijzijnde_dragers` → `(aantal, enige)`).
- **Rollengrens (ADR-050, `980587b`):** wie registreert, corrigeert — een registratie-feit neemt
  de medewerker terug (`WIJZIGEN`), een landschapsobject vernietigt de beheerder (`VERWIJDEREN`),
  de modelinhoud verbouwt niemand. Structureel via `verwijder_actie()` + frozensets, niet per
  route (borging `test_rollengrens_adr050`). Sloot en passant het beschermingsgat: de modelinhoud
  stond open via het generieke relatie-endpoint (achterdeur) — nu `_weiger_modelinhoud`.
- **Skills (`8cb3bcb`):** één kernregel *"de vorm bepaalt nooit de betekenis"* (drie gezichten,
  i.p.v. drie losse regels) · de adversariële checkvraag vóór de bouw · de rollengrens · de
  bronscan-norm · de stale LI037-verwijder-regel herschreven naar een categorie.
- **Veldnorm-fix (`6d1b3fc`):** de gate-3 oordeel-select overruled `.lk-veld` (css-poort rood
  sinds `78ffd5e`); het oordeel wordt nu vanaf de klikbare leeslaag-zin bediend, drie keuzes op
  volle grootte, geen override. Norm niet versoepeld (scan bijt).
- **Vorige sessie:** LI040 (ADR-045/046 — levensfase/bedoeling/uitstap; leegte-lijn; vier
  bouwstenen; 38 patronen → 7 skills). Volledig in `TST-V041` + git-historie.

## Prioriteiten volgende sessie (zie NEXT_SESSION.md)

> Bouwvolgorde ongewijzigd: de gates van de bedrijfsfunctie-as vóór het uitstapspoor.
> Gate 2 + 3 zijn af; **gate 4 is het sluitstuk van blok A.**

1. **Gate 4 — de kaart rust op functies; procesregister uit de MVP-UI (ADR-043).** Het
   "PROCES"-veld in het componentformulier wordt een bedrijfsfunctie; het procesregister
   wordt verborgen, niet verwijderd. ⚠ **Begin read-only:** wat leest de kaart, wat raakt
   het verbergen — en **niet slopen wat de kaart nodig heeft** (`ARCHITECTUUR.LEZEN`).
2. **Blok B — uitstapspoor (ADR-046):** stuk 3 (stand per gebruiker + Gebruik/
   Gebruikersgroepen één laag) → stuk 5 (liegend signaal) → stuk 4 (tranche).
3. **Klein uit LI041 (OPVOLGPUNTEN L1–L7):** ⭐ L1 — verwijderen vertelt wat er meegaat
   (ontwerpbesluit Bert) · L2 — guard-dekkingstest ontbreekt · L4 — dev-seed vertelt gate 3
   niet · L7 — css-poort naar de per-commit-check.
4. **Opruimwerk (blok D):** sentinels (0a) · resultaatregel-uitrol (0) · fantoom-ADR-sweep
   047+048 (8) · identiteitskopieën server-side (7) · spook-gebruik (4) · platform_init-lokaal
   (11a).

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote hernoemen; lokale map opruimen. Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken + re-provision.
- **OP-30** — env-test-robuustheid `cookie_secure` expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar nooit gevuld.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
