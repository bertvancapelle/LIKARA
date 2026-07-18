# Read-only ontwerpcheckpoint — norm-beheerscherm (ADR-052 slice 4)

**Sessie:** LI045 · **Build:** V045 · **Branch:** master · **Commit:** `f0fa9bd` · **Aard:** read-only feitenopname, niets gemuteerd.

> Dit document stelt uitsluitend vast wat er is, als grond voor het ontwerp van het norm-beheerscherm.
> Formulering vanuit de beheerder/consultant; code-paden staan als onderbouwing tussen haakjes.

---

## Kernbeeld in één alinea

De gemeente kán sinds LI044 een lat leggen voor "migratieklaar" — per hard feit vastleggen dat het
bekend moet zijn (`component_norm`, ADR-052 slices 1–3). Die lat wordt vandaag **alleen door de seed
gezet en nergens door een mens verzet**: er is geen scherm, geen lees-endpoint voor de norm-definitie,
en geen schrijf-endpoint. De onderliggende bouwstenen (tabel met RLS, RBAC-recht voor de beheerder,
lees-afleiding, leesbare labels, DB-schrijfgrants) zijn er al; slice 4 is de ontbrekende **kop** erop.
De demostaat is inhoudelijk perfect geprepareerd (Archiefbeheer is klaar-verklaard mét exact 3 open
feiten), maar de norm-tabel staat in de draaiende dev-DB **op nul rijen** — de demonstratie is dus wél
gebouwd maar niet aangezet.

---

## Blok 1 — Waar leeft beheer vandaag voor de beheerder

Er zijn **twee gescheiden beheer-werelden**, en dat onderscheid bepaalt waar de norm thuishoort.

**A. Tenant-beheer — binnen de gewone app-schil (`AppLayout`), voor een tenant-account.**
De beheerder van de organisatie ziet in de linker-navigatie:

| Scherm | Menupad (route) | Wie ziet het |
|---|---|---|
| **Gebruikersbeheer** | `/gebruikers` (`gebruikersbeheer`) | alleen beheerder (`magGebruikersbeheer = hasRole('beheerder')`) |
| **Auditlog** | `/auditlog` (`auditlog`) | beheerder + auditor |
| **Checklistvragen** | `/checklistvragen` | tenant-rollen (ADR-022 W1: de vragenset is tenant-eigendom) |

**B. Platform-beheer — een aparte schil (`BeheerLayout`, `/beheer/*`), alleen voor een platform-account.**
Negen catalogus-beheerschermen: contractconfig, componentconfig, relatiekenmerk, vraagbetekenis,
partijsoort, componentrol, bivschaal, applicatiefunctie, referentiemodel. Dit zijn **platform-brede**
catalogi (één matrix voor alle tenants), geen organisatie-instellingen.

**Herbruikbaar patroon.** De beheerschermen delen één herkenbare opbouw (referentie
`RolConfigBeheer.vue`, exemplarisch voor de catalogus-familie): een `<section>` met titel + korte
uitleg-alinea → een `card` met een **tabel** (Label · Sleutel · Volgorde · Status · rij-acties) →
rij-acties (Bewerken / Deactiveren / Reactiveren) → `Dialog`-formulieren voor toevoegen/bewerken →
een bevestig-dialog voor het destructieve → **per-actie een success-toast** → affordance-gating
(`magBeheren = hasRole(...)`) met de backend als enige handhaver → nette laad-/fout-toestanden en
foutmapping (403/409/422). Het is een **pure schil op de server-endpoints** (V006/CD034: geen
serverregels dupliceren). Voor een norm-scherm is dit een sterke sjabloon, mits het beseft dat de
norm géén rijen toevoegt/verwijdert maar een **vaste set van 10 feiten** met per feit een ja/nee-toggle.

