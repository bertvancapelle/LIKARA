# ADR-052 — Tenant-norm voor harde componentfeiten + verrijkte migratieklaar-verklaring

| | |
|---|---|
| **Status** | Aanvaard — **slices 1–3 gebouwd** (`fae7593` norm-opslag/-toetsing · `626dc76` "bewust geen" · `7e2ff25` verrijkte klaarverklaring); **slice 4 (norm-beheerscherm) open**. Subknopen 1–5 besloten (zie onder). |
| **Datum** | 2026-07-17 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-027 (component-klaarverklaring — dit verrijkt haar) · ADR-013/016 (lifecycle-engine — ongemoeid) · ADR-035 (registratiegat-signalen) · ADR-028 (BIV/componentrol) · ADR-044/049 ("bewust niets" op de bedrijfsfunctie-plek) · ADR-006 (append-only audit) · OPVOLGPUNTEN L1a (ijkpunt) + LI043-1 (beoordelingsgrondslag) |
| **Grond** | `docs/Checkpoint-tenant-norm-harde-velden-en-klaarverklaring-V044.md` (read-only) |
| **Invariant (onschendbaar)** | **De checklist-score blijft de enige lifecycle-driver.** De tenant-norm én de klaarverklaring hangen *náást* de engine: ze gaten een menselijke verklaring, niet de machinale `lifecycle_status`. |

---

## Context / aanleiding

Vandaag betekent "migratieklaar" twee dingen die vaak samenvallen maar niet hetzelfde zijn:

- **De engine-status** `migratieklaar` (ADR-013/016): alle checklistvragen beantwoord én geen
  openstaande blokkade. Puur checklist-gedreven.
- **De menselijke klaarverklaring** (ADR-027): een coördinator/consultant verklaart een component
  klaar — engine-gescheiden, mag óók bij <100% scoring, met een reeds bestaand "afwijking"-begrip
  (klaar verklaard terwijl de checklist niet compleet is).

Wat ontbreekt: de gemeente kan niet vastleggen **welke feitelijke gegevens van een component bekend
moeten zijn** voordat het klaar verklaard mag worden. De checklist geeft inhoudelijk inzicht; de
*harde* feiten (eigenaar, BIV, koppelingen, contract, …) staan er los bij als read-only
registratiegat-signaal, zonder norm en zonder stem in de verklaring. Deze ADR sluit dat gat — met de
laagst mogelijke drempel, want inrichtingsdwang vooraf is precies wat LIKARA vermijdt.

## Besluit (kern)

1. **De tenant stelt per hard feit een norm: verplicht-ja/nee** ("moet dit bekend zijn voordat dit
   component migratieklaar verklaard mag worden?"). **MVP: geen weging** — alleen ja/nee. (De
   gewogen waarde-norm is een apart, groter spoor; zie §Verhouding.)

2. **"Compleet" = feit *vastgesteld*, niet veld *gevuld*.** Een verplicht feit telt pas als het een
   **echt antwoord** draagt. Daarmee tellen als *niet* vastgesteld: een leeg veld, een
   **sentinel-waarde** die "geen antwoord" betekent (bv. `hostingmodel = onbekend`), én — bij de
   relationele feiten — "er is nog nooit naar gekeken". Dit is de smalste, eerlijke vorm die de
   placeholder-val vermijdt zonder een volledige waarde-norm te bouwen.

3. **De norm dekt eigen velden én relationele feiten.** Naast eigen componentvelden (eigenaar,
   verantwoordelijke, BIV, hosting, levensfase, bedoeling, …) kan de tenant ook **koppelingen** en
   **contract/leverancier** verplicht stellen. Voor die relationele feiten is "nul" dubbelzinnig, dus
   krijgt de consultant een uitspreekbaar **"bewust geen"** — een volwaardig antwoord, streng
   onderscheiden van "nog niet gekeken" (dezelfde vorm als de "bewust niets"-bevinding op de
   bedrijfsfunctie-plek, ADR-044/049). **Voor de bedrijfsfunctie bestaat "bewust geen" al; voor
   koppelingen en contract nog niet — dat is nieuw bouwwerk in het MVP van deze norm.**

4. **De consultant verklaart; de norm is een lat, geen poort.** Het menselijk oordeel wint. De
   consultant ziet de checklist-status én de tenant-norm (welke verplichte feiten nog niet
   vastgesteld zijn) en verklaart op grond daarvan — inclusief het bewuste besluit *"niet alles is
   vastgesteld, maar dit is voldoende, ik verklaar het klaar."* De machine houdt niets tegen.

5. **Bevestiging alléén bij afwijking van de norm.** Verklaart de consultant klaar terwijl alle
   verplichte feiten vastgesteld zijn → **licht, geen drempel** (conform ADR-035/L1a: aandacht
   schaalt met gewicht). Ontbreekt er een verplicht feit → een **bevestiging die de openstaande
   feiten benoemt** en die de consultant **bewust accepteert** (of "eerst aanvullen" — geen
   doodlopend pad). De drempel hangt aan de **afwijking**, niet aan de handeling.

