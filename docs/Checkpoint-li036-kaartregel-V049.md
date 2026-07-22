# Checkpoint — de LI036-kaartregel in werkprotocol §ADR-onderhoud (READ-ONLY meting)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `ff754eb` · werktree schoon
**Grond:** gate-rapport verhuizing 1 (kandidaat-notering) · **Datum meting:** 2026-07-22
Niets gewijzigd behalve dit rapport. Scan groen (5 passed).

**De hoofduitkomst vooraf, want hij verandert de vraag:** de passage draagt drie lagen, en de
derde — de onderhoud-notitie "(Hoort óók terug in ADR-040 — staat op de ADR-onderhoudslijst.)"
— is een **voltooide to-do**: ADR-040 draagt de herziening al voluit sinds `a99fe23`
(2026-07-10, "LI036: ADR-onderhoud — ADR-034/040 naar de gebouwde realiteit"). Bovendien staat
de kaartregel-kern **al in likara-ux** als one-liner. Verplaatsen is dus geen schone knip maar
een samenvoeg-en-opschoon-besluit.

---

## Blok 1 — wat de passage precies zegt

**Vindplaats:** werkprotocol, kop `## ADR-onderhoud — bijwerken naar de gebouwde realiteit
(ADR-040)` op **r625**; de LI036-passage beslaat **r632–638** (7 regels, één alinea):

> "Bevestigd besluit: **een set-actie muteert uitsluitend de set, nooit de weergave.**
> Toevoegen/verwijderen/"haal buren erbij"/"voeg vervullende componenten toe" laten de gebruiker
> in de weergave waar hij is (Lagen blijft Lagen; de nieuwe componenten verschijnen dáár).
> Hercentreren/weergave-wissel hoort bij dubbelklik en de expliciete weergave-schakelaar. De
> vroegere ADR-040-regel "een set opbouwen via een ingang = brede plaat → overzicht"
> (`toonOverzicht()` in het gedeelde set-pad) is hiermee HERZIEN en uit de code verwijderd.
> (Hoort óók terug in ADR-040 — staat op de ADR-onderhoudslijst.) (LI036)"

**Functioneel drieledig — de knip letterlijk:**

| Laag | Tekst (begrenzing) | Soort |
|---|---|---|
| (i) | "Bevestigd besluit: een set-actie muteert uitsluitend de set… weergave-schakelaar." (r632–636a) | **UX-kaartregel** — hoe de kaart op een set-actie reageert |
| (ii) | "De vroegere ADR-040-regel … is hiermee HERZIEN en uit de code verwijderd." (r636b–638a) | **herzieningshistorie** — grond bij (i), UX-context |
| (iii) | "(Hoort óók terug in ADR-040 — staat op de ADR-onderhoudslijst.)" (r638) | **onderhoud-notitie** — werkprotocol-soort, en **achterhaald**: ADR-040 r212–216 draagt de herziening al voluit ("**HERZIENING — set-acties wijzigen nooit de weergave.** Het Fase-1-gedrag … is met LI036 **teruggedraaid** …"), geland in `a99fe23` op 2026-07-10 — d.w.z. de to-do was al vervuld vóór de passage in verhuizing 1 hierheen verhuisde |

**Markers:** `(LI036)` aan het slot + `ADR-040` in de tekst — beide reizen mee bij elke route.

---

## Blok 2 — leeft de regel al in likara-ux?

1. **Ja — als one-liner.** likara-ux **r784**, slotzin van de toggle-actie-bullet: "…verwijderen
   geeft een korte succes-toast. **Set-acties wijzigen nooit de weergave.**" Zelfde kern, zonder
   de uitwerking (Lagen blijft Lagen; dubbelklik/schakelaar) en zonder de herzieningsgrond.
   → Verplaatsen van (i)+(ii) is dus **samenvoegen met die zin (= herformuleren)** of
   **toevoegen ernaast (= dubbeling)** — geen schone toevoeging.
