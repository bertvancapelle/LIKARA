# Checkpoint — "wie gebruikt dit" component-breed

**Sessie:** LI047 · **Build:** V047 · **Commit:** 1dfe435 · **Type:** READ-ONLY feitenopname vóór een domeinbesluit
**Datum:** 2026-07-20

> Dit rapport **wijzigt niets** aan code/schema/seed. Het enige geschreven bestand is dit rapport zelf.
> DB-metingen zijn `SELECT` als `lk_admin`. Feiten met vindplaats (bestand:regel).
> Waar iets niet vast te stellen was: **"niet vastgesteld"**.

---

## Correctie vooraf — mijn bewering over de demostaat was onjuist

In mijn stop-rapport op de open-punten-opdracht schreef ik dat `component_norm` nul rijen heeft en dat
alle 267 checklistscores op `ja` staan. **Dat klopt niet.** Ik citeerde
`docs/Checkpoint-open-punten-tabblad-V047.md` — een rapport dat is geschreven op commit `5e00bab`,
**vóór** de reseed van deze sessie — als was het een verse meting. De reseed die daarna is uitgevoerd
heeft precies gedaan wat hij moest doen.

Verse meting (blok 5 hieronder) geeft: **10 norm-rijen waarvan 6 verplicht**, **266 ja + 1 nee**. Exact
wat jij zei. De gevolgtrekking die ik eraan hing — "de browsercheck is niet uitvoerbaar" — was daarmee
óók onjuist; alle drie de gevallen zitten in de data.

De les is niet "het document was verouderd" maar dat ik een document als meting heb gepresenteerd. Een
rapport draagt de stand van zijn eigen commit, niet die van vandaag.

---

## Kernbevinding

**Er is geen domeinregel die gebruikersgroepen aan applicaties bindt. Er is één applicatie-zijdige
controle, en het commentaar erboven verraadt dat het een overblijfsel is van een structuur die niet
meer bestaat.**

```python
# LI059 Slice 3: ouder is een component met type 'applicatie' (geen subtabel meer).
_ouder = await component_service.haal_op(session, tenant_id, data.applicatie_id)
if _ouder.componenttype != _APPLICATIE_TYPE:
    raise NietGevonden(_APPLICATIE_TYPE, data.applicatie_id)
```
`gebruikersgroep_service.py:381-384`

Toen "applicatie" nog een eigen subtabel was, wás de ouder per definitie een applicatie. LI059 haalde die
subtabel weg en verving de structuur door een typevergelijking — de beperking bleef staan als
typecontrole, zonder dat er ooit een domeinargument voor is opgeschreven.

**En het precedent bestaat al.** ADR-041 deed exact dezelfde herziening één laag hoger:

> *"Bij analyse bleek de onderliggende structuur al **component-breed** (de FK wijst naar de generieke
> [element])."* — `ADR-041:32`
> *"Schrijf-slot component-breed (`organisatiegebruik_service.py`): `toegestane_typen` [verwijderd]"* — `ADR-041:196`

De grove laag is dus al bewust verbreed, met dezelfde redenering die jij nu op de fijne laag toepast.
De verfijning is bij die herziening niet meegenomen.

---

## Blok 1 — Wat houdt het vandaag tegen?

### 1.1 De backend-weigering — **één plek, alleen bij aanmaken**

| Operatie | Typecontrole? | Vindplaats |
|---|---|---|
| **Aanmaken** (`maak_aan`) | **ja** — 404 als `componenttype != 'applicatie'` | gebruikersgroep_service.py:383-384 |
| Wijzigen (`wijzig`) | nee | — |
| Verwijderen (`verwijder`) | nee | gebruikersgroep_service.py:444 |
| Lezen (`lijst`, `haal_op`, `lees_detail`) | nee | :285, :356, :370 |

`_APPLICATIE_TYPE` komt in de hele service **twee keer** voor: de definitie (`:36`) en die ene controle
(`:383-384`). Er is geen tweede plek die het herhaalt.

⚠ Merk op dat de weigering een **404** is, geen 422. Voor de gebruiker leest dat als "dit component
bestaat niet" terwijl het er wel is — het verbergt de regel in plaats van hem uit te leggen.

### 1.2 Is de weigering een aanname of een regel? — **een aanname; geen ADR grondt hem**

Doorzocht: alle 12 ADRs die `gebruikersgroep` noemen. **Niets vastgesteld** dat de applicatie-binding
motiveert. Wat er wél staat, wijst de andere kant op:

- **ADR-036a** (`gebruikersgroep-afdeling-structureel`) beschrijft de afdeling als herbruikbaar ding en
  noemt géén typebeperking (`:50-51`).
- **ADR-036/038** (in de modeldocstring, `models.py`): een groep is *"de fijne verfijning ván dat grove
  feit"* — en dat grove feit is component-breed.
- **ADR-041:187**: *"organisatiegebruik is component-breed (elk componenttype mag)"*.

De enige toelichting bij de weigering zelf is de LI059-regel hierboven, en die legt een *herkomst* uit,
geen *reden*.

### 1.3 Het tabblad — **één conditie**

`ComponentDetail.vue:209`: `if (isSubtype.value) t.push({... key: 'gebruikersgroepen' ...})`, met
`isSubtype = !!component.value?.heeft_applicatie_subtype` (`:88`). Dezelfde vlag gate't ook het paneel
zelf (`:596`) en de Datatypes- en Koppelingen-tabs.

Het contrast staat drie regels lager in hetzelfde bestand — de grove laag draagt al de tegengestelde keuze:

```js
// ADR-046 stuk 2 — "Wie gebruikt dit" (grof organisatiegebruik) is component-breed
```
`ComponentDetail.vue:216`

**Twee lagen van dezelfde vraag, in dezelfde tabrij, met tegengestelde condities.**

### 1.4 Rechten — **entiteit-gebonden, niet type-gebonden**

Alle vijf de routes gebruiken `vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.X)`
(`routes/gebruikersgroep.py:45, :70, :95, :104, :115, :124`). Geen enkele permissie noemt een
componenttype. De grove laag is identiek opgezet (`routes/organisatiegebruik.py:41, :66, :77`).
**De verbreding raakt het rechtenmodel niet.**

### 1.5 Waar leeft de aanname nog meer? — **volledige lijst**

| # | Plek | Aard | Vindplaats |
|---|---|---|---|
| 1 | De typecontrole bij aanmaken | **gedrag** — dit is de enige echte blokkade | gebruikersgroep_service.py:383-384 |
| 2 | Tabblad + paneel achter `isSubtype` | **gedrag** | ComponentDetail.vue:209, :596 |
| 3 | Prop `applicatieId` van de sectie | naamgeving | GebruikersgroepSectie.vue:23 |
| 4 | API-veld `applicatie_id` (request + response) | **contract** | schemas/gebruikersgroep.py · service `_lees` :89 |
| 5 | Docstring *"gebruikersgroepen van één applicatie (in ApplicatieDetail)"* | tekst | GebruikersgroepSectie.vue:3 |
| 6 | Servicedocstring *"applicatie is een serving-relatie (applicatie → gebruikersgroep)"* | tekst | gebruikersgroep_service.py:4 |
| 7 | `_applicaties_van`, `applicatie_id`-filter in `lijst` | naamgeving | :152, :287, :319-324 |
| 8 | `componenten_voor_context` — *"de applicatie-bron van de serving-relatie"* | tekst (leest al component-breed) | :250-253 |
| 9 | Modeldocstring *"De band met de applicatie blijft de serving-relatie"* | tekst | models.py, klasse `Gebruikersgroep` |

**Alleen 1 en 2 zijn gedrag.** 3, 5, 6, 7, 8 en 9 zijn naamgeving/tekst; 4 is een contractnaam.

⚠ **Punt 4 verdient aandacht.** Het API-veld heet `applicatie_id` terwijl het een component-id is.
Datzelfde geldt al voor de grove laag: de kolom `organisatiegebruik.applicatie_id` draagt de opmerking
*"de kolomnaam is historisch"* (`models.py:473`), en de frontend geeft er al een component-id in door
(`OrganisatiegebruikSectie.vue:92`: `applicatie_id: props.componentId`). Er is dus een **precedent om de
historische naam te laten staan** en alleen de betekenis te verbreden. Dat is de goedkoopste weg, maar
het laat een misleidende naam in het contract staan — hetzelfde punt dat al op de opvolglijst staat voor
`heeft_applicatie_subtype`.

---

## Blok 2 — Wat raakt het buiten dit ene feit?

**Kern van dit blok: de vierde weg verandert geen enkele bepaling. Hij verandert alleen wie de vraag kán
beantwoorden.** Daarom is het antwoord op de vragen 6 t/m 9 vier keer "niets schuift".

### 2.1 (vraag 6) De norm — **betekenis noch uitkomst verandert**

