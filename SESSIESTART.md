# SESSIESTART — LIKARA V050

**Datum**: 2026-07-23
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V050 — [N] skills geladen"
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

# SESSIE_BRIEFING.md — LIKARA V050

**Gegenereerd**: 2026-07-23

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V050 |
| Datum | July 2026 |
| Commit | d90629e |
| Tests | backend 1221 passed / 2 skipped · frontend 102 files / 1374 passed · vite build OK · css-build 14 scans OK · kopverwijzingen-scan groen |
| TST-rapport | TST-V050-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
d90629e [docs] LI049 opschoonplan zeven skills — kaart, borgingsbesluit, recept, vijf blokken, hygiëneborging (diagnose + drie verankeringen)
28e04a9 [docs] LI049 checkpoint resterende opschoning — chronologie-kaart negen skills, dubbelingen, collisions, dode verwijzing
5c4879a [skills] LI049 §Kernprincipe — LI035-bullet opgegaan in de prose; vangrail-lijstje en techniek+proces-conflictregel behouden; drie UX-first-momenten intact
c8d76b9 [docs] LI049 checkpoint UX-first — hermeting: drie momenten, binnen-kop-dubbeling, conflictvarianten
cc93de3 [frontend] LI049 check-css-build — gedrifte uitzondering-moraal vervangen door bewaakte verwijzing naar likara-tests §Bronscans; codespecifieke instructie verbatim behouden
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V050

**Gegenereerd**: 2026-07-23
**Vorige build**: V049 → **V050**
**Branch**: master
**Laatste commits (LI049)**: `a225a63`+`6ccdd53` kopverwijzingen-scan · `ae3f9ca` verhuizing 1
(werkprotocol-sessiekoppen) · `94c5625` verhuizing 2 (P8-leesvolgorde) · `201092d`/`558f39d`/
`87ab572` tests-consolidatie · `3c7268a` verhuizing 3 (§Bronscans) · `ff754eb` P8a-telling ·
`049c4c9` LI036-kaartregel · `cc93de3` mjs-verwijzing · `5c4879a` UX-first-Kernprincipe ·
`d90629e` opschoonplan

> **Sessie LI049 — de skills zijn weer één waarheid, en er staat voortaan een wachter bij.**
>
> Wat er ná LI049 anders is:
> - **Elke `skill §kop`-verwijzing wordt machinaal bewaakt** (kopverwijzingen-scan, in de
>   backend-suite; ving zich al drie keer op nieuw werk). Vijf beperkingen + werking staan in de
>   scan zelf gedocumenteerd.
> - **`werkprotocol` en `tests` zijn volledig op onderwerp geordend** (0 chronologische koppen);
>   de bronscan-eisen staan canoniek in `likara-tests §Bronscans`; dubbelingen zijn per geval
>   naar één bron gebracht met bewaakte verwijzingen.
> - **De resterende opschoning (7 skills, 82 koppen, 37%) is gemeten en gepland** —
>   `docs/Opschoonplan-zeven-skills.md` — maar **uitgesteld** (zie hieronder).

---

## LI050 = productie-gereedheidsspoor

**Er moet komende week een productieversie van LIKARA klaarstaan.** Daardoor kantelt de
planning: geen skill-opschoning, maar productie-gereedheid.

### Eerste stap: read-only inventarisatie — wat moet er écht vóór productie in

De bestaande "vóór productie"-lijst is opgesteld toen "geen actieve gebruikers, alleen
testdata" nog gold. Die aanname vervalt. Per bestaand vóór-productie-punt vaststellen:

- is het **van karakter veranderd** nu er echte gebruikers en echte data komen (wat in
  ontwikkelmodus een curiositeit was, kan in productie een risico zijn);
- is het **nu nog gratis** en later duur (schemastappen zijn kosteloos zolang er geen
  productiedata is; daarna zijn het datamigraties);
- of is het **na livegang net zo goed te doen**.

Pas op die geverifieerde grond bouwen — niet ervoor. De vier scherpste kandidaten staan
canoniek in `docs/OPVOLGPUNTEN.md` §"Nieuw uit LI049" (P50-1 t/m P50-4): de
checklistvraag-deactivering (poort + gevolg), de namenkaart zonder paginering, de
`organisatiegebruik.applicatie_id`-schemastap (laatste goedkope moment), en de
keuzelijsten-inventarisatie (beheerbaar vs. code-vast; verwant ADR-026).

### De skill-opschoning is UITGESTELD, niet vervallen

