# OPVOLGPUNTEN — CompliData

Geparkeerde punten en volgende prioriteiten. Canoniek bijgewerkt bij sessie-afsluiting.
OPVOLGPUNTEN.md is een **normaal tracked projectbestand** (besluit DC011).
**Stand**: build **V012**, migratie head **`0028`** (`0028_adr024_partij_lidmaatschap`),
commit-basis `0a11038` (leden-overzicht filter-fix + server-side sortering).

---

## Geland deze sessie (V012)

ADR-024 partij-fundament + diverse fixes:

- `04ed4a4` — ADR-026 componenttype-typering beheerbaar.
- `fd4c299` — ADR-024 slice 1: externe partij (leverancier-promotie naar element-subtype `partij`).
- `988e337` — blokkadelijst: component-kolom + type-onafhankelijke doorklik.
- `8923114` — dashboard-label blokkades corrigeren.
- `0e02e2d` — ADR-024 slice 2a: Partijen-beheer (alle aarden) + aard-filter + `PARTIJ`-recht.
- `b2b1216` — ADR-024 slice 2a-bis: partij-lidmaatschap (persoon/afdeling → organisatie; migratie 0028).
- `0a11038` — leden-overzicht filtert op organisatie + server-side sorteerbaar (Naam/Aard) + gepagineerd.

---

## Volgende prioriteiten — ADR-024 vervolgslices

1. **2b — Rollen-catalogus.** Nieuwe relatiekenmerk-dimensie `beheerrol` (enum-migratie + seed). Rollen
   **platform-breed** (zoals de overige catalogi). Startset van **7 BEHEERBARE** rollen: Functioneel
   beheer · Technisch beheer · Applicatiebeheer · Contractbeheer · Product owner · Eigenaar ·
   Proceseigenaar. **Gate** (schema/enum-migratie). Open knopen B-i (relatietype) / B-ii/iii (rollen-
   inhoud) eerst beslissen.
2. **2c — Rol-toewijzing.** Via een `assignment`-relatie: **betrokkene → rol → component ÉN contract**.
   Frontend rol-sectie op **component-detail én contract-detail**.
3. **2d — Twee overzichten.** Object → betrokkenen + rol; partij → objecten + rol (van twee kanten).
4. **2e — Gaten-signaal (geparkeerd).** "Object zonder toegewezen rol." Sluit aan op de signalering-
   discipline (niet generaliseren vóór n=3); bouwen als concreet geval.

### ADR-024 scope-besluiten (referentie voor de slices)

- Eén **"Partijen"-scherm** met aard-filter — **geland**.
- Persoon/afdeling **verplicht** aan een organisatie; persoon **optioneel** aan een afdeling — **geland**
  (2a-bis).
- Organisatiestructuur **dieper** dan dit (sub-afdelingen, hiërarchie >2 lagen) — **GEPARKEERD**.
- **Rol leeft in de toewijzing**, niet als eigenschap op de persoon (geen functie-veld op de partij).
- **Leverancier = ROL/tegenpartij ≠ aard** (een leverancier hoeft niet `externe_partij` te zijn).

---

## Geparkeerde follow-ups (bewust uitgesteld)

1. **Contract-leverancier verruimen.** De slice-1-koppeling borgt nu `aard = externe_partij`; een
   leverancier (tegenpartij) hoeft niet extern te zijn — ook **interne organisaties/afdelingen** moeten
   als tegenpartij kunnen dienen. Apart contract-spoor (raakt `_valideer_externe_partij` + de picker-
   filter `aard=externe_partij`).

2. **Bredere sorteer-sweep** (uit het diagnoserapport — elke rij-tabel per kolom sorteerbaar; regel:
   gepagineerd/groeibaar ⇒ **server-side**):
   - *(a) lichte client-side sweep* (vaste, korte tabellen): PartijLijst (Aard/Contactpersoon),
     config-beheer-tabellen (Checklist/Component/Contract/RelatieKenmerk), detail-sub-tabellen
     (ContractSectie, contract-detail gekoppelde applicaties, StructuurSectie, PlaatsingSignalenView).
   - *(b) zwaardere server-side lijstview-slice*: de vier **migratie-lijstviews** (Plateau/Gap/
     WorkPackage/Deliverable) — vergt een sorteer-allowlist **per endpoint**.
   - *(geland)*: Component/Blokkade/Contract/Partij-lijst + leden-overzicht op partij-detail.

3. **ADR-027 — Categorie-klaar-verklaring + voortgangsrapportage.** Volledig voorstel in `docs/adr`
   (`ADR-027_Categorie_klaarverklaring_voorstel.md` canoniek landen indien nog niet). Te plannen **ná
   ADR-024**. Niet-scorend, **gescheiden van de score-engine**; per categorie **human sign-off** met
   verplicht oordeel; heropenen met reden; tenant-brede voortgang per categorie; werkverdeling-inzicht
   (leunt op ADR-024).

4. **Dashboard punt 2 (optioneel).** "X actieve blokkades op N componenten" — vergt een **distinct-count**
   van componenten-met-actieve-blokkade in `dashboard_service`, apart van de lifecycle-"geblokkeerd"-
   telling (die divergeert zodra een component met blokkade nog niet volledig gescoord is).

5. **Blokkade-doorklik type-doel (latente beperking).** Zowel de Component-kolom als de Vraag-link op de
   tenant-brede blokkadelijst routeren niet-applicatie-componenten correct naar component-detail
   (geland); let op dat **toekomstige** doelen consistent op componenttype blijven routeren.

6. **Tenant-eigen catalogi (geparkeerd).** Tenant-eigen **partijsoort** én tenant-eigen **rollen** (beide
   nu platform-breed); plus per-tenant zichtbaarheid/cosmetisch verbergen van ongebruikte catalogus-
   opties.

---

## Lopende conventies (blijvend van kracht)

- **Elke rij-tabel per kolom sorteerbaar**; gepagineerd/groeibaar ⇒ server-side (ADR-017 keyset), korte
  vaste tabellen mogen client-side, niet-tabellen (graaf/projectie/boom) vallen erbuiten. Vastgelegd in
  de complidata-frontend-skill (V012).
- **Invariant → schema (NOT NULL/CHECK/FK), beleid → code (Pydantic/422)**; conditionele CHECK voor
  "X verplicht bij aard Y", service cross-row voor "Y moet bij Z horen" (complidata-db, V012).
- **Live-DB-dekkingstest naast de seed-test**; een service-/SQL-meting bewijst het scherm-gedrag niet —
  toets end-to-end via de api-client (complidata-tests, V012).
- **Migratie-ID ≤32 tekens** (`alembic_version` = `varchar(32)`) — harde conventie.
- **Live-test-teardown ruimt element-residu structureel op**: residu-check ná de run = 0 per subtype.
- **Gate-per-schema-slice** (nieuwe tabel/RLS/migratie/RBAC/audit) → bouwen + testen + gate-rapport, pas
  commit ná `AKKOORD: commit`. Doorloop-met-commit alléén voor licht/additief (read-side/frontend/docs).
- **Signalering/registratiegat niet generaliseren vóór n=3** (complidata-frontend, V012).

---

## Pre-existing (geen bug)

- `test_auth_pkce.py::test_callback_succes_zet_cd_session_cookie` — faalt **omgevingsgebonden**
  (Secure-cookievlag in test/dev), DB-onafhankelijk. Te onderzoeken: de Secure-cookie-assertie
  omgevings-onafhankelijk maken.
- Achtergrond-uitstelpunten (refresh-token-realm-hardening, secrets, VPS-deploy e.a.): zie de
  changelog-historie; niet sessie-kritiek.
