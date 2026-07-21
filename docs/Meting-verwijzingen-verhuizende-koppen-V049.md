# Meting — verwijzingen naar de verhuizende koppen

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `477565f` · **Aard:** READ-ONLY
**Vertrekpunt:** `docs/Checkpoint-skillconsolidatie-V049.md` (hergebruikt; gericht bijgemeten)
**Datum meting:** 2026-07-21 · Er is niets gewijzigd behalve het aanmaken van dit rapport.

---

## Blok 1 — verwijzingen naar de vijf verdwijnende werkprotocol-koppen

Gezocht repo-breed (`.md`, `.py`, `.js`, `.vue`, `.mjs`; excl. `node_modules`, excl. dit rapport en
het vorige checkpoint) op: `§LI035|§LI036|§LI039|§LI040|§LI048`, combinaties van `werkprotocol` met
die nummers, én inhouds-citaten uit de vijf secties ("niet-geresolvede", "telling vóór besluit",
"set-acties wijzigen nooit", "inventarisatie is een meting", "patroon-signalen", "bedieningsdoc",
"volle CC-sessie"). **21 treffers beoordeeld.**

### Tabel (alle beoordeelde treffers)

| Vindplaats | Soort | Verwijst naar | Skill bedoeld | Raakt | Gegenereerd |
|---|---|---|---|---|---|
| NEXT_SESSION.md:51 | levende bron | de vijf koppen bij naam ("`LI035`, `LI036`, `LI039`, `LI040`, `LI048`") | werkprotocol | **ja** | nee |
| NEXT_SESSION.md:53 | levende bron | "…óf in §LI035 landen" | werkprotocol (context: het consolidatievoorstel) | **ja** | nee |
| SESSIE_BRIEFING.md:86 | gegenereerd | spiegel van NEXT_SESSION:51 | werkprotocol | **ja** | **ja** |
| SESSIE_BRIEFING.md:88 | gegenereerd | spiegel van NEXT_SESSION:53 | werkprotocol | **ja** | **ja** |
| SESSIESTART.md:128 | gegenereerd | spiegel van NEXT_SESSION:51 | werkprotocol | **ja** | **ja** |
| SESSIESTART.md:130 | gegenereerd | spiegel van NEXT_SESSION:53 | werkprotocol | **ja** | **ja** |
| likara-domeinmodel/SKILL.md:996 | levende bron (skill) | "Aansluitend op §LI039 *'telling vóór besluit — denkbaar is niet geteld'*" | **skillnaam ontbreekt**; via het citaat: werkprotocol (r571) | **ja** | nee |
| likara-frontend/SKILL.md:1717 | levende bron (skill) | "de niet-geresolvede-component-les in likara-werkprotocol" | werkprotocol (LI040-inhoud, r595–598) | **voorwaardelijk** — geen kop genoemd; blijft waar mits de les-term behouden blijft | nee |
| frontend/tests/Icoon.test.js:8 | **code** | "(zie likara-werkprotocol: de niet-geresolvede-component-les)" | werkprotocol (LI040-inhoud) | **voorwaardelijk** — idem | nee |
| docs/OPVOLGPUNTEN.md:1965 | levende bron | "de stille-lege-render-faalmodus uit likara-werkprotocol" | werkprotocol (LI040-inhoud) | **voorwaardelijk** — idem | nee |
| docs/OPVOLGPUNTEN.md:2145 | levende bron | "werkprotocol staat op 595 regels, met vier nieuwe koppen onder §Gate-discipline" | werkprotocol, maar de Gate-discipline-###-koppen (blijven) | nee — wel **al onwaar** (638 regels, checkpoint 1.1) | nee |
| docs/Validatie-patronen-LI039.md:112 | vastlegging | "likara-werkprotocol: 21–22 (LI039-bewijzen)…" | werkprotocol — claim-nummers, geen koppen | nee | nee |
| likara-ux/SKILL.md:690 | levende bron | §LI035 "Proces-detail = twee blokken" | likara-ux (eigen sectie) | nee | nee |
| likara-ux/SKILL.md:1006 | levende bron | "(LI043, §LI035)" | likara-ux (eigen sectie) | nee | nee |
| likara-backend/SKILL.md:687 | levende bron | §LI035 "Audit-dekking is ORM-dekking" | likara-backend (eigen sectie) | nee | nee |
| likara-domeinmodel/SKILL.md:793 | levende bron | §LI035/§LI036/LI037/LI038 | domeinmodel + ux (eigen secties) | nee | nee |
| likara-domeinmodel/SKILL.md:926, 988 | levende bron | §LI040 (meervoud-regel · feit-op-niveau) | domeinmodel (eigen sectie "LI040/ADR-046") | nee | nee |
| docs/Onderzoek-normdrift-en-taal-V047.md:91, 147, 214 | vastlegging | tests §LI039 · security §LI035 · tests §LI040 | likara-tests (2×), likara-security | nee | nee |
| docs/Validatie-patronen-LI039.md:70 | vastlegging | likara-backend §LI035 | likara-backend | nee | nee |
| docs/Checkpoint-open-punten-tabblad-V047.md:331 | vastlegging | §LI040 "elk `*Detail*`-scherm gebruikt `<DetailKop>`" | **skillnaam ontbreekt**; via het citaat: likara-frontend | nee | nee |
| docs/Checkpoint-open-punten-tabblad-V047.md:412 | vastlegging | likara-ux §LI039 | likara-ux | nee | nee |
| modules/…/tests/test_component_open_punten_li047.py:5 · test_component_bevinding_adr052.py:21 · test_component_norm_adr052.py:25 · test_gebruik_component_breed_adr055.py:8 | code (4×) | "likara-tests §LI039" (eigen-test-tenant-norm) | likara-tests | nee | nee |

