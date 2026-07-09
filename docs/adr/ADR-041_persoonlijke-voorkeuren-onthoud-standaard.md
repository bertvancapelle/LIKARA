# ADR-041 — Persoonlijke voorkeuren: "onthoud als mijn standaard"

**Status:** Gerealiseerd (LI034, V035) — voorkeur-laag (`gebruiker_voorkeur`, migratie 0055,
RBAC eigen-scope), kaart-kijkfilter als persoonlijke standaardkijk + reload-fix; de
sectie-voorkeur op "Gebruikte componenten" is bewust teruggerold (te versnipperd).
**Datum:** 2026-07-07 (voorstel) · 2026-07-08 (gerealiseerd, V035)
**Relatie:** Voortkomend uit ADR-040 (kaart-herbouw) — de vraag "welke componenttypen tellen als
*gebruikt*" bleek een labelkwestie maar is een voorkeur-kwestie. Bouwt op het gevestigde eigenaars-
patroon (Keycloak-`sub`) van `impact_view` en het tenant-scoped RLS/RBAC-recept. **Expliciet
onderscheiden van de opgeslagen views (ADR-033)** — zie context.
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt.
Puur registratie/weergave, read-only t.o.v. de lifecycle.

---

## Context / aanleiding

LIKARA is een generiek multi-tenant platform. Wat een gebruiker als "zijn beeld" van het landschap
beschouwt, verschilt per persoon en per organisatie: de één werkt altijd met alleen applicaties, de
ander rekent databases, koppelvoorzieningen en landelijke voorzieningen mee. Vandaag legt LIKARA zulke
kijk-keuzes nergens **per gebruiker, blijvend** vast:

- De kaart onthoudt ringen/set deels client-side (`sessionStorage 'lk-state'`), maar dat **overleeft geen
  nieuwe sessie of ander apparaat** en is niet per gebruiker. Filters, diepte en kleur-op-domein worden
  zelfs binnen de tab niet bewaard.
- De **opgeslagen views** (ADR-033, `impact_view`) lijken erop, maar bewaren **bewust géén** kijk-
  instellingen — de model-intentie is expliciet "een view is een startpunt, geen bevroren verkenning".
- Er is **geen** generieke per-gebruiker voorkeur-opslag (CC-validatie LI034, punt 2 — breed
  bevestigd afwezig).

Concreet bleek de sectie "Gebruikte applicaties" een labelkwestie ("applicaties" vs. "componenten").
Bij analyse bleek de onderliggende structuur al **component-breed** (de FK wijst naar de generieke
component-tabel; alleen een schrijf-slot knijpt het tot `applicatie`). Het echte punt is niet het woord,
maar dat **wíj niet mogen bepalen** welke componenttypen als "gebruikt" tellen — dat is een keuze van de
gebruiker.

**Onderscheid met de opgeslagen views.** Een opgeslagen view is *"deze specifieke set wil ik
terugvinden"* — een benoemd startpunt dat je bewust opent. Een persoonlijke standaard is *"zó kijk ik
altijd"* — een stille voorkeur die er al is zodra je binnenkomt. Twee verschillende dingen voor de
gebruiker; het model hoort dat te weerspiegelen.

---

## Besluit (kern)

1. **Persoonlijke voorkeuren worden een eigen, lichte laag** — los van de opgeslagen views. Per gebruiker
   (sleutel = Keycloak-`sub`), tenant-scoped met het gevestigde RLS/RBAC-recept. Dit is de eerste
   voorkeur-opslag van zijn soort in LIKARA.
2. **"Onthoud als mijn standaard" is een vinkje bij de keuze zelf** — niet op een apart settings-scherm,
   niet als één verzamelknop. De voorkeur woont waar de gebruiker de keuze maakt; hij ziet ter plekke
   wat zijn standaard is en kan het daar herroepen.
