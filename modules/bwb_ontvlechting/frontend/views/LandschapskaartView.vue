<script setup>
/**
 * LandschapskaartView v3 — interactieve landschapskaart op Cytoscape.js (ADR-025 → ADR-040).
 *
 * Drie weergaven (Overzicht = brede plaat / Praatplaat = concentric centraal op één centrum + kring /
 * Lagen = preset-baanposities per laag-baan, LI036; de `modus`-computed is een dunne adapter op de
 * weergave-as — de Impact-verkenner is met ADR-040 afgeschaft),
 * zoeken + vier filters (domein/leverancier/hosting/
 * lifecycle), actieve migratieset, node-detail met doorklik naar het applicatie-detail, en een
 * lifecycle-legenda. De Cytoscape-graaf is een afgeleide van de reactieve state (tekenGraaf());
 * álle panelen (zoek/resultaten/set/detail/legenda/samenvatting) zijn pure Vue-state, zodat de
 * UI testbaar is met een gemockte cytoscape. Read-only; geen engine-aanraking.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from '@/composables/router'
import { detailRoute } from '@/detailIngang'
import cytoscape from '@/composables/cytoscape'
import { api } from '@/api'
import { useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { neemKaartHandoff } from '@/composables/kaartHandoff'
import { useSleepbaar } from '@/composables/useSleepbaar'
import { procesBoomLayout } from '../procesBoom'
import { humaniseer, veldLabel } from '../labels'
import { STAND_CODERING, STAND_LEGENDA, standKaartKleur } from '../standCodering'
import ZoekMultiSelect from './ZoekMultiSelect.vue'
import KaartBeginscherm from './KaartBeginscherm.vue'

const router = useRouter()
// Toast voor de "Volgorde opgeslagen"-bevestiging; defensief: in tests zonder Toast-provider null.
let toast = null
try { toast = useToast() } catch { /* geen Toast-provider (bv. unit-test) */ }
const route = useRoute()

// Lifecycle → kleur (node-achtergrond + rand).
const LC_STYLE = {
  migratieklaar: { bg: '#dcfce7', border: '#22c55e' },
  geblokkeerd: { bg: '#fee2e2', border: '#ef4444' },
  in_inventarisatie: { bg: '#dbeafe', border: '#3b82f6' },
  concept: { bg: '#f1f5f9', border: '#94a3b8' },
  null: { bg: '#f8fafc', border: '#cbd5e1' },
}
const lcStyle = (s) => LC_STYLE[s] || LC_STYLE.null
const LIFECYCLE_OPTIES = ['migratieklaar', 'in_inventarisatie', 'geblokkeerd', 'concept']
// LI036 — 'eigenaar' ("is eigendom van", org → component) is een eigen ring. Stond eerder niet in
// RINGEN → geen checkbox → `ringAan.has('eigenaar')` altijd false → de eigendom-edges werden
// permanent weggefilterd terwijl hun nodes wél zichtbaar bleven. Default AAN (essentieel: wie is
// verantwoordelijk voor dit component).
// LI033b — 'gebruikt' ("organisatie gebruikt applicatie", org → applicatie) is een eigen ring, spiegel
// van 'eigenaar'. Default AAN. Doet mee in de ego-kring (praatplaat) via `_burenVan` (alle actieve
// ringen) — geen aparte impact-bedrading (IMPACT_RINGEN is met de Impact-verkenner afgeschaft).
// ADR-043 gate 4 slice 2 — ring 'bedrijfsfuncties' (de plek-projectie: functie-plekken + systeem→
// plek-lijnen uit de subgraaf-verrijking): standaard AAN, zichtbaar in alle drie de weergaven.
// Vooraan = de "waarvoor"-laag (verving de proceslaan, G1).
const RINGEN = ['bedrijfsfuncties', 'applicaties', 'samenstelling', 'rollen', 'eigenaar', 'gebruikt', 'gebruikers', 'contracten', 'infrastructuur', 'organisatiestructuur']
// ADR-024 — context-ring "Organisatiestructuur" (persoon-met-rol → afdeling → organisatie); standaard
// UIT (zie ringAan), want context, niet de hoofdvraag van de kaart.
const RING_DEFAULT_UIT = new Set(['organisatiestructuur'])
// LI034 slice 2 — startstand van de RINGEN op de PRAATPLAAT: alleen de VIER kernkringen ("wat raakt
// dit object"): Gebruikt door (`gebruikers` + `gebruikt`), Rollen & beheer (`rollen`), Contracten
// (`contracten`), Infra & koppelingen (`infrastructuur` + `applicaties`). De context-ringen
// (`eigenaar`/`samenstelling`/`organisatiestructuur`) starten UIT — één klik terug te halen via de
// ring-checkboxes. Geldt ALLEEN op de praatplaat en ALLEEN bij het BETREDEN (niet bij hercentreren of
// re-render → een handmatig aangezette context-ring blijft staan). Het Overzicht houdt zijn eigen
// startstand (`ringAan` hierboven: alles-behalve-`organisatiestructuur`).
// ADR-043 gate 4 — 'bedrijfsfuncties' hoort bij de kern ("waarvoor gebruiken we dit object"): de
// ring is standaard-aan in álle weergaven, dus de praatplaat-startstand zet hem niet uit.
const RING_PRAATPLAAT_KERN = new Set(['bedrijfsfuncties', 'gebruikers', 'gebruikt', 'rollen', 'contracten', 'infrastructuur', 'applicaties'])
// ADR-031 — leesbare ring-namen. Backend levert ring='beheerorganisatie' → bij laden gemapt op 'rollen'.
const RING_LABELS = {
  bedrijfsfuncties: 'Bedrijfsfuncties', // ADR-043 gate 4 — plek-projectie + systeem-lijnen (de "waarvoor"-laag)
  applicaties: 'Componenten',
  samenstelling: 'Samenstelling', // ADR-033 1b — "onderdeel van" (component↔component aggregatie)
  rollen: 'Rollen & beheer',
  eigenaar: 'Eigendom', // LI036 — "is eigendom van" (eigenaar-organisatie → component)
  gebruikt: 'Gebruikt', // LI033b — "gebruikt" (organisatie → applicatie, uit het grove feit organisatiegebruik)
  gebruikers: 'Gebruikers',
  contracten: 'Contracten',
  infrastructuur: 'Infrastructuur',
  organisatiestructuur: 'Organisatiestructuur', // ADR-024 — "hoort bij" (persoon → afdeling → organisatie)
}
// LI019 1d-v2 → LI036 — laag-banen ("Lagen"-weergave): definitie (label + bandkleur) + default-
// volgorde (van boven naar beneden). De volgorde is gebruiker-herschikbaar (drag-drop) en wordt in
// sessionStorage bewaard. Startvolgorde per LI036 slice 1: … → Contracten → Overig (Overig onderaan).
const LANE_DEF = {
  bedrijfsfuncties: { label: 'Bedrijfsfuncties', bg: '#fff7ed' }, // ADR-043 gate 4 — de "waarvoor"-laag, bovenaan
  rollen: { label: 'Rollen & beheer', bg: '#fef9c3' },
  gebruikers: { label: 'Gebruikers', bg: '#f0fdf4' },
  componenten: { label: 'Componenten', bg: '#eff6ff' },
  infrastructuur: { label: 'Infrastructuur', bg: '#f0f9ff' },
  overig: { label: 'Overig', bg: '#f8fafc' },
  contracten: { label: 'Contracten', bg: '#faf5ff' },
}
const DEFAULT_LANE_VOLGORDE = ['bedrijfsfuncties', 'rollen', 'gebruikers', 'componenten', 'infrastructuur', 'contracten', 'overig']
// LI019 1d-v6 — swimlane-grid: nodes wrappen per lane binnen een BEGRENSDE breedte, zodat één grote
// lane (bv. 58 partijen) de andere lanes niet uitrekt en cy.fit() niet extreem uitzoomt (kernoorzaak B).
const MAX_LANE_W = 1200 // max model-breedte voor het node-grid per lane
const NODE_W = 190 // horizontale spreiding tussen nodes
const NODE_H = 72 // verticale spreiding per rij
const LANE_PAD = 30 // verticale padding binnen een lane (ruimte voor de header)
const LANE_MIN_H = 110 // min lane-hoogte — lege/kleine lane blijft zichtbaar met placeholder
const LANE_COLS = Math.max(1, Math.floor(MAX_LANE_W / NODE_W)) // kolommen per lane (= 6)
// ADR-031 — gebruikersgroep-node-stijl (distinctief t.o.v. applicaties).
const GG_STYLE = { bg: '#e0f2fe', border: '#0ea5e9' }
// LI036 rolbanen — de ENE rol-tag-kleurbron (node-pill in de Lagen-weergave én de popup lezen
// dezelfde map; geen tweede kleurdefinitie elders). Rand/vulling/vorm blijven onaangeroerd —
// de tag is een eigen HTML-element. 'gebruikt' krijgt óók een tag (elke plek toont zijn rol;
// géén tag = "hier geen rol", besluit B).
const ROL_TAG = {
  gebruikt: { label: 'gebruikt', bg: '#e0f2fe', tekst: '#075985' }, // sky — spiegelt de Gebruikers-baan
  levert: { label: 'levert', bg: '#ccfbf1', tekst: '#0f766e' },     // teal
  beheert: { label: 'beheert', bg: '#ede9fe', tekst: '#6d28d9' },   // paars
  eigenaar: { label: 'eigenaar', bg: '#fce7f3', tekst: '#be185d' }, // roze
}
// Welke rollen landen in de "Rollen & beheer"-baan (gebruikt → Gebruikers-baan).
const _ROLLEN_RB = ['beheert', 'eigenaar', 'levert']
// Oranje van de geselecteerd-component-rand (node:selected) — één bron voor de focus-rand.
const SELECTIE_RAND = '#f59e0b'
// LI025/LI036 — de ene dim-maat voor KNOPEN (CY-stijl `node.lk-dim`) én hun rol-tags (HTML-overlay):
// een tag deelt altijd de dim-staat van zijn knoop, met exact dezelfde opacity.
const DIM_NODE_OPACITY = 0.35
// Deterministische domeinkleuren (border in "kleur op domein"-modus).
const DOMEIN_PALET = ['#2563eb', '#d97706', '#0891b2', '#7c3aed', '#16a34a', '#db2777', '#65a30d', '#dc2626']
// Neutrale, UNIFORME tint voor de niet-actieve kleur-kanalen (kaart-lezing, slice A): één grijs over
// álle nodes → geen per-node-variatie die als status/domein te lezen valt. Bewust true-grey (géén
// slate — dat lijkt op de lifecycle-tinten `concept`/`null`).
const NEUTRAAL = { bg: '#e5e7eb', border: '#9ca3af' }

// ── State ───────────────────────────────────────────────────────────────────────
const nodes = ref([])
const edges = ref([])
const laden = ref(true)
const fout = ref(null)

// LI036 — de vroegere tweede layout-as (`layoutModus` 'radiaal'|'swimlane', LI019-parkeren) is
// GECONVERGEERD op de ene `weergave`-as hieronder: 'lagen' ís de baan-layout. Eén bron van waarheid.
const laneVolgorde = ref([...DEFAULT_LANE_VOLGORDE]) // LI019 1d-v2 — gebruiker-herschikbare baanvolgorde
const verbergLegeLanes = ref(false) // LI019 1d-v2 — lege banen verbergen voor een compactere weergave
const toonRegistratiegaps = ref(false) // LI019 1d-v7 — losse nodes (registratiegaps) óók tonen (default UIT)
const bandPx = ref([]) // schermposities van de lane-banden (top/height px), gesynct met cy pan/zoom
const zoekterm = ref('')
const filterTypes = ref([]) // LI019 1b — componenttype-multiselect (optie_sleutels)
const filterLeveranciers = ref([]) // LI019 1b-v2 — leverancier-multiselect (partij-ids)
const filterHosting = ref([]) // LI019 1b-v2 — hostingmodel-multiselect (enum-sleutels)
const filterLifecycle = ref([]) // LI019 1b-v2 — lifecycle-multiselect (status-sleutels)
// Standaard staan alle ringen aan, behalve de context-ringen in RING_DEFAULT_UIT (Organisatiestructuur).
const ringAan = ref(new Set(RINGEN.filter((r) => !RING_DEFAULT_UIT.has(r))))
const actieveSet = ref(new Set())
// LI033 — component-ids die "grof-only" zijn (organisatie gebruikt de applicatie, nog géén afdeling/
// groep als verfijning). Puur client-side afgeleid uit de org-ingang / het blok-handoff; voedt een
// rustige node-markering ("nog niet verfijnd") zónder node-attribuut of engine-raakvlak. Leeg = geen
// markering.
const grofOnlyIds = ref(new Set())
// ADR-040 F1 stap 2a — EXPLICIETE weergave-state (niet meer set-grootte-afgeleid). De weergave volgt
// de HANDELING van de gebruiker: één component inspecteren / "toon impact" / deep-link → 'praatplaat'
// (concentric centraal op het centrum + kring); brede verkenning / view / "hele landschap" →
// 'overzicht' (de volledige set als brede plaat). Een zichtbare schakelaar wisselt.
// LI036 stap 3 — set-ACTIES ("voeg toe"/buren) wijzigen de weergave NIET meer (bevestigd besluit).
// LI036 — derde weergave 'lagen': dezelfde set + filters, maar elk knoop in zijn laag-baan
// (preset-posities; zie _swimlanePositions/_laneVan). Dit is de ENE weergave-as — er is geen
// aparte layout-as meer.
const weergave = ref('overzicht') // 'overzicht' | 'praatplaat' | 'lagen'
const egoStartId = ref(null) // het praatplaat-CENTRUM (rename naar centrumId is cosmetisch; uitgesteld
                             // om de history-serialisatie niet te raken — zie de ontvlechtings-eis).
// `modus` is nu een DUNNE adapter op de expliciete weergave-state (de ~10 lees-plekken blijven zo
// werken): praatplaat-met-geresolveerd-centrum → 'ego' (concentric centraal + ego-kring); overzicht →
// 'geheel' (volledige set, concentric-op-degree); leeg beginscherm → 'leeg'. De praatplaat wint vóór de
// set-grootte, zodat "toon impact"/deep-link óók vanuit het hele landschap (lege set) de kring toont.
const modus = computed(() => {
  if (weergave.value === 'praatplaat' && egoStartId.value && nodePerId.value[egoStartId.value]) return 'ego'
  if (actieveSet.value.size === 0) return heleLandschap.value ? 'geheel' : 'leeg'
  return 'geheel'
})
// Kan er een praatplaat getoond worden? (er is een geresolveerd centrum). Stuurt de schakelaar-knop.
const kanPraatplaat = computed(() => !!(egoStartId.value && nodePerId.value[egoStartId.value]))
// Handeling → weergave (besluit A). `toonPraatplaat` zet het centrum + de weergave; `toonOverzicht`
// schakelt naar de brede plaat. De schakelaar en de ingangen roepen deze aan.
// ADR-040 F1 stap 2a — een weergave-WISSEL via de schakelaar begint met een schone lei: de legenda-
// spotlight (`legendaTypeFilter` → `lk-dim`) en een oude node-selectie/detail reizen NIET mee naar de
// nieuwe plaat (anders dimt een eerdere spotlight het hele Overzicht en blijft een oude detail/rand
// staan). Uitsluitend op de schakel-acties — de inspectie-paden (`toonPraatplaat(id)` vanuit kies/drill/
// dubbelklik) zetten zélf het detail en blijven ongemoeid.
function _verseWeergave() {
  legendaTypeFilter.value = null
  geselecteerdNodeId.value = null
  detailId.value = null
}
// LI034 slice 2 — de ring-startstand van de praatplaat (kern aan, context uit). Alleen aanroepen bij
// het BETREDEN van de praatplaat; de bestaande teken-/re-layout-watch verwerkt de ring-wijziging
// (geen tweede pad). History-/sessie-herstel zet `ringAan` rechtstreeks en loopt NIET hierlangs.
function _zetPraatplaatRingen() {
  ringAan.value = new Set(RING_PRAATPLAAT_KERN)
}
function toonPraatplaat(id) {
  const betreedt = weergave.value !== 'praatplaat' // overzicht→praatplaat = betreden (níét hercentreren)
  if (id) egoStartId.value = id        // inspecteren/hercentreren op een concreet component
  else _verseWeergave()                // schakelaar-ingang (geen id) → schone lei
  if (egoStartId.value) {
    weergave.value = 'praatplaat'
    if (betreedt) _zetPraatplaatRingen() // LI034 slice 2 — startstand kern-4; gebruikerskeuze daarna behouden
  }
}
function toonOverzicht() {
  _verseWeergave()
  weergave.value = 'overzicht'
}
// LI036 — schakelaar-ingang "Lagen": zelfde set + filters, knopen in laag-banen. Schone lei bij
// het wisselen (identiek aan toonOverzicht); het praatplaat-centrum blijft staan zodat terugwisselen kan.
function toonLagen() {
  _verseWeergave()
  weergave.value = 'lagen'
}
const detailId = ref(null)
const opbouwModus = ref(true) // geheel-model: true=insluiten (begint leeg), false=afpellen (begint vol)
// KAART-LEZING (slice A, ADR-043) — één actieve lezing; de actieve claimt zijn kleur-kanaal, de rest
// wordt neutraal. Session-persistent via lk-state (NIET de voorkeur-laag — ADR-041 is een latere stap).
const LEZING_OPTIES = [{ key: 'werk', label: 'Werk' }, { key: 'status', label: 'Status' }, { key: 'domein', label: 'Domein' }]
const lezing = ref('status')
const diepte = ref(1) // 1 = directe buren (ego); 2 = ook indirecte applicatie-buren (één hop dieper)

const containerRef = ref(null)
let cy = null
// LI023 — observatie (tests/diagnostiek): aantal uitgevoerde re-layouts. Hier (vóór defineExpose
// + de debounce-watch) gedeclareerd om TDZ te vermijden; de gedebouncede re-layout vult 'm.
const _relayoutTeller = ref(0)

// ADR-031 — sub-granulariteit Gebruikers-ring: groepeer gebruikersgroepen per organisatie.
const groepeerPerOrg = ref(true)
const _rawNaam = (id) => nodes.value.find((n) => n.id === id)?.naam
// Effectieve graaf-nodes/-edges. Bij "groepeer per organisatie" vervangen we de individuele
// gebruikersgroep-nodes door één aggregaat-node per organisatie (gesommeerd ledental) en hangen
// de serving-edges aan dat aggregaat (gededupliceerd). Alle graaf-afgeleiden gebruiken deze.
// LI031 — `_aggDoelVoorGg(gg)`: waar landt een gebruikersgroep bij "groepeer per organisatie"?
// Is de organisatie zélf al een node in de graaf, dán de org-node (geen tweede, org-genaamde
// `gg-org-…`-node die de org zou dubbelen — die kreeg dezelfde naam maar een ander id, dus de
// id-dedup in getekendeNodes ving 'm niet). Anders een synthetisch per-org aggregaat.
function _aggDoelVoorGg(gg, orgNodeIds) {
  const orgId = gg.organisatie_id || null
  if (orgId && orgNodeIds.has(orgId)) return orgId // absorbeer in de bestaande org-node
  return `gg-org-${orgId || '__overig__'}`
}
const grafNodes = computed(() => {
  if (!groepeerPerOrg.value) return nodes.value
  const overig = nodes.value.filter((n) => n.element_type !== 'gebruikersgroep')
  const orgNodeIds = new Set(overig.map((n) => n.id))
  const agg = new Map()
  for (const g of nodes.value) {
    if (g.element_type !== 'gebruikersgroep') continue
    const orgId = g.organisatie_id || null
    if (orgId && orgNodeIds.has(orgId)) continue // org-node vertegenwoordigt de groepen al → geen dubbel
    const key = orgId || '__overig__'
    const cur = agg.get(key) || {
      id: `gg-org-${key}`, element_type: 'gebruikersgroep', laag: 'business',
      naam: orgId ? _rawNaam(orgId) || 'Organisatie' : 'Overige groepen',
      organisatie_id: orgId, aantal_leden: 0,
    }
    cur.aantal_leden += g.aantal_leden || 0
    agg.set(key, cur)
  }
  return [...overig, ...agg.values()]
})
const grafEdges = computed(() => {
  if (!groepeerPerOrg.value) return edges.value
  const orgNodeIds = new Set(nodes.value.filter((n) => n.element_type !== 'gebruikersgroep').map((n) => n.id))
  const naarAgg = new Map()
  for (const n of nodes.value) {
    if (n.element_type === 'gebruikersgroep') naarAgg.set(n.id, _aggDoelVoorGg(n, orgNodeIds))
  }
  const out = []
  const gezien = new Set()
  for (const e of edges.value) {
    if (e.ring === 'gebruikers' && naarAgg.has(e.doel_id)) {
      const aggId = naarAgg.get(e.doel_id)
      const k = `${e.bron_id}->${aggId}`
      if (gezien.has(k)) continue
      gezien.add(k)
      out.push({ ...e, doel_id: aggId })
    } else out.push(e)
  }
  return out
})

const nodePerId = computed(() => Object.fromEntries(grafNodes.value.map((n) => [n.id, n])))
const heeftData = computed(() => nodes.value.length > 0)
const isApplicatie = (n) => n?.element_type === 'applicatie'

// ── Data laden (set-gestuurd — Fase B/LI022) ────────────────────────────────────
// "Hele landschap"-staat: bewust de volledige plaat tonen, LOS van de set-grootte. Een lege set
// betekent niet langer "toon alles", maar het lege beginscherm (de gebruiker kiest een ingang).
const heleLandschap = ref(false)
// Fase B slice 2b-v2 (LI023) — het beginscherm is NIET langer aan de set-grootte gekoppeld: de
// gebruiker bouwt er een set op en sluit het zelf via "Toon op de kaart" (@sluit). Zo verdwijnt het
// scherm niet meer onder zijn voeten zodra het eerste component is toegevoegd. Start open.
const beginschermOpen = ref(true)
// LI052 — remount-sleutel voor <KaartBeginscherm>. "Begin opnieuw" (wisSet) verhoogt 'm, zodat het
// beginscherm ALTIJD vers hermount — óók wanneer het al open stond (dan verandert beginschermOpen niet
// en zou de interne picker-buffer/vinkjes/zoekresultaten anders de reset overleven).
const beginschermSleutel = ref(0)
const beginscherm = computed(() => actieveSet.value.size === 0 && !heleLandschap.value)
// Voortgangsteller bij het laden van het hele landschap: {gedaan,totaal} of null. (cy.add is één
// synchrone call zonder native telbare batches → we tellen op de in chunks verwerkte nodes.)
const tekenVoortgang = ref(null)
let _laadGen = 0
const HELE_CHUNK = 50

function _volgendeFrame() {
  return new Promise((res) => {
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(() => res())
    else setTimeout(res, 0)
  })
}
function _mapEdges(rauw) {
  // ADR-031 — map de backend-ring 'beheerorganisatie' op de UI-ringnaam 'rollen'.
  return (rauw || []).map((e) => (e.ring === 'beheerorganisatie' ? { ...e, ring: 'rollen' } : e))
}

// Drie laadpaden: beginscherm (niets laden) · niet-lege set (subgraaf = set + 1-hop) · hele
// landschap (volledige graaf mét voortgangsteller). Bij elke set-/staat-wijziging wordt de hele set
// opnieuw opgehaald (idempotent; geen incrementele merge). `_laadGen` verwerpt verouderde races.
async function herlaadGraaf() {
  const gen = ++_laadGen
  if (beginscherm.value) {
    nodes.value = []
    edges.value = []
    egoStartId.value = null
    _seedScopeOrgs() // ADR-040 F1 stap 2b — geen orgs → lege scope
    tekenVoortgang.value = null
    fout.value = null
    laden.value = false
    return
  }
  laden.value = true
  fout.value = null
  try {
    if (actieveSet.value.size > 0) {
      // Niet-lege set → set-scoped subgraaf (een set ís focus; geen volledige plaat).
      const data = await api.landschapskaart.subgraaf([...actieveSet.value], diepte.value)
      if (gen !== _laadGen) return
      nodes.value = data.nodes || []
      edges.value = _mapEdges(data.edges)
      _schoonSetOp() // LI052 — spook-ids (geen node in de respons) uit de set halen (één keer, geen refetch)
      _seedScopeOrgs() // ADR-040 F1 stap 2b — eenmalige deterministische seed: alle aanwezige orgs aan
    } else {
      // Lege set + hele-landschap-actie → de volledige graaf, in chunks verwerkt voor "X van N".
      const data = await api.landschapskaart.haalGrafdata({ diepte: diepte.value })
      if (gen !== _laadGen) return
      const ruw = data.nodes || []
      tekenVoortgang.value = { gedaan: 0, totaal: ruw.length }
      const verwerkt = []
      for (let i = 0; i < ruw.length; i += HELE_CHUNK) {
        for (let j = i; j < Math.min(i + HELE_CHUNK, ruw.length); j++) verwerkt.push(ruw[j])
        tekenVoortgang.value = { gedaan: verwerkt.length, totaal: ruw.length }
        if (i + HELE_CHUNK < ruw.length) await _volgendeFrame()
        if (gen !== _laadGen) return
      }
      nodes.value = verwerkt
      edges.value = _mapEdges(data.edges)
      // ADR-040 F1 stap 2a — "hele landschap" = het volledige Overzicht: GEEN automatisch praatplaat-
      // centrum meer seeden. De weergave volgt de handeling — de Praatplaat wordt pas actief zodra de
      // gebruiker zélf een object kiest (dubbelklik/hercentreren, "toon impact", deep-link). Zo is het
      // hele landschap identiek aan het lege beginscherm: overzicht, geen centrum, Praatplaat-knop disabled.
      egoStartId.value = null
      // ADR-040 F1 stap 2b — "Organisaties in beeld" staan standaard aan: eenmalige deterministische seed.
      _seedScopeOrgs()
      tekenVoortgang.value = null
      // Fase B — "toon hele landschap" is een verse verkennings-wortel: hef de history opnieuw op
      // (na de flush van de scope-default) zodat die default geen losse "terug"-stap wordt.
      nextTick(() => { if (gen === _laadGen && _historieKlaar) _zaaiHistorie() })
    }
  } catch (e) {
    if (gen === _laadGen) {
      fout.value = e?.status === 401 ? null : e?.message || 'Laden van de landschapskaart mislukt.'
      tekenVoortgang.value = null
    }
  } finally {
    if (gen === _laadGen) laden.value = false
  }
}

// Diepte-toggle: herlaad de grafdata (?diepte=…) én pas de stap-diepte client-side toe (ego-view).
async function zetDiepte(d) {
  if (diepte.value === d) return
  diepte.value = d
  await herlaadGraaf()
}

// Alleen applicaties (+ sinds de scope-slice óók de eigen organisaties) zijn selecteerbaar via de
// zoeklijst/filters/actieve set; partijen, contracten en infrastructuur verschijnen automatisch als
// ring-nodes rond de gekozen apps.
const _isApp = (n) => n?.element_type === 'applicatie' || (n?.element_type === 'component' && n?.laag === 'application')
const _isOrg = (n) => n?.element_type === 'partij' && n?.soort === 'organisatie'

// ── Organisaties in beeld (LI053 → ADR-040 F1 stap 2b) — de balk bestuurt UITSLUITEND de org-overlay ──
// Een vinkje toont/verbergt de organisatie-node ÉN haar (per-org) gebruikersgroepen. Componenten,
// infra, contracten, personen en externe partijen vallen er NOOIT onder — die blijven altijd staan.
// De balk staat alléén op OVERZICHT (breed op organisatie filteren); op de praatplaat is de scope
// inert (het centrum + de kring bepalen wat je ziet — geen stille organisatie-verberging).
// ADR-040 F1 stap 2b — VOORSPELBAAR: geen reactieve auto-settle meer. `scopeOrgs` wordt bij élke load
// éénmalig deterministisch geseed op "alle aanwezige organisaties aan" (`_seedScopeOrgs`, aangeroepen
// in `herlaadGraaf` vóór de render). Een bewuste uitvink geldt binnen het huidige beeld; een set-
// wijziging/herlaad reset naar "alle aan" (init-semantiek A). Geen ná-render-beweging (fcose-fragiliteit).
const scopeOrgs = ref(new Set())   // aangevinkte organisatie-ids
const organisatieNodes = computed(() => nodes.value.filter(_isOrg))
function _seedScopeOrgs() {
  scopeOrgs.value = new Set(nodes.value.filter(_isOrg).map((o) => o.id))
}
function toggleScopeOrg(id) {
  const s = new Set(scopeOrgs.value)
  s.has(id) ? s.delete(id) : s.add(id)
  scopeOrgs.value = s
}
function _inScope(n) {
  // Scope bestuurt uitsluitend de organisatie-overlay op OVERZICHT en LAGEN (LI036 — daar is de
  // scopebalk ook zichtbaar; nooit onzichtbaar doorfilteren).
  if (actieveSet.value.has(n.id)) return true             // set-lid (focus) → altijd zichtbaar
  // ADR-040 F1 stap 2b — op de praatplaat is de scope inert: het centrum + de kring bepalen wat je ziet,
  // dus nooit een kring-organisatie stil wegfilteren (de balk is daar ook verborgen).
  if (weergave.value === 'praatplaat') return true
  if (_isOrg(n)) return scopeOrgs.value.has(n.id)         // org-node: alleen aangevinkte organisaties
  if (n.element_type === 'gebruikersgroep') {
    // Org-gebonden groep volgt de organisatie-vinkjes; org-loze groep NIET (die volgt de Gebruikers-
    // ring, elders via de edge-/getekendeNodes-zeef).
    if (n.organisatie_id) return scopeOrgs.value.has(n.organisatie_id)
    return true
  }
  return true                                             // componenten/infra/contract/persoon/extern: altijd
}
// Application-componenten zijn selecteerbaar (zoeklijst) + de eigen organisaties als vertrekpunt.
const appNodes = computed(() => nodes.value.filter((n) => _isApp(n) || _isOrg(n)).filter(_inScope))

