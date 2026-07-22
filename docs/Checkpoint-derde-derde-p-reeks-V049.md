# Checkpoint — de "derde/derde"-kwestie in de P8-subreeks (READ-ONLY meting)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `87ab572` · werktree schoon
**Grond:** gate-rapport verhuizing 2 · blok-A-rapport scan
**Datum meting:** 2026-07-22 · Niets gewijzigd behalve dit rapport. Scan groen (5 passed).

**De hoofduitkomst vooraf: de veronderstelde tegenstrijdigheid bestaat niet.** Git-archeologie
bewijst dat P8a's "Derde instantie" een **andere lijn** telt dan P8c's "Derde" — beide kloppen.
Het probleem is geen fout nummer maar een **ambigu "dezelfde lijn"** dat op leesvolgorde
onnavolgbaar is geworden. Dat verandert het correctie-oppervlak wezenlijk (Blok 3).

---

## Blok 1 — de zelfbenoemingen

| Kop | Regel | Aanhef letterlijk | Rangtelwoord |
|---|---:|---|---|
| P8a | 302–303 | "Derde instantie van dezelfde lijn, en de scherpste: niet een filter dat verbergt, maar een filter dat **zelf** verborgen is." | **derde** + "instantie … lijn" |
| P8b | 350–352 | "De tweelingregel van §P8a, en hij hoort er direct naast: …" | geen rang ("tweelingregel" = relatie) |
| P8c | 383–384 | "Derde in dezelfde lijn als §P8a en §P8b, en dezelfde faalmodus: …" | **derde** + "lijn" |
| P8d | 415 | "Vierde in de lijn van §P8a–c, en de goedkoopste om te voorkomen." | **vierde** + "lijn" |

**Botsingen:** precies één — P8a en P8c zeggen allebei "derde" (r302 vs. r383). Geen dubbele
vierdes; P8b draagt geen rang.

### 1.3 De bedoelde telling — met git-bewijs twee verschillende lijnen

- **P8b/P8c/P8d tellen de leesvolgorde-lijn a→b→c→d** en kloppen sinds verhuizing 2 óók fysiek:
  P8b noemt zich tweeling ván a, P8c "derde als §P8a en §P8b" (a=1, b=2 ✓), P8d "vierde van
  §P8a–c" ✓.
