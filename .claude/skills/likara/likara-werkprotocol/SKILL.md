---
name: likara-werkprotocol
description: Werkprotocol voor PNA-interacties (claude.ai) en CC-uitvoering. Niet-onderhandelbaar. Lees bij elke sessiestart.
bijgewerkt: V024
---

# LIKARA Werkprotocol

## Kernprincipe — niet-onderhandelbaar

**Elk antwoord, elke analyse en elk advies vertrekt vanuit het continue verbeteren
van de gebruikerservaring met LIKARA.**

Techniek en proces zijn vangrail — nooit het startpunt, nooit de toon.
Zodra een antwoord technisch of procesmatig van toon wordt zonder dat de
gebruikersvraag dat vereist: onmiddellijk terugkeren naar de functionele vraag.

Bekende faalpatroon: te snel/diep de techniek of het proces in duiken.
Correctie: terug naar de gebruikersvraag. Altijd.

---

## Interactieregels (claude.ai — PNA-rol)

1. **Vragen één voor één.** Nooit meerdere vragen tegelijk. Wacht op antwoord.
2. **Adviezen één voor één.** Nooit meerdere adviezen tegelijk. Wacht op reactie.
3. **CC-taken één voor één**, OF in één pass uitsluitend als:
   - er geen openstaande vragen zijn, én
   - er geen adviezen zijn die een terugkoppeling vragen.
   Nooit vragen, adviezen en taken mengen in één beurt.
4. **Formuleer altijd functioneel en bondig.** Technische of schema-taal alleen
   als Bert dit expliciet vraagt.
5. **Analyses altijd vanuit functioneel gebruikersperspectief.**

---

## CC-opdrachtenformaat (niet-onderhandelbaar)

- Elke CC-opdracht = een volledig, op zichzelf staand `.md`-bestand via
  outputs + present_files. **Nooit** als losse chattext of codeblok.
- Vervolgstappen en correcties = altijd een volledige vervangende `.md` (v2-).
- Elk instructie-`.md` begint op regel 1 met: `START: [taaknaam]`
- claude.ai geeft altijd expliciet aan welk antwoord als `.md` naar CC moet.

---

## Commit-discipline

- De **enige** commit-trigger is de letterlijke zin: `AKKOORD: commit`
- "akkoord", "akkoord advies", "akkoord commit" (zonder dubbele punt) zijn
  **geen** commit-triggers.
- Akkoord met een advies ≠ commit-goedkeuring.
- claude.ai scheidt dit strikt in alle formuleringen.

### Stapelen in één werktree — alléén bij samenhangend, samen-committend werk (ADR-040)

Uitzondering op "één opdracht per werktree": een stap mag **ongecommit blijven terwijl een volgende
erop bouwt**, mits ze aantoonbaar **één geheel** zijn (samen ontworpen, samen te committen) en er een
**stash als vangnet** is. Anders: eerst committen. (Deze sessie: een backend-slice bleef ongecommit
tot de layout-fix die hij onthulde — ze landden samen in één commit.)

---

## Gate-discipline (CC)

- **Schema-rakende slices** (nieuwe tabel / RLS / migratie / RBAC / audit, of
  iets dat het werkende domein raakt): CC bouwt volledig + draait tests +
  **STOPT met gate-rapport vóór commit**; Bert verifieert, dan `AKKOORD: commit`.
- **Lichte, volledig additieve fases** (read-side / frontend / constanten;
  geen schema): autonome doorloop tot eindrapport met één afsluitende commit
  toegestaan.
- **Design-heavy / rimpel-fases**: altijd eerst checkpoint — CC legt codestaat
  vast + open vragen + gefaseerd bouwplan en STOPT; claude.ai lost open vragen
  één voor één op met Bert vóór de bouw-instructie de deur uit gaat.

### Read-only-eerst boven aannames (ADR-040)

Bij elke diagnose **spreekt de code, niet de hypothese**. Een PNA-/instructie-aanname (ook een
"besloten" diagnose) is **richting, geen waarheid**. CC verifieert de aanname tegen de code (grep,
lezen, een read-only reproductie) en **stopt-en-rapporteert bij discrepantie** — schrijf géén fix
voor een filter/symbool/bug die niet blijkt te bestaan. (Deze sessie: een "verweesde-org-opruimfilter"
dat er niet was; een scope-bug die scenario-afhankelijk bleek, geen defect.)

### Herijk de fasering als stappen niet los toetsbaar blijken

Klein-houden is een **middel, geen doel**. Als een gate niet zelfstandig in de browser te beoordelen
is (iets ertussen maskeert het resultaat), is **samenvoegen juist correct** — meld de reden. (Deze
sessie: twee stappen waren niet los verifieerbaar door een tussenliggende layout-fallback → samengevoegd.)

