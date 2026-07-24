# Checkpoint — vraagevolutie, bouwkant (V051)

| | |
|---|---|
| **Soort** | Read-only meting — niets gebouwd, niets gewijzigd, niet gecommit |
| **Datum** | 2026-07-24 |
| **Gemeten tegen** | branch `master`, HEAD `4dd7eea` (V051), werktree schoon |
| **Tenant-meting** | dev-tenant `11111111-1111-1111-1111-111111111111`, als `lk_app` met tenant-context (`set_config`, transactie-lokaal), read-only |
| **Kader** | ADR-056 + de acht LI051-besluiten van Bert (die het ADR aanscherpen; o.a. géén "klopt nog"-knop — opnieuw antwoorden ís de bevestiging) |

---

## Stap 0 — stand

`master` @ `4dd7eea` ("[docs] LI050 afsluiting — V051"), `git status` leeg. Alle vindplaatsen
hieronder verwijzen naar deze commit.

---

## M1 — Het antwoord: wat ligt er vast, en hoe komt het tot stand?

### Wat een antwoord draagt (`Checklistscore`, models.py:1084-1126)

| Gegeven | Kolom | Aanwezig |
|---|---|---|
| Afhandeling (oordeel) | `score` (enum ja/nee/deels/nvt, **nullable** in DB; Create dwingt non-null af) | ja — models.py:1118 |
| Keuze/getal | `antwoord_waarde` (jsonb, envelope `{optie}`/`{opties}`/`{getal}`) | ja — models.py:1126 |
| Toelichting | `bevinding` (Text) + `actie` (Text) | ja — models.py:1119, 1122 |
| Verantwoordelijke | `verantwoordelijke_id` (FK partij) | ja — models.py:1121 |
| Wanneer | `created_at`/`updated_at` (TimestampMixin) | ja |
| **Wie antwoordde** | — géén kolom; alleen `actor_sub` in de audit-trail | **0** kolommen |
| **Bevroren formulering** | — bestaat niet; alleen `checklistvraag_id`-verwijzing | **0** kolommen — models.py:1117 |

### Paden waarlangs het antwoord ontstaat en wijzigt

| Handeling | Route | Recht | UI |
|---|---|---|---|
| Eerste antwoord | `POST /checklistscores` (routes/checklistscore.py:93-100) | `CHECKLISTSCORE.AANMAKEN` (medewerker/beheerder, `_INHOUD` — rbac.py:150) | scoreknop, `ChecklistscoreSectie.vue:263` |
| Oordeel wijzigen | `PATCH /checklistscores/{id}` met `{score}` (routes:103-110) | `CHECKLISTSCORE.WIJZIGEN` | scoreknop, sectie:259, 274 |
| Velden wijzigen | zelfde PATCH met `{bevinding, actie, verantwoordelijke_id[, antwoord_waarde]}` — **bewust zonder score** | idem | uitklaprij "Opslaan", sectie:320-343 |
| Verwijderen | `DELETE /checklistscores/{id}` (routes:113-122; registratie-feit → guard `WIJZIGEN`, rbac.py:267) | `WIJZIGEN` | **niet in de UI** (0 aanroepen van `api.checklistscores.verwijder` in de sectie) |

Aanmaken en wijzigen zijn dus **hetzelfde PATCH-pad in twee gedaanten**: het scherm splitst
het in een score-PATCH en een velden-PATCH (beide `checklistscore_service.werk_bij`, :391-414).

### Wat telt als "het antwoord aanraken" (besluit 7 — inventaris, geen keuze)

Handelingen die vandaag op een gegeven antwoord bestaan: (1) score-PATCH, (2) velden-PATCH,
(3) DELETE (API-only). Alle drie onder `CHECKLISTSCORE.WIJZIGEN` — precies het recht dat
besluit 7 als dover aanwijst. Er is géén aparte "lees"-handeling die als aanraken gelezen zou
kunnen worden. NB: de bewerk-uitklaprij opent vandaag **voorgevuld** met de huidige waarden
(sectie:300-313) — kader-besluit 3 (alles leeg behalve toelichting) wijkt daarvan af.

