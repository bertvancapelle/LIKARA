# SESSIESTART — LIKARA V045

**Datum**: 2026-07-18
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V045 — [N] skills geladen"
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

# SESSIE_BRIEFING.md — LIKARA V045

**Gegenereerd**: 2026-07-18

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V045 |
| Datum | July 2026 |
| Commit | f0fa9bd |
| Tests | backend 1149 passed / 2 skipped · frontend 92 files / 1175 passed · vite build OK · css-build OK |
| TST-rapport | TST-V045-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
f0fa9bd [docs] LI044-patronen vastgelegd in skills + opvolgpunt VeldUitleg-overlay
7e2ff25 [frontend][backend] ADR-052 slice 3 — verrijkte migratieklaar-verklaring — ADR-052
626dc76 [backend+frontend] ADR-052 slice 2 — "bewust geen" voor koppelingen en contract
fae7593 [backend] ADR-052 slice 1 — tenant-norm harde feiten: opslag + default + vastgesteld-leesbron
8a9ea3d [docs] ADR-052 tenant-norm harde feiten + migratieklaar-verklaring (met checkpoint)
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V045

**Gegenereerd**: 2026-07-18
**Vorige build**: V044 → **V045**
**Branch**: master
**Laatste commit (code)**: `7e2ff25` ADR-052 slice 3 (verrijkte klaarverklaring) · daarvóór `626dc76`
slice 2 ("bewust geen") · `fae7593` slice 1 (norm-opslag) · `c82ad80` gate-4 sloop
**Laatste commit (docs)**: `f0fa9bd` LI044-patronen in skills + opvolgpunt VeldUitleg-overlay

> **Sessie LI044 — de gemeente kan nu haar eigen lat voor "migratieklaar" leggen; het procesregister is uit de MVP-UI.**
>
> Wat LI044 heeft opgeleverd (gebruikerstaal):
> - **Gate-4 sloop.** Het procesregister is uit de MVP-UI gehaald (nav, routes, ProcesLijst/ProcesDetail
>   + secties, PartijProcessenSectie, ComponentProcessenSectie, de kaart proces-ingang en de doodlopende
>   "Bekijk op kaart"). Datamodel, bouwstenen (procesBoom/ProcesDiagram) en slapende endpoints blijven;
>   het concept is geparkeerd (ADR-043), niet verwijderd.
> - **Tenant-norm voor harde componentfeiten (ADR-052, slices 1–3).** De gemeente kan per hard feit
>   vastleggen dat het bekend moet zijn vóór een component migratieklaar verklaard mag worden. "Vastgesteld"
>   = een echt antwoord (leeg/sentinel/nooit-gekeken tellen niet). Voor koppelingen/contract is er nu een
>   uitspreekbaar **"bewust geen"**. De consultant verklaart; de norm is een **lat, geen poort**.
> - **Verrijkte klaarverklaring.** Klaar verklaren blijft licht — behalve bij **afwijking van de norm**:
>   dan benoemt een bevestiging de open feiten (bewust akkoord óf "eerst aanvullen"). Het component toont
>   een **live badge**; de klaarverklaring bevriest een **snapshot** (wie/wanneer/welke feiten open). De
>   amber waarschuwing is **klikbaar** → verantwoordingsvenster met de reden + stand-bij-het-besluit; de
>   reden staat niet meer permanent bij de status. Een venster valt nooit meer buiten beeld.
> - **Borging:** ADR-052 teruggevouwen naar de gebouwde realiteit; LI044-patronen vastgelegd in vijf
>   skills; ADR-045 besluit 2 / "fileshare = gat" gemarkeerd als verworpen (ADR-051 besluit 3).

---

## Top-5 prioriteiten volgende sessie (LI045)

> **Functionele volgorde: maak eerst af wat je begon (de norm bruikbaar maken), dán de volgende waardelaag.**

1. **Slice 4 — norm-beheerscherm.** *De beheerder kan de norm nu niet zien of aanpassen; alleen de seed
   zet hem.* Elke tenant zit vast aan de default (eigenaar · verantwoordelijke · BIV · contract ·
   koppelingen) — BvoWB kan BIV pas uitzetten als dit scherm er is. **Maakt ADR-052 af.** Raakt geen
   schema (norm-tabel `component_norm` bestaat); UI + toets + optionele default-norm-actie.

