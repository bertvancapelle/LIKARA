# Checkpoint — de drie borgingsregels: algemeen vs. frontend-gebonden (READ-ONLY)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `94c5625` · werktree schoon
**Grond:** `docs/Meting-verwijzingen-verhuizende-koppen-V049.md` (Blok 3) · `docs/Checkpoint-skillconsolidatie-V049.md`
**Datum meting:** 2026-07-22 · Er is niets gewijzigd behalve het aanmaken van dit rapport.

**De kernbevinding vooraf, omdat alles eronder ernaartoe wijst:** verhuizing 3 is in GEEN
enkele route een verbatim-verhuizing. Regel B en C leven niet als los blok maar als **eis (3)
van een opsomming** binnen een verder frontend-gebonden bullet (r1718–1740), en eis (1) van
diezelfde opsomming **bestaat al als eigen bullet in likara-tests** (r452–455). Elke route
knipt in een opsomming en/of voegt samen met bestaande tekst — beide zijn herformuleren.

---

## Blok 1 — exacte begrenzing en verwevenheid

Vindplaatsen ongewijzigd t.o.v. de meting (likara-frontend is deze sessie alleen op r97 van een
testbestand na niet geraakt): alles onder **"## LI040-patronen — bouwstenen +
bron-scan-handhaving (gevalideerd)"** (r1679).

### Regel C — afleiden i.p.v. opsommen (r1731–1740, binnen de Handhaving-bullet r1718–1740)

Eerste regel (r1731): `vals alarm slaat wordt genegeerd en is erger dan geen scan; (3) **geen benoemde uitzondering —`
Laatste regel (r1740): `geen lijst.)`

| Deel | Tekst (begin) | Oordeel |
|---|---|---|
| r1731–1732a | "(3) **geen benoemde uitzondering — een uitzondering is een achterdeur (LI047)**." | **algemeen** (tevens de eerste vorm van regel B) |
| r1732b–1733a | "Vraagt een geval om een uitzondering…, dan is meestal het GEVAL fout, niet de regel; en wie er één opneemt, verbreedt de volgende." | **algemeen** |
| r1733b–1734a | "Moet er tóch iets buiten vallen, laat het dan **afleiden** i.p.v. opsommen." | **algemeen** (de C-kern) |
| r1734b–1737a | "(LI047: twee tegels in `GapDetailView` droegen hun label als `<h2>`… definitiepaar (`dl`/`dt`/`dd`) van maken." | **frontend-gebonden** (GapDetailView, `<h2>`, `dl/dt/dd`) |
| r1737b–1740 | "Tegenvoorbeeld waar afleiden wél mag: `test_schema_aanroepen_scan.py` slaat aanroepen binnen `pytest.raises` over… structurele eigenschap, geen lijst.)" | **backend-voorbeeld** — bewijst de algemeenheid |

**1.3 — kan de kern zonder voorbeeld?** Ja: r1731–1734a (2½ zin) staat volledig op zichzelf en
het tegenvoorbeeld is al backend. **Maar** de kern is genummerd als **eis (3)** van de lijst
"Eisen aan élke scan: (1) bijten · (2) geen vals-positieven · (3) geen uitzondering" — hem
wegknippen laat in likara-frontend een lijst "(1)(2)" achter en dwingt daar een herformulering
af. C is de meest knipbare van de drie, en zelfs C is geen pure knip.

### Regel A — het bereik versmalt stiller (r1741–1757)

Eerste regel (r1741): `- **LI048 snede 2 — het BEREIK van een scan is even belangrijk als zijn regels, en versmalt`
Laatste regel (r1757): `     Zakt het, dan is dat een bevinding — geen getal dat je bijwerkt.`

