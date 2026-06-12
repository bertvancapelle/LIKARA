# ADR-022 (voorbereiding) — Beoordelingsprofiel / checklist per componenttype

**Status**: Voorgenomen (ontwerpblok, nog niet uitgewerkt)
**Volgorde**: ADR-022 **vóór** ADR-006 (de audit-trail logt het definitieve
besturingsmodel — eerst het model vaststellen, dan auditen).
**Voortbouwend op**: ADR-021 (component-herfundering, Fasen A–E) en Wijziging W1
(CD054b — verenigde Componenten-UI, convergente aanmaak).

---

## Onderwerp

Een **componenttype kan een eigen beoordelingsprofiel (checklist) krijgen** (besluit Bert).
Vandaag draagt alleen het subtype `applicatie` een checklist + lifecycle + blokkades; kale
infra (database, fileshare, …) heeft enkel registratie. Besturing volgt het **type**, niet de
invoerroute — de convergente aanmaak (CD054b-v2) is daarvan de eerste stap: aanmaak met type
`applicatie` levert direct de checklist, ongeacht via welk pad (component- of applicatie-pad).

Het bestaande subtype-mechanisme (shared-PK supertype/subtype, `SUBTYPE_BESCHERMD`) is de
hefboom: **"nieuw checklist-dragend type = nieuw subtype-besluit"**. ADR-022 bepaalt of, en hoe,
andere typen een eigen profiel krijgen.

## Open ontwerpvragen (voor de afpelling)

1. **Lifecycle/blokkades of alleen scores?** Krijgen andere checklist-dragende typen het volledige
   engine-apparaat (lifecycle-statusberekening + auto-blokkades, ADR-013), of alleen een
   scores-checklist zonder readiness-engine?
2. **Readiness-rapportage**: tellen niet-applicatie-typen mee in de bestaande readiness-/
   impact-rapportage (één geïntegreerd beeld), of apart (per type)?
3. **Configuratievorm**: een **vragenset per componenttype**, platform-beheerd — vermoedelijk een
   nieuwe catalogus-familie-instantie (zie het catalogus-familiepatroon) die vragen aan een
   `componenttype` bindt. Hergebruikt dit `checklistvraag` met een type-discriminator, of een
   aparte tabel?
4. **Relatie tot het subtype-mechanisme**: elk checklist-dragend type als eigen subtype-tabel
   (zoals `applicatie`), of een generieker "profiel"-construct bovenop `component` zonder per-type
   subtype-tabel? Afweging: subtype-tabel = sterke typing + eigen velden; generiek profiel =
   minder schema-churn.

## Niet in deze voorbereiding

Geen besluit, geen datamodel, geen migratie — dit document bakent uitsluitend het onderwerp en
de openstaande vragen af zodat het ontwerpblok zonder kennisverlies kan starten.