### Wie mag antwoorden

`Entiteit.CHECKLISTSCORE` volgt `_INHOUD` (rbac.py:150): viewer/auditor lezen; **medewerker en
beheerder** maken aan en wijzigen. Dat is de kring die per besluit 7 de stille notitie dooft.

---

## M2 — De vraagstelling: wat kan er veranderen, en waar?

| Handeling | Route | Recht | Scherm (ChecklistConfigBeheer.vue) |
|---|---|---|---|
| Vraagtekst wijzigen | `PATCH /checklistconfig/vragen/{id}` — `VraagUpdate.vraag` (schemas/checklistconfig.py:131-147) | `CHECKLISTVRAAG.WIJZIGEN` = **beheerder-only** (rbac.py:220-225) | **NIET aangeboden** — het scherm roept `werkVraagBij` uitsluitend met `{volgorde}` aan (:336, sleep) |
| Prioriteit wijzigen | zelfde route (`VraagUpdate.prioriteit`) | idem | **niet aangeboden** (alleen bij aanmaken) |
| Vraag naar andere categorie | zelfde route (`VraagUpdate.categorie_id`) | idem | **niet aangeboden** |
| Vraag (de)activeren | `POST /vragen/{id}/actief` (routes/checklistconfig.py:166-174) | idem | ja — toggle "Deactiveren/Activeren" (:690), mét `_bevestigImpact` (:213) |
| Antwoordtype zetten | `PATCH /vragen/{id}/antwoordtype` — alleen vanuit `geen` (service:473-488) | idem | ja (:227); beperking als grijze regel :727 + server-409 |
| Optie toevoegen | `POST /vragen/{id}/opties` (routes:177-184) | `CHECKLISTVRAAG.AANMAKEN` (beheerder) | ja (:254) |
| Optie hernoemen (label) | `PATCH /opties/{id}` — `OptieUpdate` = label+volgorde (schemas:217-228) | `WIJZIGEN` | ja (:270) — **ook bij afgeleide sets** (service:558-571 staat label toe) |
| Optie uitzetten | `POST /opties/{id}/deactiveren` (routes:197-203) | `WIJZIGEN` | ja (:281) |
| **Optie heractiveren** | **bestaat niet** | — | **bestaat niet** — het scherm toont "gedeactiveerd" als kale (danger-rode) badge zonder handeling (:768) |
| Nieuwe vraag | `POST /vragen` (routes:122-130) | `AANMAKEN` | ja (:194), mét `_bevestigImpact` |

### De twee expliciete vaststellingen

1. **Bevestigd:** de vraagtekst is via de API wijzigbaar terwijl het scherm het niet aanbiedt.
   `PATCH /vragen/{id}` accepteert `vraag` (schema :138); `werk_vraag_bij` (service:319-335) doet
   `setattr` + commit — **géén fan-out, géén markering, bestaande antwoorden volledig onaangeroerd**.
   De audit legt de wijziging wél vast met oud én nieuw (checklistvraag staat in
   `AUDIT_TENANT_ENTITEITEN`, audit.py:58; per-veld-diff via `bouw_wijziging`).
2. **Bevestigd (ADR-056 besluit 15):** heractiveren van een uitgezette optie bestaat niet.
   Minimaal nodig: (a) schema — `OptieUpdate` kent geen `actief` (schemas:217-228), dus óf een
   veld erbij óf een eigen `POST /opties/{id}/activeren` (spiegel van `/deactiveren`);
   (b) service — een activeer-functie (spiegel van `deactiveer_optie`, :574-584, incl. de
   afgeleide-set-weigering); (c) scherm — een handeling op de "gedeactiveerd"-rij (:768), die er
   nu geen enkele draagt. Geen schema-migratie nodig: de kolom `actief` bestaat (models.py:1078).