3. **Bewust gezet, blijft tot herroepen.** Het vinkje is de bewuste stap die "nu even zo bekeken"
   promoveert tot "voortaan mijn standaard". **Geen stille onthouding**: afwijken van je standaard
   (even iets anders bekijken) wijzigt de standaard niet — alleen het vinkje doet dat. LIKARA past de
   standaard toe bij elke sessie, op elk apparaat, tot de gebruiker hem wijzigt.
4. **Herbruikbaar patroon.** Eén mechanisme, één herkenbaar vinkje (zelfde plek, zelfde tekst overal).
   **Eerste toepassing: welke componenttypen tellen als "gebruikt".** Erkende volgende toepassingen:
   standaard-ringen, standaard verkenningsdiepte, kleur-op-domein.
5. **Vaste-bril vs. momentkeuze.** Het vinkje geldt alléén voor "hoe ik altijd kijk"-keuzes
   (componenttypen, ringen, diepte, kleur-op-domein). **Momentkeuzes** (zoekterm, welk component centraal
   staat, een selectie op de kaart, de weergave Overzicht/Praatplaat) krijgen **geen** vinkje — die
   blijven vers per keer; een onthouden default zou daar hinderen.
6. **Label-anker.** De sectiekop wordt en blijft **"Gebruikte componenten"** (vast, generiek, consistent
   met de rest van het platform: Componenten-lijst, ComponentDetail, kaart). De persoonlijke voorkeur
   bepaalt puur wélke componenttypen de gebruiker standaard ziet/vastlegt — **niet** het woord. Het label
   beweegt niet mee met de instelling (een meebewegend label klopt alleen bij precies één gekozen type;
   "componenten" klopt altijd).
7. **Afbakening: persoonlijk ≠ platformbeheer.** Dit is nadrukkelijk een **gebruikersvoorkeur**, geen
   tenant-brede beheerinstelling. (Sorteerregel voor toekomstige keuzes: platformvormend → centraal
   beheer; persoonlijke werkstijl → deze voorkeur-laag; momentkeuze → vers, inline.)

---

## Model / aanpak

- **Nieuwe lichte voorkeur-laag** (module-laag, naast `gebruiker_persoon`): tenant-scoped, `TenantMixin`
  + FORCE RLS + tenant-isolatie-policy + REVOKE/GRANT, conform het bestaande recept. Sleutel =
  Keycloak-`sub` (de gevestigde eigenaarssleutel; e-mail als niet-stabiele fallback nergens als sleutel).
- **Vorm van de opslag** (key/value vs. vaste kolommen) — subknoop 1. Voorkeur gaat uit naar een
  generieke, uitbreidbare vorm zodat latere voorkeuren (ringen/diepte/kleur) er zonder migratie bij
  kunnen.
- **Eerste voorkeur — gebruikte-componenttypen-scope.** De set toegestane componenttypen voor
  organisatiegebruik wordt per gebruiker bewaard. Het huidige schrijf-slot (`_APPLICATIE_TYPE` +
  `valideer_applicatie`) wordt verbreed zodat de gebruiker meer dan alleen `applicatie` mag vastleggen,
  begrensd door zijn eigen voorkeur-set. De read is al component-breed (geen wijziging aan de read-shape).
- **Eerlijk bij bestaande registratie** (dezelfde lijn als de popup-gaten in ADR-040): verruimen laat
  bestaand vastgelegd gebruik staan; versmallen verbergt geen bestaand feit maar maakt zichtbaar dat het
  buiten de huidige scope valt.
- **Frontend:** het "onthoud als mijn standaard"-vinkje als klein, herbruikbaar patroon (vaste plek/tekst
  bij de keuze), plus het toepassen van de bewaarde standaard bij het laden. Vorm bevestigd via de LI034-
  mockup.

---

## Invarianten

- **Engine onaangeroerd / score blijft enige driver.** Voorkeuren zijn registratie/weergave; ze voeden de
  engine niet. Dubbele engine-borging per slice zoals gebruikelijk.