6. **Eén feit voedt het zichtbare badge én de log.** Het akkoord-met-open-feiten wordt vastgelegd op
   de klaarverklaring als een **snapshot van de openstaande verplichte feiten** + wie + wanneer.
   Daaruit leest:
   - het **badge** op het component ("klaar verklaard, maar N verplichte feiten open") — een **live
     her-afleiding** die vanzelf **dooft** zodra de consultant het feit alsnog vaststelt;
   - de **logregel** — een **bevroren snapshot** die blijft staan: *"consultant X kreeg deze open
     feiten voorgelegd en verklaarde toch klaar."*
   Beide uit **één norm-definitie**, maar tegen **verschillende peildata** (badge = nu; log = moment
   van akkoord). Dat onderscheid is bewust en mag niet vervlakken tot één van beide.

7. **Engine-grens (herbevestigd).** De norm gatet uitsluitend de **klaarverklaring** (die al
   engine-gescheiden is, ADR-027). Ze grijpt **niet** in het score-/lifecycle-/blokkade-schrijfpad.
   De engine-status `migratieklaar` blijft puur checklist-gedreven; de menselijke verklaring is de
   laag die de norm meeweegt. Twee waarheden, elk heel.

### L1a-uitzondering (expliciet)

L1a houdt vooruit-handelingen bewust licht. Klaar verklaren is normaal zo'n vooruit-handeling.
**Uitzondering:** klaar verklaren **terwijl verplichte feiten van de tenant-norm ontbreken** is geen
gewone vooruitgang maar het **bewust overrulen van de norm van de gemeente** — en verdient dáárom
het rijke, auditeerbare akkoord (besluit 5+6). De drempel zit in de afwijking, niet in het verklaren.
Deze uitzondering wordt hier expliciet vastgelegd zodat een latere sessie L1a niet leest als "klaar
verklaren is altijd licht" en het verantwoordingsmoment stil laat verdwijnen.

## Model / aanpak (indicatief — vorm belegd bij de bouw, ná deze ADR)

- **Norm-opslag:** een **tenant-scoped** vastlegging (per hard feit een verplicht-vlag) — de
  checklist is de enige tenant-eigen catalogus, dus dit is tenant-eigen data met het bestaande
  RLS-recept. Exacte vorm (eigen tabel vs. vlag-set) = subknoop 1.
- **"Vastgesteld"-leesbron:** één afleiding "welke verplichte feiten zijn niet vastgesteld op dít
  component" — bouwt voort op de bestaande per-component signaal-leesbron
  (`registratiegaten`/`badge_voor_component`), **uitgebreid** met de feiten die nu geen gat-signaal
  hebben (levensfase/bedoeling/complexiteit/prioriteit + de hostingmodel-sentinel) en met de
  "bewust geen"-bevinding voor koppelingen/contract.
- **"Bewust geen" voor koppelingen en contract:** een uitspreekbare bevinding per component
  (spiegel van de bedrijfsfunctie-"bewust niets"), zodat "geen koppelingen" een antwoord kan zijn.
- **Klaarverklaring-snapshot:** een kolom op de bestaande `component_klaarverklaring` die de
  openstaande-feiten-snapshot + peildatum vastlegt (de reden-dialog van `MigratiegereedheidSectie`
  toont al een open-vragen-caveat → natuurlijke plek voor de bevestiging).
- **Audit:** het rijkere besluit ("ter beoordeling gekregen, toch akkoord") landt via de
  klaarverklaring-kolom (echte kolom, want de audit vangt kolommen); ADR-006-keten ongemoeid.

## Invarianten

- **Engine onaangeroerd** — geen import van/schrijf naar lifecycle/score/blokkade vanuit de norm of
  de verklaring; dubbele engine-borging per slice (import-afwezigheid + live geen-mutatie).
- **Eén bron, meerdere ingangen** — badge en log lezen uit hetzelfde feit/dezelfde norm-definitie;
  nooit twee parallelle afleidingen die uiteen kunnen lopen.
- **De vorm bepaalt nooit de betekenis** — "leeg/sentinel/nooit-gekeken" ≠ "vastgesteld"; afwezigheid
  wordt nooit stil als antwoord gelezen. De consultant stelt vast.

## Gevolgen

- De gemeente kan haar eigen lat voor "migratieklaar" vastleggen, per feit, en toch op elk moment
  doorgaan met invullen — de norm blokkeert niets; ze weegt mee bij het verklaren.
- Een component dat écht geen koppelingen/contract heeft, kan compleet zijn (bewust geen), niet
  eeuwig "onvolledig".
- "Klaar verklaard met openstaande registratie" wordt een **zichtbaar, terug te lezen, bewust**
  besluit — het verschil tussen "het systeem liet iets door" en "een mens koos dit welbewust".