**Contrast vraag↔optie:** een vráág is wél symmetrisch aan/uit te zetten (routes:166-174 +
scherm :690); alleen de óptie is eenrichtingsverkeer.

---

## M3 — Waar landt het sein voor de consultant?

- **Het overzicht van wat openstaat** = `component_open_punten_service.open_punten`
  (:143-211) → `OpenPuntenSectie.vue`, tabblad "Open punten" op `ComponentDetail`. Drie
  blokken; het blok voor **niet-blokkerende** signalen is `valt_op` ("Dit valt op",
  service:171-191) — draagt vandaag 2 soorten: `checklist_nee_deels` (gebundeld met aantal) en
  `staat_los` (OpenPuntenSectie.vue:58-61).
- **Zou een "vraagstelling aangepast"-punt die weg kunnen volgen?** Ja, als derde soort in
  `valt_op`: server-side een telling per component (vergt een verouderd-markering op het
  antwoord — bestaat nog niet, zie M1), een `VALT_OP_TEKST`-regel en een route
  `{"soort":"tab","tab":"checklist"}` (het patroon van `checklist_nee_deels`, service:176-179).
- **⚠ Het tabblad-getal:** het getal op het tabblad is **alleen blok 1**:
  `moetNog = openPunten?.moet_nog?.aantal` (ComponentDetail.vue:78) → label
  `Open punten (${moetNog})` (:263). Een punt in `valt_op` telt vandaag **niet** mee in het
  tabblad-getal — alleen in de teller op de schakelaar-stand "Dit valt op (N)"
  (OpenPuntenSectie.vue:47-49). ADR-056 besluit 10 zegt "telt mee in het Open punten-getal op
  het tabblad" — dat botst met de gebouwde knip. **Besluit Bert nodig** (zie bouwvragen).
- **Neutrale melding-vorm:** bestaat en is herbruikbaar als bouwsteen —
  `afwijkingCodering.js:37-53`: soort `verschoven` = neutraal (`--lk-color-text-muted`, icoon ↔,
  klasse `lk-afwijking-verschoven`, zin zonder verwijt-taal, :76-79). ADR-056 besluit 7 wijst
  hier al naar; de bron is generiek genoeg om een derde soort naast `bewust`/`verschoven` te
  dragen of als model te dienen.
- **Waar de consultant zijn antwoorden ziet** = `ChecklistscoreSectie.vue` (checklist-tab,
  per-vraag-rij met uitklap). De melding bij het antwoord zelf zou in die rij/uitklaprij
  landen; per-rij inline feedback (`veldStatus`) bestaat daar al als vorm.

---

## M4 — De geschiedenis als bron van de oude formulering

- **Ingang op componentdetail:** ja — `ObjectHistoriePaneel` ('i'-knop) →
  `GET /objecthistorie/component/{id}`; toegang volgt het object (`COMPONENT.LEZEN`, dus ook de
  medewerker).
- **Wordt een vraagtekst-wijziging vastgelegd met oud én nieuw?** Ja — `checklistvraag` staat in
  de audit-allowlist (audit.py:58); de diff draagt per veld `{oud, nieuw}`. Leesbaar: de
  regel-naam komt uit `NAAMBRON["checklistvraag"] = ("veld","vraag")` (auditlog_service.py:140)
  — de vraag heet naar zijn **tekst**, niet zijn code; lange waarden stapelen
  (`diffWeergave`, labels.js). Twee schoonheidsfoutjes: het veldlabel `vraag` staat niet in
  `VELD_LABELS` (labels.js:128-155) en het entiteit-type niet in `AUDIT_ENTITEIT`
  (labels.js:57-79) — beide vallen op humanize-terugval ("Vraag"/"Checklistvraag"), leesbaar
  maar ongecureerd.
