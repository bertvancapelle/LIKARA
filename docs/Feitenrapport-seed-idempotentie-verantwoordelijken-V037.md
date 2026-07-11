# Feitenrapport — Seed-idempotentie-smell: het verantwoordelijken-blok (V037/LI037)

**Checkpoint:** LI037_checkpoint_seed_idempotentie_verantwoordelijken · **Datum:** 2026-07-11 ·
**Basis:** commit a970fac (schone werktree). Read-only — niets gewijzigd behalve dit rapport; de
meting op de dev-DB was een pure SELECT (geen mutatie, geen reseed).

---

## Waarom dit ertoe doet (functioneel — vanuit de gebruiker)

De testwereld van LIKARA hoort een **vaste, herkenbare wereld** te zijn: sommige antwoorden hebben
een verantwoordelijke, en een aantal is **bewust leeg gelaten** — juist die lege plekken
demonstreren een sterkte van LIKARA: het systeem maakt registratiegaten zichtbaar ("hier ontbreekt
nog een verantwoordelijke", het aandacht-signaal `antwoord_zonder_verantwoordelijke`).

Het probleem: **elke keer dat de testdata opnieuw wordt opgebouwd, slibben twee van die
bewust-lege plekken dicht.** Wie demonstreert of test kan dus niet vertrouwen op wat hij ziet —
kijkt hij naar de ontworpen stand, of naar een uitgeklede versie die afhangt van hoe vaak er
toevallig gereseed is? Het bewijsmateriaal voor de "ontbrekende verantwoordelijke"-functie
brokkelt af tot het beeld helemaal weg is. Dezelfde handeling (testdata herladen) hoort altijd
exact dezelfde wereld op te leveren, **inclusief de bewust-lege plekken**. Dit rapport legt vast
wat er precies gebeurt en waarom, zodat een latere gerichte fix die stabiele testwereld herstelt.

---

## 1. Het blok zelf

**Vindplaats:** `backend/dev_seed_testdata.py`, binnen `_seed_bvowb_scenario`, blok
"── ADR-037 — verantwoordelijke per checklistantwoord (afdeling-dan-persoon), demonstratief ──",
r. 1554–1590 (comment r. 1554–1558, code r. 1559–1590).

```python
    # ── ADR-037 — verantwoordelijke per checklistantwoord (afdeling-dan-persoon), demonstratief ──
    # Maakt de UX zichtbaar: één blokkerend antwoord mét PERSOON-verantwoordelijke (de bijbehorende
    # OPEN blokkade toont die afgeleid, "persoon — afdeling"), één niet-blokkerend antwoord met een
    # AFDELING, één met een PERSOON, en de overige antwoorden BEWUST LEEG (voedt het Pass 2-signaal).
    # Registratief: `werk_bij` stuurt géén score mee → engine no-op. Idempotent (alleen lege rijen).
    pers_id = partij_id.get("J. de Vries")
    afd_id = partij_id.get("Informatievoorziening")
    if pers_id and afd_id:
        actieve_blok = { … Blokkade.checklistscore_id WHERE status IN (open, in_behandeling) … }
        leeg = (await session.execute(
            select(Checklistscore).where(
                Checklistscore.tenant_id == tid,
                Checklistscore.verantwoordelijke_id.is_(None),
            ).order_by(Checklistscore.created_at)
        )).scalars().all()
        blok_rij = next((s for s in leeg if s.id in actieve_blok), None)
        nonblok = [s for s in leeg if s.id not in actieve_blok]
        toewijzingen = []
        if blok_rij is not None:                       # blokkerend antwoord → PERSOON
            toewijzingen.append((blok_rij.id, pers_id))
        if len(nonblok) >= 1:                           # niet-blokkerend → AFDELING
            toewijzingen.append((nonblok[0].id, afd_id))
        if len(nonblok) >= 2:                           # niet-blokkerend → PERSOON
            toewijzingen.append((nonblok[1].id, pers_id))
        for score_id, verantw_id in toewijzingen:
            await checklistscore_service.werk_bij(
                session, tid, score_id, ChecklistscoreUpdate(verantwoordelijke_id=verantw_id))
        await session.commit()
        telling["verantwoordelijken"] = len(toewijzingen)
```

**Functionele bedoeling** (ADR-037 Pass 2, demonstratief): precies **drie** score-rijen krijgen
een `verantwoordelijke_id` — (1) het éne **blokkerende** antwoord → persoon **J. de Vries** (zodat
de afgeleide blokkade-eigenaar "persoon — afdeling" zichtbaar is), (2) één niet-blokkerend antwoord →
afdeling **Informatievoorziening**, (3) één niet-blokkerend antwoord → persoon. **Alle overige
antwoorden horen bewust leeg** te blijven: die lege rijen voeden het **Pass 2-aandacht-signaal
`antwoord_zonder_verantwoordelijke`** (`registratiegaten_service.py:59/341/386`, label in
`labels.js:349`) — het testscenario moet dat gat kunnen tonen. De UPDATE loopt via
`checklistscore_service.werk_bij` zónder `score`-veld → engine-no-op (dat deel klopt).

## 2. De niet-idempotente stap — waarom elke run +2

**Selectiecriterium:** de query pakt **álle score-rijen waar `verantwoordelijke_id` NU leeg is**,
geordend op `created_at`, en vult daarvan de **eerstvolgende** exemplaren: het eerste lege
blokkerende antwoord (indien aanwezig) + `nonblok[0]` + `nonblok[1]`.

**Waarom niet stabiel over runs:** het criterium is **"wat nu leeg is"**, niet "welke rijen gevuld
hóren te zijn". Run 1 vult de eerste drie rijen; bij run 2 staan die drie **niet meer in `leeg`**
(ze zijn gevuld), dus schuift het venster op: `nonblok[0]`/`nonblok[1]` zijn dan de **volgende
twee** lege rijen. Het doel verschuift elke run — een klassieke moving-target.

**Waarom precies 2 (en niet 3):** de **blokkerende tak stabiliseert zichzelf** — het scenario heeft
precies één actieve blokkade (Zaaksysteem), dus één blokkerende score; na run 1 is die gevuld,
valt uit `leeg`, en `blok_rij` is vanaf run 2 `None` (de tak vult niets meer). De **twee
niet-blokkerende takken zijn onvoorwaardelijk** (`len(nonblok) >= 1` / `>= 2` is bij 260+ lege
rijen altijd waar) → **+2 per run**. Het getal 2 is dus geen constante maar het aantal
onvoorwaardelijke takken in het blok.

**Empirisch bevestigd (read-only meting op de dev-DB, na de 2 fase-0-runs):** 267 scores totaal,
**5 gevuld** (bedoeld: 3), 262 leeg. De vijf gevulde rijen zijn exact de opschuivende
`created_at`-kop: Zaaksysteem **1.1** (persoon, 1 open blokkade — run 1, blok-tak),
**1.2** (afdeling) + **1.3** (persoon) — run 1; **1.4** (afdeling) + **1.5** (persoon) — run 2.

**Randfeit:** de `order_by(Checklistscore.created_at)` heeft **geen tiebreaker** (geen `id`).
De gemeten timestamps verschillen per milliseconde (sequentiële aanmaak), dus praktisch is de
volgorde stabiel — maar formeel is het geen totale ordening (bij gelijke timestamps zou de
rijkeuze DB-afhankelijk zijn). Ondergeschikt aan de hoofd-oorzaak, wel relevant voor een fix.

**Het comment liegt:** "Idempotent (alleen lege rijen)" (r. 1558) — de aanname is precies
omgekeerd: juist **doordat** het blok alleen-lege-rijen pakt, verschuift het doelwit elke run.
"Alleen lege rijen vullen" beschermt tegen *overschrijven*, niet tegen *aangroeien*.

## 3. Het krimpende "bewust leeg"-signaal

**Bedoelde stand:** 3 gevuld / **264 bewust leeg** (267 totaal).

**Feitelijk verloop per run k:** gevuld = 3 + 2·(k−1); leeg = 264 − 2·(k−1).

| Run | Gevuld | Bewust leeg |
|---|---|---|
| 1 | 3 | 264 (bedoelde stand) |
| 2 | 5 | 262 ← **huidige dev-DB-stand (gemeten)** |
| 3 | 7 | 260 |
| 10 | 21 | 246 |
| 133 | 267 | **0 — signaal dood** |

Hard onbruikbaar (0 lege rijen) pas bij run 133, maar het scenario **verwatert veel eerder**: de
demonstratieve pointe ("slechts 3 gevuld, de rest is het aandacht-gat") vervaagt vanaf run 2, en
de vulling kruipt categorie voor categorie door de Zaaksysteem-checklist (na ±44 runs zijn alle 89
Zaaksysteem-antwoorden gevuld en verdwijnt Zaaksysteem volledig uit het
`antwoord_zonder_verantwoordelijke`-signaal). Elke reseed geeft een subtiel ándere canonieke stand
— precies wat een idempotente seed niet mag doen.

## 4. Bron van de niet-idempotentie (de precieze oorzaak)

**Kern = optie (a): de UPDATE heeft geen stabiele sleutel/guard.** Het blok selecteert zijn
doelrijen op een **run-afhankelijke toestand** ("de eerstvolgende lege rijen") in plaats van op een
**deterministisch kenmerk** ("déze rijen horen gevuld"). Alle andere seed-blokken zijn idempotent
via een stabiele identiteit (skip-op-naam, skip-op-tripel, `ON CONFLICT DO NOTHING`, get-or-create);
dit blok is de enige zonder zo'n anker. De blok-tak ontsnapt alleen per toeval (er is precies één
blokkerende rij, en die blijft gevuld). Sub-oorzaak (b) — de ordening — is slechts een randfeit:
óók met een perfecte tiebreaker blijft "eerstvolgende lege" een moving-target.