// ── Filter-opties (datagedreven; alleen uit de applicaties) ──────────────────────
const _uniek = (sel) => [...new Set(appNodes.value.map(sel).filter(Boolean))].sort()
const domeinOpties = computed(() => _uniek((n) => n.domein))
const hostingOpties = computed(() => _uniek((n) => n.hosting_model))
const domeinKleur = computed(() => Object.fromEntries(domeinOpties.value.map((d, i) => [d, DOMEIN_PALET[i % DOMEIN_PALET.length]])))

// LI019 1b — type-filter: volledige componenttype-catalogus (tenant) i.p.v. alleen de
// in de graaf voorkomende typen. Client-side doorzoekbaar (kleine, vaste lijst).
const typeCatalogus = ref([]) // [{ optie_sleutel, label }]
const typeLabelMap = computed(() => Object.fromEntries(typeCatalogus.value.map((o) => [o.optie_sleutel, o.label])))
const zoekComponenttypes = ({ zoek } = {}) => {
  const q = (zoek || '').toLowerCase()
  return typeCatalogus.value.filter((o) => !q || (o.label || '').toLowerCase().includes(q))
}
// LI019 1b-v2 — leverancier-filter: server-side zoeken in externe partijen (de bron van de
// leverancier-verrijking). idVeld=id → eenduidige match op n.leverancier_id (geen naam-ambiguïteit).
const zoekLeveranciers = (params) => api.partijen.lijst({ ...params, aard: 'externe_partij' })

// LI019 1b-v2 — hosting/lifecycle als doorzoekbare multi-select uit de bestaande opties
// (hostingOpties = in de graaf aanwezige hostingmodellen; LIFECYCLE_OPTIES = vaste statusset).
const _zoekUitLijst = (opties) => ({ zoek } = {}) => {
  const q = (zoek || '').toLowerCase()
  return opties.value.filter((o) => !q || o.label.toLowerCase().includes(q))
}
const hostingFilterOpties = computed(() => hostingOpties.value.map((h) => ({ sleutel: h, label: typeLabel(h) })))
const lifecycleFilterOpties = computed(() => LIFECYCLE_OPTIES.map((lc) => ({ sleutel: lc, label: typeLabel(lc) })))
const zoekHosting = _zoekUitLijst(hostingFilterOpties)
const zoekLifecycle = _zoekUitLijst(lifecycleFilterOpties)

// ADR-028 — rol (multi-select, doorzoekbaar) + BIV-drempel per aspect (ordinaal). De rol-catalogus
// + BIV-niveaus komen uit /componenten/opties; de BIV-drempel vergelijkt client-side op de ordinale
// rang (positie in de al geordende `biv_niveaus`).
const rolCatalogus = ref([]) // [{ optie_sleutel, label }]
const rolLabelMap = computed(() => Object.fromEntries(rolCatalogus.value.map((o) => [o.optie_sleutel, o.label])))
const zoekRollen = ({ zoek } = {}) => {
  const q = (zoek || '').toLowerCase()
  return rolCatalogus.value.filter((o) => !q || (o.label || '').toLowerCase().includes(q))
}
const bivNiveaus = ref([]) // [{ optie_sleutel, label }] — ordinaal (laag → hoog)
const bivRangMap = computed(() => Object.fromEntries(bivNiveaus.value.map((o, i) => [o.optie_sleutel, i])))
const filterRollen = ref([])
const filterBivB = ref('')
const filterBivI = ref('')
const filterBivV = ref('')
const BIV_ASPECTEN = [
  { veld: 'biv_beschikbaarheid', ref: filterBivB, label: 'Beschikbaarheid' },
  { veld: 'biv_integriteit', ref: filterBivI, label: 'Integriteit' },
  { veld: 'biv_vertrouwelijkheid', ref: filterBivV, label: 'Vertrouwelijkheid' },
]
// BIV-drempel: leeg → geen filter; onbekende drempel → fail-open; node zónder waarde valt weg.
function _bivVoldoet(waarde, minSleutel) {
  if (!minSleutel) return true
  const drempel = bivRangMap.value[minSleutel]
  if (drempel == null) return true
  const rang = bivRangMap.value[waarde]
  return rang != null && rang >= drempel
}

// ── LI034 / ADR-041 — persoonlijke STANDAARDKIJK (kaart-kijkfilter) ──────────────────────────────
// Eén persoonlijke voorkeur (sleutel `kaart_kijkfilter`, slice-1-voorkeur-laag): het GEHEEL van hoe je
// kijkt — ringen + filters + diepte + groepeer + lane-opties. NOOIT de MOMENTKEUZE (welke set/
// centrum/weergave/zoekterm/scope je nú bekijkt). Toegepast bij een verse kaart-start en bij "Begin
// opnieuw"; in-sessie herladen behoudt het werk (lk-state wint).
const _KIJK_SLEUTEL = 'kaart_kijkfilter'
const opgeslagenKijk = ref(null) // de opgeslagen standaardkijk (blob) of null = geen standaard
const kijkFout = ref(null)
const kijkBezig = ref(false)
const _KALE_KIJK = () => ({
  ringAan: RINGEN.filter((r) => !RING_DEFAULT_UIT.has(r)),
  fTypes: [], fLev: [], fHost: [], fLc: [], fRol: [], bivB: '', bivI: '', bivV: '',
  diepte: 1, groepeerPerOrg: true,
  laneVolgorde: [...DEFAULT_LANE_VOLGORDE], verbergLegeLanes: false, toonRegistratiegaps: false,
})
// Het GEHEEL van de huidige kijk (kijk-variabelen; géén momentkeuze).
const _huidigeKijk = () => ({
  ringAan: [...ringAan.value],
  fTypes: [...filterTypes.value], fLev: [...filterLeveranciers.value], fHost: [...filterHosting.value],
  fLc: [...filterLifecycle.value], fRol: [...filterRollen.value],
  bivB: filterBivB.value, bivI: filterBivI.value, bivV: filterBivV.value,
  diepte: diepte.value, groepeerPerOrg: groepeerPerOrg.value,
  laneVolgorde: [...laneVolgorde.value], verbergLegeLanes: verbergLegeLanes.value,
  toonRegistratiegaps: toonRegistratiegaps.value,
})
// Genormaliseerde signatuur (volgorde-onafhankelijk) voor de gewijzigd-vergelijking.
const _kijkSig = (k) => JSON.stringify({
  ringAan: [...(k.ringAan || [])].sort(),
  fTypes: [...(k.fTypes || [])].sort(), fLev: [...(k.fLev || [])].sort(), fHost: [...(k.fHost || [])].sort(),
  fLc: [...(k.fLc || [])].sort(), fRol: [...(k.fRol || [])].sort(),
  bivB: k.bivB || '', bivI: k.bivI || '', bivV: k.bivV || '',
  diepte: k.diepte ?? 1, groepeerPerOrg: k.groepeerPerOrg !== false,
  laneVolgorde: k.laneVolgorde || [], verbergLegeLanes: !!k.verbergLegeLanes, toonRegistratiegaps: !!k.toonRegistratiegaps,
})
// Actief zodra de huidige kijk afwijkt van de opgeslagen standaard (of er nog geen standaard is).
const kijkGewijzigd = computed(() =>
  !opgeslagenKijk.value || _kijkSig(_huidigeKijk()) !== _kijkSig(opgeslagenKijk.value),
)
// Zet de kijk-variabelen uit een blob — NOOIT de momentkeuze (actieveSet/egoStartId/weergave/zoekterm/
// focus/scope/selectie). Defensief per veld (onbekende/malformed velden genegeerd).
function _pasKijkToe(k) {
  if (!k || typeof k !== 'object') return
  if (Array.isArray(k.ringAan)) ringAan.value = new Set(k.ringAan.filter((r) => RINGEN.includes(r)))
  if (Array.isArray(k.fTypes)) filterTypes.value = [...k.fTypes]
  if (Array.isArray(k.fLev)) filterLeveranciers.value = [...k.fLev]
  if (Array.isArray(k.fHost)) filterHosting.value = [...k.fHost]
  if (Array.isArray(k.fLc)) filterLifecycle.value = [...k.fLc]
  if (Array.isArray(k.fRol)) filterRollen.value = [...k.fRol]
  if (typeof k.bivB === 'string') filterBivB.value = k.bivB
  if (typeof k.bivI === 'string') filterBivI.value = k.bivI
  if (typeof k.bivV === 'string') filterBivV.value = k.bivV
  if (k.diepte === 1 || k.diepte === 2) diepte.value = k.diepte
  if (typeof k.groepeerPerOrg === 'boolean') groepeerPerOrg.value = k.groepeerPerOrg
  if (Array.isArray(k.laneVolgorde)) {
    const geldig = k.laneVolgorde.filter((x) => LANE_DEF[x])
    if (DEFAULT_LANE_VOLGORDE.every((x) => geldig.includes(x))) laneVolgorde.value = geldig
  }
  if (typeof k.verbergLegeLanes === 'boolean') verbergLegeLanes.value = k.verbergLegeLanes
  if (typeof k.toonRegistratiegaps === 'boolean') toonRegistratiegaps.value = k.toonRegistratiegaps
}
async function laadStandaardkijk() {
  try {
    const alle = await api.voorkeuren.haalAlle()
    const rij = (alle || []).find((v) => v.voorkeur_sleutel === _KIJK_SLEUTEL)
    if (rij?.waarde && typeof rij.waarde === 'object') opgeslagenKijk.value = rij.waarde
  } catch { /* geen voorkeur bereikbaar → geen standaard (kale default) */ }
}
async function slaKijkOp() {
  if (!kijkGewijzigd.value || kijkBezig.value) return
  kijkBezig.value = true; kijkFout.value = null
  try {
    const k = _huidigeKijk()
    await api.voorkeuren.zet(_KIJK_SLEUTEL, k)
    opgeslagenKijk.value = k
  } catch (e) {
    kijkFout.value = e?.message || 'Opslaan van je standaardkijk mislukt.'
  } finally {
    kijkBezig.value = false
  }
}
async function herroepKijk() {
  if (kijkBezig.value || !opgeslagenKijk.value) return
  kijkBezig.value = true; kijkFout.value = null
  try {
    await api.voorkeuren.herroep(_KIJK_SLEUTEL)
    opgeslagenKijk.value = null
    _pasKijkToe(_KALE_KIJK()) // terug naar de kale default
  } catch (e) {
    kijkFout.value = e?.message || 'Herroepen van je standaardkijk mislukt.'
  } finally {
    kijkBezig.value = false
  }
}

// ── Zoeken + filteren ─────────────────────────────────────────────────────────
// LI028 — `filterActief` stuurt UITSLUITEND het graafpad (zichtbareNodes). De vrije zoekterm hoort
// hier BEWUST NIET bij: die voedt alleen de resultatenlijst (`_matcht` → `gefilterdeNodes`). Anders
// zou typen de graaf-tak omschakelen (ego → context-buren via _metContext; geheel → opbouw/
// afpel) en het aantal nodes veranderen zonder dat er een chip is toegevoegd.
const filterActief = computed(
  () =>
    !!(
      filterTypes.value.length ||
      filterLeveranciers.value.length ||
      filterHosting.value.length ||
      filterLifecycle.value.length ||
      filterRollen.value.length ||
      filterBivB.value ||
      filterBivI.value ||
      filterBivV.value
    ),
)
// LI019 1c-v2 — attribuut-multifilters: OR binnen één filter, AND tussen filters, op de VOLLEDIGE
// node-set (alle ringen). Per attribuut-filter (leverancier/hosting/lifecycle) bepaalt de gebruiker
// kenmerkloze nodes via de vaste optie "Zonder [X]" (sentinel ZONDER): zonder die chip vallen
// kenmerkloze nodes weg, mét die chip blijven ze. Het type-filter houdt type-loze nodes (contracten/
// partijen/groepen) altijd vrij (geen "Zonder type"-optie).
const ZONDER = '__zonder__'
function _matchAttr(selectie, waarde) {
  if (!selectie.length) return true
  if (waarde == null || waarde === '') return selectie.includes(ZONDER)
  return selectie.includes(waarde)
}
function _nodeVoldoet(n, f) {
  if (f.types.length && _heeftTypeLabel(n) && !f.types.includes(n.element_type)) return false
  if (!_matchAttr(f.lev, n.leverancier_id)) return false
  if (!_matchAttr(f.host, n.hosting_model)) return false
  if (!_matchAttr(f.life, n.lifecycle_status)) return false
  // ADR-028 — rol/BIV gelden UITSLUITEND voor componenten (nodes mét een `componentrol`).
  // Context-nodes (partij/contract/gebruikersgroep — geen componentrol) zijn exempt: nooit
  // wegfilteren op een rol/BIV-filter (org-partijen zitten via `_isOrg` óók in appNodes).
  if (n.componentrol) {
    if (f.rol.length && !f.rol.includes(n.componentrol)) return false
    // BIV-drempel per aspect (AND); een component zónder waarde op een aspect valt weg bij een drempel.
    if (!_bivVoldoet(n.biv_beschikbaarheid, f.bivB)) return false
    if (!_bivVoldoet(n.biv_integriteit, f.bivI)) return false
    if (!_bivVoldoet(n.biv_vertrouwelijkheid, f.bivV)) return false
  }
  return true
}
const _huidigeFilters = () => ({
  types: filterTypes.value, lev: filterLeveranciers.value, host: filterHosting.value, life: filterLifecycle.value,
  rol: filterRollen.value, bivB: filterBivB.value, bivI: filterBivI.value, bivV: filterBivV.value,
})
function _filterMatch(n) {
  return _nodeVoldoet(n, _huidigeFilters())
}
function _matcht(n) {
  const q = zoekterm.value.trim().toLowerCase()
  if (q && !`${n.naam || ''} ${n.domein || ''} ${n.leverancier_naam || ''}`.toLowerCase().includes(q)) return false
  return _filterMatch(n)
}
const gefilterdeNodes = computed(() => appNodes.value.filter(_matcht))

// LI019 1c-v2 — Ego-bevestiging: een filterwijziging die het centrum-component zou verbergen vraagt
// eerst om bevestiging. Annuleren herstelt de vorige filterstaat (snapshot); doorgaan bevestigt 'm.
const egoFilterDialog = ref(false)
let _filterRevert = false
let _filterSnap = { types: [], lev: [], host: [], life: [], rol: [], bivB: '', bivI: '', bivV: '' }
function _commitFilterSnap() {
  _filterSnap = {
    types: [...filterTypes.value], lev: [...filterLeveranciers.value],
    host: [...filterHosting.value], life: [...filterLifecycle.value],
    rol: [...filterRollen.value], bivB: filterBivB.value, bivI: filterBivI.value, bivV: filterBivV.value,
  }
}
watch([filterTypes, filterLeveranciers, filterHosting, filterLifecycle, filterRollen, filterBivB, filterBivI, filterBivV], () => {
  if (_filterRevert) return
  // Bij een history-herstel niet de ego-filterdialog openen; wel de snapshot-baseline meenemen
  // zodat een láter echte filterwijziging tegen de juiste uitgangsstaat vergelijkt.
  if (_herstellen) { _commitFilterSnap(); return }
  const centrum = egoStartId.value ? nodePerId.value[egoStartId.value] : null
  if (modus.value !== 'ego' || !centrum) { _commitFilterSnap(); return }
  // Alleen vragen bij de overgang zichtbaar → verborgen van het centrum.
  if (_nodeVoldoet(centrum, _filterSnap) && !_nodeVoldoet(centrum, _huidigeFilters())) {
    egoFilterDialog.value = true
  } else {
    _commitFilterSnap()
  }
})
function egoFilterDoorgaan() {
  _commitFilterSnap()
  egoFilterDialog.value = false
}
function egoFilterAnnuleer() {
  _filterRevert = true
  filterTypes.value = [..._filterSnap.types]
  filterLeveranciers.value = [..._filterSnap.lev]
  filterHosting.value = [..._filterSnap.host]
  filterLifecycle.value = [..._filterSnap.life]
  filterRollen.value = [..._filterSnap.rol]
  filterBivB.value = _filterSnap.bivB
  filterBivI.value = _filterSnap.bivI
  filterBivV.value = _filterSnap.bivV
  egoFilterDialog.value = false
  nextTick(() => { _filterRevert = false })
}
// LI027 — vrije zoekterm in de resultatenlijst (client-side, op naam, case-insensitive).
const zoekResultaten = ref('')
const gefilterdeResultaten = computed(() => {
  const q = zoekResultaten.value.trim().toLowerCase()
  return q ? gefilterdeNodes.value.filter((n) => (n.naam || '').toLowerCase().includes(q)) : gefilterdeNodes.value
})

// ── Zichtbare nodes/edges per modus ──────────────────────────────────────────────
// Directe buren van één node (via de actieve ringen).
function _burenVan(id) {
  const ids = new Set()
  for (const e of grafEdges.value) {
    if (!ringAan.value.has(e.ring)) continue
    if (e.bron_id === id) ids.add(e.doel_id)
    else if (e.doel_id === id) ids.add(e.bron_id)
  }
  return ids
}
// Ego-zichtbare ids: centrum + 1e hop (alle ringen). Bij diepte 2 óók de 2e hop, maar uitsluitend
// applicatie-nodes (partijen/contracten/infra blijven op diepte 1) — "indirecte applicatie-buren".
const egoZichtbaarIds = computed(() => {
  const sp = egoStartId.value
  const ids = new Set()
  if (!sp) return ids
  ids.add(sp)
  const hop1 = _burenVan(sp)
  hop1.forEach((id) => ids.add(id))
  if (diepte.value >= 2) {
    hop1.forEach((id) => {
      if (!isApplicatie(nodePerId.value[id])) return
      _burenVan(id).forEach((n2) => {
        if (isApplicatie(nodePerId.value[n2])) ids.add(n2)
      })
    })
  }
  return ids
})
// LI019 1d-v4 (bug 7) — context behouden bij een actief filter: voeg aan de gematchte (component-)
// nodes hun context-buren toe via de NIET-flow-ringen (contracten/gebruikers/rollen/infrastructuur),
// zodat die ringen zichtbaar blijven. Flow-buren (peer-componenten) worden NIET toegevoegd — die zijn
// zelf onderworpen aan het filter.
function _metContext(matchedIds) {
  const ids = new Set(matchedIds)
  for (const e of grafEdges.value) {
    if (e.ring === 'applicaties') continue
    if (matchedIds.has(e.bron_id)) ids.add(e.doel_id)
    if (matchedIds.has(e.doel_id)) ids.add(e.bron_id)
  }
  return ids
}
// LI036 organisatiebalk — de zichtbaar-pipeline als FUNCTIE met de scope-zeef als parameter, zodat
// de balk-lijst (`organisatiesInBeeld`) exact dezelfde pipeline contrafeitisch kan draaien ("alsof de
// org-vinkjes aan staan") zónder tweede, driftende node-pad. `zichtbareNodes` = deze functie met de
// gewone `_inScope`.
function _bepaalZichtbaar(inScopeFn) {
  // LI019 1c — de filterselects gelden in ALLE modi. LI019 1d-v4 — bij een actief filter komen de
  // context-buren (niet-flow ringen) van de gematchte componenten mee, zodat de ringen zichtbaar blijven.
  // ADR-024 scope: de organisatie-scope is een extra zeef VÓÓR de weergave (alleen org-nodes + hun
  // gebruikersgroepen; componenten nooit). ADR-040 F1 stap 2b — geldt op OVERZICHT; op de praatplaat is
  // `_inScope` inert. Filters/ringen/selectie werken daarbinnen ongewijzigd door.
  let alle = grafNodes.value.filter(inScopeFn)
  if (modus.value === 'ego') {
    if (!filterActief.value) return alle.filter((n) => egoZichtbaarIds.value.has(n.id))
    const matched = new Set(alle.filter((n) => egoZichtbaarIds.value.has(n.id) && _filterMatch(n)).map((n) => n.id))
    const zichtbaar = _metContext(matched)
    return alle.filter((n) => zichtbaar.has(n.id))
  }
  // Geheel model toont standaard het VOLLEDIGE landschap. Filters verfijnen: opbouw = de match (+
  // context); afpel = alles behalve de match.
  if (!filterActief.value) return alle
  // LI028 — graaf-filtering op de attribuut-/typefilters (`_filterMatch`), NIET op de zoekterm:
  // typen mag de getekende graaf niet veranderen (de zoekterm voedt alleen de resultatenlijst).
  if (!opbouwModus.value) return alle.filter((n) => !_filterMatch(n))
  const matched = new Set(alle.filter(_filterMatch).map((n) => n.id))
  const zichtbaar = _metContext(matched)
  return alle.filter((n) => zichtbaar.has(n.id))
}
const zichtbareNodes = computed(() => _bepaalZichtbaar(_inScope))
const zichtbareNodeIds = computed(() => new Set(zichtbareNodes.value.map((n) => n.id)))
// Zichtbare edges bínnen een node-set: beide endpoints aanwezig + ring aan. Eén bron voor de echte
// weergave (`zichtbareEdges`) én het contrafeitelijke balk-pad.
function _edgesBinnen(ids) {
  // Fix 4 — ringAan filtert de edges in ALLE modi (niet meer alleen ego/geheel).
  return grafEdges.value.filter((e) => ids.has(e.bron_id) && ids.has(e.doel_id) && ringAan.value.has(e.ring))
}
const zichtbareEdges = computed(() => _edgesBinnen(zichtbareNodeIds.value))

// ── Actieve set ─────────────────────────────────────────────────────────────────
function inSet(id) {
  return actieveSet.value.has(id)
}
function toggleSet(id) {
  const s = new Set(actieveSet.value)
  s.has(id) ? s.delete(id) : s.add(id)
  actieveSet.value = s
  heleLandschap.value = false // Fase B — een set opbouwen verlaat de hele-landschap-modus
}
// ADR-033 — in de componentenlijst is klikken = toevoegen/verwijderen uit de actieve set
// (de aparte "+"-knop is vervallen). Het detailpaneel volgt de aangeklikte component.
function kiesComponent(id) {
  toggleSet(id)
  detailId.value = id
  // ADR-040 F1 stap 2a — één component selecteren = dat component inspecteren → praatplaat centraal
  // op die node (alleen als het component nu in de set zit; deselecteren zet geen praatplaat).
  if (actieveSet.value.has(id)) toonPraatplaat(id)
}
function voegAlleGefilterdeToe() {
  const s = new Set(actieveSet.value)
  for (const n of gefilterdeNodes.value) s.add(n.id)
  actieveSet.value = s
  heleLandschap.value = false
  toonOverzicht() // ADR-040 F1 stap 2a — bulk toevoegen = brede verkenning → overzicht
}
// Fase B slice 2b (LI023) — het beginscherm levert componenten via zijn ingangen (zoek/leverancier/
// contract/gebruikerscontext). Voeg ze toe aan de set (al-aanwezige ids stil overgeslagen → geen
// duplicaten); de set-watch haalt vervolgens de subgraaf van de bijgewerkte set op.
function voegComponentenToeAanSet(componenten) {
  const s = new Set(actieveSet.value)
  const g = new Set(grofOnlyIds.value)
  for (const c of componenten || []) {
    if (!c?.id) continue
    s.add(c.id)
    // LI033 — de org-ingang markeert grof-only componenten (verfijnd === false) mee; andere ingangen
    // dragen de vlag niet (blijven ongemarkeerd).
    if (c.grofOnly === true) g.add(c.id)
  }
  actieveSet.value = s
  grofOnlyIds.value = g
  heleLandschap.value = false
  // LI036 stap 3 (bevestigd besluit) — een SET-actie wijzigt uitsluitend de set, nooit de weergave:
  // wie in Lagen "voeg toe" klikt, blijft in Lagen (de nieuwe componenten verschijnen in hun banen).
  // De vroegere `toonOverzicht()` (ADR-040 "ingang → brede plaat") is hier vervallen; hercentreren/
  // weergave-wissel hoort bij dubbelklik en de expliciete schakelaar.
}
// Slice 5 (LI023) — directe COMPONENT-buren van een node, afgeleid uit de al-geladen graaf.
// NB: leest bewust uit `grafEdges` + `nodePerId` (de reactieve bron, idem `detailKoppelingen`) en
// NIET uit `cy.neighborhood().data()`: de Cytoscape-node-data draagt alleen id/label/stijl (zie
// `_nodeData`), geen element_type/naam → `_isApp` op cy-data zou niet werken. Geen API-call.
function componentBuren(id) {
  const buurIds = new Set()
  for (const e of grafEdges.value) {
    if (e.bron_id === id) buurIds.add(e.doel_id)
    else if (e.doel_id === id) buurIds.add(e.bron_id)
  }
  const out = []
  for (const bid of buurIds) {
    const m = nodePerId.value[bid]
    if (m && _isApp(m)) out.push({ id: m.id, naam: m.naam, element_type: m.element_type })
  }
  return out
}
// Component-node: voeg het component ZELF + al zijn component-buren toe (dedup in de set-functie).
function voegBurenToe(id) {
  const m = nodePerId.value[id]
  const self = m ? { id: m.id, naam: m.naam, element_type: m.element_type } : { id }
  voegComponentenToeAanSet([self, ...componentBuren(id)])
}
// Context-node (org/contract/leverancier/gebruikersgroep): voeg alléén de component-buren toe.
function voegContextComponentenToe(id) {
  voegComponentenToeAanSet(componentBuren(id))
}
const actieveSetNodes = computed(() => [...actieveSet.value].map((id) => nodePerId.value[id]).filter(Boolean))

// LI027 — focus op de actieve set (graph-filter) + wis-alles. Focus schakelt automatisch uit
// zodra de set leeg is.
const focusOpSet = ref(false)
function wisSet() {
  actieveSet.value = new Set()
  grofOnlyIds.value = new Set() // LI033 — verse start → grof-only-markering weg
  geselecteerdNodeId.value = null // verse start → selectie/highlight weg
  weergave.value = 'overzicht' // ADR-040 F1 stap 2a — verse start → default-weergave
  egoStartId.value = null
  heleLandschap.value = false
  beginschermOpen.value = true // "Begin opnieuw"/"Wis alles" = volledige reset → terug naar het beginscherm
  beginschermSleutel.value += 1 // LI052 — forceer een verse picker (buffer/vinkjes/zoekresultaten leeg)
  // ADR-040 F1 stap 2b — geen `_scopeAangeraakt` meer; de reset naar het beginscherm herlaadt (lege set)
  // en `_seedScopeOrgs` zet de scope opnieuw op "alle aan" (hier leeg — geen orgs op het beginscherm).
  legendaPos.value = { x: null, y: null } // LI025 — legenda terug naar standaardpositie
  popupPos.value = { x: null, y: null } // LI034 — klik-popup terug naar standaardpositie
  // LI034 — "Begin opnieuw" wist de bewaarde in-sessie-staat: een F5 hierna komt op het beginscherm
  // (geen stale set). Een direct daaropvolgende `beforeunload` schrijft de nu-lege set — die wordt niet
  // als set hersteld (length-guard in `_herstelKaartState`), dus F5 landt op het beginscherm.
  try { sessionStorage.removeItem(_LK_STATE_KEY) } catch { /* sessionStorage onbereikbaar */ }
  // LI034/ADR-041 — "Begin opnieuw" gaat naar je opgeslagen standaardkijk (geen standaard → kale
  // default zoals nu; wisSet reset de kijk-variabelen zelf niet). Nooit de actieve set (die is net leeg).
  if (opgeslagenKijk.value) _pasKijkToe(opgeslagenKijk.value)
}
// Fase B — bewuste "toon het hele landschap"-actie: leegt de set en zet de hele-landschap-vlag,
// waarna de herfetch-watch de volledige graaf laadt (mét voortgangsteller).
function toonHeleLandschap() {
  toonStartscherm.value = false
  actieveSet.value = new Set()
  grofOnlyIds.value = new Set() // LI033 — het hele landschap heeft geen org-gescoopte grof-only-context
  toonOverzicht() // ADR-040 F1 stap 2a — hele landschap = brede plaat → overzicht
  heleLandschap.value = true
  beginschermOpen.value = false // hele landschap = bewuste ingang → sluit het beginscherm
}
watch(() => actieveSet.value.size, (n) => { if (n === 0) focusOpSet.value = false })

// Fase B — set-gestuurd herladen: elke wijziging van de set óf de hele-landschap-vlag haalt de
// bijbehorende graaf opnieuw op. NIET tijdens de mount (de initiële laad gebeurt expliciet in
// onMounted ná het bepalen van deep-link/herstelde staat) → `_mountKlaar` voorkomt een dubbele fetch.
let _mountKlaar = false
// LI052 — anti-lus-guard: het opruimen van niet-resolvende set-ids (_schoonSetOp) muteert de set en
// zou zo een nieuwe fetch triggeren. De huidige nodes zijn dan al correct (een spook-id levert per
// definitie geen extra buren), dus die ene mutatie mag de fetch overslaan. Precies één keer.
let _slaHerlaadOver = false
watch(
  () => `${[...actieveSet.value].sort().join('|')}#${heleLandschap.value}`,
  () => {
    if (!_mountKlaar) return
    if (_slaHerlaadOver) { _slaHerlaadOver = false; return }
    herlaadGraaf()
  },
)
// LI052 — na een subgraaf-load: verwijder set-ids die GEEN node opleverden (spook-ids). Zo bevat de
// set alleen materialiseerbare leden → teller/modus (op geresolveerde leden) en de set convergeren.
// Toetst bewust tegen de RUWE respons-nodes (nodes.value), niet nodePerId (dat gg-nodes aggregeert).
function _schoonSetOp() {
  const aanwezig = new Set((nodes.value || []).map((n) => n.id))
  const behouden = [...actieveSet.value].filter((id) => aanwezig.has(id))
  if (behouden.length !== actieveSet.value.size) {
    _slaHerlaadOver = true // deze opschoon-mutatie mag GEEN nieuwe fetch uitlokken
    actieveSet.value = new Set(behouden)
  }
}

