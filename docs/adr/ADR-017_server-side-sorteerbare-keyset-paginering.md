# ADR-017 — Server-side sorteerbare keyset-paginering

| | |
|---|---|
| **Status** | Aanvaard |
| **Datum** | 2026-06-07 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-005 (API: cursor-paginering, foutformaat) · ADR-009 (BWB-datamodel) · ADR-014 (canoniek foutformaat) · P5 (`pagination.py`, keyset-referentie) |

## Context

De module-lijsten gebruiken sinds P5 **keyset-cursor-paginering** op een vaste
sleutel `(created_at, id)` (`modules/bwb_ontvlechting/backend/services/pagination.py`):
`ORDER BY (created_at, id)`, een seek via `WHERE (created_at, id) > cursor`
(`tuple_`-rijvergelijking), `limit + 1` om "is er meer" te bepalen, en een
ondoorzichtige base64-cursor die `created_at|id` draagt. Een misvormde cursor ⇒
`ValueError` ⇒ canoniek **400 `ONGELDIGE_CURSOR`**.

De gebruiker kan lijsten **niet sorteren**. Sorteren mag echter **niet client-side**
gebeuren: bij gepagineerde data sorteert de client alleen de toevallig geladen
pagina, wat een misleidende ordening geeft. Sorteren hoort **server-side**, en moet
samengaan met keyset-paginering (geen terugval naar offset/limit, dat de
keyset-voordelen — stabiele, O(1)-seeks zonder grote offsets — zou verspelen).

Tegelijk is een sorteerveld dat rechtstreeks uit de querystring in `ORDER BY` zou
belanden een **injectie-/informatielek-risico**; het sorteerveld moet door een
expliciete **allowlist**.

Dit ADR legt het patroon vast en wijst één **referentie-implementatie** aan
(Applicatie-lijst). Het is het fundament voor latere consumenten (#12
blokkadesoverzicht) en de retrofit van de overige keyset-lijsten — beide **buiten
scope** van dit besluit.

## Besluit

### B1 — API-contract

Lijst-endpoints accepteren naast `limit` en `after` twee nieuwe, **optionele**
query-parameters:

```
GET /api/v1/<lijst>?limit=25&after=<cursor>&sort=<veld>&order=<asc|desc>
```

- **Default (geen `sort`/`order`)** = exact het huidige gedrag. Voor de
  Applicatie-lijst is dat `sort=created_at`, `order=asc` (chronologisch, oudste
  eerst — bevestigd tegen de code: `order_by(created_at, id)` met `tuple_ > `).
  Een client die geen `sort`/`order` stuurt, krijgt een ongewijzigde respons en
  ongewijzigd cursorgedrag → **backwards-compatible**.

### B2 — Allowlist (verplicht; security)

Elk sorteerbaar endpoint definieert een **expliciete allowlist** van toegestane
sorteervelden, als een **Pydantic-enum** (`Literal`-equivalent) per entiteit. De
enum:

- valideert `sort` op de **API-rand**: een onbekend veld ⇒ **422** (FastAPI-
  validatie), nooit een rauwe stringkolom in `ORDER BY`;
- mapt 1-op-1 op een **kolom-object** in de service (de enige plek waar een
  veldnaam een SQL-kolom wordt). `order` is een eigen enum `asc|desc`
  (`Sorteerrichting`), default `asc`.

Geen veldnaam uit de querystring bereikt ooit `ORDER BY` buiten deze map om.

### B3 — Zelfbeschrijvende cursor + mismatch-detectie

De cursor wordt **zelfbeschrijvend**: hij draagt naast de sleutelwaarde óók de
`sort` en `order` waarop hij is uitgegeven. Formaat (base64, opaque):

```
v2 | sort | order | <sorteerwaarde> | <id>
```

- De **sorteersleutel** is `(sorteerwaarde, id)` i.p.v. alleen `(created_at, id)`;
  `id` blijft de **stabiele tiebreaker** die een totale ordening garandeert (ook
  bij niet-unieke sorteerkolommen zoals `naam` of een enum).
- Een `after`-cursor waarvan `sort`/`order` **niet overeenkomt** met de huidige
  request ⇒ **400 `ONGELDIGE_CURSOR`** (geen stille, verkeerde paginering).
- De **frontend reset de cursor** bij elke sorteerwissel (begint weer op pagina 1).

De legacy-helpers (`encode_cursor`/`decode_cursor`, 2-delig `created_at|id`)
blijven **ongewijzigd** bestaan voor de nog niet geretrofitte entiteiten; de
sorteerbare helpers zijn een additieve uitbreiding.

### B4 — Richting en tiebreaker

Sorteren gebeurt op `(kolom DIR, id DIR)` met **dezelfde** richting `DIR` voor
kolom én tiebreaker, zodat één `tuple_`-rijvergelijking de seek blijft uitdrukken:

- `order=asc` → `ORDER BY kolom ASC, id ASC` + `WHERE (kolom, id) > (waarde, id)`;
- `order=desc` → `ORDER BY kolom DESC, id DESC` + `WHERE (kolom, id) < (waarde, id)`.

Dezelfde DIR op de tiebreaker is essentieel: een gemengde richting
(`kolom DESC, id ASC`) is geen geldige rijvergelijking en zou de seek breken.

