# LIKARA Changelog V038

**Datum**: 2026-07-11

## Wijzigingen

Sessie LI037 — Deelprocessen eerste-klas + tree-view-procesbeheer.

- **Deelprocessen eerste-klas op de kaart (fase 0–4, ADR-034-amendement).** Seed naar 3
  procesniveaus + gap-deelproces (`ba6f688`); backend subboom-projectie — elk subboom-lid als
  knoop, hiërarchie-edges "onderdeel van", vervult-edges op het geregistreerde (deel)proces,
  selectie-schaal, één roll-up-bron (`8904b2a`); proceszone als boom + registratiegap-cue met
  subboom-semantiek (`4a29f2a`); twee proces-ingangen (ProcesDetail + "Via proces") via één
  handoff, herkomst = oranje selectie + centrering (`932f607`); dubbelklik-inzoom =
  set-inperking met history-terugweg (`a970fac`).
- **Seed-idempotentie.** Verantwoordelijken-blok op vaste identiteit, twee-runs-stabiel
  (`ef2421f`).
- **Tree-view procesregister.** Verbindingslijnen op de gedeelde `procesBoomStructuur` +
  gap-cue (`ca6501a`); verwijderen (409 leesbaar) + verhangen met kring-preventie-vóóraf en
  N-kinderen-bevestiging (`ed0799b`).
- **Gating-/vorm-consistentie.** Destructieve acties op 6 plekken vooraf gegate op het
  VERWIJDEREN-recht (`magVerwijderen`); ProcesLijst-rij-acties als Buttons, destructief =
  danger (`d4b7266`). RBAC-matrix ongewijzigd.
- **Borging.** 12 patronen in vier likara-skills + zes nieuwe opvolgpunten (`d87aad7`).

Tests: backend 1001 (2 skipped) / frontend 81 files, 1046 groen · 0 kritieken ·
migratie-head 0059 (geen schema-wijziging). TST: `docs/TST-V038-Validatierapport.md`.
