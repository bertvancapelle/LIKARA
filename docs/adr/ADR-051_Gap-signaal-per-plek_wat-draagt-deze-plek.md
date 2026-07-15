# ADR-051 — Het gap-signaal per plek: wat draagt deze plek?

| | |
|---|---|
| **Status** | Besloten (LI041) — bouw nog niet gestart (gate 3, stap 1 = dit ADR) |
| **Datum** | 2026-07-14 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-044 (plaatsing als eerste-klas feit; besluit 4 — herijkt) · ADR-045 ("ondersteunt werk" op het componenttype; besluit 2 — herijkt) · ADR-049 (functievervulling + de leeslaag `dekking_overzicht`) · ADR-050 (een tabelfeit mag zich nooit voordoen als een bevoegdheidsregel — dezelfde figuur) · ADR-046 (levensfase — de "gedragen door iets dat verdwijnt"-familie) · ADR-043 (bedrijfsfunctie als ruggengraat) |
| **Grond** | `docs/Feitenrapport-gapsignaal-V041.md` (read-only checkpoint) · besluiten Bert LI041 |
| **Invariant (ongewijzigd)** | Score blijft de enige lifecycle-driver. Dit ADR is registratie + leeslaag; de engine wordt niet geraakt. |

---

## Context — de werkvoorraad die de kaart eerlijk houdt

Aan het eind van de workshop loopt de consultant door de bedrijfsfunctieboom en wil **per plek**
zien waar hij staat — zijn werkvoorraad. Vandaag ziet hij dat niet: er is géén signaal op
bedrijfsfuncties of plaatsingen (feitenrapport §2.2), en een plek zonder koppeling toont
simpelweg niets (§2.4). De teleenheid blijft de **plaatsing**, niet de functie (ADR-044
besluit 4): er zijn geen "Toezicht-gaten", er zijn **plekken** met of zonder ondersteuning.

Gate 3 geeft de consultant per plek één van **vier standen** — en één handeling:

| Stand | Betekenis | Handeling |
|---|---|---|
| **"Nog geen ondersteunend systeem"** | openstaande vraag | *ga navragen* |
| **"Ondersteund via een bovenliggende functie — hier niet bevestigd"** | half antwoord (omhoog-cue) | *ga doorvragen* |
| **"Hier draait dit [systeem/systemen]"** | bevestigd (een koppeling op deze plek) | — |
| **"Hier draait niets — vastgesteld"** | bevinding | *klaar; geen gat* |

Bij een koppeling kan hij bovendien zeggen of het systeem het werk **naar behoren draagt** of
een **noodoplossing** is — of dat nog even in het midden laten.

---

## Besluit 1 — Een koppeling hoog in de boom werkt door als **cue**, niet als antwoord

Koppel je het Zaaksysteem aan *Uitvoering*, dan hangen daar **110 functies** onder (gemeten,
§5.3). Die plekken melden voortaan: **"ondersteund via een bovenliggende functie — hier niet
bevestigd"** — een **derde stand tussen gat en groen**.

*Grond:* dit is dezelfde figuur als de grove koppeling (ADR-049): een koppeling hoog in de boom
is een **onvoltooid antwoord** voor alles eronder — niet niks, niet af. En dezelfde
eerlijkheidslijn als het verdrongen antwoord (ADR-049 correctie): **het scherm zwijgt nooit
over iets dat het weet.**

**Verworpen — strikt** (elke plek voor zichzelf; de 110 blijven kaal gat): gooit informatie weg
die er ís. De consultant ziet 110 gaten die hij zojuist meende af te dekken, gaat het signaal
negeren, en dan is de werkvoorraad een klaagmuur.

**Verworpen — rollup** (de koppeling groent de hele subboom): **verzint 110 antwoorden** op
vragen die niemand stelde. Exact wat LI040 met twee migraties uit LIKARA sloopte —
*LIKARA verzint niets.* De cue is bewust een **derde kleur**, geen groen: hij zegt "kijk hier
nog even", niet "dit is af".

---

## Besluit 2 — "Hier draait niets" is een uitkomst ván de registratie, geen tweede registratie

De vraag *"wat draagt deze plek?"* heeft precies één antwoord: *dit systeem* · *deze systemen* ·
*niets, en dat weten we zeker* · *nog niet gevraagd*. **Eén vraag, dus één bron.**

De uitkomst woont daarom **in `functievervulling`**: een rij draagt ófwel een component, ófwel de
uitkomst *"geen systeem"*. **Structureel geborgd: altijd precies één van beide — nooit geen van
beide, nooit allebei.** Een bevinding is niet minder een antwoord dan een component — hij is
alleen leeg.

Dit onderscheidt strikt (ADR-044 besluit 3, ongewijzigd): *nooit naar gekeken* = een openstaande
vraag (afwezigheid van registratie); *vastgesteld dat er niets draait* = een aanwezige
registratie met uitkomst "geen" (klaar — niet opnieuw navragen).

