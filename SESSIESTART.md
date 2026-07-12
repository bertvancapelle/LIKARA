# SESSIESTART — LIKARA V039

**Datum**: 2026-07-12
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V039 — [N] skills geladen"
5. Wacht op START: [naam] van Bert

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

## Opdrachtformaat CC-opdrachten (VERPLICHT — standaardwerkwijze)

claude.ai levert elke CC-opdracht ALTIJD aan als een .md-bestand
(downloadbaar), nooit als een los codeblok in de chat. Bert gebruikt dat
.md-bestand in CC. Deze afspraak geldt in elke sessie.

---

# SESSIE_BRIEFING.md — LIKARA V039

**Gegenereerd**: 2026-07-12

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V039 |
| Datum | July 2026 |
| Commit | d7df7e3 |
| Tests | backend 1001 (2 skipped) / frontend 84 files, 1089 groen |
| TST-rapport | TST-V039-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
d7df7e3 LI038 skill-review: kernles regel-vs-bouwsteen, useSleepbaar/ZoekSelect-faalmodus, proces-only-beeldpatronen, ADR-043-terrein
6c49ed3 LI038: ADR-043 bedrijfsfunctie als logische ruggengraat (herijkt ADR-042) + feitenrapport referentiemodel
f1d3270 LI038 gate 3: dubbelklik-inzoom op proces-ids + history + 'Toon in procesbeeld' vanuit de Boom
e91f2a2 LI038 gate 2: klik-popup in het proces-diagram + gedeelde useSleepbaar-overlay-sleep (v2)
82806ff LI038 gate 1: proces-only Diagram-weergave in Processen + ZoekSelect gekozen-waarde-is-label (v2)
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V039

**Gegenereerd**: 2026-07-12
**Vorige build**: V039
**Branch**: master

> **Sessie LI038 — Proces-only structuurbeeld geland + ADR-043: bedrijfsfunctie als logische
> ruggengraat (V039).**
>
> Afgerond in LI038:
> - **Proces-only structuurbeeld (3 gates, volledig geland):** Boom|Diagram-schakelaar in het
>   processen-scherm + api-vrij `ProcesDiagram` op `procesFocusSet` (keten boven / subboom
>   beneden / zusjes opzij) (`82806ff`) · klik-popup met drie gescheiden uitgangen (hele
>   landschap binnen het beeld / Bekijk op de kaart via de handoff / Open proces) +
>   geconvergeerde `useSleepbaar`-overlay-sleep (kaart-legenda en -popup draaien er nu ook op)
>   (`e91f2a2`) · dubbelklik-inzoom op **proces-ids** (`procesSubboomSet`, werkt bij 0
>   kinderen/0 vervullers) + snapshot+cursor-history met "← Terug" + "Toon in procesbeeld"
>   vanuit de Boom (`f1d3270`).
> - **ZoekSelect-bouwsteen-fix (picker-regel 4):** gekozen waarde = label, nooit filter —
>   klik-op-gefocust-veld opent de volle lijst + ×-wis-gebaar, platform-breed geërfd.
> - **ADR-043 (herijkt ADR-042):** de "waarvoor"-as verschuift van proces naar
>   **bedrijfsfunctie**; referentiemodel als eerste-klas begrip (GEMMA = instantie 1);
>   procesregister wordt in de MVP **verborgen, niet verwijderd** (`6c49ed3`, grond:
>   `Feitenrapport-referentiemodel-bedrijfsfuncties-V038.md`).
> - **Skill-review** (4 skills, `d7df7e3`) — kernles: *een regel in de skills is geen borging;
>   een gedeelde bouwsteen dwingt af.*
>
> Tests: backend **1001 (2 skipped)** / frontend **84 files, 1089** groen; TST:
> `TST-V039-Validatierapport.md` (0 kritieken). Migratie-head **0059** (geen schema deze sessie).

---

## Volgende stappen — HERZIENE TOP-5 (in deze volgorde)