// ── Praatplaat-centrering (ADR-040 F1) ────────────────────────────────────────────
// De Impact-verkenner (ADR-033: drill-down over de koppelingsketen, `modus === 'impact'`) is met
// de tweedeling Overzicht/Praatplaat AFGESCHAFT — de Praatplaat (concentric centraal op één centrum
// + ego-kring) vervangt haar. De bijbehorende machinerie (drillPad, huidigeFocus, impactDirect/
// -Zichtbaar, _impactBuren, IMPACT_RINGEN, topbalkNodes, stapTerug) is verwijderd. "Toon impact" op
// één component is nu simpelweg: centreer de praatplaat op dat component (`drillNaar`).
// Vlag: een history-herstel (terug/vooruit) is bezig — onderdruk de afgeleide neven-effecten
// (ego-recenter hieronder + filter-dialog + push) zodat de herstelde toestand niet wordt
// overschreven of dubbel-gepusht.
let _herstellen = false
// Vlag: de eerstvolgende (her)tekening komt uit een herstel → zonder layout-animatie tekenen,
// zodat rap terug/vooruit geen 400ms-animaties opstapelt (de hang). Geconsumeerd in tekenGraaf.
let _herstelZonderAnimatie = false
// Een wijziging van de actieve set naar precies 1 component zet dat component als praatplaat-centrum
// (het centrum voor de concentric-plaat) en hercentreert. De weergave zelf volgt de HANDELING (de
// ingangen zetten 'overzicht'/'praatplaat' expliciet) — deze watch raakt `weergave` niet.
watch(
  () => [...actieveSet.value].sort().join('|'),
  () => {
    if (_herstellen) return // bij history-herstel blijft de herstelde ego/weergave staan
    if (actieveSet.value.size === 1) {
      egoStartId.value = [...actieveSet.value][0]
      _recenterPending = true
    }
  },
)
// "Toon impact" op één component → praatplaat centraal op dat component (ADR-040 F1 stap 2a).
function drillNaar(id) {
  if (!nodePerId.value[id]) return
  detailId.value = id
  toonPraatplaat(id)
}

// ── ADR-033 slice 2c/2d — opgeslagen & deelbare views (voorkant) ─────────────────────
const auth = useAuthStore()
// Beheer-recht op views = de IMPACT_VIEW-AANMAKEN/WIJZIGEN/VERWIJDEREN-lijn (medewerker/beheerder).
// Viewer/auditor zien de lijst en kunnen gedeelde views openen, maar krijgen geen opslaan/beheer.
const magViewsBeheren = computed(() => auth.hasRole('medewerker', 'beheerder'))
const opgeslagenViews = ref([])
const toonStartscherm = ref(false) // 2d — startscherm bij ≥1 opgeslagen view

async function laadViews() {
  try {
    opgeslagenViews.value = (await api.impactViews.lijst()) || []
  } catch {
    opgeslagenViews.value = [] // faalt zacht: geen views-lijst/startscherm
  }
}

// Foutmapping (403/404/409/422) → Toast (of, bij `veld`, de 422-veldtekst terug voor inline-weergave).
function _viewFout(e, { veld = false } = {}) {
  const status = e?.status
  if (veld && status === 422) {
    const det = Array.isArray(e?.detail) ? e.detail[0] : null
    return det?.msg || 'Controleer de naam (verplicht, max 150 tekens).'
  }
  const bericht =
    status === 403 ? 'Je hebt geen rechten voor deze actie.'
    : status === 404 ? 'Deze view bestaat niet (meer).'
    : status === 409 ? 'Je hebt al een view met deze naam.'
    : status === 422 ? 'Controleer de naam (verplicht, max 150 tekens).'
    : (e?.message || 'Er ging iets mis.')
  toast?.add?.({ severity: 'error', summary: 'View', detail: bericht, life: 4000 })
  return null
}

// Opslaan-/bewerken-dialog (gedeelde vorm; bewerkId=null → nieuw, anders bewerken).
const viewDialogOpen = ref(false)
const viewBewerkId = ref(null)
const viewNaam = ref('')
const viewGedeeld = ref(false)
const viewSelectieBijwerken = ref(false) // bewerken: selectie → huidige actieve set
const viewNaamFout = ref(null)
const viewBezig = ref(false)

function openOpslaan() {
  viewBewerkId.value = null
  viewNaam.value = ''
  viewGedeeld.value = false
  viewSelectieBijwerken.value = false
  viewNaamFout.value = null
  viewDialogOpen.value = true
}
function openBewerk(v) {
  viewBewerkId.value = v.id
  viewNaam.value = v.naam
  viewGedeeld.value = !!v.gedeeld
  viewSelectieBijwerken.value = false
  viewNaamFout.value = null
  viewDialogOpen.value = true
}
function sluitViewDialog() { viewDialogOpen.value = false }

async function bewaarView() {
  viewNaamFout.value = null
  const naam = viewNaam.value.trim()
  if (!naam) { viewNaamFout.value = 'Naam is verplicht.'; return }
  viewBezig.value = true
  try {
    if (viewBewerkId.value) {
      const body = { naam, gedeeld: viewGedeeld.value }
      // Selectie alleen bijwerken als de gebruiker dat kiest én er een actieve set is.
      if (viewSelectieBijwerken.value && actieveSet.value.size) body.component_ids = [...actieveSet.value]
      await api.impactViews.werkBij(viewBewerkId.value, body)
    } else {
      await api.impactViews.maak({ naam, component_ids: [...actieveSet.value], gedeeld: viewGedeeld.value })
    }
    viewDialogOpen.value = false
    toast?.add?.({ severity: 'success', summary: 'View opgeslagen', life: 2000 })
    await laadViews()
  } catch (e) {
    const veld = _viewFout(e, { veld: true })
    if (veld) viewNaamFout.value = veld // 422 → inline op het naamveld
  } finally {
    viewBezig.value = false
  }
}

// Openen: de bewaarde selectie wordt de actieve set → de adaptieve weergave volgt vanzelf
// (de herfetch-watch laadt de subgraaf van die set).
function openView(v) {
  actieveSet.value = new Set(v.component_ids || [])
  toonOverzicht() // ADR-040 F1 stap 2a — een opgeslagen (meervoudige) view = brede plaat → overzicht
  heleLandschap.value = false
  toonStartscherm.value = false
  beginschermOpen.value = false // een view openen = bewuste ingang → sluit het beginscherm
}
async function verwijderView(v) {
  try {
    await api.impactViews.verwijder(v.id)
    toast?.add?.({ severity: 'success', summary: 'View verwijderd', life: 2000 })
    await laadViews()
  } catch (e) {
    _viewFout(e)
  }
}
// 2d — escape vanuit het startscherm: toon meteen het hele landschap (Fase B-actie), zonder een
// view te kiezen.
// LI046 — derde uitgang van het startscherm: gewoon zelf beginnen (lege verkenning).
// De modal was een verplichte horde voor wie zelf wil zoeken: de enige escape was juist
// de zware hele-kaart-actie. Sluiten onthult het beginscherm ("Begin je verkenning").
function sluitStartscherm() {
  toonStartscherm.value = false
}

function beginMetHeleKaart() {
  toonHeleLandschap()
}

// ── Detail ────────────────────────────────────────────────────────────────────
const detailNode = computed(() => (detailId.value ? nodePerId.value[detailId.value] : null))
// Slice 5 (LI023) — component-buren van de getoonde node, gememoïseerd via computed (reactief op
// grafEdges/nodePerId; één berekening i.p.v. twee per render voor disabled-staat + telling).
const geselecteerdNodeBuren = computed(() => (detailId.value ? componentBuren(detailId.value) : []))
const detailKoppelingen = computed(() => {
  const id = detailId.value
  if (!id) return 0
  return grafEdges.value.filter((e) => e.bron_id === id || e.doel_id === id).length
})
// LI034 — leesbare ondertitel van de klik-popup: "type · status" (alleen node-popup).
const popupSub = computed(() => {
  if (popupKind.value !== 'node') return ''
  const n = detailNode.value
  if (!n) return ''
  const status = n.lifecycle_status ? typeLabel(n.lifecycle_status) : null
  return [_typeRegelVoor(n), status].filter(Boolean).join(' · ')
})
// LI034 — "wat raakt dit object" in gewone taal: één regel per kring, uitsluitend afgeleid uit de
// AL GELADEN graafdata (nodes/edges/node-metadata) — geen nieuw endpoint. Een ontbrekende relatie
// wordt NIET verborgen maar als leesbaar registratiegat benoemd (`gat: true`). Alleen voor een
// component/applicatie als centrum (de eerste ADR-040-praatplaat); context-nodes houden hun velden.
// NB: de expliciete contract→leverancier-lijn komt pas in slice 3 — hier tonen we de leverancier
// zoals de node-metadata (`leverancier_naam`) die al draagt; niets verzonnen.
const _popupNaamVan = (nid) => nodePerId.value[nid]?.naam || null
const popupSamenvatting = computed(() => {
  if (popupKind.value !== 'node') return []
  const n = detailNode.value
  if (!n || !_isApp(n)) return []
  const id = n.id
  const ggs = []; const beheer = []; const contracten = []; const hosts = []; const koppel = new Set()
  for (const e of grafEdges.value) {
    if (e.ring === 'gebruikers' && e.bron_id === id) { const nm = _popupNaamVan(e.doel_id); if (nm) ggs.push(nm) }
    else if (e.ring === 'rollen' && e.doel_id === id) { const nm = _popupNaamVan(e.bron_id); if (nm) beheer.push(e.label ? `${nm} (${e.label})` : nm) }
    else if (e.ring === 'contracten' && e.bron_id === id) { const nm = _popupNaamVan(e.doel_id); if (nm) contracten.push(nm) }
    else if (e.ring === 'infrastructuur' && e.doel_id === id) { const nm = _popupNaamVan(e.bron_id); if (nm) hosts.push(nm) }
    else if (e.ring === 'applicaties' && (e.bron_id === id || e.doel_id === id)) { const nm = _popupNaamVan(e.bron_id === id ? e.doel_id : e.bron_id); if (nm) koppel.add(nm) }
  }
  const orgNamen = (n.gebruikt_door_organisaties || []).map(_popupNaamVan).filter(Boolean)
  const gebruikers = [...orgNamen, ...ggs]
  const eig = n.eigenaar_organisatie_id ? _popupNaamVan(n.eigenaar_organisatie_id) : null
  const regel = (key, label, tekst) => ({ key, label, tekst, gat: false })
  const gat = (key, label, tekst) => ({ key, label, tekst, gat: true })
  const out = []
  out.push(gebruikers.length
    ? regel('gebruikt', 'Gebruikt door', `${gebruikers.length}: ${gebruikers.join(', ')}`)
    : gat('gebruikt', 'Gebruikt door', 'nog geen gebruik geregistreerd'))
  out.push(beheer.length
    ? regel('beheer', 'Beheerd door', beheer.join(', '))
    : gat('beheer', 'Beheerd door', 'geen beheerrol toegewezen'))
  out.push(contracten.length
    ? regel('contract', 'Valt onder', `${contracten.join(', ')}${n.leverancier_naam ? ` · leverancier: ${n.leverancier_naam}` : ''}`)
    : gat('contract', 'Valt onder', 'geen contract gekoppeld'))
  out.push(eig
    ? regel('eigenaar', 'Eigenaar', eig)
    : gat('eigenaar', 'Eigenaar', 'nog geen eigenaar geregistreerd'))
  out.push(hosts.length
    ? regel('infra', 'Draait op', hosts.join(', '))
    : gat('infra', 'Draait op', 'geen infrastructuur geregistreerd'))
  out.push(koppel.size
    ? regel('koppel', 'Koppelt met', `${koppel.size}: ${[...koppel].join(', ')}`)
    : gat('koppel', 'Koppelt met', 'geen koppelingen geregistreerd'))
  return out
})
function selecteerNode(id) {
  detailId.value = id
  // LI021 — in ego-modus hercentreert een klik op ELKE node (applicatie, partij, gebruikersgroep, …),
  // niet langer alleen applicaties.
  if (modus.value === 'ego' && nodePerId.value[id]) {
    egoStartId.value = id
    _recenterPending = true // LI019 1d-v4 (bug 5) — alléén ná een expliciete recenter op het ego-centrum
  }
  // Fix 3: highlight + centreer de node in de grafiek (voor o.a. klik op een actieve-set-item).
  if (!cy) return
  cy.elements?.().unselect?.()
  const node = cy.getElementById?.(String(id))
  if (!node || !node.length) return
  node.select?.()
  cy.animate?.({ center: { eles: node }, zoom: Math.max(cy.zoom?.() ?? 1, 1.2), duration: 400, easing: 'ease-in-out-cubic' })
}
function openApplicatie() {
  if (detailNode.value) router.push(detailRoute('component', detailNode.value.id))
}

// ── ADR-033 — selectie-highlight: enkelklik op een knoop kleurt ALLEEN z'n incidente lijnen ──
// Oranje (`SELECTIE_RAND`, de ene gedeelde bron) markeert uitsluitend het aangeklikte component +
// de lijnen van/naar dat component. Toegepast als runtime cytoscape-klassen (geen relayout per klik).
const geselecteerdNodeId = ref(null)
// Pure predicate (testbaar): is deze edge incident aan de huidige selectie?
const _edgeGehighlight = (e) =>
  !!geselecteerdNodeId.value && (e.bron_id === geselecteerdNodeId.value || e.doel_id === geselecteerdNodeId.value)

function _pasSelectieHighlight() {
  if (!cy) return
  try {
    cy.edges?.()?.removeClass?.('hl-edge')
    cy.nodes?.()?.removeClass?.('hl-node')
    const sel = geselecteerdNodeId.value
    if (!sel) return
    // LI036 rolbanen — match op de LOGISCHE id: in de Lagen-weergave kan één partij meerdere visuele
    // instances hebben (`logischId` in de node-data); ALLE instances + hun lijnen lichten samen op.
    // Buiten Lagen is logischId === id → identiek aan het oude getElementById-gedrag.
    cy.nodes?.()?.forEach?.((node) => {
      const d = node.data?.() || {}
      if ((d.logischId || d.id) !== String(sel)) return
      node.addClass?.('hl-node')
      node.connectedEdges?.()?.addClass?.('hl-edge')
    })
  } catch { /* gemockte cytoscape in tests → no-op */ }
}
// LI034 — een selectie(-wijziging) stuurt zowel de incidente-lijn-highlight als de dim-op-klik.
watch(geselecteerdNodeId, () => { _pasSelectieHighlight(); _pasDim() })

// Enkelklik op een knoop: inspecteren = detail tonen + alléén z'n incidente lijnen highlighten.
// Géén hercentreren/drill (dat is dubbelklik). Werkt consistent in elke weergave.
function inspecteerNode(id) {
  // Enkelklik = de normale selectie-semantiek (mét dim). Bij een klik op dezelfde knoop vuurt de
  // watch niet → dim expliciet bijwerken.
  geselecteerdNodeId.value = id
  _pasDim()
  openNodePopup(id) // zet detailId + toont het detail (zoals nu)
}

// ── Toestand-geschiedenis (browser-model: lineair + cursor) ─────────────────────────
// Heen-en-weer door bezochte kaarttoestanden met een cursor. Eén toestand = selectie/
// centrering (actieve set + geselecteerde node + weergave/praatplaat-centrum) + ring-instellingen
// (welke ringen aan, "Groepeer per organisatie") + filters (type/leverancier/hosting/lifecycle,
// zoekterm, "Focus op actieve set"). Zoom/pan tellen NIET (puur kijkhoek → geen entry).
// De weergave (overzicht/praatplaat) is één toestand-entry — geen tweede terug-mechanisme. Werkgeheugen
// binnen de sessie; niet gepersisteerd (opgeslagen views dekken bewaren/delen, ongemoeid).
// shallowRef + bevroren snapshots: geen diepe reactiviteit op de (groeiende) history → geen
// geheugenlek bij een lange klik-sessie. Begrensd op de laatste _HIST_MAX entries.
const historie = shallowRef([])
const cursor = ref(-1)
const _HIST_MAX = 50
let _historieKlaar = false
const kanTerug = computed(() => cursor.value > 0)
const kanVooruit = computed(() => cursor.value < historie.value.length - 1)

function _maakToestand() {
  return {
    set: [...actieveSet.value], sel: geselecteerdNodeId.value,
    weergave: weergave.value, ego: egoStartId.value,
    ring: [...ringAan.value], groep: groepeerPerOrg.value,
    fTypes: [...filterTypes.value], fLev: [...filterLeveranciers.value],
    fHost: [...filterHosting.value], fLc: [...filterLifecycle.value],
    zoek: zoekterm.value, focus: focusOpSet.value,
    scopeOrgs: [...scopeOrgs.value],
  }
}
// Genormaliseerde signatuur van de history-relevante toestand (volgorde-onafhankelijk) —
// een wijziging hiervan = een nieuwe toestand. Zoom/pan zitten er bewust NIET in.
const _toestandSig = computed(() => JSON.stringify({
  set: [...actieveSet.value].sort(), sel: geselecteerdNodeId.value,
  weergave: weergave.value, ego: egoStartId.value,
  ring: [...ringAan.value].sort(), groep: groepeerPerOrg.value,
  fTypes: [...filterTypes.value].sort(), fLev: [...filterLeveranciers.value].sort(),
  fHost: [...filterHosting.value].sort(), fLc: [...filterLifecycle.value].sort(),
  zoek: zoekterm.value, focus: focusOpSet.value,
  scopeOrgs: [...scopeOrgs.value].sort(),
}))
watch(_toestandSig, () => {
  if (!_historieKlaar || _herstellen) return
  // Browser-model: een nieuwe wijziging vanaf een teruggehaalde toestand knipt de
  // vooruit-tak (alles ná de cursor) af en begint daar een nieuw pad. Begrensd op _HIST_MAX
  // (oudste valt eruit). Bevroren snapshot (geen diepe reactiviteit).
  let arr = historie.value.slice(0, cursor.value + 1)
  arr.push(Object.freeze(_maakToestand()))
  if (arr.length > _HIST_MAX) arr = arr.slice(arr.length - _HIST_MAX)
  historie.value = arr
  cursor.value = arr.length - 1
})
function _zaaiHistorie() {
  historie.value = [Object.freeze(_maakToestand())]
  cursor.value = 0
  _historieKlaar = true
}
function _herstelToestand(t) {
  _herstellen = true
  // Anti-thrash: de door dit herstel uitgelokte (her)tekening zonder layout-animatie laten
  // verlopen (tekenGraaf consumeert deze vlag); de nextTick hieronder wist een eventuele rest.
  _herstelZonderAnimatie = true
  const setGelijk = (s, a) => s.size === a.length && a.every((x) => s.has(x))
  const arrGelijk = (cur, a) => cur.length === a.length && cur.every((x, i) => x === a[i])
  // ALLEEN toewijzen wat écht verandert: nieuwe Set-/array-instanties laten de teken-watch op
  // referentie vuren → anders forceert elke (ook gelijke) herstelstap een volledige relayout
  // (de kern van de hang). Een gelijk-blijvende toestand levert nu nul (re)tekeningen.
  if (!setGelijk(actieveSet.value, t.set)) actieveSet.value = new Set(t.set)
  if (geselecteerdNodeId.value !== t.sel) geselecteerdNodeId.value = t.sel
  if (weergave.value !== t.weergave) weergave.value = t.weergave
  if (egoStartId.value !== t.ego) egoStartId.value = t.ego
  if (!setGelijk(ringAan.value, t.ring)) ringAan.value = new Set(t.ring)
  if (groepeerPerOrg.value !== t.groep) groepeerPerOrg.value = t.groep
  if (!arrGelijk(filterTypes.value, t.fTypes)) filterTypes.value = [...t.fTypes]
  if (!arrGelijk(filterLeveranciers.value, t.fLev)) filterLeveranciers.value = [...t.fLev]
  if (!arrGelijk(filterHosting.value, t.fHost)) filterHosting.value = [...t.fHost]
  if (!arrGelijk(filterLifecycle.value, t.fLc)) filterLifecycle.value = [...t.fLc]
  if (zoekterm.value !== t.zoek) zoekterm.value = t.zoek
  if (focusOpSet.value !== t.focus) focusOpSet.value = t.focus
  // LI053 — scopeModus is vervallen; een oud-format snapshot dat het veld nog bevat laadt gewoon
  // (het overtollige veld wordt genegeerd).
  if (t.scopeOrgs && !setGelijk(scopeOrgs.value, t.scopeOrgs)) scopeOrgs.value = new Set(t.scopeOrgs)
  // ADR-040 F1 stap 2b — geen `_scopeAangeraakt` meer. Een pure scope-herstelstap wijzigt de set NIET →
  // de reload-watch vuurt niet → `_seedScopeOrgs` overschrijft de herstelde scope niet (terug/vooruit
  // van de scope blijft werken). Een herstel dat óók de set wijzigt herlaadt en volgt init-semantiek A
  // ("alle aan") — bewust; terug/vooruit over set-grenzen is uitgesteld werk (niet gebroken).
  // Afgeleide watchers (drill-reset, filter-dialog, push) draaien op de flush → pas dáárná
  // vrijgeven; een onverbruikte animatie-vlag (geen tekening uitgelokt) ook wissen. Centreren
  // loopt via de layout-stop (_naLayout) — geen losse cy.fit() meer (auto-centreren gaat hierin op).
  nextTick(() => { _herstellen = false; _herstelZonderAnimatie = false })
}
function terugInHistorie() {
  if (!kanTerug.value) return
  cursor.value -= 1
  _herstelToestand(historie.value[cursor.value])
}
function vooruitInHistorie() {
  if (!kanVooruit.value) return
  cursor.value += 1
  _herstelToestand(historie.value[cursor.value])
}

// ── Klik-detail-popups (koppeling + knoop) + fullscreen — read-only weergave ─────
// Gedeelde popup-state: koppeling- én knoop-popup delen vorm + sluitgedrag. Een nieuwe
// klik VERVANGT de open popup (zelfde refs). Engine onaangeroerd (alleen lezen via api).
const popupOpen = ref(false)
const popupKind = ref(null) // 'node' | 'edge'
const popupEdgeRing = ref(null) // LI046 slice 3 — de leeg-melding is flow-specifiek
const popupTitel = ref('')
const popupBadge = ref(null) // 'Inkomend' | 'Uitgaand' (alleen koppeling t.o.v. ego)
const popupLaden = ref(false)
const popupVelden = ref([]) // [{ label, waarde }] — uitsluitend ingevulde velden (knoop-popup)
// Koppeling-popup (ADR-023a Fase 4) — master-detail: links de flow-lijst van het paar, rechts het detail.
const popupFlows = ref([]) // [{ id, naam, positie:'uit'|'in', tegenNaam, richting, protocol, impact, omschrijving }]
const popupSelId = ref(null) // geselecteerde flow (master); default = eerste rij
const popupMelding = ref(null) // RBAC-/terugval-melding (geen technische fout)
// LI036 rolbanen — rol-context in de popup: de rol(len) van de AANGEKLIKTE plek (instance) bovenaan,
// de overige rol(len) van dezelfde partij eronder. `_klikRollen` wordt door de node-tap-handler gezet
// (consume-once in openNodePopup); buiten de Lagen-weergave blijven beide leeg.
const _klikRollen = ref([])
const popupRolActief = ref([]) // rol-sleutels van de aangeklikte instance
const popupRolOverig = ref([]) // overige rol-sleutels van dezelfde partij (andere instances)
const popupGeselecteerd = computed(() => popupFlows.value.find((f) => f.id === popupSelId.value) || popupFlows.value[0] || null)
function selecteerFlow(id) { popupSelId.value = id }
const popupActies = ref([]) // [{ label, fn }] — doorklik-links naar detailschermen (node + edge)
const geselecteerdeEdgeId = ref(null) // cy-id van de aangeklikte edge (highlight zolang popup open)
const fullscreen = ref(false)

// B2 — doorklik-link naar het detailscherm van een node (null als er geen eigen scherm is).
// LI034 bug B — ÉÉN gedeelde doorklik-conditie voor de component-detailpagina: een component op de
// applicatielaag heeft een betekenisvol detailscherm (applicatie én andere componenttypes op
// `laag==='application'`); infra (technology) en niet-componenten (partij/contract/gebruikersgroep) niet.
// Gebruikt door zowel de popup (`_detailLink`) als het zijpaneel ("Open component →") → geen twee
// uiteenlopende drempels meer. (NB: backend-nodes dragen het componenttype als `element_type`, nooit
// letterlijk 'component' — daarom is `laag==='application'` de juiste, bredere conditie.)
const _heeftComponentDetail = (n) => !!n && (n.element_type === 'applicatie' || n.laag === 'application')
function _detailLink(node, aanleiding = null) {
  if (!node) return null
  // LI046 — de kaart vertaalt zijn node naar de canonieke objectsoort; de ROUTE komt uit de
  // gedeelde ingang (`detailRoute`). Kaart-nodes dragen het componenttype als `element_type`
  // (nooit letterlijk 'component'), dus de applicatielaag-drempel blijft hier.
  const soort =
    node.element_type === 'partij' || node.element_type === 'contract'
      ? node.element_type
      : node.element_type === 'gebruikersgroep'
        ? null
        : _heeftComponentDetail(node)
          ? 'component'
          : null
  if (!soort) return null
  const route = detailRoute(soort, node.id, aanleiding)
  if (!route) return null
  const label = { partij: 'Open partij →', contract: 'Open contract →', component: 'Open component →' }[soort]
  return { label, fn: () => router.push(route) }
}

function sluitPopup() {
  popupOpen.value = false
  popupKind.value = null
  popupEdgeRing.value = null
  popupTitel.value = ''
  popupBadge.value = null
  popupVelden.value = []
  popupFlows.value = []
  popupSelId.value = null
  popupMelding.value = null
  popupActies.value = []
  popupRolActief.value = [] // LI036 — rol-context hoort bij déze popup
  popupRolOverig.value = []
  // B1 — highlight van de aangeklikte edge opheffen.
  geselecteerdeEdgeId.value = null
  cy?.edges?.()?.removeClass?.('sel-edge')
  // ADR-033 — deselecteren: de node-selectie + z'n incidente-lijn-highlight vervallen → alles neutraal.
  geselecteerdNodeId.value = null
}

// Veld alleen opnemen als de waarde bestaat/ingevuld is (toon nooit lege regels).
const _veld = (label, waarde) => (waarde != null && waarde !== '' ? { label, waarde } : null)
const _velden = (arr) => arr.filter(Boolean)

// ── LI036 slice 2 · stap 3 — herkomst-uitsplitsing + vervullende componenten (popup-helpers) ──
// Herkomst-regels (edge.herkomst uit de subgraaf) compact per deelproces gegroepeerd:
// [{ label: <deelproces>, waarde: 'Registreren, Archiveren' }]. None/leeg → geen regels.
function _herkomstVelden(herkomst) {
  if (!herkomst || !herkomst.length) return []
  const per = new Map()
  for (const h of herkomst) {
    const k = h.proces_naam || 'Proces'
    if (!per.has(k)) per.set(k, [])
    if (h.applicatiefunctie_label && !per.get(k).includes(h.applicatiefunctie_label)) per.get(k).push(h.applicatiefunctie_label)
  }
  return [...per.entries()].map(([naam, functies]) => ({ label: naam, waarde: functies.join(', ') || '—' }))
}
// De systeem→plek-edges van een bedrijfsfunctie-plek in de huidige subgraaf (bron = component,
// doel = plek-knoop). HARDE guard op `relatietype`: de ring 'bedrijfsfuncties' draagt óók
// `functie_plaatsing`-edges (plek→ouder-plek); die tellen NOOIT mee als dragers.
const _vervulEdgesVan = (plekId) => grafEdges.value.filter(
  (e) => e.relatietype === 'functievervulling' && e.doel_id === plekId,
)
// ADR-043 gate 4 (G8) — de stand komt UIT de gedeelde leeslaag: de backend hangt `plek_stand`
// (gat/via_boven/hier/werkvoorraad/niets) aan elke plek-knoop (uit `plek_standen`, server-side). De
// kaart LEEST dat; hij rekent de dekking NIET zelf na (de invariant). Herhaalt een plek zich (path-
// expansie), dan draagt elk exemplaar dezelfde stand (de backend borgt die gelijke waarheid — G7
// hard-grens 1). Slice B2 (LI043): de stand wordt op de kaart als KLEUR getoond (uit `standCodering`,
// `_nodeData`-vulling onder de werk-lezing), niet meer als rand-stijl.
// De rustige popup-benoeming van een gat / half-antwoord (eerlijk-gaten-tonen, popupSamenvatting-lijn).
const popupProcesGap = computed(() => {
  if (popupKind.value !== 'node') return false
  const n = nodePerId.value[detailId.value]
  return !!(n && n.element_type === 'bedrijfsfunctie' && (n.plek_stand === 'gat' || n.plek_stand === 'via_boven'))
})
// "Ondersteund door"-sectie van de plek-popup: scanbare COMPONENTNAMEN die deze plek dragen (het
// antwoord ná verdringing — de backend tekent nooit een verdrongen systeem). Reactief op de open popup.
const popupVervuldDoor = computed(() => {
  if (popupKind.value !== 'node') return []
  const n = nodePerId.value[detailId.value]
  if (!n || n.element_type !== 'bedrijfsfunctie') return []
  return _vervulEdgesVan(n.id)
    .map((e) => {
      const comp = nodePerId.value[e.bron_id]
      return comp ? { id: comp.id, naam: comp.naam, herkomst: _herkomstVelden(e.herkomst) } : null
    })
    .filter(Boolean)
    .sort((a, b) => a.naam.localeCompare(b.naam))
})

