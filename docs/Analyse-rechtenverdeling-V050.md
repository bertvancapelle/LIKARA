# Analyse rechtenverdeling × reikwijdte — V050 (read-only)

**Opdracht:** `START: analyse-rechtenverdeling-reikwijdte-V050` · **Datum:** 2026-07-23
**Aard:** read-only meting; niets gewijzigd, niets gecommit. Reikwijdte-schaal: R0 kijken ·
R1 eigen registratie · R2 organisatiebreed · R3 platformbreed.

---

## 1. Stand

Branch `master` · HEAD `2dc5592` ("[docs] LI050 checkpoint productie-gereedheid …") · werktree
schoon vóór dit rapport. Tellingen op tenant-data komen uit het checkpoint van vandaag
(`docs/Checkpoint-productie-gereedheid-V050.md`, zelfde datastand: tenant `11111111-…`,
24 componenten waarvan 20 applicatie).

---

## 2. M1 — De rechtenwerelden zoals ze nu bestaan

**Twee werelden, hard gescheiden (ADR-012):**

| Wereld | Rollen | Matrix | Guard | Sessie/DB-rol |
|---|---|---|---|---|
| Tenant | viewer · medewerker · beheerder · auditor (4) | `backend/app/core/rbac.py` `PERMISSIES` — **31 entiteiten** | `vereist_permissie` | `get_tenant_session` (lk_app, RLS) |
| Platform | platformbeheerder · platformoperator (2) | `backend/app/core/platform_rbac.py` `PLATFORM_PERMISSIES` — **12 entiteiten** | `vereist_platform_permissie` | `get_platform_session` (lk_platform) |

**Scheiding:** een account is óf tenant óf platform — tenant-users dragen een `tenant_id`-claim,
platform-users niet (realm-inrichting; `likara-security` §Tweelaags rollenmodel). Kruisverkeer
faalt beide kanten op 403: platform-account op tenant-endpoint mist `tenant_id` (403
`TENANT_MISMATCH`); tenant-account op platform-endpoint levert geen platform-rollen
(`extract_platform_rollen` negeert tenant-rollen, `platform_rbac.py:132-135`). Geen overerving
tussen rollen (`rbac.py:7`); fail-secure bij onbekende rol/entiteit (`rbac.py:335-343`).

**Vier patronen in de tenant-matrix** (rbac.py):

| Patroon | Mapping | Gebruikt door (telling) |
|---|---|---|
| `_INHOUD` (r106-111) | Viewer L · Medewerker LAW · Beheerder LAWV · Auditor L | **23** entiteiten |
| `_ALLEEN_LEZEN` (r115-120) | alle rollen L | 1 (ARCHITECTUUR) |
| `_EIGEN_BEHEER` (r126-131) | Viewer/Auditor L · Medewerker/Beheerder LAWV + maker-guard in service | 1 (IMPACT_VIEW) |
| `_EIGEN_VOORKEUR` (r139-144) | álle rollen LAWV + sub-guard in service | 1 (GEBRUIKER_VOORKEUR) |
| maatwerk beheerder-only-mutatie | Viewer/Medewerker/Auditor L · Beheerder LAWV | 2 (REFERENTIEMODEL r184-189, COMPONENT_NORM r199-204) |
| maatwerk smal | AUDITLOG (beheerder+auditor L, r220-225) · GEBRUIKERSBEHEER + TENANT_INSTELLINGEN (beheerder-only, r227-238) | 3 |

**Bestaande uitzonderingen mét reden (gedocumenteerd in de matrix zelf):**
- `REFERENTIEMODEL` week af van `_INHOUD` en werd **versmald naar beheerder-only** met precies de
  reikwijdte-redenering van deze analyse: *"een medewerker mocht aanmaken — dat was te ruim voor een
  import die het hele functie-landschap herschrijft"* (rbac.py:179-183). **Dit is het interne
  precedent voor R2-handelingen.**