**Welke rol zou de norm mogen zetten.** De norm is **tenant-eigen governance-data** (`component_norm`
is tenant-scoped met RLS — zie blok 3), dus hij hoort **niet** in de platform-schil `/beheer/*` maar in
de **tenant-schil (`AppLayout`)**. Het recht is al belegd: RBAC-entiteit `COMPONENT_NORM` (tenant-domein)
= Viewer L · Medewerker L · **Beheerder LAWV** · Auditor L (`rbac.py:199`, expliciet het
REFERENTIEMODEL/CHECKLISTVRAAG-patroon: "iedereen leest de norm — hij bepaalt 'compleet' —, alleen de
beheerder stelt hem in"). Logische plaatsing: een nav-item gegate op `hasRole('beheerder')`, naast
Gebruikersbeheer/Checklistvragen.

**Bestaat er al een "instellingen van deze organisatie"-scherm?** Er is een RBAC-entiteit
`TENANT_INSTELLINGEN` (beheerder LAWV, `rbac.py:233`), maar **geen scherm, route of nav-item** erbij —
puur een reservering. Het dichtste bestaande verwant is **Checklistvragen** (een tenant-eigen catalogus
die de beheerder inricht). De norm-lat zou daarmee het **eerste echte governance-instellingenscherm van
de organisatie** zijn — een broer van Checklistvragen, niet van de platform-catalogi.

---

## Blok 2 — Welke feiten staan werkelijk in de norm

**De volledige normeerbare set (één bron).** De 10 harde feiten leven als code-constante `HARDE_FEITEN`
in `component_norm_service.py:41` — één plek, geen tweede lijst:

| Sleutel | Bron van "vastgesteld?" | Default verplicht? |
|---|---|---|
| `eigenaar` | signaal `component_zonder_eigenaar` (eigenaar-organisatie leeg) | **ja** |
| `verantwoordelijke` | signaal `component_zonder_verantwoordelijke` (geen roltoewijzing) | **ja** |
| `biv` | signaal `biv_classificatie_onvolledig` (≥1 BIV-veld leeg) | **ja** |
| `gebruikersgroep` | signaal `component_zonder_gebruikersgroep` (geen serving-relatie) | nee |
| `bedrijfsfunctie` | signaal `component_zonder_bedrijfsfunctie` | nee |
| `levensfase` | eigen veld `component.levensfase IS NULL` | nee |
| `bedoeling` | eigen veld `component.migratiepad IS NULL` | nee |
| `hosting` | eigen veld `component.hostingmodel` — sentinel `onbekend` telt als leeg | nee |
| `koppelingen` | echte flow-registratie **of** "bewust geen"-bevinding | **ja** |
| `contract` | echte contract-associatie **of** "bewust geen"-bevinding | **ja** |

**Platform-default.** `DEFAULT_VERPLICHT` (`component_norm_service.py:50`) = **eigenaar ·
verantwoordelijke · biv · contract · koppelingen** op verplicht; de overige vijf op niet-verplicht.
Generiek voor elke tenant (likara-ux W4: de default versmalt niet mee met één tenant-wens).
`componentrol` valt bewust buiten de set (NOT NULL met vaste beginstand → nooit leeg → een norm erop
is zinloos, ADR-052 subknoop 3).

**Het taalgat is al gedicht.** Elk van de 10 feiten heeft al een leesbaar label in `NORM_FEIT_LABEL`
(`labels.js:326`): Eigenaar-organisatie · Verantwoordelijke · BIV-classificatie · Gebruikersgroep ·
Bedrijfsfunctie · Levensfase · Bedoeling (migratiepad) · Hostingmodel · Koppelingen · Contract. Deze
labels leven vandaag alléén in de klaarverklaring/badge-context (`MigratiegereedheidSectie`); het
beheerscherm kan ze **rechtstreeks hergebruiken**. Er is dus **geen open taalgat** — het gat dat de
opdracht vermoedde is bij slice 3 al gevuld.

**"Bewust geen" — voor wie wel, voor wie niet.** Drie feiten kennen een uitspreekbaar "bewust geen":
- **koppelingen** en **contract** — via de `component_bevinding`-tabel (`ComponentBevindingSoort`,
  ADR-052 slice 2);
- **bedrijfsfunctie** — via `functievervulling.geen_systeem` (ADR-044/049).

De overige zeven feiten (eigenaar, verantwoordelijke, biv, gebruikersgroep, levensfase, bedoeling,
hosting) hebben **geen** "bewust geen": daar betekent "vastgesteld" simpelweg dat er een echte waarde
staat. Dit verschil is scherp voor wat de beheerder redelijkerwijs mag verplichten: een feit met
"bewust geen" kan de consultant altíjd beantwoorden (desnoods met "dit heeft geen contract"). Een feit
zónder "bewust geen" dat de beheerder verplicht stelt, kan voor een component dat het legitiem mist
**nooit** vastgesteld raken — bv. een component dat terecht geen gebruikersgroep heeft, blijft eeuwig
"niet vastgesteld" als de beheerder gebruikersgroep verplicht stelt. Dat is een ontwerpoverweging, geen
bug (zie blok 6).

---

## Blok 3 — Wat er al te lezen en te schrijven valt

**Lees-route voor de norm-DEFINITIE: bestaat niet.** De service-functie `haal_norm`
(`component_norm_service.py:76`) geeft de norm als `{feit: verplicht}`, maar wordt **alleen intern**
gebruikt (door `norm_status`). Er is **geen HTTP-endpoint** dat de norm-definitie teruggeeft. De enige
norm-route is `GET /component-normen/status/{component_id}` (`routes/component_norm.py`) — de
**per-component vastgesteld-status**, niet de norm zelf. RBAC: `COMPONENT_NORM.LEZEN`.

**Schrijf-route voor de norm: bestaat niet.** Bevestigd — `routes/component_norm.py` bevat uitsluitend
de status-GET. Geen `PUT`/`PATCH`/`POST`, geen schrijf-functie in de service. Alles eronder is echter
al klaar: de RBAC-matrix staat de beheerder `WIJZIGEN` toe, en de DB-grants op `component_norm` geven
`lk_app` volledige `SELECT/INSERT/UPDATE/DELETE` (`0071_adr052_component_norm.py:45`). Slice 4 hoeft dus
alleen de schrijf-service + route + scherm toe te voegen; schema en rechten dragen hem al.

**Hoe komt de norm in de database.** Via `seed_component_norm(session, tenant_id)` (`seed.py:179`):
10 rijen, de vijf `DEFAULT_VERPLICHT`-feiten op `verplicht=true`, idempotent
(`ON CONFLICT (tenant_id, feit_sleutel) DO NOTHING` — een door de tenant aangepaste rij blijft ongemoeid).
De tabel: tenant-scoped, `ENABLE`+`FORCE ROW LEVEL SECURITY`, `tenant_isolation`-policy,
`UNIQUE(tenant_id, feit_sleutel)`, kolommen `feit_sleutel String(60)` + `verplicht Boolean NOT NULL
default false` (migratie `0071`). **Aanroep: alléén in `dev_seed_testdata.py` (`main`, regel 1800) voor
de dev-tenant.** De echte tenant-onboarding `maak_tenant` (`api/v1/platform.py:34`) maakt **enkel de
tenant-registry-rij** — hij seedt **niets** (geen checklist, geen antwoordconfig, geen norm). Een via
het platform aangemaakte tenant krijgt dus geen norm-rijen (en trouwens ook geen checklistvragen).
**Bij een tenant zonder norm-rijen** degradeert de lezing netjes: `haal_norm` geeft alles `False` →
niets verplicht → `norm_status` = leeg → geen enkel badge. Stil inert, geen crash — maar ook stil
onzichtbaar.

**Waar de norm gelezen wordt bij het toetsen — één gedeelde leesbron.** Alles leunt op
`component_norm_service.norm_status`. Twee consumenten:
1. de route `/component-normen/status/{id}` → **`MigratiegereedheidSectie`** (het live badge + het
   norm-blok in de klaarverklaring-dialog);
2. `component_klaarverklaring_service._open_verplichte_feiten` (regel 61) → de **bevroren snapshot**
   `open_feiten` bij `maak_aan`/`wijzig_status`.

Beide uit dezelfde definitie, tegen verschillende peildata (badge = nu; snapshot = moment van akkoord —
ADR-052 besluit 6). **Verder leunt niets op de norm** — bewust: de norm-afwijking leeft **alleen als
badge op het component**, níét in `dashboard_service.klaar_met_afwijking` (ADR-052 B5/LI044, om de twee
afwijkingssoorten niet te vervlakken). Wat dus meebeweegt zodra de beheerder de lat verzet: uitsluitend
het live badge + de klaarverklaring-dialog op de component-/applicatie-detailschermen. De bevroren
snapshots bewegen niet mee.

---

## Blok 4 — Wat de consultant merkt als de lat verschuift

**Feit AAN zetten.** Op elk component herberekent `MigratiegereedheidSectie` bij het laden de
norm-status. Direct van beeld veranderen:
- het **live badge** "Klaar verklaard, maar N verplicht(e) feit(en) nog niet vastgesteld: …" — dit
  verschijnt **alleen op componenten die al klaar verklaard zijn** (`heeftNormAfwijking = isKlaar &&
  normOpen.length > 0`);
- het **norm-blok in de klaarverklaring-dialog** ("Nog niet vastgesteld (tenant-norm)") plus de
  knop-omslag naar **"Toch klaar verklaren" / "Eerst aanvullen"** — dit verschijnt voor **elk**
  component dat je op dat moment klaar verklaart met een open verplicht feit (ADR-052 besluit 5 /
  L1a-uitzondering).

Getallen over de 19 dev-componenten — per default-feit hoeveel er **niet-vastgesteld** zijn (read-only
gemeten, exact de service-definities):

| Feit | Niet-vastgesteld |
|---|---|
| eigenaar | 3 / 19 |
| verantwoordelijke | 7 / 19 |
| biv | **16 / 19** |
| koppelingen | 9 / 19 |
| contract | 6 / 19 |

BIV is veruit het meest ontbrekende feit. Merk op: het aantal componenten waarvan het **live badge**
vandaag zou wijzigen is veel kleiner dan deze aantallen, want alleen klaar-verklaarde componenten
dragen het badge — en dat zijn er vier (zie blok 5), waarvan één met open default-feiten (Archiefbeheer).

**Feit UIT zetten.** Spiegelbeeld: dat feit valt weg uit het badge en het dialog-blok; een component dat
"3 open" was, zakt naar "2 open". BIV uitzetten zou het grootste gat (16/19) in één klap uit beeld halen.

**Wat gebeurt met al gedane klaarverklaringen (vastgesteld in de code, niet uit de ADR).**
- De **bevroren snapshot** (`ComponentKlaarverklaring.open_feiten`) **beweegt niet mee**: `open_feiten`
  wordt uitsluitend gezet bij `maak_aan` en `wijzig_status` en nooit herberekend
  (`component_klaarverklaring_service.py:86,130`). Het verantwoordingsvenster toont dus altijd de stand
  van het besluitmoment.
- Het **live badge beweegt wél mee**: `MigratiegereedheidSectie._laadNorm` haalt bij élk laden verse
  norm-status op (regel 98–107); `snapshotLabels` leest daarentegen de bevroren `open_feiten` (regel 66).
  Precies de "twee peildata" uit ADR-052 besluit 6 — hier bevestigd in de code.

**Kan een verschuivende norm een eerdere verklaring achteraf misleidend laten lijken? Ja — concreet.**
Voegt de beheerder later een feit toe dat verplicht wordt, dan verschijnt op een **al klaar-verklaard**
component een nieuw live badge "klaar verklaard, maar X open". Dat suggereert dat de consultant X
**bewust heeft overruled** — terwijl X op het besluitmoment niet in de norm zat en dus **niet** in de
bevroren snapshot staat. Het badge (live) en de verantwoording (bevroren) spreken elkaar dan zichtbaar
tegen: het badge zegt "X open", het venster noemt X niet. Omgekeerd verdwijnt bij het **verwijderen**
van een feit uit de norm het live badge stil, terwijl het venster het nog als "nog niet vastgesteld bij
het verklaren" toont. De audit blijft dus intact (de bevriezing is eerlijk), maar de **live badge kan
een besluit toeschrijven dat de consultant nooit nam**. Dit is de scherpste ontwerpspanning die het
beheerscherm introduceert — een lat die je kunt verzetten, herbeoordeelt live het verleden.

---

## Blok 5 — De dev-database als demostaat

**Norm nu in dev: nul rijen.** `component_norm` is **leeg** in de draaiende DB (gemeten: 0 rijen).
Er is één tenant met data (BvoWB dev, `11111111-…`, 19 componenten); de platform-registry-tabel `tenant`
is zelf leeg (de dev-tenant staat daar niet in). Gevolg: **geen enkel component toont vandaag een live
norm-badge**, en de klaarverklaring-dialog toont geen norm-blok — want zonder norm-rijen is niets
verplicht.

**Dit is een drift/stale-staat, geen bewuste keuze.** Een volledige `dev_seed_testdata.py`-run zou 10
norm-rijen zetten (`main` regel 1800, vóór het scenario). Dat de tabel leeg is terwijl er wél vier
klaarverklaringen bestaan met correcte snapshots (Archiefbeheer's `open_feiten =
{biv, eigenaar, verantwoordelijke}` — die alleen door de service berekend kan zijn toen de norm-rijen
er wél waren), bewijst dat de norm-rijen ooit bestonden en sindsdien uit de draaiende DB verdwenen zijn.
De draaiende DB loopt dus achter op de huidige seed.

**Als de default-norm actief was (gemeten over de 5 default-feiten):**

| Open default-feiten | Aantal | Componenten |
|---|---|---|
| 0 (norm-compleet) | 3 | DMS, Klantportaal, Zaaksysteem |
| 1 | 6 | BRP, Burgerzaken-suite, Financieel systeem, Gegevensmakelaar, Sociaal domein suite, Zaakafhandelcomponent |
| 2 | 3 | HR-systeem, Omgevingsloket, Vergunningensysteem |
| 3 | 1 | **Archiefbeheer** |
| 4 | 4 | Aangiften, Reisdocumenten, Shared DB-server, Verkiezingen |
| 5 (alle) | 2 | Extern SaaS-platform, Shared fileshare |

**Concrete demonstratiegevallen:**
- **Archiefbeheer** — klaar verklaard mét exact 3 open feiten (biv/eigenaar/verantwoordelijke), en die
  snapshot staat al bevroren. Zodra de norm (opnieuw) geseed is, licht hier het live badge op. Dit is
  precies het LI044-walkthrough-geval ("klaar mét open feiten → badge").
- **DMS / Klantportaal / Zaaksysteem** — klaar verklaard én norm-compleet (0 open) → geen badge. Het
  "norm-compleet, dus rustig"-geval.
- **Shared fileshare / Extern SaaS-platform** — alle 5 default-feiten open (sterk "hier moet nog veel"-
  geval); niet klaar-verklaard, dus geen badge, wél het volledige norm-blok zodra iemand ze klaar
  probeert te verklaren.

**Kan een browsercheck vandaag iets tonen? Nee — niet zoals de DB nu staat.** Met 0 norm-rijen toont
geen enkel component een norm-badge en toont de dialog geen norm-blok. De demostaat is **niet te vlak**
— hij is alleen **niet aangezet**. Een reseed (`dev_seed_testdata.py`), of straks het beheerscherm zelf
dat de rijen schrijft, zet de 10 rijen en dan lichten Archiefbeheer's badge en de dialog-blokken op.

---

## Blok 6 — Verrassingen, gaten en risico's

**Verrassingen / stale-staat.**
- De norm-tabel staat op nul in de draaiende dev-DB, terwijl de klaarverklaring-snapshots bewijzen dat
  hij ooit gevuld was. Vóór een browsercheck van slice 4 zinvol is, moet de dev-DB gereseed (of de norm
  anderszins gezet) worden. Ik heb dit **niet** gerepareerd (read-only).
- De platform-onboarding `maak_tenant` seedt **helemaal niets** — noch de norm, noch de checklistvragen,
  noch de antwoordconfig. De volledige tenant-baseline hangt vandaag uitsluitend aan
  `dev_seed_testdata.py` (dev-only). Een echt via het platform aangemaakte tenant zou dus zonder norm
  én zonder checklist starten. Dit is breder dan de norm, maar het raakt slice 4 direct: als de norm
  een default hoort te hebben "voor elke verse tenant", dan bestaat het pad "verse tenant" in productie
  nog niet.

**Waar bestaande werking op een niet-afgedwongen aanname leunt.**
- Het live badge veronderstelt dat de norm bij het klaar verklaren **niet meer verschuift**. Zodra de
  beheerder de lat kan verzetten (slice 4), is die aanname onwaar en kan het badge een besluit
  toeschrijven dat de consultant nooit nam (blok 4). Dit is nergens afgevangen — de code kent geen
  begrip "de norm zoals hij was bij dit besluit" naast de bevroren feiten-snapshot.
- Zeven van de tien feiten hebben geen "bewust geen". Verplicht stellen daarvan maakt een component dat
  het feit legitiem mist onherstelbaar "niet vastgesteld". De code dwingt niets af hierover; het is puur
  een gevolg van welke toggle de beheerder aanzet.

**Open vragen die vóór de bouw beslist moeten worden (nu stilzwijgend in de code).**
1. **Waar woont het scherm?** De data en het recht wijzen naar de tenant-schil (`AppLayout`, beheerder),
   als broer van Checklistvragen — niet naar de platform-`/beheer`-schil. Is dat de bedoelde plek, en
   krijgt het een eigen nav-item of valt het onder een nog te bouwen "Instellingen"-ingang
   (`TENANT_INSTELLINGEN` bestaat als recht maar zonder scherm)?
2. **Wat is de vorm van de toggle?** De catalogus-beheerschermen voegen rijen toe/deactiveren; de norm
   heeft een **vaste set van 10 feiten met per feit ja/nee**. Is dit een simpele lijst met per rij een
   schakelaar (geen toevoegen/verwijderen), en gebruikt hij `NORM_FEIT_LABEL` + een korte uitleg per
   feit?
3. **Verzetten van de norm herbeoordeelt het verleden — is dat gewenst?** Moet het live badge op een
   reeds klaar-verklaard component meebewegen met een latere normverschuiving (huidig gedrag), of moet
   het bevriezen op de norm-zoals-hij-was bij het besluit? Dit raakt de kern van "twee peildata".
4. **Geldt de default alleen bij een verse tenant, of moet een bestaande tenant zonder norm-rijen
   alsnog de default krijgen?** Nu degradeert "geen rijen" naar "niets verplicht" — een bewust andere
   uitkomst dan de default-vijf.
5. **Mogen feiten zónder "bewust geen" überhaupt verplicht gesteld worden**, of waarschuwt het scherm
   bij het aanzetten daarvan dat sommige componenten het feit nooit kunnen vaststellen?

**Wat ik zou willen opruimen maar niet mocht (read-only):**
- De norm-rijen in de dev-DB herstellen (reseed) zodat een browsercheck iets toont.
- De onbedoelde asymmetrie "dev_seed seedt de norm, onboarding niet" — óf een gedeelde
  baseline-seed-stap voor beide paden. Genoteerd, niet aangeraakt.

---

## Afsluiting

**Read-only — niets gewijzigd, niets gebouwd, niets gecommit.**

- `git status`: alleen dit nieuwe document (`docs/Checkpoint-norm-beheerscherm-V045.md`) is nieuw; de
  rest van de werktree is schoon.
- Alembic-head en de test-suites zijn **onaangeroerd** — er is geen migratie gedraaid, geen reseed, geen
  schrijfquery uitgevoerd (uitsluitend `SELECT`-metingen als `lk_admin`, plus code-lezen). De laatst
  bekende stand (V045: backend 1149 passed / 2 skipped · frontend 1175 passed · 1 alembic head) is niet
  aangetast.
