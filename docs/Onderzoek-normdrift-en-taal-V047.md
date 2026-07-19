# Onderzoek — normdrift in de demostaat, en "gemeente/systeem" op het scherm

**Sessie:** LI047 · **Build:** V047 · **Commit:** 5e00bab · **Type:** READ-ONLY onderzoek
**Datum:** 2026-07-19 · Twee losse sporen, één opdracht.

> Dit rapport **wijzigt niets** aan code/schema/seed/data. Het enige geschreven bestand is dit rapport zelf.
> Geen reseed uitgevoerd, geen testsuite gedraaid (zie A.4). Feiten met vindplaats of met de gedraaide query.

---

## Deel A — waardoor raakt de dev-tenant zijn norm (en zijn scores) kwijt?

### Kernbevinding: het zijn TWEE oorzaken, niet één

De audit-trail scheidt ze scherp. `component_norm` en de Zaaksysteem-score zijn op **verschillende
momenten door verschillende actoren** geraakt:

| Verschijnsel | Actor | Laatste moment | Aard |
|---|---|---|---|
| `component_norm` leeg | `system:onbekend` (backend-proces) | 2026-07-19 **18:40–18:41** | **testsuite tegen de dev-tenant** |
| Zaaksysteem-score `nee`→`ja` | **`j.devries@bvowb.test`** | 2026-07-19 **09:46:49** | **handmatige UI-actie** (browsercheck) |

Dat is belangrijk voor het vervolg: een fix op het ene spoor lost het andere niet op.

---

### A.1 De stand, en het verschil met wat de seed hoort te zetten

```sql
SELECT 'component',count(*) FROM component
UNION ALL SELECT 'component_norm',count(*) FROM component_norm
UNION ALL SELECT 'component_klaarverklaring',count(*) FROM component_klaarverklaring
UNION ALL SELECT 'component_bevinding',count(*) FROM component_bevinding;
SELECT score::text,count(*) FROM checklistscore GROUP BY 1;
```

| Tabel / verdeling | Gemeten | Wat de seed hoort te zetten | Verschil |
|---|---|---|---|
| `component_norm` | **0 rijen** | **10 rijen**, waarvan **6 verplicht** | **alles weg** |
| `component_klaarverklaring` | 5 | 5 | — |
| `component_bevinding` | 3 | 3 | — |
| `checklistscore` | **267× `ja`, 0× `nee`/`deels`** | 266× `ja` + **1× `nee`** (Zaaksysteem) | **1 score omgeslagen** |
| `blokkade` | 1× `opgelost` | 1× `open` | gevolg van bovenstaande |

**De zes verplichte feiten** (bevestigt de correctie uit het vorige checkpoint): `seed_component_norm`
zet de vijf `DEFAULT_VERPLICHT` op true (seed.py:190-193 · component_norm_service.py:58-60), en
`_seed_bvowb_scenario` zet daarná **`bedoeling`** óók op true (dev_seed_testdata.py:1794-1800) — de
gemodelleerde latverschuiving. Netto: eigenaar · verantwoordelijke · biv · contract · koppelingen ·
**bedoeling**.

### A.2 Wie haalt de rijen weg — **twee testbestanden, allebei op de dev-tenant**

Een scan over álle testbestanden op brede deletes van deze tabellen levert exact twee treffers:

| Bestand | # DELETE-statements | Tenant | Tenant-gescoped? | Beperkt tot eigen fixtures? |
|---|---:|---|---|---|
| `tests/test_component_norm_adr052.py` | **7** | `11111111-…-111111111111` = **de dev-tenant** (:20) | ja | **nee** |
| `tests/test_component_bevinding_adr052.py` | **4** | idem (:18) | ja | **nee** |

Alle overige 44 testbestanden die de dev-tenant gebruiken, doen **geen** delete op deze tabellen.

**Waarom "niet beperkt tot eigen fixtures" hier onvermijdelijk is:** `component_norm` is **tenant-scoped,
niet component-scoped**. Er ís geen eigen-fixture-afbakening mogelijk — elke rij van het tenant is
"andermans" rij. De teardown kan dus niet netjes worden gemaakt zolang hij op de dev-tenant draait.

De twee kritieke plekken:

```python
# test_component_norm_adr052.py:167-173 — helper, draait in élke live-test van dit bestand
async def _norm_alles_verplicht(s):
    await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})   # ← wist de seed-norm
    for f in cn.HARDE_FEITEN:
        s.add(ComponentNorm(tenant_id=uuid.UUID(_TID), feit_sleutel=f, verplicht=True))   # ← zet ALLE 10 op true
```
```python
# test_component_norm_adr052.py:193-202 — de teardown die 'm leeg achterlaat
await s.execute(text("DELETE FROM component_norm WHERE tenant_id = :t"), {"t": _TID})
try:
    ...
finally:
    await s.execute(text("DELETE FROM component_norm WHERE tenant_id = :t"), {"t": _TID})   # ← eindstand: 0 rijen
    await s.commit()
```

Dezelfde helper staat in `test_component_bevinding_adr052.py:96-103`, met teardown op `:133`, `:172`, `:226`.

**De tegenhanger die het wél goed doet, in dezelfde ADR-familie:**
`tests/test_component_norm_beheer_adr052.py:19` gebruikt `_TID = "99990052-4b00-0000-0000-000000000052"` —
een **eigen test-tenant**. Drie bestanden uit hetzelfde ADR-052-spoor, één ervan gescheiden, twee niet.

Dit is exact het geval dat likara-tests §LI039 beschrijft: *"zodra een teardown NIET tot eigen rijen te
beperken is, is een eigen test-tenant verplicht"* — met `test_referentiemodel_import_gate1b.py` als
precedent (tenant `9999…`). De regel bestaat; deze twee bestanden dragen hem niet.

### A.3 Ander schrijfpad? — ja, en het verklaart de tweede helft

**De seed-volgorde** (dev_seed_testdata.py `main()`): `seed_component_norm` (:1890) → `_seed_bvowb_scenario`
(:1905). Binnen het scenario: applicaties + scores (:1103-1134) → klaarverklaringen (:1781-1792) →
`_seed_schoon_geval` (:1795) → **bedoeling-toggle** (:1794-1800). Een latere stap overschrijft geen eerdere;
de volgorde is bewust en gedocumenteerd ("VOLGORDE is essentieel", :1779-1781). **Geen zelf-overschrijvend
seed-pad gevonden.**

**Het beheerscherm** kan de norm wél muteren: `NormBeheer.vue` → `component_norm_beheer_service` zet de
`verplicht`-vlag. Dat verklaart geen léégte (het scherm kent geen delete-pad: `lk_platform`/`lk_app` hebben
geen DELETE-grant en er is geen endpoint), maar wel losse `update`-records in de audit.

**De handmatige score-wijziging — bewezen:**

```sql
SELECT a.tijdstip, c.naam, coalesce(a.actor_email,a.actor_sub) AS actor
FROM audit_log a
LEFT JOIN checklistscore s ON s.id=a.entiteit_id
LEFT JOIN component c ON c.id=s.component_id
WHERE a.entiteit_type='checklistscore' AND a.wijziging->'score'->>'oud' IS NOT NULL;
-- 2026-07-19 09:46:49.836376+00 | Zaaksysteem | j.devries@bvowb.test
```

**Precies één** score-update in de hele audit-historie: `{"score": {"oud": "nee", "nieuw": "ja"}}` op
Zaaksysteem, door een **echt dev-gebruikersaccount** (niet `system:`). Dat is een UI-handeling — vrijwel
zeker een browsercheck waarin iemand de score op "ja" zette en zo de blokkade legitiem liet auto-oplossen
(het gedrag dat `checklistscore_service` hoort te vertonen). **Geen defect** — wél demostaat-schade.

### A.4 Reproduceerbaar? — **ja, en zonder de suite te draaien**

De opdracht verbiedt een suite-run als die de dev-DB muteert. Dat is hier aantoonbaar het geval (A.2), dus
**ik heb geen enkele test gedraaid**. Dat is ook niet nodig: de audit-trail is het bewijs.

```sql
SELECT tijdstip, actie, wijziging::text FROM audit_log
WHERE entiteit_type='component_norm' ORDER BY tijdstip;
```