- **P8a telt een óúdere lijn.** Bewijs: bij commit `14dd669` (de commit die P8a introduceerde;
  commit-message draagt letterlijk P8a's titel) bestond van de subreeks **alleen P8a** — P8b/c/d
  kwamen pas in `0b2814f`. "Derde instantie" kán dus niet op a-b-c-d slaan. Wat er op dat moment
  wél stond, direct erboven in §P8 (r291–298, toen én nu): "**Verbergen mag, stiekem verbergen
  niet — twee LI041-instanties.** (1) De **verdrongen grove koppeling** … (2) De **ongetelde
  reikwijdte** …". P8a — een filter dat *zelf* verborgen is — is **instantie 3 van díé
  stiekem-verbergen-lijn**, en "de scherpste" past daar naadloos op. Inhoudelijk sluitend,
  chronologisch bewezen.

**Conclusie:** twee lijnen delen het woord "derde": de LI041-instantielijn binnen §P8 (waar P8a
nr. 3 is) en de LI048-subreekslijn (waar P8c nr. 3 is). Geen van beide zinnen is onwaar; de
verwijzing "dezelfde lijn" in P8a is alleen niet meer te volgen nu de subreeks ervóór… erná
staat.

---

## Blok 2 — wat leunt er op het woord

1. **Interne verwijzingen: alle via nummer, geen enkele via rang.** P8b r350 → "§P8a"
   (+relatiewoord "tweelingregel"); P8c r383 → "§P8a en §P8b"; P8d r415 → "§P8a–c". Een
   woordwijziging in P8a's aanhef breekt **0** interne verwijzingen.
2. **Extern rangtelwoord-gebruik: 0.** Repo-brede zoek op "Derde instantie", "derde in dezelfde
   lijn", "tweelingregel", "Vierde in de lijn" buiten likara-ux en de vastleggingen: geen
   treffers. ⚠ Niet verwarren met NEXT_SESSION:252 "**derde eis** naast bijten en
   geen-vals-positieven (likara-tests §Bronscans)" — dat is de bronscan-eisenfamilie, een andere
   "derde"; die raakt deze correctie niet.
3. **De 2 productiecode-verwijzingen wijzen op het nummer**, geverifieerd op de regel zelf:
   `auditlog_service.py:264` → "likara-ux §P8a" · `:355` → "(§P8b)". Geen rang — een
   aanhef-wijziging raakt ze niet.

---

## Blok 3 — het correctie-oppervlak (voorgesteld, niet uitgevoerd)

De meting verandert de vraag: **"Derde" → "Eerste" zou de zin ONWAAR maken** (P8a is niet de
eerste van de lijn die hij telt — hij telt de LI041-instanties, en dáárvan is hij echt de
derde). De opties, klein naar groot:

| Optie | Ingreep | Oordeel uit de meting |
|---|---|---|
| **(a) niets doen** | 0 woorden | feitelijk juist maar ambigu blijvend: twee "derdes" 80 regels uit elkaar zonder dat de lezer kan zien dat het twee lijnen zijn |
| **(b) de lijn expliciteren** | 1 zin, 1 regel (r302): "Derde instantie van dezelfde lijn" → "Derde instantie van de stiekem-verbergen-lijn uit §P8 (na de twee LI041-instanties dáár)" — rest van de zin ongemoeid | neemt de ambiguïteit weg zónder iets onwaar te maken; **meer dan een woordcorrectie → herformuleren → Berts besluit** |
| **(c) hernummeren op leesvolgorde** ("Eerste") | 1 woord | **afgeraden op grond van de meting**: maakt een ware zin onwaar |

2. De minimale zinvolle set (optie b) raakt uitsluitend de **zelfbenoeming** in r302; geen zin
   die inhoudelijk iets anders zegt, geen andere subkop.
3. **Markers:** de te wijzigen zin draagt geen herkomst-marker; de LI048-marker zit in de
   P8a-kopregel en die blijft in elke optie onaangeroerd.

---

## Blok 4 — bewaking

1. `git status` skills: **schoon** · branch `master` · HEAD `87ab572` · scan **5 passed**.
2. **De scan vangt hier niets en hoeft niets te vangen:** in alle drie de opties blijven de
   koppen (`### P8a …` t/m `### P8d …`) en hun nummers byte-gelijk — alleen aanhef-tekst zou
   wijzigen, en aanhef-tekst is geen anker waarnaar met `§` verwezen wordt (de externe
   verwijzingen wijzen op nummers, zie Blok 2). Bevestigd: het correctie-oppervlak ligt volledig
   buiten het scanbereik.

---

## Wat je tegenkwam (buiten de vragen)

1. **Het gate-rapport van verhuizing 2 (en de meting daarvóór) waren op dit punt te stellig**:
   beide noemden het een "botsing/tegenstrijdigheid". De code wint van het rapport — het is een
   **ambiguïteit tussen twee ware tellingen**, geen fout. Hierbij gecorrigeerd.
2. **De ontstaansvolgorde van de subreeks is nu ook gedocumenteerd feit**: P8a (`14dd669`) →
   P8b/c/d (`0b2814f`), beide 2026-07-21 — consistent met "elk nieuw stuk vóór het vorige anker
   ingevoegd" uit het oorspronkelijke consolidatievoorstel.
3. Optie (b)'s formulering is een voorstel op één regel, geen uitgevoerde tekst — bij akkoord
   verdient de exacte bewoording nog één blik (de zin moet §P8's "twee LI041-instanties"
   letterlijk naast zich weten).

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
