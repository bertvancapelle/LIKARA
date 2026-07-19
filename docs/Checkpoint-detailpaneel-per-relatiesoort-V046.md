# Checkpoint — wat vertelt het detailpaneel als je op een lijn klikt?

| | |
|---|---|
| **Sessie** | LI046 · V046 · read-only feitenopname vóór ontwerp |
| **Datum** | 2026-07-19 |
| **Commit** | `142d1c5` (werktree schoon; dit rapport is het enige nieuwe bestand) |
| **Modus** | Niets gewijzigd, niets gebouwd, niet gecommit |

**Uitkomst in één zin:** Berts waarneming klopt en is een *fall-through-bug in één bouwsteen* — het paneel kent wél per-lijnsoort-takken (8 stuks, ADR-031), maar de ringen **`gebruikt`** en **`eigenaar`** hebben er geen, vallen door naar het koppeling-lege-pad en tonen daardoor "Geen koppelingen gevonden." op lijnen die per definitie geen koppelingen kúnnen hebben; alle informatie om het juiste verhaal te tonen is op dat moment al in handen van de functie.

---

## Blok 1 — Reproductie van de waarneming

**Aanklikbare lijnsoorten.** De kaart kent 10 ringen (`LandschapskaartView.vue:54`):

| Ring | In gebruikerstaal | Bron (backend `landschapskaart_service.py`) |
|---|---|---|
| `applicaties` | koppeling tussen componenten | flow-relaties (`:379`) |
| `bedrijfsfuncties` | systeem ondersteunt bedrijfsfunctie-plek + plek-hiërarchie | functievervulling/functie_plaatsing (`:578-586`, ADR-043 G4) |
| `samenstelling` | bestaat uit | aggregation (`:369`) |
| `rollen` | partij vervult beheerrol | roltoewijzing (`:398`; backend-ring "beheerorganisatie") |
| `eigenaar` | organisatie is eigenaar van component | `component.eigenaar_organisatie_id` (`:449`) |
| `gebruikt` | **organisatie gebruikt component** | `organisatiegebruik`-tabel (`:469`) |
| `gebruikers` | gebruikersgroep gebruikt component | serving (`:360`) |
| `contracten` | valt onder contract · geleverd door | association (`:356`) + `contract.leverancier_id` (`:490`) |
| `infrastructuur` | draait op | assignment (`:353`) |
| `organisatiestructuur` | hoort bij | partij-hiërarchie (`:423`) |

(De vroegere `processen`-ring bestaat niet meer — vervangen door `bedrijfsfuncties`, ADR-043 G1.)

**Het paneel.** Eén gedeelde popup in `LandschapskaartView.vue` (`popupKind = 'node' | 'edge'`, `:1280`), gevuld door `openEdgePopup(edge)` (`:1538-1627`). Dit is het **enige** lijn-klik-oppervlak in de hele frontend (grep op edge-tap-handlers: alleen `:2593`).

**De tekst.** "Geen koppelingen gevonden." staat op `:3245` en verschijnt als `popupKind==='edge' && !popupFlows.length && !popupLaden && !popupMelding`. **Voorwaarde-analyse:** `openEdgePopup` behandelt niet-flow-ringen via een else-if-keten (`:1558-1608`) die **acht** gevallen dekt (rollen, contracten×2, infrastructuur, samenstelling, organisatiestructuur, functie_plaatsing, bedrijfsfuncties, gebruikers) — **maar `gebruikt` en `eigenaar` ontbreken**. Een klik op zo'n lijn doorloopt géén tak: `popupVelden` blijft leeg, de functie returnt, en de template valt terug op het koppeling-lege-bericht. Berts lijn ("Gemeente West Betuwe — gebruikt → Sociaal domein suite") is `ring='gebruikt'` — **reproductie bevestigd uit de code**. Bijvangst: `popupTitel` wordt in het fall-through-pad níét gezet (`:1552-1556` zetten hem niet; alleen de takken doen dat) — de kop is dan leeg of een restant van de vorige popup (welke van de twee Bert zag: niet vastgesteld).

## Blok 2 — Wat toont het paneel per lijnsoort vs. wat de data draagt

| Lijnsoort | Paneel vandaag | Feiten werkelijk aan de lijn (niet getoond → *cursief*) |
|---|---|---|
| koppeling (flow) | master-detail: alle flows van het ongeordende paar (API-fetch `:1614`), per flow naam/richting/protocol/impact/omschrijving | dekkend |
| rol/beheer | rol-label + Partij/Object | dekkend (roltoewijzing draagt niet meer) |
| valt onder contract | Component/Contract (namen) | *`relatie_rol`-kenmerk (valt_onder/onderhoud/hosting) · band-dekking (ADR-030) · contract-einddatum* |
| geleverd door | Contract/Leverancier | dekkend |
| draait op | Component/Host | dekkend |
| samenstelling | Geheel/Onderdeel | dekkend |
| hoort bij | Onderdeel/Hoort bij | dekkend |
| onderdeel van (functie) | Functie/Onderdeel van | dekkend |
| ondersteunt (functie) | Systeem/Bedrijfsfunctie | *plaatsings-/vervullingskenmerken (ADR-044: o.a. applicatiefunctie, herkomst)* |
| gebruikt door (groep) | Component/Gebruikersgroep/Leden | dekkend |
| **gebruikt (organisatie)** | **niets — "Geen koppelingen gevonden."** | organisatie × component (het grove feit); *verfijning: gebruikersgroepen/afdelingen die via `gebruik_id` onder dit feit hangen (ADR-036)* |
| **eigenaar** | **niets — "Geen koppelingen gevonden."** | `eigenaar_organisatie_id` |

