# SESSIE_BRIEFING.md — LIKARA V042

**Gegenereerd**: 2026-07-14

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V042 |
| Datum | July 2026 |
| Commit | 6d1b3fc |
| Tests | backend 1122 (2 skipped) / frontend 93 files, 1219 groen |
| TST-rapport | TST-V042-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
6d1b3fc [frontend] LI041: het oordeel staat waar het over gaat — veldnorm-fix — ADR-051
8cb3bcb [skills] LI041: de vorm bepaalt nooit de betekenis — kernregel + checkvraag + rollengrens — ADR-049/050/051
78ffd5e LI041: gate 3 — het gap-signaal per plek (ADR-051)
a5f8473 [docs] ADR-051 — gap-signaal per plek: wat draagt deze plek? (gate 3 stap 1)
8c2bf00 [docs] Feitenrapport gate 3 — het gap-signaal per plek (read-only checkpoint)
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V042

**Gegenereerd**: 2026-07-14
**Vorige build**: V042
**Branch**: master
**Laatste commit**: `6d1b3fc` (veldnorm-fix) · daarvóór `8cb3bcb` skills · `78ffd5e` gate 3 · `980587b` gate 2a + rollengrens · `8c2bf00`/`a5f8473` feitenrapport + ADR-051

> **Sessie LI041 — Blok A voor tweederde af: de consultant kan nu koppelen én zijn werkvoorraad zien.**
>
> Wat LI041 heeft opgeleverd (gebruikerstaal):
> - **Gate 2 (ADR-049) — de consultant hangt een systeem aan een bedrijfsfunctie**, grof
>   (*"ons handhavingssysteem ondersteunt Toezicht"* — geldt overal) of fijn (*"maar in Milieu
>   doen we het met de inspectie-app"* — op díé plek). Fijn verdringt grof **bij het lezen**; het
>   grove antwoord blijft bestaan en wordt weer leesbaar zodra je het fijne weghaalt. Eén gedeelde
>   leesregel (`dekking_overzicht`), geen `if` per scherm. `980587b`.
> - **Gate 3 (ADR-051) — het gap-signaal per plek.** Vier standen: *nog geen systeem · ondersteund
>   via een bovenliggende functie (hier niet bevestigd) · hier draait dit · hier draait niets —
>   vastgesteld.* Plus een oordeel op elke koppeling (*naar behoren / noodoplossing / nog niet
>   beoordeeld*). Twee vensters (de boom-cue + de centrale werkvoorraad) uit één afleiding
>   (`plek_standen`). `78ffd5e`.
> - **De rollengrens verschoven (ADR-050) — wie registreert, corrigeert.** Een registratie-feit
>   (een uitspraak) neemt de medewerker terug; een landschapsobject vernietigt de beheerder; de
>   modelinhoud verbouwt niemand. Structureel via `verwijder_actie()`, niet per route. Onderweg
>   geland, buiten het oorspronkelijke plan — ontstaan uit de vraag *"is een consultant een
>   beheerder of een gebruiker?"* Sloot en passant een beschermingsgat: de modelinhoud stond open
>   via het generieke relatie-endpoint (achterdeur) — nu gedicht.
> - **De patronen verankerd (skills):** één kernregel *"de vorm bepaalt nooit de betekenis"* (drie
>   gezichten, i.p.v. drie losse regels) · de adversariële checkvraag vóór de bouw · de
>   rollengrens · de bronscan-norm · de stale LI037-verwijder-regel herschreven. `8cb3bcb`.
> - **Eén veldnorm-schending gedicht:** de gate-3 oordeel-select overruled `.lk-veld` om in de
>   actie-strook te passen. Het oordeel staat nu waar het over gaat — de leeslaag-zin is klikbaar,
>   drie keuzes op volle grootte. `6d1b3fc`.
>
> Tests: backend **1122 (2 skipped)** / frontend **93 files, 1219** groen; TST:
> `TST-V042-Validatierapport.md` (**0 kritieken**). Migratie-head **0070**.

---

## Volgende stappen — Blok A afmaken (gate 4), dan blok B

> Bouwvolgorde ongewijzigd (herzien LI040→LI041): **de gates van de bedrijfsfunctie-as vóór het
> uitstapspoor.** Gate 2 + 3 zijn af; gate 4 is het sluitstuk van blok A.

### Blok A — de MVP-belofte (nog één gate)
- **Gate 1 — referentiemodel inlezen** ✅ (gate 1b)
- **Gate 2 — koppelen (ADR-049)** ✅ `980587b`
- **Gate 3 — het gap-signaal per plek (ADR-051)** ✅ `78ffd5e`
- **Gate 4 — VOLGENDE: de kaart rust op functies; het procesregister uit de MVP-UI (ADR-043).**
  Het veld *"PROCES"* in het componentformulier wordt een **bedrijfsfunctie**; het procesregister
  wordt **verborgen, niet verwijderd** (n≥2 — de LI038-bouw wordt hergebruikt). **Hierna is de
  logische kaart de MVP.**

  ⚠ **Begin met een read-only checkpoint** vóór er iets verandert:
  - Wat leest de kaart vandaag, en waar hangt het procesregister in de UI?
  - Wat raakt het **verbergen** van het procesregister — welke schermen/routes/tests?
  - **Niet verwijderen wat de kaart nodig heeft:** de kaart-lagenweergave gebruikt
    `ARCHITECTUUR.LEZEN` (proces-projectie als read-only subgraaf-verrijking). Verbergen ≠ slopen.

### Blok B — het uitstapspoor (ADR-046), ná blok A
Ongewijzigd t.o.v. LI040: stuk 3 (stand per gebruiker + Gebruik/Gebruikersgroepen één laag) →
stuk 5 (het liegende `component_zonder_gebruikersgroep`-signaal) → stuk 4 (tranche). Details en
ontwerpeisen: OPVOLGPUNTEN §"Nieuw uit LI040".

### Direct oppakbaar (klein, uit LI041 — OPVOLGPUNTEN L1–L7)
- ⭐ **L1** — een component verwijderen zou moeten vertellen wat er meegaat (ontwerpbesluit Bert:
  spiegel vs. weigering; urgenter sinds ADR-050 verwijderen breder neerlegt).
- **L2** — de guard-dekkingstest ontbreekt (modelinhoud-bescherming leunt op een afspraak).
- **L4** — de dev-seed vertelt het gate-3-verhaal niet (verse DB → gate 3 onzichtbaar).
- **L7** — de css-build-poort naar de per-commit-groencheck halen (liet een schending landen).

### Staande werkafspraken (ongewijzigd + LI041)
- Startregel: uitsluitend op `START: [naam]`; `AKKOORD: commit` exclusief door Bert in CC, letterlijk.
- **De vorm bepaalt nooit de betekenis** (kernregel LI041): geen tabel-/endpoint-/typefeit als
  bevoegdheids-/oordeelsregel; geen stille keuze; het scherm zwijgt nooit over wat het weet.
- **Adversariële checkvraag vóór de bouw**: waar een ontwerp een niet-besloten keuze maakt (tiebreak,
  categorie, vertrekpunt), stel eerst een read-only checkvraag — bouw niet door op een aanname die
  zich voordoet als een besluit.
- UX-first; browserverificatie is het sluitpunt (assert op zichtbare tekst); één taak per schone
  worktree; meten vóór besluiten; leeg ≠ fout maar wél vindbaar; fix in de bouwsteen met een scan
  die bijt.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V042 |
| Datum | 2026-07-14 |
| Tests | backend 1122 (2 skipped) / frontend 93 files, 1219 groen |
| Migratie-head | 0070_adr051_gapsignaal |
| TST-rapport | TST-V042-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | zes likara-skills bijgewerkt (LI041 — kernregel + checkvraag + rollengrens + bronscan-norm) |


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V042"
4. Wacht op START: [naam] van Bert