| Deel | Tekst (begin) | Oordeel |
|---|---|---|
| r1741–1742a | "het BEREIK van een scan is even belangrijk als zijn regels, en versmalt stiller." | **algemeen** |
| r1742b–1745a | "De lijstkop-scan pakte `*Lijst.vue`… (`AuditTrailView`, `NormBeheer`, `ChecklistConfigBeheer`, …). Een naamconventie is geen criterium maar een toevalligheid." | **gemengd** — casus frontend, slotzin algemeen, in één doorlopende passage |
| r1745b–1747a | "**Leid het bereik af uit wat de gebruiker ziet**, niet uit hoe bestanden heten: hier de menu-routes uit `AppLayout.vue` → componenten uit `router/index.js` → scan die bestanden." | **gemengd in één zin** — hét lastige geval, letterlijk: de regel vóór de dubbele punt, de frontend-invulling erna; en de regel-formulering zelf ("wat de gebruiker ziet") is al UI-taal — een backend-variant zou "uit de gezaghebbende bron" moeten zeggen, en dat is een ander woord |
| r1747b | "Drie dingen die dit patroon nodig heeft, alle drie hard geleerd in één sessie:" | **algemeen** |
| sub 1, r1748–1752 | kern "Een niet-resolvebaar pad moet LUID falen, nooit `continue`." algemeen · bewijs (`@modules`-alias, "zeven van de veertien schermen") frontend · moraal ("een borging die stilletjes smaller wordt…") algemeen | **gemengd** |
| sub 2, r1753–1755 | kern "Het criterium mag het bestaande bereik niet uitsluiten." algemeen · bewijs (tabel/Bedrijfsfuncties/boom) frontend · "een ratel, zodat een **scherm** er nooit ongezien vanaf valt" gemengd woord | **gemengd** |
| sub 3, r1756–1757 | kern "Toets het GETAL in een suite" algemeen · bewijs (`LijstKopSchermen.test.js`, "veertien schermen") frontend · slotzin algemeen | **gemengd** |