### Tellingen

- **Sneuvelt hard** (kop of kopnaam genoemd): **7** — NEXT_SESSION:51+53 (levende bron, 2),
  hun 4 gegenereerde spiegels, en domeinmodel:996 (1).
- **Voorwaardelijk** (inhoudsverwijzing zonder kop; blijft waar mits de les-formulering na
  verplaatsing behouden blijft): **3** — frontend-skill:1717, Icoon.test.js:8 (code),
  OPVOLGPUNTEN:1965.
- **In vastleggingen** (buiten het latere scanbereik) die deze verhuizing raken: **0**.
  Álle rakende verwijzingen staan in levende bronnen (3), gegenereerde bestanden (4) of code (1
  van de 3 voorwaardelijke). De angst dat vastleggingen het grootste slachtoffer zijn, klopt
  voor déze verhuizing niet.
- **Niet toe te wijzen uit de verwijzing zelf** (skillnaam ontbreekt, alleen via citaat-matching
  herleid): **2** — domeinmodel:996 en Checkpoint-open-punten-tabblad-V047:331. Beide per
  definitie onbewaakbaar voor een scan die op `skill §kop` matcht — zelf een bevinding.

### Per kop

| Kop | Verwijzingen die sneuvelen |
|---|---|
| LI035 | 1 (NEXT_SESSION:53) + 2 spiegels |
| LI036 | **0** |
| LI039 | 1 (domeinmodel:996, skill-loos) |
| LI040 | 0 hard; 3 voorwaardelijke inhoudsverwijzingen |
| LI048 | **0** |
| alle vijf tegelijk | 1 (NEXT_SESSION:51) + 2 spiegels |

NEXT_SESSION:51–53 ís het consolidatievoorstel zelf; na uitvoering hoort die passage sowieso
afgevoerd/bijgewerkt te worden (werkprotocol §Geen schuld: wat je onwaar maakt, herstel je in
dezelfde beweging).

---

## Blok 2 — de P-volgorde

### 2.1–2.2 De 11 externe P-verwijzingen: allemaal nummer-verwijzingen

| # | Vindplaats | Wijst naar | Type |
|---|---|---|---|
| 1 | likara-backend/SKILL.md:476 | §P8b | nummer |
| 2 | likara-frontend/SKILL.md:1114 | §P8b | nummer |
| 3 | likara-frontend/SKILL.md:1469 | §P8a | nummer |
| 4 | likara-frontend/SKILL.md:1698 | §P9 | nummer |
| 5 | modules/…/services/auditlog_service.py:264 | §P8a | nummer (docstring) |
| 6 | modules/…/services/auditlog_service.py:355 | §P8b | nummer (comment) |
| 7 | docs/OPVOLGPUNTEN.md:1922 | §P8a | nummer |
| 8 | docs/OPVOLGPUNTEN.md:1935 | §P8a | nummer |
| 9 | docs/OPVOLGPUNTEN.md:1970 | §P9 | nummer |
| 10 | docs/OPVOLGPUNTEN.md:2047 | §P8b | nummer |
| 11 | NEXT_SESSION.md:161 | §P8a | nummer |