- **Structureel boven conventioneel.** De per-gebruiker-scheiding wordt door RLS + `sub`-sleutel
  afgedwongen, niet door conventie.
- **Geen verzwakking van bestaande borging.** Het verbreden van het schrijf-slot houdt een gesloten,
  gevalideerde set (nu per-gebruiker-voorkeur i.p.v. hardcoded `applicatie`) — geen vrije tekst.

---

## Gevolgen

- **Eerste voorkeur-laag in LIKARA** — één kleine nieuwe module-laag + route/service + RBAC-entiteit +
  migratie. In ontwikkelmodus: alembic-stap + reseed, geen datamigratie.
- **"Gebruikte applicaties" → "Gebruikte componenten"** als vaste kop; de interne inconsistentie
  (`component_*`-datavorm onder een "applicatie"-label) wordt en passant opgeheven.
- **Schrijf-slot verbreed** van hardcoded `applicatie` naar de per-gebruiker toegestane typen-set.
- **RBAC/audit:** nieuwe permissie-entiteit voor de voorkeur-laag conform het bestaande patroon;
  voorkeuren zijn per definitie eigen-scope (een gebruiker beheert alleen zijn eigen voorkeuren).
- **Herbruikbaar** voor ringen/diepte/kleur-op-domein zodra gewenst — zonder het mechanisme opnieuw te
  bedenken.

---

## Open subknopen (te beslissen vóór de bouw — met voorlopige default)

1. **Opslagvorm.** Key/value (één rij per `(sub, voorkeur-sleutel)` met een waarde-blob) vs. vaste
   kolommen per voorkeur. *Default: generieke key/value — uitbreidbaar naar latere voorkeuren zonder
   migratie; de waarde is een klein, gevalideerd JSON-blob per voorkeur-sleutel.*
2. **Toegestane-typen-bron voor de gebruikte-componenttypen-voorkeur.** Uit welke lijst kiest de
   gebruiker zijn typen — de bestaande componenttype-catalogus (`componentconfig`)? *Default: ja, de
   bestaande componenttype-set als keuzelijst; de voorkeur is een deelverzameling daarvan.*
3. **Leeg/initieel gedrag.** Wat ziet een gebruiker zonder ingestelde voorkeur — alle typen, of alleen
   `applicatie` (huidig gedrag)? *Default: bij géén voorkeur het huidige gedrag (applicatie) als veilige
   baseline, zodat bestaande schermen niet stil veranderen; de gebruiker verbreedt bewust.*
4. **Reikwijdte van "onthoud".** Geldt de bewaarde voorkeur alleen voor de betreffende sectie/kaart, of
   platformbreed waar dat type keuze speelt? *Default: per voorkeur-sleutel, toegepast overal waar die
   keuze voorkomt (één "mijn componenttypen" geldt consistent).*
5. **RBAC-entiteit.** Eigen entiteit voor de voorkeur-laag (eigen-scope) conform het bestaande
   `_INHOUD`-patroon. *Default: ja, eigen entiteit; muteren uitsluitend eigen voorkeuren.*
6. **Herroep-ergonomie.** Is uitvinken van het vinkje voldoende om te herroepen (voorkeur verwijderd /
   terug naar baseline), of hoort er een expliciete "terug naar standaard"-actie bij? *Default: uitvinken
   = herroepen (voorkeur weg, terug naar baseline); geen aparte actie nodig.*
7. **Woordkeuze vinkje + bevestiging.** "Onthoud als mijn standaard" / "Je standaard" (mockup) —
   definitief of nog aan te scherpen. *Default: mockup-teksten als vertrekpunt; finale copy bij de bouw.*

---

## Bouw-fasering (indicatief, ná besluitvorming)

Eigen slices, ná ADR-akkoord; werktree-discipline één taak tegelijk, gate + browsercheck per UI-slice:

1. **Voorkeur-laag** (schema-gate, mét migratie + reseed) — de lichte per-gebruiker voorkeur-opslag
   (`sub`-sleutel, RLS/RBAC), read/write-route + service, engine-onaangeroerd-borging.