**1.3:** de kop-zin + drie kale subeisen zijn als algemene regel formuleerbaar, maar **niet
verliesvrij**: (i) de kernzin van de afleidingsregel moet geherformuleerd ("wat de gebruiker
ziet" → laag-neutraal); (ii) alle drie subeisen dragen hun **bewijs** uitsluitend in het
frontend-voorbeeld — kaal verplaatsen levert regels zonder hun "hard geleerd"-grond, en dat is
precies het informatieverlies waar deze sessie tegen wapent. Regel A is van de drie het diepst
frontend-geworteld.

### Regel B — een zichtbare uitzondering is óók een achterdeur (r1758–1768)

Eerste regel (r1758): `- **LI048 — een zichtbare uitzondering is óók een achterdeur.** De lijstkop-scan droeg één sessie`
Laatste regel (r1768): `  — en kijk eerst of het geval zelf op te lossen valt.`

| Deel | Tekst (begin) | Oordeel |
|---|---|---|
| r1758a | "een zichtbare uitzondering is óók een achterdeur." | **algemeen** |
| r1758b–1760a | "De lijstkop-scan droeg één sessie lang `LIJSTKOP_OPENSTAAND = {BedrijfsfunctieLijst.vue}`: het scherm dat de schakelaar en een tweede actie in de kop had." | **frontend-gebonden** (de casus) |
| r1760b–1761 | "De uitzondering was verdedigd (afleiden kon niet zonder de fout te cementeren), gedocumenteerd, en werd bij élke run afgedrukt — geen stille skip." | **gemengd** (casusfeit, generiek leesbaar) |
| r1762–1764a | "**hij deed geen schade, hij legitimeerde een VORM.** De volgende sessie die één **scherm** niet kan omzetten, heeft dan een voorbeeld. Zo ontstaan achterdeuren — niet met een besluit, maar met een precedent." | **algemeen op één woord na** ("scherm") |
| r1764b–1766 | "De uitweg was wat de regel al zei: *het GEVAL is fout, niet de regel.*" algemeen · "De twee dingen die het **scherm** tegenhielden bleken allebei al beslist…" casus | **gemengd** |
| r1767–1768 | "**Toets bij een uitzondering niet 'richt hij schade aan?' maar 'welke vorm maak ik navolgbaar?'** — en kijk eerst of het geval zelf op te lossen valt." | **algemeen** |

**1.3:** de moraal (4 zinnen) staat op zichzelf, maar de casus ís het bewijs ("de scherpste
vorm van deze regel") en het woord "scherm" zit ín de algemene zinnen verweven — selectief
knippen vergt minimaal één woordwijziging. Vrijwel-verliesvrij, niet volledig.

---

## Blok 2 — staat er al iets in `likara-tests`?

1. **Regel A, B, C zelf: 0 vindplaatsen** in likara-tests (grep op achterdeur/versmalt/afleiden:
   0 treffers voor deze betekenis). Bevestigt de meting. **Maar twee verwante buren:**
   - **r452–455** (§LI040-patronen): "**Bewijs dat een test/scan bijt.** Elke bron-scan draagt
     een ZELFTEST… (referenties: veld-scan + detailkop-scan in `check-css-build.mjs`, elk 5/5).
     Zonder bijt-bewijs is een vangnet een aanname." — dit **is eis (1)** uit de
     frontend-opsomming, in eigen woorden.
   - **r484–486** (§LI041-patronen): "⚠ Verfijn de scan zoals in LI041: verbied alléén de
     implementatie-interne symbolen… — anders wordt de scan vals-rood." — raakt eis (2)
     (vals-alarm-familie) van de andere kant.
2. **Afwijking in formulering:** eis (1) bestaat in tests met een ándere formulering en eigen
   referenties. Wie de frontend-eisenlijst (1)(2)(3) integraal meeneemt, zet er een **tweede
   bijt-eis naast** — dan is verhuizen geen toevoegen maar **samenvoegen**, en samenvoegen is
   herformuleren. Wie alleen B+C (eis 3) en A meeneemt, ontloopt de dubbeling met r452–455 maar
   knipt de opsomming (Blok 1).
3. **Natuurlijkste landingskop:** er bestaat **geen onderwerpskop** "bronscans" in likara-tests.
   De twee kandidaten zijn **§LI040-patronen (…scan-zelftests…)** (r445, draagt de bijt-eis) en
   **§LI041-patronen (bronscan-norm…)** (r471, draagt de bronscan-norm) — **allebei
   chronologische sessiekoppen**: likara-tests heeft precies de kwaal die verhuizing 1 in het
   werkprotocol heeft verholpen (10 van de 27 `##`-koppen zijn sessiekoppen: LI020/21/22/35/36/
   39/40/41/46/47). Voorstel als er tóch geland moet worden: een nieuwe onderwerpskop
   "Bronscans — bereik, uitzonderingen en bijt-bewijs" waar r452–455 en r484–486 dan óók onder
   horen — maar dat is consolidatie van likara-tests zelf, een grotere beweging dan verhuizing 3.

---

## Blok 3 — gevolgen per route (gemeten, niet gekozen)

### Route (a) — abstraheren (algemene kern → tests; illustratie blijft in frontend)

- **Verwijzers die zouden moeten meebewegen** (actuele regelnummers, verschoven sinds de meting
  door de (a)-afvoer in NEXT_SESSION):
  | Vindplaats | Tekst | Actie bij route (a) |
  |---|---|---|
  | NEXT_SESSION.md:252 | "…derde eis naast bijten en geen-vals-positieven **(frontend)**" | "(frontend)" wordt onwaar → mee in dezelfde commit |
  | docs/OPVOLGPUNTEN.md:1905 | "De les staat in `likara-frontend`…" | idem |
  | NEXT_SESSION.md:58–64 | deel (c) — het voorstel zelf | afvoeren bij uitvoering |
  | SESSIESTART.md:142/334 · SESSIE_BRIEFING.md:100/292 | spiegels | volgen via gen_build, niet aanraken |
  | frontend/scripts/check-css-build.mjs:509–514 | gedrifte kopie van regel B | buiten scope (eigen besluit); drift blijft |
- **Vangt de scan een dode verwijzing na deze knip? NEE — 0.** Geen van de bovenstaande noemt
  een kop bij naam met `§`; het zijn skill-naam-zonder-kop-verwijzingen ("(frontend)", "staat in
  likara-frontend"). Dit valt onder beperking 4 van de scan. **De verwijzer-updates van route
  (a) zijn dus volledig onbewaakt handwerk** — het tegendeel van verhuizing 1, waar de scan
  domeinmodel:996 ving.

### Route (b) — verbatim verplaatsen (alles incl. frontend-voorbeelden → tests)

- **Wat frontend verliest:** r1741–1768 (28 regels) + eis (3) uit de Handhaving-bullet — de
  lessen over de lijstkop-scan verdwijnen uit de skill van de laag waar die scan
  (`check-css-build.mjs`) woont en onderhouden wordt. De frontend-bouwer die de scan aanpast
  vindt de bereik-ratel en de uitzonderingsregel dan alleen nog via de tests-skill (en de
  gedrifte comment in de scan zelf).
- **"Verbatim" is bovendien niet haalbaar:** eis (3) kan niet mee zonder de opsomming (1)(2)(3)
  te breken, en eis (1)/(2) kunnen niet mee zonder dubbeling met tests r452–455/r484–486
  (Blok 2.2). Route (b) is dus in werkelijkheid "grotendeels verbatim + één knip in de bullet".
- **Geldt C's algemeenheids-bewijs ook voor A en B?** Nee:
  - **C**: bewijst zich al in een backend-voorbeeld (`test_schema_aanroepen_scan.py`) — echt laag-neutraal;
  - **B**: de moraal is algemeen, maar het enige bewijs is de frontend-casus (`LIJSTKOP_OPENSTAAND`);
  - **A**: alle drie subeisen bewijzen zich uitsluitend in de lijstkop-scan — frontend-geworteld
    in élk bewijs, en zijn kernzin is in UI-taal gesteld.

---

## Blok 4 — losse eindjes

1. **Scan groen op `94c5625`**: 5 passed (incl. hoofdscan); werktree schoon (alleen dit rapport
   nieuw na oplevering). Alembic onaangeraakt.
2. **Verwijzingen in/rond de drie regels die konden sneuvelen door verhuizing 1/2: 0 gebroken.**
   Twee nabije verwijzingen gecontroleerd: r1698 → likara-ux §P9 (kop bestaat; nummer-verwijzing,
   volgorde-ongevoelig ✓) en r1717 → "de niet-geresolvede-component-les in likara-werkprotocol"
   (inhoudsverwijzing; de les leeft sinds verhuizing 1 verbatim onder §Browsercheck, de term is
   behouden ✓). De markers "(LI047)"/"LI048" in de drie regels zijn dateringen, geen
   kop-verwijzingen.

## Afwijkingen t.o.v. de vorige meting

| Punt | Meting zei | Nu gemeten |
|---|---|---|
| Begrenzingen A/B/C | r1741–1757 · r1731–1733+r1758–1768 · r1733–1740 | **bevestigd**, ongewijzigd |
| Externe verwijzers | B: 2 (+spiegels); A en C: 0 | **bevestigd**; regelnummers verschoven: NEXT_SESSION 257→**252**, spiegel-regels idem (−5 door de (a)-afvoer) |
| mjs-kopie | "al gedrift" | bevestigd, ongewijzigd (r509–514) |

Geen tegenspraak; wel één **aanvulling** die de meting niet zag: de dubbeling van eis (1) met
tests r452–455 — de meting keek naar de drie regels, niet naar de opsomming waar B/C in wonen.

## Wat je tegenkwam (buiten de vragen)

1. **likara-tests heeft zelf de chronologie-kwaal:** 10 van de 27 `##`-koppen zijn sessiekoppen.
   Elke landing van verhuizing 3 in een sessiekop reproduceert het probleem dat verhuizing 1
   net heeft opgelost; een onderwerpskop "bronscans" bestaat niet en zou er bij consolidatie
   van likara-tests vanzelf moeten komen (met r452–455 en r484–486 als eerste bewoners).
2. **De Handhaving-bullet (r1718–1740) is zelf al dubbel-lagig**: hij somt vier concrete
   frontend-scans op ÉN draagt de drie algemene eisen — de verwevenheid zit niet alleen in de
   drie regels maar in de bullet-structuur eromheen.
3. **De scan is blind op precies deze verhuizing** (Blok 3a): alle bestaande verwijzers zijn
   skill-naam-zonder-kop. Wie route (a) of (b) uitvoert, moet de twee levende-bron-verwijzers
   (NEXT_SESSION:252, OPVOLGPUNTEN:1905) met de hand meenemen — niets wordt rood als dat
   vergeten wordt.
4. **NEXT_SESSION:60** (deel (c)) noemt de drie regels bij hun roepnaam — wordt bij uitvoering
   van verhuizing 3 afgevoerd, samen met het nog openstaande deel (b) (r58-blok erboven).

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