**Plek-/volgordeverwijzingen ("de paragraaf hierboven"): 0 van de 11.** Omdat er niet hernummerd
wordt, **breekt geen van de 11** bij herordening.

Aanvullend gevonden (gegenereerde spiegels, geen aparte herstelactie — Blok 4):
SESSIESTART.md:238 en SESSIE_BRIEFING.md:196 spiegelen NEXT_SESSION:161 (§P8a);
SESSIESTART.md:137–138 en SESSIE_BRIEFING.md:94–96 spiegelen het voorstel-citaat van de volgorde
("In het bestand: P8 → P9 → P8d → …") — dat citaat wordt na herordening **onwaar in de bron**
(NEXT_SESSION:60–62) en volgt dan vanzelf in de spiegels.

### 2.3 Volgorde-beroep bínnen likara-ux

| Regel | Zin | Blijft waar na herordening (P8→P8a→P8b→P8c→P8d)? |
|---|---|---|
| 331 (P8d) | "Vierde in de lijn van §P8a–c, en de goedkoopste om te voorkomen." | **ja** — "vierde in de lijn" is rangorde in de regelfamilie; na herordening klopt hij ook fysiek |
| 359 (P8c) | "Derde in dezelfde lijn als §P8a en §P8b…" | **ja** — idem, wordt ook fysiek kloppend |
| 391–392 (P8b) | "De tweelingregel van §P8a, en hij hoort er direct naast… P8a gaat over een filter dat hij niet ziet" | **ja** — P8a en P8b zijn nu al aangrenzend (r389/r422) en blijven dat; de claim wordt ná herordening ook in leesrichting waar |
| 424 (P8a) | "Derde instantie van dezelfde lijn, en de scherpste" | **formeel ja** ("instantie" = ontstaansvolgorde), maar ⚠ na herordening staat P8a als éérste van de subreeks en noemt zich "derde" — leest dan als positieclaim. Bovendien noemen P8c (r359) én P8a (r424) zich **allebei "derde"** — die botsing bestaat nu al. |
| 433–434 (P8a, punt 1) | "zie §'een lijst legt uit, een teller zwijgt'" | **ja** — wijst naar §4 Lege staten (r108 e.v.), buiten de subreeks |
| 673 · 860 · 1063 | "(aanvulling op P8)" (2×) · "(§P8)" | **ja** — nummer-verwijzingen |

"Hierboven/hieronder"-afhankelijkheden binnen r275–470: **0** (r463 "eronder" beschrijft
UI-chips, r467 "volgende sessie" is tijd).

---

## Blok 3 — wat meebeweegt met de drie borgingsregels

### 3.1 Verwijzers — 3 bevestigd, 2 gegenereerde spiegels erbij, verder 0

| Vindplaats | Soort | Wat er staat |
|---|---|---|
| NEXT_SESSION.md:257–258 | levende bron | "Een scan met een benoemde uitzondering is een achterdeur — derde eis naast bijten en geen-vals-positieven **(frontend)**" — de skill-aanduiding "(frontend)" wordt onwaar bij verhuizing naar likara-tests |
| docs/OPVOLGPUNTEN.md:1901–1905 | levende bron | "De les staat in `likara-frontend`: een uitzondering die geen schade doet en netjes wordt afgedrukt, is nog steeds een achterdeur…" — skillnaam wordt onwaar |
| frontend/scripts/check-css-build.mjs:509–514 | code (kopie, geen verwijzing) | zie 3.2 |
| SESSIESTART.md:334 · SESSIE_BRIEFING.md:292 | gegenereerd | spiegels van NEXT_SESSION:257 — volgen vanzelf |

Bredere zoek op citaten ("legitimeer", "navolgbaar", "GEVAL is fout", "versmalt stiller",
"afleiden i.p.v. opsommen"): **0 verdere treffers** die naar deze regels verwijzen
(ReferentiemodelConfigBeheer.test.js:3 en HERKOMST.md:5 gebruiken "navolgbaar" in eigen betekenis;
Feitenrapport-V039:141 gebruikt "legitimeert" over harde regel 8). Voor regel A (bereik) en
regel C (afleiden) zijn er **0 externe verwijzers** — alleen regel B heeft er.

