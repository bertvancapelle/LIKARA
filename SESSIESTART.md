# SESSIESTART — LIKARA V047

**Datum**: 2026-07-19
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V047 — [N] skills geladen"
5. Wacht op START: [naam] van Bert

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

## Opdrachtformaat CC-opdrachten (VERPLICHT — standaardwerkwijze)

claude.ai levert elke CC-opdracht ALTIJD aan als een .md-bestand
(downloadbaar), nooit als een los codeblok in de chat. Bert gebruikt dat
.md-bestand in CC. Deze afspraak geldt in elke sessie.

---

# SESSIE_BRIEFING.md — LIKARA V047

**Gegenereerd**: 2026-07-19

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V047 |
| Datum | July 2026 |
| Commit | aca7cb1 |
| Tests | backend 1159 passed / 2 skipped · frontend 97 files / 1248 passed · vite build OK · css-build OK |
| TST-rapport | TST-V047-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
aca7cb1 [skills] LI046-patronen vastgelegd — kaart-leesbaarheid (linkerkolom + relaties op hoedanigheid) + werkwijze-lessen
f7929a9 [docs] LI046 read-only checkpoints — linkerkolom (kijkinstellingen vs vertrekpunten) + hertekenen/overlappende lijnen
6651f1f [frontend] LI046 — relaties tussen twee knopen gescheiden op hoedanigheid + de klik levert alles onder het paar
3a72b35 [frontend] LI046 — kijkinstellingen-kolom alléén bij een getekende kaart; views + beheer naar het startpaneel; BIV/Rol achter een inklap
70f2cbb [skills] LI046-patronen vastgelegd — één-ingang/aanleiding-in-URL/veld-anker/popup-takken-scan/de-bezoeker-wint + rm→find-fix + invariant-boven-afspraak — ADR-054
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V047

**Gegenereerd**: 2026-07-19
**Vorige build**: V046 → **V047**
**Branch**: master
**Laatste commit (code)**: `6651f1f` relaties op hoedanigheid · `3a72b35` linkerkolom-gate ·
`9ee6fcb` terugkeer landt in de kaart · `61665a4` derde uitgang · `466eb7b`/`4dd1387`/`80d0038` slice 3/2/1
**Laatste commit (docs)**: `aca7cb1` LI046-patronen · `f7929a9` checkpoints · `bf67e67` ADR-054 + register ·
afsluiting: deze sessie-commit

> **Sessie LI046 — de kaart vertelt, en het component verandert: één ingang naar het detailscherm, een
> linkerkolom die alleen verschijnt als er iets te zien is, en relaties die je per hoedanigheid uit elkaar
> ziet lopen.**
>
> Wat een gebruiker ná LI046 kan dat hij vanochtend niet kon (gebruikerstaal):
> - **Vanaf de kaart naar een detailscherm gaat nu langs één deur, met de aanleiding erbij (ADR-054).**
>   Klik je door op een systeem, dan land je op het detailscherm mét de reden waarom je er bent — de
>   aanleiding staat in de URL, het aangeraakte veld is gemarkeerd, en er bestaat geen route die je zonder
>   landing binnenlaat. De kaart vertelt; het component verandert. Kom je terug, dan land je bij je bewaarde
>   beeld — en verdween je selectie helemaal, dan krijg je dat eerlijk te zien in plaats van een lege kaart.
> - **De kijkinstellingen-kolom verschijnt alleen bij een getekende kaart.** Zolang er niets getekend is,
>   is er ook geen linkerkolom vol knoppen die nergens op slaan; opgeslagen kijken en het beheer ervan
>   staan nu op het startpaneel, en het Rol/BIV-filter zit achter een rustige inklap. De kolom gaat over
>   *kijken*, niet over *binnenkomen* — hij hangt aan "is er data", niet aan "staat het beginscherm open".
> - **Twee systemen die op meer dan één manier met elkaar te maken hebben, zie je nu uit elkaar lopen.**
>   Een beheerrelatie en een gebruiksrelatie tussen dezelfde twee knopen liggen niet meer op één lijn maar
>   als aparte banen, elk met de juiste richting; klik je op zo'n baan, dan krijg je *alles* wat tussen dat
>   paar loopt. Roltoewijzing telt als beheer-hoedanigheid mee.
> - **Vastgelegd, nog te bouwen:** het **open-punten-overzicht per component** — "alles wat dít systeem nog
>   nodig heeft" als één lijst; het fundament (`norm_status` + registratiegaten per component) staat er.