- `COMPONENT_NORM`: *"iedereen leest, alleen de beheerder stelt 'm in"* (rbac.py:195-198).
- `GEBRUIKER_VOORKEUR`: alle rollen schrijven — bewust, strikt persoonlijk (rbac.py:133-138);
  eigen-scope in de service (`voorkeur_service.py:33-34`, sub nooit client-aanleverbaar).
- `IMPACT_VIEW`: maker-ownership in de service (`impact_view_service.py:81,107`).
- **ADR-050**: het verwijder-pad volgt het onderwerp — registratie-feit ⇒ WIJZIGEN (7 entiteiten,
  `REGISTRATIE_FEIT_ENTITEITEN` r255-264), landschapsobject ⇒ VERWIJDEREN (11 entiteiten, r266-278),
  geërfd via `verwijder_actie()` (r285-289) + borgingstest `test_rollengrens_adr050`. **Deze analyse
  gebruikt die bestaande indeling; er is geen tweede classificatie nodig** — de reikwijdte-vraag komt
  er als derde as (R2/R3) bovenop, niet ernaast.

---

## 3. M2 — Elke handeling op reikwijdte

Bewijs-conventie: "matrix" = rbac.py-regel; tellingen uit het V050-checkpoint of de genoemde service.

### R0 — kijken (raakt niets)

| Handeling | Waar in de UI | Bewijs | Rol nu | Klopt? |
|---|---|---|---|---|
| Landschap, lijsten, kaart, architectuur, signalering bekijken | alle lees-schermen | alle 31 entiteiten geven elke rol L behalve AUDITLOG/GEBRUIKERSBEHEER/TENANT_INSTELLINGEN (matrix) | alle 4 tenant-rollen | ja |
| Auditlog inzien | Auditlog-scherm | AUDITLOG: beheerder+auditor L, viewer/medewerker géén (rbac.py:220-225) | beheerder · auditor | ja — R0 maar privacy-gevoelig, bewust smal |
| Platform-metadata lezen | platform-shell | operator overal L (platform_rbac.py, 10 config-matrices) | platformoperator | ja |

### R1 — eigen registratie (raakt 1 object of 1 feit)

| Handeling | Waar in de UI | Bewijs reikwijdte | Rol nu | Klopt? |
|---|---|---|---|---|
| Landschapsobject vastleggen/wijzigen (component, contract, partij, datatype, gebruikersgroep, bedrijfsfunctie, proces, plateau, work_package, deliverable, gap — **11**) | detail-/lijstschermen | 1 object per handeling; `_INHOUD` (matrix r147-178) | medewerker (LAW) | ja |
| Landschapsobject **verwijderen** | detailkop, destructieve zone | 1 object, maar cascade sleept andermans registraties mee → ADR-050: VERWIJDEREN (r266-278) | beheerder | ja — bewust zwaarder (ADR-050) |
| Registratie-feit vastleggen/corrigeren/terugnemen (koppeling/relatie, checklistantwoord, gebruik, contract-koppeling, vervullingen, bevinding — **7**) | secties op de detailschermen | 1 feit; terugnemen guardt op WIJZIGEN (`verwijder_actie`, geverifieerd `routes/functievervulling.py:99-104`) | medewerker | ja |
| Roltoewijzing leggen/terugnemen | PartijRollenSectie | 1 feit; guardt op PARTIJ.WIJZIGEN (`routes/roltoewijzing.py:63`) | medewerker | ja |
| Blokkade-status bijwerken | BlokkadeSectie | 1 blokkade; handmatig alleen open↔in_behandeling (`blokkade_service.py:414-418`) | medewerker | ja |
| Klaarverklaren / heropenen | ComponentDetail-kop | 1 component; A resp. W (`routes/component_klaarverklaring.py:43,62`); de zwaarte-drempel zit in de afwijking-bevestiging (ADR-052 besluit 5), niet in de rol | medewerker | ja |
| Eigen view opslaan/delen/verwijderen | Landschapskaart | eigen record; `_EIGEN_BEHEER` + maker-guard (`impact_view_service.py:81`) | elke maker (medewerker+) | ja |
| Eigen voorkeur zetten/wissen | "★ sla op als mijn standaard" | eigen record; `_EIGEN_VOORKEUR` + sub-guard (`voorkeur_service.py:33`) | álle rollen | ja — bewuste afwijking |

