# Checkpoint — hoeveel wegen leiden er naar een component?

| | |
|---|---|
| **Sessie** | LI046 · V046 · read-only feitenopname vóór bouw |
| **Datum** | 2026-07-19 |
| **Commit** | `142d1c5` (werktree: alleen de twee LI046-checkpointrapporten, ongecommit) |
| **Modus** | Niets gewijzigd behalve dit rapport; niets gebouwd; niet gecommit |
| **Voorafgaand** | `Checkpoint-detailpaneel-per-relatiesoort-V046.md` |

**Uitkomst in één zin:** er zijn **21 navigaties naar het componentdetail verspreid over 16 bestanden, waarvan er precies één context meegeeft** (de blokkade-doorklik met `?tab=&cat=&markeer=`); het aanleiding-mechanisme bestáát dus al — URL-gedragen, deelbaar en herstelbaar — maar is checklist-specifiek en wordt nergens anders gebruikt, en vier plekken nemen zelfstandig de beslissing "welk objecttype heeft welk detailscherm".

---

## Blok 1 — De volledige inventaris

### Wegen naar het componentdetail (`name: 'component-detail'`)

| # | Waar | Wat klikt de gebruiker | Hoe | Context mee? |
|---|---|---|---|---|
| 1 | `BlokkadeOverzichtView.vue:100-117` | blokkade-rij / vraag-link | `router-link` met query | **JA** — `?markeer=<vraagcode>` + bij applicatie `?tab=checklist&cat=<categorie>` |
| 2 | `ComponentLijst.vue:359` | rij (naam) | `router-link` | kaal |
| 3 | `ComponentLijst.vue:366` | zoekresultaat | `router.push` | kaal |
| 4 | `LandschapskaartView.vue:1319` (`_detailLink`) | "Open component →" in knoop-popup én zijpaneel (2 consumenten, één gedeeld predicaat) | `router.push` | kaal |
| 5 | `LandschapskaartView.vue:1135` | detail-paneel-knop | `router.push` | kaal |
| 6 | `SignaleringView.vue:53-58,161` | signaal-rij (3 taks: component/applicatie/entiteit) | `router-link` | kaal — **een signaal-doorklik verliest zijn aanleiding** |
| 7 | `PlaatsingSignalenView.vue:93` | signaal-rij | `router-link` | kaal |
| 8 | `DashboardView.vue:224` | applicatie in dashboard-lijst | `router-link` | kaal |
| 9 | `PartijDetail.vue:380` | component-via-contract (leverancier) | `router-link` | kaal |
| 10 | `PartijRollenSectie.vue:27-31` | object van een rol (eigen type→route-map) | `router-link` | kaal |
| 11 | `GebruikteApplicatiesSectie.vue:107` | gebruikte applicatie op partij | `router-link` | kaal |
| 12 | `ContractDetail.vue:205,226` | applicatie bij (deel)contract | `router-link` | kaal |
| 13 | `StructuurSectie.vue:81` | onderdeel/host-rij | `router-link` | kaal |
| 14 | `ImpactSectie.vue:39` | geraakt component | `router-link` | kaal |
| 15 | `ArchitectuurView.vue:54` | element in architectuurlijst (eigen type→route-map) | `router-link` | kaal |
| 16 | `ArchitectuurLagenView.vue:23` | pill in lagenweergave (eigen type→route-map) | `router-link` | kaal |

Plus de **legacy-redirects** `applicatie-detail`/`applicatie-bewerken` (`router/index.js:111-112`) en `component-bewerken` → `?bewerk=1` (`router/index.js:126`).

### Andere landschapsobjecten (apart geteld)

| Object | Detailroute? | Ingangen (bestanden) | Context ooit mee? |
|---|---|---|---|
| **contract** | ✓ `contract-detail` | 10 bestanden (o.a. ContractLijst/-Sectie/-Detail, PartijDetail, kaart `_detailLink`) | nooit |
| **partij** | ✓ `partij-detail` | 9 bestanden (o.a. PartijLijst, VerantwoordelijkheidSectie, kaart, ArchitectuurView) | nooit |
| **bedrijfsfunctie** | **✗ — geen detailscherm** (alleen `bedrijfsfunctie-lijst`, `router/index.js:139`) | nav-link + lijst zelf | n.v.t. |
| **proces** | **✗ — geen route** (MVP-verborgen, ADR-043) | geen | n.v.t. |

Het vraagstuk is dus **breder dan componenten** (contract/partij delen het patroon, allen kaal), en voor twee landschapsobjecten is er überhaupt geen plek om te landen.

## Blok 2 — Bestaat er al zoiets als een aanleiding?

**Ja — vier mechanismen, verschillend van gedrag en herbruikbaarheid:**