// Directe pre-fill van een knoop-popup uit de kaart-data (vóór de detail-fetch laadt).
function _nodePrefill(n) {
  return _velden([
    _veld('Type', n.element_type ? typeLabel(n.element_type) : null),
    _veld(veldLabel('lifecycle_status'), n.lifecycle_status ? typeLabel(n.lifecycle_status) : null),
    // ADR-046 — levensfase op de node (kaart-signaal; None = nog niet vastgelegd → weggelaten).
    _veld('Levensfase', n.levensfase ? typeLabel(n.levensfase) : null),
    _veld('Domein', n.domein ? typeLabel(n.domein) : null),
    _veld('Leverancier', n.leverancier_naam),
    _veld('Hosting', n.hosting_model ? typeLabel(n.hosting_model) : null),
    n.blokkades_open != null ? { label: 'Open blokkades', waarde: String(n.blokkades_open) } : null,
  ])
}

function _nodeVelden(et, d, n) {
  if (et === 'applicatie') {
    return _velden([
      _veld(veldLabel('lifecycle_status'), d.lifecycle_status ? typeLabel(d.lifecycle_status) : null),
      // ADR-046 — twee vragen, twee velden: Levensfase (feit) + Bedoeling (migratiepad).
      _veld('Levensfase', d.levensfase ? typeLabel(d.levensfase) : null),
      _veld('Eigenaar-organisatie', d.eigenaar_organisatie_naam),
      _veld('Hostingmodel', d.hostingmodel ? typeLabel(d.hostingmodel) : null),
      _veld('Bedoeling', d.migratiepad ? typeLabel(d.migratiepad) : null),
      _veld('Complexiteit', d.complexiteit ? typeLabel(d.complexiteit) : null),
      _veld('Prioriteit', d.prioriteit ? typeLabel(d.prioriteit) : null),
      _veld('Beschrijving', d.beschrijving),
      n.blokkades_open ? { label: 'Open blokkades', waarde: String(n.blokkades_open) } : null,
    ])
  }
  if (et === 'contract') {
    const looptijd = [d.begindatum, d.einddatum].some(Boolean) ? `${d.begindatum || '…'} – ${d.einddatum || '…'}` : null
    return _velden([
      _veld('Leverancier', d.leverancier_naam),
      _veld('Contracttype', d.contracttype ? typeLabel(d.contracttype) : null),
      _veld('Looptijd', looptijd),
      _veld('Omschrijving', d.omschrijving),
    ])
  }
  if (et === 'bedrijfsfunctie') {
    // ADR-043 gate 4 — bedrijfsfunctie-plek-knoop: de inhoud is de "Ondersteund door"-sectie
    // (`popupVervuldDoor`) + de gap-cue (`popupProcesGap`), geen velden-muur in de dl.
    return _velden([])
  }
  if (et === 'partij') {
    const adres = [d.straat_huisnummer, d.postcode, d.plaats].filter(Boolean).join(', ') || null
    return _velden([
      _veld('Aard', d.aard ? typeLabel(d.aard) : null),
      _veld('Functietitel', d.functietitel),
      _veld('Adres', adres),
      _veld('Telefoon', d.telefoon),
      _veld('Mobiel', d.mobiel),
      _veld('E-mail', d.email),
      _veld('Omschrijving', d.omschrijving),
    ])
  }
  // infrastructuur/generiek component
  return _velden([
    _veld('Type', d.componenttype_label),
    _veld(veldLabel('lifecycle_status'), d.lifecycle_status ? typeLabel(d.lifecycle_status) : null),
    _veld('Eigenaar-organisatie', d.eigenaar_organisatie_naam),
    _veld('Hostingmodel', d.hostingmodel ? typeLabel(d.hostingmodel) : null),
    _veld('Beschrijving', d.beschrijving),
    n.blokkades_open ? { label: 'Open blokkades', waarde: String(n.blokkades_open) } : null,
  ])
}

// Knoop-popup: dispatch per element_type naar het juiste detail-endpoint; node-data als
// directe pre-fill. GEEN hercentreren (dat is dubbelklik). 403 → nette terugval-melding.
async function openNodePopup(id) {
  const n = nodePerId.value[id]
  if (!n) return
  detailId.value = id
  popupKind.value = 'node'
  popupBadge.value = null
  popupTitel.value = n.naam || ''
  popupMelding.value = null
  const _nodeLink = _detailLink(n)
  popupActies.value = _nodeLink ? [_nodeLink] : []
  popupFlows.value = []
  popupSelId.value = null
  popupVelden.value = _nodePrefill(n)
  // ADR-043 gate 4 — bedrijfsfunctie-plek: de "Vervuld door"-sectie is een REACTIEVE afleiding op
  // de open popup (`popupVervuldDoor` — geen snapshot; volgt de actuele set).
  // LI036 rolbanen — rol-context (alleen partijen, alleen Lagen): aangeklikte rol(len) bovenaan
  // (uit de tap-handler, consume-once), de overige rollen van dezelfde partij eronder.
  const klik = _klikRollen.value
  _klikRollen.value = []
  if (weergave.value === 'lagen' && n.element_type === 'partij') {
    const alle = [...new Set(instanceProjectie.value.instances
      .filter((i) => i.logischId === id).flatMap((i) => i.rollen))]
    popupRolActief.value = klik.filter((r) => alle.includes(r))
    popupRolOverig.value = alle.filter((r) => !popupRolActief.value.includes(r))
  } else {
    popupRolActief.value = []
    popupRolOverig.value = []
  }
  popupOpen.value = true
  // ADR-031 — gebruikersgroep heeft geen detail-endpoint: toon ledental + organisatie uit node-data.
  if (n.element_type === 'gebruikersgroep') {
    popupVelden.value = _velden([
      n.aantal_leden ? { label: 'Leden', waarde: String(n.aantal_leden) } : null,
      _veld('Organisatie', n.organisatie_id ? nodePerId.value[n.organisatie_id]?.naam : null),
    ])
    popupLaden.value = false
    return
  }
  popupLaden.value = true
  try {
    const et = n.element_type
    let d
    // LI059 Slice 4 — applicatie ÍS een component; er is geen aparte /applicaties-haal meer.
    if (et === 'contract') d = await api.contracten.haal(id)
    else if (et === 'partij') d = await api.partijen.haal(id)
    else if (et === 'bedrijfsfunctie') d = n // plek-knoop: synthetisch path-id, geen fetch — node-data volstaat
    else d = await api.componenten.haal(id)
    if (popupKind.value !== 'node' || detailId.value !== id) return // intussen vervangen
    popupVelden.value = _nodeVelden(et, d, n)
  } catch (e) {
    popupMelding.value = e?.status === 403
      ? 'Meer details niet beschikbaar (geen leesrecht).'
      : 'Details konden niet geladen worden.'
  } finally {
    popupLaden.value = false
  }
}

// Eén flow-relatie → een master-detail-rij. Positie t.o.v. de aangeklikte pijl: 'uit'
// (bron===edge.bron, uitgaand →) of 'in' (bron===edge.doel, inkomend ←). Tegenpartij = het
// doel van déze flow (waar de stroom heen gaat).
function _flowRij(r, edge) {
  const k = r.kenmerken || {}
  return {
    id: r.id,
    naam: r.naam || '–',
    positie: r.bron_id === edge.bron_id ? 'uit' : 'in',
    tegenNaam: nodePerId.value[r.doel_id]?.naam || '',
    richting: k.richting,
    protocol: k.protocol,
    impact: k.impact_bij_verbreking,
    omschrijving: r.omschrijving,
  }
}

// ── LI046 slice 3 — per-ring-takken van de edge-popup. Elke ring vertelt zijn EIGEN
// verhaal; de dekking is geborgd met een test (RINGEN ⊆ _EDGE_TAKKEN — zie
// LandschapskaartPopups.test.js): een nieuwe ring zonder tak laat de suite falen. Valt
// er op runtime tóch een onbekende ring doorheen, dan toont de fallback een neutraal
// bron→label→doel-verhaal — nooit meer een lege bevinding over een ander relatietype
// (de "Geen koppelingen gevonden."-bug op de gebruikt-lijn).
// Een tak geeft { titel, velden, aanleidingBron?, aanleidingDoel?, laadGebruikStand? }
// terug; de aanleidingen reizen mee met de doorklik (gedeelde ingang, slice 1/2).
const _EDGE_TAKKEN = {
  applicaties: null, // flow — het master-detail-pad met API-call (in openEdgePopup zelf)
  rollen: ({ edge, bronNaam, doelNaam }) => ({
    titel: edge.label || 'Rol',
    velden: [_veld('Partij', bronNaam), _veld('Object', doelNaam)],
  }),
  // LI034 slice 3 — de contracten-ring draagt twee soorten lijnen: component→contract
  // ("valt onder") en contract→leverancier ("geleverd door"); onderscheid via relatietype.
  contracten: ({ edge, bronNaam, doelNaam }) =>
    edge.relatietype === 'leverancier'
      ? { titel: 'Geleverd door', velden: [_veld('Contract', bronNaam), _veld('Leverancier', doelNaam)] }
      : {
          titel: 'Valt onder contract',
          velden: [_veld('Component', bronNaam), _veld('Contract', doelNaam)],
          aanleidingBron: { tab: 'contracten' }, // het feit leeft op de Contracten-tab
        },
  infrastructuur: ({ bronNaam, doelNaam }) => ({
    titel: 'Draait op',
    velden: [_veld('Component', doelNaam), _veld('Host', bronNaam)],
  }),
  // ADR-033 1b — samenstelling: bron=geheel → doel=onderdeel ("bestaat uit").
  samenstelling: ({ bronNaam, doelNaam }) => ({
    titel: 'Samenstelling',
    velden: [_veld('Geheel', bronNaam), _veld('Onderdeel', doelNaam)],
  }),
  // ADR-024 — hoort bij: bron (persoon/afdeling) → doel (afdeling/organisatie).
  organisatiestructuur: ({ bronNaam, doelNaam }) => ({
    titel: 'Hoort bij',
    velden: [_veld('Onderdeel', bronNaam), _veld('Hoort bij', doelNaam)],
  }),
  // ADR-043 gate 4 — twee lijnsoorten: plek-hiërarchie ("onderdeel van") en systeem→plek
  // ("ondersteunt", het antwoord ná verdringing — nooit een verdrongen systeem).
  bedrijfsfuncties: ({ edge, bronNaam, doelNaam }) =>
    edge.relatietype === 'functie_plaatsing'
      ? { titel: 'Onderdeel van', velden: [_veld('Functie', bronNaam), _veld('Onderdeel van', doelNaam)] }
      : {
          titel: 'Ondersteunt',
          velden: [_veld('Systeem', bronNaam), _veld('Bedrijfsfunctie', doelNaam)],
          aanleidingBron: { tab: 'bedrijfsfunctie' }, // het feit leeft op de Bedrijfsfunctie-tab
        },
  gebruikers: ({ nodeDoel, bronNaam, doelNaam }) => ({
    titel: 'Gebruikt door',
    velden: [
      _veld('Component', bronNaam),
      _veld('Gebruikersgroep', doelNaam),
      nodeDoel?.aantal_leden ? { label: 'Leden', waarde: String(nodeDoel.aantal_leden) } : null,
    ],
  }),
  // LI046 slice 3 — de twee ringen die eerder stil in het koppeling-pad vielen.
  // Eigenaar: read-only projectie van `component.eigenaar_organisatie_id`; de doorklik
  // landt bij het feit (veld-anker uit slice 2).
  eigenaar: ({ bronNaam, doelNaam }) => ({
    titel: 'Eigenaar',
    velden: [_veld('Organisatie', bronNaam), _veld('Component', doelNaam)],
    aanleidingDoel: { veld: 'eigenaar' },
  }),
  // Gebruikt: het grove gebruiksfeit (organisatiegebruik). De HARDHEID van het feit staat
  // bovenaan — een stand, geen tekort (grof op organisatieniveau · verfijnd naar afdeling);
  // async bijgeladen. De doorklik landt op de Gebruik-tab van het component.
  gebruikt: ({ bronNaam, doelNaam }) => ({
    titel: 'Gebruikt',
    velden: [_veld('Organisatie', bronNaam), _veld('Component', doelNaam)],
    aanleidingDoel: { tab: 'gebruik' },
    laadGebruikStand: true,
  }),
}

// De stand van het grove gebruiksfeit bijladen (grof/verfijnd) — de kaart-payload draagt
// die niet op de edge. Zelfde taal als de leeslijst (ADR-046 stuk 2): verfijnd zonder
// afdelingsnamen is "afdeling nog onbekend" — de normale stand na een eerste workshop,
// geen fout; grof is een stand, geen verwijt.
async function _laadGebruikStand(edge) {
  popupLaden.value = true
  try {
    const rijen = await api.organisatiegebruik.lijstVoorApplicatie({ applicatie_id: edge.doel_id })
    if (popupKind.value !== 'edge') return
    const feit = (rijen || []).find((r) => r.organisatie_id === edge.bron_id)
    if (!feit) return // feit niet (meer) vindbaar → basisvelden blijven staan, geen verzonnen stand
    const stand = feit.heeft_verfijning
      ? feit.afdelingen?.length
        ? `Verfijnd naar afdeling: ${feit.afdelingen.join(', ')}`
        : 'Verfijnd — afdeling nog onbekend'
      : 'Op organisatieniveau — nog niet verfijnd naar afdeling'
    popupVelden.value = _velden([{ label: 'Stand', waarde: stand }, ...popupVelden.value])
  } catch (e) {
    popupMelding.value = e?.status === 403
      ? 'Meer details niet beschikbaar (geen leesrecht).'
      : 'Details konden niet geladen worden.'
  } finally {
    popupLaden.value = false
  }
}

// Koppeling-popup (flow-edge) — ADR-023a Fase 4. Eén edge = een gericht applicatiepaar dat één
// of meer flows bundelt. Haal ALLE flows van het ONGEORDENDE paar op, sorteer op naam, en toon
// ze als master-detail (links lijst + richting-icoon, rechts detail). Geldt ook bij n=1.
async function openEdgePopup(edge) {
  if (!edge) return
  const bronNaam = nodePerId.value[edge.bron_id]?.naam || '?'
  const doelNaam = nodePerId.value[edge.doel_id]?.naam || '?'
  popupKind.value = 'edge'
  popupEdgeRing.value = edge.ring ?? null
  popupBadge.value = null
  popupMelding.value = null
  popupVelden.value = []
  popupFlows.value = []
  popupSelId.value = null
  popupOpen.value = true
  popupLaden.value = false

  if (edge.ring === 'applicaties') {
    popupActies.value = _edgeActies(edge)
    popupTitel.value = `Koppelingen: ${bronNaam} ↔ ${doelNaam}`
    popupLaden.value = true
    try {
      const p = await api.relaties.lijst({ paar_bron_id: edge.bron_id, paar_doel_id: edge.doel_id, relatietype: 'flow' })
      if (popupKind.value !== 'edge') return
      const rijen = (p.items || []).map((r) => _flowRij(r, edge))
      rijen.sort((a, b) => String(a.naam).localeCompare(String(b.naam), 'nl'))
      popupFlows.value = rijen
      popupSelId.value = rijen[0]?.id ?? null // eerste rij automatisch geselecteerd
    } catch (e) {
      popupMelding.value = e?.status === 403
        ? 'Meer details niet beschikbaar (geen leesrecht).'
        : 'Details konden niet geladen worden.'
    } finally {
      popupLaden.value = false
    }
    return
  }

  const tak = _EDGE_TAKKEN[edge.ring]
  const verhaal = tak
    ? tak({ edge, bronNaam, doelNaam, nodeDoel: nodePerId.value[edge.doel_id] })
    : {
        // Runtime-fallback (onbekende ring): eerlijk neutraal verhaal, nooit een lege
        // bevinding over koppelingen. De dekkingstest hoort dit pad onbereikbaar te houden.
        titel: edge.label || 'Relatie',
        velden: [_veld('Van', bronNaam), _veld('Naar', doelNaam)],
      }
  popupTitel.value = verhaal.titel
  popupVelden.value = _velden(verhaal.velden)
  popupActies.value = _edgeActies(edge, verhaal)
  if (verhaal.laadGebruikStand) await _laadGebruikStand(edge)
}

// B2 + LI046 — doorklik naar bron/doel wáár die een eigen detailscherm heeft, mét het
// aangeklikte feit als aanleiding (gedeelde ingang): landen bij het feit, niet bovenaan.
function _edgeActies(edge, verhaal = {}) {
  return [
    { id: edge.bron_id, aanleiding: verhaal.aanleidingBron || null },
    { id: edge.doel_id, aanleiding: verhaal.aanleidingDoel || null },
  ]
    .map(({ id, aanleiding }) => {
      const node = nodePerId.value[id]
      const l = _detailLink(node, aanleiding)
      return l ? { label: `Open ${node.naam} →`, fn: l.fn } : null
    })
    .filter(Boolean)
}

// Enkele- vs. dubbel-tap op een knoop (Cytoscape kent geen native dbltap). De enkele-
// klik-actie (popup) wordt ~280ms uitgesteld; komt er binnen die drempel een tweede tap,
// dan is het een dubbelklik → hercentreren, en de popup opent NIET (geen flikker).
let _tapTimer = null
let _tapId = null
const _DBLTAP_MS = 280
function onNodeTap(id) {
  if (_tapId === id && _tapTimer) {
    clearTimeout(_tapTimer); _tapTimer = null; _tapId = null
    legendaTypeFilter.value = null // LI025 — dieper verkennen heft de legenda-dim op (schone focus)
    // ADR-043 gate 4 — een bedrijfsfunctie-plek is geen component: dubbelklik hercentreert NIET
    // (een plek-id is synthetisch, geen subgraaf-anker). Geen plek-inzoom in deze slice.
    const knoop = nodePerId.value[id]
    if (knoop?.element_type === 'bedrijfsfunctie') return
    // ADR-040 F1 stap 2a — DUBBELklik = HERCENTREREN: dit component wordt het praatplaat-centrum
    // (concentric centraal + ego-kring). Zowel vanuit Overzicht als binnen de praatplaat.
    actieveSet.value = new Set([id])
    toonPraatplaat(id)
    selecteerNode(id)
    return
  }
  if (_tapTimer) clearTimeout(_tapTimer)
  _tapId = id
  _tapTimer = setTimeout(() => {
    _tapTimer = null; _tapId = null
    // ADR-033 — ENKELklik = inspecteren: detail tonen + ALLEEN de incidente lijnen highlighten
    // (consistent in elke weergave; géén drill/hercentreren meer op enkelklik).
    inspecteerNode(id)
  }, _DBLTAP_MS)
}

// Fullscreen-overlay (in-app): de hele view vult het venster via een CSS-klasse — GEEN
// remount, dus alle state (centrum/selectie/popup/set/filters) blijft behouden.
// LI036 — bij vergroten/verkleinen HERFIT de plaat (zelfde indeling, passend gecentreerd in de
// nieuwe maat): de CSS-maatwissel triggert de bestaande ResizeObserver → `_pasCanvasMaat`
// (resize + dezelfde fit als _naLayout; géén re-layout, knopen verspringen niet). Het vroegere
// viewport-behoud (`_behoudViewport` + zoom/pan-herstel + setTimeout-nudge) is bewust vervallen;
// dit dekt óók de Escape-uitgang (die zet alleen de vlag — zelfde observer-pad).
let _recenterPending = false // LI019 1d-v4 (bug 5) — true ná een expliciete ego-recenter (dubbelklik/set-klik)
function toggleFullscreen() {
  fullscreen.value = !fullscreen.value
}
// Hét ene maatwissel-pad (ResizeObserver-callback): her-meten + passend maken op de BESTAANDE
// posities. De fit vuurt zoom/pan-events → de overlay-hersync (banden + rol-tags) loopt vanzelf
// mee via de bestaande 'pan zoom resize'-handler.
function _pasCanvasMaat() {
  cy?.resize?.()
  cy?.fit?.(undefined, 50)
}

function _opEscape(e) {
  if (e.key !== 'Escape') return
  if (popupOpen.value) sluitPopup()
  else if (fullscreen.value) fullscreen.value = false
}

// ── Cytoscape-graaf (afgeleide van de state) ─────────────────────────────────────
const hostingIcoon = (h) => (h === 'saas' ? '☁' : '🏢')

// Fix 1 — tekstkleur volgt de achtergrond-luminantie: wit op donkere nodes, donker op lichte.
function _txtColor(bg) {
  const h = String(bg || '').replace('#', '')
  if (h.length !== 6) return '#1a1a2e'
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16)
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.55 ? '#ffffff' : '#1a1a2e'
}
// LI019 Taak 3 — element_types die géén componenttype zijn (gebruikt door het TYPE-FILTER, dat
// alleen op componenttypes werkt). NB: het type-LABEL onder de node verschijnt sinds de
// vorm-per-type-slice voor ÁLLE typen (zie `_typeRegelVoor`), dit blijft puur de filter-scoping.
const GEEN_COMPONENTTYPE = new Set(['partij', 'gebruikersgroep', 'contract'])
const _heeftTypeLabel = (n) => !!n.element_type && !GEEN_COMPONENTTYPE.has(n.element_type)

// ── Vorm per node-type (kleur blijft status) — ÉÉN gedeelde bron, gelezen door graph + swimlane ──
// Alleen native, labelvriendelijke Cytoscape-vormen; de in de praktijk dicht-bij-elkaar liggende
// paren (leverancier/contract, afdeling/organisatie) krijgen een echt ander silhouet.
const _AARD_VORM = {
  persoon: 'ellipse',            // individu = ovaal
  organisatie: 'hexagon',        // organisatie-koepel
  organisatie_eenheid: 'cut-rectangle', // afdeling — duidelijk anders dan organisatie-hexagon
  externe_partij: 'rhomboid',    // leverancier — schuin blok, duidelijk anders dan contract-tag
}
// LI036 slice 2 — verloop-pijl-marker (ArchiMate/BPMN-processignaal) voor de proces-knoop: een
// SVG-data-URI in de node-ACHTERGROND (CY_STYLE-selector op element_type), zodat de marker bij de
// vorm-definitie hoort en automatisch meereist, mee-dimt (node-opacity) en mee-schaalt met de knoop.
// Kleur parametriseerbaar: donker op de lichte knoop, wit op de grijze legenda-glyph.
const _pijlDataUri = (kleur) => 'data:image/svg+xml;utf8,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M2 8h9M8 4l4 4-4 4" stroke="${kleur}" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`)
const _PROCES_PIJL = _pijlDataUri('#475569')
function _vormVoorType(n) {
  // Bedrijfsfunctie-plek = afgeronde rechthoek MET verloop-pijl (marker via CY_STYLE hieronder) —
  // zelfde basissilhouet als component; de pijl is het onderscheid (ArchiMate BusinessFunction).
  if (n.element_type === 'bedrijfsfunctie') return 'round-rectangle'
  if (n.element_type === 'gebruikersgroep') return 'octagon'        // groep/rol-badge
  if (n.element_type === 'contract') return 'tag'                   // label/"document"
  if (n.element_type === 'partij') return _AARD_VORM[n.soort] || 'round-rectangle'
  if (n.laag === 'technology') return 'barrel'                      // infrastructuur = cilinder
  return 'round-rectangle'                                          // component (application)
}
// Vormen die een ruimer bounding-box nodig hebben om het (tweeregelige) label te bevatten.
const _SHAPE_KLASSE = (shape) =>
  (shape === 'ellipse' || shape === 'barrel') ? 'rond'
  : (shape === 'hexagon' || shape === 'octagon') ? 'veelhoek'
  : null

// Leesbare type-aanduiding (tweede labelregel) voor ÁLLE typen — naast de vorm het tekstsignaal.
const _AARD_LABEL = {
  persoon: 'Persoon', organisatie: 'Organisatie', organisatie_eenheid: 'Afdeling',
  externe_partij: 'Leverancier',
}
function _typeRegelVoor(n) {
  if (n.element_type === 'bedrijfsfunctie') return 'Bedrijfsfunctie' // ADR-043 gate 4 — plek-knoop
  if (n.element_type === 'partij') return _AARD_LABEL[n.soort] || 'Partij'
  if (n.element_type === 'gebruikersgroep') return 'Gebruikersgroep'
  if (n.element_type === 'contract') return 'Contract'
  if (n.laag === 'technology') return 'Infrastructuur'
  return typeLabel(n.element_type) // componenttype, bv. "Applicatie" / "Database"
}

// Legenda-glyphs: CSS-benaderingen van de Cytoscape-vormen (clip-path / border-radius). Neutrale
// grijze vulling — kleur blijft voorbehouden aan status; deze glyphs tonen alléén de vorm→type-uitleg.
const VORM_LEGENDA = [
  // ADR-043 gate 4 — bedrijfsfunctie: zelfde afgeronde rechthoek als component, met de witte verloop-pijl als onderscheid.
  { label: 'Bedrijfsfunctie', stijl: { borderRadius: '3px', backgroundImage: `url("${_pijlDataUri('#ffffff')}")`, backgroundSize: '80%', backgroundRepeat: 'no-repeat', backgroundPosition: 'center' } },
  { label: 'Component', stijl: { borderRadius: '3px' } },
  { label: 'Infrastructuur', stijl: { borderRadius: '50% / 35%' } },
  { label: 'Contract', stijl: { clipPath: 'polygon(0 0,80% 0,100% 50%,80% 100%,0 100%)' } },
  { label: 'Persoon', stijl: { borderRadius: '50%' } },
  { label: 'Gebruikersgroep', stijl: { clipPath: 'polygon(30% 0,70% 0,100% 30%,100% 70%,70% 100%,30% 100%,0 70%,0 30%)' } },
  { label: 'Organisatie', stijl: { clipPath: 'polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)' } },
  { label: 'Afdeling', stijl: { clipPath: 'polygon(15% 0,85% 0,100% 15%,100% 85%,85% 100%,15% 100%,0 85%,0 15%)' } },
  { label: 'Leverancier', stijl: { clipPath: 'polygon(22% 0,100% 0,78% 100%,0 100%)' } },
]
// Uitklapbare legenda — standaard ingeklapt; open/dicht-voorkeur onthouden (sessionStorage, niet-gevoelig).
const _LEGENDA_KEY = 'lk-legenda-open'
const legendaOpen = ref(false)
try { legendaOpen.value = sessionStorage.getItem(_LEGENDA_KEY) === '1' } catch { /* sessionStorage onbereikbaar */ }
function toggleLegenda() {
  legendaOpen.value = !legendaOpen.value
  try { sessionStorage.setItem(_LEGENDA_KEY, legendaOpen.value ? '1' : '0') } catch { /* negeren */ }
}

// LI025 — interactieve legenda-typefilter: klik een vorm-categorie → dat type blijft scherp, alle
// andere nodes dimmen (lk-dim, opacity 0.15); de graaf beweegt NIET (geen relayout, geen verbergen).
// View-only spotlight (buiten `_toestandSig`/history). Predicaat spiegelt `_vormVoorType`/
// `_typeRegelVoor` (één bron).
const legendaTypeFilter = ref(null)
function toggleLegendaFilter(label) {
  legendaTypeFilter.value = legendaTypeFilter.value === label ? null : label
}
const _LEGENDA_MATCH = {
  Bedrijfsfunctie: (n) => n.element_type === 'bedrijfsfunctie', // ADR-043 gate 4
  // Component = de round-rectangle-glyph: alles wat geen bedrijfsfunctie/gg/contract/partij/technology is.
  Component: (n) => n.element_type !== 'bedrijfsfunctie' && n.element_type !== 'gebruikersgroep' && n.element_type !== 'contract' && n.element_type !== 'partij' && n.laag !== 'technology',
  Infrastructuur: (n) => n.laag === 'technology',
  Contract: (n) => n.element_type === 'contract',
  Gebruikersgroep: (n) => n.element_type === 'gebruikersgroep',
  Persoon: (n) => n.element_type === 'partij' && n.soort === 'persoon',
  Organisatie: (n) => n.element_type === 'partij' && n.soort === 'organisatie',
  Afdeling: (n) => n.element_type === 'partij' && n.soort === 'organisatie_eenheid',
  Leverancier: (n) => n.element_type === 'partij' && n.soort === 'externe_partij',
}
function _legendaMatch(n, label) {
  const f = _LEGENDA_MATCH[label]
  return f ? f(n) : true
}
// LI034 — geünificeerde dim-eigenaar (`lk-dim`), twee bronnen met een vaste voorrang:
//   1. node-SELECTIE (enkelklik → `geselecteerdNodeId`): scherp = de node + z'n directe buren
//      (`_burenVan`, uit het grafmodel — NIET cy.neighborhood(), want cy-node-data draagt geen
//      element_type/naam) + de incidente lijnen; al het overige dimt. Zo lees je in één blik
//      "wat raakt dit object".
//   2. legenda-typefilter (`legendaTypeFilter`): spotlight op één vorm-categorie (nodes only).
// Zolang er een selectie is, wint (1); bij deselectie valt het terug op de legenda-staat (2);
// zonder beide → alles neutraal. Mirror van _pasSelectieHighlight (optional-chaining houdt de
// gemockte cytoscape veilig); wordt ook na (her)tekenen aangeroepen (tekenGraaf).
function _pasDim() {
  if (!cy) return
  try {
    const sel = geselecteerdNodeId.value
    if (sel) {
      const scherp = _burenVan(sel)
      scherp.add(sel)
      // LI036 rolbanen — dim matcht op de LOGISCHE id (instances delen `logischId`; buiten Lagen
      // is logischId === id). Edge-incidentie via de logische endpoints (bronLog/doelLog).
      cy.nodes?.()?.forEach?.((node) => {
        const d = node.data?.() || {}
        node[scherp.has(d.logischId || d.id) ? 'removeClass' : 'addClass']?.('lk-dim')
      })
      cy.edges?.()?.forEach?.((edge) => {
        const d = edge.data?.() || {}
        const incident = (d.bronLog || d.source) === sel || (d.doelLog || d.target) === sel
        edge[incident ? 'removeClass' : 'addClass']?.('lk-dim')
      })
    } else {
      cy.edges?.()?.removeClass?.('lk-dim')
      const type = legendaTypeFilter.value
      if (!type) cy.nodes?.()?.removeClass?.('lk-dim')
      else cy.nodes?.()?.forEach?.((node) => {
        const past = _legendaMatch(node.data?.() || {}, type)
        node[past ? 'removeClass' : 'addClass']?.('lk-dim')
      })
    }
  } catch { /* gemockte cytoscape in tests → no-op */ }
  // LI036 — de rol-tag-overlay volgt de ZOJUIST gezette knoop-dim (leest `lk-dim` van het cy-element
  // in updateRolTags — zelfde bron, geen kopie). Draait bij élke dim-wijziging: selectie-wissel en
  // legenda-filter komen hierlangs (watches), de layout-stop roept _pasDim als laatste aan.
  updateRolTags()
}
watch(legendaTypeFilter, _pasDim)