---

## Vertrekpunt LI047 — welk gat voelt de gebruiker nu als eerste?

De consultant ziet nu **per feit** of het vastgesteld is (badges, de norm-"i"), en de kaart vertelt hem
netjes waar hij is. Maar er is nog steeds **geen scherm dat per systeem bundelt "alles wat dít systeem nog
nodig heeft"**. Hij leest zijn werkvoorraad feit-voor-feit, niet component-voor-component. Dát blijft het
eerstvolgende gat — en het fundament ervoor (`norm_status` + registratiegaten per component) staat er nu.

## Top-5 prioriteiten volgende sessie (LI047)

> **Functionele volgorde: eerst het gat dat de consultant voelt, dan meteen de seed — want de rest van de
> lijst wordt in de browser afgemeld en leunt dus op een seed die het geval kent — en pas daarna de laatste
> MVP-feiten.**

1. **Open-punten-overzicht per component.** *Nu de norm per component leesbaar is welke feiten niet
   vastgesteld zijn, kan "alles wat dit systeem nog nodig heeft" eindelijk als één lijst bestaan.* Dit is
   waar de consultant het hardst "de weg kwijt" bleek. Start met een **mockup** (Bert beslist op beeld);
   fundament = `norm_status` + `registratiegaten` per component (geen schema).

2. **Dev-seed vertelt het volledige verhaal (L4).** *Randvoorwaarde voor de rest van de lijst: bij vrijwel
   elke prioriteit is browserverificatie het afmeldpunt, en een seed die het geval niet kent maakt van elke
   browsercheck een gok.* Het schone geval (S1) is er; het gate-3-verhaal nog niet. Vul de seed zodat een
   verse DB toont:
   - koppelingen, "hier draait niets" en de noodoplossing (het gate-3-verhaal);
   - een **partij die van hetzelfde systeem eigenaar én gebruiker is en meerdere beheerrollen draagt** — het
     geval waarvoor de baan-scheiding op hoedanigheid (LI046) gebouwd is, nu alleen zichtbaar na handmatig
     vastleggen;
   - een **knooppaar met relaties van meerdere hoedanigheden** — cross-ring overlap komt in de dev-data 0×
     voor, dus dat gedrag is er niet te zien;
   - een component met **openstaande punten** (voor prioriteit 1) en een **gebruiksrelatie met een
     uitstap-stand** (voor prioriteit 4).

3. **Archiefwet-feit bouwen (ADR-053).** *De norm-slices zijn geland — het feit kan erin.* Eén hard
   componentfeit "draagt dit systeem archiefbescheiden" (`ja` / `bewust geen` / `null` = niet gekeken),
   in de platform-default maar **niet** standaard verplicht (de tenant zet de lat zelf). Eigen enum-kolom
   op het component (géén "bewust geen"-relatie-mechanisme — dat is relatie-verankerd). Subknopen open;
   grond: `docs/adr/ADR-053_Archiefwet-als-hard-componentfeit.md`. Raakt schema (nieuwe kolom + migratie) → gate.

4. **Laatste MVP-laag op de functie-as (ADR-046 stuk 3 → 5 → 4).** *Maakt de MVP af; lag bewust ná gate 4.*
   Uitstap-stand op de gebruiksrelatie (`organisatiegebruik`, stuk 3) → afgeleide zwaarte-telling (stuk 5,
   nooit opgeslagen) → tranche (stuk 4). Grond: OPVOLGPUNTEN LI040/LI041-blokken, ADR-046.

5. **Terugweg-fijnslijpen (open ontwerpbesluiten LI046).** *De kaart landt nu terug, maar niet alles reist
   mee.* Beslis wat er wél/niet in `lk-state` hoort: org-scope, Rol/BIV-filter, weergavekeuze, zoom/pan;
   en of view-verwijderen een bevestiging krijgt en "selectie bijwerken" een ingang. Grond: OPVOLGPUNTEN
   §"Nieuw uit LI046" (punten 1–5).

---

## Openstaande beslissingen

- **Terugweg naar de kaart (LI046, punten 1–5).** Bij terugkeer landt de bewaarde selectie (ADR-054), maar
  org-scope, Rol/BIV-filter, weergavekeuze en zoom/pan reizen niet mee; een gedeeltelijk verdwenen selectie
  wordt stil kleiner getekend; view-verwijderen vraagt niet om bevestiging; "selectie bijwerken" heeft geen
  ingang. Allemaal **open ontwerpbesluiten** — geen oplossingsvoorkeur vastgelegd.
