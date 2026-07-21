# Checkpoint — skillconsolidatie (READ-ONLY meting)

**Sessie:** LI049 · **Build bij aanvang:** V049 · **Branch:** master · **HEAD:** `477565f`
**Datum meting:** 2026-07-21 · **Aard:** READ-ONLY — er is niets gewijzigd, verplaatst of gecommit.

Alle getallen in dit rapport zijn **vers gemeten** tegen de werktree op `477565f`; getallen uit
NEXT_SESSION.md (het voorstel) zijn hermeten, niet overgenomen. Afwijkingen staan per blok én
verzameld in §Afwijkingen.

---

## Blok 1 — `likara-werkprotocol`: koppen en concurrentie

Bestand: `.claude/skills/likara/likara-werkprotocol/SKILL.md`

### 1.1 Totaal

**638 regels** (`wc -l`). Frontmatter: r1–8 (8 regels). Het voorstel zei 621 — **afwijking, zie §Afwijkingen**.

### 1.2 Alle koppen met omvang

Omvang = kopregel t/m de regel vóór de volgende kop van gelijk of hoger niveau.
`##`-secties tellen hun `###`-subsecties mee; bij de twee grote secties staat de "eigen tekst"
(vóór de eerste subsectie) apart. Som van alle `##`-secties + frontmatter = 638 (sluitend).

| Regel | Niveau | Kop | Bereik | Regels |
|---:|---|---|---|---:|
| 9 | ## | Kernprincipe — niet-onderhandelbaar | 9–22 | 14 |
| 23 | ## | KERNLES LI038 — een regel in de skills is geen borging… | 23–71 | 49 |
| 72 | ## | Scope voeren op de ids van je eigen domein (LI038) | 72–82 | 11 |
| 83 | ## | Interactieregels (claude.ai — PNA-rol) | 83–96 | 14 |
| 97 | ## | CC-opdrachtenformaat (niet-onderhandelbaar) | 97–106 | 10 |
| 107 | ## | Commit-discipline | 107–167 | 61 (eigen tekst 107–125 = 19) |
| 126 | ### | Stapelen in één werktree… (ADR-040) | 126–132 | 7 |
| 133 | ### | Verstrengelde werktree ontwarren… (LI046) | 133–142 | 10 |
| 143 | ### | Parallelle read-only sporen in een eigen worktree (LI042) | 143–167 | 25 |
| 168 | ## | Gate-discipline (CC) | 168–309 | 142 (eigen tekst 168–179 = 12) |
| 180 | ### | Sneden die dezelfde functie ontsluiten… (LI047) | 180–189 | 10 |
| 190 | ### | Read-only-eerst boven aannames (ADR-040) | 190–205 | 16 |
| 206 | ### | Meet tenant-data BINNEN de tenant-context (LI047) | 206–220 | 15 |
| 221 | ### | Een typegebonden beperking zónder ADR… (ADR-055/LI047) | 221–234 | 14 |
| 235 | ### | Een bewijs over de GEWIJZIGDE bestanden… (LI047) | 235–250 | 16 |
| 251 | ### | Reikwijdte-scan vóór een klasse-fix (LI037) | 251–259 | 9 |
| 260 | ### | Adversariële checkvraag vóór de bouw (LI041) | 260–291 | 32 |
| 292 | ### | Herijk de fasering als stappen niet los toetsbaar blijken | 292–297 | 6 |
| 298 | ### | Vraag geen metadata over een gebeurtenis… (LI045) | 298–309 | 12 |
| 310 | ## | Browsercheck vóór commit — niet-optioneel… (LI032) | 310–410 | 101 |
| 411 | ## | Tool-cadans richting productie (LI042 — vaste stappen) | 411–432 | 22 |
| 433 | ## | Geen schuld laten ontstaan (LI032) | 433–458 | 26 |
| 459 | ## | CC-autonomiescope | 459–467 | 9 |
| 468 | ## | Structurele oplossing — niet-onderhandelbaar | 468–477 | 10 |
| 478 | ## | UX-first als correctieprotocol | 478–490 | 13 |
| 491 | ## | Operationele afspraken | 491–504 | 14 |
| 493 | ### | Stack opstarten | 493–504 | 12 |
| 505 | ## | UX-first analysekader (LI024, bevestigd werkprotocol) | 505–521 | 17 |
| 522 | ## | ADR-onderhoud — bijwerken naar de gebouwde realiteit (ADR-040) | 522–528 | 7 |
| 529 | ## | Keuze-sortering vóór je iets onthoudt (LI034, pointer) | 529–534 | 6 |
| 535 | ## | LI035 — UX-first-aanscherping + browsercheck-als-patroonbron | 535–550 | 16 |
| 551 | ## | LI036 — set-acties wijzigen nooit de weergave | 551–560 | 10 |
| 561 | ## | LI039 — werkprotocol-aanscherpingen | 561–592 | 32 |
| 593 | ## | LI040 — sessielessen (gevalideerd) | 593–613 | 21 |
| 614 | ## | LI048 — een inventarisatie is een meting, geen indruk | 614–638 | 25 |