De bepaling van `gebruikersgroep` blijft `_SIG_GG` afwezig ⟺ vastgesteld
(`component_norm_service.py:76`, `_FEIT_SIGNAAL`). Het signaal blijft dezelfde serving-relatie meten
(`registratiegaten_service.py:202-207`). Er wordt niets ontkoppeld.

**Voor geen enkel component in het demolandschap schuift de uitkomst** — vandaag niet. Wat verandert is
dat drie componenten die het punt dragen het voortaan kunnen wégwerken.

De contracttoets `test_signaal_mapping_is_een_bron` (`tests/test_component_norm_adr052.py:50-59`), die
vastlegt dat de vijf feiten rechtstreeks naar de signaal-constanten verwijzen, **blijft ongewijzigd
staan**. Dat was bij de drie eerdere wegen niet zo.

### 2.2 (vraag 7) De klaarverklaring-snapshot — **bestaande vastleggingen ongemoeid, nieuwe identiek**

`_open_verplichte_feiten` leest `norm_status` (`component_klaarverklaring_service.py:62-70`). Omdat de
bepaling niet verandert, verandert ook niet wat er wordt weggeschreven. Bestaande `open_feiten` zijn
opgeslagen tekstwaarden en worden sowieso nooit herrekend.

⚠ Bovendien: `gebruikersgroep` is **niet verplicht** in deze tenant (meting 5.2), dus het feit komt
überhaupt niet in een snapshot voor. Ook als het later verplicht wordt gesteld, verandert de verbreding
de uitkomst niet — alleen de mogelijkheid om hem te beïnvloeden.

### 2.3 (vraag 8) Het tenant-brede signaal — **exact dezelfde componenten, gekwantificeerd**

```sql
SELECT c.componenttype, count(*) AS componenten,
  count(*) FILTER (WHERE EXISTS(SELECT 1 FROM relatie r WHERE r.tenant_id=c.tenant_id
    AND r.relatietype='serving' AND r.bron_id=c.id)) AS met_gg_verfijning,
  count(*) FILTER (WHERE EXISTS(SELECT 1 FROM organisatiegebruik og WHERE og.tenant_id=c.tenant_id
    AND og.applicatie_id=c.id)) AS met_grof_gebruik,
  count(*) FILTER (WHERE NOT EXISTS(SELECT 1 FROM relatie r WHERE r.tenant_id=c.tenant_id
    AND r.relatietype='serving' AND r.bron_id=c.id)) AS signaal_vuurt
FROM component c GROUP BY 1 ORDER BY 1;
```

| type | componenten | met verfijning | met grof gebruik | signaal vuurt |
|---|---:|---:|---:|---:|
| applicatie | 16 | 7 | 10 | 9 |
| database | 1 | 0 | 0 | 1 |
| fileshare | 1 | 0 | 0 | 1 |
| saas_dienst | 1 | 0 | 0 | 1 |

Het signaal vuurt op **12 van de 19** componenten. Daarvan zijn er **3 niet-applicatie** — precies de
drie die het punt vandaag **niet kunnen beantwoorden**. Na de verbreding wijst het signaal **dezelfde
12 componenten** aan; het verschil is dat alle 12 er iets aan kunnen doen.

⚠ Opvallend: die drie hebben **ook geen grof gebruik** (0 van 3). Zelfs de laag die vandaag al
component-breed is, is er niet ingevuld — de fileshare waar volgens de aanleiding "Burgerzaken op werkt"
heeft in de demodata nog geen enkele gebruiker geregistreerd, grof noch fijn.

### 2.4 (vraag 9) De impact-voorspelling in Normbeheer — **schuift niet**

`component_norm_beheer_service.py:80` telt met `feit_vastgesteld`, dezelfde bepaling. Zelfde invoer,
zelfde uitkomst. Het getal "dit raakt N componenten" blijft wat het is.

### 2.5 (vraag 10) De grove laag — **blijft, en de verfijnregel geldt ongewijzigd**

De verhouding is structureel vastgelegd, niet per type: `gebruikersgroep.gebruik_id` is **NOT NULL** met
een FK naar `organisatiegebruik` en `ON DELETE RESTRICT` (`models.py`, `fk_gebruikersgroep_gebruik`).
Een groep hoort dus **altijd** bij een grof feit (ADR-038 — de org-loze groep bestaat niet meer), en
`maak_aan` maakt het grove feit aan als het nog niet bestaat (`gebruikersgroep_service.py:392`:
`organisatiegebruik_service.ensure(...)`).