**Verworpen — een aparte tabel voor "vastgesteld: niets"**: twee bronnen over dezelfde vraag
lopen stil uit de pas, en de leeslaag zou ze moeten samenvoegen — de tweede-waarheid-val
(kernles LI038).

---

## Besluit 3 — "Noodgreep of volwaardig" is een oordeel over de PLEK, niet over het componenttype

⚠ **Dit herijkt ADR-045 besluit 2**, dat het onderscheid als eigenschap van het **componenttype**
voorzag ("harde ontwerpeis voor gate 3"). Bert verwerpt dat expliciet:

> **Een fileshare is niet inherent een noodgreep.** Een bouwtekeningenarchief op een
> netwerkschijf is prima — het ís een archief. Datzelfde archief voor vergunningverlening is een
> brandhaard. **Het oordeel zit niet in het ding, maar in wat het moet dragen** — en dat weet
> alleen de consultant, ter plekke.

Een catalogus-vlag zou LIKARA **in beide richtingen laten liegen**: een prima archiefoplossing als
gat bestempelen, én een riskante Access-database níét als noodgreep kunnen markeren omdat "client
software" toevallig niet aangevinkt staat. Dit is dezelfde fout die LIKARA al meermaals verwierp —
**de vorm van het ding laten bepalen wat het betekent** (ADR-050: *"een tabelfeit mag zich nooit
voordoen als een bevoegdheidsregel"*; hier: een tabel-/typefeit mag zich nooit voordoen als een
inhoudelijk oordeel).

Het oordeel is dus een **eigenschap van de koppeling**: *draagt dit systeem dit werk naar behoren,
of is dit een noodoplossing?* Het geldt voor **elk** componenttype — ook een applicatie kan een
noodgreep zijn (een uitgefaseerd systeem dat nog draait; vgl. de levensfase-familie, ADR-046).

**Verworpen — het type stelt voor, de consultant overruled**: twee waarheden over hetzelfde ding;
zodra ze verschillen weet niemand welke telt.

---

## Besluit 4 — Het oordeel is optioneel; leeg is een eigen, vindbare stand

Niet ingevuld = **"nog niet beoordeeld"** — gedempt getoond, met een **eigen filteroptie**.

*"Ze gebruiken het zaaksysteem — of dat goed werkt weet ik niet."* Een verplicht veld zou de
consultant dwingen te gokken, en dan staat er een **verzonnen oordeel** dat niet van een echt te
onderscheiden is. Dat is de les van "Midden" en "Onbekend" (LI040, migraties 0067/0068): **leeg ≠
fout, en LIKARA verzint nooit een antwoord.** Het lege oordeel is bovendien werkvoorraad:
*"12 koppelingen zonder oordeel."*

---

## Besluit 5 — Eén afleiding, twee vensters

De **boom** toont de cue op de plek (daar werkt hij). De **centrale signalering** telt en lijst ze
op (*"waar moet ik nog langs?"* — de vraag die de consultant écht stelt).

Beide uit **één gedeelde afleiding**, bronscan-geborgd tegen een tweede implementatie. Twee
schermen die hetzelfde feit anders vertellen is erger dan één scherm dat zwijgt (kernles LI038;
zelfde vorm als `dekking_overzicht`, ADR-049). Het signaal is **read-only afgeleid, nooit
opgeslagen** — ook de teller niet (ADR-045 besluit 8-lijn).

---

## Wat dit ADR herijkt

| Bron | Oorspronkelijk | Herijking (dit ADR) | Reden |
|---|---|---|---|
| **ADR-044 besluit 4** | **drie** standen per plek (nog geen · grof gekoppeld–verfijning ontbreekt · geen systeem vastgesteld) | **vier** standen: de **omhoog-cue** ("ondersteund via een bovenliggende functie — hier niet bevestigd") komt erbij als derde stand tussen gat en bevestigd. | Een koppeling hoog in de boom is bekende informatie voor alles eronder; die verzwijgen (strikt) of tot antwoord verheffen (rollup) is beide onwaar (besluit 1). |
| **ADR-045 besluit 2** | het noodgreep/volwaardig-onderscheid als eigenschap van het **componenttype** (harde ontwerpeis voor gate 3) | het oordeel verhuist naar de **koppeling** (de plek): *naar behoren / noodoplossing / nog niet beoordeeld*, voor elk componenttype. | Het oordeel zit in wat het systeem moet dragen, niet in het ding; een catalogus-vlag laat LIKARA in beide richtingen liegen (besluit 3). |

**Onaangeroerd blijven:** de teleenheid is de plaatsing (ADR-044 besluit 4) · *nooit gevraagd* ≠
*vastgesteld niets* (ADR-044 besluit 3) · verfijnen vervangt grof op die plek (ADR-049) · aanbod
gesloten, motor generiek · **engine-invariant** (score blijft de enige lifecycle-driver).

---

## Gevolgen (benoemd, niet gebouwd — stap 2 volgt ná Berts akkoord)