## 5. Reikwijdte — raakt dit patroon andere seed-blokken?

**Nee — dit is de enige plek.** `grep is_(None)` op `dev_seed_testdata.py` levert exact één hit
(r. 1573, dit blok). Ter controle langs de andere blok-types: processen/vervullingen = skip-op-naam
/ skip-op-tripel (`RegistratieConflict`-vangst); componenten/partijen/contracten/relaties =
naam-/paar-maps met skip; scores = per (component, vraag)-identiteit; `_seed_dev_gebruikers` =
get-or-create op vaste Keycloak-subs; de database-scoring-backfill is idempotent (run 2: 0
profielen). De run-2-telling bevestigt het: **alle** tellers 0 behalve `verantwoordelijken=2`.
Eén fix dicht dus het hele gat.

## 6. Fix-opties (schetsen — geen keuze, niets gebouwd)

1. **Stabiele deterministische sleutel (vul altijd exact dezelfde rijen).** Selecteer de drie
   doelrijen op identiteit i.p.v. positie — bv. Zaaksysteem-vraag **1.1** (= de blokkerende rij in
   het scenario) → persoon, **1.2** → afdeling, **1.3** → persoon; vul alleen als nog leeg.
   *Consequentie:* idempotent per constructie; "bewust leeg" is stabiel 264; het comment wordt
   waar. De seed kent dan expliciet drie vraagcodes (koppelt de demonstratie aan het bestaande
   scoringsplan — de blokkade hangt daar al aan een vaste vraag). Sluit aan bij de heersende
   skip-op-identiteit-stijl van de rest van de seed. Bijvangst: de huidige dev-DB draagt al 5
   gevulde rijen — een verse reseed (named-volume-reset) zet de canonieke stand terug; de fix
   zelf hoeft geen bestaande data te repareren (testdata-regel: reseed, geen datamigratie).