// LI025 — floating/draggable legenda. Standaard rechtsonder (CSS-fallback, x/y = null); slepen zet
// een absolute viewport-positie. Reset naar standaard bij "Begin opnieuw" (wisSet).
// LI038 gate 2 v2 — het sleep-gedrag is geconvergeerd naar de gedeelde `useSleepbaar`-composable
// (zelfde semantiek: DOM-positie-init bij eerste drag, knoppen/links/inputs geen greep, document-
// listeners met opruiming); de proces-diagram-popup is de derde afnemer.
const {
  pos: legendaPos, dragging: legendaDragging,
  onMousedown: onLegendaMousedown, onMousemove: onLegendaMousemove, onMouseup: onLegendaMouseup,
} = useSleepbaar()

// LI034 — sleepbare klik-POPUP (zelfde patroon als de legenda). De popup is hét ene versleepbare
// klik-detail-element (de vroegere sleep op het zijbalk-detailpaneel is vervallen — dat paneel blijft
// gedokt als set-werkblad). null = standaard linksboven op het canvas; slepen zet een viewportpositie
// (zodat je 'm van de opgelichte lijnen af kunt schuiven). Reset naar standaard bij "Begin opnieuw".
const {
  pos: popupPos, dragging: popupDragging,
  onMousedown: onPopupMousedown, onMousemove: onPopupMousemove, onMouseup: onPopupMouseup,
} = useSleepbaar()

// LI019 1d-v5 → LI036 — baan-indeling (Lagen-weergave), afgeleid uit bestaande node-velden. Robuust voor de werkelijke
// data: ÉLK element_type dat geen partij/contract/gebruikersgroep is, is een componenttype →
// componenten (technology-laag → infrastructuur). Zo belanden application-componenten nóóit meer in
// "Overig", ook als `laag` ontbreekt of een componenttype geen application-laag-typing heeft (bug 1).
function _laneVan(n) {
  const et = n.element_type
  if (et === 'bedrijfsfunctie') return 'bedrijfsfuncties' // ADR-043 gate 4 — vóór de rest-tak (anders → componenten)
  if (et === 'gebruikersgroep') return 'gebruikers'
  if (et === 'contract') return 'contracten'
  if (et === 'partij') return 'rollen'
  if (!et) return 'overig'
  return n.laag === 'technology' ? 'infrastructuur' : 'componenten'
}
// Aantal zichtbare INSTANCES per baan (voor lege-baan-detectie en x-spreiding). LI036 — telt de
// instance-projectie: een partij met meerdere petten telt in élke rolbaan die ze raakt.
const _laneTelling = computed(() => {
  const c = {}
  for (const inst of instanceProjectie.value.instances) { c[inst.baan] = (c[inst.baan] || 0) + 1 }
  return c
})
// Zichtbare lanes in gebruikersvolgorde; lege lanes alleen weg als "Verberg lege lanes" aan staat.
const zichtbareLanes = computed(() =>
  laneVolgorde.value
    .filter((k) => LANE_DEF[k])
    .map((key) => ({ key, label: LANE_DEF[key].label, bg: LANE_DEF[key].bg, aantal: _laneTelling.value[key] || 0 }))
    .filter((l) => !verbergLegeLanes.value || l.aantal > 0),
)
// LI019 1d-v6 — per lane: de nodes (gesorteerd) + grid-afmetingen. Lane-hoogte schaalt met het
// aantal rijen (nodes wrappen over LANE_COLS kolommen); lanes worden cumulatief gestapeld (`top`).
// ADR-043 gate 4 (G7) — boom-layout van de bedrijfsfunctie-plekzone: rij = diepte (wortel boven),
// kolommen gegroepeerd per boom. De backend levert PATH-GEËXPANDEERDE plek-knopen (elke plek één
// pad, één ouder) → de bestaande single-parent `procesBoomLayout` past 1-op-1 (geen nieuwe layout).
// Gedeelde pure module (`procesBoom.js`) — de layout-samenval-test draait tegen DEZELFDE definitie.
const _functiePlekBoom = computed(() => {
  const ids = new Set(instanceProjectie.value.instances.filter((i) => i.baan === 'bedrijfsfuncties').map((i) => i.id))
  const hier = grafEdges.value
    .filter((e) => e.relatietype === 'functie_plaatsing')
    .map((e) => ({ bron: e.bron_id, doel: e.doel_id }))
  return procesBoomLayout(ids, hier, (id) => nodePerId.value[id]?.naam || String(id))
})
const laneLayout = computed(() => {
  // LI036 — banen vullen zich met INSTANCES (partij per rolbaan; identiteitsbanen strikt één).
  const perLane = {}
  for (const inst of instanceProjectie.value.instances) {
    ;(perLane[inst.baan] ||= []).push(inst)
  }
  let top = 0
  return zichtbareLanes.value.map((l, index) => {
    const nodes = (perLane[l.key] || []).slice().sort((a, b) => (a.node.naam || '').localeCompare(b.node.naam || ''))
    // ADR-043 gate 4 — de bedrijfsfunctie-plekzone is rij-per-diepte (boom), niet het wrap-grid;
    // alle andere banen exact ongewijzigd (default-pad byte-identiek — de tak hangt aan deze key).
    const rows = l.key === 'bedrijfsfuncties' && nodes.length
      ? _functiePlekBoom.value.rijen
      : Math.max(1, Math.ceil(nodes.length / LANE_COLS))
    const height = Math.max(LANE_MIN_H, rows * NODE_H + 2 * LANE_PAD)
    const band = { key: l.key, label: l.label, bg: l.bg, aantal: l.aantal, leeg: nodes.length === 0, index, top, height, nodes }
    top += height
    return band
  })
})
// Banden voor de overlay = de lane-layout (key/label/kleur/leeg + display-index + model top/height).
const laneBanden = computed(() => laneLayout.value)
function _nodeData(n) {
  const isGG = n.element_type === 'gebruikersgroep'
  // KAART-LEZING (slice A) — de ACTIEVE lezing claimt zijn kleur-kanaal; de andere kanalen worden
  // neutraal (één uniforme tint over álle nodes → geen per-node-variatie die als betekenis leest):
  // status → VULLING = lifecycle-tint; domein → RAND-KLEUR = domeinkleur; werk → RAND-STIJL (cues,
  // in de return hieronder). GG houdt zijn vaste identiteitskleur (context-node, geen lezing). Vorm/
  // selectie/dim/blokkade-label blijven buiten de lezingen.
  const L = lezing.value
  // KAART-LEZING (slice A) VULLING: status → lifecycle-tint; werk → stand-kleur uit de GEDEELDE bron
  // (`standCodering`, slice B2/optie A: het token op tekenmoment geresolved voor het canvas — dezelfde
  // kleur als de lijst-pill, één bron). Alle vijf standen dragen kleur; niet-plek-nodes blijven neutraal.
  const _standKleur = L === 'werk' && n.plek_stand && STAND_CODERING[n.plek_stand]
    ? standKaartKleur(n.plek_stand)
    : null
  let bg = isGG
    ? GG_STYLE.bg
    : L === 'status' ? lcStyle(n.lifecycle_status).bg
    : _standKleur || NEUTRAAL.bg
  let border = isGG
    ? GG_STYLE.border
    : L === 'domein' && n.domein ? domeinKleur.value[n.domein] : NEUTRAAL.border
  // ADR-033 — geen automatische oranje rand; oranje = uitsluitend de selectie (runtime hl-node).
  // VORM = TYPE (vorm-per-type-slice): via de ene gedeelde bron `_vormVoorType` (graph + swimlane).
  // TYPE-LABEL voor ÁLLE typen als tweede tekstsignaal naast de vorm; GG toont ook het ledental.
  let tweede = _typeRegelVoor(n)
  if (isGG && n.aantal_leden > 0) tweede += ` (${n.aantal_leden})`
  const label = (n.naam || '') + (!isGG && n.blokkades_open > 0 ? ' ⚠' : '') + `\n${tweede}`
  // HARDE leesbaarheidseis: tekstkleur ALTIJD via de luminantie van de werkelijke vulkleur (`bg`),
  // voor elke vorm × elke status — nooit een vaste kleur per vorm.
  // LI025 — discriminerende type-velden meegeven, zodat de legenda-dim (`_legendaMatch` op
  // node.data()) het type herkent (anders bevat data() alleen id/label/bg/border/txt/shape).
  return {
    id: n.id, label, bg, border, txt: _txtColor(bg), shape: _vormVoorType(n),
    element_type: n.element_type, laag: n.laag, soort: n.soort,
    // ADR-028 — randbehandeling: alléén externe dataproviders krijgen een afwijkende (gestippelde)
    // rand (CY-selector node[rol="externe_dataprovider"]). Andere rollen dragen géén randsignaal.
    // KAART-LEZING — Werk-cues verschijnen UITSLUITEND in de werk-lezing; in status/domein blijven de
    // randen effen (neutraliseer-model). Slice B2 (LI043): de VIJF plek-standen dragen voortaan KLEUR
    // (de `bg` hierboven, uit de gedeelde bron), niet langer een rand-stijl-reeks — daarom vervallen de
    // plek-gat/plek-via_boven rand-cues hier. De niet-plek-stand Werk-cues blijven rand-stijl:
    // externe_dataprovider · grof-only (identiteit/herkomst, geen plek-stand).
    rol: L === 'werk' && n.componentrol === 'externe_dataprovider' ? 'externe_dataprovider' : null,
    grofOnly: L === 'werk' && grofOnlyIds.value.has(n.id) ? true : undefined,
    // LI037 fase 3d — het vroegere aparte `procesHerkomst`-accent is vervallen: de herkomst-
    // markering is voortaan uitsluitend de bestaande oranje selectie (hl-node).
  }
}
function _edgeData(e, i) {
  let lc = '#94a3b8' // LI019 1d-v5 — iets donkerder default zodat edges tussen lanes goed zichtbaar zijn
  let w = 1.5
  let ls = 'solid'
  // ADR-033 1b — samenstelling ("onderdeel van") gestreept, om visueel te onderscheiden van de
  // doorgetrokken koppelt-met/draait-op/gebruikt-door-relaties.
  if (e.ring === 'samenstelling') ls = 'dashed'
  // ADR-024 — organisatiestructuur ("hoort bij") gestippeld: visueel onderscheidbaar van de
  // doorgetrokken ICT-relaties én van de gestreepte samenstelling; het is context, geen afhankelijkheid.
  if (e.ring === 'organisatiestructuur') ls = 'dotted'
  // ADR-033 — lijnen zijn standaard NEUTRAAL in álle weergaven (geen blanket-oranje meer). Oranje
  // betekent voortaan uitsluitend "de incidente lijnen van het aangeklikte component" — toegepast
  // als runtime `hl-edge`-klasse (zie `_pasSelectieHighlight`), zodat de kleur betekenis houdt.
  // Koppelingsdetails op flow-edges: "koppeling · REST · → · 3×" (→ eenrichting, ↔ twee-/
  // bidirectioneel; "N×" alleen bij ≥2 samengetrokken koppelingen op dit paar — ADR-023a Fase 3).
  let label = ''
  if (e.ring === 'applicaties') {
    const pijl = e.richting === 'tweerichting' || e.richting === 'bidirectioneel' ? '↔' : '→'
    label = ['koppeling', e.protocol ? String(e.protocol).toUpperCase() : null, pijl, e.aantal >= 2 ? `${e.aantal}×` : null].filter(Boolean).join(' · ')
  } else if (e.ring === 'bedrijfsfuncties') {
    // ADR-043 gate 4 — de systeem→plek-lijn draagt "ondersteunt"; de plek-hiërarchie "onderdeel
    // van". Geen N×-bundeling: elke edge is precies één systeem→plek of één plek→ouder-plek.
    label = e.label || ''
  } else {
    // ADR-031 — rol-naam / 'gebruikt door' / 'valt onder' / 'draait op' uit de edge-data.
    label = e.label || ''
  }
  // LI023 — labels staan default verborgen (text-opacity:0) en verschijnen bij hover (alle modi).
  // LI036 — bronLog/doelLog = de LOGISCHE endpoints (bij een rol-instance-remap wijken source/target
  // af); de edge-tap-resolutie en de dim-op-klik matchen dáárop.
  return {
    id: `e${i}-${e.bron_id}-${e.doel_id}-${e.relatietype}`, source: e.bron_id, target: e.doel_id, ring: e.ring, lc, w, ls, label,
    bronLog: e.bron_logisch || e.bron_id, doelLog: e.doel_logisch || e.doel_id,
  }
}
// LI036 "ring uit wint" — baan→ring-map voor de gaps-inperking: een écht relatie-loze knoop
// (registratiegap) toont onder de toggle alléén als de ring van zijn CATEGORIE aan staat
// (categorie via _laneVan; de componenten-baan hoort bij de 'applicaties'-ring). 'overig'
// (categorieloos) heeft geen ring → altijd tonen onder de toggle — daar is niets uitgezet, en
// stil verbergen zou een echte gap onzichtbaar maken.
const _BAAN_RING = { bedrijfsfuncties: 'bedrijfsfuncties', rollen: 'rollen', gebruikers: 'gebruikers', componenten: 'applicaties', infrastructuur: 'infrastructuur', contracten: 'contracten' }
// LI020 → LI036 — definitieve node-set voor het canvas (IDENTIEK voor alle weergaven — Lagen is
// enkel een andere layout, geen andere set). "Ring uit wint": zichtbaar is wat de AANstaande
// ringen dragen — een knoop is zichtbaar als hij het ego-centrum of een set-lid is (bewuste
// keuzes), OF hij minstens één ZICHTBARE (ring-aan) edge raakt, OF hij onder "Toon
// registratiegaps" een échte gap is (geen énkele relatie) in een categorie waarvan de ring aan
// staat. Een knoop die alléén via uitgezette ringen relaties had, valt dus weg — óók met de
// gaps-toggle aan, en óók in de Lagen-weergave (de vroegere banen-uitzondering is vervallen).
// LI036 organisatiebalk — het getekend-predicaat als FUNCTIE over een aangeleverde zichtbaar-set,
// zodat de balk-lijst dezelfde regels contrafeitisch kan draaien. `getekendeNodes` = deze functie
// over de gewone `zichtbareNodes`; de edges worden per set via `_edgesBinnen` bepaald (voor de
// echte weergave identiek aan `zichtbareEdges`).
function _bepaalGetekend(nodesArr) {
  const ids = new Set(nodesArr.map((n) => n.id))
  const edges = _edgesBinnen(ids)
  const metZichtbareEdge = new Set()
  edges.forEach((e) => { metZichtbareEdge.add(e.bron_id); metZichtbareEdge.add(e.doel_id) })
  // Alle relaties, ring-ONGEACHT — onderscheidt "échte gap" van "alleen-via-uitgezette-ring".
  const heeftRelatie = new Set()
  grafEdges.value.forEach((e) => { heeftRelatie.add(e.bron_id); heeftRelatie.add(e.doel_id) })
  // LI027 — focus op actieve set: beperk tot de set-nodes (altijd) + hun directe buren via een zichtbare edge.
  let focusIds = null
  if (focusOpSet.value && actieveSet.value.size > 0) {
    focusIds = new Set(actieveSet.value)
    edges.forEach((e) => {
      if (actieveSet.value.has(e.bron_id)) focusIds.add(e.doel_id)
      if (actieveSet.value.has(e.doel_id)) focusIds.add(e.bron_id)
    })
  }
  const uniek = new Map()
  for (const n of nodesArr) {
    if (uniek.has(n.id)) continue
    if (focusIds) {
      if (focusIds.has(n.id)) uniek.set(n.id, n) // focus-modus: set-nodes + directe buren
      continue
    }
    const egoCentrum = modus.value === 'ego' && n.id === egoStartId.value
    // LI034 bug A — een GEKOZEN component (set-lid) altijd tekenen, óók zonder zichtbare edges. Analoog
    // aan de `egoCentrum`-uitzondering (die op de praatplaat de relatie-loze node al tekent): "ik koos
    // dit → ik hoor het te zien", geen leeg canvas op Overzicht. Type-agnostisch. Niet-gekozen losse
    // nodes blijven de bewuste registratiegaten-keuze (verborgen tenzij `toonRegistratiegaps`).
    const setLid = actieveSet.value.has(n.id)
    // LI036 "ring uit wint" — de ring-bewuste gaps-term vervangt de twee kale termen (de vroegere
    // `weergave==='lagen'`-banen-uitzondering en de kale gaps-toggle): een gap toont alleen als hij
    // ÉCHT relatie-loos is én de ring van zijn categorie aan staat ('overig' = geen ring = tonen).
    const catRing = _BAAN_RING[_laneVan(n)]
    const gapZichtbaar = toonRegistratiegaps.value && !heeftRelatie.has(n.id) && (!catRing || ringAan.value.has(catRing))
    if (gapZichtbaar || egoCentrum || setLid || metZichtbareEdge.has(n.id)) uniek.set(n.id, n)
  }
  return [...uniek.values()]
}
const getekendeNodes = computed(() => _bepaalGetekend(zichtbareNodes.value))

// LI036 organisatiebalk (model i) — de balk toont alleen organisaties die bij de HUIDIGE selectie in
// beeld (zouden) zijn: dezelfde pipeline (zichtbaar → getekend, dus ná ringen/"ring uit wint"/filters/
// focus, cross-view identiek), maar met de org-vinkjes weggedacht. Zo valt een geladen-maar-irrelevante
// organisatie (het RID-geval) weg, én blijft een UITGEZETTE organisatie zichtbaar-onaangevinkt in de
// balk zolang de selectie haar relevant maakt (focussen blijft omkeerbaar). Kleine benadering: álle
// org-vinkjes worden samen weggedacht (één extra pipeline-run i.p.v. één per organisatie) — verschil
// kan alleen ontstaan via org↔org-edges (organisatiestructuur, default uit).
const organisatiesInBeeld = computed(() =>
  _bepaalGetekend(_bepaalZichtbaar((n) => _isOrg(n) || _inScope(n))).filter(_isOrg),
)

// LI034 bug A — getekende set-leden ZONDER zichtbare relatie (op Overzicht): eerlijk benoemen dat het
// component nog geen relaties in beeld heeft (gaten tonen, niet verbergen). Alleen op Overzicht — op de
// praatplaat is de relatie-loze node het centrum en spreekt dat voor zich.
const relatieLozeSetLeden = computed(() => {
  if (weergave.value !== 'overzicht') return []
  const metEdge = new Set()
  zichtbareEdges.value.forEach((e) => { metEdge.add(e.bron_id); metEdge.add(e.doel_id) })
  return getekendeNodes.value.filter((n) => actieveSet.value.has(n.id) && !metEdge.has(n.id))
})

// ── LI036 rolbanen — instance-projectielaag (Lagen-only) ─────────────────────────────────────────
// Rol-afleiding per partij uit de RING van haar zichtbare edges (de rol zit al op elke geladen edge;
// puur frontend, geen backend). Ring → rol: gebruikt → 'gebruikt'; rollen (beheerorganisatie) →
// 'beheert'; eigenaar → 'eigenaar'; contracten+relatietype 'leverancier' ("geleverd door") → 'levert'.
function _rollenVanPartij(id, edges) {
  const rollen = new Set()
  for (const e of edges) {
    if (e.bron_id !== id && e.doel_id !== id) continue
    if (e.ring === 'gebruikt') rollen.add('gebruikt')
    else if (e.ring === 'rollen') rollen.add('beheert')
    else if (e.ring === 'eigenaar') rollen.add('eigenaar')
    else if (e.ring === 'contracten' && e.relatietype === 'leverancier') rollen.add('levert')
  }
  return rollen
}
// De projectie tussen de LOGISCHE laag (getekendeNodes/zichtbareEdges) en de teken-/banenlaag
// (_elementen/laneLayout) — naar het gg-aggregatie-precedent (grafNodes/grafEdges hierboven):
// - ALLEEN in de Lagen-weergave actief; daarbuiten 1-op-1 door (Overzicht/Praatplaat ongewijzigd).
// - Identiteitsbanen (component/infra/contract/gebruikersgroep) — strikt één instance per object.
// - PARTIJEN op hun rol: per geraakte rolbaan een visuele instance (gebruikt → Gebruikers;
//   beheert/eigenaar/levert → Rollen & beheer). Meerdere petten = meerdere instances (id
//   `<partijId>@<baan>`, zelfde `_nodeData`-uiterlijk, gedeelde `logischId`); één pet houdt de
//   logische id. Partij zonder rol in deze selectie → Rollen & beheer zónder rol-tag (besluit B).
// - Rol-edges hangen aan de instance van hun EIGEN ring (gebruikt-edge → @gebruikers; rol-/
//   eigenaar-/levert-edge → @rollen); overige partij-edges (bv. organisatiestructuur) → de
//   @rollen-instance, met fallback naar de enige bestaande instance (gemarkeerde default).
const instanceProjectie = computed(() => {
  const zn = getekendeNodes.value
  const znIds = new Set(zn.map((n) => n.id))
  const ze = zichtbareEdges.value.filter((e) => znIds.has(e.bron_id) && znIds.has(e.doel_id))
  if (weergave.value !== 'lagen') {
    return { instances: zn.map((n) => ({ node: n, id: n.id, logischId: n.id, baan: _laneVan(n), rollen: [] })), edges: ze }
  }
  const instances = []
  const instMap = new Map() // partij-logischId → { gebruikers?: instanceId, rollen?: instanceId }
  for (const n of zn) {
    if (n.element_type !== 'partij') {
      instances.push({ node: n, id: n.id, logischId: n.id, baan: _laneVan(n), rollen: [] })
      continue
    }
    const rollen = _rollenVanPartij(n.id, ze)
    const banen = []
    if (rollen.has('gebruikt')) banen.push(['gebruikers', ['gebruikt']])
    const rb = _ROLLEN_RB.filter((r) => rollen.has(r))
    if (rb.length || !banen.length) banen.push(['rollen', rb]) // rol-loos → Rollen & beheer, zonder tag
    const m = {}
    for (const [baan, rs] of banen) {
      const iid = banen.length > 1 ? `${n.id}@${baan}` : n.id // suffix alleen bij meerdere petten
      m[baan] = iid
      instances.push({ node: n, id: iid, logischId: n.id, baan, rollen: rs })
    }
    instMap.set(n.id, m)
  }
  const instVoor = (logischId, ring) => {
    const m = instMap.get(logischId)
    if (!m) return logischId // geen partij → identiteit
    if (ring === 'gebruikt') return m.gebruikers || m.rollen
    return m.rollen || m.gebruikers // rol-/eigenaar-/levert-/context-edges → de wie-baan-instance
  }
  const edges = ze.map((e) => {
    const b = instVoor(e.bron_id, e.ring)
    const d = instVoor(e.doel_id, e.ring)
    return b === e.bron_id && d === e.doel_id ? e : { ...e, bron_id: b, doel_id: d, bron_logisch: e.bron_id, doel_logisch: e.doel_id }
  })
  return { instances, edges }
})

// LI019 1d-v2 — geen compound-parents meer: lanes zijn een HTML-overlay (zie laneBanden/bandPx),
// niet langer cytoscape-nodes. Daardoor renderen edges tussen lanes weer normaal (correctie 3).
// LI036 — de teken-elementen komen uit de instance-projectie (buiten Lagen = identiek aan voorheen).
// Instances delen de ENE knoop-stijlbron (`_nodeData` van de onderliggende node); alleen id/
// logischId/rollen komen erbij (rand/vulling/vorm/label onaangeroerd).
function _elementen() {
  const { instances, edges } = instanceProjectie.value
  return [
    ...instances.map((inst) => {
      const d = _nodeData(inst.node)
      return { data: { ...d, id: inst.id, logischId: inst.logischId, rollen: inst.rollen }, classes: _SHAPE_KLASSE(d.shape) || undefined }
    }),
    ...edges.map((e, i) => ({ data: _edgeData(e, i) })),
  ]
}
const zichtbaarAantal = computed(() => getekendeNodes.value.length)

