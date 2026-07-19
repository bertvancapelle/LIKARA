# ADR-050 — Wie registreert, corrigeert: de rollengrens knipt op het onderwerp, niet op het werkwoord

| | |
|---|---|
| **Status** | **Gerealiseerd.** De rollengrens-sweep (besluiten 1–4) gebouwd (LI041, `980587b`): classificatie in `backend/app/core/rbac.py` (`REGISTRATIE_FEIT_ENTITEITEN`/`LANDSCHAPSOBJECT_ENTITEITEN` → `verwijder_actie`, `:255-289`), frontend-gating spiegelt mee (registratie-feit → `WIJZIGEN`/medewerker, landschapsobject → `VERWIJDEREN`/beheerder). Geborgd door `test_rollengrens_adr050`. |
| **Datum** | 2026-07-14 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-010 (RBAC-rollenmatrix) · ADR-012 (tweelaags rollenmodel) · ADR-042 (procesvervulling — waar de regel voor het eerst is opgeschreven) · ADR-049 (gate 2a — de achtste instantie) · ADR-023 (unified relatiemodel — de aggregation/composition-vs-uitspraak-scheiding) · ADR-036 (organisatiegebruik) |
| **Grond** | `docs/Meting-rollengrens-V041.md` (read-only meting, deze sessie) · `routes/procesvervulling.py:5-7` (de regel, al opgeschreven) · besluiten Bert LI041 |
| **Invariant (ongewijzigd)** | Score blijft de enige lifecycle-driver. Dit ADR raakt rechten + gating; de engine wordt niet aangeraakt. De rechtenmatrix (`PERMISSIES`) verandert niet. |

---

## Context — een half nageleefde regel is de schuld

Een consultant koppelt in de workshop met één klik een systeem aan een bedrijfsfunctie. Hoort hij twee
minuten later *"nee, dat is vorig jaar uitgefaseerd"*, dan kan hij zijn eigen registratie **niet
terugnemen** — daar moet een beheerder aan te pas komen (gate 2a: koppelen = medewerker, ontkoppelen =
beheerder). Wie mag registreren maar niet corrigeren, heeft geen bevoegdheid maar een **val**: één klik
heen, en je zit eraan vast. In de praktijk omzeilt de consultant dat — er iets naast zetten, of het laten
staan — en dan liegt de kaart, precies waar we hem eerlijk wilden houden.

De code kende de regel al en schreef hem zelfs op (`routes/procesvervulling.py:5-7`):

> *"het opheffen van een registratie-feit is registratiebeheer (medewerker-werk), geen verwijdering van een
> inhouds-object."*

De meting (`docs/Meting-rollengrens-V041.md`) legde bloot: **vier** registratie-feiten volgen die regel
(procesvervulling, roltoewijzing, bedrijfsfunctie-plaatsing, contract band-dekking — alle guarden hun delete
op `WIJZIGEN`). **Zeven** vergaten hem en staan op `VERWIJDEREN` (beheerder), waaronder gate 2a. Een regel
die alleen in tekst bestaat en per route opnieuw gekozen moet worden, wordt vergeten — dat is precies wat er
gebeurde. Daarom wordt hij nu uitgesproken en overal toegepast.

---

## Besluit 1 — De grens knipt op het onderwerp

> **Wat de gemeente zégt** — koppelingen, gebruik, rollen, scores, vervullingen — is **registratie**. De
> **medewerker** legt vast, corrigeert en neemt terug. Volledige CRUD.
>
> **Wat er bestáát in het landschap** — componenten, contracten, partijen — vernietigt de **beheerder**. Eén
> delete daar sleept andermans werk mee.
>
> **Wat de gemeente kréég** — het referentiemodel, de functieboom — is de grond eronder. Die verbouw je niet.

De rechtenmatrix verandert **niet**. Wat verandert is **welke handeling elke verwijder-knop bewaakt**: een
registratie-feit opheffen guardt op **`WIJZIGEN`** (medewerker mag het), een landschapsobject vernietigen op
**`VERWIJDEREN`** (beheerder). **Er komt geen nieuwe rol** — de consultant *is* de medewerker.

---

## Besluit 2 — Drie categorieën (indeling uit de meting)