### R2 — organisatiebreed (één klik raakt het werk van de hele gemeente)

| Handeling | Waar in de UI | Bewijs reikwijdte | Rol nu | Klopt? |
|---|---|---|---|---|
| **Checklistvraag aanmaken** | Checklistvragen-scherm | elke component van het type krijgt er een open vraag bij; lifecycle-fanout (`test_vraagbeheer_w1_fanout.py`: migratieklaar → in_inventarisatie); type applicatie = **20** componenten | **medewerker** (CHECKLISTVRAAG A, `routes/checklistconfig.py:74-84`) | **nee — te licht (besluit Bert)** |
| **Checklistvraag wijzigen** (tekst/betekenis/antwoordtype/opties) | idem | wijzigt wat élke collega ziet en welke antwoorden geldig zijn; opties zijn tenant-breed | **medewerker** (W, `routes/checklistconfig.py:85-160`) | **nee — te licht (zelfde cluster)** |
| **Checklistvraag deactiveren** | idem, knop "Deactiveren" | raakt **20** componenten (type applicatie); **5** gegeven antwoorden onzichtbaar; engine telt scheef; onafsluitbaar "Dit valt op"-punt + blokkade (checkpoint §2A) | **medewerker** (W, `routes/checklistconfig.py:118-127`) | **nee — te licht (scherpste geval)** |
| Organisatienorm verzetten (feit verplicht/vrij) | Migratienorm-scherm | raakt alle componenten die er niet aan voldoen (`impact_voor_feit` voorspelt het aantal: "raakt 12 systemen…", `NormBeheer.vue`) | beheerder (COMPONENT_NORM W, `routes/component_norm.py:86-95`; matrix r199-204) | ja |
| Referentiemodel inlezen/hervatten | Bedrijfsfuncties → inlezen | herschrijft de functie-as: GEMMA = **297** functies + **302** plaatsingen (likara-backend §LI039) | beheerder (REFERENTIEMODEL A, `routes/referentiemodel.py:44,55`; matrix r184-189) | ja — het gecorrigeerde precedent |
| Gebruiker aanmaken / rol wijzigen / in-uitschakelen | Gebruikersbeheer | bepaalt wat élke collega kan; 6 routes | beheerder (GEBRUIKERSBEHEER, matrix r227-232) | ja |

### R3 — platformbreed (geldt voor alle gemeenten)

| Handeling | Waar in de UI | Bewijs reikwijdte | Rol nu | Klopt? |
|---|---|---|---|---|
| Catalogi beheren: componenttypen+typering, contractconfig, relatiekenmerken (incl. **beheerrollen**), partijsoorten, vraagbetekenis, componentrol, BIV-schaal, applicatiefuncties (**8**) | platform-shell ConfigBeheer-schermen | catalogus-tabellen zonder RLS — één wijziging geldt voor élke tenant (likara-domeinmodel §5) | platformbeheerder (LAW, geen V — soft-deactivate; operator L) | ja |
| Referentiemodel-aanbod cureren | ReferentiemodelConfigBeheer | platform-gecureerd aanbod voor alle tenants | platformbeheerder | ja |
| Tenant aanmaken/beheren | platform-shell | maakt een gemeente-omgeving | platformbeheerder (TENANT, `backend/app/api/v1/platform.py:23-36`) | ja |
| *(geen handeling mogelijk)* protocol/richting/impact, hostingmodel, levensfase, e.a. **±14 code-enums** wijzigen | nergens — code-vast | wijziging = codewijziging + deploy, geldt voor alle tenants (checkpoint §2D) | niemand (deploy) | functionele vraag P50-4 — besluit Bert |

