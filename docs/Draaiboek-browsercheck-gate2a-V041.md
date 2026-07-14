# Draaiboek — browsercheck gate 2a (systeem koppelen aan bedrijfsfunctie)

**Build:** V041 (ongecommitte gate-2a-bouw) · **Datum:** 2026-07-14 · **Voor:** Bert
**Doel:** klik-voor-klik verifiëren dat de consultant een systeem aan een functie/plek kan
koppelen, verfijnen en weghalen — en dat het grove antwoord nooit stil verdwijnt.

> Loop dit van boven naar beneden af. Elke stap = **een handeling** → **een ✅ verwacht
> resultaat** (letterlijke tekst die je op het scherm ziet). Wijkt iets af: noteer stap +
> verwacht + gezien in de uitslagtabel onderaan, **stop**, en koppel terug in CC. Niet
> committen tot alles ✅ staat.

Alle namen hieronder zijn **echt** — gemeten in de dev-DB, niet verzonnen.

---

## A. Klaarzetten (eenmalig)

### A1. Stack + frontend starten, mét de gebouwde code
De api-container draait met bind-mounts, maar laadt de nieuwe koppel-routes pas na een
herstart. Draai vanuit de repo-root:

```bash
# 1. Stack omhoog (als hij nog niet draait) — de init-container migreert + seedt.
docker compose -f docker-compose.yml up -d

# 2. HERSTART de api zodat de gate-2a-routes geladen worden (verplicht — anders krijg je
#    later een foutmelding bij het koppelen).
docker compose -f docker-compose.yml restart api

# 3. Frontend dev-server (aparte terminal).
cd frontend && npm run dev
```

**Controle dat de koppel-route leeft** (verwacht `HTTP 401` = bestaat, vraagt login):
```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/api/v1/functievervullingen/dekking
```

Open in de browser: **http://localhost:3000**

### A2. Inloggen als beheerder
1. Klik **Inloggen** → je komt op het Keycloak-scherm.
2. Log in als **`beheerder-test`** / **`changeme_dev`**.

> Van gebruiker wisselen (nodig bij stap 7): klik rechtsboven in de blauwe balk op
> **Uitloggen**, en log opnieuw in met een ander account.

### A3. Naar de functieboom
Sidebar (links) → onder het kopje **BWB-ontvlechting** → klik **Bedrijfsfuncties**.
Je bent nu op het scherm met de knoppen **Boom** | **Diagram** bovenaan (blijf op **Boom**).

### A4. De testfunctie vinden
Typ in het **Zoeken**-veld: **`Toezicht`**.
De boom klapt open naar alle plekken van Toezicht. **Toezicht staat op vier plekken** —
onder elk van deze vier bovenliggende functies:

- **Toezicht en handhaving Publieksdiensten**
- **Toezicht en handhaving fysieke leefomgeving**
- **Toezicht en handhaving sociaal domein**
- **Toezicht en handhaving veiligheidsdomein**

✅ Je ziet **vier** rijen "**Toezicht**", elk nét onder een van die vier functies. Onder elke
Toezicht-rij staat de regel **"staat ook onder: …"** met de andere drie plekken (klikbaar).
Dat bewijst: één functie, vier plekken — geen kopie.

### A5. Baseline vastleggen
Er zijn nu nog **geen** koppelingen: geen enkele Toezicht-rij toont de regel
"**Ondersteund door:** …". (Hard te checken, read-only:)
```bash
docker exec lk-postgres psql -U lk_admin -d likara -At -c "SELECT count(*) FROM functievervulling"
```
✅ Uitkomst: **0**.

---

## B. De zeven stappen

> Blijf ingelogd als **beheerder-test** voor stap 1 t/m 6. De knop **Koppel systeem** staat
> in de actie-rij van een functierij (rechts; verschijnt op de actieve rij / bij focus).

### Stap 1 — Grof koppelen: "geldt overal"
1. Klik op een **Toezicht**-rij (maakt niet uit welke van de vier) op **Koppel systeem**.
2. In de dialoog "**Koppel een systeem aan "Toezicht"**": typ in het zoekveld
   (**"Zoek een systeem…"**) → **`Zaaksysteem`** → klik het aan.
3. De keuze **"Geldt overal — op elke plek waar "Toezicht" staat"** staat al aangevinkt.
   Onder de zin verschijnt: *"Zaaksysteem" ondersteunt "Toezicht" — op elke plek waar deze
   functie staat.*
4. Klik **Koppelen**.

✅ Rechtsonder een groene melding **"Gekoppeld"**. **Alle vier** de Toezicht-rijen tonen nu:
**"Ondersteund door: Zaaksysteem"** met daarachter het **getelde** label
**"geldt op alle 4 plekken"** (geen loze belofte — het label telt de reikwijdte).