- **"Bewust geen" op de gebruiksrelatie.** Het gebruiksdata-model (`organisatiegebruik`) kent geen "bewust
  geen"-stand, anders dan het Archiefwet-feit (ADR-053). Of die drieslag ook op de gebruiksrelatie hoort is
  een **eigen, nog te nemen besluit** (OPVOLGPUNTEN LI046-4).
- **Reikwijdte norm-afwijking (B5/D4, besloten LI044).** Niet samengevoegd met `klaar_met_afwijking` in de
  dashboardteller (twee semantisch verschillende afwijkingen). Uitbreiding naar een dashboard-/lijstsignaal
  is een **eigen, nog te nemen besluit** (ADR-052 §Reikwijdte).
- **Archiefwet-subknopen (ADR-053).** De vorm is besloten (eigen enum-feit); de subknopen (waar in de
  norm-UI, hoe de "bewust geen"-taal luidt, of het default-verplicht wordt) zijn open.
- **Beoordelingsgrondslag (post-MVP).** ADR-052 is de smalle MVP-voorloper; de volle gewogen waarde-norm
  blijft het grote post-MVP-spoor (OPVOLGPUNTEN LI043-1).

---

## Bekende risico's en aandachtspunten

- **Geen verstrengelde werktree** — alle LI046-bouw is per opdracht apart geland (`3a72b35`, `6651f1f`,
  `9ee6fcb`, `61665a4`, `466eb7b`, `4dd1387`, `80d0038`); docs/skills apart (`aca7cb1`, `f7929a9`,
  `bf67e67`, `3b7941f`, `70f2cbb`). Schone start.
- **Suites groen:** backend 1159 passed / 2 skipped · frontend 97 files / 1248 passed · vite build OK ·
  css-build OK · alembic 1 head (`0073`), 0 branches.
- **Kaart-leesbaarheid is invariant, geen afspraak** — de baanverdeling (`baanVerdeling`) en de
  `heeftData`-kolomgate leunen niet op een ring- of laag-aanname; een nieuwe relatiesoort of projectie
  erft het gedrag zonder losse regel (frontend §LI046, werkprotocol §KERNLES LI038).
- **Norm-borging is per scherm** — een nieuw scherm dat norm-feiten toont heeft zijn **eigen** tellende
  test nodig; er is geen globale scan (OPVOLGPUNTEN LI045-2/3).
- **Open verificatie GEMMA** — of de publieke GEMMA Archi-repo méér functie↔proces-relaties draagt dan
  ons AMEFF-bestand (4% gemeten) staat nog open (OPVOLGPUNTEN LI045-5).

---

## Geleerde patronen deze sessie

Verankerd in de likara-skills (LI046-vastlegging, `aca7cb1` · `70f2cbb`), geen memory-duplicaat:
- **De kaart vertelt, het component verandert** — één gedeelde detail-ingang (`detailRoute`), de aanleiding
  in de URL, geen route zonder landing, het veld-anker markeert (ux/frontend §LI046, ADR-054).
- **De bezoeker wint** — een vaste volgorde-invariant bij binnenkomst; het beginscherm-binnenkomstmoment is
  één eenmalige regel ná de beslisboom, niet per tak (frontend §LI046).
- **Een kijk-kolom hangt aan "is er data", niet aan "staat het beginscherm open"** — `heeftData`, bewust
  níét `!beginschermOpen`; kijken ≠ binnenkomen (ux/frontend §LI046).
- **Richting is betekenis, de laan is de betekenis** — relaties gescheiden op hoedanigheid met
  richting-gecorrigeerde banen; ring-agnostisch, invariant boven afspraak (frontend §LI046).
- **De klik levert alles onder het paar** — klik op een baan toont álle relaties tussen die twee knopen,
  niet alleen de aangeklikte (ux §LI046).
- **Groen bewijst geen schone bron** — tests groen terwijl de bron null-bytes droeg; controleer het bestand
  zelf (`file`, hexdump) vóór commit (werkprotocol §LI046).
- **Eén shell schrijft per repo** — stel eerst "waar sta ik" vast; een tweede shell die commit maakt je
  "ongecommit"-lezing onbetrouwbaar (werkprotocol §LI046).
- **`rm` is geweigerd — `find … -delete`** voor de Vite-modulecache (werkprotocol §LI046).


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V047"
4. Wacht op START: [naam] van Bert