**Dode matrix-entries (recht bestaat, handeling niet):** tenant `TENANT_INSTELLINGEN` (0 routes) en
platform `CHECKLISTCONFIG`, `PLATFORMINSTELLINGEN`, `PLATFORMMETADATA` (0 routes — geverifieerd:
alleen de 10 hierboven genoemde platform-entiteiten dragen guards; checklistconfig verhuisde met
ADR-022 W1 naar de tenant-kant, de platform-entry bleef achter).

---

## 4. M3 — De mismatches (gesorteerd op gebruikersimpact)

1. **Te licht bewaakt — het checklistvraag-cluster (aanmaken · wijzigen · antwoordtype · opties ·
   deactiveren).** Bevestigd en verbreed t.o.v. het checkpoint: niet alleen *deactiveren* maar de
   héle vraagbeheer-groep is R2 onder medewerker-recht (`_INHOUD` W/A). Wat de gebruiker merkt: een
   collega-consultant kan met twee klikken de vragenlijst van de hele gemeente veranderen — open
   punten verschijnen op 20 componenten, of antwoorden verdwijnen uit beeld met een scheve status
   als gevolg. **De codebase zelf bevat het precedent voor de fix**: REFERENTIEMODEL werd om deze
   exacte reden van `_INHOUD` naar beheerder-only versmald (rbac.py:179-183), en COMPONENT_NORM is
   vanaf de bouw zo gedaan. Of CHECKLISTVRAAG dat ook moet: **besluit Bert** (rechtenmatrix is
   "door Bert vastgesteld", rbac.py:3). De voordeur versterkt dit geval: het is óók het enige
   scherm zonder énige knop-gating (M4) — zelfs een viewer ziet de Deactiveren-knop.
2. **Dode rechten-entries (4).** TENANT_INSTELLINGEN + platform CHECKLISTCONFIG/
   PLATFORMINSTELLINGEN/PLATFORMMETADATA staan in een matrix zonder één route. De gebruiker merkt
   er niets van; de volgende bouwer wél — een matrix die rechten belooft die nergens gelden is een
   tweede waarheid in wording. (Opruimen of bouwen: besluit Bert; geen productieblokker.)
3. **Te zwaar bewaakt: 0 gevallen gevonden.** De kandidaat (functievervulling-verwijderen zou
   beheerder-only zijn) bleek een stale comment — de code guardt op WIJZIGEN = medewerker
   (zie §7 Tegenspraken). Dagelijks R1-werk kan overal door de medewerker.
4. **Verkeerde wereld: 0 harde gevallen.** De vragenset is bewust tenant (ADR-022 W1); alle
   gedeelde catalogi zijn bewust platform. Het énige grijze gebied is code-vast i.p.v. beheerbaar
   (P50-4, protocol e.d.) — dat is "geen wereld" in plaats van de verkeerde.

---

## 5. M4 — De voordeur: wat ziet iemand die er niet bij mag?

**Nav-gating, tenant-shell** (`AppLayout.vue`, 17 nav-items): **15 van 17 zichtbaar voor élke
tenant-rol** — 8 ongegate (o.a. Checklistvragen r190, Migratienorm r198) en 7 gegate op een
computed die álle vier de rollen omvat (`magArchitectuurZien` r24 / `magMigratieZien` r20). Echt
beperkt: 2 — Gebruikersbeheer (beheerder, r136/r28) en Auditlog (beheerder+auditor, r144/r30).
**Platform-shell** (`BeheerLayout.vue`): 9/9 nav-items ongegate binnen de shell; de shell zelf zit
achter `meta.platform`.

**Knop-zichtbaar-maar-403** (de backend handhaaft altijd; dit is wat de gebruiker ervaart):

