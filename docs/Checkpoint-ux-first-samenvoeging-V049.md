# Checkpoint — de UX-first-plekken: uniek per plek, kosten per optie (READ-ONLY meting)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `cc93de3` · werktree schoon
**Grond:** Checkpoint-skillconsolidatie (aanvangsmeting, 4 plekken) · verhuizing 1
**Datum meting:** 2026-07-22 · Niets gewijzigd behalve dit rapport. Scan groen (5 passed).

---

## Blok 1 — de plekken nú (hermeten; afwijking t.o.v. de aanvangsmeting)

**Het zijn er geen vier meer maar DRIE koppen — de vierde plek (de losse LI035-bullet) is door
verhuizing 1 ín §Kernprincipe gevouwen** en staat daar nu als bullet direct onder de prose die
(bijna) hetzelfde zegt. De aanvangsmeting ("3 koppen + 1 bullet elders") is dus achterhaald;
de dubbeling is er niet minder om, hij is **zichtbaarder** geworden — binnen één kop.

| # | Plek | Regels | Tekst (kern, letterlijk) |
|---|---|---|---|
| 1a | §Kernprincipe — prose | r9–19 | "**Elk antwoord, elke analyse en elk advies vertrekt vanuit het continue verbeteren van de gebruikerservaring met LIKARA.** Techniek en proces zijn vangrail — nooit het startpunt, nooit de toon. Zodra een antwoord technisch of procesmatig van toon wordt …: onmiddellijk terugkeren naar de functionele vraag. Bekende faalpatroon: te snel/diep de techniek of het proces in duiken. Correctie: terug naar de gebruikersvraag. Altijd." |
| 1b | §Kernprincipe — de ingevouwen bullet | r21–24 | "**Gebruikerservaring is áltijd het uitgangspunt**; techniek, schema-keuzes, gates en commit-discipline zijn vangrails — nooit de toon of het vertrekpunt van een antwoord. Conflicteert gebruikerslogica met een **technische** voorkeur, dan wint de gebruikerservaring. (LI035)" |
| 2 | §UX-first als correctieprotocol | r572–581 | "Als claude.ai merkt dat een antwoord technisch of procesmatig van toon wordt …: 1. Stop. 2. Stel de functionele vraag opnieuw centraal. 3. Geef het antwoord vanuit de gebruikerservaring. Conflict tussen gebruikerslogica en **proces**voorkeur: **gebruikerservaring wint.**" |
| 3 | §UX-first analysekader (LI024) | r608–621 | het 4-vragenkader (wat ziet de gebruiker / welk probleem / eenvoudigste oplossing / pas dan techniek als vangrail) + "Een analyse die bij stap 4 begint, is een overtreding … Een advies zonder stap 1–3 mag niet worden uitgebracht." + "niet-onderhandelbaar" |

(r349 "sterkste vangrail van LI041" is het woord in een andere betekenis — geen UX-first-plek.)

---

## Blok 2 — wat is uniek per plek

| Plek | Uniek (staat nergens anders) |
|---|---|
| 1a Kernprincipe-prose | de **terugkeer-instructie als reflex** ("onmiddellijk terugkeren naar de functionele vraag") · het benoemde **faalpatroon + de correctie** ("te snel/diep de techniek in duiken → terug naar de gebruikersvraag. Altijd.") |
| 1b de bullet | vrijwel niets — **bevestigt de aanvangsmeting**. Twee restjes: (i) het explicietere vangrail-lijstje ("schema-keuzes, **gates en commit-discipline**" — de prose zegt alleen "techniek en proces"); (ii) de conflictregel in de **techniek**-variant (zie de ⚠ hieronder) |
| 2 Correctieprotocol | het **3-staps stopprotocol** (Stop → functionele vraag centraal → antwoord vanuit gebruikerservaring) — het enige uitvoerbare herstel-recept · de conflictregel in de **proces**-variant |
| 3 Analysekader | het **4-vragenkader** als instrument · de **twee verboden** ("analyse die bij stap 4 begint = overtreding"; "advies zonder stap 1–3 mag niet") · de (LI024)-marker |

⚠ **De twee conflictregel-varianten zijn samen breder dan elk afzonderlijk**: 1b zegt
"technische voorkeur", 2 zegt "procesvoorkeur". Wie er bij samenvoegen één kiest, versmalt de
regel — elke samenvoeging moet "techniek én proces" expliciet dekken.