| Categorie | Wat het is | Verwijder-pad | Entiteiten |
|---|---|---|---|
| **Inrichting** | bepaalt hoe LIKARA wérkt | platform: **geen hard-delete** (soft-deactivate, W) | alle `*config`-catalogi (platform); `checklistvraag` (tenant, gedraagt zich al zo) |
| **Landschapsobject** | een ding dát bestaat | **`VERWIJDEREN`** (beheerder) | component · contract · partij · datatype · gebruikersgroep · bedrijfsfunctie · proces · plateau · work_package · deliverable · gap |
| **Registratie-feit** | een *uitspraak óver* dingen | **`WIJZIGEN`** (medewerker) | functievervulling · procesvervulling · roltoewijzing · organisatiegebruik · component_contract · checklistscore · bedrijfsfunctie-plaatsing · contract band-dekking · plateau/gap/deliverable-lid · `relatie` (**alle** typen — zie besluit 4) |

Onaangeroerd op `VERWIJDEREN`/beheerder blijven **alle landschapsobjecten**. Het inrichtingsdomein kent al
geen hard-delete (`platform_rbac.py:55`) — daar bestaat "vernietigen" niet, alleen deactiveren.

---

## Besluit 3 — `checklistscore` gaat mee

De afgeleide blokkade die bij het verwijderen van een score meeverdwijnt
(`checklistscore_service.py:417-421`; `models.py:1052`) is een **gevolg** van die score, geen zelfstandige
menselijke registratie — een schaduw bij een ding. Wie de score mag zetten (medewerker, al zo), mag hem
terugnemen. De **engine-invariant blijft**: score is de enige lifecycle-driver; alleen *wíé* hem mag
terugnemen verandert.

---

## Besluit 4 — Alle relaties zijn uitspraken; de grond herken je aan de herkomst, niet aan het relatietype

Het onderscheid tussen "uitspraak" en "grond" zit **niet in het relatietype en niet in het endpoint**, maar
in de **herkomst**: het één is *gezegd* door de gemeente, het ander *gekregen* uit een referentiemodel.

- **Grond** = wat uit een referentiemodel komt (de bedrijfsfunctie-plaatsingen met bronsleutel). Niet
  corrigeerbaar — **door niemand**, ook de beheerder niet (*"modelinhoud lees je, je wijzigt hem niet"*,
  ADR-043). Beschermd door **`MODELINHOUD_BESCHERMD`**, een **inhoudelijke** bescherming, **geen rol**. Zou je
  de grond met een rol beschermen, dan zeg je impliciet dat een beheerder de GEMMA-boom mág verbouwen — dat mag
  hij niet.
