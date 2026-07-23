# NEXT_SESSION.md — LIKARA V051

**Gegenereerd**: 2026-07-23
**Vorige build**: V050 → **V051**
**Branch**: master
**Laatste commits (LI050)**: `9d6adfc` werkprotocol bronplicht+afsluitregel · `2dc5592` checkpoint
productie-gereedheid · `181fa75` vraagbeheer beheerder-only (ADR-022 W2) · `4a452d8` categorie als
entiteit + indeling + code systeem-toegekend (W3/W4, migratie 0074) · `ca6b063` engine: uitgezette
vraag telt niet mee (actieve_vraag) · `ac3b92f` vraag-volgorde + sleep-bouwsteen (W5, migratie
0075) · `e304955` ADR-056 vraagevolutie + checkpoint-grond · `6ab1960` vraagbeheer-UX
(leesbaar/bedienbaar + optie-sleep-fix + wachters) · `e6c4cec` rechtenanalyse-rapport

> **Sessie LI050 — het vraagbeheer is van de beheerder, leesbaar, en bedienbaar met slepen; en
> ADR-056 legt vast hoe vragen mogen evolueren.**
>
> Wat er ná LI050 anders is:
> - **Vraagbeheer is beheerder-only** (lezen blijft breed) en de **categorie is een eigen
>   tenant-entiteit** met composiet-FK; de **vraagcode is van het scherm** (systeem-toegekend);
>   vragen en categorieën hebben een **sleep-volgorde** (migraties 0074+0075).
> - **De engine negeert uitgezette vragen** ("een uitgezette vraag bestaat voor de beoordeling
>   niet") via één gedeelde afleiding `services/actieve_vraag.py` — dit dichtte de
>   checkpoint-gaten G2-1/G2-2 (scores op gedeactiveerde vragen telden mee; dode routes in
>   "Dit valt op").
> - **Het beheerscherm is leesbaar**: één regel per vraag (kop van een omrand blok,
>   `lk-inhoudskader`), onderbouwing achter één klik, één vraag tegelijk open, selectie met een
>   eigen kanaal; **optie-slepen gerepareerd** (tabelrijen droegen HTML5-drag niet — audit-bewijs).
> - **Drie nieuwe wachters met bijt-bewijs**: sleep-bronscan + tabel-element-verbod ·
>   werkvlakgrens-scan (geen card-in-card) · precies-één-selectie.
> - **ADR-056 (vraagevolutie) is beslist, niet gebouwd** — 16 besluiten incl. mockup-ronde.

---

## Top-5 prioriteiten LI051

1. **ADR-056 bouwen — sliceverdeling eerst.** De formulering bevroren bij het antwoord,
   verduidelijking vs. echte wijziging (één opslaan-moment per vraag, geen voorselectie),
   verouderd = neutraal + wegwerkbaar, optie-heractiveren, antwoordtype-slot mét reden.
   Open subknopen staan in het ADR (o.a. invoerings-vulling van de 267 antwoorden, de
   beheerder-UI voor tekstbewerking). Schema-rakend → gates.
2. **P50-2 Namenkaart zonder paginering** — gemeten (checkpoint §2B: 1 echte treffer + 2
   verwante); nu de fix-vorm kiezen (niet de limiet ophogen).
3. **P50-3 `organisatiegebruik.applicatie_id`** — Berts schemabesluit op het laatste goedkope
   moment (gate); checkpoint §2C somt de 7 verwante "applicatie"-namen op.
4. **Productie-hardening (OP-14/OP-28, scherpste punt van het checkpoint):** 31
   `changeme_dev`-vindplaatsen + 9 testaccounts + drie code-defaults die in productie stil
   doorvallen — **niets houdt dit tegen** (`validate_startup_config` checkt alleen aanwezigheid).
   Let op: de voorwaarden-zin bij OP-28 is gecorrigeerd (ADR-006 en gebruikersbeheer zijn al
   gebouwd).
5. **Consultant-drempels + P50-4-besluit.** De twee drempels (Bevinding/Verantwoordelijke/Actie
   achter "eerst scoren" + uitklap; Antwoord-veld ontbreekt bij 71/98 vragen zonder antwoordtype)
   — benoemd vervolgpunt uit de meting; en het functionele besluit welke keuzelijsten beheerbaar
   horen (meting klaar, checkpoint §2D: 31 lijsten, protocol drievoudig code-vast).

---

## Openstaande beslissingen

- **ADR-056 subknopen** (bij de bouw): invoerings-vulling, opslag-vorm in detail, plek stille
  notitie, meerkeuze-zonder-envelope.
- **P50-3**: kolom-hernoeming — eigen gate, eigen besluit.
- **P50-4**: welke keuzelijsten hóren beheerbaar (meting klaar; functionele keuze).
- **G2-3 tenant-registry**: provisioning-afspraak vóór de eerste echte tenant (registry is leeg
  terwijl er tenant-data bestaat — platform-brede backfills raken 0 tenants).
- **L7 css-poort**: de css-build-controle draait pas bij de afsluiting — deze sessie mét bewijs
  (kopstijl-afwijking landde in `6ab1960`, pas bij de TST gevangen). Proceskeuze Bert.
- **Contextpaneel** hangt nog aan categorie-volgorde 8 (`ComponentDetail.vue:752`) — sinds W5
  kan de beheerder die volgorde verslepen; betekenis-markering op de categorie is de echte vorm.
- **Import-lijn Tiel** (persoonsnamen) — geparkeerd. **Opschoonplan 7 skills** — uitgesteld
  (route in `docs/Opschoonplan-zeven-skills.md`). **Demostand uittredende deelnemer** — kan
  onafhankelijk ingepland.

---

## Bekende risico's en aandachtspunten

- **Suites groen (TST-V051, 0 kritieken):** backend **1236 passed / 2 skipped** (incl.
  kopverwijzingen-scan) · frontend **1404 passed / 104 files** · vite build OK · css-build
  14 scans OK · alembic **1 head** (`0075`), 0 branches, 38× RLS.
- **Migraties deze sessie: 2** (0074 checklist_categorie · 0075 vraag-volgorde) — beide
  toegepast én reseed-consistent bewezen (0 verspringingen).
- **Auditlog toont `categorie_id` als kale id** in wijzigingsregels (sinds W3) — leesbaarheid.
- **Restdata-les:** een actieve testvraag van een browsercheck maakt lifecycle-tests rood;
  opruimen + herbereken vóór de suite-uitslag telt (2× gebeurd deze sessie).
- De **dev-server-herstart met cache-leging**: `rm` staat in de deny-lijst — `npm run dev --
  --force` is de werkende weg (of `find … -delete`, zie werkprotocol).

---

## Geleerde patronen deze sessie (verankerd in de skills)

- **Welke laag bewijst deze toets** (likara-tests): handler-tests bewijzen de JS-keten, niet de
  browser-mechaniek — 1394 groen terwijl het optie-slepen nergens werkte; borg op de renderlaag
  (tabel-element-verbod) en benoem de browsercheck expliciet als sluitpunt.
- **Lees de definitie, niet de naam** (likara-frontend §werkvlak-rand): `card` draagt geen rand —
  wachter `werkvlakGrens.scan.test.js` (geen card-in-card).
- **Selectie · aanwijzen · aanstip zijn drie kanalen** (likara-frontend §Signaal-kanalen): twee
  bijna gelijke tinten op één kanaal maken selectie onleesbaar.
- **De audit-trail is het meetinstrument** voor "bereikte de browserhandeling de opslag"
  (likara-werkprotocol §Browsercheck): 12 categorie-updates, 0 optie-updates = bewijs in één blik.
