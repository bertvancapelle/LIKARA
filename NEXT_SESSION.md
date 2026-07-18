# NEXT_SESSION.md — LIKARA V046

**Gegenereerd**: 2026-07-18
**Vorige build**: V045 → **V046**
**Branch**: master
**Laatste commit (code)**: `f8a9142` slice 4c (lat tijdens invullen) · `d748fcf` 4b (norm-beheerscherm) ·
`aaeeb15` 4a (verschoven lat) · `6a0931a` S1 (schoon geval) · `3e74a47` C1 (feit-brug)
**Laatste commit (docs)**: `0c7860d` LI045-patronen in skills · afsluiting: deze sessie-commit

> **Sessie LI045 — de gemeente legt haar eigen lat nu zélf, en het systeem schrijft nooit een keuze toe die niemand maakte.**
>
> Wat een gemeente ná LI045 kan dat ze vanochtend niet kon (gebruikerstaal):
> - **De beheerder legt en verzet de lat zelf** — een eigen "Migratienorm"-scherm waar hij per hard feit
>   aanzet of het meetelt om klaar te kunnen verklaren. Vóór hij opslaat leest hij **wat het raakt**
>   ("raakt 12 systemen, waarvan 1 eerder klaar verklaard") — een rustige voorspelling, geen blokkade.
>   Tot vanochtend kon alleen de seed de norm zetten; nu is het een gemeente-keuze met een moment en een
>   eigenaar.
> - **Een verschoven lat leest niet meer als een besluit van de consultant.** Verzet de beheerder de lat
>   ná een klaarverklaring, dan krijgt die verklaring een **neutraal** signaal ("sindsdien verplicht
>   gesteld — daar is hier nog niet naar gekeken"), niet de amber van een bewuste afwijking. Wat de
>   consultant destijds wél bewust accepteerde blijft amber; dragen beide, dan staan ze naast elkaar.
> - **De consultant ziet tijdens het invullen welke velden meetellen** — een rustige "i" bij het feit
>   zegt "telt mee om klaar te kunnen verklaren; opslaan kan wel zonder". En hij herkent de plek uit zijn
>   werkvoorraad: onder "Waarvoor gebruiken we het" staat nu het woord **"Bedrijfsfunctie"**.
> - **De demostaat toont eindelijk hoe "in orde" eruitziet** — één systeem dat volledig aan de lat
>   voldoet en géén signaal draagt, zodat een browsercheck kan bewijzen dat een signaal terecht wégblijft.
> - **Besloten, nog te bouwen:** de **Archiefwet** als hard componentfeit (ADR-053) — "valt hier
>   archiefwaardig materiaal onder?" — in de norm zoals eigenaar en contract.

---

## Vertrekpunt LI046 — welk gat voelt de gebruiker nu als eerste?

De consultant ziet nu **per feit** of het vastgesteld is (badges, de norm-"i"), maar er is nog **geen
scherm dat per systeem bundelt "alles wat dít systeem nog nodig heeft"**. Hij leest zijn werkvoorraad
feit-voor-feit, niet component-voor-component. Dát is het eerstvolgende gat — en het fundament ervoor
(`norm_status` + registratiegaten per component) staat er nu.

## Top-5 prioriteiten volgende sessie (LI046)

> **Functionele volgorde: eerst het overzicht dat de norm nú al kán dragen, dan de laatste MVP-feiten.**

1. **Open-punten-overzicht per component.** *Nu de norm per component leesbaar is welke feiten niet
   vastgesteld zijn, kan "alles wat dit systeem nog nodig heeft" eindelijk als één lijst bestaan.* Dit is
   waar de consultant het hardst "de weg kwijt" bleek. Start met een **mockup** (Bert beslist op beeld);
   fundament = `norm_status` + `registratiegaten` per component (geen schema).

2. **Archiefwet-feit bouwen (ADR-053).** *De norm-slices zijn nu geland — het feit kan erin.* Eén hard
   componentfeit "draagt dit systeem archiefbescheiden" (`ja` / `bewust geen` / `null` = niet gekeken),
   in de platform-default maar **niet** standaard verplicht (de tenant zet de lat zelf). Eigen enum-kolom
   op het component (géén "bewust geen"-relatie-mechanisme — dat is relatie-verankerd). Subknopen open;
   grond: `docs/adr/ADR-053_…`. Raakt schema (nieuwe kolom + migratie) → gate.

3. **Laatste MVP-laag op de functie-as (ADR-046 stuk 3 → 5 → 4).** *Maakt de MVP af; lag bewust ná gate 4.*
   Uitstap-stand op de gebruiksrelatie (`organisatiegebruik`, stuk 3) → afgeleide zwaarte-telling (stuk 5,
   nooit opgeslagen) → tranche (stuk 4). Grond: OPVOLGPUNTEN LI040/LI041-blokken, ADR-046.

4. **Dev-seed vertelt het volledige verhaal (L4).** *Het schone geval (S1) is er nu; het gate-3-verhaal
   nog niet.* Vul de seed zodat een verse DB óók koppelingen, "hier draait niets" en de noodoplossing
   toont — elke browsercheck leunt op de seed.

5. **Docs-hygiëne: README ADR-register bijwerken (049–053).** *De ADR-tabel loopt tot 048.* Klein; voeg
   049 (functievervulling) t/m 053 (Archiefwet) toe.

---

## Openstaande beslissingen

- **Reikwijdte norm-afwijking (B5/D4, besloten LI044).** De norm-afwijking is bewust **niet** samengevoegd
  met `klaar_met_afwijking` in de dashboardteller (twee semantisch verschillende afwijkingen). Uitbreiding
  naar een dashboard-/lijstsignaal is een **eigen, nog te nemen besluit** (ADR-052 §Reikwijdte).
- **Archiefwet-subknopen (ADR-053).** De vorm is besloten (eigen enum-feit); de subknopen (waar in de
  norm-UI, hoe de "bewust geen"-taal luidt, of het een default-verplicht wordt) zijn open.
- **Bewaartermijn buiten LIKARA (ADR-053 / horizon).** Een bewaartermijn volgt uit zaaktype × resultaat
  (Selectielijst) — géén component-veld. Vastgelegd als grens, niet als scope.
- **Beoordelingsgrondslag (post-MVP).** ADR-052 is de smalle MVP-voorloper; de volle gewogen waarde-norm
  blijft het grote post-MVP-spoor (OPVOLGPUNTEN LI043-1).

---

## Bekende risico's en aandachtspunten

- **Geen verstrengelde werktree** — alle LI045-bouw is per opdracht apart geland (`aaeeb15`, `d748fcf`,
  `f8a9142`, `6a0931a`, `3e74a47`, `0c7860d`). Schone start.
- **Suites groen:** backend 1159 passed / 2 skipped · frontend 1202 passed · vite build OK · css-build OK ·
  alembic 1 head (`0073`), 0 branches.
- **Norm-borging is per scherm** — een nieuw scherm dat norm-feiten toont heeft zijn **eigen** tellende
  test nodig; er is geen globale scan. Een sectie zonder `provide('normVerplicht')` toont stil geen
  aanduiding (OPVOLGPUNTEN LI045-2/3).
- **Open verificatie GEMMA** — of de publieke GEMMA Archi-repo méér functie↔proces-relaties draagt dan
  ons AMEFF-bestand (4% gemeten) staat nog open (OPVOLGPUNTEN LI045-5).

---

## Geleerde patronen deze sessie

Verankerd in de likara-skills (LI045-vastlegging, `0c7860d`), geen memory-duplicaat:
- **Nooit een besluit toeschrijven dat een mens niet nam** — verschoven lat (neutraal) vs. bewuste
  afwijking (amber); het verschil snapshot × live ís het signaal, geen extra opslag (ux §LI045).
- **Het sterretje is voor opslaan-blokkerend** — een genormeerd veld is geen verplicht veld (ux §LI045).
- **Eén aanduiding per feit, op het kleinste omvattende element** — feit-prop + tellende test (ux §LI045).
- **Hetzelfde feit heet overal hetzelfde, of de brug wordt zichtbaar** — ondertitel uit dezelfde
  labelbron; enkelvoud/meervoud is geen afwijking (ux §LI045).
- **Toon gevolgen vóór opslaan** — een rustige voorspelling, geen blokkade (ux §LI045).
- **Toets een referentiemodel op dekking vóór je erop bouwt** — lage dekking = nee (domeinmodel §LI045).
- **Een feit in de default; de verplichtstelling is een tenant-keuze** — kun je niet versmallen, dan niet
  standaard verplicht (domeinmodel §LI045; complementair aan W4).
- **De demostaat bevat het rustige eindbeeld** — geborgd met een test die het schone geval bewaakt
  (werkprotocol).
- **Vraag geen metadata over een gebeurtenis die in deze slice nog niet kan bestaan** (werkprotocol).