2. **Natuurlijkste landingskop:** `## LI036 — kaartpatronen: zichtbaarheid, rolbanen,
   filterbalk, toggle-acties` (**r753**) — de bullet waar de one-liner al staat, in de sectie
   die ook "een toggle-actie maakt alleen z'n eigen actie ongedaan" draagt. ⚠ Dat is zelf een
   **chronologische sessiekop**: likara-ux draagt de consolidatie-kwaal nog (ux-consolidatie is
   niet gestart) — landen dáár herhaalt het patroon dat elders net is opgeruimd.
3. **ADR-040-buurt in ux bestaat:** de herzien-noot bij §Drie-modus graaf (r211–217), §Filters,
   controls en verbergen (ADR-040) (r275) en §LI036-kaartpatronen (r753). De buurt is er; de
   kop-vorm is het voorbehoud.

---

## Blok 3 — wat raakt een verplaatsing

1. **Verwijzingen naar de passage zelf: 0** in levende bronnen en code (repo-breed op de
   kernzin; de treffers zijn ADR-040:212 — dat de regel zélf draagt — en de
   V037-vastleggingen Bouwplan/Feitenrapport, die blijven). **Naar `werkprotocol
   §ADR-onderhoud`:** 1 levende bron — NEXT_SESSION:190 (top-5 punt 3, "Werkprotocol
   §ADR-onderhoud") + 2 gegenereerde spiegels; die wijzen op de **kop**, niet op deze passage.
2. **De kop blijft overeind** zonder de passage: §ADR-onderhoud heeft zijn eigen intro-alinea
   (r627–630, de kernregel + het layout-voorbeeld). Geen lege kop.
3. **De scan vangt bij deze verplaatsing niets — en er valt ook niets te vangen:** 0
   kop-genoemde verwijzingen naar de passage; de NEXT_SESSION-verwijzing wijst op een kop die
   blijft bestaan. Onbewaakt handwerk: 0.
4. `git status` schoon · branch `master` · HEAD `ff754eb` · scan **5 passed**.

---

## De routes die uit de meting volgen (consequenties, geen keuze)

| Route | Wat er gebeurt | Consequentie |
|---|---|---|
| (a) hele passage → ux §LI036-kaartpatronen | (i)+(ii) samenvoegen met de r784-one-liner | herformuleren (Berts besluit); (iii) vervalt als voltooid; landt in een sessiekop |
| (b) alleen (i)+(ii) → ux, (iii) schrappen | zelfde samenvoeging; onderhoud-notitie weg met ADR-040:212+`a99fe23` als bewijs | idem (a); werkprotocol §ADR-onderhoud houdt alleen zijn eigen intro |
| (c) laten staan, alleen (iii) schrappen | de voltooide to-do weg; regel blijft in het werkprotocol | minimale ingreep; de kaartregel blijft op een plek waar een kaart-bouwer hem niet zoekt, met de ux-one-liner als tweede vindplaats (bestaande situatie) |

Alle drie raken 0 bewaakte verwijzingen.

## Wat je tegenkwam (buiten de vragen)

1. **De onderhoud-notitie was al 12 dagen voltooid** toen verhuizing 1 hem meeverhuisde — de
   verhuizing was verbatim (correct), maar verplaatste daarmee ook een achterhaalde zin. Een
   voltooide to-do die als open leest is precies de soort onwaarheid die deze sessie elders
   opruimt.
2. **likara-ux is de volgende kandidaat voor de chronologie-consolidatie**: de natuurlijke
   landingsplek van deze regel is een sessiekop (§LI036-kaartpatronen), en ux draagt er nog
   ~15+ (LI023 t/m LI046). Elke losse landing dáár vergroot wat een latere ux-consolidatie moet
   verplaatsen.
3. De werkprotocol-passage en de ux-one-liner zijn sinds LI036 **stil naast elkaar blijven
   bestaan** (twee vindplaatsen van dezelfde regel in twee skills) — deze meting is de eerste
   die dat als paar in beeld brengt; het is dezelfde familie als de stap-2-dubbelingen.

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