- Nieuw bouwwerk t.o.v. vandaag: de norm-opslag + -toetsing, de uitbreiding van de per-component
  leesbron, "bewust geen" voor koppelingen/contract, en de snapshot-kolom + bevestiging.

## Reikwijdte-keuze bij de bouw (B5, LI044 — besloten, niet in het oorspronkelijke besluit)

De norm-afwijking ("verplichte feiten niet vastgesteld") en het bestaande `klaar_met_afwijking`
("checklist niet compleet") zijn **twee semantisch verschillende afwijkingen** — ze worden **niet
samengevoegd in één dashboardteller** (dat zou misleiden; "twee waarheden, elk heel" — zie de
invariant). De norm-afwijking leeft daarom bewust **alléén als badge op het component**
(`MigratiegereedheidSectie`), niet in `dashboard_service.klaar_met_afwijking`. Uitbreiding naar een
dashboard-/lijstsignaal voor de norm-afwijking is een **eigen, nog te nemen besluit**, geen bijvangst
van deze ADR (likara-domeinmodel §LI041-kernregel, vierde toepassing).

## Subknopen — besloten bij de bouw (LI044)

1. **Norm-opslagvorm → BESLOTEN.** Eigen **tenant-scoped tabel `component_norm`** met het RLS-recept;
   één rij per (hard feit, verplicht-vlag). Geen vlag-set naast de componentconfig.
2. **Default-norm meeleveren → BESLOTEN.** LIKARA levert een verstandige platform-default mee:
   **eigenaar · verantwoordelijke · BIV · contract · koppelingen** verplicht (`DEFAULT_VERPLICHT`).
   Generiek voor elke tenant; een tenant die een feit niet hanteert zet het in zijn **eigen norm** uit
   (tenant-configuratie) — de default versmalt daar niet mee (likara-ux W4). Degradeert netjes: geen
   norm-rij = niet-verplicht.
3. **Welke feiten "hard" heten → BESLOTEN.** De kiesbare set = **10 harde feiten** (`HARDE_FEITEN`):
   eigenaar, verantwoordelijke, BIV, gebruikersgroep, bedrijfsfunctie, levensfase, bedoeling, hosting,
   koppelingen, contract. **`componentrol` valt af** (NOT NULL met vaste beginstand → nooit leeg →
   moot).
4. **Vorm van "bewust geen" → BESLOTEN.** Een **component-verankerde eigen tabel `component_bevinding`**
   met **dezelfde vorm** als de bedrijfsfunctie-"bewust niets" (die embedded in `functievervulling.
   geen_systeem` leeft). **Frontend geconvergeerd** → één `BewustGeenControl.vue` (2 consumenten:
   `ContractSectie`/`KoppelingSectie`); **opslag gespiegeld** (twee tabellen op dezelfde leest) tot een
   **derde drager** unificatie rechtvaardigt (n≥2 — likara-domeinmodel harde regel 8). Consistentie
   langs write-guard (409 `REGISTRATIE_BESTAAT`) + read "real wins"; de generieke `relatie_service`
   blijft onaangeroerd.
5. **Sentinel-lijst → BESLOTEN.** Kort en expliciet: **alleen `hostingmodel = onbekend`** telt als "niet
   vastgesteld". Uitbreidbaar wanneer een nieuw sentinel-veld bijkomt.

## Verhouding tot de beoordelingsgrondslag (OPVOLGPUNTEN LI043-1)

Deze ADR is de **smalle MVP-voorloper** van de grondslag: een **aanwezigheids-/vastgesteld-norm**
(ja/nee bekend), niet de volle **waarde-norm** (welke waarden tellen als juist). "Vastgesteld =
echt antwoord, sentinel telt niet mee" is bewust de eerste, smalste vorm van diezelfde waarde-norm,
zodat de latere gewogen grondslag hierop bouwt **zonder herbouw**. De grondslag zelf blijft het
grote post-MVP-ontwerpspoor.

## Bouw-fasering (indicatief, ná deze ADR)

De read-only feitenopname is gedaan (`docs/Checkpoint-tenant-norm-harde-velden-en-klaarverklaring-V044.md`).
Slices, elk met engine-onaangeroerd-borging + gate-discipline:
1. ✅ **Norm-opslag + -toetsing** (`component_norm`, tenant-scoped; de "vastgesteld"-leesbron uitgebreid) — **gebouwd `fae7593`**.
2. ✅ **"Bewust geen" voor koppelingen en contract** (`component_bevinding`, spiegel bedrijfsfunctie) — **gebouwd `626dc76`**.
3. ✅ **Verrijkte klaarverklaring** (snapshot-kolom `open_feiten` + bevestiging bij afwijking + badge/log uit één feit; slice 3b verantwoordingsvenster, 3c reden-achter-de-waarschuwing) — **gebouwd `7e2ff25`**.
4. ⏳ **Norm-beheerscherm** (de tenant stelt de verplicht-vlaggen in) + optionele default-norm — **OPEN** (LI045-prioriteit 1).