### B5 — NULLS-conventie

Voor **nullable** sorteerkolommen geldt de vaste conventie **`NULLS LAST`** (in
beide richtingen), zodat ontbrekende waarden deterministisch achteraan komen en de
keyset-seek consistent blijft. Een NULLS-correcte keyset-seek vergt een uitbreiding
op de enkele `tuple_`-vergelijking (een extra predicaat op de NULL-grens).

**Reikwijdte**: de referentie-allowlist (Applicatie) bevat **uitsluitend
NOT NULL-kolommen** (`naam`, `eigenaar_organisatie`, de enum-kolommen,
`created_at`), zodat dit randgeval daar niet optrad.

> **Geïmplementeerd in CD016 (#12 blokkadesoverzicht)** — eerste consument met
> nullable sorteerkolommen (`toelichting`, `eigenaar`, `opgelost_op`). De
> NULLS-LAST-keyset zit in `services/pagination.py`
> (`encode_sort_cursor_nullable`/`decode_sort_cursor_nullable` met een **null-vlag**
> in de cursor, plus `keyset_order_by_nulls_last`/`keyset_seek_nulls_last` met de
> **case-split-seek**: niet-null-regio vs. null-staart). NULLs staan in **beide**
> richtingen achteraan; de aanpak generaliseert over tekst- én timestamp-kolommen
> (geen type-sentinel). De v2-cursor (Applicatie-lijst) blijft ongemoeid (aparte
> `v2n`-variant). **Caveat**: de NULL-ordening is offline **structureel** getest,
> nog niet **empirisch** tegen Postgres — bevestiging staat als opvolgpunt bij de
> live-DB-run (#23).

### B6 — Indexen: afweging

**Geen index-migratie in dit besluit.** Bij de verwachte volumes (honderden
applicaties per tenant) sorteert PostgreSQL triviaal in het geheugen; een index per
sorteerkolom is nu premature optimalisatie. Wanneer een sorteerkolom op een grote
tenant knelt, wordt een index `(tenant_id, sorteerkolom, id)` toegevoegd — dezelfde
volgorde als de keyset-seek, zodat hij zowel het filter, de sortering als de
tiebreaker dekt. Dit sluit aan op de bestaande backlog-discipline ("index pas bij
aantoonbare druk", vgl. de Koppeling-OR-filter-notitie).

### B7 — Frontend

- PrimeVue **DataTable** in **lazy-modus** (`:lazy`): de tabel sorteert niet zelf,
  maar emit `@sort`. De `sortField` mapt op een allowlist-veldnaam; `sortOrder`
  (1/-1) → `order` (`asc`/`desc`).
- Een sorteerklik **reset de cursor** en haalt de lijst opnieuw op met `sort`/`order`;
  **"Meer laden"** blijft binnen de actieve sortering (zelfde `sort`/`order`,
  vervolg-cursor).
- **Toegankelijk**: `aria-sort` op de actieve kolomheader, toetsenbordbedienbare
  sorteerheaders.

## Gevolgen

**Positief**
- Eén generiek, herbruikbaar keyset-sorteerpatroon (`pagination.py`) voor alle
  lijsten; volgende consumenten (#12, koppelingen) erven het zonder herontwerp.
- Sorteren is server-side en correct over paginagrenzen heen; keyset-voordelen
  blijven behouden (geen offset-scans).
- Sorteerveld-injectie is uitgesloten (allowlist-enum, 422 bij onbekend veld).
- Geen datamodel-, enum-, RLS- of migratiewijziging; volledig additief.

**Negatief / aandachtspunten**
- De cursor is nu zelfbeschrijvend (v2-formaat); cursors zijn opaque en worden niet
  over versies/sorteringen heen hergebruikt (de frontend start altijd op pagina 1
  en reset bij sorteerwissel) — een v1-cursor onder v2 levert netjes 400.
- NULLS-LAST is als conventie vastgelegd maar nog niet geïmplementeerd (allowlist
  bevat nu geen nullable kolommen); de uitbreiding volgt bij de eerste behoefte.
- De allowlist staat op twee plekken (enum voor validatie, kolom-map in de service);
  een test borgt dat beide synchroon zijn.

## Alternatieven overwogen

- **Client-side sorteren** — verworpen: sorteert alleen de geladen pagina, wat bij
  gepagineerde data een misleidende, onvolledige ordening oplevert.
- **Offset/limit-paginering om willekeurig te kunnen sorteren** — verworpen: geeft
  de keyset-voordelen op (stabiele seeks, geen dure offsets, geen verschuiving bij
  inserts tijdens het pagineren).
- **Rauw `sort`-veld direct in `ORDER BY`** — verworpen: injectie-/lekrisico; de
  allowlist-enum is niet-onderhandelbaar.
- **Index per sorteerkolom meteen aanleggen** — verworpen voor nu: premature bij de
  huidige volumes; vastgelegd als conditionele vervolgstap (B6).

## Niet in scope

- #12 blokkadesoverzicht (eerste consument ná dit fundament).
- Retrofit van de overige keyset-lijsten (koppelingen e.a.).
- De NULLS-LAST-implementatie (conventie vastgelegd; bouw bij eerste nullable
  sorteerkolom).
- Index-migraties (conditioneel, B6).