2. **Gebruikte-componenttypen-voorkeur** — schrijf-slot verbreden naar de per-gebruiker typen-set; kop
   naar "Gebruikte componenten"; het "onthoud als mijn standaard"-vinkje bij de keuze. Browsercheck.
3. **Toepassen bij laden** — de bewaarde standaard wordt bij binnenkomst toegepast; baseline bij geen
   voorkeur. Browsercheck.
4. **(Later, apart)** hetzelfde vinkje-patroon uitrollen naar standaard-ringen, verkenningsdiepte,
   kleur-op-domein — elk als eigen kleine slice wanneer gewenst.

Elke slice met engine-onaangeroerd-borging en de gangbare gate-discipline.

---

## Gebouwde realiteit — Slice 1 (backend voorkeur-laag)

Wat daadwerkelijk is gebouwd (met de afwijkingen t.o.v. het voorstel, en de reden):

- **Generieke key/value-laag** (subknoop 1 = key/value): tabel `gebruiker_voorkeur` (`GebruikerVoorkeur`)
  — `(tenant_id, sub, voorkeur_sleutel)` uniek, `waarde` als JSONB-blob; FORCE RLS + `tenant_isolation`
  + REVOKE/GRANT (spiegel van `impact_view`). Migratie `0055_adr041_gebruiker_voorkeur`.
- **Service** `voorkeur_service` — eigen-scope hard via `huidige_actor()`-`sub` (nooit client-
  aanleverbaar); upsert (aanmaken/vervangen), lijst-eigen, herroep (idempotent). Engine onaangeroerd.
- **Route** `/voorkeuren` — `GET` (eigen), `PUT /{sleutel}` (upsert), `DELETE /{sleutel}` (herroep);
  sleutel-vorm `^[a-z][a-z0-9_]*$` (≤100) in het pad; body `{waarde}` met `extra='forbid'` + grootte-
  guard (≤4096 bytes).
- **RBAC** — nieuwe entiteit `GEBRUIKER_VOORKEUR`. **Afwijking t.o.v. subknoop 5 / het `_INHOUD`-patroon:**
  élke tenant-rol (óók Viewer/Auditor) mag zijn EIGEN voorkeuren volledig beheren (`_EIGEN_VOORKEUR` =
  LAWV voor alle rollen), omdat een voorkeur strikt persoonlijk is (nooit gedeeld) en de feature anders
  voor lees-rollen onbruikbaar zou zijn; de eigen-scope zit in de service. Bevestigd bij de bouw.
- **Niet geaudit** (bewust): `gebruiker_voorkeur` staat NIET in `AUDIT_TENANT_ENTITEITEN` — een
  persoonlijke UI-standaard is geen compliance-record; auditen zou de hash-chain met ruis vullen.

---

## Besluit-correctie (kern) — een voorkeur is een KIJKFILTER, nooit een invoerregel

Een persoonlijke voorkeur bepaalt alléén **wat je standaard ziet**, niet **wat je mag invoeren**:

- **Wat als gebruik geregistreerd mag worden** is een eigenschap van het landschap, **gelijk voor de hele
  tenant**: organisatiegebruik is **component-breed** (elk componenttype mag). Niet persoonsafhankelijk.
- **Wat jij standaard ziet** is je persoonlijke voorkeur: een **weergavefilter** (met directe preview),
  nooit een schrijf-slot.

Dit corrigeert de eerste slice-2-poging, die de voorkeur het schrijf-slot van `organisatiegebruik` liet
sturen (per-gebruiker verschillende invoerregels op gedeelde data). Dat is teruggedraaid.

## Gebouwde realiteit — Slice 2 (herzien: kijkfilter)