**De oude TOP-5 is vervallen.** Die was gerangschikt toen het procesregister de "waarvoor"-as
was; ADR-043 heeft die grond verplaatst.

### 1. Bedrijfsfunctie-as + gevalideerde GEMMA-import *(= de MVP)*
Zonder dit is LIKARA geen logische kaart. Start: de **8 ADR-043-subknopen beslissen** +
read-only bouw-validatie (AMEFF-parse-route, subtype-recept-kosten, soft-vervallen op
elementen). Dwarsdoorsnede: het ADR-spoor "generieke registratie-feiten op objecten" **samen
ontwerpen** (de eigen-laag-bij-een-referentie-object is er een instantie van).

### 2. Kaart op functies + procesregister verbergen
Koppelregel component↔functie, gap-signalering ("functie zonder ondersteunend systeem"), kaart
rust op functies; procesmenu/-ingangen eruit (model blijft intact — hergebruik van de
LI038-bouw: boom/diagram/inzoom/history/gap-cue, n≥2-abstractie).

### 3. Beginscherm als enige vertrekpunt
Eerste indruk van de MVP: rustige lege start, filterkolom pas bij selectie; "Begin opnieuw" →
terug naar alleen het beginscherm.

### 4. Plaatstaat-herstel na onbedoelde onderbreking
Kwaliteitspunt, geen bestaanspunt — kan wachten tot de kaart klopt. lk-state overleeft
timeout/herlaad/browser-dicht zonder tijdslimiet; eerst read-only feitencheck
(Keycloak-sessieduur, waar lk-state leeft, privacy-randje).

### 5. Architectuur-scherm compleet verwijderen
Klein en goedkoop; kan tussendoor. Eerst read-only inventarisatie.
**KRITISCH: `ARCHITECTUUR.LEZEN` NIET verwijderen — de kaart gebruikt het.**

**Gezakt (blijven op de backlog):** rapportage & export; bredere ruggengraat. Je exporteert
pas iets als de kaart het juiste verhaal vertelt.

### Openstaand (detail + status in `docs/OPVOLGPUNTEN.md`)
ADR-043-subknopen (8) · ADR-spoor registratie-feiten op objecten (twee ankers) · spoor 2
proces→proces-flow (urgentie gedaald; facade vergt type-borging) · rollenmodel generiek vs.
functioneel · history-grens hele-landschap-herstel · detailscherm-procesbeheer ·
proces-ingang-weergave (productie-evaluatie).

### Staande werkafspraken (ongewijzigd)
- Startregel: uitsluitend op `START: [naam]`; `AKKOORD: commit` is de exclusieve commit-trigger
  (uitsluitend door Bert, rechtstreeks in CC — nooit in een opdracht-`.md`).
- UX-first: gebruikerservaring is het uitgangspunt, techniek is vangrail; browsercheck-bevindingen
  → patroon-onderzoek vóór punt-fixes; rol-gating browserchecken met béíde rollen.
- Gate-discipline: schema-/UX-slices stoppen met gate-rapport + browsercheck-draaiboek vóór commit;
  reikwijdte-scan vóór een klasse-fix; vitest altijd vanuit `frontend/`; backend-suite vanaf de
  repo-root.
- **Kernles LI038:** bij elke slice die een bestaande skill-regel raakt → read-only verifiëren dat
  de code de regel nakomt; regels borgen in gedeelde bouwstenen; fix in de bouwsteen, niet in de
  consument.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V039 |
| Datum | 2026-07-12 |
| Tests | backend 1001 (2 skipped) / frontend 84 files, 1089 groen |
| Migratie-head | 0059_adr042_procesvervulling |
| TST-rapport | TST-V039-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | vier likara-skills bijgewerkt (LI038: kernles regel-vs-bouwsteen, useSleepbaar, proces-only-beeld, ADR-043-terrein) |


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V039"
4. Wacht op START: [naam] van Bert

