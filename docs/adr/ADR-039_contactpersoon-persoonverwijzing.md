# ADR-039 — Aanspreekpunt van een partij: verwijzing naar een geregistreerde persoon

**Status:** Besloten (Bert, sessie LI032)
**Datum:** 2026-07-04
**Relatie:** verfijnt het partijenregister (**ADR-024**) — het aanspreekpunt van een organisatie/
externe partij wordt een verwijzing i.p.v. vrije tekst. Volgt het sjabloon van **ADR-037**
(vrije tekst → partij-FK + validator + read-verrijking) en **ADR-036a** (structurele verwijzing
i.p.v. vrije tekst). Kolom-specifieke `ON DELETE SET NULL` zoals **ADR-024 B6** (`component.eigenaar_organisatie_id`).
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt.
Dit is registratie/structuur/read, geen engine.

## Context / aanleiding

Het aanspreekpunt van een partij was een **vrij tekstveld** (`partij.contactpersoon`, `String(255)`).
Voor de gebruiker gaf dat drie problemen:

- **Tikfouten en dubbelen** — dezelfde persoon werd per partij anders gespeld; geen enkele bron van
  waarheid over "wie is dit eigenlijk".
- **Geen doorklik / identiteit** — een naam als tekst leidt nergens heen; je kon niet zien of die
  persoon ook elders in het register bestaat, welke afdeling of welk e-mailadres erbij hoort.
- **Losse gegevens** — telefoon/e-mail van het aanspreekpunt stonden los van de persoon, niet bij
  de persoon zelf.

Tegelijk bestaat de persoon vaak al: in het register hangen personen onder hun organisatie/
leverancier (bijv. contactpersonen van een leverancier). Het aanspreekpunt hoort dus naar zo'n
bestaande persoon te wijzen, niet naar losse tekst.

## Besluit

1. **`partij.contactpersoon` (vrije tekst) → `contactpersoon_id` (verwijzing).** Het aanspreekpunt
   is een verwijzing naar een **persoon-partij**, optioneel (leeg = registratiegat, géén blokkade).
   Composiet-FK `(tenant_id, contactpersoon_id) → element(tenant_id, id)`, **`ON DELETE SET NULL`**
   kolom-specifiek op `contactpersoon_id` (PostgreSQL 15+; een kale SET NULL zou óók de gedeelde
   `tenant_id` nullen). Migratie **0054** op **0053**; geen backfill (ontwikkelmodus → reseed).

2. **De contactpersoon is een persoon die bij déze partij hoort.** `persoon.organisatie_id` = deze
   partij. Service-validatie `_valideer_contactpersoon` → **422 `ONGELDIGE_CONTACTPERSOON`** als de
   gekozen persoon niet bestaat, geen persoon is, of bij een andere partij hoort. Zo kan er nooit
   een aanspreekpunt worden gezet dat niet bij de partij past.

3. **Het veld leeft alleen op aard ∈ {organisatie, externe_partij}** — de aarden die een eigen
   aanspreekpunt dragen. Op een afdeling of persoon wordt het geweigerd
   (**422 `CONTACTPERSOON_ALLEEN_PARTIJ`**) — spiegel van hoe `functietitel` alleen op een persoon
   leeft (ADR-024 Optie 1).

4. **Ter-plekke aanmaken (search-first).** Staat de juiste persoon er nog niet, dan maakt de
   gebruiker die aan via een klein inline-formulier (naam verplicht + functietitel/e-mail/telefoon/
   mobiel/afdeling) zonder de flow te verlaten. De nieuwe persoon krijgt deze partij als thuis
   (`organisatie_id` = deze partij) en wordt meteen als aanspreekpunt gekozen. Aanmaken alleen met
   aanmaakrecht; de kern-maatregel tegen wildgroei is een vergevingsgezinde zoek (ilike/partieel/
   trim) zodat een bestaande persoon gevonden wordt vóór iemand een dubbele aanmaakt.

## Gevolgen

- **Read-verrijking + doorklik.** De lijst-read levert `contactpersoon_naam` (batch-join); lijst én
  detail tonen het aanspreekpunt als **doorklikbare persoon** i.p.v. kale tekst.
- **Oude tekstveld vervalt schoon.** `partij.contactpersoon` is verwijderd; de dev-seed is opnieuw
  opgezet met gekozen personen (elke leverancier krijgt zijn eerste contactpersoon als aanspreekpunt).
- **Picker is edit-only, met hint bij aanmaken.** Een persoon kan pas bij een partij horen nadat die
  partij bestaat; bij het *aanmaken* bestaat de partij-id nog niet, dus zijn er geen kandidaten. De
  picker verschijnt daarom alleen in de bewerk-flow; bij aanmaken toont het formulier een hint
  ("aanspreekpunt kies je nadat de partij is aangemaakt"). Dit is door het datamodel afgedwongen,
  geen aparte beleidskeuze.
- **Inline-formulier onder de picker.** Het aanmaak-formulier heeft meerdere velden; die renderen we
  net **onder** de picker (niet ín de dropdown-regel). Bewuste, gedocumenteerde afwijking van het
  single-veld-afdelingpatroon (ADR-036a) — toegankelijker en geen popup-op-popup.
- **RBAC/audit bewegen niet mee.** `contactpersoon_id` is een kolom op de bestaande entiteit
  `partij` (al vol CRUD, al op `AUDIT_TENANT_ENTITEITEN`); de audit-diff capture't de mapped column
  vanzelf.
- **Engine onaangeroerd, dubbel geborgd.** `partij_service` importeert geen lifecycle/score-symbolen
  (import-afwezigheidstest) en een aanspreekpunt-mutatie laat geen `component_profiel`/lifecycle
  ontstaan.

## Alternatieven overwogen

- **Vrije tekst behouden.** Verworpen: exact het probleem (tikfouten, dubbelen, geen doorklik).
- **Aanspreekpunt via de relatie-facade (`Relatie`).** Verworpen: geen ArchiMate-relatie maar een
  registratie-feit; een eenvoudige nullable FK op de partij is structureel voldoende en goedkoper
  dan een relatie-rij (ADR-023: eigen kolom bij een 1-op-1 registratie-verwijzing).
- **Aanspreekpunt op elke aard.** Verworpen: een afdeling/persoon draagt zelf geen aanspreekpunt
  (spiegel van `functietitel` persoon-only); zou de UI verwarren en registratiegaten uitnodigen.
- **Aanmaken via een aparte "+ Nieuw"-knop.** Verworpen: lokt voortijdig aanmaken → duplicaten.
  Search-first (aanmaken pas in de lege zoekuitkomst) met vergevingsgezinde zoek is de norm
  (ADR-036a / likara-ux).