| Geval | Telling | Wat de gebruiker ervaart |
|---|---|---|
| `ChecklistConfigBeheer.vue` — **0 rol-checks** in de hele view (geen auth-import); mutatie-knoppen op r341/r426/r434/r314/r475; nav-ingang óók ongegate | **1 view** (het enige scherm waar knoppen zonder énige gating direct via de nav bereikbaar zijn) | een viewer/auditor ziet "Deactiveren"/"Opslaan"/toevoegen, klikt, en krijgt pas dán een weigering |
| Formulier-Opslaan ongegate terwijl de *entree* wél gegate is: `PartijFormulier.vue:392`, `ContractFormulier.vue:329`, `ComponentFormulier.vue:555` (routes zonder rol-meta) | 3 formulieren | alleen via een directe URL bereikbaar; wie er zo komt kan invullen en krijgt bij Opslaan een 403 |
| Alle overige views met mutatie-knoppen | ±35 views/secties **wél** gegate (mag*-computed of prop-keten, o.a. `AfdelingSelect`/`ContactpersoonSelect` via `magAanmaken`-prop) | knop verschijnt alleen voor wie hem mag gebruiken |

**Route-laag-detail:** geen enkele route dwingt tenant-rol-niveaus af (`MIGRATIE_ROLLEN` = alle
vier; `routeBeslissing` checkt alleen tenant↔platform). Gebruikersbeheer/auditlog/checklistvragen
zijn via directe URL door elke tenant-rol te openen — de nav verbergt, de backend weigert. Bewust
patroon (affordance vs. handhaving, likara-security §Rol-gating), geen autorisatie-gat.

**Omgekeerd (mag wel, geen ingang): 0 gevallen.** NormBeheer klopt precies (knoppen `v-if="magBeheren"`
r147 + read-only-hint r106-110 voor niet-beheerders); de auditor heeft zijn Auditlog-ingang.
Detail: de rol **platformoperator komt in de frontend niet voor** (0 grep-hits) — alle platform-gating
checkt alleen `platformbeheerder`; een operator-sessie zou alle 9 config-schermen read-only zien
(knoppen verborgen). Geen ontbrekende ingang, wel een niet-gemodelleerde rol in de UI.

---

## 6. M5 — Catalogi en keuzelijsten: van wie zijn ze?

| Groep | Gedeeld of per gemeente | Wie wijzigt | Bewijs |
|---|---|---|---|
| 9 platform-catalogi (componentconfig, contractconfig, relatiekenmerk, partijsoort, vraagbetekenis, componentrol, biv_schaal, applicatiefunctie, referentiemodel_optie) | **gedeeld** over alle tenants (geen RLS) | uitsluitend platformbeheerder (lk_platform LAW; lk_app SELECT-only, geen tenant-endpoint) | platform_rbac.py + likara-db §Grants |
| Checklistvragen + antwoordopties | **per gemeente** (RLS + FORCE, kopie bij onboarding) | tenant (medewerker+, zie M3-1) | `models.py` checklistvraag, ADR-022 W1 |
| ±14 code-enums (protocol, hostingmodel, levensfase, …) | gedeeld — in de code | niemand zonder deploy | checkpoint §2D |

- **"Gedeelde lijst wijzigbaar door één gemeente": 0 gevallen.** Geen enkele tenant-route raakt een
  platform-catalogus; de grants blokkeren het ook op DB-niveau (lk_app SELECT-only). De scherpste
  multi-tenant-fout bestaat hier niet.
- **Omgekeerde (zou per gemeente kunnen verschillen maar is gedeeld/vast):** (a) de code-enums uit
  P50-4 — een koppelprotocol verschilt per landschap en is nu platform-vast in code; (b) principiëler:
  álle catalogi behalve de checklistvraag zijn platform-gedeeld — dat is een vastgelegde kernregel
  (likara-domeinmodel §5: *"Checklistvraag is de ENIGE tenant-eigen catalogus — niet-onderhandelbaar"*),
  passend bij de één-tenant-fase (likara-ux §Eén tenant nu). Zodra meerdere gemeenten écht
  verschillen (eigen beheerrollen? eigen partijsoorten?), is dat een heroverwegings-besluit van Bert,
  geen bug.

## 7. M6 — Wat zegt de vastlegging, en volgt de code hem?