- **Schrijf-slot component-breed** (`organisatiegebruik_service.py`): `toegestane_typen` +
  `valideer_gebruikt_componenttype` + de voorkeur-afhankelijkheid verwijderd; vervangen door
  `valideer_component` (doel = bestaand `Component`; niet-component/niet-bestaand → 422 `ONGELDIG_COMPONENT`).
  `ensure` (no-op — de gebruikersgroep-gate levert altijd een applicatie) + `maak_aan` bijgewerkt. Geen
  per-gebruiker invoerregel meer.
- **Voorkeur = weergavefilter met directe preview** (`GebruikteApplicatiesSectie.vue`): de sectie toont op
  organisatieniveau alleen rijen waarvan het componenttype in de **live geselecteerde** set zit; de
  opgeslagen standaard seedt die set (baseline `{applicatie}`). Rijen buiten de kijk-scope worden eerlijk
  benoemd ("N buiten je huidige kijk-scope"), niet verzwegen; een hint maakt duidelijk dat het een eigen
  kijkfilter is. De read blijft component-breed (geen read-parameter).
- **Ongewijzigd:** kop "Gebruikte componenten", het "Sla mijn voorkeur op"-gedrag (opslaan-actie,
  opgeslagen/gewijzigd-status, herroep via lege selectie → baseline) en de voorkeur-laag (slice 1).
- **`voorkeur_service.haal_waarde` + `GEBRUIKTE_COMPONENTTYPEN` blijven staan** — de generieke read-API van
  de laag; de frontend leest de voorkeur via `api.voorkeuren.haalAlle` (zelfde sleutelnaam). Geen schema/
  migratie; engine onaangeroerd.

---

## Koerscorrectie 2 — de eerste toepassing is het KAART-KIJKFILTER (niet de sectie)

De sectie-toepassing (gebruikte componenten per organisatie/afdeling) bleek **te versnipperd** en is
**teruggedraaid**: de gebruikte-componenten-sectie toont weer gewoon álle gebruikte componenten
(component-breed), zónder persoonlijk filter of control. Het component-brede schrijf-slot blijft als losse
verbetering.

De juiste, eerste toepassing van het "onthoud als mijn standaard"-patroon is het **kijkfilter van de
landschapskaart als geheel**: één persoonlijke **standaardkijk**.

## Gebouwde realiteit — Kaart-kijkfilter-standaard

- **Standaardkijk = de kijk-variabelen, niet de momentkeuze** (`LandschapskaartView.vue`). Opgeslagen onder
  de voorkeur-sleutel **`kaart_kijkfilter`** (slice-1-laag, hergebruikt): `ringAan` + filters
  (`filterTypes`/`filterLeveranciers`/`filterHosting`/`filterLifecycle`/`filterRollen`/BIV) + `diepte` +
  `kleurOpDomein` + `groepeerPerOrg` + lane-opties. **NOOIT** de momentkeuze (`actieveSet`, `egoStartId`,
  `weergave`, `geselecteerdNodeId`, `zoekterm`, `focusOpSet`, `scopeOrgs`) — de standaard bepaalt *hoe* je
  kijkt, niet *waarnaar*.
- **Opslaan-actie** ("★ Sla op als mijn standaardkijk") met het herbruikbare patroon: opgeslagen/gewijzigd-
  status (knop actief zodra de kijk afwijkt), en **herroep** (→ voorkeur weg + kale default terug).
- **Toepassen met samenloopregel (precedentie):** **in-sessie `lk-state`** (herladen behoudt het werk)
  **>** **server-standaardkijk** (verse start / "Begin opnieuw") **>** kale default. Concreet:
  `_herstelKaartState` geeft nu terug of het in-sessie herstelde; is dat niet zo, dan past de mount de
  standaardkijk toe; `wisSet` ("Begin opnieuw") past de standaardkijk toe ná de reset (nooit `actieveSet`).
- **Geen backend/schema:** de voorkeur-laag + `api.voorkeuren` + `voorkeur_service` worden ongewijzigd
  hergebruikt (de blob past binnen de bestaande grootte-guard); engine onaangeroerd.