**Telling koppen:** 22 `##` + 13 `###` = **35 koppen totaal**. Het voorstel zei "22 koppen" —
dat klopt voor alleen het `##`-niveau.

### 1.3 Chronologische koppen en waar hun inhoud thuishoort

**Zuiver chronologische verzamelbakken (titel = sessienummer + grabbelzak): 5** —
LI035, LI036, LI039, LI040, LI048. Samen **104 regels** (16+10+32+21+25; voorstel zei 105 — −1).

Niet meegeteld als verzamelbak (sessienummer in de titel, maar de titel benoemt één onderwerp):
`KERNLES LI038` (r23), `Scope voeren… (LI038)` (r72), en 10 van de 13 `###`-koppen met een
`(LIxxx)`-suffix. Die concurreren niet — hun kop zegt waar ze over gaan.

Per verzamelbak, per alinea (voorstellen zijn één regel, niets is uitgevoerd):

**LI035 (r535–550):**
| Regels | Inhoud | Hoort bij |
|---|---|---|
| r537–540 | UX-first is áltijd het uitgangspunt | §Kernprincipe (r9) |
| r541–543 | kort/bondig; vragen één-voor-één; opdrachten als `.md` met `START:` | §Interactieregels (r83) + §CC-opdrachtenformaat (r97) |
| r544–549 | browsercheck-bevindingen zijn patroon-signalen, geen punt-fixes | §Browsercheck vóór commit (r310) |

**LI036 (r551–560):**
| Regels | Inhoud | Hoort bij |
|---|---|---|
| r553–559 | set-acties muteren uitsluitend de set, nooit de weergave (herziening ADR-040) | geen bestaande werkprotocol-kop past — het is een kaart-gedragsregel; voorstel: likara-ux §LI036 — kaartpatronen (ux r752) |
| r559 (slotzin) | "hoort óók terug in ADR-040 — staat op de ADR-onderhoudslijst" | §ADR-onderhoud (r522) |

**LI039 (r561–592):**
| Regels | Inhoud | Hoort bij |
|---|---|---|
| r563–564 | disclaimer "alle regels hieronder zijn tekst-regels zonder bouwsteen" | vervalt bij verplaatsing (contextregel van de bak zelf) |
| r566–570 | read-only-eerst tweemaal herbewezen — noemt zichzelf "aanvulling op §Read-only-eerst" | §Read-only-eerst (r190) |
| r571–576 | telling vóór besluit — noemt zichzelf "aanscherping op §Reikwijdte-scan" | §Reikwijdte-scan (r251) |
| r577–580 | convergentie-vorm: tweede export in dezelfde module — "aanvulling op de KERNLES" | §KERNLES LI038 (r23) |
| r581–584 | nieuwe dependency ⇒ image herbouwen; deploy-consequentie in het gate-rapport | geen exact passende kop; voorstel: §Gate-discipline (r168) |
| r585–590 | migratie: bouw én toepassing binnen dezelfde slice | voorstel: §Gate-discipline (r168); inhoudelijk deels likara-db-materie |

**LI040 (r593–613):**
| Regels | Inhoud | Hoort bij |
|---|---|---|
| r595–598 | browserverificatie-faalmodus: stil niet-geresolvede Vue-component | §Browsercheck (r310) |
| r599–602 | volle CC-sessie ⇒ verse sessie + overdrachts-`.md` | geen bestaande kop past; voorstel: eigen kop "Sessiecapaciteit en overdracht" (raakt ook CLAUDE.md §Sessiebewaking) |
| r603–608 | reproduceerbaarheid externe bronnen (`HERKOMST.md`, commit-hash + SHA-256) | geen werkprotocol-kop; staat inhoudelijk al in likara-domeinmodel §LI039/ADR-044 (de passage verwijst er zelf naar, r607) |
| r609–612 | bedieningskennis hoort in `docs/LOKAAL-TESTEN.md` | §Browsercheck (r310) — draaiboek-randvoorwaarde |