**De gebruiksrelatie in het bijzonder.** `organisatiegebruik` draagt vandaag uitsluitend `organisatie_id` + `applicatie_id` (+ tenant/timestamps) — géén oordeel, "bewust geen", datum of notitie (`models.py:476-493`). De verfijning (afdeling) leeft op `gebruikersgroep.gebruik_id`. **ADR-046 besluit 3/4** hangt er t.z.t. de **uitstap-stand** aan (Blijft / Stopt-gepland / Stopt-in-uitvoering / Gestopt, altijd door een mens gezet, server-gestempeld wie/wanneer, geen automatische doorwerking naar het component). Niets daarvan komt vandaag in het paneel — er ís voor deze lijn geen paneel.

## Blok 3 — Eén plek of meerdere?

**Eén bouwsteen.** De popup in `LandschapskaartView.vue` wordt gedeeld door alle drie weergaven (Overzicht/Praatplaat/Lagen — zelfde `openEdgePopup`, zelfde tap-handler die instance-edges via `bronLog`/`doelLog` naar de logische edge resolvet, `:2593-2599`). Er bestaat geen tweede lijn-klik-oppervlak: een aparte KoppelingenkaartView bestaat niet (meer) in `frontend/src/views/`; `KoppelingSectie`/`StructuurSectie` op het componentdetail zijn tabellen (zelfde databron, geen lijn-klik), en `ProcesDiagram` heeft geen edge-taps. **Een aanpassing raakt dus één plek.**

**Waarop kiest hij zijn inhoud?** Op **ring** (plus `relatietype` voor de twee contract-soorten en `functie_plaatsing`) — maar de keten heeft **geen else/fallback**: elke onbekende ring erft stilzwijgend de lege koppeling-staat. De bouwsteen bepaalt dus wél op relatiesoort, met een onveilige rest-tak — precies de constructie waar de KERNLES LI038 voor waarschuwt (de regel bestaat, maar niets dwingt af dat elke ring een tak hééft).

## Blok 4 — De doorklikknoppen

`popupActies` wordt vóór de ring-vertakking gevuld (`:1544-1551`): per endpoint wordt de node uit `nodePerId` gehaald en `_detailLink(node)` bepaalt de knop ("Open {naam} →"). **Daarom werken de knoppen wél terwijl het paneel "niets" meldt.** En: het `edge`-object dat `openEdgePopup` binnenkrijgt draagt `ring` én `relatietype` (`:1538`, gebruikt op `:1558/:1566/:1584`) — **de informatie om het juiste verhaal te tonen is er dus al**; er ontbreekt uitsluitend een tak in de else-if-keten.

## Blok 5 — Reikwijdte van hetzelfde patroon

Alle 25 "Geen …"-lege-staten in de views doorlopen: de overige passen bij hun object (afdelingen op een partij, blokkades op een component, deelcontracten op een contract, enz.) en volgen de lege-staat-norm. **Het patroon "leegte gemeld op een niet-gestelde vraag" is vandaag beperkt tot de twee popup-fall-through-ringen (`gebruikt`, `eigenaar`).** Opvallend contrast: de **node**-popup meldt dezelfde feiten wél eerlijk als gat ("nog geen gebruik geregistreerd" / "nog geen eigenaar geregistreerd", `popupSamenvatting`, `:1099-1109`) — de kaart kent het nette antwoord dus al op knoop-niveau, alleen niet op lijn-niveau.

## Blok 6 — Verrassingen, risico's en open vragen

**Stille keuzes die niemand expliciet genomen heeft:**
- dat een onbekende ring in het koppeling-pad valt (niemand koos dat; het is het ontbreken van een else);
- dat rijkere lijnen (contract-rol, band-dekking, vervullings-kenmerken) alleen namen tonen — nooit besloten hoeveel detail de popup hoort te dragen versus de doorklik (detail-op-aanvraag-principe LI036);
- dat de popupTitel in het fall-through-pad ongedefinieerd blijft.

**Norm-/signaleringsfeiten:** het paneel toont er geen, en er is geen plek gevonden waar de popup een gat toont dat elders niet als gat telt. Wél het omgekeerde risico — dat is precies de aanleiding: "Geen koppelingen gevonden." op een bestáánd gebruiksfeit laat een geregistreerd feit als gat lezen, terwijl de signalering dat feit nergens als gat telt. Misleiding, geen inconsistentie in de telling.

**Open ontwerpvragen voor Bert (zonder voorkeur):**
1. Wat hoort de gebruikt-lijn te vertellen — alleen het grove feit (organisatie × component), of ook de verfijning (afdelingen/groepen onder dat gebruik)?
2. Verdient de eigenaar-lijn een eigen paneel, of volstaat de knoop-popup die de eigenaar al toont?
3. Wordt de lijn-popup t.z.t. de plek waar de ADR-046-uitstap-stand zichtbaar is — en alleen lezen, of ook zetten vanaf de kaart?
4. Moet er een structurele fallback komen (neutraal paneel: bron → label → doel) zodat een toekomstige ring nooit meer in het koppeling-pad kan vallen — de bouwsteen-borging uit KERNLES LI038?
5. Hoeveel van de rijkere lijn-feiten (contract-rol, band-dekking, einddatum, vervullings-kenmerken) hoort in de popup, en wat blijft doorklik?
6. Moet de popupTitel in élk pad gegarandeerd gezet zijn (invariant), of is dat onderdeel van vraag 4?

**Niet vastgesteld:** welke titel Bert feitelijk boven het lege paneel zag (leeg of stale — beide mogelijk uit de code); of de `eigenaar`-fall-through in de praktijk al door een gebruiker is geraakt.

---

**STOP** — geen fix, geen ontwerp, geen commit.