| Vastlegging | Volgt de code hem? |
|---|---|
| ADR-010 (RBAC, declaratieve matrix) | ja — `PERMISSIES` enige bron, fail-secure; matrixtests her-coderen de tabel |
| ADR-012 (+A/B/C: tweelaags model, strikte scheiding) | ja — twee matrices, kruis-403, aparte DB-rollen; **maar** 3 platform-entiteiten uit de matrix hebben geen route meer (M3-2) |
| ADR-050 (rollengrens op het onderwerp) | ja — `verwijder_actie` + frozensets + `test_rollengrens_adr050`; **maar** de Entiteit-comment bij FUNCTIEVERVULLING (rbac.py:57-59) zegt nog "guardt op VERWIJDEREN (beheerder)" terwijl de frozenset (r256) én de route (`functievervulling.py:99-104`) WIJZIGEN afdwingen — stale comment |
| ADR-022 W1 (vragenset = tenant-eigendom) | ja — maar de reikwijdte-vraag (welke tenant-ról) is daar nooit gesteld; OPVOLGPUNTEN P50-1 verwachtte zelfs platformbeheer (checkpoint §5.1) |
| ADR-052 (norm: iedereen leest, beheerder stelt in) | ja — COMPONENT_NORM-matrix + route-guard |
| likara-security §Tweelaags rollenmodel / §RBAC-handhaving | ja |
| likara-domeinmodel §7 (rollengrens + `_INHOUD`-patroon) | ja |

---

## 8. Samenvattende tabel

Telling op de handelings-rijen uit M2 (gebundelde rijen tellen als hun bundel):

| Reikwijdte | Handelingen (rijen/bundels) | Waarvan nu verkeerd bewaakt |
|---|---|---|
| R0 — kijken | 3 | 0 |
| R1 — eigen registratie | 8 bundels (≈ 23 entiteit-acties) | 0 |
| R2 — organisatiebreed | 6 | **3** (het checklistvraag-cluster: aanmaken · wijzigen · deactiveren) |
| R3 — platformbreed | 3 (+ ±14 code-vaste lijsten zonder handeling) | 0 |
| dode entries | 4 | n.v.t. (recht zonder handeling) |

## 9. Niet vastgesteld

- **Geen browserverificatie** — schermgedrag (welke knop zichtbaar is) is uit de code afgeleid.
- **Wat Bert wíl** — deze analyse stelt de ist-stand vast; elke "klopt dat?"-cel met *nee* is een
  voorgelegd besluit, geen conclusie.
- De platform-shell-voordeur voor de **platformoperator** is gemeten op matrix-niveau (overal L);
  of elk beheerscherm zijn knoppen voor de operator verbergt is onderdeel van M4.

## 10. Tegenspraken (code wint)

1. **rbac.py intern:** Entiteit-comment FUNCTIEVERVULLING (r57-59, "verwijderen = VERWIJDEREN/
   beheerder, opdrachtkeuze gate 2a") ↔ `REGISTRATIE_FEIT_ENTITEITEN` (r256) + route
   (`functievervulling.py:99-104`) = WIJZIGEN/medewerker. De frozenset en route zijn de werkelijkheid
   (ADR-050 kwam ná gate 2a); de comment is stale.
2. **Platform-matrix ↔ routes:** CHECKLISTCONFIG/PLATFORMINSTELLINGEN/PLATFORMMETADATA staan in
   `PLATFORM_PERMISSIES` maar hebben 0 routes; ADR-012-tekst ("Checklistconfig LAW/L",
   platform_rbac.py:52-55) beschrijft een verhuisde werkelijkheid.
3. **Tenant-matrix ↔ routes:** TENANT_INSTELLINGEN heeft 0 routes.
4. **OPVOLGPUNTEN P50-1** verwachtte platformbeheer op vraagbeheer — code zegt tenant (al gemeld in
   het checkpoint §5.1; hier opnieuw geraakt omdat de reikwijdte-vraag erop voortbouwt).
