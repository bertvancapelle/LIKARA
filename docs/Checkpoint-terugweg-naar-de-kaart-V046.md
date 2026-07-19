# Checkpoint — wat gebeurt er als je terugloopt naar de kaart?

| | |
|---|---|
| **Sessie** | LI046 · V046 · read-only feitenopname vóór ontwerp |
| **Datum** | 2026-07-19 |
| **Commit** | `61665a4` (werktree: alleen de drie ongecommitte checkpoint-docs + dit rapport) |
| **Modus** | Niets gewijzigd behalve dit bestand; niets gebouwd; niet gecommit |

**Uitkomst in één zin:** de terugweg leest de bewaarde staat volledig, haalt de subgraaf op en **tekent de kaart daadwerkelijk** — maar achter de opake beginscherm-overlay, want de herstel-tak is de enige van de drie binnenkomst-takken die `beginschermOpen` niet op `false` zet; mechanisch is dit een **gat (B)**, met één normatieve rand: een oude LI023-regel ("sluiten alleen via expliciete gebruikersactie") staat formeel nog overeind en niemand heeft ooit besloten of die óók voor een herstelde terugkeer geldt.

---

## Blok 1 — Wat doet "Terug naar Landschapskaart" precies?

- De knop komt uit **`useTerugNavigatie`** (`frontend/src/composables/useTerugNavigatie.js`): het label is afgeleid van de herkomst-route (`HERKOMST_LABELS`), en `gaTerug()` is letterlijk **`router.back()`** (`:36`). Het is dus **exact hetzelfde mechanisme als de browser-terugknop** — zelfde history-entry, geen verschil in gedrag. Wat de consultant ook kiest, hij doorloopt dezelfde route.
- Hij komt terug op **dezelfde URL als waar hij vandaan kwam: de kale `/landschapskaart`** — de actieve set leeft niet in de URL (bewust; de staat leeft in `lk-state`), dus "dezelfde route" en "kale kaartroute" zijn hier hetzelfde ding.
- Ook de nav-link "Landschapskaart" in de zijbalk komt op dezelfde kale route uit → zelfde mount-pad, zelfde gedrag.

## Blok 2 — Wat wordt er bewaard, en wat wordt ermee gedaan?

**Bewaard** in `lk-state` (sessionStorage; geschreven bij route-leave `:2601` én `beforeunload` `:2606`; `_bewaarKaartState` `:2554-2573`):

| Bewaard | Niet bewaard |
|---|---|
| actieve set · ringen (`ringAan`) · `egoStartId` · baanvolgorde + verberg-lege-banen · registratiegaps-toggle · groepeer-per-org · kaart-lezing | **weergave** (bewust — LI036-momentkeuze, `:2559-2560`) · **organisatie-scope (`scopeOrgs`)** · **rol-/BIV-filters** · zoekterm · zoom/pan · `beginschermOpen` |

**Wat ermee gebeurt bij terugkomst** (mount, `:2630-2662`): de binnenkomst kent drie takken —

1. **handoff** (consume-once): set gezet → `beginschermOpen = false` (`:2639`);
2. **deep-link** (`?center=`): set gezet → `beginschermOpen = false` (`:2648`);
3. **herstel** (`_herstelKaartState`, `:2651-2653`): set + ringen + alles hersteld… **zonder** `beginschermOpen = false`.

Daarna draait voor álle drie `herlaadGraaf()` (`:2662`) — de subgraaf van de herstelde set wordt opgehaald en de tekenketen (redraw-watch) tekent de kaart. **Het spoor loopt dus nergens dood tussen "gelezen" en "getekend": de kaart ís getekend — onzichtbaar achter de opake beginscherm-overlay** (`z-20`, `absolute inset-0`), die default open staat (`beginschermOpen = ref(true)`, `:294`) en alleen dicht gaat via de expliciete acties (view openen `:1038`, hele landschap `:881`, "Toon N componenten"-knop `:3360`).

**Waarom "21 in beeld"/"Toon 1 component" wél zichtbaar zijn:** de chips-teller en de actiebalk ("Toon N componenten op de kaart") leven ín het beginscherm en lezen de herstelde set — vandaar dat de kaart "weet waar hij was" terwijl je hem niet ziet. Klopt exact met de waarneming.

## Blok 3 — Bewust of een gat?