### Stap 2 — Fijn koppelen op één plek: "alleen hier"
1. Zoek de Toezicht-rij die onder **Toezicht en handhaving fysieke leefomgeving** staat.
   Klik daar op **Koppel systeem**.
2. Kies systeem **`Vergunningensysteem`**.
3. Vink nu **"Alleen hier — onder "Toezicht en handhaving fysieke leefomgeving""** aan.
   De zin wordt: *"Vergunningensysteem" ondersteunt "Toezicht" alleen op deze plek (onder
   "Toezicht en handhaving fysieke leefomgeving"). Een grof antwoord op deze plek wordt hier
   vervangen.*
4. Klik **Koppelen**.

✅ Die éne rij toont nu **"Ondersteund door: Vergunningensysteem"** met label **"alleen
hier"**.

### Stap 2b — Het scherm zwijgt niet over wat het verbergt ⭐
*(De kernbevinding LI041: verdringen mag, stiekem verbergen niet.)*
Kijk op de rij die je zojuist verfijnde (Toezicht onder fysieke leefomgeving):

✅ Onder "Ondersteund door: Vergunningensysteem · alleen hier" staat een **gedempte** regel:
**"Zaaksysteem geldt overal, maar is hier vervangen door de verfijning"**. Zaaksysteem is dus
**niet** spoorloos — je ziet dat het er nog is (en er staat géén "weghalen" bij; die actie
hoort bij de plekken waar het grove wél geldt).

Kijk nu naar de **andere drie** Toezicht-rijen:

✅ Ze tonen "Ondersteund door: Zaaksysteem" met het afgetelde label
**"geldt nog op 3 van de 4 plekken"** (was "alle 4" — één plek is nu verfijnd).

### Stap 2c — Bevestigd is niet verdrongen ⭐
*(Correctie 2: een systeem dat je hier expliciet bevestigt, mag niet als "weggedrukt" ogen.)*
1. Op diezelfde rij (Toezicht onder fysieke leefomgeving) klik **Koppel systeem** → kies
   **`Zaaksysteem`** (hetzelfde systeem dat overal geldt) → vink **"Alleen hier — …"** aan →
   **Koppelen**.

✅ Zaaksysteem staat nu **gewoon** in "Ondersteund door: Vergunningensysteem, Zaaksysteem ·
alleen hier". De gedempte regel **"Zaaksysteem geldt overal, maar is hier vervangen…" is
WEG** — het systeem is hier bevestigd, niet verdrongen. De rij spreekt zichzelf niet tegen.

2. **Herstel voor de volgende stap:** klik achter **Zaaksysteem** op **weghalen** →
   **Weghalen**. De gedempte "vervangen"-regel komt terug (Zaaksysteem is weer alleen grof).

### Stap 3 — ⭐ DE KERNSTAP: het fijne weghalen → het grove is wéér leesbaar
*(Dit bewijst ADR-049: het grove antwoord is nooit weggeschreven — het stond er nog steeds.)*
1. Op diezelfde rij (Toezicht onder fysieke leefomgeving), achter **Vergunningensysteem**,
   klik **weghalen**.
2. Er opent een bevestiging "**Koppeling weghalen**" met de zin: *De koppeling van
   "Vergunningensysteem" aan "Toezicht" hier weghalen? Het antwoord dat overal geldt wordt op
   deze plek weer leesbaar.*
3. Klik **Weghalen**.

✅ Melding **"Koppeling weggehaald"**. Die rij toont nu **weer gewoon** "Ondersteund door:
Zaaksysteem" — de gedempte "vervangen"-regel is verdwenen. **Dit is de belangrijkste stap.**

### Stap 3b — De reikwijdte telt weer terug
Kijk naar de vier Toezicht-rijen:

✅ Alle vier tonen weer het label **"geldt op alle 4 plekken"** (de afgetelde "3 van 4" is
weer heel). Niets is verloren gegaan — de verfijning was slechts een leeslaag eroverheen.

### Stap 4 — Niet-koppelbaar component staat niet in de picker
1. Klik op een Toezicht-rij op **Koppel systeem**.
2. Typ in het zoekveld **`Shared DB-server`** (dat is een database — ondersteunt geen werk).

✅ **Shared DB-server verschijnt NIET** in de lijst. Onder het zoekveld staat de vaste regel:
**"Componenten waarmee werk gedaan wordt."**
3. Klik **Annuleren**.

### Stap 5 — Vervallen functie: zichtbaar, niet koppelbaar, wél een uitgang
1. Maak het **Zoeken**-veld leeg en typ **`Regionale samenwerking`**.

✅ De rij "**Regionale samenwerking**" is zichtbaar met een rustige tint en de markering
**"⚠ vervallen in het referentiemodel"**. Er is **géén** knop **Koppel systeem** op die rij,
maar wél de uitgang **"Toon in functiebeeld →"**.
2. Typ weer **`Toezicht`** in het zoekveld om verder te gaan.