- **⚠ Kan de consultant er vanaf zijn antwoord bij komen? Nee — dat is een nieuwe route.**
  Twee gaten: (1) de **componentgeschiedenis** toont een vraagwijziging niet — het
  component-filter matcht op entiteit-is-component / `component_id` in de diff / relatie-
  endpoints (auditlog_service.py:343-362), en een `checklistvraag`-regel draagt geen van
  drieën (een vraag is tenant-breed, niet component-gebonden); (2) het **tenant-logboek**
  (AuditTrailView) dat de regel wél toont is beheerder/auditor-only (rbac.py:227-232) — de
  medewerker die het sein krijgt, mag de bron niet in. `checklistvraag` is ook geen
  objecthistorie-type (routes/objecthistorie.py:40-49). Kader-besluit 5 ("opvraagbaar via de
  bestaande geschiedenis") vergt dus een bouwkeuze: wélke geschiedenis, en wie mag erin.

---

## M5 — De beheerderskant

- **Waar landt de keuze verduidelijking/wijziging?** Het beheerscherm heeft vandaag géén
  opslaan op vraagniveau (vraagtekst is niet eens bewerkbaar, M2); ADR-056 besluit 13 voorziet
  één opslaan-venster per vraag — dat venster bestaat nog niet.
- **Vorm "toont vóór opslaan wat het raakt": bestaat** — `_bevestigImpact`
  (ChecklistConfigBeheer.vue:140-152) haalt `GET /checklistconfig/impact?componenttype=…` en
  legt "raakt N componenten" in een bevestiging voor (gebruikt bij vraag toevoegen en
  (de)activeren). **Maar de telling is componenten** (`impact_telling`, service:229-237 —
  `count(Component)` per type), **niet antwoorden**. "Dit raakt N antwoorden" (besluit 12) is
  een nieuwe telling: `count(Checklistscore) WHERE checklistvraag_id = …` — die bestaat nergens.
- **Teller per vraag/categorie:** per categorie bestaan `aantal_vragen` (CategorieRead) en een
  uitstaande-vragen-telling (:88-90); een teller **per vraag** (van wat dan ook, laat staan
  "N verouderde antwoorden") bestaat niet.

---

## M6 — Wat mag hier niet gebeuren

- **Klaar-bepaling:** `bepaal_lifecycle` telt `aantal_gescoord` als **rij-bestaan** van
  antwoorden op actieve vragen (lifecycle_service.py:124-134) tegen `aantal_vragen` (actieve
  vragen van het type, :112-121). Een sein/markering naast het antwoord raakt geen van beide.
  Compleet ⟺ status ∈ {migratieklaar, geblokkeerd} blijft intact.
- **Waar het per ongeluk tóch zou kunnen doorwerken** (de drie plekken die de bouw moet mijden):
  1. **Blok "dit moet nog" → snapshot**: `open_feiten` bij klaarverklaring =
     `_open_verplichte_feiten` (component_klaarverklaring_service.py:86) — uitsluitend
     norm-feiten. Landt het sein in `valt_op`, dan bereikt het de snapshot structureel nooit.
  2. **Score legen**: verboden (invariant). Meetdetail: omdat de telling rij-bestaan telt, zou
     legen de "beantwoord"-telling niet eens wijzigen — maar het vervalst de bron van de
     beoordelingsstatus en de blokkade-synchronisatie leest `score` (:215-266). Blijft verboden.
  3. **Vraag-deactiveren als omweg**: `zet_actief` heeft wél fan-out (herbereken_type,
     service:456-468) — "verouderd" uitdrukken via de actief-vlag zou de engine raken. Niet doen.
- **Besluit 4 (oude antwoord telt mee) → telling:** er verandert **niets**. De rij blijft
  bestaan; `aantal_gescoord` en de blokkade-stand zijn ongevoelig voor een markering ernaast.

---

## M7 — Omvang (dev-tenant, als lk_app, 2026-07-24)

| Meting | Getal |
|---|---|
| Antwoorden (checklistscore-rijen) | **267** |
| — met écht gevulde `antwoord_waarde` | **0** |
| — waarvan op een keuzelijst-vraag (allemaal zonder ingevulde keuze) | **91** |
| — op een inactieve vraag | **0** |
| — met lege score | **0** |
| Componenten met antwoorden | **5** |
| Vragen totaal | **98** |
| — met keuzelijst (enkelvoudig/meerkeuze) | **27** |
| — getal / geen | **2** / **69** |
| — inactief | **0** |
| Opties totaal | **96** |
| — inactief | **0** |
| — afgeleid (read-only set) | **10** |

**Meetvoetnoot:** alle 267 lege antwoord-waarden staan als **JSON-`null`** in de jsonb-kolom,
niet als SQL-NULL (`WHERE antwoord_waarde IS NOT NULL` geeft misleidend 267; `= 'null'::jsonb`
geeft 267, echt gevuld = 0). Functioneel identiek voor de app (ORM leest JSON-null als `None`),
maar elke toekomstige SQL-meting of -migratie op deze kolom moet op `'null'::jsonb` toetsen.
ADR-056 subknoop 4 ("alle 267 zonder antwoord_waarde") klopt dus inhoudelijk.

**Optie-moment:** `ChecklistVraagOptie` draagt geen `created_at` (models.py:1050-1081, geen
TimestampMixin) — ADR-056 besluit 5 ("het moment is de minimale drager") staat nog open.

### De "gevolgen"-teksten van ADR-056

De opdracht zegt drie; **het ADR somt er vier op** (kop zegt "drie", lijst telt 4 — zelf al een
kleine correctie waard). Alle vier bestaan nog:

| # | Tekst | Vindplaats | Aanwezig |
|---|---|---|---|
| 1 | VraagUpdate-docstring "Geen fan-out nodig" | schemas/checklistconfig.py:131-134 | 1× |
| 2 | Optie-docstring "bewerken = soft-deactiveren via `actief`" | models.py:1051-1053 | 1× |
| 3 | ADR-022 "De herkomst toont de vraagtekst" | ADR-022:255 | 1× |
| 4 | Grijze uitlegregel antwoordtype | ChecklistConfigBeheer.vue:727 | 1× |

---

## Niet kunnen vaststellen

- **Hoe de audit-diff van een vraagtekst-wijziging er live uitziet** (de leesbaarheid is uit de
  code afgeleid — NAAMBRON/diffWeergave — maar er is in de dev-tenant nog nooit een vraagtekst
  gewijzigd, dus er bestaat geen echte logregel om te tonen). Geen blokkade; bij de bouw hoort
  een browsercheck met een echte wijziging.
- **Het gedrag van `TimestampMixin.updated_at` bij een setattr zonder feitelijke wijziging** —
  niet relevant genoeg om voor dit checkpoint live te meten; genoteerd omdat "aanraken" (besluit
  7) er mogelijk op wil leunen.

## Waar de code iets anders zegt dan ADR-056 of een skill

1. **ADR-056 besluit 8** ("klopt nog"-knop) is door LI051-kaderbesluit 3 **vervangen**
   (opnieuw antwoorden ís de bevestiging) — het ADR moet daarop bijgewerkt worden, incl.
   besluit 12-vangrail ("beheerder kan niet aftekenen" blijft; de wegwerk-handeling wijzigt).
2. **ADR-056 besluit 10 vs. de gebouwde teller-knip:** het tabblad-getal telt alleen
   "Dit moet nog" (ComponentDetail.vue:78, 263); blok-3-punten tellen alleen in hun eigen
   schakelaar-stand. "Verouderd telt mee in het getal op het tabblad" kan dus niet zonder óf de
   tabblad-telling te verbreden óf het besluit te herformuleren. Melden, niet gekozen.
3. **ADR-056 besluit 9 / kader-besluit 5** ("de bestaande geschiedenis"): de bestaande
   componentgeschiedenis toont vraagwijzigingen niet en het tenant-logboek is voor de
   consultant gesloten (M4) — "de bestaande geschiedenis" bestaat voor dít doel nog niet.
4. **ADR-056 "Gevolgen"-kop zegt drie, somt vier** — de vier zijn alle vier geverifieerd aanwezig.
5. Kleiner: de optie-badge "gedeactiveerd" is **danger-rood** (ChecklistConfigBeheer.vue:768)
   terwijl er niets kapot is (LI040-lijn: neutrale taal/toon bij afgeleide uitkomsten) — gaat
   vanzelf mee met besluit 15 (de rij krijgt een handeling en een neutrale staat).
6. Kleiner: `AUDIT_ENTITEIT` en `VELD_LABELS` kennen `checklistvraag`(-optie/-categorie) resp.
   `vraag` niet — humanize-terugval, geen fout, wel ongecureerd op het moment dat de
   geschiedenis leeslaag voor consultants wordt.

## Bouwvragen (vanuit wat de consultant of de beheerder merkt)

1. **Het getal op het tabblad:** hoort "de vraagstelling is aangepast" mee te tellen in het
   getal dat de consultant op "Open punten" ziet, of alleen in de stand "Dit valt op"? De
   gebouwde knip telt vandaag alleen "Dit moet nog" op het tabblad — besluit nodig (zie
   discrepantie 2).
2. **Opnieuw antwoorden met behoud van toelichting:** de bewerk-rij opent vandaag voorgevuld
   met álle huidige waarden. Kader-besluit 3 wil afhandeling én keuze leeg, toelichting
   behouden — geldt dat lege openen alléén voor een verouderd antwoord, of verandert de
   bewerk-rij overal?
3. **De weg naar de oude formulering:** waar klikt de consultant heen vanaf zijn antwoord —
   krijgt de componentgeschiedenis de vraagwijzigingen erbij, of komt er een eigen ingang —
   en wie mag die geschiedenis zien (vandaag: niemand onder beheerder/auditor)?
4. **Wat dooft de stille notitie precies:** telt élke bewerking (ook alleen een toelichting
   bijwerken of een verantwoordelijke kiezen) als "het antwoord aanraken", of alleen een
   handeling die het oordeel/de keuze raakt? Beide lopen vandaag door hetzelfde wijzig-recht.
5. **Keuzevraag zonder gemaakte keuze (91 van de 267):** verschijnt het sein bij een
   optie-uitbreiding bij álle antwoorden op die vraag — ook waar nooit een keuze is ingevuld
   (kader-besluit 2 zegt: juist die) — en geldt dat dan voor alle 27 keuzelijst-vragen met
   terugwerkende kracht vanaf het nulpunt?
6. **Het éne opslaan-venster van de beheerder:** het scherm kent vandaag geen bewerking van de
   vraagtekst en geen verzamelmoment (elke optie-handeling slaat direct op). Hoe komt de
   beheerder van "losse directe handelingen" naar "één opslaan per vraag met één keuze en de
   voorspelling 'raakt N antwoorden'" — en die voorspelling vergt een nieuwe telling
   (antwoorden per vraag; de bestaande impact-telling telt componenten)?
7. **Weer-aanzetten van een antwoordmogelijkheid:** de beheerder ziet "gedeactiveerd" zonder
   handeling; welke plek krijgt de aanzet-handeling en loopt die door dezelfde
   verduidelijking/wijziging-keuze als de rest (kader-besluit 1: één sein per vraag)?
8. **Het nulpunt:** bevriezen op de huidige formulering bij invoering (ADR-056 subknoop 1) —
   volstaat dat als enige vulling, en is het invoeringsmoment dan het moment waarop de teller
   voor iedereen op nul staat (kader-besluit 6)?