2. **Open-punten-overzicht per component.** *Nu de norm bestaat en per component leesbaar is welke feiten
   niet vastgesteld zijn, kan "alles wat dit systeem nog nodig heeft" eindelijk betekenis dragen.* Het
   fundament staat (`norm_status` + `registratiegaten`); dit is waar de consultant het hardst "de weg
   kwijt" bleek. Start met een mockup (Bert beslist op beeld).

3. **Laatste MVP-laag op de functie-as (ADR-046 stuk 3 → 5 → 4).** *Maakt de MVP af; lag bewust ná gate 4.*
   Uitstap-stand op de gebruiksrelatie (`organisatiegebruik`, stuk 3) → afgeleide zwaarte-telling (stuk 5,
   nooit opgeslagen) → tranche (stuk 4). Grond: OPVOLGPUNTEN LI040/LI041-blokken, ADR-046.

4. **Dev-seed vertelt het volledige verhaal (L4).** *Elke browsercheck leunt op de seed.* Norm en "bewust
   geen" zitten er nu in, maar het gate-3-verhaal (koppelingen, "hier draait niets", de noodoplossing) is
   op een verse DB nog onzichtbaar. Vul de seed zodat een verse DB het hele verhaal toont.

5. **VeldUitleg adopteert `popoverPositie.js`.** *Rekenkern is gedeeld, 75 views dragen hem nog niet → de
   borging is niet af* (KERNLES: elk pad moet de regel dragen). Klein/eigen slice; regressierisico
   (in-flow `absolute` → `fixed`/viewport-klem over 75 views) benoemen; browserverificatie over meerdere
   schermen. Zie OPVOLGPUNTEN + likara-frontend §Overlay-positionering.

---

## Openstaande beslissingen

- **Reikwijdte norm-afwijking (B5, besloten deze sessie).** De norm-afwijking is bewust **niet**
  samengevoegd met `klaar_met_afwijking` in de dashboardteller (twee semantisch verschillende
  afwijkingen). Uitbreiding naar een dashboard-/lijstsignaal voor de norm-afwijking is een **eigen, nog
  te nemen besluit** (ADR-052 §Reikwijdte-keuze).
- **Contract-analyse (notitie klaar, geen besluit).** A1 afgeleide contract-afloop-leeslaag · A2
  spiegelsignaal "component zonder contract" · B1 verantwoordelijkheid/toelichting op contract (skills
  LI038, besloten niet gebouwd). Bedrag/administratie buiten scope. Bron: `docs/Analyse-contractregistratie-V040.md`.
- **Beoordelingsgrondslag (post-MVP).** ADR-052 is de smalle MVP-voorloper (aanwezigheids-/vastgesteld-norm);
  de volle gewogen waarde-norm blijft het grote post-MVP-ontwerpspoor (OPVOLGPUNTEN LI043-1).

---

## Bekende risico's en aandachtspunten

- **Geen verstrengelde werktree** — alle LI044-bouw is per opdracht apart geland (`c82ad80`, `fae7593`,
  `626dc76`, `7e2ff25`, `f0fa9bd`). Schone start.
- **Suites groen:** backend 1149 passed / 2 skipped · frontend 1175 passed · vite build OK · css-build OK ·
  alembic 1 head (`0073`), 0 branches.
- **Slice 4 vóór verdere norm-uitbreiding** — zolang de norm alleen via de seed te zetten is, kan een
  browsercheck de norm-varianten niet zonder reseed tonen (zie L4/dev-seed).

---

## Geleerde patronen deze sessie

Verankerd in de likara-skills (LI044-vastlegging, `f0fa9bd` + deze afsluiting), geen memory-duplicaat:
- **Vastgesteld = een echt antwoord** (leeg/sentinel/nooit-gekeken tellen niet); **geen norm = geen eis**
  (domeinmodel §Norm & vastgesteld).
- **"Bewust geen"** = write-guard (409) + read "real wins", generieke relatie-service onaangeroerd
  (domeinmodel §Registratie-feiten).
- **De drempel hangt aan de afwijking, niet aan de handeling** — uitzondering op L1a (ux).
- **Eén norm-definitie, twee peildata** — signaal leeft / snapshot bevriest; de snapshot mag opgeslagen als
  audit van een wilsbesluit, niet als afgeleide waarde (ux).
- **Een venster valt nooit buiten beeld** — gedeelde `popoverPositie.js`, rekenkern puur + unit-getest
  (frontend + tests).
- **Vorm convergeert eerder dan schema** — UI bij n=2, opslag pas bij de derde drager (domeinmodel harde regel 8).
- **Een tenant-wens versmalt nooit de platform-default** (ux).


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V045"
4. Wacht op START: [naam] van Bert