**Bevestigd: die regel is typeloos.** Er is geen tak die hem per componenttype anders toepast. Voor een
fileshare zou hij precies zo werken als voor een applicatie: verfijn je naar afdeling, dan ontstaat (of
bestaat) het grove feit voor die organisatie, en de verfijning hangt eronder.

---

## Blok 3 — Waar wordt de vraag raar?

### 3.1 (vraag 11) Per type — **en het model draagt het antwoord al**

De vraag "welke afdeling gebruikt dit" is zinvol waar een component **werk van mensen ondersteunt**. Dat
is geen inschatting van mij: het is een catalogus-eigenschap die LIKARA al voert.

```sql
SELECT optie_sleutel, ondersteunt_werk, checklist_dragend FROM componentconfig_optie
WHERE dimensie='componenttype' ORDER BY volgorde;
```

| type | ondersteunt_werk | vraag zinvol? |
|---|:-:|---|
| applicatie | **t** | ja |
| database | **f** | **nee** — wordt door applicaties gebruikt, niet door een afdeling; dat is een koppeling |
| server_compute | **f** | **nee** — idem |
| client_software | **t** | ja |
| saas_dienst | **t** | ja |
| integratievoorziening | **f** | **nee** — idem |
| fileshare | **t** | **ja** — en dit is het geval uit de aanleiding |
| landelijke_voorziening | **t** | ja |

**Vijf van de acht typen: zinvol. Drie: niet.** En de fileshare, het geval dat de hele herziening
motiveert, staat aan de goede kant van die grens.

`ondersteunt_werk` is precies de vraag "wordt hier werk mee gedaan" — dezelfde eigenschap die het
`bedrijfsfunctie`-feit al type-scoopt (zie 3.3).

### 3.2 (vraag 12) Kan de norm dat onderscheid aan? — **nee, de norm niet; het signaal wél**

```sql
SELECT column_name, data_type FROM information_schema.columns WHERE table_name='component_norm';
```
→ `id · tenant_id · feit_sleutel · verplicht · created_at · updated_at`

**Geen `componenttype`-kolom.** De norm is per tenant per feit, alles-of-niets: een organisatie zet
`gebruikersgroep` verplicht voor álle typen tegelijk, of voor geen.

### 3.3 Maar de differentiatie is er al — via het signaal

`bedrijfsfunctie` lost exact dit probleem al op, en niet in de norm maar in de meting:

```python
def _ondersteunt_werk_typen():
    """Subquery: de componenttypen die WERK ondersteunen (ADR-045; catalogus-eigenschap, nooit
    een hardcoded typelijst). Gedeeld door het gat-signaal en de badge — zelfde regel als de
    koppel-picker/`functievervulling`-service."""
```
`registratiegaten_service.py:71-78`, toegepast op `:234` en `:427`

Omdat `_beslis_vastgesteld` voor signaal-gedekte feiten "vastgesteld ⟺ signaal afwezig" hanteert
(`component_norm_service.py:159-160`), telt een type-gescoopt feit voor de uitgesloten typen **altijd als
vastgesteld** — het punt ontstaat daar niet, ook niet als de tenant het feit verplicht stelt.

**Dat is precies het mechanisme dat `gebruikersgroep` mist.** Dezelfde subquery op `_SIG_GG` toepassen
maakt de vraag stil op database, server_compute en integratievoorziening, zonder de norm aan te raken en
zonder een hardcoded typelijst.

⚠ **Dit is wel een verandering van de meting**, en dus het enige punt in dit hele rapport waar wél iets
schuift: het signaal zou dan op **9 componenten** vuren in plaats van 12 (de database valt af; de
fileshare en het saas_dienst blijven, want die ondersteunen werk). Zie open vraag 2.

---

## Blok 4 — De kleinste ingreep

### 4.1 (vraag 13) Gesplitst

| Laag | Wat | Omvang |
|---|---|---|
| **Schema** | **niets** — zie 4.3 | 0 |
| **Backend** | de typecontrole `gebruikersgroep_service.py:383-384` vervangen door dezelfde validatie die de grove laag gebruikt (component bestaat, hoort bij de tenant) | ~2 regels |
| **Backend (optioneel, open vraag 2)** | `_SIG_GG` scopen op `_ondersteunt_werk_typen()`, naar het model van `_SIG_GEEN_BF` | ~1 regel + de lijst-variant :280 |
| **Frontend** | het Gebruikersgroepen-tabblad en -paneel losmaken van `isSubtype` (ComponentDetail.vue:209, :596); prop hernoemen naar `componentId` | ~4 regels |
| **Seed/demodata** | **niets nodig** — de drie niet-applicatiecomponenten hebben nog geen gebruik. Wil je de verbreding in de browsercheck zien werken, dan is één gebruikersgroep op de Shared fileshare het bewijs | 0 of 1 seedregel |
| **Tests** | zie 4.4 | 3-4 toetsen |