1. **De deep-link-query op ComponentDetail** (`ComponentDetail.vue:246-252, 290`): `?tab=` + `?cat=` (tab/categorie openen, CD022), `?markeer=<vraagcode>` (checklistvraag markeren — doorgegeven als `:markeer-code` aan `ChecklistscoreSectie`, `:552`), `?bewerk=1` (bewerk-overlay). **Leeft in de URL** → deelbaar, herstelbaar, overleeft F5. **Eén producent** (`BlokkadeOverzichtView.detailDoel`) — niet hergebruikt door de 15 andere ingangen.
2. **`?center=` op de landschapskaart** (deep-link componentdetail → kaart) — zelfde URL-familie, omgekeerde richting.
3. **De kaart-handoff** (LI038, proces→kaart): consume-once store, **niet** in de URL → bewust niet deelbaar/herstelbaar. Ander gedrag dan mechanisme 1.
4. **`useTerugNavigatie`** (contextuele terugknop) + **`useLijstStaat`** (lijststaat; precedentie deep-link > bewaarde staat) — flankerend: brengen je terug, niet aan.

**Conclusie voor de ontwerpvraag:** er valt iets te **promoveren** (mechanisme 1 is precies "landen bij het feit", URL-gedragen), maar het is vandaag checklist-specifiek (`markeer` = vraagcode, geen generiek feit-anker) en per plek opnieuw te verzinnen.

## Blok 3 — Waar kán een aanleiding landen?

**Landingsplekken op ComponentDetail** (`ComponentDetail.vue:201-226`): tabs `overzicht` · `bedrijfsfunctie` (altijd) · `checklist` (alleen checklist-dragend) · `datatypes`/`gebruikersgroepen`/`koppelingen` (alleen subtype applicatie) · `gebruik` · `opbouw` · `impact` · `contracten` · `verantwoordelijkheden` (altijd) · `blokkades` (checklist-dragend). Binnen `checklist`: 12 categorieën + vraag-markering. Plus de bewerk-overlay (`?bewerk=1`).

**Eerlijkheidstoets — kaart-ringen → landingsplek:**

| Ring-feit | Aanwijsbare landing | Oordeel |
|---|---|---|
| koppeling (flow) | tab `koppelingen` | ✓ (alleen bij subtype applicatie — niet-applicatie-component mét flow heeft **geen tab**) |
| draait op / samenstelling | tab `opbouw` | ✓ |
| valt onder contract | tab `contracten` | ✓ |
| rol/beheer | tab `verantwoordelijkheden` | ✓ |
| gebruikt (organisatie) | tab `gebruik` | ✓ |
| gebruikt door (groep) | tab `gebruikersgroepen` | ✓ subtype-only — zelfde gat als flow |
| ondersteunt (bedrijfsfunctie) | tab `bedrijfsfunctie` | ✓ |
| eigenaar | veld op Overzicht | **gedeeltelijk** — tab bestaat, veld-markering bestaat niet (markeer is checklist-only) |
| onderdeel van (functie-hiërarchie) | — | **✗ — bedrijfsfunctie heeft geen detailscherm**; dit feit heeft geen landingsplek |
| hoort bij (organisatiestructuur) | — (partij-kant) | partij-detail bestaat, maar zonder sectie-anker |

**Eerlijkheidstoets — de open punten uit het open-punten-overzicht** (bronnen per `OPVOLGPUNTEN.md:107-117`; het exacte mockup-lijstje van negen is niet in de repo aangetroffen — **niet vastgesteld**; onderstaande negen zijn de gedocumenteerde bronnen):

| Open punt | Landing | Oordeel |
|---|---|---|
| checklist nee/deels | `?tab=checklist&cat=…&markeer=<code>` | ✓ — bestaat en werkt al |
| geen eigenaar | Overzicht (veld) | gedeeltelijk — geen veld-anker |
| geen verantwoordelijke | tab `verantwoordelijkheden` | ✓ |
| BIV onvolledig | Overzicht/bewerk-overlay (3 velden) | gedeeltelijk — geen veld-anker |
| geen gebruikersgroep | tab `gebruikersgroepen` | ✓ bij applicatie; **✗ bij niet-subtype** (tab bestaat daar niet) |
| geïsoleerd (geen koppeling) | tab `koppelingen` | idem — subtype-only |
| geen bedrijfsfunctie | tab `bedrijfsfunctie` | ✓ |
| levensfase/bedoeling leeg | bewerk-overlay (`?bewerk=1`) of Overzicht | gedeeltelijk — geen veld-anker; `?bewerk=1` opent de héle overlay |
| beschrijving leeg | idem | gedeeltelijk |

**Feiten zonder (eerlijke) landingsplek — de kernuitkomst:** (a) alle **veld-niveau-feiten** buiten de checklist (eigenaar, BIV, levensfase, bedoeling, beschrijving) — er is geen generiek veld-anker, alleen de checklist kent markering; (b) **functie-hiërarchie-feiten** — bedrijfsfunctie heeft geen detailscherm; (c) **flow/groep-feiten op niet-applicatie-componenten** — de tab bestaat daar niet.

## Blok 4 — Is "alles door één ingang" scanbaar?