2. **Bedoelde-stand-guard (skip-als-al-gevuld).** Vooraf tellen: zijn er al ≥1 (of ≥3) rijen met
   een gevulde `verantwoordelijke_id`, sla het blok dan over. *Consequentie:* minimale ingreep,
   drift stopt; maar de guard is grover — een handmatig (via de UI) gevulde rij telt mee en kan de
   demonstratieve drie-rijen-stand op een half-verse DB laten ontbreken; welke rijen gevuld zijn
   blijft run-1-volgorde-afhankelijk (geen expliciete identiteit).
3. **Expliciete leeg-lijst (omgekeerd vastleggen welke rijen leeg horen).** Een lijst "deze N
   rijen blijven leeg" en de rest vullen. *Consequentie:* keert de verhouding om (3 gevuld/264
   leeg zou een 264-regel-lijst vergen) — past niet bij dit blok; alleen zinvol als het signaal
   ooit "bijna alles gevuld, enkele gaten" moet tonen. Feitelijk genoteerd als denkrichting,
   praktisch de zwaarste.

Bij elke optie hoort dezelfde afronding: het onjuiste "Idempotent"-comment (r. 1558) meecorrigeren
en de reproduceerbaarheidscheck (twee runs → identieke tellingen, zoals fase 0 die introduceerde)
als bewijs draaien.

---

*Einde feitenrapport. Read-only checkpoint; geen code, seed, tests of data gewijzigd.*