- **Alle overige relaties zijn uitspraken** van de gemeente over haar eigen landschap → **medewerker
  (`WIJZIGEN`)**: `flow` · `association` · `assignment` · `access` · `serving` · `realization` ·
  **component-samenstelling** (`aggregation`/`composition` tussen componenten — *"onze Burgerzaken-suite bestaat
  uit Aangiften, Reisdocumenten en Verkiezingen"*) · **plateau-/gap-/deliverable-lidmaatschap** (*"dit systeem
  hoort bij onze doelsituatie van 2027"*).

⚠ **De knip op relatietype vervalt volledig, en er komt geen knip op endpoint.** Beide zouden een *tabelfeit*
respectievelijk een *endpoint-feit* tot bevoegdheidsregel maken — dezelfde fout in twee jasjes. Een relatietype
zoals `aggregation` draagt zowel de GEMMA-grond (gekregen) als de component-samenstelling (gezegd); alleen de
herkomst scheidt ze. Een nieuw relatietype **erft medewerker**, tenzij het uit een referentiemodel komt.

### De grond beschermde zichzelf niet — een bug die deze slice blootlegt en dicht

De meting vond dat `MODELINHOUD_BESCHERMD` alléén in `bedrijfsfunctie_service` leeft, terwijl
`relatie_service.verwijder` (`:213-215`) **geen enkele guard** heeft en elke relatie op id wist. De modelinhoud
was dus beschermd via de **voordeur** (het bedrijfsfunctie-plaatsing-endpoint) en stond open via de
**achterdeur** (het generieke relatie-endpoint). Dat dit vandaag beheerder-only is, is **geen bescherming maar
geluk**. Een bescherming die maar op één plek leeft is geen bescherming — dezelfde les als de gedeelde
leesregel-bouwsteen in ADR-049. Daarom sluit deze slice de grond **eerst** (één slot, teruggevoerd op de
bestaande `MODELINHOUD_BESCHERMD`-bescherming; het legitieme import-pad houdt zijn `via_import`-sleutel), en
verschuift **dan** de rollen. De guard is een **bugfix**, geen concessie aan de sweep.

---

## De grond onder de regel (waarom dit veilig is)

De cascade-meting toont: **vernietiging die andermans werk wist zit uitsluitend bij landschapsobjecten.**
`component`-delete is het scherpst — één klik wist scores, blokkades, koppelingen, roltoewijzingen én
gebruiksfeiten, **zonder enige weigering** (`component_service.py:762-772`; de read-only `impact_analyse` op
`:841` wordt niet aangeroepen). Die objecten blijven juist bij de beheerder. De registratie-feiten die
verschuiven nemen bij een delete **niets** uit het landschap mee — hun hele punt is dat er niets verdwijnt
(functievervulling: het grove antwoord wordt weer leesbaar, ADR-049; organisatiegebruik: de 409-weigering bij
verfijning **blijft**, die beschermt tegen stil verlies, niet tegen de verkeerde rol).

---

## Gevolgen (benoemd, niet gebouwd — stap 2 volgt ná Berts akkoord)

1. **De regel wordt structureel geërfd, niet per route herhaald.** Er komt één gedeelde vorm — een expliciete
   categorie/constante bij de entiteit (inrichting · landschapsobject · registratie-feit) — waaruit het
   verwijder-pad (`WIJZIGEN` vs `VERWIJDEREN`) volgt. Een nieuw registratie-feit **erft** de regel in plaats
   van hem opnieuw te moeten kiezen; dat is de enige manier waarop "zeven feiten vergaten hem" onmogelijk
   wordt. Een structurele borging (bronscan-/dekkingstest) bewaakt dat elk registratie-feit-DELETE op
   `WIJZIGEN` guardt.
2. **Frontend-gating beweegt exact mee** (`magVerwijderen` → `magBewerken` voor de verschoven feiten); geen
   scherm strenger of losser dan de backend (de meting vond nu geen gat; er ontstaat er geen).
3. **Geen schema, geen migratie** — rechten + gating. De rechtenmatrix (`PERMISSIES`) blijft `_INHOUD`.
4. **De grond beschermt zichzelf** (besluit 4): `relatie_service.verwijder`/`werk_bij` weigeren een
   modelinhoud-plaatsing (aggregation waarvan het kind een bedrijfsfunctie mét bronsleutel is) met
   `MODELINHOUD_BESCHERMD` — één slot, teruggevoerd op de bestaande bescherming; het import-pad blijft werken.
5. **Verschuift** (naar `WIJZIGEN`/medewerker): functievervulling · `relatie` (**alle** typen, veilig ná de
   guard) · organisatiegebruik · component_contract · checklistscore · plateau/gap/deliverable-lidmaatschap.
   **Blijft** (op `VERWIJDEREN`/beheerder): alle landschapsobjecten (component · contract · partij · datatype ·
   gebruikersgroep · bedrijfsfunctie · proces).

---

## Alternatieven overwogen

1. **Een vijfde rol ("consultant")** — **verworpen**: verplaatst de vraag naar *"is deze persoon een
   consultant?"* en vermenigvuldigt de rechtenmatrix. De consultant ís de medewerker; de grens hoort bij het
   onderwerp van de handeling, niet bij een extra rol.
2. **Alleen gate 2a repareren** — **verworpen**: laat de regel half nageleefd (zeven feiten blijven fout) en
   herhaalt precies de fout die de sweep juist verhelpt — een regel die per route opnieuw gekozen wordt, wordt
   opnieuw vergeten.
3. **De knip op relatietype** (aggregation/composition → beheerder) — **verworpen**: een relatietype draagt
   zowel de GEMMA-grond (gekregen) als de component-samenstelling (gezegd); knippen op het type maakt een
   *tabelfeit* tot bevoegdheidsregel en zou de medewerker vastzetten aan zijn eigen component-samenstelling
   (besluit 4).
4. **De knip op endpoint** (*"plateau-leden lopen via hun eigen endpoint, dus die knippen los"*) — **verworpen**:
   dezelfde fout als de tabel-knip, in een ander jasje — een *endpoint-feit* als bevoegdheidsregel. Het verschil
   zit in de herkomst, niet in het endpoint (besluit 4).
5. **De grond met een rol beschermen** (alleen de beheerder mag de GEMMA-boom wijzigen) — **verworpen**:
   modelinhoud is voor *niemand* corrigeerbaar; een rol-bescherming zegt impliciet dat de beheerder de boom mag
   verbouwen. De bescherming is inhoudelijk (`MODELINHOUD_BESCHERMD`), niet rol-gebaseerd (besluit 4).
6. **De rechtenmatrix aanpassen (V naar medewerker geven)** — **verworpen**: dat zou de medewerker óók
   landschapsobjecten laten vernietigen. De grens hoort op route-niveau (welke actie de DELETE bewaakt), niet
   in de matrix-`V`.