**Ja.** Aangrijpingspunt: het **route-naam-literal** — een dekkingsscan grept view-bronnen op `name: 'component-detail'` (en `'contract-detail'`, `'partij-detail'`, plus de legacy `'applicatie-detail'`) buiten de gedeelde ingang-bouwsteen. De navigaties zijn vandaag allemaal via dat literal geschreven (21/21 gevonden op exact dat patroon) — er is geen dynamische route-constructie die de scan zou missen, behalve de drie **type→route-mapjes** (`ArchitectuurView.vue:54`, `ArchitectuurLagenView.vue:23`, `PartijRollenSectie.vue:27-31`) die het literal in een object stoppen; ook die zijn grep-baar.

**Legitieme uitzonderingen die de scan moet toestaan:** `router/index.js` (de redirects), de gedeelde ingang zelf, en testbestanden. Open (blok 5): of kale rij-klikken in ComponentLijst een uitzondering zijn of óók door de ingang moeten.

**Precedenten in de codebase:** frontend `tests/api.filter.test.js` (allowlist + luide fout bij onbekende sleutel), `scripts/check-css-build.mjs` (bestands-scan met de-vervuilde patronen), backend `test_rollengrens_adr050` (bronscan over alle routes tegen een classificatie). De scan is dus naar bestaand recept te maken; het geschikte huis is een vitest-bronscan naar het model van de api-filtertest.

## Blok 5 — Verrassingen, risico's en open vragen

**Verrassingen:**
- **Vier plekken beslissen zelfstandig "welk type → welk detailscherm"**: `_detailLink` (kaart), ArchitectuurView, ArchitectuurLagenView, PartijRollenSectie — vier kopieën van dezelfde afweging; een vijfde consument kan de volgende `gebruikt`-tak-vergissing worden.
- **`markeer` heeft precies één producent en één consument-keten** — het beste mechanisme is tegelijk het minst hergebruikte.
- **Bedrijfsfunctie en proces zijn landschapsobjecten zonder detailscherm** — "binnenkomen bij het feit" kan daar structureel niet.
- Legacy-routes `applicatie-*` leven nog als redirects (werkende maar dubbele paden).

**Terug-knop / deelbare URL / plaatstaat:** het bestaande query-mechanisme (`tab`/`cat`/`markeer`/`bewerk`) leeft volledig in de URL → **deelbaar en herstelbaar vandaag al mogelijk**; `router.replace` bij tab-wissel houdt de history schoon (CD022). De kaart-handoff is bewust consume-once (níét deelbaar) — een aanleiding via dat kanaal zou de belofte breken. `lk-state`/`useLijstStaat` hanteren al de precedentie "deep-link wint van bewaarde staat" — een aanleiding-query past daarin zonder conflict. `useTerugNavigatie` (router.back) blijft werken zolang de aanleiding een gewone navigatie is.

**Stille keuzes die niemand expliciet genomen heeft:**
- of de aanleiding een **generiek anker** wordt (feit-soort + feit-id in de query) of per feit-soort een eigen parameter (zoals `markeer` nu);
- of een aanleiding zonder eerlijke landingsplek (blok 3) de navigatie **weigert, kaal landt, of de dichtstbijzijnde tab opent** — elk van de drie liegt op zijn eigen manier;
- of kale lijst-/rij-navigaties óók door de ingang moeten (uniformiteit) of legitiem kaal blijven (er ís geen aanleiding);
- of de subtype-conditie op de tabs (`koppelingen`/`gebruikersgroepen` alleen bij applicatie) houdbaar is zodra open punten op élk componenttype ernaartoe willen.

**Open ontwerpvragen voor Bert:**
1. Wordt de gedeelde ingang een promotie van het bestaande query-mechanisme (`tab`/`cat`/`markeer`) naar een generiek feit-anker, of iets nieuws?
2. Wat doet de ingang bij een feit zonder landingsplek — weigeren, kaal landen, of dichtstbijzijnde tab?
3. Vallen kale rij-klikken (lijsten) onder "alles door één ingang", of alleen feit-doorklikken?
4. Krijgen bedrijfsfunctie (en t.z.t. proces) een detailscherm, of is de lijst-met-focus daar de landingsplek?
5. Worden de vier type→route-mapjes onderdeel van dezelfde gedeelde ingang (één beslispunt), of blijft type-routing apart?
6. Moet de dekkingsscan er in dezelfde slice bij (KERNLES LI038: de regel houdt pas als een scan hem afdwingt), of mag hij volgen?

**Niet vastgesteld:** het exacte negental uit de mockup (niet in de repo aangetroffen; de negen gedocumenteerde open-punt-bronnen uit `OPVOLGPUNTEN.md` zijn als benadering gebruikt); of er buiten de frontend nog ingangen bestaan (e-mail/export-links) — niets gevonden, maar afwezigheid is geen bewijs.

---

**STOP** — geen fix, geen ontwerp, geen commit.