De volledige route ligt vast in **`docs/Opschoonplan-zeven-skills.md`**: de gemeten kaart
(7 skills, 82 chronologische koppen, 37% van alle skill-tekst), het bewezen vier-stappen-recept,
de vijf-blokken-indeling met pauzepunten, en de hygiëneborging in drie verankeringen. Het is
vindbaarheids-hygiëne, geen fout-herstel — het blokkeert geen bouwwerk en uitstellen kost niets
behalve tijd.

Wanneer hij wél draait: **eerste stap is het borgingsbesluit + de kop-vorm-scan** (verankering
3), anders keert de kwaal vrij terug. ⚠ De kop-vorm-scan kan **niet** vooruit gebouwd worden
als rem: hij staat meteen rood op de 82 bestaande koppen. Volgorde blijft: eerst opschonen, dan
borgen.

---

## Top-5 prioriteiten LI050

1. **Read-only inventarisatie productie-gereedheid** — de bestaande vóór-productie-lijst +
   P50-1 t/m P50-4 langs de drie vragen (karakter veranderd / nu gratis / kan later). Rapport,
   geen bouw.
2. **P50-1 Checklistvraag-deactivering meten** — poort (permissie) én gevolg (antwoorden +
   "Dit moet nog") — vóór livegang.
3. **P50-2 Namenkaart-limiet meten** — waar, welke limiet, welke schermen; dan pas de fix-vorm.
4. **P50-3 `organisatiegebruik.applicatie_id`** — Berts schemabesluit op het laatste goedkope
   moment (gate).
5. **P50-4 Keuzelijsten-inventarisatie** — beheerbaar vs. vast; protocol-lijst als aanleiding,
   ADR-026 als verwant patroon.

---

## Openstaande beslissingen

- **P50-3**: de kolom-hernoeming is schema-rakend — eigen gate, eigen besluit.
- **Import-lijn Tiel**: persoonsnamen in de bron (overnemen / functie / leeg) — geparkeerd.
- **Opschoonplan deel 2**: kop-vorm wél of niet machinaal borgen — beslist pas wanneer de
  opschoning start.
- **Demostand uittredende deelnemer**: startstap (read-only checkpoint op de dev-seed-knip)
  kan onafhankelijk van het productiespoor worden ingepland.

---

## Bekende risico's en aandachtspunten

- **Suites groen:** backend **1221 passed / 2 skipped** (incl. kopverwijzingen-scan) · frontend
  **102 files / 1374 passed** · vite build OK · css-build 14× OK (alle zelftests bijten) ·
  alembic **1 head** (`0073`), 0 branches · TST-V050: **0 kritieken**.
- **Migraties in LI049: 0** — de hele sessie was skill-/borging-werk; applicatiegedrag
  ongewijzigd.
- **De scan bewaakt verwijzingen, niet kop-vorm of dubbelingen** — de chronologie-kwaal in de 7
  resterende skills blijft onbewaakt tot het opschoonplan draait (bewust, zie hierboven).
- **Kop-naam-collisions** in backend/frontend/ux maken sommige `§`-verwijzingen ambigu
  (OPVOLGPUNTEN); geen actieve verwijzing raakt er nu een.
- **Tellingen in gate-rapporten zijn momentopnamen** — hermeten binnen de context blijft de
  regel (werkprotocol §Meet tenant-data).

---

## Geleerde patronen deze sessie

Verankerd in de skills/scan zelf (het sessiewerk wás skill-onderhoud); de scherpste:

- **Een verwijzing zonder bewaking is een belofte zonder houder** — de scan maakte 54–56
  verwijzingen hard en ving drie echte breuken vóór ze landden.
- **Verbatim verhuizen is bewijsbaar**: multiset-gelijkheid ("eruit = erin") maakt "geen letter
  anders" een assert i.p.v. een belofte (verhuizing 2, tests-stap 1).
- **De code wint van het rapport — ook van het eigen rapport**: drie keer gecorrigeerd
  (LI044-vet-anker "niet dood" · checkpoint-regelnummer over een regeleinde · "derde/derde"
  bleek met git-archeologie twee wáre tellingen).
- **Waar zoekt de gebruiker de regel** is de beslisregel die élke dubbeling-keuze deze sessie
  besliste — canoniek daar, elders één bewaakte verwijzing.
- **Een voltooide to-do die als open leest is een onwaarheid** (de ADR-040-onderhoudszin;
  de "(a) nog open"-notitie) — bij langslopen herstellen, niet laten staan.


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V050"
4. Wacht op START: [naam] van Bert