⚠ **Docstrings en veldnamen** (blok 1.5, punten 3-9) zijn geen gedrag maar liegen na de verbreding wel.
Dat is een eigen opruimsnede; ik zou hem niet met de gedragswijziging mengen.

### 4.2 (vraag 14) Wat verandert er zichtbaar, per type?

| Type | Vandaag | Na de verbreding |
|---|---|---|
| applicatie | tabblad, registratie werkt | **ongewijzigd** |
| fileshare · saas_dienst · client_software · landelijke_voorziening | geen tabblad; het punt "geen gebruikersgroep" staat er en is onbeantwoordbaar | **tabblad verschijnt**, het punt wordt wegwerkbaar |
| database · server_compute · integratievoorziening | idem onbeantwoordbaar | tabblad verschijnt; **mét open vraag 2** verdwijnt bovendien het punt, omdat de vraag daar niet geldt |

In het demolandschap raakt dit **drie componenten**: Shared fileshare, Extern SaaS-platform en Shared
DB-server.

### 4.3 (vraag 15) Kan iets níét zonder schemawijziging? — **nee. Er is geen schemagrens.**

Alle vreemde sleutels van `Gebruikersgroep` wijzen naar generieke doelen (`models.py`, klasse
`Gebruikersgroep`):

- `fk_gebruikersgroep_element` → `element` (elk element, geen typebeperking)
- `fk_gebruikersgroep_gebruik` → `organisatiegebruik` (**al component-breed**)
- `fk_gebruikersgroep_afdeling` → `element` (een organisatie_eenheid-partij)

De band met het component is een `serving`-relatie, en `relatie_service.maak_aan` valideert geen
`element_type`. **De structuur is dus al component-breed — net als bij ADR-041.** De beperking leeft
uitsluitend in de applicatielaag.

Er is **geen migratie nodig, geen kolom, geen enum.** Dat is het sterkste argument dat dit een
overblijfsel is en geen ontwerp.

### 4.4 (vraag 16) Borging

1. **Een tellende toets over de catalogus**: voor elk componenttype dat `ondersteunt_werk` draagt, levert
   `maak_aan` een gebruikersgroep op — geen hardcoded typelijst in de toets, maar een lus over de
   catalogus, zodat een nieuw type de regel erft.
2. **Een toets die de weigering-regressie vangt**: een gebruikersgroep op een fileshare geeft **geen** 404.
3. **De bestaande contracttoets ongewijzigd laten slagen** (`test_signaal_mapping_is_een_bron`) — dat
   bewijst dat de verbreding de norm niet heeft aangeraakt.
4. **Frontend: een tellende toets** dat het Gebruikersgroepen-tabblad voor elk componenttype verschijnt,
   in de vorm van de bestaande tabblad-toetsen.
5. ⚠ **Wat geen enkele toets vangt**: de docstrings en veldnamen die "applicatie" zeggen. Er is geen scan
   voor misleidende contractnamen — dat punt staat al op de opvolglijst voor `heeft_applicatie_subtype`.

---

## Blok 5 — De demostaat, opnieuw vastgesteld

### 5.1 (vraag 17) Verse meting — **gezond; mijn eerdere melding was fout**

```sql
SELECT 'component',count(*) FROM component
UNION ALL SELECT 'component_norm',count(*) FROM component_norm
UNION ALL SELECT 'component_norm VERPLICHT',count(*) FROM component_norm WHERE verplicht
UNION ALL SELECT 'component_klaarverklaring',count(*) FROM component_klaarverklaring
UNION ALL SELECT 'component_bevinding',count(*) FROM component_bevinding
UNION ALL SELECT 'organisatiegebruik',count(*) FROM organisatiegebruik
UNION ALL SELECT 'gebruikersgroep',count(*) FROM gebruikersgroep;
SELECT score::text,count(*) FROM checklistscore GROUP BY 1 ORDER BY 1;
```