### 3.2 De kopie in check-css-build.mjs naast de skill-tekst

**check-css-build.mjs r509–514 (comment):**
> "GEEN UITZONDERINGENLIJST. Er stond er even één in (BedrijfsfunctieLijst, dat de schakelaar en
> een tweede actie in de kop droeg). Hij deed geen schade en werd elke run afgedrukt — maar hij
> legitimeerde een VORM: de volgende sessie die één scherm niet kan omzetten heeft dan een
> voorbeeld. Zo ontstaan achterdeuren: niet met een besluit, maar met een precedent. Het scherm
> is omgezet, de lijst is weg."

**likara-frontend r1758–1768 (skill):**
> "…De uitzondering was verdedigd (afleiden kon niet zonder de fout te cementeren),
> gedocumenteerd, en werd bij élke run afgedrukt — geen stille skip. Hij is er tóch uitgegaan…
> **hij deed geen schade, hij legitimeerde een VORM.** … Zo ontstaan achterdeuren — niet met een
> besluit, maar met een precedent. De uitweg was wat de regel al zei: *het GEVAL is fout, niet de
> regel.* … **Toets bij een uitzondering niet 'richt hij schade aan?' maar 'welke vorm maak ik
> navolgbaar?'**"

**Oordeel:** inhoudelijk gelijk, tekstueel **al uiteengelopen** — de mjs-versie is korter, mist de
"GEVAL is fout"-uitweg en de toets-vraag, en verschilt in interpunctie ("achterdeuren:" vs
"achterdeuren —"). Het is een parallelle formulering, geen letterlijke kopie; verhuizing van de
skill-regel verandert hier niets, maar de drift bestaat al vandaag.

---

## Blok 4 — gegenereerd vs. mens-bijgewerkt

