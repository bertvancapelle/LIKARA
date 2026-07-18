# Read-only meting — welk teken en welke kleur zijn vrij voor de norm-aanduiding op het formulier?

**Sessie:** LI045 · **Build:** V045 · **Aard:** feitenopname, geen bouw · Gedaan náást de openstaande
4b-gate (die changeset onaangeroerd).

> Voorgenomen vorm: een klein **tikbaar teken achter het veldlabel** dat bij aanraking uitleg geeft —
> voorkeur van Bert: een **blauw uitroepteken ("!")** als link naar de uitleg. Niet het sterretje (dat
> belooft "opslaan geblokkeerd", en dat is hier onwaar). Deze meting stelt vast of teken én kleur vrij zijn.

---

## Kernuitkomst in één zin

**Het blauwe uitroepteken botst — niet met de amber ⚠, maar frontaal met de bestaande blauwe "i" van
`VeldUitleg`: die staat al op exact dezelfde plek (achter het veldlabel), in exact dezelfde kleur
(blauw = `--lk-color-primary`), met exact hetzelfde gedrag (tikbaar → uitlegpaneel), en dat op álle vijf
de norm-velden die een formulierveld hebben.**

---

## Blok 1 — Het uitroepteken: waar komt het al voor?

Het **losse teken "!"** komt als standalone glyph nergens voor. De **uitroepteken-familie** wordt op deze
schermen gedragen door **⚠ (driehoek-met-uitroepteken)**, altijd in **amber (waarschuwing)** of **rood
(fout)** — nooit blauw:

| Vindplaats | Vorm | Betekenis / gewicht |
|---|---|---|
| `MeldingBanner.vue` (gedeeld, verschijnt op **formulieren**/secties) | ⚠ amber (`warn`) · ⚠ rood (`danger`) | weigering/conflict ("bestaat al") resp. echte fout — met scroll-vangnet, niet te missen |
| `MigratiegereedheidSectie.vue` (**componentdetail**) | ⚠ amber | "klaar verklaard mét afwijking" — een echt verantwoordingssignaal (zwaar) |
| Landschapskaart, BedrijfsfunctieLijst, ProcesDiagram, Dashboard, PlaatsingSignalen | ⚠ amber | diverse waarschuwingen |
| Signalering (Registratiegaten-tab) | 🔴/🟡 emoji | ernst-indeling (geen ⚠, geen "!") |

**Ziet de gebruiker de nieuwe "!" naast een ⚠?** Op het **formulier** verschijnt ⚠ alleen als een
**tijdelijke MeldingBanner** (bovenaan het blok, bij een fout/conflict) — niet permanent, niet op de
veldlabels. De norm-"!" zou juist **permanent achter de labels** staan. Ander plek, andere kleur (blauw
vs amber). Op het **componentdetail** staat de amber ⚠ in het Migratiegereedheid-blok, los van de velden.

**Oordeel blok 1 — botst het teken?** Met de ⚠ zelf: **niet hard** (andere vorm: driehoek vs los teken;
andere kleur: amber/rood vs blauw). Máár de **betekenis "let op"** is al bezet door ⚠ in amber/rood. Een
blauw "!" zet daar een **tweede "let op"-teken** naast in een derde kleur — een gebruiker kan zich
afvragen: is dit blauwe "!" een waarschuwing zoals de amber ⚠, of iets anders? Dat is een echte
dubbelzinnigheid, geen "waarschijnlijk niet verwarrend". De hárde botsing zit echter in blok 2/3.

---

## Blok 2 — De kleur blauw: is die vrij?