### Stap 6 — Twee systemen op één plek
1. Zoek de Toezicht-rij onder **Toezicht en handhaving sociaal domein**. Klik **Koppel
   systeem** → kies **`Klantportaal`** → vink **"Alleen hier — onder "Toezicht en handhaving
   sociaal domein""** aan → **Koppelen**.
2. Klik op diezelfde rij **nogmaals** **Koppel systeem** → kies **`Extern SaaS-platform`** →
   weer **"Alleen hier — …"** → **Koppelen**.

✅ Die éne rij toont nu **beide**: "Ondersteund door: **Klantportaal**, **Extern
SaaS-platform**" (label "alleen hier"). Twee systemen dragen samen die plek.

### Stap 7 — Rol-gating: medewerker koppelt, maar haalt niet weg
1. Klik rechtsboven **Uitloggen**. Log in als **`medewerker-test`** / **`changeme_dev`**.
2. Ga terug naar **Bedrijfsfuncties** en zoek **`Toezicht`**.

✅ Op de Toezicht-rijen staat **Koppel systeem** wél (koppelen mag). Achter een gekoppeld
systeem (bv. Zaaksysteem) staat **géén** **weghalen**-link — een medewerker mag niet
ontkoppelen.
3. Klik **Uitloggen** en log weer in als **`beheerder-test`** (voor het opruimen).

✅ Als beheerder verschijnt **weghalen** wél weer achter elk gekoppeld systeem.

---

## C. Opruimen — terug naar nul

Als **beheerder-test**, zoek **`Toezicht`** en verwijder alle koppelingen die je maakte:

1. Achter **Zaaksysteem** (op een willekeurige Toezicht-rij, label "geldt overal") →
   **weghalen** → de zin zegt *"…hij verdwijnt op elke plek waar "Toezicht" staat."* →
   **Weghalen**. (Eén handeling — het grove gold overal.)
2. Op de rij onder **sociaal domein**: **weghalen** achter **Klantportaal** → **Weghalen**.
3. Idem **weghalen** achter **Extern SaaS-platform** → **Weghalen**.

✅ Geen enkele Toezicht-rij toont nog "Ondersteund door: …". Harde controle:
```bash
docker exec lk-postgres psql -U lk_admin -d likara -At -c "SELECT count(*) FROM functievervulling"
```
✅ Uitkomst weer **0** — geen restdata.

---

## D. Uitslag

| Stap | Onderwerp | ✅/❌ | Wat je zag |
|---|---|---|---|
| 1 | Grof koppelen — label "geldt op alle 4 plekken" | | |
| 2 | Fijn koppelen — alleen hier | | |
| 2b | ⭐ Verdrongen Zaaksysteem gedempt zichtbaar + "geldt nog op 3 van de 4 plekken" | | |
| 2c | ⭐ Bevestigd systeem staat gewoon; geen "vervangen"-regel | | |
| 3 | ⭐ Fijn weghalen → grof weer gewoon in de rij | | |
| 3b | Label telt terug naar "geldt op alle 4 plekken" | | |
| 4 | Database niet in picker + scope-regel | | |
| 5 | Vervallen functie — zichtbaar, niet koppelbaar | | |
| 6 | Twee systemen op één plek | | |
| 7 | Rol-gating (medewerker vs beheerder) | | |
| C | Opruimen → terug naar 0 | | |

**Afsluiting:**
- **Alles ✅** → typ in CC: **`AKKOORD: commit`** (dan pas landt de gate-2a-bouw).
- **Eén of meer ❌** → **stop**, koppel terug met *stap · verwacht · gezien*; niet committen.

---

## Bijlage — verschillen t.o.v. het gate-rapport (code wint)

1. **Starten:** het gate-rapport sprak van "rebuild/restart lk-api". In werkelijkheid volstaat
   **`docker compose restart api`** — de api draait met bind-mounts (`./backend`, `./modules`)
   en `--reload`; er is **geen** image-rebuild nodig. Een herstart is wél nodig: bij de check
   bleek de nieuwe route pas na `restart api` bereikbaar.
2. **Namen:** het gate-rapport gebruikte "Milieu" en "handhavingssysteem" als voorbeeld. In de
   dev-DB heet de functie écht **Toezicht** (goed), maar de plekken heten **"Toezicht en
   handhaving <domein>"** (niet "Milieu"), en de systemen heten **Zaaksysteem /
   Vergunningensysteem / Klantportaal / Extern SaaS-platform** (niet "handhavingssysteem").
   Dit draaiboek gebruikt de echte namen.
3. **Route-introspectie:** `GET /openapi.json` geeft in dev **404** (API-docs staan uit); het
   bestaan van een route check je daarom via de HTTP-status van het endpoint zelf (401 =
   bestaat, 404 = bestaat niet), niet via de OpenAPI-lijst.