// LI019 1d (Taak 4) — ná de layout(-animatie): bij radiaal-Ego centreren op het centrum-component,
// anders fit op het geheel. Wordt als layout-`stop`-callback gebruikt voor élke layout, zodat een
// wijziging (filter/ring/selectie/view/layout) automatisch herpositioneert + centreert. Raakt geen
// reactieve state aan → geen layout-her-trigger-loop.
// ADR-040 F1 (Praatplaat-ellips) — ná de concentric-plaatsing de radiale kring uitrekken tot een ELLIPS
// die de VENSTERVERHOUDING volgt: in een liggend venster breder dan hoog, zodat de brede ruimte benut
// wordt en buren meer onderlinge afstand krijgen (betere leesbaarheid). Deterministisch (leest cy-state,
// past een schaling toe — geen re-layout/timing-hack) en alléén in de Praatplaat (ego). We rekken UIT
// langs de langere canvas-as en comprimeren NOOIT → geen nieuwe overlap. Mild geclamped (max 1.7) zodat
// het bij weinig buren een lichte ellips blijft, niet een lelijke vervorming.
function _ellipsPraatplaat() {
  // `modus === 'ego'` impliceert weergave 'praatplaat' (de concentric-tak) — in 'lagen' kan dit niet.
  if (!cy || modus.value !== 'ego') return
  const w = cy.width?.() || 0
  const h = cy.height?.() || 0
  if (!(w > 0) || !(h > 0)) return
  const ar = w / h
  let fx = 1, fy = 1
  if (ar > 1) fx = Math.min(ar, 1.7)            // liggend → horizontaal uitrekken
  else if (ar < 1) fy = Math.min(1 / ar, 1.7)   // staand → verticaal uitrekken
  if (fx === 1 && fy === 1) return
  const c = egoStartId.value ? cy.getElementById?.(String(egoStartId.value)) : null
  let cx, cyy
  if (c && c.length) { const p = c.position(); cx = p.x; cyy = p.y }
  else { const bb = cy.elements().boundingBox(); cx = (bb.x1 + bb.x2) / 2; cyy = (bb.y1 + bb.y2) / 2 }
  cy.nodes().forEach((n) => {
    const p = n.position()
    n.position({ x: cx + (p.x - cx) * fx, y: cyy + (p.y - cyy) * fy })
  })
}
function _naLayout() {
  if (!cy) return // LI036 — de viewport-behoud-vlag is vervallen (maatwissel herfit via _pasCanvasMaat)
  // ADR-040 F1 — de fit/resize + het opnieuw aanbrengen van highlight/legenda-dim horen DETERMINISTISCH
  // bij het EINDE van de layout (deze stop-callback), niet in een losse `setTimeout` in tekenGraaf.
  // Eerst her-meten (de flex-hoogte kan later gezet zijn), dan fitten/centreren.
  cy.resize?.()
  _ellipsPraatplaat() // Praatplaat-kring → ellips op vensterverhouding (vóór fit/center)
  // LI019 1d-v4 (bug 5) — centreer alléén op het ego-centrum ná een expliciete recenter (dubbelklik/
  // set-klik); bij elke andere wijziging (m.n. een filter die de node-set verandert) → fit op het
  // geheel, zodat de zichtbare nodes altijd in beeld komen.
  if (_recenterPending && modus.value === 'ego' && egoStartId.value) {
    _recenterPending = false
    const c = cy.getElementById?.(String(egoStartId.value))
    if (c && c.length) cy.center?.(c)
    else cy.fit?.(undefined, 50)
  } else {
    _recenterPending = false // recenter-verzoek geconsumeerd (bv. in de Lagen-weergave waar niet gecentreerd wordt)
    cy.fit?.(undefined, 50)
  }
  updateBands()
  updateRolTags() // LI036 — rol-tag-overlay volgt de verse posities (zelfde stop-moment als de banden)
  _pasSelectieHighlight() // ADR-033 — na een (her)tekening de selectie-highlight opnieuw aanbrengen
  _pasDim() // LI025/LI034 — en de dim (selectie of legenda; nieuwe node-objecten dragen de klasse nog niet)
}
// LI019 1d-v6 — swimlane-posities: nodes in een GRID per lane (LANE_COLS kolommen, wrappend over
// meerdere rijen), gecentreerd per rij. Begrensde breedte → geen extreme uitzoom (kernoorzaak B).
// Object-map {nodeId:{x,y}} (Cytoscape lookt id zelf op).
function _swimlanePositions() {
  const pos = {}
  for (const lane of laneLayout.value) {
    const { nodes, top } = lane
    // ADR-043 gate 4 — bedrijfsfunctie-plekzone als BOOM: rij = diepte, kolom uit de gedeelde
    // boom-layout (gegroepeerd per wortelfunctie), horizontaal gecentreerd rond 0 zoals de anderen.
    if (lane.key === 'bedrijfsfuncties' && nodes.length) {
      const boom = _functiePlekBoom.value
      const off = (boom.kolommen - 1) / 2
      nodes.forEach((n) => {
        const kol = boom.kolom.get(n.id) ?? 0
        const rij = boom.rij.get(n.id) ?? 0
        pos[n.id] = { x: (kol - off) * NODE_W, y: top + LANE_PAD + rij * NODE_H + NODE_H / 2 }
      })
      continue
    }
    const count = nodes.length
    nodes.forEach((n, xi) => {
      const row = Math.floor(xi / LANE_COLS)
      const rowStart = row * LANE_COLS
      const rowCount = Math.min(LANE_COLS, count - rowStart) // nodes op deze (mogelijk laatste) rij
      const colInRow = xi - rowStart
      const x = (colInRow - (rowCount - 1) / 2) * NODE_W // rij horizontaal gecentreerd rond 0
      const y = top + LANE_PAD + row * NODE_H + NODE_H / 2
      pos[n.id] = { x, y }
    })
  }
  return pos
}
// LI019 1d-v6 — sync de HTML-band-overlay met cy's pan/zoom: per-lane model-top/-hoogte → schermpixels.
// Banden zijn altijd volledige canvasbreedte (CSS); alleen verticale positie/hoogte volgen pan/zoom.
function updateBands() {
  if (!cy || weergave.value !== 'lagen') { bandPx.value = []; return }
  const zoom = cy.zoom?.() || 1
  const pan = cy.pan?.() || { x: 0, y: 0 }
  bandPx.value = laneBanden.value.map((b) => ({ top: b.top * zoom + pan.y, height: b.height * zoom }))
}
// LI036 rolbanen — rol-tag-overlay: kleine HTML-pills (kleur + kort woord) ónder elke rol-instance.
// Zelfde overlay-patroon als de banden (HTML rond het canvas, gesynct op pan/zoom/layout-stop);
// kleuren uit de ene ROL_TAG-bron; pointer-events-none (kliks gaan naar de knoop). In de gemockte
// suite ontbreekt renderedBoundingBox → overlay blijft daar leeg (browsercheck is het bewijs).
const rolTagPx = ref([])
function updateRolTags() {
  if (!cy || weergave.value !== 'lagen') { rolTagPx.value = []; return }
  const uit = []
  for (const inst of instanceProjectie.value.instances) {
    if (!inst.rollen.length) continue
    const el = cy.getElementById?.(String(inst.id))
    if (!el || !el.length || typeof el.renderedBoundingBox !== 'function') continue
    const bb = el.renderedBoundingBox()
    // LI036 — de tag deelt de dim-staat van zijn KNOOP: lees de `lk-dim`-class die `_pasDim` (de ene
    // dim-eigenaar) zojuist op het cy-element zette — geen parallelle dim-berekening.
    uit.push({ id: inst.id, x: (bb.x1 + bb.x2) / 2, y: bb.y2, rollen: inst.rollen, dim: !!el.hasClass?.('lk-dim') })
  }
  rolTagPx.value = uit
}
// LI019 1d-v3 — lanevolgorde herschikken door de lane-header op het canvas te verslepen.
// `_herschikLane` is de pure reorder: verplaats `bron` naar de positie van `doel`, persisteer
// direct in sessionStorage en bevestig met een subtiele toast. Geen aparte bewaar-knop.
function _herschikLane(bronKey, doelKey) {
  if (!bronKey || !doelKey || bronKey === doelKey) return
  if (!LANE_DEF[bronKey] || !LANE_DEF[doelKey]) return
  const order = laneVolgorde.value.filter((k) => k !== bronKey)
  order.splice(order.indexOf(doelKey), 0, bronKey)
  laneVolgorde.value = order
  _bewaarKaartState()
  toast?.add?.({ severity: 'success', summary: 'Volgorde opgeslagen', life: 2000 })
}
// Welke lane ligt onder schermpositie clientY (voor drop-bepaling tijdens het slepen)?
function _laneOpY(clientY) {
  const rect = containerRef.value?.getBoundingClientRect?.()
  if (!rect) return null
  const y = clientY - rect.top
  for (const b of laneBanden.value) {
    const px = bandPx.value[b.index]
    if (px && y >= px.top && y < px.top + px.height) return b.key
  }
  return null
}
const sleepLane = ref(null) // key van de lane die nu versleept wordt (voor de visuele hint)
function onLaneSleepStart(e, key) {
  sleepLane.value = key
  e.currentTarget?.setPointerCapture?.(e.pointerId)
}
function onLaneSleepEinde(e) {
  if (!sleepLane.value) return
  const doel = _laneOpY(e.clientY)
  if (doel) _herschikLane(sleepLane.value, doel)
  sleepLane.value = null
}
function _layout(geenAnimatie = false) {
  // ADR-040 F1 (layout-stap) — DETERMINISTISCH & NIET-GEANIMEERD. De vroegere 400ms-fly-in animeerde de
  // nodes vanaf hun verse (0,0)-positie (elke render doet `cy.add` opnieuw); op een dichte graaf (o.a. de
  // 3-1 gebruikt-edges die de degree opblazen) settelden ze niet naar distincte posities → knopen vielen
  // samen ("source/target overlap" → leeg-ogend canvas). `animate:false` legt élke node meteen op zijn
  // concentric-doel (bewezen: dezelfde config zónder animatie deelt distincte posities uit). `geenAnimatie`
  // (history-herstel) blijft bestaan als parameter maar is nu de standaard.
  void geenAnimatie
  const anim = { animate: false }
  // LI019 1d (Taak 2) → LI036 — Lagen-weergave: custom preset-posities per laag-baan (0 nieuwe
  // dependencies; bewust GEEN compound-nodes — dat brak eerder de edge-rendering + pointer-events).
  // `positions` als object-map {nodeId: {x,y}} (Cytoscape doet de id-lookup zelf) — géén callback
  // met `node.id` (= de id-METHODE, niet de string). animate:false + fit:true geeft een direct,
  // correct geplaatst raster; de stop-callback fit + sync't de overlay als vangrail.
  if (weergave.value === 'lagen') {
    // LI036-fix (render-eigenaar voltooid t/m Lagen) — de ingebouwde layouts MÉTEN vóór het
    // positioneren álle knopen (concentric: `nodes.updateStyle()` + `layoutDimensions` per node,
    // concentric.mjs:76/:81; grid: `layoutDimensions` in het avoidOverlap-pad). De preset-layout
    // meet niets, waardoor de éérste frame ná het schakelen de edge-endpointgeometrie
    // (knopen zijn `width/height:'label'`) nog niet had en álle lijnen de eerste paint oversloegen
    // (elke klik = style-invalidatie = alsnog tekenen; LI019 maskeerde dit met de setTimeout(100)-
    // fit die ADR-040 terecht door de stop-callback verving). Dezelfde meet-stap hier — een
    // SYNCHRONE stateberekening binnen de ene render-eigenaar (opbouw → layout → stop-fit),
    // géén timing-nudge/extra teken-cyclus.
    const ns = cy?.nodes?.()
    ns?.updateStyle?.()
    ns?.forEach?.((n) => n.layoutDimensions?.({ nodeDimensionsIncludeLabels: true }))
    return { name: 'preset', positions: _swimlanePositions(), animate: false, fit: true, padding: 60, stop: _naLayout }
  }
  // ADR-040 F1 (stap 1+3) — DETERMINISTISCH & FCOSE-VRIJ. Geen positie-behoud (`vorigePosities`) en
  // geen preset/fcose-mix-tak meer: die mix-tak viel bij node-set-groei terug op fcose, hét pad met
  // de edges-onzichtbaar-render-bug (lijnen weg bij scope-re-check / buren toevoegen). Elke render legt
  // zich nu opnieuw, deterministisch (concentric) uit.
  // Ego: concentric met het geselecteerde component centraal.
  // ADR-040 F1 (layout-leesbaarheid) — ONDERLINGE AFSTAND. `nodeDimensionsIncludeLabels:true` reserveert
  // al de GEMETEN node-grootte (labelbreedte); `minNodeSpacing` is daarbovenop enkel een kleine GAP en
  // `spacingFactor` blijft 1.0 (géén globale opblazing). De eerdere 90px-gap × 1.6 zette knopen véél te
  // ver uiteen (labels onleesbaar zodra de plaat paste). Nu: knopen dicht genoeg voor leesbare labels
  // zonder inzoomen, maar niet overlappend. (Fijn-afstemming is een browsercheck-criterium — headless
  // meet labelbreedte niet.)
  if (modus.value === 'ego') {
    return {
      name: 'concentric', concentric: (n) => (n.id() === egoStartId.value ? 10 : 5), levelWidth: () => 1,
      minNodeSpacing: 25, spacingFactor: 1.0, padding: 40, nodeDimensionsIncludeLabels: true, ...anim, stop: _naLayout,
    }
  }
  // Overzicht (geheel): een CENTRUMLOZE, gebalanceerde plaat — geen ster/verticale as (concentric legt
  // ringen rond één centrum op, terwijl het Overzicht geen natuurlijk middelpunt heeft). Gekozen: de
  // built-in `grid` — deterministisch (identieke posities bij herhaling), stabiel, géén externe/afwezige
  // layout-plugin (cose/fcose zijn niet-deterministisch en zijn juist afgeschaft wegens de edges-
  // onzichtbaar-bug). `avoidOverlap` + `nodeDimensionsIncludeLabels` houden de (grotere) knopen uit elkaar
  // op basis van hun GEMETEN grootte. De Praatplaat houdt hierboven de radiale concentric-layout.
  return {
    name: 'grid', avoidOverlap: true, avoidOverlapPadding: 24, nodeDimensionsIncludeLabels: true,
    condense: false, padding: 40, ...anim, stop: _naLayout,
  }
}

async function tekenGraaf() {
  if (!cy) return
  // Consumeer de herstel-vlag synchroon bij het starten (vóór de awaits), zodat exact de
  // door dit herstel uitgelokte (her)tekening zonder animatie verloopt.
  const _geenAnim = _herstelZonderAnimatie
  _herstelZonderAnimatie = false
  await nextTick()
  await nextTick() // tweede tick voor (HMR-)edge cases waarin de layout nog niet geflusht is
  // Cytoscape meet zijn container soms op 0 (flex-hoogte nog niet gezet) → forceer een hoogte
  // zodat de graaf nooit op 0px initialiseert en zichtbaar blijft i.p.v. leeg.
  const el = containerRef.value
  if (el && el.offsetHeight === 0) el.style.minHeight = '500px'
  // ADR-040 F1 (stap 1+3) — geen positie-behoud meer: elke render legt zich deterministisch (concentric)
  // opnieuw uit. De `vorigePosities`-capture + de preset/fcose-mix-tak zijn vervallen (fcose weg).
  cy.elements().remove()
  cy.add(_elementen())
  cy.layout(_layout(_geenAnim)).run()
  // ADR-040 F1 — geen losse `setTimeout`-fit meer: de her-meting + fit/centrering + highlight/dim lopen
  // deterministisch via de layout-stop-callback (`_naLayout`), zodat ze exact ná de layout gebeuren.
}

const CY_STYLE = [
  {
    selector: 'node',
    style: {
      'background-color': 'data(bg)', 'border-color': 'data(border)', 'border-width': 2,
      // ADR-040 F1 (layout-leesbaarheid) — GROTERE knopen: font 11 → 14, ruimere text-max-width + padding,
      // zodat namen zonder inzoomen goed leesbaar zijn (node-grootte volgt het label via width:'label').
      label: 'data(label)', 'font-size': 14, color: 'data(txt)', 'text-valign': 'center', 'text-halign': 'center',
      // Vorm-per-type-slice — elk type heeft nu een tweeregelig label (naam + type): wrap aan,
      // hoogte volgt het label, ruime padding zodat de type-regel onder de naam past.
      width: 'label', height: 'label', shape: 'data(shape)', 'text-wrap': 'wrap', 'text-max-width': 180,
      'padding-left': 16, 'padding-right': 16, 'padding-top': 9, 'padding-bottom': 9,
    },
  },
  // ADR-043 gate 4 — bedrijfsfunctie-plek: afgeronde rechthoek + VERLOOP-PIJL-marker (rechtsonder,
  // in de padding-zone). Hoort bij de vorm-definitie (geen aparte overlay): dimt en schaalt mee.
  {
    selector: 'node[element_type = "bedrijfsfunctie"]',
    style: {
      'background-image': _PROCES_PIJL, 'background-width': 12, 'background-height': 12,
      'background-position-x': '96%', 'background-position-y': '90%', 'background-clip': 'none',
    },
  },
  // Ronde vormen (ellipse/barrel) clippen het label aan de randen → ruimere padding.
  { selector: 'node.rond', style: { 'padding-left': 18, 'padding-right': 18, 'padding-top': 12, 'padding-bottom': 12 } },
  // Veelhoeken (hexagon/octagon) knijpen het label aan de hoeken → ruimere padding.
  { selector: 'node.veelhoek', style: { 'padding-left': 16, 'padding-right': 16, 'padding-top': 12, 'padding-bottom': 12 } },
  // ADR-028 — externe dataprovider: afwijkende (gestippelde, dikkere) rand. Géén nieuwe vulkleur;
  // vorm blijft = type, vulkleur blijft = lifecycle; de rand-KLEUR blijft data(border). Selectie/
  // highlight-regels hieronder winnen (staan later en zetten border-style terug op solid).
  { selector: 'node[rol="externe_dataprovider"]', style: { 'border-style': 'dashed', 'border-width': 3 } },
  // LI033 — grof-only ("nog niet verfijnd"): rustige, gestippelde rand. Géén nieuwe vulkleur; de
  // rand-KLEUR blijft data(border) (lifecycle). Onderscheidbaar van de gestreepte externe-dataprovider;
  // selectie/highlight-regels hieronder winnen (staan later en zetten border-style terug op solid).
  { selector: 'node[?grofOnly]', style: { 'border-style': 'dotted', 'border-width': 3 } },
  // ADR-043 gate 4 (G8) — de plek-standen (gat/via_boven/hier/werkvoorraad/niets) dragen sinds slice B2
  // (LI043) KLEUR als vulling (uit `standCodering`, in `_nodeData` onder de werk-lezing), niet meer een
  // rand-stijl-reeks. De vroegere `node[?procesGap]`/`node[?plekViaBoven]` rand-cues zijn daarmee vervallen.
  {
    selector: 'edge',
    style: {
      width: 'data(w)', 'line-color': 'data(lc)', 'line-style': 'data(ls)',
      'target-arrow-shape': 'triangle', 'target-arrow-color': 'data(lc)', 'curve-style': 'bezier',
      // Koppelingsdetail-label (flow-edges): protocol + richting.
      // Concrete hex i.p.v. een CSS-custom-property: cytoscape resolvet `var(--…)` niet (invalide-color-
      // warning) — dezelfde muted-grijs als de UI-tekst, nu wél door cytoscape leesbaar. Font 8 → 10 mee
      // vergroot met de knopen, zodat de lijn-teksten óók zonder inzoomen leesbaar zijn.
      label: 'data(label)', 'font-size': 10, color: '#64748b', 'text-wrap': 'none',
      'text-opacity': 0, // LI023 — default verborgen; zichtbaar bij hover (mouseover-handler)
      'text-rotation': 'autorotate', 'text-background-color': '#fff', 'text-background-opacity': 0.8,
    },
  },
  // B1 — aangeklikte edge gemarkeerd zolang de popup open is (accentkleur + dikker).
  { selector: 'edge.sel-edge', style: { 'line-color': '#e67e22', 'target-arrow-color': '#e67e22', width: 4, 'z-index': 999, 'text-opacity': 1 } },
  // ADR-033 — selectie-highlight: alléén de incidente lijnen van het aangeklikte component +
  // de knoop zelf krijgen de oranje SELECTIE_RAND (één gedeelde kleurbron).
  { selector: 'edge.hl-edge', style: { 'line-color': SELECTIE_RAND, 'target-arrow-color': SELECTIE_RAND, width: 2.5, 'z-index': 900 } },
  { selector: 'node.hl-node', style: { 'border-width': 3, 'border-color': SELECTIE_RAND, 'border-style': 'solid' } },
  // LI025 — legenda-typefilter: niet-matchende nodes dimmen (spotlight op het gekozen type).
  // LI034 — óók de dim-op-klik (selectie): scherp blijft de node + z'n directe buren + incidente
  // lijnen; al het overige dimt. Zelfde `lk-dim`-klasse, gedeelde teken-eigenaar `_pasDim`.
  { selector: 'node.lk-dim', style: { opacity: DIM_NODE_OPACITY } },
  // Gedimde lijnen (niet-incident aan de selectie) sterker terugleggen dan nodes, zodat het
  // opgelichte relatie-web rust krijgt; edge-labels van gedimde lijnen verdwijnen.
  { selector: 'edge.lk-dim', style: { opacity: 0.12, 'text-opacity': 0 } },
  // Fix 3: visuele markering van de geselecteerde node (klik op set-item / node).
  { selector: 'node:selected', style: { 'border-width': 4, 'border-color': SELECTIE_RAND, 'border-style': 'solid' } },
]

let resizeObserver = null

