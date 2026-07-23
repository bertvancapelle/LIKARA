# Checkpoint — vraagevolutie (LI050, read-only meting)

**Doel**: gemeten grond onder het ontwerp "vragen evolueren" (verduidelijking vs. wijziging,
uitbreidende keuzelijsten, rustige melding voor de consultant, totaalbeeld + voorspelling voor de
beheerder, niets blokkeert). Dit checkpoint bouwt niets en kiest niets.

## Stand

- Branch `master`, HEAD `ac3b92f` (sleep-snede geland).
- **Ongecommit**: de ergonomie-snede (3 bestanden: `ChecklistConfigBeheer.vue`,
  `ChecklistConfigBeheer.test.js`, `sleepLijst.test.js`) wacht op browsercheck + akkoord.
- Untracked: `docs/Analyse-rechtenverdeling-V050.md` (eigen commit-spoor).
- Metingen: dev-tenant `11111111-…`, als `lk_app` met tenant-context.

## M1 — Wat weet een antwoord vandaag over zijn vraag?

- **Uitsluitend de vraag als geheel**: `checklistscore.checklistvraag_id` (models.py:1117, composiet-FK
  r1094-1098). Geen tekst-snapshot, geen versieveld op het antwoord.
- **Vraagtekst is vandaag al wijzigbaar** in opslag en API: `VraagUpdate.vraag` (schemas/
  checklistconfig.py:138, max 2000 tekens), service `werk_vraag_bij` (checklistconfig_service.py:319-335),
  route `PATCH /vragen/{id}` (routes/checklistconfig.py:133). Het **scherm biedt géén
  tekstbewerking aan** — de enige frontend-aanroep is de sleep-volgorde (ChecklistConfigBeheer.vue:335).
- **Met bestaande antwoorden gebeurt feitelijk niets**: `werk_vraag_bij` raakt alleen de vraagrij —
  geen markering, geen herberekening, geen melding.
- **Audit**: ja — `checklistvraag` staat in `AUDIT_TENANT_ENTITEITEN` (app/core/audit.py:59-62);
  een update wordt vastgelegd als `{veld: {oud, nieuw}}` (audit.py:155-181), append-only met
  hash-keten. De oude formulering is dus **terugvindbaar, maar als logregel**: opvraagbaar per
  entiteit (auditlog_service), zonder relatie vanaf het antwoord — reconstructie van "wat stond er
  toen ik antwoordde" vergt een tijdstip-join over de log. Bron-kwaliteit: logregel, geen domeinbron.

## M2 — Wat gebeurt er vandaag met een keuzelijst die verandert?

- **Toevoegen**: alleen aan vrije sets (checklistconfig_service.py:523-541; afgeleid → 409).
  **Hernoemen** (label): mag altijd, óók bij afgeleide sets (r558-565; volgorde bij afgeleid → 409).
  **Uitzetten**: alleen vrije opties, soft (`actief=false`, r574-581). **Heractiveren bestaat niet**
  (`OptieUpdate` kent alleen label/volgorde, schemas:217-223; geen route).
- **Antwoord naar een uitgezette optie**: op data niet meetbaar — de tenant heeft **0 inactieve
  opties en 0 optie-antwoorden** (zie tellingen). Uit de code: leesbaar — de vraag-read levert ook
  inactieve opties voor label-resolutie (checklistvraag_service.py:9-11); de keuze-control toont
  alleen actieve (ChecklistscoreSectie.vue:226-229).
- **Spoor van uitbreiding ná antwoorden**: geen domein-spoor. `ChecklistVraagOptie` heeft **geen
  TimestampMixin** (models.py:1050) — zelfs geen `created_at`. Alleen de audit-log (optie-creates
  worden geauditeerd, audit.py:62) kan de volgorde der dingen reconstrueren.

## M3 — Herbruikbare bouwstenen (norm-patroon, ADR-052)

