# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V042 · 2026-07-14
- **Commit:** LI041-commits (`8c2bf00`/`a5f8473` feitenrapport + ADR-051 · `980587b`
  gate 2a + rollengrens · `78ffd5e` gate 3 · `8cb3bcb` skills · `6d1b3fc` veldnorm-fix)
  + afsluitcommit (TST + docs + build) volgt.
- **Tests:** backend 1122 (2 skipped) · frontend 93 files, 1219 groen · 0 kritieken
- **Migratie-head:** `0070_adr051_gapsignaal` (0069 functievervulling · 0070 gap-signaal:
  component_id nullable + geen_systeem + oordeel, XOR-CHECK)
- **TST-rapport:** `docs/TST-V042-Validatierapport.md` (0 kritieken; geen nieuwe migratie
  deze afsluiting — skills + frontend-fix raken het schema niet)
- **Dev-DB:** GEMMA-model intact; gate-2/3-registratie via de live gate-tests bewezen. ⚠ De
  dev-seed zaait nog géén koppelingen/bevinding/noodoplossing → gate 3 is op een verse DB
  onzichtbaar (OPVOLGPUNTEN L4).
- **Bekende ruis:** dubbeltap-timer-tests blijven belastinggevoelig (geen regressie).

## Deze sessie (LI041 — koppelen, gap-signaal, rollengrens) — AFGEROND

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