- **Het leeg-openen-besluit** is vastgelegd in de skills (likara-ux, LI021: *"Bij schaal opent de kaart leeg… vertrekpunt = de gebruiker kiest"*; LI023 Fase B: *"De kaart opent altijd leeg (beginscherm)"*). Het is geformuleerd voor de **verse start bij schaal** en maakt **geen onderscheid** tussen "ik open de kaart" en "ik kom terug op de kaart" — dat onderscheid is nergens besloten.
- **De vlag-regel** (likara-ux `:307-311`, LI023): *"Sluiten = alleen via expliciete gebruikersactie; heropenen = wisSet() + harde reset"* — geschreven tegen spooksluitingen, vóórdat het lk-state-herstel bestond.
- **Het herstel-besluit** (LI034, likara-frontend): *"`lk-state` = in-sessie werk over navigatie/reload heen"* — de uitdrukkelijke bedoeling is werkbehoud.
- **Bewijs richting gat (B):** (a) de twee zuster-takken van dezelfde binnenkomst-beslisboom (handoff, deep-link) sluiten de overlay wél — de herstel-tak is dezelfde soort "binnenkomst met bekende set" en mist alleen die ene regel; (b) de code behandelt een herstelde set elders al als "geen verse start": het views-startscherm wordt bij een herstelde set juist **onderdrukt** (`:2657`, conditie `actieveSet.size === 0`); (c) de volledige laad- en tekenketen draait — er wordt werk gedaan dat niemand te zien krijgt.

**Conclusie: (B) een gat op mechanisch niveau — met een (A)-rand.** De tekenstap wordt wél aangeroepen; alleen de overlay-vlag ontbreekt in de herstel-tak. Maar de LI023-regel "sluiten alleen via expliciete gebruikersactie" staat formeel nog, en die botst hier met het LI034-werkbehoud. **Het te nemen besluit is dus smal en precies: geldt "sluiten alleen expliciet" óók voor een herstelde terugkeer, of is terugkeren-met-bewaard-werk zelf de expliciete ingang?** Niet gerepareerd, conform opdracht.

## Blok 4 — Hoe vaak raakt dit de gebruiker?

- **Drie detail-views** dragen de terugknop: ComponentDetail, ContractDetail, PartijDetail (grep `useTerugNavigatie`: 3 consumenten). De beweging kaart → contract → terug en kaart → partij → terug verliest dus hetzelfde.
- **Elke terugweg loopt door hetzelfde mount-pad**: terugknop, browser-terug én de nav-link — alle drie de kale route, alle drie de herstel-tak.
- **F5/reload**: identiek (het LI034-`beforeunload`-pad bewaart, de herstel-tak leest) — ook daar landt de gebruiker met bewaard werk op het beginscherm. **Sessie-timeout + herlogin**: zelfde route, zelfde gedrag.
- De frequentie is dus niet "soms": **elke terugkeer naar de kaart binnen een sessie** toont het verkennerscherm in plaats van het bewaarde beeld.

## Blok 5 — Verrassingen, risico's en open vragen

**Verrassingen:**
- **De organisatie-scope en de rol-/BIV-filters zitten níét in `lk-state`** — kijk-variabelen (per de LI034-sortering "vaste bril") die bij elke terugkeer stil verdwijnen. Dat is een tweede, kleiner werkverlies dat achter het overlay-probleem schuilgaat, en niemand heeft die weglating expliciet besloten (de bewaarlijst documenteert alleen wat er wél in zit).
- **De weergave (Overzicht/Praatplaat/Lagen) is bewust momentkeuze** (LI036) — óók als de kaart bij terugkeer zou tekenen, kan hij in een ándere weergave tekenen dan waarin je vertrok.
- Zoom/pan is nergens bewaard (bestaand, gedocumenteerd: buiten de historie).
- De zojuist gebouwde "Zelf beginnen"-uitgang raakt dit niet: het views-startscherm verschijnt bij een herstelde set niet eens; het probleem is de beginscherm-overlay, een andere laag.

**Stille keuzes die een oplossing zou moeten maken (niemand heeft ze genomen):**
- terugkeer = **direct tekenen** zoals achtergelaten, of beginscherm mét één duidelijke "verder waar je was"-weg (de opdracht-vraag);
- of de LI023-vlag-regel wordt herzien ("herstelde binnenkomst = expliciete ingang") of gehandhaafd met een zichtbare verder-knop;
- of scope/filters alsnog in `lk-state` horen;
- of de weergave voor déze route wél mee terug moet reizen (LI036-sortering herzien of niet);
- wat er gebeurt als de bewaarde set inmiddels leeg gefetcht wordt (component verwijderd) — nu niet vastgesteld wat de gebruiker dan ziet (**niet vastgesteld**).

**Open ontwerpvragen voor Bert:**
1. Is terugkeren-met-bewaard-werk een expliciete ingang (kaart tekent direct) of blijft het beginscherm met een "verder waar je was"-route?
2. Wordt de LI023-regel "sluiten alleen via expliciete gebruikersactie" herzien of gehandhaafd — en waar leggen we dat vast?
3. Horen organisatie-scope en rol-/BIV-filters in de bewaarde kaartstaat?
4. Reist de weergave (Overzicht/Praatplaat/Lagen) mee terug, of blijft die momentkeuze?
5. Moeten terugknop en browser-terug identiek blijven (nu zijn ze het — bewaren als eigenschap)?
6. Wat toont de terugkeer als de bewaarde set niet meer bestaat?

---

**STOP** — geen fix, geen ontwerp, geen commit.