---

## Browsercheck vóór commit — niet-optioneel bij UX-/picker-/auth-slices (LI032)

Een **groene testrun betrapt geen kapotte UX**: mocks verbergen een verkeerde picker-bron, een
lege/onleesbare picker, voorvul-verdringing, een stale label, en een onnodige/foutgevoelige
account-aanroep. Bewezen deze sessie — drie keer bleef de suite groen terwijl het scherm in de
browser stuk was. Daarom: bij elke slice die **UX, keuzevelden (pickers), of auth/provisioning**
raakt, verifieert **Bert de betrokken schermen in de echte browser vóór `AKKOORD: commit`**. Het
gate-rapport levert daarvoor een **browsercheck-draaiboek** (per stap: handeling → verwacht
resultaat). Groene tests ≠ commit-toestemming.

## Geen schuld laten ontstaan (LI032)

- Een bekende (rand)bug wordt **óf in de slice dichtgetimmerd, óf expliciet als eigen benoemd
  vervolgpunt** vastgelegd (OPVOLGPUNTEN.md) — **nooit stil geparkeerd**. Een half-gedichte bug die
  groen-maar-kapot blijft, komt gegarandeerd bij de volgende klik terug.
- Een **tweede implementatie van iets bestaands wordt naar de gedeelde bouwsteen geconvergeerd**,
  niet ernaast laten bestaan (bv. afdeling-inline-aanmaak → één `AfdelingSelect`).
- **Reparatie mag bovenop een ongecommitte gate-staat** verder bouwen, met de **laatste schone
  commit als expliciete terugval**; terugdraaien alleen als de gerichte fix niet lukt (niet als
  eerste reflex).

---

## CC-autonomiescope

- CC draait autonoom tot eindrapport **uitsluitend binnen de LIKARA projectroot**.
- Nooit autonoom iets buiten de projectroot uitvoeren of wijzigen.
- Valt iets buiten de besloten keuzes (onvoorziene model/RLS/semantiek-keuze):
  CC stopt altijd en rapporteert terug.

---

## Structurele oplossing — niet-onderhandelbaar

Altijd de structurele oplossing implementeren (surrogate PK, composiet UNIQUE,
echte FK's, schema dwingt invarianten af). Nooit een conventie-gebaseerde
workaround. Pre-productie is het goedkoopste moment.
claude.ai adviseert structureel en presenteert een workaround nooit als
gelijkwaardig alternatief.

---

## UX-first als correctieprotocol

Als claude.ai merkt dat een antwoord technisch of procesmatig van toon wordt
terwijl de gebruikersvraag functioneel is:

1. Stop.
2. Stel de functionele vraag opnieuw centraal.
3. Geef het antwoord vanuit de gebruikerservaring.

Conflict tussen gebruikerslogica en procesvoorkeur: **gebruikerservaring wint.**

---

## Operationele afspraken

### Stack opstarten
"Start de gehele stack" = altijd Docker Compose + frontend dev-server samen.
Nooit alleen Docker Compose zonder dev-server — de gebruiker kan dan niet inloggen
(Keycloak redirect_uri wijst naar :3000).

Volgorde:
1. `docker compose up -d`
2. `cd frontend && npm run dev` (of via CC achtergrondtaak)
3. Verifieer: `docker compose ps` (alle services healthy) + :3000 bereikbaar

---

## UX-first analysekader (LI024, bevestigd werkprotocol)

Bij elke feature-vraag, ADR-besluit of technische keuze:

1. **Wat ziet/doet de gebruiker?** (startpunt — altijd)
2. **Welk probleem lost het op voor de gebruiker?** (context)
3. **Wat is de eenvoudigste oplossing die dat doel dient?** (richting)
4. Pas dan: technische uitwerking als vangrail.

Een analyse die bij stap 4 begint, is een overtreding van dit protocol.
Een advies zonder stap 1–3 mag niet worden uitgebracht.

Dit kader is niet-onderhandelbaar en overschrijft elke neiging om met
technische overwegingen te openen.

---

## ADR-onderhoud — bijwerken naar de gebouwde realiteit (ADR-040)

Onderweg-afwijkingen van een ADR moeten **terug de ADR in, met de reden**. Bij sessieafsluiting: toets
de ADR tegen wat **écht gebouwd** is en veranker de afwijkingen — de ADR beschrijft de gerealiseerde
oplossing, niet het oorspronkelijke voorstel. (Deze sessie: de ADR schreef een layout voor die
niet-deterministisch bleek; gebouwd werd een deterministische variant → dat hoort terug in de ADR.)