| Bestand | Status | Bewijs |
|---|---|---|
| SESSIESTART.md | **gegenereerd** | header "SESSIESTART — LIKARA V049"; geschreven door `gen_sessiestart_md.py` (gen_build stap 6, r296) |
| SESSIE_BRIEFING.md | **gegenereerd** | header "Gegenereerd: 2026-07-21"; `gen_sessie_briefing.py` (stap 5, r293) |
| CLAUDE.md | mens, behalve het BOUWSTATUS-blok (generator, gen_build r141–176) | — |
| NEXT_SESSION.md | **mens** (generator raakt hem alleen bij placeholder — gen_next_session.py r55–60) | — |
| docs/PROJECTGEHEUGEN.md · docs/OPVOLGPUNTEN.md · skills · ADR's | mens | — |
| docs/changelog/* | template generator, inhoud mens | gen_build r178–191 |

**Consequentie voor de tellingen:** van de rakende verwijzingen zijn er **6 gegenereerd**
(SESSIE_BRIEFING 86/88/196/292 zit deels buiten Blok-1-scope; strikt binnen de drie verhuizingen:
Blok 1: 4 · Blok 2-spiegels: 4 · Blok 3-spiegels: 2). Géén daarvan apart herstellen — ze volgen
zodra NEXT_SESSION.md klopt en `gen_build` opnieuw draait. Handmatig te herstellen blijven
uitsluitend de verwijzingen in levende bronnen en code.

---

## Blok 5 — de sessiemarker per alinea

19 alinea's/eenheden in de vijf secties. **9 dragen een eigen marker, 10 niet.**

### Draagt al een marker in de eigen tekst (9)

| Regels | Marker in de tekst |
|---|---|
| LI035 r544–549 | "De LI035-les" (r544) |
| LI039 r566–570 | "LI039 leverde er twee" (r567) |
| LI039 r571–576 | ADR-044 + Verkenning §B1 + "(LI040 herbevestigd… ADR-046)" — ⚠ eigen sessie LI039 zelf niet genoemd |
| LI039 r577–580 | ADR-044 (r580) — ⚠ idem |
| LI039 r581–584 | "(LI039: defusedxml…)" (r583) |
| LI039 r585–590 | "(LI039-incident: …)" (r586) |
| LI040 r595–598 | "(likara-tests, LI040)" (r598) |
| LI040 r603–608 | "*(Reden uit LI040: …)*" (r606) |
| LI040 r609–612 | "*(LI040: een browsercheck-draaiboek…)*" (r611) |

### Ontleent zijn datering uitsluitend aan de kop — **krijgt bij verhuizing een marker (10)**

| Regels | Inhoud | Noot |
|---|---|---|
| LI035 r537–540 | UX-first áltijd het uitgangspunt | geen enkele marker |
| LI035 r541–543 | kort/bondig; één-voor-één; `.md`-formaat | geen enkele marker |
| LI036 r553–559 | set-acties muteren alleen de set | noemt ADR-040, maar als **onderwerp** van de herziening — de sessie (LI036) staat alleen in de kop |
| LI039 r563–564 | disclaimer "tekst-regels zonder bouwsteen" | vervalt vermoedelijk bij verplaatsing; zo niet, dan marker nodig |
| LI040 r599–602 | volle CC-sessie → verse sessie + overdrachts-`.md` | geen enkele marker |
| LI048 r616–621 | het incident (Auditlog-placeholder) | **de hele LI048-sectie bevat nul sessiemarkers** — |
| LI048 r623–626 | de fout-duiding ("Oracle FIN-DB") | — vijf eenheden, |
| LI048 r629–631 | regel: tel het ding zelf | — maar het is één samenhangend |
| LI048 r632–633 | regel: checkpointtabel = teller per cel | — verhaal: één marker op het |
| LI048 r634–638 | regel: rapport wijkt af ⇒ rapport is fout | — blok volstaat als het bijeen blijft |

---

## Afwijkingen t.o.v. het vorige checkpoint

| Punt | Checkpoint zei | Nu gemeten | Oordeel |
|---|---|---|---|
| Blok 3-verwijzers | "2 tekstverwijzingen + drift-risico mjs" | bevestigd, **+2 gegenereerde spiegels** (SESSIESTART:334, SESSIE_BRIEFING:292) | aanvulling, geen fout |
| 11 externe P-verwijzingen | 11 | 11 bevestigd, **+2 gegenereerde spiegels** van NEXT_SESSION:161 | aanvulling |
| mjs-kopie "drift-risico" | risico | drift is **al feit**: teksten verschillen nu al in omvang en interpunctie (3.2) | aanscherping |

Geen tegenspraak met het vorige checkpoint gevonden.

---

## Wat je tegenkwam (buiten de vragen)

1. **Tweede dode kop-verwijzing, nu in productiecode:** `backend/dev_seed_testdata.py:1496`
   verwijst naar "werkprotocol §LI044" — die kop bestaat niet (de LI044-seed-regel staat als
   alinea onder §Browsercheck). Naast de al gevonden dode verwijzing in TST-V048:120. Niet
   gerepareerd; genoteerd.
2. **OPVOLGPUNTEN.md:2145 is al onwaar:** "werkprotocol staat op 595 regels" — het zijn er 638.
   Raakt de verhuizing niet, maar bevestigt dat structuurgetallen in levende bronnen verouderen
   zonder dat iets het meldt.
3. **P8a en P8c noemen zich allebei "derde"** (r424 "derde instantie" · r359 "derde in dezelfde
   lijn") — bestaat vandaag al; na herordening gaat P8a's "derde" als positieclaim gelezen worden
   terwijl hij vooraan staat.
4. **De LI048-sectie is de enige van de vijf zonder énige eigen sessiemarker** (0 van 5 eenheden)
   — precies de sectie over "een meting draagt zijn herkomst".
5. **NEXT_SESSION:51–62 (het voorstel zelf) wordt door uitvoering onwaar** — inclusief het
   volgorde-citaat "P8 → P9 → P8d → …". Hoort in dezelfde beweging bijgewerkt/afgevoerd,
   anders spiegelen SESSIESTART/SESSIE_BRIEFING bij de volgende build een achterhaald voorstel.
6. **De twee skill-loze verwijzingen** (domeinmodel:996, Checkpoint-…-V047:331) tonen een
   patroon: `§LI0xx` zonder skillnaam is onbewaakbaar zodra hetzelfde sessienummer in meerdere
   skills een kop is — vandaag geldt dat voor LI035 (4 skills), LI039 (3), LI040 (4).

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