| Onderdeel | Oordeel | Reden |
|---|---|---|
| Scheiding "lat verschoven" (neutraal) vs "bewust afgeweken" (amber) | **model + presentatie herbruikbaar** | Eén backend-bron (`api.componentNormen.afwijking`), presentatie-splitsing in MigratiegereedheidSectie.vue:19-60 (besluiten 8-11). Het principe — "verouderd door andermans besluit" is neutraal, nooit rood — is exact wat de consultant-melding nodig heeft; de afleiding zelf is feit-sleutel-specifiek. |
| Klaarverklaring-snapshot (`open_feiten`) | **model** | Bevriest de stand op het móment van het besluit (models.py:1483-1489; klaarverklaring_service.py:61-70, 84-86): echte kolom, server-berekend, audit vangt de omslag. Vraagevolutie vraagt het omgekeerde (stand per antwoord op antwoord-moment), maar de vorm is het bruikbare voorbeeld. |
| Voorspelling vóór opslaan ("raakt N") | **herbruikbaar** | `impact_telling` (checklistconfig_service.py:229-237) + `_bevestigImpact`-confirm in het beheerscherm bestaan al voor vraagbeheer. Voor evolutie telt hij iets anders (antwoorden op déze vraag i.p.v. componenten van het type), maar de vorm — read-only telling + bevestiging vóór de mutatie — is generiek. |
| Signaal wegwerken door consultant | **model, geen kant-en-klare vorm** | Dichtstbijzijnde: de "bewust geen"-bevinding (ADR-052 besluit 9/10) — een expliciete, geauditeerde menshandeling dooft een systeem-signaal (component_bevinding_service; demping in component_open_punten_service.py:20-23). Eén-klik "mijn antwoord klopt nog" is nieuw, het principe bestaat. |

## M4 — Waar zou de consultant het zien?

- **De plek bestaat**: tabblad "Open punten (N)" onder Beoordeling (ComponentDetail.vue:263, LI048
  besluit 1), gevoed door `component_open_punten_service` met drie blokken; **blok 3 "dit valt op"**
  is de bestaande categorie voor niet-blokkerende signalen (docstring r7-11) — checklist-nee/deels
  wordt daar nu al gebundeld getoond met route naar het checklist-tabblad. Een verouderd-antwoord-
  signaal zou die weg volgen.
- **Blokkeert er iets?** Nee, nergens: de teller is `len(punten)` (besluit 14, alleen een getal op
  het tabblad); de lifecycle leest uitsluitend `score` (ADR-013/016, `actieve_vraag`); en
  klaarverklaren wordt **niet geweigerd** op open feiten — die worden gesnapshot
  (klaarverklaring_service.py:84-86). **De niet-blokkerende signaalcategorie bestaat dus al.**