**Onderscheidendheid van de drie koppen (2.3):** ze grijpen op **drie verschillende momenten**
en overlappen niet grotendeels:
- §Kernprincipe = **de norm, altijd** (+ het faalpatroon);
- §Analysekader = **vooraf** — het instrument vóór elke analyse/advies/feature-keuze;
- §Correctieprotocol = **tijdens/achteraf** — het herstel-recept zodra het toch misgaat.
De echte overlap zit niet tússen de koppen maar **bínnen §Kernprincipe** (1a↔1b: twee
formuleringen van de norm direct onder elkaar) plus de dubbele conflictregel (1b↔2).

---

## Blok 3 — de opties (gemeten, geen keuze)

| Optie | Wat er gebeurt | Wat sneuvelt tenzij expliciet meegenomen | Overig gevolg |
|---|---|---|---|
| **(a) alles → één kop** | drie koppen + bullet worden één sectie | te bewaren: het 3-staps protocol · het 4-vragenkader + 2 verboden · faalpatroon + correctie · terugkeer-reflex · béíde conflictvarianten · het vangrail-lijstje · markers (LI024)/(LI035) — dat is ±20 regels: één kop kán het dragen maar wordt zelf een verzamelsectie | de **momenten verliezen hun eigen vindbare kop**: wie midden in een ontspoord antwoord "correctieprotocol" zoekt of vóór een analyse "analysekader", vindt één lange sectie. Zwaarste redactie (2 conflictvarianten verenigen) |
| **(b) alleen 1b laten opgaan in 1a** | de ingevouwen bullet versmelt met de prose van zijn eigen kop | vrijwel niets — mits het vangrail-lijstje ("schema-keuzes, gates en commit-discipline") en de techniek-variant van de conflictregel in de prose landen (mini-herformulering binnen één kop, marker (LI035) mee) | de binnen-kop-dubbeling weg; **drie koppen, drie momenten blijven**; kleinste ingreep die de aanvangsklacht ("vier plekken") oplost |
| **(c) alles laten staan** | niets | niets | tussen de kóppen is het **herhaling-met-reden** (drie momenten — kenmerk); bínnen §Kernprincipe is het sinds verhuizing 1 eerder een **gebrek** (twee normformuleringen direct onder elkaar leest als redactie-ongeluk) |

**Verwijzingen en scan, alle opties:** er bestaat **0** kop-genoemde verwijzing naar deze drie
koppen (repo-breed gemeten; alleen vastleggingen en de open NEXT_SESSION-(a)-notitie noemen de
samenvoeging als besluit, zonder kop-vorm). Zelfs optie (a) — koppen weg — maakt dus niets
rood; de scan blijft in elke optie groen. Er is geen bewakingsargument; de keuze is puur
inhoudelijk.

---

## Blok 4 — bewaking

1. **Verwijzers: 0 kop-genoemd, 0 in code.** Levende tekstverwijzing: alleen
   NEXT_SESSION r49–50 ("Nog open uit (a): de drie UX-first-koppen samenvoegen — eigen besluit,
   daar gaat inhoud verloren") — dat ís dit besluit; wordt bij de afsluiting afgevoerd.
2. `git status` schoon · branch `master` · HEAD `cc93de3` · scan **5 passed**.

## Wat je tegenkwam (buiten de vragen)

1. **Verhuizing 1 heeft het probleem van vorm veranderd**: de vierde plek is niet opgeheven
   maar naar binnen gevouwen — de zichtbaarste dubbeling is nu 1a↔1b binnen één kop, en dát is
   ook op te lossen zonder aan de drie-momenten-structuur te komen (optie b).
2. **Het volledige UX-first-plaatje is breder dan het werkprotocol**: likara-ux draagt de norm
   óók (eigen §Kernprincipe + §"Functioneel beschrijven is de NORM" (DC014)), net als CLAUDE.md
   (§Werkprotocol-kern). Buiten dit besluit, maar een latere ux-consolidatie komt dezelfde
   vraag tegen — en het antwoord hier zet de toon.
3. De aanvangsmeting noemde de bullet "zonder verlies samenvoegbaar"; de hermeting nuanceert:
   **bijna** — twee restjes (vangrail-lijstje, techniek-conflictvariant) moeten expliciet mee,
   anders is ook optie (b) niet verliesvrij.

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