// LI022 — kaart-UI-state bewaren over navigatie heen (sessionStorage; transient UI-state, geen Pinia).
const _LK_STATE_KEY = 'lk-state'
function _bewaarKaartState() {
  try {
    sessionStorage.setItem(_LK_STATE_KEY, JSON.stringify({
      // ADR-040 — de modus is een dunne adapter op de weergave; bewaar de ACTIEVE SET zodat het beeld
      // (overzicht/praatplaat) behouden blijft bij terugnavigatie. Geen dode `modus`-sleutel.
      actieveSet: [...actieveSet.value],
      // LI036 — de weergave zelf is een MOMENTKEUZE en wordt bewust niet bewaard (LI034-sortering);
      // de baan-opties (volgorde/verberg-leeg) zijn kijk-voorkeuren en reizen wél mee.
      laneVolgorde: laneVolgorde.value,
      verbergLegeLanes: verbergLegeLanes.value,
      toonRegistratiegaps: toonRegistratiegaps.value,
      egoStartId: egoStartId.value,
      ringAan: [...ringAan.value],
      groepeerPerOrg: groepeerPerOrg.value,
      // KAART-LEZING (slice A) — session-persistent (zoals de overige lk-state), NIET de cross-device
      // voorkeur-laag (ADR-041 "onthoud als mijn standaard" is een latere additieve stap).
      lezing: lezing.value,
    }))
  } catch { /* sessionStorage niet beschikbaar — negeren */ }
}
function _herstelKaartState() {
  let s = null
  try { s = JSON.parse(sessionStorage.getItem(_LK_STATE_KEY) || 'null') } catch { s = null }
  if (!s) return false  // geen in-sessie state → de caller past desgewenst de standaardkijk toe
  // ADR-033 — herstel de actieve set (de modus volgt eruit). Fase B: de graaf is bij mount nog niet
  // geladen (set-gestuurd) → herstel de set as-is; de daaropvolgende `herlaadGraaf` haalt de subgraaf
  // van die set op.
  if (Array.isArray(s.actieveSet) && s.actieveSet.length) actieveSet.value = new Set(s.actieveSet)
  // LI036 — de weergave wordt niet hersteld (momentkeuze; een oude `layoutModus`-sleutel uit een
  // vroegere sessie wordt genegeerd). Baanvolgorde herstellen mits een geldige permutatie van de
  // bekende banen (anders default).
  if (Array.isArray(s.laneVolgorde)) {
    const geldig = s.laneVolgorde.filter((k) => LANE_DEF[k])
    if (DEFAULT_LANE_VOLGORDE.every((k) => geldig.includes(k))) laneVolgorde.value = geldig
  }
  if (typeof s.verbergLegeLanes === 'boolean') verbergLegeLanes.value = s.verbergLegeLanes
  if (typeof s.toonRegistratiegaps === 'boolean') toonRegistratiegaps.value = s.toonRegistratiegaps
  if (Array.isArray(s.ringAan)) ringAan.value = new Set(s.ringAan.filter((r) => RINGEN.includes(r)))
  if (typeof s.groepeerPerOrg === 'boolean') groepeerPerOrg.value = s.groepeerPerOrg
  // KAART-LEZING (slice A) — herstel de lezing; legacy lk-state (vóór slice A) droeg alleen een
  // `kleurOpDomein`-boolean → map die eenmalig naar de domein-lezing.
  if (['werk', 'status', 'domein'].includes(s.lezing)) lezing.value = s.lezing
  else if (s.kleurOpDomein === true) lezing.value = 'domein'
  // egoStartId herstellen (de subgraaf-fetch laadt die node mee als hij nog bestaat).
  if (s.egoStartId) egoStartId.value = s.egoStartId
  return true  // in-sessie state hersteld → standaardkijk NIET toepassen (herladen behoudt het werk)
}
onBeforeRouteLeave(_bewaarKaartState)
// LI034 — herladen (F5) behoudt het actieve werk. `onBeforeRouteLeave` vuurt NIET bij een reload, dus
// persisteren we de ACTUELE in-sessie-staat óók op `beforeunload`. Zo herstelt de mount ná een F5 de
// werkelijke set (bv. die ene zojuist gekozen component), niet een stale route-leave-snapshot. De
// listener wordt in `onBeforeUnmount` opgeruimd (geen lek).
function _opUnload() { _bewaarKaartState() }
onMounted(() => window.addEventListener('beforeunload', _opUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', _opUnload))

onMounted(async () => {
  // Fase B — geen onvoorwaardelijke full-graph-laad meer: eerst catalogus + views, dán de set/staat
  // bepalen, dán pas de bijbehorende graaf laden (lege set → beginscherm, niets laden).
  // LI019 1b — componenttype-catalogus voor het type-filter (faalt zacht: leeg → niets te kiezen).
  try {
    const _opties = await api.componenten.opties()
    typeCatalogus.value = _opties?.componenttype || []
    // ADR-028 — rol-catalogus + ordinale BIV-niveaus voor de kaartfilters.
    rolCatalogus.value = _opties?.componentrol_opties || []
    bivNiveaus.value = _opties?.biv_niveaus || []
  } catch {
    typeCatalogus.value = []
  }
  // ADR-033 slice 2c — opgeslagen views laden (faalt zacht). Voedt de views-lijst + het startscherm.
  await laadViews()
  // LI034/ADR-041 — de opgeslagen persoonlijke standaardkijk laden (faalt zacht → geen standaard).
  await laadStandaardkijk()
  // ADR-033 — deep-link ?center=<applicatie-id> (vanuit het applicatie-detail): de component
  // wordt als enige in de actieve set gezet → Ego-view (afgeleide modus), centraal op de kaart.
  // De oude ?modus-param is vervallen (de modus volgt voortaan de actieve set) en wordt genegeerd.
  // LI033 — handoff vanuit het "Gebruikte applicaties"-blok (consume-once): open exact díé set +
  // draag de grof-only-markering mee. Heeft voorrang op deep-link én bewaarde state.
  const _handoff = neemKaartHandoff()
  const qCenter = route.query?.center ? String(route.query.center) : null
  if (_handoff && Array.isArray(_handoff.componentIds) && _handoff.componentIds.length) {
    actieveSet.value = new Set(_handoff.componentIds)
    grofOnlyIds.value = new Set(_handoff.grofOnlyIds || [])
    // LI033 — handoff vanuit "Gebruikte applicaties" (consume-once): open exact die set, neutraal.
    if (_handoff.weergave === 'lagen') weergave.value = 'lagen'
    beginschermOpen.value = false
  } else if (qCenter) {
    // Expliciete deep-link heeft voorrang op bewaarde state. ADR-040 F1 stap 2a: één centrum → praatplaat.
    actieveSet.value = new Set([qCenter])
    egoStartId.value = qCenter
    weergave.value = 'praatplaat'
    _zetPraatplaatRingen() // LI034 slice 2 — deep-link betreedt de praatplaat → kern-4-startstand (vóór _zaaiHistorie)
    detailId.value = qCenter
    // ADR-025 — "Bekijk op kaart": het beginscherm overslaan en direct de ego-view tonen.
    beginschermOpen.value = false
  } else {
    // Precedentie: in-sessie `lk-state` (herladen behoudt werk) > server-standaardkijk > kale default.
    const hersteld = _herstelKaartState()
    if (!hersteld && opgeslagenKijk.value) _pasKijkToe(opgeslagenKijk.value)
  }
  // ADR-033 slice 2d — startscherm: bij ≥1 opgeslagen view en géén expliciete ingang (deep-link of
  // herstelde actieve set) tonen we de views als instap. 0 views → direct het geheel-model.
  if (!qCenter && opgeslagenViews.value.length >= 1 && actieveSet.value.size === 0) {
    toonStartscherm.value = true
  }
  // Fase B — eerste graaf-laad volgens de zojuist bepaalde staat (lege set → beginscherm = niets
  // laden; deep-link/herstelde set → subgraaf). Daarna pas de herfetch-watch scherpstellen, zodat
  // de set-assignments hierboven geen dubbele fetch geven.
  await herlaadGraaf()
  _mountKlaar = true
  // Toestand-geschiedenis zaaien op de zojuist opgebouwde begintoestand (cursor 0). Vanaf hier
  // legt elke betekenisvolle wijziging een nieuwe entry vast (zie de _toestandSig-watch).
  _zaaiHistorie()
  await nextTick() // wacht tot de canvas-div in de DOM staat (en de flex-hoogte gezet is)
  if (containerRef.value) {
    // LI019 1d-v4 (bug 6) — maxZoom begrenst de fit-inzoom bij een kleine node-set, zodat 2 nodes
    // niet schermvullend-groot worden; minZoom houdt een grote graaf zinvol.
    cy = cytoscape({ container: containerRef.value, elements: [], style: CY_STYLE, minZoom: 0.1, maxZoom: 1.6 })
    // Enkele tap = popup (uitgesteld), dubbele tap = hercentreren — zie onNodeTap.
    // LI036 rolbanen — de LOGISCHE-id-grens: een tap op een rol-instance resolvet hier naar de
    // onderliggende partij (alles stroomafwaarts — set/praatplaat/detail — werkt op logische ids);
    // de rollen van de aangeklikte plek reizen mee voor de popup-rolcontext (consume-once).
    cy.on('tap', 'node', (evt) => {
      const d = evt.target.data?.() || {}
      _klikRollen.value = Array.isArray(d.rollen) ? d.rollen : []
      onNodeTap(d.logischId || evt.target.id())
    })
    // LI019 1d-v2 → LI036 — houd de baan-band- én rol-tag-overlay synchroon met pan/zoom/resize.
    cy.on('pan zoom resize', () => { updateBands(); updateRolTags() })
    // Tap op een koppeling (flow-edge) opent de koppeling-popup.
    cy.on('tap', 'edge', (evt) => {
      // LI036 rolbanen — zoek de logische edge op de LOGISCHE endpoints (bronLog/doelLog; bij een
      // rol-instance wijken source/target af van grafEdges).
      const src = evt.target.data('bronLog') || evt.target.data('source')
      const tgt = evt.target.data('doelLog') || evt.target.data('target')
      const ring = evt.target.data('ring')
      const edge = grafEdges.value.find((e) => e.bron_id === src && e.doel_id === tgt && e.ring === ring)
      if (!edge) return
      // B1 — markeer de aangeklikte edge zolang de popup open is.
      cy.edges().removeClass('sel-edge')
      evt.target.addClass('sel-edge')
      geselecteerdeEdgeId.value = evt.target.id()
      openEdgePopup(edge)
    })
    // Tap op leeg canvas sluit een open popup.
    cy.on('tap', (evt) => { if (evt.target === cy) sluitPopup() })
    // LI023 — edge-labels verschijnen bij hover (en blijven zichtbaar bij een geselecteerde edge).
    cy.on('mouseover', 'edge', (evt) => evt.target.style('text-opacity', 1))
    cy.on('mouseout', 'edge', (evt) => { if (!evt.target.hasClass('sel-edge')) evt.target.style('text-opacity', 0) })
    // ADR-040 F1 — de INITIËLE render loopt via dezelfde ene scheduler als de re-layout-watch, zodat
    // de eerste teken + een reactieve settle (bv. scope-balk) tot ÉÉN redraw coalesceren (geen dubbel).
    _planRedraw()
    // Her-meten + passend maken bij containerwijzigingen (modus-wissel, sidebar, venster-resize,
    // en LI036: de Vergroten/Verkleinen-maatwissel) — één gedeeld pad: `_pasCanvasMaat`.
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(_pasCanvasMaat)
      resizeObserver.observe(containerRef.value)
    }
  }
  window.addEventListener('keydown', _opEscape)
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  cy?.destroy?.()
  window.removeEventListener('keydown', _opEscape)
})

defineExpose({ openNodePopup, openEdgePopup, selecteerFlow, onNodeTap, sluitPopup, _EDGE_TAKKEN, RINGEN, toggleFullscreen, fullscreen, popupOpen, _edgeData, groepeerPerOrg, grafNodes, grafEdges, zichtbareNodes, zichtbareEdges, _laneVan, _swimlanePositions, _layout, laneVolgorde, verbergLegeLanes, laneBanden, getekendeNodes, _herschikLane, toonRegistratiegaps, modus, weergave, toonPraatplaat, toonOverzicht, toonLagen, kanPraatplaat, instanceProjectie, rolTagPx, popupRolActief, popupRolOverig, _pasCanvasMaat, CY_STYLE, popupVervuldDoor, actieveSet, grofOnlyIds, toggleSet, kiesComponent, drillNaar, _nodeData, geselecteerdNodeId, _edgeGehighlight, inspecteerNode, historie, cursor, kanTerug, kanVooruit, terugInHistorie, vooruitInHistorie, _vormVoorType, legendaOpen, toggleLegenda, scopeOrgs, organisatieNodes, organisatiesInBeeld, toggleScopeOrg, _inScope, opgeslagenViews, magViewsBeheren, toonStartscherm, openView, openOpslaan, openBewerk, bewaarView, verwijderView, beginMetHeleKaart, sluitStartscherm, viewDialogOpen, viewNaam, viewGedeeld, laadViews, heleLandschap, beginscherm, beginschermOpen, tekenVoortgang, toonHeleLandschap, herlaadGraaf, wisSet, voegComponentenToeAanSet, actieveSetNodes, componentBuren, voegBurenToe, voegContextComponentenToe, geselecteerdNodeBuren, detailNode, _relayoutTeller, legendaTypeFilter, toggleLegendaFilter, _legendaMatch, legendaPos, legendaDragging, onLegendaMousedown, onLegendaMousemove, onLegendaMouseup, popupPos, popupDragging, onPopupMousedown, onPopupMousemove, onPopupMouseup, popupKind, popupSub, popupSamenvatting, _pasDim,
  // ADR-028 — rol/BIV-filter (test-toegang).
  filterRollen, filterBivB, filterBivI, filterBivV, _filterMatch, bivNiveaus, rolCatalogus })

// ADR-040 F1 — ÉÉN render-eigenaar. Elke wijziging die een hertekening vergt, loopt via één
// gecoalesceerde scheduler (`_planRedraw`); ook de INITIËLE render (onMounted) gaat hier doorheen.
// De pending-vlag + `nextTick` coalesceren álle verzoeken binnen dezelfde tick tot ÉÉN `tekenGraaf()`.
// Zo verdwijnt de dubbele render-bij-openen (initiële teken + een tweede, door de reactieve settle
// uitgelokte hertekening): de settle valt in dezelfde tick en wordt meegenomen in de ene redraw.
//
// De watch reageert op de WERKELIJK GETEKENDE node-samenstelling (`getekendeNodes`-id-compositie: vangt
// scope/ring/zoekfilter/nieuwe subgraaf + `focusOpSet`) én op wijzigingen die de id-set niet veranderen
// maar wél een redraw vergen (edges via ring-toggle, weergave-wissel, kleur-op-domein, baan-opties).
// `weergave` staat er expliciet in: overzicht↔lagen wijzigt `modus` níét ('geheel'→'geheel') maar
// vergt wél een andere layout.
// History-herstel (terug/vooruit) tekent DIRECT (synchroon), zodat `tekenGraaf` de
// `_herstelZonderAnimatie`-vlag synchroon consumeert (de hang-fix) — bewust buiten de coalesce.
let _redrawPending = false
function _hertekenNu() {
  _redrawPending = false
  if (!_mountKlaar || !cy) return // niet vóór de eerste render / vóór cy bestaat
  _relayoutTeller.value++
  tekenGraaf()
}
function _planRedraw() {
  if (!_mountKlaar || !cy) return
  if (_redrawPending) return // coalesce: er staat al een redraw gepland voor deze tick
  _redrawPending = true
  nextTick(_hertekenNu)
}
watch(
  [
    () => getekendeNodes.value.map((n) => n.id).join('|'), // de werkelijk getekende node-set
    zichtbareEdges, modus, weergave, lezing, groepeerPerOrg, verbergLegeLanes, laneVolgorde, toonRegistratiegaps,
  ],
  () => {
    if (_herstellen) _hertekenNu() // hang-fix: synchroon (buiten de coalesce)
    else _planRedraw()
  },
  { deep: false },
)

function centreer() {
  cy?.fit?.()
}
function toggleRing(r) {
  const s = new Set(ringAan.value)
  s.has(r) ? s.delete(r) : s.add(r)
  ringAan.value = s
}
const typeLabel = (t) => humaniseer(t)
</script>

<template>
  <div
    :class="['flex w-full flex-col', fullscreen ? 'fixed inset-0 z-[400] bg-[var(--lk-color-bg)]' : '']"
    data-testid="lk-wrapper"
    :style="fullscreen ? 'height: 100vh' : 'height: calc(100vh - 9rem)'"
  >
    <!-- ADR-040 F1 stap 2a → LI036 — Topbar: EXPLICIETE weergave-schakelaar (Overzicht | Praatplaat |
         Lagen). De weergave volgt de handeling; deze knoppen tonen waar je bent en laten je wisselen.
         Praatplaat is pas actief zodra er een centrum is (geen lege praatplaat). -->
    <div class="flex items-center gap-[var(--lk-space-sm)] border-b border-[var(--lk-color-border)] bg-white p-[var(--lk-space-sm)]">
      <div class="inline-flex overflow-hidden rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)]" role="group" aria-label="Weergave" data-testid="lk-weergave-schakelaar">
        <button
          type="button" data-testid="lk-weergave-overzicht"
          :aria-pressed="weergave === 'overzicht'"
          :class="['px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] font-semibold', weergave === 'overzicht' ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-white text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]']"
          @click="toonOverzicht"
        >Overzicht</button>
        <button
          type="button" data-testid="lk-weergave-praatplaat"
          :aria-pressed="weergave === 'praatplaat'"
          :disabled="!kanPraatplaat"
          :title="kanPraatplaat ? '' : 'Kies eerst een component als middelpunt'"
          :class="['px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] font-semibold border-l border-[var(--lk-color-border)] disabled:opacity-40 disabled:cursor-not-allowed', weergave === 'praatplaat' ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-white text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]']"
          @click="toonPraatplaat()"
        >Praatplaat</button>
        <button
          type="button" data-testid="lk-weergave-lagen"
          :aria-pressed="weergave === 'lagen'"
          title="Dezelfde selectie, per laag-baan"
          :class="['px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] font-semibold border-l border-[var(--lk-color-border)]', weergave === 'lagen' ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-white text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]']"
          @click="toonLagen"
        >Lagen</button>
      </div>
      <!-- Fase B — "Begin opnieuw": enige harde reset → terug naar het lege beginscherm. -->
      <!-- LI052 — altijd zichtbaar/bruikbaar (ook op het beginscherm: daar idempotent) → gegarandeerd verse start. -->
      <button type="button" data-testid="lk-begin-opnieuw" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)]" @click="wisSet">Begin opnieuw</button>
      <span class="ml-auto text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="lk-zichtbaar-aantal">{{ zichtbaarAantal }} in beeld</span>
    </div>

    <!-- Fase B slice 2b (LI023) — "in beeld"-chips: één chip per component in de set (≥1), zichtbaar
         buiten het beginscherm (overzicht/praatplaat). Tweede set-bewerkingsplek naast de context-routes;
         × verwijdert via de bestaande toggleSet → de set-watch herlaadt de subgraaf. -->
    <div
      v-if="actieveSet.size"
      data-testid="lk-chips"
      class="flex flex-wrap items-center gap-1 border-b border-[var(--lk-color-border)] bg-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)]"
    >
      <span class="text-[length:var(--lk-text-xs)] font-semibold text-[var(--lk-color-text-muted)]">In beeld:</span>
      <span
        v-for="n in actieveSetNodes"
        :key="n.id"
        :data-testid="`lk-chip-${n.id}`"
        class="flex items-center gap-1 rounded bg-[var(--lk-color-accent)] px-[var(--lk-space-xs)] py-0.5 text-[length:var(--lk-text-xs)]"
      >
        {{ n.naam }}
        <button
          type="button"
          :data-testid="`lk-chip-verwijder-${n.id}`"
          :aria-label="`Verwijder ${n.naam} uit beeld`"
          class="leading-none text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-danger)]"
          @click="toggleSet(n.id)"
        >×</button>
      </span>
    </div>

    <div class="flex min-h-0 flex-1">
      <!-- Linkerpaneel: zoek + filters + resultaten -->
      <aside class="flex w-60 flex-shrink-0 flex-col gap-[var(--lk-space-sm)] overflow-y-auto border-r border-[var(--lk-color-border)] bg-white p-[var(--lk-space-md)]" data-testid="lk-links">
        <!-- LI034/ADR-041 — persoonlijke standaardkijk: sla de huidige kijk (filters/ringen/diepte/kleur)
             op als je standaard; komt terug bij een verse kaart-start en bij "Begin opnieuw". -->
        <div data-testid="lk-standaardkijk" class="flex flex-col gap-1 border-b border-[var(--lk-color-border)] pb-[var(--lk-space-sm)]">
          <button
            type="button"
            data-testid="lk-standaardkijk-opslaan"
            :disabled="!kijkGewijzigd || kijkBezig"
            class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] text-white disabled:cursor-not-allowed disabled:opacity-50"
            @click="slaKijkOp"
          >★ Sla op als mijn standaardkijk</button>
          <span
            data-testid="lk-standaardkijk-status"
            :class="['text-[length:var(--lk-text-xs)]', kijkGewijzigd ? 'text-[var(--lk-color-warning,#b45309)]' : 'text-[var(--lk-color-text-muted)]']"
          >{{ kijkGewijzigd ? (opgeslagenKijk ? 'Gewijzigd — nog niet je standaard' : 'Nog geen standaardkijk opgeslagen') : 'Dit is je standaardkijk' }}</span>
          <button
            v-if="opgeslagenKijk"
            type="button"
            data-testid="lk-standaardkijk-herroep"
            class="self-start text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-danger)] hover:underline"
            @click="herroepKijk"
          >Herroep standaardkijk (terug naar kale default)</button>
          <p v-if="kijkFout" role="alert" data-testid="lk-standaardkijk-fout" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-danger)]">{{ kijkFout }}</p>
        </div>
        <!-- ADR-033 2c — opgeslagen views (eigen + gedeeld; server filtert). Openen = de bewaarde
             selectie wordt de actieve set → de adaptieve weergave volgt. Beheer (✎/×) alleen voor
             de maker (is_eigenaar) mét beheer-recht. -->
        <div v-if="opgeslagenViews.length" data-testid="lk-views" class="flex flex-col gap-1 border-b border-[var(--lk-color-border)] pb-[var(--lk-space-sm)]">
          <p class="font-semibold text-[length:var(--lk-text-sm)]">Opgeslagen views</p>
          <ul class="flex flex-col gap-0.5">
            <li v-for="v in opgeslagenViews" :key="v.id" :data-testid="`lk-view-${v.id}`" class="flex items-center gap-1 text-[length:var(--lk-text-sm)]">
              <button type="button" class="grow truncate text-left hover:underline" :data-testid="`lk-view-open-${v.id}`" :title="v.naam" @click="openView(v)">{{ v.naam }}</button>
              <span v-if="!v.is_eigenaar && v.gedeeld" :data-testid="`lk-view-gedeeld-${v.id}`" class="shrink-0 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]" :title="`gedeeld door ${v.maker_naam || '—'}`">gedeeld door {{ v.maker_naam || '—' }}</span>
              <template v-if="v.is_eigenaar && magViewsBeheren">
                <button type="button" class="shrink-0 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)]" :data-testid="`lk-view-bewerk-${v.id}`" aria-label="View bewerken" title="Bewerken" @click="openBewerk(v)">✎</button>
                <button type="button" class="shrink-0 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-danger)]" :data-testid="`lk-view-verwijder-${v.id}`" aria-label="View verwijderen" title="Verwijderen" @click="verwijderView(v)">×</button>
              </template>
            </li>
          </ul>
        </div>

        <input v-model="zoekterm" type="search" data-testid="lk-zoek" placeholder="🔍 Zoek naam/domein/leverancier…" class="lk-veld" />

        <!-- LI029 — zoekresultaten direct onder de zoekbalk. Alleen in kaart-modus (beginscherm dicht)
             én bij een actieve zoekopdracht óf filter (het beginscherm heeft zijn eigen zoek). -->
        <div
          v-if="!beginschermOpen && (zoekterm.trim() || filterActief)"
          data-testid="lk-kaartzoek"
          class="flex flex-col gap-[var(--lk-space-xs)] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-accent)]/30 p-[var(--lk-space-sm)]"
        >
          <p class="font-semibold text-[length:var(--lk-text-sm)]">
            Componenten ({{ zoekResultaten.trim() ? `${gefilterdeResultaten.length} van ${gefilterdeNodes.length}` : gefilterdeNodes.length }})
          </p>
          <input
            v-model="zoekResultaten"
            type="search"
            placeholder="Zoek in resultaten…"
            data-testid="lk-zoek-resultaten"
            aria-label="Zoek in resultaten"
            class="lk-veld"
          />
          <ul class="flex max-h-64 flex-col gap-1 overflow-y-auto" data-testid="lk-resultaten">
            <!-- Klikken op de naam = toevoegen/verwijderen uit de set + detail tonen (kiesComponent);
                 de "+"-knop voegt alleen toe (✓ als het al in beeld is). -->
            <li v-for="n in gefilterdeResultaten" :key="n.id" :data-testid="`lk-res-${n.id}`" :class="['flex items-center gap-1 rounded px-1 py-0.5 text-[length:var(--lk-text-sm)]', inSet(n.id) ? 'bg-[var(--lk-color-accent)]' : '']">
              <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: lcStyle(n.lifecycle_status).bg, border: `1px solid ${lcStyle(n.lifecycle_status).border}` }"></span>
              <button type="button" :aria-pressed="inSet(n.id)" class="grow truncate text-left hover:underline" :data-testid="`lk-res-naam-${n.id}`" @click="kiesComponent(n.id)">{{ n.naam }}</button>
              <span v-if="n.blokkades_open > 0" :data-testid="`lk-res-blok-${n.id}`" title="Open blokkade(s)">⚠</span>
              <span v-if="n.hosting_model">{{ hostingIcoon(n.hosting_model) }}</span>
              <button
                v-if="!inSet(n.id)"
                type="button"
                :data-testid="`lk-res-voegtoe-${n.id}`"
                class="shrink-0 rounded px-1.5 font-semibold text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]"
                :title="`${n.naam} toevoegen aan beeld`"
                :aria-label="`${n.naam} toevoegen aan beeld`"
                @click="toggleSet(n.id)"
              >+</button>
              <span v-else :data-testid="`lk-res-gekozen-${n.id}`" class="text-[var(--lk-color-primary)]" title="Al in beeld">✓</span>
            </li>
            <li v-if="!gefilterdeResultaten.length" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">Geen resultaten.</li>
          </ul>
          <button type="button" data-testid="lk-voeg-alle" class="mt-1 rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] text-white" @click="voegAlleGefilterdeToe">+ Voeg alle gefilterde toe</button>
        </div>

        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="font-semibold">Type</span>
          <ZoekMultiSelect
            v-model="filterTypes"
            :zoek-functie="zoekComponenttypes"
            :weergave="(o) => o.label"
            id-veld="optie_sleutel"
            :chip-label="(v) => typeLabelMap[v] || v"
            placeholder="Zoek type…"
            testid="lk-filter-type"
          />
        </label>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="font-semibold">Leverancier</span>
          <ZoekMultiSelect
            v-model="filterLeveranciers"
            :zoek-functie="zoekLeveranciers"
            :weergave="(o) => o.naam"
            id-veld="id"
            :vaste-optie="{ id: ZONDER, naam: 'Zonder leverancier' }"
            placeholder="Zoek leverancier…"
            testid="lk-filter-leverancier"
          />
        </label>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="font-semibold">Hosting</span>
          <ZoekMultiSelect
            v-model="filterHosting"
            :zoek-functie="zoekHosting"
            :weergave="(o) => o.label"
            id-veld="sleutel"
            :chip-label="(v) => typeLabel(v)"
            :vaste-optie="{ sleutel: ZONDER, label: 'Zonder hosting' }"
            placeholder="Zoek hosting…"
            testid="lk-filter-hosting"
          />
        </label>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="font-semibold">{{ veldLabel('lifecycle_status') }}</span>
          <ZoekMultiSelect
            v-model="filterLifecycle"
            :zoek-functie="zoekLifecycle"
            :weergave="(o) => o.label"
            id-veld="sleutel"
            :chip-label="(v) => typeLabel(v)"
            :vaste-optie="{ sleutel: ZONDER, label: 'Zonder beoordelingsstatus' }"
            placeholder="Zoek beoordelingsstatus…"
            testid="lk-filter-lifecycle"
          />
        </label>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="font-semibold">Rol</span>
          <ZoekMultiSelect
            v-model="filterRollen"
            :zoek-functie="zoekRollen"
            :weergave="(o) => o.label"
            id-veld="optie_sleutel"
            :chip-label="(v) => rolLabelMap[v] || v"
            placeholder="Zoek rol…"
            testid="lk-filter-rol"
          />
        </label>
        <label
          v-for="a in BIV_ASPECTEN"
          :key="a.veld"
          class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]"
        >
          <span class="font-semibold">{{ a.label }} ≥</span>
          <select
            v-model="a.ref.value"
            :data-testid="`lk-filter-${a.veld}`"
            :aria-label="`Filter op minimaal ${a.label}`"
            class="lk-veld"
          >
            <option value="">— Alle —</option>
            <option v-for="n in bivNiveaus" :key="n.optie_sleutel" :value="n.optie_sleutel">{{ n.label }}</option>
          </select>
        </label>

        <label v-if="modus === 'geheel'" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input type="checkbox" :checked="!opbouwModus" data-testid="lk-afpel-toggle" @change="opbouwModus = !opbouwModus" />Afpel-modus (begint vol)
        </label>

        <!-- Diepte-toggle (ego + geheel): 1 stap = directe buren, 2 stappen = ook indirecte. -->
        <div v-if="modus === 'ego' || modus === 'geheel'" class="flex flex-col gap-1" data-testid="lk-diepte">
          <p class="font-semibold text-[length:var(--lk-text-sm)]">Diepte</p>
          <div class="flex gap-1">
            <button type="button" data-testid="lk-diepte-1" :aria-pressed="diepte === 1" :class="['rounded-[var(--lk-radius-btn)] px-[var(--lk-space-sm)] py-0.5 text-[length:var(--lk-text-xs)]', diepte === 1 ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-[var(--lk-color-accent)]']" @click="zetDiepte(1)">1 stap (direct)</button>
            <button type="button" data-testid="lk-diepte-2" :aria-pressed="diepte === 2" :class="['rounded-[var(--lk-radius-btn)] px-[var(--lk-space-sm)] py-0.5 text-[length:var(--lk-text-xs)]', diepte === 2 ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-[var(--lk-color-accent)]']" @click="zetDiepte(2)">2 stappen</button>
          </div>
        </div>

        <!-- Fix 4 — ring-checkboxes in alle modi (globale laagfilters). Geen wrapper-<template>
             zonder directive: Vue rendert die niet → checkboxes verdwenen (LI018-regressie). -->
        <p class="font-semibold text-[length:var(--lk-text-sm)]">Ringen</p>
        <template v-for="r in RINGEN" :key="r">
          <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
            <input type="checkbox" :checked="ringAan.has(r)" :data-testid="`lk-ring-${r}`" @change="toggleRing(r)" />{{ RING_LABELS[r] || typeLabel(r) }}
          </label>
          <!-- ADR-031 — sub-granulariteit: alleen zichtbaar als de Gebruikers-ring aan staat. -->
          <label v-if="r === 'gebruikers' && ringAan.has('gebruikers')" class="ml-5 flex items-center gap-2 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
            <input type="checkbox" :checked="groepeerPerOrg" data-testid="lk-groepeer-org" @change="groepeerPerOrg = !groepeerPerOrg" />Groepeer per organisatie
          </label>
        </template>

        <!-- LI019 1d-v7 — registratiegaps: standaard tonen Overzicht/Praatplaat de edge-rakende
             node-set. Aan = óók losse nodes zonder relatie (registratiegaps); de Lagen-weergave
             toont losse nodes sowieso (elke node hoort in een baan). -->
        <label class="mt-[var(--lk-space-sm)] flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input type="checkbox" v-model="toonRegistratiegaps" data-testid="lk-registratiegaps" />Toon registratiegaps
        </label>
        <!-- LI019 1d-v3 → LI036 — Lagen-optie: lege banen verbergen. De baanvolgorde wijzig je door de
             baan-kop op het canvas te verslepen (geen zijbalk-lijst meer). -->
        <label v-if="weergave === 'lagen'" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input type="checkbox" v-model="verbergLegeLanes" data-testid="lk-verberg-lege" />Verberg lege banen
        </label>

      </aside>

      <!-- Midden: "Organisaties in beeld"-balk bovenin + het kaart-canvas eronder. -->
      <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <!-- LI053 → ADR-040 F1 stap 2b — de balk bestuurt UITSLUITEND de organisatie-overlay: een vinkje
             toont/verbergt de organisatie-node + haar gebruikersgroepen. Componenten worden nooit geraakt.
             Default alle aan (eenmalige seed). Op OVERZICHT én LAGEN (LI036 — de scope werkt daar door,
             dus de control hoort zichtbaar te zijn: nooit stiekem verbergen, P8); op de praatplaat bepaalt
             het centrum + de kring wat je ziet (scope daar inert) → balk verborgen. -->
        <div
          v-if="organisatieNodes.length && weergave !== 'praatplaat'"
          data-testid="lk-scopebalk" role="group" aria-label="Organisaties in beeld"
          class="flex flex-wrap items-center gap-x-[var(--lk-space-md)] gap-y-1 border-b border-[var(--lk-color-border)] bg-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)]"
        >
          <span class="text-[length:var(--lk-text-sm)] font-semibold">Organisaties in beeld:</span>
          <!-- LI036 — de lijst = organisaties die bij DEZE selectie in beeld (zouden) zijn
               (`organisatiesInBeeld`, model i) — niet de volledige geladen subgraaf. Een uitgezette
               organisatie blijft onaangevinkt staan zolang de selectie haar relevant maakt. -->
          <label v-for="o in organisatiesInBeeld" :key="o.id" class="flex items-center gap-1 text-[length:var(--lk-text-sm)]">
            <input type="checkbox" :checked="scopeOrgs.has(o.id)" :data-testid="`lk-scope-org-${o.id}`" @change="toggleScopeOrg(o.id)" />{{ o.naam }}
          </label>
          <span v-if="!organisatiesInBeeld.length" data-testid="lk-scope-leeg" class="text-[length:var(--lk-text-sm)] italic text-[var(--lk-color-text-muted)]">geen organisatie in beeld</span>
        </div>

      <!-- Canvas — min-h-0 is kritiek: zonder negeert een flex-child de height:100% van de parent,
           waardoor Cytoscape op hoogte 0 initialiseert en de graaf leeg/onzichtbaar blijft. -->
      <div class="relative min-h-0 min-w-0 flex-1 bg-[var(--lk-color-surface)]">
        <!-- LI019 1d-v4 → LI036 — laag-banen in TWEE HTML-lagen ROND het canvas (geen compound-nodes,
             zodat Cytoscape uitsluitend gewone nodes + edges bevat — edges en node-clicks werken
             normaal). (1) band-ACHTERGRONDEN onder het canvas (z-0, niet-interactief, translucent). -->
        <div v-if="weergave === 'lagen'" class="pointer-events-none absolute inset-0 z-0 overflow-hidden" data-testid="lk-lanes" aria-hidden="true">
          <div
            v-for="b in laneBanden"
            :key="b.key"
            :data-testid="`lk-lane-${b.key}`"
            class="absolute left-0 right-0 border-b border-[var(--lk-color-border)]"
            :style="{ top: (bandPx[b.index]?.top ?? 0) + 'px', height: (bandPx[b.index]?.height ?? 0) + 'px', background: b.bg, opacity: 0.5 }"
          ></div>
        </div>
        <!-- Inline min-height als harde vangrail: zelfs als de flex-hoogteketen faalt, krijgt
             Cytoscape een meetbare hoogte op het init-moment (anders blijft de graaf leeg). -->
        <div ref="containerRef" data-testid="lk-canvas" class="relative z-[1] h-full w-full" style="min-height: 500px"></div>
        <!-- Toestand-geschiedenis: heen-en-weer door bezochte kaarttoestanden (selectie/centrering,
             weergave, ringen, filters). "← Terug naar Landschapskaart" (de kaart verlaten) is een
             andere actie en blijft elders. -->
        <div class="absolute left-3 top-3 z-10 flex gap-[var(--lk-space-xs)]">
          <button
            type="button" data-testid="lk-hist-terug" aria-label="Vorige kaarttoestand"
            :disabled="!kanTerug"
            class="h-10 rounded-[var(--lk-radius-btn)] bg-white/90 px-3 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)] hover:bg-[var(--lk-color-accent)] disabled:opacity-40 disabled:cursor-not-allowed"
            @click="terugInHistorie"
          >← Terug</button>
          <button
            type="button" data-testid="lk-hist-vooruit" aria-label="Volgende kaarttoestand"
            :disabled="!kanVooruit"
            class="h-10 rounded-[var(--lk-radius-btn)] bg-white/90 px-3 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)] hover:bg-[var(--lk-color-accent)] disabled:opacity-40 disabled:cursor-not-allowed"
            @click="vooruitInHistorie"
          >Vooruit →</button>
        </div>

        <!-- Uitklapbare legenda — rechtsonder op het canvas. Standaard ingeklapt tot een knop;
             uitgeklapt: "Vorm = type" (negen vorm-glyphs) + "Kleur = status" (lifecycle + ⚠). -->
        <div class="absolute bottom-3 right-3 z-10" data-testid="lk-legenda">
          <button
            v-if="!legendaOpen"
            type="button" data-testid="lk-legenda-toggle" aria-expanded="false"
            class="h-10 rounded-[var(--lk-radius-btn)] bg-white/90 px-3 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)] hover:bg-[var(--lk-color-accent)]"
            @click="toggleLegenda"
          >Legenda</button>
          <div
            v-else
            data-testid="lk-legenda-paneel"
            :style="legendaPos.x !== null ? { position: 'fixed', left: legendaPos.x + 'px', top: legendaPos.y + 'px', bottom: 'auto', right: 'auto', zIndex: 30 } : {}"
            :class="['max-h-[70%] w-60 overflow-auto rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-white/95 p-[var(--lk-space-sm)] shadow-[var(--lk-shadow-lg)]', legendaDragging ? 'cursor-grabbing' : 'cursor-grab']"
            @mousedown="onLegendaMousedown"
          >
            <div class="mb-1 flex items-center justify-between">
              <span class="font-semibold text-[length:var(--lk-text-sm)]">Legenda</span>
              <button type="button" data-testid="lk-legenda-sluit" aria-label="Legenda inklappen" class="px-1 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-text)]" @click="toggleLegenda">×</button>
            </div>
            <!-- Vorm = type -->
            <div data-testid="lk-legenda-vorm" class="flex flex-col gap-1">
              <p class="text-[length:var(--lk-text-xs)] font-semibold text-[var(--lk-color-text-muted)]">Vorm = type</p>
              <button
                v-for="v in VORM_LEGENDA"
                :key="v.label"
                type="button"
                :data-testid="`lk-legenda-type-${v.label}`"
                :aria-pressed="legendaTypeFilter === v.label"
                :title="legendaTypeFilter === v.label ? 'Filter opheffen' : `Toon alleen: ${v.label}`"
                :class="['flex items-center gap-2 text-left text-[length:var(--lk-text-sm)] cursor-pointer rounded px-1 hover:bg-[var(--lk-color-accent)]', legendaTypeFilter === v.label ? 'bg-[var(--lk-color-accent)] font-semibold' : '']"
                @click="toggleLegendaFilter(v.label)"
              >
                <span class="inline-block h-3.5 w-3.5 shrink-0 bg-[var(--lk-color-text-muted)]" :style="v.stijl" aria-hidden="true"></span>{{ v.label }}
              </button>
            </div>
            <!-- MEEBEWEGENDE LEZING-LEGENDA (slice A): toont ALLEEN de codering van de ACTIEVE lezing —
                 dicht het `kleurOpDomein`-gat (legenda en kaart vertellen altijd hetzelfde verhaal). -->
            <!-- status → Kleur = status (lifecycle-tinten) -->
            <div v-if="lezing === 'status'" data-testid="lk-legenda-status" class="mt-[var(--lk-space-sm)] flex flex-col gap-1 border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]">
              <p class="text-[length:var(--lk-text-xs)] font-semibold text-[var(--lk-color-text-muted)]">Kleur = status</p>
              <span v-for="lc in LIFECYCLE_OPTIES.concat(['null'])" :key="lc" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
                <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: lcStyle(lc).bg, border: `1px solid ${lcStyle(lc).border}` }"></span>{{ lc === 'null' ? 'geen profiel' : typeLabel(lc) }}
              </span>
            </div>
            <!-- domein → Kleur = domein (rand-kleur; domeinen in beeld) -->
            <div v-else-if="lezing === 'domein'" data-testid="lk-legenda-domein" class="mt-[var(--lk-space-sm)] flex flex-col gap-1 border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]">
              <p class="text-[length:var(--lk-text-xs)] font-semibold text-[var(--lk-color-text-muted)]">Kleur = domein</p>
              <span v-for="d in domeinOpties" :key="d" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
                <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: '#e5e7eb', border: `2px solid ${domeinKleur[d]}` }" aria-hidden="true"></span>{{ typeLabel(d) }}
              </span>
              <span v-if="!domeinOpties.length" class="text-[length:var(--lk-text-sm)] italic text-[var(--lk-color-text-muted)]">Geen domein in beeld</span>
            </div>
            <!-- werk → Kleur = stand (B2, LI043): de vier ernst-regels UIT de gedeelde bron (STAND_LEGENDA);
                 swatch via var(token) — DOM resolvet dezelfde token die de node op canvas resolvet, dus
                 legenda en kaart lopen niet uiteen. Daaronder de twee resterende rand-cues (geen plek-stand). -->
            <div v-else data-testid="lk-legenda-werk" class="mt-[var(--lk-space-sm)] flex flex-col gap-1 border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]">
              <p class="text-[length:var(--lk-text-xs)] font-semibold text-[var(--lk-color-text-muted)]">Kleur = stand</p>
              <span v-for="rij in STAND_LEGENDA" :key="rij.ernst" :data-testid="`lk-legenda-stand-${rij.ernst}`" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
                <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: `var(${rij.token})` }" aria-hidden="true"></span>{{ rij.tekst }}
              </span>
              <span class="mt-1 flex items-center gap-2 text-[length:var(--lk-text-sm)]">
                <span class="inline-block h-3.5 w-3.5 shrink-0 rounded-sm border-[2px] border-dashed border-[var(--lk-color-text-muted)]" aria-hidden="true"></span>Externe dataprovider
              </span>
              <span class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
                <span class="inline-block h-3.5 w-3.5 shrink-0 rounded-sm border-[2px] border-dotted border-[var(--lk-color-text-muted)]" aria-hidden="true"></span>Nog niet verfijnd
              </span>
            </div>
            <!-- Blokkade-cue: label-signaal, buiten de lezingen → ALTIJD zichtbaar. -->
            <div data-testid="lk-legenda-blokkade" class="mt-[var(--lk-space-sm)] flex flex-col gap-1 border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]">
              <span class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">⚠ Open blokkade(s)</span>
            </div>
          </div>
        </div>

        <!-- LI036 rolbanen — rol-tags (kleur + kort woord) ónder elke rol-instance (z-[4], boven het
             canvas, onder de baan-koppen). pointer-events-none: kliks gaan naar de knoop eronder. -->
        <div v-if="weergave === 'lagen' && rolTagPx.length" class="pointer-events-none absolute inset-0 z-[4] overflow-hidden" data-testid="lk-roltags" aria-hidden="true">
          <!-- Tag deelt de dim-staat van zijn knoop: zelfde opacity als `node.lk-dim` (één DIM_NODE_OPACITY-bron). -->
          <div v-for="t in rolTagPx" :key="t.id" class="absolute flex -translate-x-1/2 gap-0.5" :style="{ left: t.x + 'px', top: (t.y + 2) + 'px', opacity: t.dim ? DIM_NODE_OPACITY : 1 }">
            <span
              v-for="r in t.rollen" :key="r" :data-testid="`lk-roltag-${t.id}-${r}`"
              class="rounded-full px-1.5 text-[10px] font-semibold leading-4 shadow-[var(--lk-shadow-sm)]"
              :style="{ background: ROL_TAG[r].bg, color: ROL_TAG[r].tekst }"
            >{{ ROL_TAG[r].label }}</span>
          </div>
        </div>

        <!-- (2) baan-KOPPEN BOVEN het canvas (z-[5]). De container is pointer-events-none → node-
             clicks gaan ongehinderd naar het canvas; alleen de header-span vangt pointer-events af
             (versleepbaar). De lege-baan-tekst zit ook hier zodat ze leesbaar boven het canvas staat. -->
        <div v-if="weergave === 'lagen'" class="pointer-events-none absolute inset-0 z-[5] overflow-hidden" data-testid="lk-lane-headers">
          <div
            v-for="b in laneBanden"
            :key="b.key"
            class="absolute left-0 right-0"
            :class="sleepLane === b.key ? 'ring-2 ring-[var(--lk-color-primary)] ring-inset' : ''"
            :style="{ top: (bandPx[b.index]?.top ?? 0) + 'px', height: (bandPx[b.index]?.height ?? 0) + 'px' }"
          >
            <span
              :data-testid="`lk-lane-header-${b.key}`"
              class="pointer-events-auto absolute left-2 top-1 flex cursor-grab touch-none select-none items-center gap-1 rounded bg-white/80 px-1 text-[length:var(--lk-text-sm)] font-semibold text-[var(--lk-color-text-muted)] shadow-[var(--lk-shadow-sm)] active:cursor-grabbing"
              title="Versleep om de lanevolgorde te wijzigen"
              @pointerdown="onLaneSleepStart($event, b.key)"
              @pointerup="onLaneSleepEinde"
            ><span aria-hidden="true" class="opacity-60">⠿</span>{{ b.label }}</span>
            <span v-if="b.leeg" :data-testid="`lk-lane-leeg-${b.key}`" class="absolute inset-0 flex items-center justify-center text-[length:var(--lk-text-xs)] italic text-[var(--lk-color-text-muted)]">Geen objecten geregistreerd</span>
          </div>
        </div>

        <!-- Tools (rechtsboven) -->
        <div class="absolute right-3 top-3 z-10 flex gap-1">
          <!-- LI036 — de vroegere geparkeerde layout-wisselaar (Radiaal↔Swimlanes, v-if="false") is
               vervangen door de derde optie "Lagen" op de weergave-schakelaar in de topbar. -->
          <button type="button" data-testid="lk-centreer" class="rounded-[var(--lk-radius-btn)] bg-white/90 px-2 py-1 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)]" @click="centreer">⊡ Centreer</button>
          <!-- KAART-LEZING (slice A): werk / status / domein — één actief; claimt zijn kleur-kanaal, de rest neutraal. -->
          <div class="flex items-center gap-1 rounded-[var(--lk-radius-btn)] bg-white/90 px-1 py-0.5 shadow-[var(--lk-shadow-sm)]" role="group" aria-label="Kaart-lezing" data-testid="lk-lezing">
            <span class="pl-1 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">Toon:</span>
            <button
              v-for="opt in LEZING_OPTIES"
              :key="opt.key"
              type="button"
              :data-testid="`lk-lezing-${opt.key}`"
              :aria-pressed="lezing === opt.key"
              :class="['rounded-[var(--lk-radius-btn)] px-2 py-0.5 text-[length:var(--lk-text-sm)]', lezing === opt.key ? 'bg-[var(--lk-color-primary)] text-white font-semibold' : 'text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]']"
              @click="lezing = opt.key"
            >{{ opt.label }}</button>
          </div>
          <!-- Fullscreen-overlay (in-app): één toggle — vergroten ingebed, verkleinen in de overlay. -->
          <button type="button" :data-testid="fullscreen ? 'lk-fullscreen-sluit' : 'lk-fullscreen-open'" :aria-pressed="fullscreen" class="rounded-[var(--lk-radius-btn)] bg-white/90 px-2 py-1 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)]" @click="toggleFullscreen">{{ fullscreen ? '✕ Verkleinen' : '⛶ Vergroten' }}</button>
        </div>

        <!-- LI034 — dé versleepbare klik-detail-popup (koppeling of knoop): het aangeklikte object +
             z'n directe kring blijven scherp (dim-op-klik), de popup vat in gewone taal samen "wat
             raakt dit". Sleep 'm van de opgelichte lijnen af (mousedown op de popup; knoppen/links
             blijven werken). Sluiten = deselecteren (knop, Escape, of een tap op leeg canvas). -->
        <div
          v-if="popupOpen"
          data-testid="lk-popup"
          role="dialog"
          aria-label="Detail"
          :style="popupPos.x !== null ? { position: 'fixed', left: popupPos.x + 'px', top: popupPos.y + 'px' } : {}"
          :class="[popupPos.x !== null ? 'z-30' : 'absolute left-3 top-3 z-20', 'max-w-[90%] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-white p-[var(--lk-space-md)] shadow-[var(--lk-shadow-lg)]', popupKind === 'edge' ? 'w-[34rem]' : 'w-72', popupDragging ? 'cursor-grabbing' : 'cursor-grab']"
          @mousedown="onPopupMousedown"
        >
          <div class="flex items-start justify-between gap-2">
            <div>
              <p v-if="popupBadge" data-testid="lk-popup-badge" class="text-[length:var(--lk-text-xs)] font-semibold uppercase text-[var(--lk-color-primary-700)]">{{ popupBadge }}</p>
              <p class="font-semibold" data-testid="lk-popup-titel">{{ popupTitel }}</p>
              <p v-if="popupSub" data-testid="lk-popup-sub" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">{{ popupSub }}</p>
            </div>
            <button type="button" data-testid="lk-popup-sluit" aria-label="Sluiten" class="shrink-0 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-text)]" @click="sluitPopup">✕</button>
          </div>
          <!-- LI036 rolbanen — rolcontext (partij, Lagen): de rol van de aangeklikte plek bovenaan
               (zelfde kleur als de node-tag), de andere rol(len) van deze partij eronder. -->
          <div v-if="popupRolActief.length || popupRolOverig.length" data-testid="lk-popup-rollen" class="mt-2 flex flex-col gap-1 text-[length:var(--lk-text-sm)]">
            <div v-if="popupRolActief.length" class="flex flex-wrap items-center gap-1">
              <span class="text-[var(--lk-color-text-muted)]">Rol hier:</span>
              <span
                v-for="r in popupRolActief" :key="r" :data-testid="`lk-popup-rol-${r}`"
                class="rounded-full px-2 text-[length:var(--lk-text-xs)] font-semibold leading-5"
                :style="{ background: ROL_TAG[r].bg, color: ROL_TAG[r].tekst }"
              >{{ ROL_TAG[r].label }}</span>
            </div>
            <div v-if="popupRolOverig.length" class="flex flex-wrap items-center gap-1">
              <span class="text-[var(--lk-color-text-muted)]">{{ popupRolActief.length ? 'Ook:' : 'Rollen:' }}</span>
              <span
                v-for="r in popupRolOverig" :key="r" :data-testid="`lk-popup-rol-${r}`"
                class="rounded-full px-2 text-[length:var(--lk-text-xs)] font-semibold leading-5"
                :style="{ background: ROL_TAG[r].bg, color: ROL_TAG[r].tekst }"
              >{{ ROL_TAG[r].label }}</span>
            </div>
          </div>
          <!-- LI034 — "wat raakt dit object": één regel per kring; registratiegaten leesbaar benoemd. -->
          <div v-if="popupSamenvatting.length" data-testid="lk-popup-samenvatting" class="mt-2 flex flex-col gap-0.5 text-[length:var(--lk-text-sm)]">
            <p v-for="s in popupSamenvatting" :key="s.key" :data-testid="`lk-popup-sam-${s.key}`" :class="s.gat ? 'italic text-[var(--lk-color-text-muted)]' : ''">
              <span class="text-[var(--lk-color-text-muted)]">{{ s.label }}:</span> {{ s.tekst }}
            </p>
          </div>
          <p v-if="popupLaden" data-testid="lk-popup-laden" class="mt-2 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Laden…</p>
          <dl v-if="popupVelden.length" data-testid="lk-popup-velden" class="mt-2 grid grid-cols-[auto_1fr] gap-x-[var(--lk-space-sm)] gap-y-0.5 text-[length:var(--lk-text-sm)]">
            <template v-for="v in popupVelden" :key="v.label">
              <dt class="text-[var(--lk-color-text-muted)]">{{ v.label }}</dt>
              <dd class="break-words">{{ v.waarde }}</dd>
            </template>
          </dl>
          <!-- LI037 fase 2 (besluit 6/A3) — rustige gat-benoeming: dit (deel)proces heeft in zijn
               hele subboom geen ondersteunend systeem (spiegel van de popupSamenvatting-gat-regels). -->
          <p
            v-if="popupProcesGap"
            data-testid="lk-popup-geen-systeem"
            class="mt-2 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
          >Geen ondersteunend systeem geregistreerd.</p>
          <!-- LI036 stap 3 (besluit A) — "Vervuld door": scanbare componentnamen; de herkomst
               (deelproces · functies) klapt per component uit (native details, standaard dicht). -->
          <div v-if="popupVervuldDoor.length" data-testid="lk-popup-vervuld" class="mt-2 flex flex-col gap-0.5 text-[length:var(--lk-text-sm)]">
            <p class="font-semibold">Vervuld door: {{ popupVervuldDoor.length }} component{{ popupVervuldDoor.length === 1 ? '' : 'en' }}</p>
            <template v-for="c in popupVervuldDoor" :key="c.id">
              <details v-if="c.herkomst.length" :data-testid="`lk-popup-vervuld-${c.id}`" class="ml-1">
                <summary class="cursor-pointer">{{ c.naam }}</summary>
                <div class="ml-4 flex flex-col gap-0.5 text-[var(--lk-color-text-muted)]">
                  <p v-for="h in c.herkomst" :key="h.label" :data-testid="`lk-popup-herkomst-${c.id}`">{{ h.label }} · {{ h.waarde }}</p>
                </div>
              </details>
              <p v-else :data-testid="`lk-popup-vervuld-${c.id}`" class="ml-1">{{ c.naam }}</p>
            </template>
          </div>
          <!-- Koppeling-popup (flow-edge) — master-detail: links de flow-lijst (naam + richting-
               icoon), rechts het detail van de geselecteerde flow. Ook bij n=1 (ADR-023a Fase 4). -->
          <div v-if="popupKind === 'edge' && popupFlows.length" data-testid="lk-popup-md" class="mt-2 flex gap-[var(--lk-space-md)]">
            <ul data-testid="lk-popup-lijst" class="w-2/5 shrink-0 flex flex-col gap-0.5 border-r border-[var(--lk-color-border)] pr-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
              <li v-for="f in popupFlows" :key="f.id">
                <button
                  type="button"
                  :data-testid="`lk-popup-flow-${f.id}`"
                  :aria-selected="popupGeselecteerd && f.id === popupGeselecteerd.id"
                  :class="['flex w-full items-center gap-1 rounded px-1 py-0.5 text-left', popupGeselecteerd && f.id === popupGeselecteerd.id ? 'bg-[var(--lk-color-accent)] font-semibold' : 'hover:bg-[var(--lk-color-accent)]']"
                  @click="selecteerFlow(f.id)"
                >
                  <span :class="['shrink-0', f.positie === 'uit' ? 'text-[var(--lk-color-success,#16a34a)]' : 'text-[var(--lk-color-danger)]']" :title="f.positie === 'uit' ? 'Uitgaand' : 'Inkomend'">{{ f.positie === 'uit' ? '→' : '←' }}</span>
                  <span class="grow truncate">{{ f.naam }}</span>
                </button>
              </li>
            </ul>
            <dl v-if="popupGeselecteerd" data-testid="lk-popup-detail" class="grid w-3/5 grid-cols-[auto_1fr] content-start gap-x-[var(--lk-space-sm)] gap-y-0.5 text-[length:var(--lk-text-sm)]">
              <dt class="col-span-2 font-semibold text-[length:var(--lk-text-base)]" data-testid="lk-popup-detail-naam">{{ popupGeselecteerd.naam }}</dt>
              <dt class="text-[var(--lk-color-text-muted)]">Tegenpartij</dt><dd class="break-words">{{ popupGeselecteerd.tegenNaam || '—' }}</dd>
              <dt class="text-[var(--lk-color-text-muted)]">Datastroom</dt><dd>{{ popupGeselecteerd.richting ? typeLabel(popupGeselecteerd.richting) : '—' }}</dd>
              <dt class="text-[var(--lk-color-text-muted)]">Protocol</dt><dd>{{ popupGeselecteerd.protocol ? typeLabel(popupGeselecteerd.protocol) : '—' }}</dd>
              <dt class="text-[var(--lk-color-text-muted)]">Impact bij verbreking</dt><dd>{{ popupGeselecteerd.impact ? typeLabel(popupGeselecteerd.impact) : '—' }}</dd>
              <template v-if="popupGeselecteerd.omschrijving"><dt class="text-[var(--lk-color-text-muted)]">Omschrijving</dt><dd class="break-words">{{ popupGeselecteerd.omschrijving }}</dd></template>
            </dl>
          </div>
          <p v-else-if="popupKind === 'edge' && popupEdgeRing === 'applicaties' && !popupLaden && !popupMelding" data-testid="lk-popup-md-leeg" class="mt-2 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Geen koppelingen gevonden.</p>
          <p v-if="popupMelding" data-testid="lk-popup-melding" class="mt-2 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">{{ popupMelding }}</p>
          <div v-if="popupActies.length" class="mt-2 flex flex-col items-start gap-1">
            <button v-for="(a, i) in popupActies" :key="i" type="button" :data-testid="i === 0 ? 'lk-popup-actie' : `lk-popup-actie-${i}`" class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] text-white" @click="a.fn">{{ a.label }}</button>
          </div>
        </div>

        <!-- Fase B — voortgangsteller "X van N" bij het laden van het hele landschap (echt
             meebewegend getal naar een bekend totaal, geen tijd-spinner). -->
        <!-- Fase B slice 2b-v2 (LI023) — het 4-ingangen-beginscherm staat als eigen overlay vóór de
             canvas-meldingen: het blijft open (beginschermOpen) terwijl de gebruiker een set opbouwt
             en sluit pas via "Toon op de kaart" (@sluit), niet automatisch bij de eerste toevoeging.
             De component-root draagt data-testid="lk-beginscherm". -->
        <KaartBeginscherm
          v-if="beginschermOpen"
          :key="beginschermSleutel"
          class="absolute inset-0 z-20 bg-[var(--lk-color-bg)]"
          :opgeslagen-views="opgeslagenViews"
          :component-opties="typeCatalogus"
          :eigenaar-opties="[]"
          :set-grootte="actieveSetNodes.length"
          @voeg-componenten-toe="voegComponentenToeAanSet"
          @open-view="openView"
          @toon-hele-landschap="toonHeleLandschap"
          @sluit="beginschermOpen = false"
        />
        <p v-else-if="tekenVoortgang" data-testid="lk-voortgang" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[var(--lk-color-text-muted)]">{{ tekenVoortgang.gedaan }} van {{ tekenVoortgang.totaal }} componenten geladen…</p>
        <p v-else-if="laden" data-testid="lk-laden" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[var(--lk-color-text-muted)]">Landschap laden…</p>
        <p v-else-if="fout" role="alert" data-testid="lk-fout" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[var(--lk-color-danger)]">{{ fout }}</p>
        <p v-else-if="!heeftData" data-testid="lk-leeg" class="absolute left-1/2 top-1/2 max-w-md -translate-x-1/2 -translate-y-1/2 text-center text-[var(--lk-color-text-muted)]">Geen componenten in deze selectie.</p>
        <!-- LI034 bug A — rustige cue bij een gekozen component zónder relaties in beeld (geen leeg canvas). -->
        <p
          v-if="relatieLozeSetLeden.length"
          data-testid="lk-geen-relaties"
          class="absolute bottom-3 left-1/2 z-10 max-w-[90%] -translate-x-1/2 rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-white/85 px-[var(--lk-space-md)] py-1 text-center text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)] shadow-[var(--lk-shadow-sm)]"
        >{{ relatieLozeSetLeden.length === 1
          ? `“${relatieLozeSetLeden[0].naam}” heeft nog geen relaties in beeld.`
          : `${relatieLozeSetLeden.length} componenten hebben nog geen relaties in beeld.` }}</p>
      </div>
      </div>

      <!-- Rechterpaneel: actieve set + detail + legenda -->
      <aside class="flex w-56 flex-shrink-0 flex-col gap-[var(--lk-space-md)] overflow-y-auto border-l border-[var(--lk-color-border)] bg-white p-[var(--lk-space-md)]" data-testid="lk-rechts">
        <div>
          <div class="mb-1 flex items-center gap-2">
            <p class="font-semibold text-[length:var(--lk-text-sm)]">Actieve set ({{ actieveSetNodes.length }})</p>
            <button v-if="actieveSet.size > 0" type="button" data-testid="lk-set-wis" class="ml-auto text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-danger)] hover:underline" @click="wisSet">Wis alles</button>
          </div>
          <label v-if="actieveSet.size > 0" class="mb-1 flex items-center gap-2 text-[length:var(--lk-text-sm)]">
            <input type="checkbox" v-model="focusOpSet" data-testid="lk-focus-set" />Focus op actieve set
          </label>
          <ul class="flex max-h-40 flex-col gap-1 overflow-y-auto" data-testid="lk-set">
            <li v-for="n in actieveSetNodes" :key="n.id" :data-testid="`lk-set-${n.id}`" class="flex items-center gap-1 text-[length:var(--lk-text-sm)]">
              <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: lcStyle(n.lifecycle_status).bg }"></span>
              <button type="button" class="grow truncate text-left hover:underline" @click="selecteerNode(n.id)">{{ n.naam }}</button>
              <span v-if="n.blokkades_open > 0">⚠</span>
              <button type="button" class="text-[var(--lk-color-danger)]" :data-testid="`lk-set-verwijder-${n.id}`" @click="toggleSet(n.id)">×</button>
            </li>
            <li v-if="!actieveSet.size" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">Nog niets geselecteerd.</li>
          </ul>
          <!-- ADR-033 2c — huidige actieve set bewaren als view (alleen met beheer-recht op views). -->
          <button v-if="actieveSet.size > 0 && magViewsBeheren" type="button" data-testid="lk-view-opslaan" class="mt-1 w-full rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)]" @click="openOpslaan">💾 View opslaan</button>
        </div>

        <div class="border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]">
          <p class="mb-1 font-semibold text-[length:var(--lk-text-sm)]">Detail</p>
          <!-- LI034 — het zijbalk-detail blijft GEDOKT als set-werkblad (set-acties + buren). De
               versleepbare klik-popup is nu hét ene zwevende detail-element; dit paneel sleept niet meer. -->
          <div
            v-if="detailNode"
            data-testid="lk-detail"
            class="flex flex-col gap-1 text-[length:var(--lk-text-sm)]"
          >
            <p class="font-semibold" data-testid="lk-detail-naam">{{ detailNode.naam }}</p>
            <!-- LI021 — partij: aard; gebruikersgroep: ledental; anders de component-velden. -->
            <p v-if="detailNode.element_type === 'partij'" data-testid="lk-detail-aard"><span class="text-[var(--lk-color-text-muted)]">Aard:</span> {{ detailNode.soort ? typeLabel(detailNode.soort) : '—' }}</p>
            <p v-else-if="detailNode.element_type === 'gebruikersgroep'"><span class="text-[var(--lk-color-text-muted)]">Leden:</span> {{ detailNode.aantal_leden ?? 0 }}</p>
            <template v-else>
              <p><span class="text-[var(--lk-color-text-muted)]">Domein:</span> {{ detailNode.domein || '—' }}</p>
              <p><span class="text-[var(--lk-color-text-muted)]">Leverancier:</span> {{ detailNode.leverancier_naam || '—' }}</p>
              <p><span class="text-[var(--lk-color-text-muted)]">Hosting:</span> {{ detailNode.hosting_model ? typeLabel(detailNode.hosting_model) : '—' }}</p>
              <p><span class="text-[var(--lk-color-text-muted)]">{{ veldLabel('lifecycle_status') }}:</span> <span class="inline-block rounded px-1" :style="{ background: lcStyle(detailNode.lifecycle_status).bg }">{{ detailNode.lifecycle_status ? typeLabel(detailNode.lifecycle_status) : '—' }}</span></p>
              <!-- ADR-046 — levensfase van het component (één waarheid; vervangt de
                   plateau-dispositie). Ontbrekend = gedempt "nog niet vastgelegd". -->
              <p data-testid="lk-detail-levensfase">
                <span class="text-[var(--lk-color-text-muted)]">Levensfase:</span>
                <template v-if="detailNode.levensfase"> {{ typeLabel(detailNode.levensfase) }}</template>
                <span v-else class="text-[var(--lk-color-text-muted)]"> nog niet vastgelegd</span>
              </p>
              <p><span class="text-[var(--lk-color-text-muted)]">Blokkades:</span> {{ detailNode.blokkades_open }}</p>
            </template>
            <p><span class="text-[var(--lk-color-text-muted)]">Koppelingen:</span> {{ detailKoppelingen }}</p>
            <!-- ADR-025 v4 (herzien ADR-046) — plateau-lidmaatschap als context: alle
                 plateaus, alfabetisch (deterministisch; geen dispositie meer). -->
            <p v-if="detailNode.plateau_naam" data-testid="lk-detail-plateau">
              <span class="text-[var(--lk-color-text-muted)]">Plateau:</span> {{ detailNode.plateau_naam }}
            </p>
            <button v-if="_heeftComponentDetail(detailNode)" type="button" data-testid="lk-detail-open" class="mt-1 rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-sm)] py-1 text-white" @click="openApplicatie">Open component →</button>
            <button type="button" :data-testid="`lk-detail-set`" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1" @click="toggleSet(detailNode.id)">{{ inSet(detailNode.id) ? '× Verwijder uit set' : '+ Voeg toe aan set' }}</button>
            <!-- Slice 5 (LI023) — set-acties: component-node = zichzelf + directe component-buren;
                 context-node = alle component-buren. Disabled (grayed) als er geen component-buren zijn. -->
            <button
              v-if="_isApp(detailNode)"
              type="button"
              data-testid="haal-buren-erbij-knop"
              :disabled="geselecteerdNodeBuren.length === 0"
              class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 disabled:cursor-not-allowed disabled:opacity-50"
              @click="voegBurenToe(detailNode.id)"
            >+ Haal buren erbij<span v-if="geselecteerdNodeBuren.length"> ({{ geselecteerdNodeBuren.length }})</span></button>
            <button
              v-else
              type="button"
              data-testid="voeg-context-componenten-toe-knop"
              :disabled="geselecteerdNodeBuren.length === 0"
              class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 disabled:cursor-not-allowed disabled:opacity-50"
              @click="voegContextComponentenToe(detailNode.id)"
            >+ Voeg alle componenten toe<span v-if="geselecteerdNodeBuren.length"> ({{ geselecteerdNodeBuren.length }})</span></button>
          </div>
          <p v-else class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]" data-testid="lk-detail-leeg">Klik een node voor detail.</p>
        </div>

      </aside>
    </div>

    <!-- LI019 1c-v2 — Ego-bevestiging: filter zou het centrum-component verbergen. -->
    <div
      v-if="egoFilterDialog"
      data-testid="lk-ego-filter-dialog"
      role="dialog"
      aria-modal="true"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    >
      <div class="card flex max-w-sm flex-col gap-[var(--lk-space-md)] bg-white p-[var(--lk-space-lg)]">
        <p>Het geselecteerde filter verbergt het huidige centrum-component. Wil je doorgaan?</p>
        <div class="flex justify-end gap-[var(--lk-space-sm)]">
          <button type="button" data-testid="lk-ego-filter-annuleer" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-1" @click="egoFilterAnnuleer">Annuleren</button>
          <button type="button" data-testid="lk-ego-filter-doorgaan" class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-1 text-white" @click="egoFilterDoorgaan">Doorgaan</button>
        </div>
      </div>
    </div>

    <!-- ADR-033 2c — opslaan/bewerken-dialog (naam + deel-toggle; bij bewerken optioneel de
         selectie bijwerken naar de huidige actieve set). 422 → inline veldfout op de naam. -->
    <div
      v-if="viewDialogOpen"
      data-testid="lk-view-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lk-view-dialog-titel"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    >
      <div class="card flex w-80 max-w-[90%] flex-col gap-[var(--lk-space-md)] bg-white p-[var(--lk-space-lg)]">
        <p id="lk-view-dialog-titel" class="font-semibold">{{ viewBewerkId ? 'View bewerken' : 'View opslaan' }}</p>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="font-semibold" for="lk-view-naam">Naam</span>
          <input
            id="lk-view-naam"
            v-model="viewNaam"
            type="text"
            data-testid="lk-view-naam"
            maxlength="150"
            :aria-invalid="!!viewNaamFout"
            aria-describedby="lk-view-naam-fout"
            class="lk-veld"
            @keyup.enter="bewaarView"
          />
          <span v-if="viewNaamFout" id="lk-view-naam-fout" role="alert" data-testid="lk-view-naam-fout" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-danger)]">{{ viewNaamFout }}</span>
        </label>
        <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input type="checkbox" v-model="viewGedeeld" data-testid="lk-view-gedeeld-toggle" />Delen met collega's (anders privé)
        </label>
        <label v-if="viewBewerkId && actieveSet.size" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input type="checkbox" v-model="viewSelectieBijwerken" data-testid="lk-view-selectie-bijwerken" />Selectie bijwerken naar de huidige actieve set ({{ actieveSet.size }})
        </label>
        <div class="flex justify-end gap-[var(--lk-space-sm)]">
          <button type="button" data-testid="lk-view-annuleer" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-1" @click="sluitViewDialog">Annuleren</button>
          <button type="button" data-testid="lk-view-bewaar" :disabled="viewBezig" class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-1 text-white disabled:opacity-50" @click="bewaarView">Opslaan</button>
        </div>
      </div>
    </div>

    <!-- ADR-033 2d — startscherm: bij ≥1 opgeslagen view een instap-lijst, met een duidelijke
         escape naar het geheel-model. Geen verplichte horde: één klik naar de kaart. -->
    <div
      v-if="toonStartscherm"
      data-testid="lk-startscherm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lk-startscherm-titel"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40"
      tabindex="-1"
      @keydown.esc="sluitStartscherm"
    >
      <div class="card flex w-96 max-w-[90%] flex-col gap-[var(--lk-space-md)] bg-white p-[var(--lk-space-lg)]">
        <p id="lk-startscherm-titel" class="font-semibold">Verdergaan met een opgeslagen view?</p>
        <ul class="flex max-h-72 flex-col gap-1 overflow-y-auto" data-testid="lk-startscherm-lijst">
          <li v-for="v in opgeslagenViews" :key="v.id">
            <button type="button" :data-testid="`lk-startscherm-open-${v.id}`" class="flex w-full items-center gap-2 rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-2 text-left text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)]" @click="openView(v)">
              <span class="grow truncate">{{ v.naam }}</span>
              <span v-if="!v.is_eigenaar && v.gedeeld" class="shrink-0 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">gedeeld door {{ v.maker_naam || '—' }}</span>
            </button>
          </li>
        </ul>
        <!-- LI046 — de nadruk volgt het ontwerpbesluit "leeg openen": ZELF BEGINNEN is de
             voorgestelde weg (de ene donkere knop, LI030-leesbaarheidsnorm); de hele kaart
             blijft beschikbaar als rustige, ontnadrukte uitgang eronder — de zware actie is
             geen voorgestelde weg. Volgorde: views (het antwoord op de vraag) → zelf → hele
             kaart. Borging van de nadruk: LandschapskaartView.test.js (één primary). -->
        <button type="button" data-testid="lk-startscherm-zelf" class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-2 text-white hover:bg-[#2D6DB5]" @click="sluitStartscherm">Zelf beginnen (zoek een component)</button>
        <button type="button" data-testid="lk-startscherm-hele-kaart" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-2 text-[var(--lk-color-text-muted)] hover:bg-[var(--lk-color-accent)]" @click="beginMetHeleKaart">Begin met de hele kaart →</button>
      </div>
    </div>
  </div>
</template>