- **Totaalbeeld beheerder**: het dashboard splitst readiness al per componenttype
  (dashboard_service.py:6, 69-84), maar een vraagevolutie-beeld ("welke wijzigingen, hoeveel
  verouderde antwoorden") bestaat niet — dat deel is nieuw; de plek is een ontwerpkeuze.

## M5 — Wat kost het minimaal in de opslag?

**Tellingen dev-tenant** (lk_app, tenant-context): **267 antwoorden** (Checklistscore); daarvan
**0 met gestructureerd antwoord** — alle 267 `antwoord_waarde` zijn JSON-null. **26 vragen met
keuzelijst, 96 opties, 0 inactief.** Een vulling bij invoering stelt dus weinig voor: 267 rijen
stempelen, 0 optie-antwoorden om te migreren.

**Alternatieven (keuze aan Bert, consequentie erbij):**
- **A — tekst-snapshot op het antwoord** (kolom op `checklistscore`, gevuld bij scoren): kleinste
  bouw; "wat stond er toen" per antwoord direct leesbaar; kost tekst-duplicatie per antwoord; het
  beheerder-besluit (verduidelijking vs. wijziging) vergt daarnaast alsnog een markering.
- **B — vraagversies** (versienummer op de vraag + versietabel met oude teksten; het antwoord draagt
  het versienummer waarop het antwoordde): draagt het besluit natuurlijk — verduidelijking = geen
  bump, wijziging = bump → alle antwoorden met een lager nummer zijn "verouderd" zonder
  per-antwoord-schrijfactie; kost een nieuwe tenant-tabel (+RLS, migratie, seed).
- **C — alleen een verouderd-markering op het antwoord**, audit als tekstbron: minimale opslag, maar
  "oude formulering opvraagbaar" leunt dan op de logregel — precies de zwakte uit M1.
- **Keuzelijst-uitbreiding herkenbaar**: minimaal `created_at` op de optie (ontbreekt vandaag,
  models.py:1050) — of dezelfde versie-/markeringsvorm als de vraagtekst.

## M6 — Wat botst er?

- **Per-ongeluk-blokkeren, twee sluippaden**: (1) als "verouderd" in **blok 1** ("dit moet nog") zou
  landen i.p.v. blok 3 — blok 1 voedt de klaarverklaring-snapshot `open_feiten`; (2) als "verouderd"
  geïmplementeerd zou worden door de **score te legen** — score is de enige lifecycle-driver, dus dan
  draait de status terug. Beide zijn per ontwerp te vermijden; het besluit "antwoord blijft bestaan"
  sluit (2) al uit.
- **Teksten die bij bouw mee moeten**: VraagUpdate-docstring "bewerkbare (niet-tellende) velden…
  geen fan-out" (schemas/checklistconfig.py:132-134) — klopt vandaag, wordt onwaar zodra wijzigen
  gevolgen krijgt. Optie-docstring "bewerken = soft-deactiveren" (models.py:1053) — label-hernoemen
  kan vandaag al stil, ook bij afgeleide sets: hetzelfde evolutie-gat, nu ongedocumenteerd.
  ADR-022 §"herkomst toont de vraagtekst" (ADR-022:255) — bij evoluerende tekst toont herkomst de
  húidige formulering, niet die van toen. Geen ADR verbiedt dit ontwerp; ADR-019 (stabiele sleutels,
  soft-deactivatie) ondersteunt het juist.

## Niet kunnen vaststellen

- Het feitelijke gedrag van een antwoord op een uitgezette optie op échte data (0 gevallen; alleen
  het codepad vastgesteld).
- Of de audit-log praktisch bruikbaar/performant is als herkomstbron (niet gemeten; READ-ONLY).
- UI-gedrag bij vraagtekst-wijziging: het scherm biedt die bewerking niet aan, dus alleen het
  API-pad kon worden vastgesteld.

## Tegenspraken

Geen harde tegenspraak met bestaande ADR's; wel drie teksten die bij bouw herzien moeten (zie M6).

## Open ontwerpvragen — besluit Bert (vanuit wat de gebruiker merkt)

1. **Verduidelijking**: merkt de consultant daar helemaal niets van, of ziet hij een stille notitie
   in de geschiedenis van zijn antwoord?
2. **"Mijn antwoord klopt nog"**: dooft die klik de melding voorgoed — en komt hij bij een
   vólgende wijziging van dezelfde vraag opnieuw?
3. **Optielabel hernoemen** (kan vandaag stil, ook bij afgeleide sets): valt dat onder dezelfde
   beheerder-keuze (verduidelijking vs. wijziging), of alleen het uitbreiden van de lijst?
4. **Waar kijkt de beheerder**: totaalbeeld op het dashboard (naast readiness per type) of in het
   vraagbeheer-scherm zelf?
5. **De oude formulering voor de consultant**: opvraagbaar bij het antwoord zelf (uitklap), of
   volstaat de geschiedenis-/logboekweg?
6. **Telt "verouderd" mee** in het Open punten-getal op het tabblad (zichtbaar, niet blokkerend),
   of alleen als badge in de checklist zelf?