**LI048 (r614–638):** één samenhangend onderwerp (incident r616–626 + drie regels r628–638:
tel het ding zelf · checkpointtabel = teller per cel · rapport wijkt af ⇒ rapport is fout).
Hoort bij §Meet tenant-data BINNEN de tenant-context (r206) — zelfde familie ("een rapport is
geen meting"); alternatief: beide samen onder één nieuwe onderwerpskop "Meten en rapporteren".

### 1.4 UX-first-plekken

**4 plekken** (voorstel sprak van "drie UX-first-koppen" — het zijn 3 koppen + 1 bullet):

| Regels | Kop | Uniek element dat bij samenvoegen behouden moet blijven |
|---|---|---|
| r9–22 | §Kernprincipe | de benoeming van het faalpatroon ("te snel de techniek in duiken") + "Correctie: terug naar de gebruikersvraag. Altijd." |
| r478–490 | §UX-first als correctieprotocol | de 3-staps stopprocedure + conflictregel "gebruikerservaring wint" |
| r505–521 | §UX-first analysekader (LI024) | het 4-vragenkader + twee verboden ("analyse die bij stap 4 begint is een overtreding"; "advies zonder stap 1–3 mag niet") |
| r537–540 | LI035, bullet 1 | **niets unieks** — herformulering van r9–22 ("techniek… zijn vangrails") |

Alle vier zeggen dezelfde kernregel; de unieke elementen zitten in kolom 3. Bullet r537–540 is
zonder verlies samenvoegbaar; de drie koppen dragen elk iets eigens.

### 1.5 §Gate-discipline en bestandsoperaties

§Gate-discipline: **142 regels** (r168–309) — klopt met het voorstel.

Bestandsoperatie-passages (commando-gedrag, backups, verwijderpatronen) binnen Gate-discipline:
**0 regels aangetroffen.** Die passages staan al onder **§Browsercheck**:
- r321–335 — "Een bestandsoperatie doet niet wat hij leest" met de vier faalvormen (glob, shell-variabele, dubbele basename, knip/regex);
- r336–339 — de regel (paden expliciet, `-print` eerst, backupnaam uit het volledige pad);
- r340–345 — "de verificatie achteraf is de belangrijkere helft".

Dichtstbijzijnde kandidaat bínnen Gate-discipline is §"Een bewijs over de GEWIJZIGDE bestanden"
(r235–250), maar die gaat over verificatie-reikwijdte na een hernoeming (aanroepers repo-breed),
niet over bestandsoperaties. **De voorstel-bewering is niet bevestigd — zie §Afwijkingen.**

### 1.6 Dubbelingen (benoemd, niet opgelost)

1. **UX-first ×4** — r9–22 · r478–490 · r505–521 · r537–540 (zie 1.4).
2. **Interactieregels/opdrachtformaat ×2** — r83–96 + r97–106 ↔ LI035 r541–543.
3. **Read-only-eerst ×2** — r190–205 ↔ LI039 r566–570 (zelfbenoemde aanvulling).
4. **Reikwijdte-scan/telling ×2** — r251–259 ↔ LI039 r571–576 (zelfbenoemde aanscherping).
5. **Convergentie ×3** — §KERNLES r23–71 ↔ LI039 r577–580 ↔ §Geen schuld r438–440 ("tweede implementatie → convergeren").
6. **Rapport ≠ meting ×2** — §Meet tenant-data r206–220 ↔ §LI048 r614–638.
7. **Browsercheck ×3** — §Browsercheck r310–410 ↔ LI035 r544–549 ↔ LI040 r595–598.

**Tegenspraken: 0 aangetroffen.** Alle overlappingen zijn versterkend/aanvullend geformuleerd.

---

## Blok 2 — `likara-ux`: de P-reeks

Bestand: `.claude/skills/likara/likara-ux/SKILL.md` (1079 regels).

### 2.1 Volgorde in het bestand vs. leesvolgorde

| # | In het bestand | Regel | Verwachte leesvolgorde |
|---|---|---:|---|
| 1 | P6b | 277 | P6b |
| 2 | P8 | 284 | P8 |
| 3 | P9 | 300 | P8a |
| 4 | P8d | 329 | P8b |
| 5 | P8c | 357 | P8c |
| 6 | P8b | 389 | P8d |
| 7 | P8a | 422 | P9 |

De P8-subreeks staat exact **omgekeerd** (P8d→P8c→P8b→P8a); elk nieuw stuk is vóór het vorige
ingevoegd. Het voorstel ("P8 → P9 → P8d → P8c → P8b → P8a") klopt, maar noemde P6b (r277) niet.

### 2.2 Gaten en dubbelen — de reeks leeft in VIER skills

Binnen likara-ux: geen dubbele nummers. Repo-breed (alle likara-skills):

| P | Vindplaats | Vorm |
|---|---|---|
| P1 | likara-frontend r1645 (kaart-kleur-lezing, LI042) | bullet, geen kop |
| P2 | alleen likara-security r96: "PKCE login/callback (P2, geïmplementeerd — ADR-002)" | vermoedelijk een fase-aanduiding, géén reekslid — **niet vast te stellen** |
| P3 | likara-frontend r1219 (legenda beweegt mee, LI042) | bullet, geen kop |
| P4 | likara-domeinmodel r619 | ###-kop |
| P5 | ontbreekt; wel **P5a** likara-frontend r562 | ###-kop |
| P6a | likara-frontend r576 | ###-kop |
| P6b, P8, P8a–d, P9 | likara-ux (tabel 2.1) | ###-koppen |
| P7 | **ontbreekt volledig** (0 hits repo-breed) | — |
| P10, P11 | likara-resilience r103, r110 | ###-koppen |

Gaten: P5 (alleen P5a), P7. De spreiding over vier skills is zelf een bevinding: wie "de
P-reeks" in likara-ux zoekt, vindt 7 van de ~13 leden.

### 2.3 Onderlinge P-verwijzingen (binnen likara-ux)

| Van | Regel | Naar |
|---|---:|---|
| P8d | 331 | "Vierde in de lijn van §P8a–c" |
| P8c | 359 | "Derde in dezelfde lijn als §P8a en §P8b" |
| P8b | 391–392 | "De tweelingregel van §P8a … P8a gaat over een filter dat hij niet ziet" |
| P8a | 424 | "Derde instantie van dezelfde lijn" (impliciet, zonder nummer) |
| §Eerlijk gaten tonen | 673 | "(aanvulling op P8)" |
| §LI039 (lege uitkomst) | 860 | "(aanvulling op P8)" |
| §LI046 (verborgen instelling) | 1063 | "(§P8)" |
| ADR-040-noot | 215 | "het herbruikbare patroon in P6a (likara-frontend)" |

⚠ De volg-teksten "derde/vierde in de lijn" beschrijven de **schrijfvolgorde**, die na
herordening niet meer klopt met de leesvolgorde — bij herordenen herformuleren.

### 2.4 Verwijzingen naar een specifieke P búíten likara-ux

| Vindplaats | Regel | Verwijst naar |
|---|---:|---|
| likara-backend/SKILL.md | 476 | likara-ux §P8b |
| likara-frontend/SKILL.md | 1114 | likara-ux §P8b |
| likara-frontend/SKILL.md | 1469 | likara-ux §P8a |
| likara-frontend/SKILL.md | 1698 | likara-ux §P9 |
| modules/bwb_ontvlechting/backend/services/auditlog_service.py | 264 | likara-ux §P8a (docstring) |
| modules/bwb_ontvlechting/backend/services/auditlog_service.py | 355 | §P8b (comment) |
| docs/OPVOLGPUNTEN.md | 1922, 1935 | §P8a (2×) |
| docs/OPVOLGPUNTEN.md | 1970 | likara-ux §P9 |
| docs/OPVOLGPUNTEN.md | 2047 | likara-ux §P8b |
| NEXT_SESSION.md | 161 | likara-ux §P8a |

Frontend-code en -tests: **0** P-verwijzingen. Totaal buiten likara-ux: **11 vindplaatsen**
(2 in productiecode). Herordening (volgorde wisselen) breekt geen van deze; **hernummeren wel** —
inclusief de twee code-vindplaatsen.

---

## Blok 3 — de drie borgingsregels in `likara-frontend`

Alle drie staan onder de kop **"## LI040-patronen — bouwstenen + bron-scan-handhaving
(gevalideerd)"** (likara-frontend r1679).

### Regel A — "het bereik van een scan versmalt stiller"

1. **Vindplaats:** likara-frontend **r1741–1757** (bullet "LI048 snede 2 — het BEREIK van een
   scan is even belangrijk als zijn regels, en versmalt stiller").
2. **Signalering klopt.** De voorbeelden zijn frontend (lijstkop-scan, `AppLayout.vue`-routes,
   `@modules`-alias), maar de drie sub-eisen zijn algemeen: (1) niet-resolvebaar pad faalt LUID,
   nooit `continue`; (2) het criterium mag het bestaande bereik niet uitsluiten (ratel);
   (3) toets het getal in een suite. Geen van de drie is frontend-gebonden.
3. **In likara-tests:** afwezig (0 hits op "bereik"/"versmalt"). Verwant maar níet hetzelfde:
   de bijt-eis (tests r452–455).
4. **Verwijzers:** geen andere skill; geen ADR; NEXT_SESSION/OPVOLGPUNTEN noemen dit patroon
   niet met vindplaats-verwijzing naar likara-frontend.

### Regel B — "een uitzondering in een scan is een precedent/achterdeur"

1. **Vindplaats:** twee passages in likara-frontend — eis (3) **r1731–1733** (binnen de
   Handhaving-bullet r1718–1740) én de uitgewerkte les **r1758–1768** ("LI048 — een zichtbare
   uitzondering is óók een achterdeur", `LIJSTKOP_OPENSTAAND`-casus).
2. **Signalering klopt.** Voorbeelden frontend (lijstkop-scan) en LI047 (`GapDetailView`-tegels),
   regel algemeen ("het GEVAL is fout, niet de regel"; "toets: welke vorm maak ik navolgbaar?").
3. **In likara-tests:** afwezig (0 hits op "achterdeur"/"uitzondering" in deze betekenis).
4. **Verwijzers:**
   - NEXT_SESSION.md r257–258 — "…derde eis naast bijten en geen-vals-positieven **(frontend)**";
   - docs/OPVOLGPUNTEN.md r1901–1905 — "De les staat in `likara-frontend`…";
   - frontend/scripts/check-css-build.mjs r508–513 — de regel staat daar **als comment in de
     scan zelf** (tweede vindplaats van de tekst, geen verwijzing; verhuist niet mee maar kan
     gaan driften t.o.v. de skill-formulering).
   - ⚠ Niet verwarren met de "achterdeur" in ADR-050 r101 en werkprotocol r49 — dat is de
     security-instantie (relatie-endpoint), een ander onderwerp.

### Regel C — "leid de doelen van een scan af i.p.v. ze op te sommen"

1. **Vindplaats:** likara-frontend **r1733–1740** (zelfde Handhaving-bullet; "Moet er tóch iets
   buiten vallen, laat het dan **afleiden** i.p.v. opsommen").
2. **Signalering klopt — sterkste bewijs van de drie:** het goedkeurende tegenvoorbeeld in de
   passage zelf is een **backend**-test (`test_schema_aanroepen_scan.py`, `pytest.raises`-
   afleiding). De regel bewijst zijn skill-overstijgendheid in zijn eigen voorbeeld.
3. **In likara-tests:** afwezig (0 hits). Verwant: de vals-rood-verfijning (tests r484–486,
   "verbied alléén implementatie-interne symbolen") raakt hetzelfde thema vanaf een andere kant.
4. **Verwijzers:** geen buiten de onder B genoemde (de drie regels delen één bullet/kopgebied,
   dus de B-verwijzers dekken feitelijk het hele blok).

**Samenvattend:** alle drie staan uitsluitend in likara-frontend (0 vindplaatsen in
likara-tests); wat er meeverhuist bij verplaatsing: 2 externe tekstverwijzingen
(NEXT_SESSION r257, OPVOLGPUNTEN r1905) + bewustzijn van de comment-kopie in
check-css-build.mjs r508–513.

---

## Blok 4 — wat breekt er bij verplaatsing?

### 4.1 Kruisverwijzingen tussen de negen skills

**84 verwijzingsregels** totaal. Per bron:

| Bron | Aantal | Regelnummers |
|---|---:|---|
| likara-backend | 7 | 55, 98, 235 (→db); 476 (→ux §P8b); 616 (→tests); 638 (→db); 692 (→resilience) |
| likara-db | 3 | 125 (→backend); 471 (→backend+security); 487 (→ux) |
| likara-domeinmodel | 19 | 10, 19, 20, 29, 149, 511, 636, 649–653, 655, 674, 730, 793, 909, 939, 1004 |
| likara-frontend | 21 | 472, 613, 863, 1114, 1223, 1229, 1270, 1418, 1434, 1466, 1469, 1475, 1485, 1560, 1585, 1651, 1687, 1689, 1698, 1717, 1840 |
| likara-resilience | 1 | 98 (→frontend) |
| likara-security | 3 | 65 (→db); 183 (→domeinmodel §7); 184 (→frontend §Destructieve gating) |
| likara-tests | 1 | 421 (→backend, ADR-028-diagnose-recept) |
| likara-ux | 21 | 3, 139, 215, 232, 233, 273, 298, 460, 472, 605, 611, 655, 695, 749, 761, 863, 935, 1016, 1030, 1037, 1047 |
| likara-werkprotocol | 8 | 29, 30, 31 (→ux/frontend, KERNLES-bewijzen); 273 (→domeinmodel); 285 (→frontend §Signaal-kanalen); 533 (→ux); 598 (→tests); 607 (→domeinmodel) |

**Gemarkeerd — wijst naar iets dat door Blok 1–3 kan verdwijnen of hernoemen:**

| Verwijzing | Risico |
|---|---|
| likara-frontend r1717 → "de niet-geresolvede-component-les in likara-werkprotocol" | die les = **§LI040-inhoud** (r595–598) — verhuist bij Blok 1 |
| likara-backend r476, likara-frontend r1114/1469/1698 → ux §P8a/§P8b/§P9 | breken niet bij herordening, wél bij hernummeren |
| likara-werkprotocol r598 → "likara-tests, LI040" | wijst naar een tests-sessiesectie; robuust zolang tests-koppen blijven |
| likara-ux r460 → "zelftest-eis bij bronscans, likara-tests" | raakt Blok 3 als de scan-eisen verhuizen (doel wordt dan juist beter vindbaar) |

### 4.2 Verwijzingen vanuit `docs/` en ADR's

**128 verwijzingsregels** naar likara-skills in `docs/` (excl. `_generators/`), verspreid over
**53 bestanden**. Met expliciete **§-kop**: 36 regels. De relevante voor deze herordening:

| Vindplaats | Verwijst naar | Risico |
|---|---|---|
| docs/Checkpoint-tabvorm-en-paginacontrast-V048.md:633 | "werkprotocol §LI047" | er bestáát geen kop "LI047" — vier `###`-koppen dragen "(LI047)" als suffix; al een losse verwijzing |
| docs/TST-V048-Validatierapport.md:120 | "werkprotocol §LI044" | **dode verwijzing vandaag al**: 0 koppen met LI044 in werkprotocol |
| docs/Checkpoint-tabvorm-…-V048.md:652 | werkprotocol §"een rapport is geen meting" | citeert een zin, geen kop (staat in §Meet tenant-data r219) — overleeft samenvoegen 1.3-LI048 alleen als de zin behouden blijft |
| NEXT_SESSION.md:235, 249, 251, 264 | §Meet tenant-data · §Gate-discipline (2×) · §Browsercheck | koppen blijven in elk voorstel bestaan |
| NEXT_SESSION.md:161, 257; OPVOLGPUNTEN.md:1922/1935/1970/2047 | ux §P8a/§P9/§P8b + frontend (regel B) | zie 2.4 / 3.4 |
| docs/Validatie-patronen-LI039.md:51–54 | werkprotocol §Read-only-eerst · §Reikwijdte-scan · §KERNLES LI038 · §Browsercheck | blijven bestaan |
| docs/Checkpoint-open-punten-tabblad-V047.md:4, 236, 586, 602 | §Gate-discipline (2×) · §KERNLES · §Browsercheck | blijven bestaan |
| docs/Onderzoek-normdrift-en-taal-V047.md:91, 147, 214, 262, 268, 297–298 | tests §LI039 · security §LI035 · tests §LI040 · db §Referentietabel · ux §generiek · domeinmodel §Terminologie + ux §LI041 | tests §LI039/§LI040 zijn sessiekoppen in likara-tests — buiten de scope van dit voorstel, maar zelfde kwetsbaarheid |
| docs/adr/ADR-052…md:100 | likara-ux §LI044 | sessiekop in ux — idem |

### 4.3 Bestaande bewaking op skill-inhoud

Gevonden — **vier controles, allemaal op bestaan/omvang, geen enkele op inhoud**:

1. `docs/_generators/gen_build.py` r118–123: elke skill uit `skills_bron.likara_skill_paden()`
   moet bestaan én **≥ 200 bytes** zijn (build blokkeert anders).
2. `docs/_generators/sluit_acties.py` r26–40 (`check_skills_gevuld`): zelfde 200-bytes-toets.
3. `backend/tests/test_skill_bron_consistentie.py` (4 tests): set-gelijkheid disk ⇔ CLAUDE.md
   "Normale modus" ⇔ afgeleide paden, incl. 2 bijt-tests. Bewaakt **welke bestanden** er zijn,
   niets over hun inhoud.
4. CONTRIBUTING.md As 4: "Alle likara-skills gevuld (>200 bytes)".

**Er bestaat GEEN toets op koppen, kruisverwijzingen of §-verwijzingen.** Een herordening die
alle negen bestanden intact laat maakt **niets rood**, en een **dode verwijzing wordt door niets
gevangen** — empirisch bewezen: de dode verwijzing "werkprotocol §LI044"
(TST-V048-Validatierapport.md:120) bestaat vandaag al zonder dat iets hem meldde. Dit is zelf
een bevinding.

### 4.4 Git-staat

`git status --short .claude/skills/likara/` → **0 regels** (schoon). Branch **master**,
HEAD **`477565f`**. De werktree als geheel was schoon bij sessiestart; na dit checkpoint bevat
hij uitsluitend dit nieuwe rapportbestand (onderdeel van de opdracht).

---

## Blok 5 — de vereisten-check van `gen_build`

Bestand: `docs/_generators/gen_build.py` (311 regels) + `sluit_acties.py` (111 regels).

### 5.1 Wat eist de check, en waarop toetst hij?

| Vereiste | Definitie | Toets | Toets-regel |
|---|---|---|---|
| 7 mappen (o.a. `docs/adr`, `.claude/skills/likara`) | `REQUIRED_DIRS` r52–60 | `is_dir()` — bestaan | r110–112 |
| 10 bestanden (CLAUDE.md, NEXT_SESSION.md, docs/PROJECTGEHEUGEN.md, SESSIE_BRIEFING.md, build_counter.json, 5 generators) | `REQUIRED_FILES` r62–73 | `is_file()` — bestaan | r114–116 |
| 9 likara-skills (afgeleid uit disk via `skills_bron`) | `REQUIRED_SKILLS` r78 | bestaan + **≥ 200 bytes** | r118–123 |
| ≥ 1 ADR; ≥ 1 changelog `*_Changelog_V*.md` | `REQUIRED_PATTERNS` r80–84 | glob-telling ≥ minimum | r125–130 |

**Inhoudstoetsen: 0.** Niets kijkt ín een bestand (behalve de bytes-telling op skills).
De check draait als stap 7 (r299), ná de bouwnummer-bump (stap 1, r269) en ná de
CLAUDE.md-update (stap 2, r284 — bewust vóór de generators, CD018/OP-18-comment r273–281).

### 5.2 Mens-bijgewerkt vs. generator-geschreven

| Bestand | Wie schrijft | Bewijs |
|---|---|---|
| `docs/PROJECTGEHEUGEN.md` | **mens** (geheel) | geen generator raakt het; alleen `REQUIRED_FILES`-bestaan r65 |
| `NEXT_SESSION.md` | **mens** (inhoud) | `gen_next_session.py` r55–60: hergenereert alléén bij placeholder — een gevuld bestand wordt nooit aangeraakt |
| changelog-inhoud | mens (template door generator, r178–191) | `maak_changelog` schrijft alleen als het bestand nog niet bestaat |
| CLAUDE.md BOUWSTATUS-blok | **generator** | `update_claude_bouwstatus` r141–176 |
| `SESSIE_BRIEFING.md`, `SESSIESTART.md` | **generator** | r293, r296 |

Een actualiteitstoets mag dus alleen `docs/PROJECTGEHEUGEN.md` en `NEXT_SESSION.md` raken —
exact zoals het 0b-voorstel zei; dat deel klopt met de gemeten werkelijkheid.

### 5.3 Waar staat het bouwnummer, en in welke vorm?

| Bestand | Regel | Letterlijke regel (nu) | Herkenbaar patroon |
|---|---:|---|---|
| docs/PROJECTGEHEUGEN.md | 8 | `- **Build:** V049 · 2026-07-21` | `^- \*\*Build:\*\* V(\d{3})` |
| NEXT_SESSION.md | 1 | `# NEXT_SESSION.md — LIKARA V048` | `^# NEXT_SESSION\.md — LIKARA V(\d{3})` (zelfde vorm als het gen_next_session-template, r15 van dat script) |

**Live bevinding — de 0b-faalmodus bestaat op dit moment in de repo:** build_counter staat op
49, PROJECTGEHEUGEN zegt **V049**, NEXT_SESSION zegt **V048**. De twee mens-bestanden volgen
bovendien **verschillende conventies** (PROJECTGEHEUGEN vooruitgeschreven naar het nieuwe
nummer; NEXT_SESSION draagt het nummer van het moment van schrijven). Een actualiteitstoets
moet dus eerst één conventie vastleggen ("welk nummer hoort erin op check-moment?") vóór hij
kan bestaan — anders geeft hij op één van beide bestanden per definitie vals alarm.

### 5.4 Het TST-rapport in de vereisten

**Niet in `gen_build.py`** (0 vermeldingen in REQUIRED_FILES/PATTERNS). Wél in
`sluit_acties.py` r14–24 (`check_tst`): `rglob("TST-*Validatierapport*.md")` onder `docs/`,
neemt het **meest recente op mtime**, toetst **alleen bestaan** — geen label-match met de
huidige build. Aanvullend: gen_build r164 schrijft `TST-{build_label}-Validatierapport.md` in
de CLAUDE.md-bouwstatustabel **zonder te toetsen of dat bestand bestaat** — dezelfde
bestaan-vs-actualiteit-familie als 0b.

### 5.5 Tests voor `gen_build`

**3 testbestanden, 11 tests:**
- `backend/tests/test_gen_build_volgorde.py` — 2 tests (bouwstatus-update vóór de briefing).
- `backend/tests/test_gen_build_backup.py` — 5 tests (alleen `.sql` naar iCloud, geen secrets, zachte fouten, volgorde).
- `backend/tests/test_skill_bron_consistentie.py` — 4 tests (skillset-divergentie, incl. bijt-bewijs).

**Niet gedekt:** de `integriteitscheck` zelf (0 tests) en het REQUIRED_FILES-gedrag (0 tests).
Een 0b-toets zou daar zijn eerste test naast leggen.

---

## Afwijkingen t.o.v. het voorstel (NEXT_SESSION.md punt 0/0b)

| # | Voorstel beweerde | Gemeten | Oordeel |
|---|---|---|---|
| 1 | werkprotocol = **621 regels** | **638 regels** | rapport fout (of gemeten op een oudere stand) |
| 2 | **22 koppen** | 22 `##`-koppen ✓, maar **35 totaal** incl. 13 `###` | klopt alleen op `##`-niveau |
| 3 | 5 verzamelbakken, samen **105 regels** | **104 regels** (16+10+32+21+25) | −1; verwaarloosbaar |
| 4 | §Gate-discipline **142 regels** | **142** (r168–309) | klopt exact |
| 5 | Gate-discipline "bevat bestandsoperatie-lessen die bij §Browsercheck horen" | **0** bestandsoperatie-regels in Gate-discipline; die lessen staan **al** onder §Browsercheck (r321–345) | **rapport fout, niet de code** — er valt hier niets te verplaatsen |
| 6 | "voeg de drie UX-first-koppen samen" | **3 koppen + 1 LI035-bullet = 4 plekken** | voorstel telde de bullet niet |
| 7 | P-reeks omgekeerd: "P8 → P9 → P8d → P8c → P8b → P8a" | klopt; voorstel miste **P6b** (r277) als eerste reekslid | grotendeels juist |
| 8 | drie borgingsregels in frontend, niet frontend-specifiek, afwezig in tests | bevestigd (r1731–1740, r1741–1757, r1758–1768; 0 hits in likara-tests) | klopt |

---

## Wat je tegenkwam (buiten de vragen)

1. **Dode kop-verwijzing bestaat al:** `docs/TST-V048-Validatierapport.md:120` verwijst naar
   "werkprotocol §LI044" — die kop bestaat niet (0 hits). Niets ving dit; bevestigt Blok 4.3.
2. **NEXT_SESSION-header is de levende 0b-casus:** header zegt V048 (r1) en "Gegenereerd
   2026-07-20 / sessie LI047" (r2–13-samenvatting), terwijl build_counter op 49 staat en de
   inhoud (Vertrekpunt LI049, Openstaand uit LI048) actueel is. Plus het conventie-verschil met
   PROJECTGEHEUGEN (§5.3) dat een 0b-ontwerpbesluit vergt.
3. **De `bijgewerkt:`-frontmatter van de skills loopt achter:** werkprotocol zegt "V042",
   ux/frontend "V043" — alle drie bevatten LI048-inhoud (≥V049). Zelfde familie als 0b, ander
   bestand.
4. **De P-reeks is geen ux-reeks maar een platform-reeks** verspreid over 4 skills, met gaten
   (P5, P7), twee kop-loze leden (P1, P3 als bullets) en één dubbelzinnig lid (P2 in
   likara-security, vermoedelijk fase-aanduiding). Een herordening alleen bínnen likara-ux
   lost het vindbaarheidsprobleem maar half op.
5. **check-css-build.mjs r508–513 draagt regel B als comment** — een tekstkopie die bij
   verplaatsing van de skill-regel niet meebeweegt (driftrisico, geen breekrisico).
6. **De B-verwijzers wijzen zonder kopnaam** ("De les staat in `likara-frontend`",
   OPVOLGPUNTEN r1905; "(frontend)", NEXT_SESSION r257) — bij verhuizing naar likara-tests
   worden die twee zinnen onwaar en moet dat in dezelfde beweging hersteld worden
   (werkprotocol §Geen schuld: "wat je onwaar maakt, herstel je in dezelfde commit").
7. **`sluit_acties.check_tst` toetst mtime-bestaan, geen label** (§5.4) — een TST-rapport van
   een vorige build houdt de check groen. Zelfde bestaan-vs-actualiteit-familie als 0b; niet in
   het voorstel genoemd.

*Einde meting. Niets gewijzigd behalve het aanmaken van dit rapport.*