**Er is géén aparte informatie-kleur naast de linkkleur.** De tokens (`themes/base.css`) kennen alleen
`--lk-color-primary` (#1B4B82) + tints (`primary-50/100/700`) en `--lk-color-accent` (#E8F0FB, bijna-wit).
**Geen `--lk-color-info`, geen `--lk-color-link`.** Blauw is dus de **enige** "interactief/link/info"-kleur.

Blauw wordt op deze schermen gebruikt voor:
- **links / doorklik** (router-links, "Bekijk … →") — de kanaal-check-bevinding "blauw = linkkleur" is
  hiermee **bevestigd**;
- de **`VeldUitleg`-"i"-knop** achter veldlabels (`text-[var(--lk-color-primary)]`);
- de **`MeldingBanner` `info`-variant**: een **blauwe ℹ** (`text-[var(--lk-color-primary)]`);
- geselecteerde tab, en de plek-stand "gedekt via" (`primary-700`).

**Is een tikbaar teken in blauw consistent?** Op zich wél — het gedraagt zich als link naar uitleg, en
blauw ís de interactie-/linkkleur. **Maar het is niet onderscheidend:** exact datzelfde blauw draagt al
de "tikbaar-info"-affordance (de "i" en de ℹ). Een blauw "!" is in kleur **niet te onderscheiden** van de
blauwe "i" die er al staat. Blauw is dus "vrij van betekenisconflict met waarschuwing", maar **bezet als
info-/link-teken** — precies de rol die het nieuwe teken wil spelen.

---

## Blok 3 — De bestaande bouwsteen `VeldUitleg`

`VeldUitleg` (`modules/.../views/VeldUitleg.vue`) is precies het voorgenomen mechanisme:
- **Trigger:** een klein rond **"i"-knopje** (`h-5 w-5`, rond, rand, tekst `--lk-color-primary` = blauw)
  **achter het veldlabel**;
- **Teken:** de letter **"i"** (niet "!");
- **Kleur:** **blauw** (`--lk-color-primary`);
- **Gedrag:** opent op **klik én focus** een paneel met de veld-uitleg (+ optionele vuistregel + per-optie
  regels); sluit op **Escape / klik-buiten / herhaalde trigger**; **focus keert terug** naar de knop;
  volledig **toetsenbord-toegankelijk** (`<button>`, `aria-expanded`, `aria-controls`).

Het voorgenomen teken (tikbaar teken achter het label → uitleg, toetsenbedienbaar) is **functioneel
identiek** aan `VeldUitleg`. Daaruit volgt:

- **Een apart blauw "!"-component zou een tweede, parallelle implementatie zijn** van exact wat
  `VeldUitleg` al doet — in strijd met de n≥2-convergentieregel en de KERNLES ("leg een regel vast in een
  gedeelde bouwsteen"). Dat is een **bevinding, geen detail**.
- **Hergebruik ligt voor de hand:** de norm-informatie kan dóór `VeldUitleg` gedragen worden (het paneel
  zegt bv. "dit veld staat op de lat van je organisatie"), zónder een nieuw teken. Dan is er geen tweede
  affordance en geen botsing.
- **Het bekende opvolgpunt** (`VeldUitleg` draagt de gedeelde `popoverPositie.js` nog niet; eigen
  `absolute`-overlay, 75 views) **zit het hergebruik hier niet in de weg** — een norm-variant die op
  `VeldUitleg` leunt erft simpelweg dezelfde (nog niet omgebouwde) positionering; consistent, geen extra
  schuld. Het is een reden om `VeldUitleg` te hergebruiken (één plek om later te verbeteren), niet om er
  een tweede naast te bouwen.

---

## Blok 4 — Waar zou de aanduiding landen?

Op het **componentformulier** (`ComponentFormulier.vue`) — de plek waar de consultant invult. Koppeling
feit → formulierveld:

| Hard feit | Formulierveld op `ComponentFormulier` | Draagt al een blauwe "i"? |
|---|---|---|
| eigenaar | `eigenaar_organisatie_id` (eigenaar-picker) | **ja** (regel 392) |
| biv | `biv_beschikbaarheid` · `_integriteit` · `_vertrouwelijkheid` (3 selects) | **ja**, elk (regel 493) |
| levensfase | `levensfase` (select) | **ja** (regel 516) |
| bedoeling | `migratiepad` (select, label "Bedoeling") | **ja** (regel 516) |
| hosting | `hostingmodel` (select) | **ja** (regel 516) |
| **verantwoordelijke** | — géén formulierveld (roltoewijzing-sectie op het **detail**) | n.v.t. |
| **gebruikersgroep** | — géén formulierveld (`GebruikersgroepSectie` op het detail) | n.v.t. |
| **bedrijfsfunctie** | — géén invoerveld (sectie op het detail; wél een losse `VeldUitleg` op de form) | n.v.t. |
| **koppelingen** | — géén formulierveld (`KoppelingSectie` op het detail) | n.v.t. |
| **contract** | — géén formulierveld (`ContractSectie` op het detail) | n.v.t. |

**Het gat:** **vijf van de tien feiten hebben géén formulierveld** — de relationele feiten
(verantwoordelijke, gebruikersgroep, bedrijfsfunctie, koppelingen, contract) leven in **secties op het
componentdetail**, niet op het aanmaakformulier. Voor die vijf kan een teken-achter-het-veldlabel
**nergens staan**; het zou naar sectie-koppen op het detail moeten verhuizen — een andere plek dan het
voorgenomen "achter het veldlabel op het formulier".

**Hoeveel velden dragen het teken?**
- Bij de **platform-default** (verplicht: eigenaar · verantwoordelijke · biv · contract · koppelingen):
  alleen **eigenaar + biv (3 velden)** hebben een formulierveld → **~4 tekens** (verantwoordelijke,
  contract, koppelingen hebben er geen).
- Bij **alle tien verplicht**: eigenaar (1) + biv (3) + levensfase + bedoeling + hosting = **7 formulier-
  velden** met het teken (de overige 5 feiten hebben geen veld).

Zeven tekens op een formulier is op zich **rustig**. Het probleem is niet het aantal — het is dat elk van
die 7 velden **al een blauwe "i" draagt**, dus zou naast elke "i" een blauw "!" komen te staan.

---

## Blok 5 — Oordeel

**Nee, het blauwe uitroepteken kan niet zoals voorgesteld.** Niet omdat de glyph "!" bezet is (die is
vrij), maar omdat de **plek, de kleur en het gedrag** al volledig bezet zijn door `VeldUitleg`: op precies
de vijf norm-velden die een formulierveld hebben, staat al een **blauwe, tikbare "i" achter het label die
een uitlegpaneel opent** — een blauw "!" ernaast is daarvan een niet te onderscheiden tweeling (zelfde
kleur, zelfde plek, zelfde gedrag, alleen een andere letter), en zou bovendien een tweede parallelle
implementatie zijn van wat die bouwsteen al doet. Daar komt bij dat "let op" al in amber/rood ⚠ leeft, dat
er geen aparte info-blauw naast de link-blauw bestaat, en dat vijf van de tien feiten überhaupt geen
formulierveld hebben om op te landen.

Het **dichtstbijzijnde alternatief dat wél vrij is** (ter overweging, niet gekozen — dat doet Bert): de
norm-signalering **dóór de bestaande `VeldUitleg` laten dragen** (geen nieuw teken; het paneel/label van de
"i" vermeldt dat het veld op de lat staat), eventueel met een **onderscheidend niet-blauw, niet-⚠ accent**
als er tóch een apart zichtbaar merkteken gewenst is. En voor de vijf relationele feiten zonder
formulierveld is sowieso een **andere landingsplek** (de sectie-koppen op het detail) nodig, los van de
teken-keuze.

---

## Afsluiting

1. **Read-only — niets gewijzigd, niets gebouwd, niets gecommit.**
2. `git status`: de openstaande **4b-changeset is onaangeroerd**; alleen dit nieuwe meting-document is
   toegevoegd.