Het spoor toont **zes bursts van 10 `create`-records met `verplicht: true` voor álle tien feiten** —
de handtekening van `_norm_alles_verplicht`, want de seed zet er vijf op true en vijf op false:

| Burst | Tijdstip |
|---|---|
| 1–3 | 2026-07-18 20:26:21 · 20:26:23 (2×) |
| 4–5 | 2026-07-18 21:03:51 · 21:03:53 (2×) |
| **6** | **2026-07-19 18:40:48 · 18:40:50** |

**En de tabel is nú leeg.** Dat is het sluitende bewijs: de laatste run heeft rijen aangemaakt en ze in de
`finally` weer verwijderd.

**Waarom de deletes zélf niet in de audit staan** — en dat is een bevestiging, geen gat in het bewijs: de
tests wissen via **core-SQL** (`session.execute(text("DELETE FROM …"))`), en de audit hangt op de
ORM-flush-hooks. Precies het bekende systemische gat uit likara-security §LI035 (*"Audit-dekking is
ORM-dekking"*). De `s.add(ComponentNorm(...))` is ORM → zichtbaar; de `DELETE` is core → onzichtbaar. De
asymmetrie in het spoor (alleen creates, nooit deletes) **past exact** op deze twee bestanden.

Aanvullend bewijs dat de suite herhaaldelijk tegen de dev-tenant draaide:

```sql
SELECT count(*) FILTER (WHERE c.id IS NOT NULL) AS nog_bestaand,
       count(*) FILTER (WHERE c.id IS NULL)     AS verdwenen
FROM (SELECT DISTINCT (wijziging->'component_id'->>'nieuw')::uuid AS cid FROM audit_log
      WHERE entiteit_type='checklistscore') x
LEFT JOIN component c ON c.id = x.cid;
-- nog_bestaand: 5 | verdwenen: 27
```
**27 van de 32** componenten waarop ooit een checklistscore is gezet, bestaan niet meer — opgeruimde
testfixtures. De dev-tenant is dus structureel het werkterrein van de live-tests.

⚠ **Niet vastgesteld:** de losse `update {verplicht: false→true}`-records (20:18:20 · 20:26:23 · 21:04:18 ·
18:41:16) zijn niet te onderscheiden tussen de seed-bedoeling-toggle en een handmatige actie in het
norm-beheerscherm — beide lopen via het ORM en produceren een identiek record.

### A.5 Wat een reseed herstelt — en wat niet

**Wel hersteld** (stand ná `docker compose down -v && up -d` + handmatige dev-seed, conform
`docs/LOKAAL-TESTEN.md`):

| Aspect | Stand na reseed |
|---|---|
| Verplichte feiten | **6**: eigenaar · verantwoordelijke · biv · contract · koppelingen · bedoeling |
| Componenten met open punten | 18 van 19 (zie tabel in `Checkpoint-open-punten-tabblad-V047.md` §5.2, kolom B) |
| **Schoon geval** | **HR-systeem** — 0 open verplichte feiten; snapshot `{}` |
| **Rijkste geval** | **Extern SaaS-platform** en **Shared fileshare** (elk 6) |
| **Bewust geen** | **Archiefbeheer** (koppelingen + contract) · **HR-systeem** (koppelingen) |
| Checklist op nee/deels | **1** (Zaaksysteem, positie 0) → 1 open blokkade |

**Niet hersteld — de oorzaak blijft staan.** Een reseed zet de norm terug; de eerstvolgende run van
`test_component_norm_adr052.py` of `test_component_bevinding_adr052.py` wist hem opnieuw. Omdat beide
`@integratie`-gemarkeerd zijn (`skipif(not _db_bereikbaar())`, test_component_norm_adr052.py:148) draaien ze
**alleen** als de dev-DB bereikbaar is — dus precies wanneer iemand aan het werk is. Dat is de situatie die
de opdracht wil vermijden: de norm verdwijnt midden in een verificatie en het lijkt een fout in het nieuwe
scherm.

### A.6 Meest waarschijnlijke oorzaak, met bewijs

> **De teardown van twee ADR-052-testbestanden wist de norm van de dev-tenant.** Beide gebruiken
> `_TID = "11111111-…-111111111111"` (de dev-tenant) en doen `DELETE FROM component_norm WHERE tenant_id=…`
> in hun `finally` — een tabel die tenant-scoped is en dus niet tot eigen fixtures af te bakenen valt.
>
> **Bewijs:** (1) exact deze twee bestanden bevatten zulke deletes (11 statements totaal); (2) de audit
> toont zes bursts van 10 creates met álle feiten op `true` — de handtekening van hun helper
> `_norm_alles_verplicht`, niet van de seed (die zet er vijf op true); (3) de laatste burst is van
> 2026-07-19 18:40 en de tabel is nu leeg; (4) de deletes ontbreken in de audit omdat ze core-SQL zijn —
> exact het bekende ORM-only-gat; (5) 27 van 32 audit-componenten zijn opgeruimde testfixtures.
>
> **De omgeslagen Zaaksysteem-score staat hier los van:** één handmatige UI-actie door
> `j.devries@bvowb.test` op 2026-07-19 09:46:49. Correct systeemgedrag, geen defect.

**Wat er nodig zou zijn om de oorzaak weg te nemen** — als voorstel, **niet uitgevoerd**:

1. **Beide bestanden op een eigen test-tenant zetten**, zoals `test_component_norm_beheer_adr052.py:19` al
   doet (`99990052-4b00-…`). Dat is één constante per bestand; de helpers en teardowns kunnen ongewijzigd
   blijven, want ze zijn al tenant-gescoped. ⚠ **Te verifiëren vóór de bouw:** de tests leunen mogelijk op
   geseede dev-data (componenten/relaties) die in een verse tenant niet bestaan — dan moeten ze hun eigen
   fixtures aanmaken. Dat is **niet vastgesteld**; het vraagt per test een leescheck.
2. **Aanvullend, structureel** (in de geest van werkprotocol §KERNLES LI038 — *"maak de regel onvergeetbaar
   in plaats van hem nóg eens op te schrijven"*): een scan die faalt zodra een testbestand een
   niet-component-gescoped `DELETE` op de **dev-tenant-id** doet. Dan kan het derde geval niet ontstaan.
   De bestaande bronscan-praktijk (`check-css-build.mjs`-vorm, likara-tests §LI040 *"bewijs dat een scan
   bijt"*) is het model.
3. **De reseed daarna**, niet daarvoor — anders is hij binnen één testrun weer weg.

---

### Open vragen voor Bert — deel A

1. De twee testbestanden op een **eigen test-tenant** zetten (zoals hun zusterbestand al doet): akkoord als
   richting, en wil je dat als eigen `START:`-opdracht vóór de reseed?
2. Wil je daarnaast de **structurele scan** (een test die faalt op een dev-tenant-brede DELETE in de
   testsuite), of is de tenant-scheiding voor nu genoeg?
3. De **reseed** zelf: pas uitvoeren ná de tenant-fix, of alvast nu zodat de demostaat klopt en de fix erna
   volgt?
4. De Zaaksysteem-score is door een **handmatige browsercheck** omgeslagen (correct gedrag). Wil je dat de
   seed dit geval "hersteld" krijgt bij elke reseed — of accepteer je dat een browsercheck de demostaat
   verandert en reseed je vóór elke verificatie?

---

## Deel B — waar staat "gemeente" en "systeem" in wat de gebruiker leest?

### B.1 "gemeente" — **klein en scherp begrensd: twee zichtbare zinnen**

Scan over `frontend/src` + `modules/bwb_ontvlechting/frontend` (`*.vue`, `*.js`; `dist/` en `node_modules/`
uitgesloten): **5 treffers, waarvan 3 codecommentaar**.

**(a) Schermtekst die generiek hoort te zijn — 2 treffers:**

| Vindplaats | Letterlijke zin | Ziet de gebruiker dit? |
|---|---|---|
| `modules/…/frontend/velduitleg.js:392` | *"Kosten per inwoner van de gemeente (gebruikelijk bij gemeentelijke voorzieningen)."* | **Ja** — uitlegpaneel bij het kostenmodel `per_inwoner` |
| `modules/…/frontend/views/PartijFormulier.vue:266` | *"Markeer je eigen organisatie als intern. Deelnemende gemeenten, partners en burger-doelgroepen zijn extern."* | **Ja** — hulptekst bij het scope-veld (intern/extern) |

**(b) Codecommentaar — niet zichtbaar, 3 treffers:** `OrganisatiegebruikSectie.vue:43`,
`StructuurSectie.vue:34`, `KoppelingSectie.vue:36` — alle drie de ADR-050-toelichting *"een uitspraak van
de gemeente"*. Geen schermtekst.

**Backend, user-facing:**

| Vindplaats | Zin | Zichtbaar |
|---|---|---|
| `services/seed_contractconfig.py:27` | catalogus-label **"Per inwoner (gemeente)"** | **Ja** — kostenmodel-keuzelijst |
| `services/seed.py` (6 vragen: 1.5, 2.7, 3.2, 4.3, 7.2, 7.4, 8.1) | checklistvragen met "gemeenten"/"gemeente-specifiek"/"Tiel"/"BWB" | **Ja** — de checklist |
| `services/seed_antwoordconfig.py:34,:39` | antwoordopties *"Gedeeld met BWB/andere gemeenten"*, *"Gemeente-specifiek"* | **Ja** — antwoordkeuzes |
| `models.py:855,:895` · `schemas/gebruiker_context.py:8` | docstrings | nee |

⚠ **De checklist-baseline is een aparte categorie.** De 89 vragen zijn tenant-eigen referentiedata
(likara-db §Referentietabel-uitzondering: *"per tenant gekopieerd bij onboarding"*) en dragen **naast**
"gemeente" ook **"Tiel"** en **"BWB"** — eigennamen van één specifieke ontvlechting, in de meegeleverde
platform-baseline. Dat is een zwaarder geval dan de twee zinnen onder (a): het raakt de vraag of de
default-checklist generiek is. **Ik heb hier niets over beslist** — zie open vraag 6.

**(c) Testdata / eigennamen — blijven staan:** `dev_seed_testdata.py` (31 regels met `Gemeente <Naam>`) —
Gemeente Tiel · Culemborg · West Betuwe. Eigennamen in de dev-fixture, conform likara-ux §generiek
(*"BvoWB is voorbeelddata, geen platformfunctie"*).

**(d) Documentatie/ADR — geen schermtekst:** 30 `.md`-bestanden onder `docs/`. Buiten scope.

### B.2 "systeem" als component-synoniem — **breder, maar geconcentreerd in drie gedeelde bronnen**

Eerst de **legitieme uitzonderingen** (domeinmodel §Terminologie), die ik heb uitgesloten:
`systeem-sleutel`/`systeem_sleutel` (beschermde catalogus-sleutel) · `SYSTEEM_ACTOR` / "Systeem (seed)"
(= LIKARA zelf, labels.js:81-94) · `Systeemsoftware` (ArchiMate-label, labels.js:226) · eigennamen
(Zaaksysteem, HR-systeem, Financieel systeem) · `identiteitssysteem`/`account-systeem`
(GebruikersbeheerView.vue:121,:239 — dat is Keycloak, geen component).

**Wat overblijft — "systeem" waar "component" of "applicatie" hoort:**

| Bron | # | Erft mee? | Voorbeeld |
|---|---:|---|---|
| **`VeldUitleg.vue:37`** (`LAT_PASSAGE`) | **1 constante** | **Ja — ~29 schermen** | *"Dit feit telt mee om dit **systeem** klaar te kunnen verklaren."* |
| **`standCodering.js`** (`lijstTekst`/`legendaTekst`, :34-41) | **6** | **Ja — lijst-pill + kaart + legenda** (LI043 één-bron) | *"hier draait een **systeem**"* · *"**systeem** bekend, gebruiker nog niet vastgelegd"* |
| **`velduitleg.js`** | **18** | per veld (één bestand) | *"Waarvoor dient dit **systeem**?"* (:33) · *"een **systeem** dat gewoon draait kan al een bestemming hebben"* (:110) |
| `NormBeheer.vue` (:93, :165, :170) | 3 | nee (per scherm) | *"welke feiten moeten bekend zijn voordat een **systeem** klaar verklaard wordt"* · *"Dit raakt N **systemen** die er nu niet aan voldoen"* |
| `SignaleringView.vue:133` | 1 | nee | *"Deze eerder klaar verklaarde **systemen** missen nu…"* |
| `SignaleringView.vue:143` | 1 | nee | `syst{{ rij.aantal === 1 ? 'eem' : 'emen' }}` — gesplitste string |
| `ComponentLijst.vue:586` | 1 | nee | `aria-label="Filter op **systemen** zonder bedrijfsfunctie"` |

**Totaal ≈ 31 zichtbare plekken, waarvan 7 in twee gedeelde bronnen** die samen het grootste bereik hebben.

⚠ **Hier zit een spanning die ik niet oplos.** Twee skill-uitspraken wijzen tegengesteld:

- likara-domeinmodel §Terminologie: *"'Systeem' is GEEN term in het model en wordt niet als synoniem
  gebruikt — niet in code, niet in UI-taal"*; en likara-ux §LI041 verwierp *"systeem"* bij een G-schijf
  expliciet ten gunste van *"waarmee wordt dit werk gedaan"*.
- Maar de UI gebruikt "systeem" op ~31 plekken **bewust en consistent** als het woord waarop de consultant
  aanslaat — en `BedrijfsfunctieLijst.vue:1130` draagt zelfs een comment die het omgekeerde vastlegt:
  *"'Component' i.p.v. 'systeem' — klopt óók voor een fileshare"*, dus daar is de keuze wél gemaakt.

Het is dus **geen slordigheid maar een onbesliste woordkeuze** die per scherm anders is uitgevallen. Zie
open vraag 7.

### B.3 Reikwijdte — kan het in één slice?

**"gemeente": ja, ruim.** Twee zichtbare frontend-zinnen + één catalogus-label. De drie codecommentaren
mogen mee als opruiming. **Buiten die slice** valt de checklist-baseline (7 vragen + 2 antwoordsets), die
een eigen besluit vraagt omdat het referentiedata is, geen schermtekst — en omdat er "Tiel"/"BWB" in staan.

**"systeem": ja, mits het een woordbesluit is en geen zoek-en-vervang.** De verhouding is gunstig:
**7 van de ~31 plekken zitten in twee gedeelde bronnen** (`LAT_PASSAGE`, `standCodering`) waar één
wijziging alles laat erven — precies het LI043-patroon *"eenmaal bron voor presentatie, alle vensters
erven"*. De resterende ~24 zijn per scherm geschreven en vragen elk een leescheck, want in sommige zinnen
is "systeem" **inhoudelijk juist** (bv. `velduitleg.js:299` *"het type ondersteunt een systeem, geen mens"*
— dáár is "systeem" de tegenpool van "mens", niet een synoniem voor component).

⚠ **`SignaleringView.vue:143`** (`syst{{ … 'eem' : 'emen' }}`) is een **gesplitste string**: een
zoek-en-vervang op "systeem" vindt hem niet. Wie deze slice bouwt moet daar expliciet langs.

---

### Open vragen voor Bert — deel B

5. De twee zichtbare "gemeente"-zinnen (`velduitleg.js:392`, `PartijFormulier.vue:266`) en het
   catalogus-label *"Per inwoner (gemeente)"*: allemaal naar "organisatie" — akkoord als één kleine slice?

6. De **checklist-baseline** draagt "gemeente(n)" én de eigennamen **"Tiel"** en **"BWB"** in 7 van de 89
   meegeleverde vragen. Dat is platform-referentiedata, geen schermtekst. Is dat een eigen spoor (de
   default-checklist generiek maken), of blijft die baseline bewust BWB-geënt?

7. **"Systeem" als woord voor een component**: de domeinmodel-terminologie verbiedt het, maar de UI gebruikt
   het op ~31 plekken consistent — en op één plek is expliciet het omgekeerde besloten
   (`BedrijfsfunctieLijst.vue:1130`). Wil je (a) "systeem" overal vervangen door component/applicatie,
   (b) het bewust toestaan als gebruikerstaal en de terminologieregel aanscherpen, of (c) alleen de twee
   gedeelde bronnen aanpakken en de rest laten?

8. Als je (a) of (c) kiest: hoort de correctie **vóór** de bouw van het tabblad "Open punten" (dat scherm
   toont norm-feiten en erft `LAT_PASSAGE`), of erna als eigen taalslice?

*(STOP na dit rapport. Geen fix, geen reseed, geen commit.)*