1. **Schemastap op `functievervulling`** (besluit 2): een **uitkomst**-onderscheid zodat een rij
   ófwel een component draagt ófwel "geen systeem — vastgesteld", plus een **oordeel**-veld
   (naar behoren / noodoplossing / leeg, besluit 3/4). **Precies-één-van-beide structureel
   geborgd** (CHECK: component_id gezet **xor** uitkomst = "geen systeem"); `component_id` wordt
   nullable en de twee partiële UNIQUE-indexen bewegen mee. Ontwikkelmodus: alembic-schemastap +
   reseed — **geen datamigratievraagstuk** (alleen testdata).
2. **De omhoog-afleiding is nieuw.** De bestaande gap-cue op de processen-lijst/kaart kijkt
   **omláág** (draagt iets ónder mij een vervulling?); gate 3 kijkt **omhóóg** (hangt er een
   koppeling op mij of op een voorouder?). De cue-**vorm** (het `gapIds`-kanaal op `ProcesDiagram`,
   dashed + popup) is generiek en al aanwezig, bewust vrijgehouden voor gate 3 — alleen de
   afleiding die hem vult moet gebouwd worden (cyclus-veilig, DAG met meervoudige ouders).
3. **Een plek is geen element-id.** De bestaande signaal-aggregator sleutelt per element-id; een
   plek is een tuple `(functie, ouder-functie)` en de "niets"-stand heeft geen component om naar te
   linken. Het plek-signaal past dus niet zonder een nieuw itemtype (of een eigen plek-signaal-
   afleiding) naast de per-element-aggregator.
4. **De naam "plaatsingsignaal" is al bezet** (het bestaande component-`draait_op`-signaal) — gate 3
   krijgt een eigen naam.
5. **Eén gedeelde afleiding** (besluit 5): boom-cue én centrale teller/lijst uit dezelfde functie,
   met een bronscan-test die een tweede implementatie laat falen (zoals de leesregel-borging in
   ADR-049).

---

## Alternatieven overwogen

1. **Strikt** (koppeling hoog werkt niet door) — **verworpen**: gooit bekende informatie weg; de
   werkvoorraad wordt een klaagmuur die de consultant leert negeren (besluit 1).
2. **Rollup** (koppeling groent de subboom) — **verworpen**: verzint antwoorden op ongestelde
   vragen — de LI040-fout die met twee migraties is verwijderd (besluit 1).
3. **"Geen systeem" in een aparte tabel** — **verworpen**: twee bronnen over één vraag, tweede-
   waarheid-val (besluit 2).
4. **Noodgreep als catalogus-vlag op het componenttype** (ADR-045's oorspronkelijke lijn) —
   **verworpen**: laat de vorm van het ding het oordeel bepalen; liegt in beide richtingen
   (besluit 3).
5. **Het oordeel verplicht maken** — **verworpen**: dwingt tot gokken; een verzonnen oordeel is niet
   van een echt te onderscheiden (besluit 4).

---

## Addendum LI042 — de kaart als derde venster op `plek_standen` (gate 4, besloten; bouw volgt)

Gate 4 (ADR-043 §"Gate 4", besluit G8) voegt een **derde consument** toe aan de afleiding van dit ADR:
de **bedrijfsfunctie-laan op de kaart**. Naast de boom-cue en de centrale werkvoorraad (besluit 5) toont
de kaart-plek voortaan dezelfde vier standen (`gat` / `via_boven` / `hier` / `niets`) — de **OMHOOG-gap**:
een plek is een gat als er op die plek zelf niets hangt, met de derde stand "ondersteund via een
bovenliggende functie". **Dezelfde `plek_standen`-afleiding, een extra venster — geen tweede implementatie**
(besluit 5 blijft de borging: bronscan-test laat een tweede afleiding falen).

Bewust **niet** overgenomen: de bestaande proces-kaart-cue kijkt **omlaag** (gat érgens in de subboom
eronder — `_procesZonderSysteem`). Dat is een **andere vraag** ("draagt iets ónder mij iets?" i.p.v. "draagt
iets óp of bóven mij iets?") en past niet op de plek-cue van gate 3. De omlaag/roll-up-blik kan later een
aparte overzichtslaag worden, maar is **niet** de cue op de plek.

Randvoorwaarde uit ADR-043 besluit G7 (laan van **plekken**, niet van functies): omdat de kaart per plek
één knoop tekent, mapt `plek_standen` er **1-op-1** op — precies de reden dat de teleenheid de plaatsing
moet zijn (ADR-044 besluit 4). Status: **besloten (LI042), bouw nog niet gestart.**

---

## Naschrift — over "zonder herbouw" (geen schuld)

Het checkpoint meldde terecht dat `functievervulling` een schemastap nodig heeft om "geen systeem
vastgesteld" te dragen, terwijl de gate-2a-oplevering stelde dat het "zonder herbouw" kon. Dat is
een onscherpe formulering, geen fout in de bouw: **"zonder herbouw" betekende dat de registratie
niet opnieuw ontworpen hoeft te worden** — een kolom erbij is geen herbouw, en dat is precies wat
besluit 2 vraagt. De vorm draagt het eindbeeld dus wél zoals bedoeld; er is geen incident.