| tabel | rijen | mijn eerdere melding |
|---|---:|---|
| component | 19 | — |
| **component_norm** | **10** | ~~0~~ **onjuist** |
| component_norm verplicht | **6** | — |
| component_klaarverklaring | 5 | — |
| component_bevinding | 3 | — |
| organisatiegebruik | 34 | — |
| gebruikersgroep | 11 | — |
| checklistscore `ja` | 266 | ~~267~~ **onjuist** |
| checklistscore `nee` | **1** | ~~0~~ **onjuist** |

**Er is geen drift.** De stand is exact wat de reseed van deze sessie hoort op te leveren; er is niets
tussen gebeurd dat verklaard moet worden. De zes verplichte feiten zijn `bedoeling · biv · contract ·
eigenaar · koppelingen · verantwoordelijke`; `bedrijfsfunctie · gebruikersgroep · hosting · levensfase`
staan op niet-verplicht.

### 5.2 (vraag 18) De drie browsercheck-gevallen — **alle drie aanwezig**

| naam | snapshot | live open (verplicht) | bewust geen |
|---|---|---|---|
| Archiefbeheer | `{}` | `{}` | koppelingen, contract |
| DMS | `{biv}` | `{biv, bedoeling}` | — |
| HR-systeem | `{}` | `{}` | koppelingen |
| Klantportaal | `{}` | `{bedoeling}` | — |
| Zaaksysteem | `{biv}` | `{biv, bedoeling}` | — |

| Geval | Component | Waarom |
|---|---|---|
| **Schoon** | **Archiefbeheer** of **HR-systeem** | klaar verklaard, snapshot leeg, live niets open |
| **Beide soorten afwijking** | **DMS** of **Zaaksysteem** | snapshot `{biv}` → `biv` is **bewust**; `bedoeling` staat er niet in → **verschoven**. Precies de twee groepen naast elkaar |
| **Bewuste vaststelling** | **Archiefbeheer** (beide soorten) of **HR-systeem** (koppelingen) | — |
| *bonus: alleen verschoven* | **Klantportaal** | snapshot leeg, live `{bedoeling}` open |

⚠ Eén afwijking t.o.v. het oude checkpoint: Archiefbeheer's snapshot is nu `{}`, niet
`{biv, eigenaar, verantwoordelijke}`. De reseed heeft die klaarverklaring op een schonere stand gezet.
**Het oude cijfer niet meer gebruiken.**

---

## Open vragen voor Bert

1. **De historische veldnaam.** Het API-veld heet `applicatie_id` maar draagt een component-id — de
   grove laag heeft dezelfde situatie en laat de naam bewust staan ("de kolomnaam is historisch",
   `models.py:473`). Laten staan en alleen de betekenis verbreden, of meenemen in de opruimsnede die al
   voor `heeft_applicatie_subtype` op de lijst staat?

2. **Type-scoping van het signaal.** Voor database, server_compute en integratievoorziening is "welke
   afdeling gebruikt dit" inhoudelijk vreemd (blok 3.1). Wil je dat `_SIG_GG` op `ondersteunt_werk` wordt
   gescoopt, naar het model van `bedrijfsfunctie` — waardoor het signaal daar stil wordt en van 12 naar
   9 componenten gaat? Dit is het enige punt in het hele voorstel waar een meting verschuift.

3. **Verplicht stellen blijft alles-of-niets.** De norm kent geen componenttype (blok 3.2). Zonder
   vraag 2 betekent "gebruikersgroep verplicht" dus ook verplicht op een databaseserver. Accepteer je
   dat, of is vraag 2 daarmee eigenlijk een voorwaarde?

4. **Het 404-antwoord.** De huidige weigering geeft 404 ("bestaat niet") in plaats van 422 ("mag niet
   hier"). Als de weigering blijft bestaan voor sommige typen, moet die dan tegelijk een eerlijker
   antwoord geven — of vervalt hij helemaal en is de vraag moot?

5. **De opruimsnede.** Zes docstrings en drie naamgevingen zeggen "applicatie" waar "component" bedoeld
   wordt (blok 1.5). Direct meenemen, of als eigen snede erna — met het risico dat de tekst een tijd
   lang iets anders zegt dan de code doet?

6. **De demodata.** De drie niet-applicatiecomponenten hebben nog géén gebruik geregistreerd, grof noch
   fijn. Wil je dat de seed er één gebruikersgroep op de Shared fileshare bij krijgt, zodat de
   browsercheck de verbreding kan laten zien in plaats van alleen een leeg tabblad?

*(STOP na dit rapport. Niets gebouwd, niets gewijzigd, geen ADR geschreven, niet gecommit.)*
