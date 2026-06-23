<script setup>
/**
 * LandschapskaartView v3 — interactieve landschapskaart op Cytoscape.js (ADR-025).
 *
 * Drie modi (Ego / Impact / Geheel model), zoeken + vier filters (domein/leverancier/hosting/
 * lifecycle), actieve migratieset, node-detail met doorklik naar het applicatie-detail, en een
 * lifecycle-legenda. De Cytoscape-graaf is een afgeleide van de reactieve state (tekenGraaf());
 * álle panelen (zoek/resultaten/set/detail/legenda/samenvatting) zijn pure Vue-state, zodat de
 * UI testbaar is met een gemockte cytoscape. Read-only; geen engine-aanraking.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from '@/composables/router'
import cytoscape from '@/composables/cytoscape'
import { api } from '@/api'
import { humaniseer } from '../labels'

const router = useRouter()
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
const RINGEN = ['applicaties', 'rollen', 'gebruikers', 'contracten', 'infrastructuur']
// ADR-031 — leesbare ring-namen. Backend levert ring='beheerorganisatie' → bij laden gemapt op 'rollen'.
const RING_LABELS = {
  applicaties: 'Applicaties',
  rollen: 'Rollen & beheer',
  gebruikers: 'Gebruikers',
  contracten: 'Contracten',
  infrastructuur: 'Infrastructuur',
}
// ADR-031 — gebruikersgroep-node-stijl (distinctief t.o.v. applicaties).
const GG_STYLE = { bg: '#e0f2fe', border: '#0ea5e9' }
const INSET = { bg: '#1e3a8a', border: '#1e3a8a' }
const RAAKVLAK = { bg: '#fed7aa', border: '#ea580c' }
// Deterministische domeinkleuren (border in "kleur op domein"-modus).
const DOMEIN_PALET = ['#2563eb', '#d97706', '#0891b2', '#7c3aed', '#16a34a', '#db2777', '#65a30d', '#dc2626']

// ── State ───────────────────────────────────────────────────────────────────────
const nodes = ref([])
const edges = ref([])
const laden = ref(true)
const fout = ref(null)

const modus = ref('ego') // 'ego' | 'impact' | 'geheel'
const zoekterm = ref('')
const filterDomein = ref('')
const filterLeverancier = ref('')
const filterHosting = ref('')
const filterLifecycle = ref('')
const ringAan = ref(new Set(RINGEN))
const actieveSet = ref(new Set())
const egoStartId = ref(null)
const detailId = ref(null)
const opbouwModus = ref(true) // geheel-model: true=insluiten (begint leeg), false=afpellen (begint vol)
const kleurOpDomein = ref(false)
const diepte = ref(1) // 1 = directe buren (ego); 2 = ook indirecte applicatie-buren (één hop dieper)

const containerRef = ref(null)
let cy = null

// ADR-031 — sub-granulariteit Gebruikers-ring: groepeer gebruikersgroepen per organisatie.
const groepeerPerOrg = ref(true)
const _rawNaam = (id) => nodes.value.find((n) => n.id === id)?.naam
// Effectieve graaf-nodes/-edges. Bij "groepeer per organisatie" vervangen we de individuele
// gebruikersgroep-nodes door één aggregaat-node per organisatie (gesommeerd ledental) en hangen
// de serving-edges aan dat aggregaat (gededupliceerd). Alle graaf-afgeleiden gebruiken deze.
const grafNodes = computed(() => {
  if (!groepeerPerOrg.value) return nodes.value
  const overig = nodes.value.filter((n) => n.element_type !== 'gebruikersgroep')
  const agg = new Map()
  for (const g of nodes.value) {
    if (g.element_type !== 'gebruikersgroep') continue
    const key = g.organisatie_id || '__overig__'
    const cur = agg.get(key) || {
      id: `gg-org-${key}`, element_type: 'gebruikersgroep', laag: 'business',
      naam: g.organisatie_id ? _rawNaam(g.organisatie_id) || 'Organisatie' : 'Overige groepen',
      organisatie_id: g.organisatie_id || null, aantal_leden: 0,
    }
    cur.aantal_leden += g.aantal_leden || 0
    agg.set(key, cur)
  }
  return [...overig, ...agg.values()]
})
const grafEdges = computed(() => {
  if (!groepeerPerOrg.value) return edges.value
  const naarAgg = new Map()
  for (const n of nodes.value) {
    if (n.element_type === 'gebruikersgroep') naarAgg.set(n.id, `gg-org-${n.organisatie_id || '__overig__'}`)
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

// ── Data laden ────────────────────────────────────────────────────────────────
async function laad() {
  laden.value = true
  fout.value = null
  try {
    const data = await api.landschapskaart.haalGrafdata({ diepte: diepte.value })
    nodes.value = data.nodes || []
    // ADR-031 — map de backend-ring 'beheerorganisatie' op de UI-ringnaam 'rollen'.
    edges.value = (data.edges || []).map((e) => (e.ring === 'beheerorganisatie' ? { ...e, ring: 'rollen' } : e))
    const eersteApp = nodes.value.find(isApplicatie)
    egoStartId.value = eersteApp ? eersteApp.id : null
  } catch (e) {
    fout.value = e?.message || 'Laden van de landschapskaart mislukt.'
  } finally {
    laden.value = false
  }
}

// Diepte-toggle: herlaad de grafdata (?diepte=…) én pas de stap-diepte client-side toe (ego-view).
async function zetDiepte(d) {
  if (diepte.value === d) return
  diepte.value = d
  await laad()
}

// Alleen applicaties zijn selecteerbaar via de zoeklijst/filters/actieve set; partijen,
// contracten en infrastructuur verschijnen automatisch als ring-nodes rond de gekozen apps.
const _isApp = (n) => n?.element_type === 'applicatie' || (n?.element_type === 'component' && n?.laag === 'application')
const appNodes = computed(() => nodes.value.filter(_isApp))

// ── Filter-opties (datagedreven; alleen uit de applicaties) ──────────────────────
const _uniek = (sel) => [...new Set(appNodes.value.map(sel).filter(Boolean))].sort()
const domeinOpties = computed(() => _uniek((n) => n.domein))
const leverancierOpties = computed(() => _uniek((n) => n.leverancier_naam))
const hostingOpties = computed(() => _uniek((n) => n.hosting_model))
const domeinKleur = computed(() => Object.fromEntries(domeinOpties.value.map((d, i) => [d, DOMEIN_PALET[i % DOMEIN_PALET.length]])))

// ── Zoeken + filteren ─────────────────────────────────────────────────────────
const filterActief = computed(
  () => !!(zoekterm.value.trim() || filterDomein.value || filterLeverancier.value || filterHosting.value || filterLifecycle.value),
)
function _matcht(n) {
  const q = zoekterm.value.trim().toLowerCase()
  if (q && !`${n.naam || ''} ${n.domein || ''} ${n.leverancier_naam || ''}`.toLowerCase().includes(q)) return false
  if (filterDomein.value && n.domein !== filterDomein.value) return false
  if (filterLeverancier.value && n.leverancier_naam !== filterLeverancier.value) return false
  if (filterHosting.value && n.hosting_model !== filterHosting.value) return false
  if (filterLifecycle.value && n.lifecycle_status !== filterLifecycle.value) return false
  return true
}
const gefilterdeNodes = computed(() => appNodes.value.filter(_matcht))

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
const zichtbareNodes = computed(() => {
  if (modus.value === 'ego') {
    return grafNodes.value.filter((n) => egoZichtbaarIds.value.has(n.id))
  }
  if (modus.value === 'impact') return grafNodes.value.filter(isApplicatie)
  // Geheel model toont standaard het VOLLEDIGE landschap (Fix 1: gebruiker verwacht alles te zien).
  // Filters verfijnen: opbouw = alleen de match; afpel = alles behalve de match.
  if (!filterActief.value) return grafNodes.value
  const match = new Set(gefilterdeNodes.value.map((n) => n.id))
  return grafNodes.value.filter((n) => (opbouwModus.value ? match.has(n.id) : !match.has(n.id)))
})
const zichtbareNodeIds = computed(() => new Set(zichtbareNodes.value.map((n) => n.id)))
const zichtbareEdges = computed(() =>
  grafEdges.value.filter(
    // Fix 4 — ringAan filtert de edges in ALLE modi (niet meer alleen ego/geheel).
    (e) => zichtbareNodeIds.value.has(e.bron_id) && zichtbareNodeIds.value.has(e.doel_id) && ringAan.value.has(e.ring),
  ),
)

// ── Impact-berekening ───────────────────────────────────────────────────────────
const flowEdges = computed(() => grafEdges.value.filter((e) => e.ring === 'applicaties'))
const grensEdges = computed(() => flowEdges.value.filter((e) => actieveSet.value.has(e.bron_id) !== actieveSet.value.has(e.doel_id)))
const raakvlakken = computed(() => {
  const s = new Set()
  for (const e of grensEdges.value) {
    if (!actieveSet.value.has(e.bron_id)) s.add(e.bron_id)
    if (!actieveSet.value.has(e.doel_id)) s.add(e.doel_id)
  }
  return s
})
const impactSamenvatting = computed(
  () => `${actieveSet.value.size} in set · ${raakvlakken.value.size} raakvlakken · ${grensEdges.value.length} grensoverschrijdende koppelingen`,
)

// ── Actieve set ─────────────────────────────────────────────────────────────────
function inSet(id) {
  return actieveSet.value.has(id)
}
function toggleSet(id) {
  const s = new Set(actieveSet.value)
  s.has(id) ? s.delete(id) : s.add(id)
  actieveSet.value = s
}
function voegAlleGefilterdeToe() {
  const s = new Set(actieveSet.value)
  for (const n of gefilterdeNodes.value) s.add(n.id)
  actieveSet.value = s
}
const actieveSetNodes = computed(() => [...actieveSet.value].map((id) => nodePerId.value[id]).filter(Boolean))

// ── Detail ────────────────────────────────────────────────────────────────────
const detailNode = computed(() => (detailId.value ? nodePerId.value[detailId.value] : null))
const detailKoppelingen = computed(() => {
  const id = detailId.value
  if (!id) return 0
  return grafEdges.value.filter((e) => e.bron_id === id || e.doel_id === id).length
})
function selecteerNode(id) {
  detailId.value = id
  // LI021 — in ego-modus hercentreert een klik op ELKE node (applicatie, partij, gebruikersgroep, …),
  // niet langer alleen applicaties.
  if (modus.value === 'ego' && nodePerId.value[id]) egoStartId.value = id
  // Fix 3: highlight + centreer de node in de grafiek (voor o.a. klik op een actieve-set-item).
  if (!cy) return
  cy.elements?.().unselect?.()
  const node = cy.getElementById?.(String(id))
  if (!node || !node.length) return
  node.select?.()
  cy.animate?.({ center: { eles: node }, zoom: Math.max(cy.zoom?.() ?? 1, 1.2), duration: 400, easing: 'ease-in-out-cubic' })
}
function openApplicatie() {
  if (detailNode.value) router.push({ name: 'applicatie-detail', params: { id: detailNode.value.id } })
}

// ── Klik-detail-popups (koppeling + knoop) + fullscreen — read-only weergave ─────
// Gedeelde popup-state: koppeling- én knoop-popup delen vorm + sluitgedrag. Een nieuwe
// klik VERVANGT de open popup (zelfde refs). Engine onaangeroerd (alleen lezen via api).
const popupOpen = ref(false)
const popupKind = ref(null) // 'node' | 'edge'
const popupTitel = ref('')
const popupBadge = ref(null) // 'Inkomend' | 'Uitgaand' (alleen koppeling t.o.v. ego)
const popupLaden = ref(false)
const popupVelden = ref([]) // [{ label, waarde }] — uitsluitend ingevulde velden (knoop-popup)
// Koppeling-popup (ADR-023a Fase 4) — master-detail: links de flow-lijst van het paar, rechts het detail.
const popupFlows = ref([]) // [{ id, naam, positie:'uit'|'in', tegenNaam, richting, protocol, impact, omschrijving }]
const popupSelId = ref(null) // geselecteerde flow (master); default = eerste rij
const popupMelding = ref(null) // RBAC-/terugval-melding (geen technische fout)
const popupGeselecteerd = computed(() => popupFlows.value.find((f) => f.id === popupSelId.value) || popupFlows.value[0] || null)
function selecteerFlow(id) { popupSelId.value = id }
const popupActies = ref([]) // [{ label, fn }] — doorklik-links naar detailschermen (node + edge)
const geselecteerdeEdgeId = ref(null) // cy-id van de aangeklikte edge (highlight zolang popup open)
const fullscreen = ref(false)

// B2 — doorklik-link naar het detailscherm van een node (null als er geen eigen scherm is).
function _detailLink(node) {
  if (!node) return null
  const id = node.id
  switch (node.element_type) {
    case 'applicatie': return { label: 'Open applicatie →', fn: () => router.push({ name: 'applicatie-detail', params: { id } }) }
    case 'partij': return { label: 'Open partij →', fn: () => router.push({ name: 'partij-detail', params: { id } }) }
    case 'contract': return { label: 'Open contract →', fn: () => router.push({ name: 'contract-detail', params: { id } }) }
    case 'gebruikersgroep': return null
  }
  // Overige componenten: alleen de applicatielaag heeft een betekenisvol detailscherm; infra (technology) niet.
  return node.laag === 'application'
    ? { label: 'Open component →', fn: () => router.push({ name: 'component-detail', params: { id } }) }
    : null
}

function sluitPopup() {
  popupOpen.value = false
  popupKind.value = null
  popupTitel.value = ''
  popupBadge.value = null
  popupVelden.value = []
  popupFlows.value = []
  popupSelId.value = null
  popupMelding.value = null
  popupActies.value = []
  // B1 — highlight van de aangeklikte edge opheffen.
  geselecteerdeEdgeId.value = null
  cy?.edges?.()?.removeClass?.('sel-edge')
}

// Veld alleen opnemen als de waarde bestaat/ingevuld is (toon nooit lege regels).
const _veld = (label, waarde) => (waarde != null && waarde !== '' ? { label, waarde } : null)
const _velden = (arr) => arr.filter(Boolean)

// Directe pre-fill van een knoop-popup uit de kaart-data (vóór de detail-fetch laadt).
function _nodePrefill(n) {
  return _velden([
    _veld('Type', n.element_type ? typeLabel(n.element_type) : null),
    _veld('Status', n.lifecycle_status ? typeLabel(n.lifecycle_status) : null),
    _veld('Domein', n.domein ? typeLabel(n.domein) : null),
    _veld('Leverancier', n.leverancier_naam),
    _veld('Hosting', n.hosting_model ? typeLabel(n.hosting_model) : null),
    n.blokkades_open != null ? { label: 'Open blokkades', waarde: String(n.blokkades_open) } : null,
  ])
}

function _nodeVelden(et, d, n) {
  if (et === 'applicatie') {
    return _velden([
      _veld('Status', d.lifecycle_status ? typeLabel(d.lifecycle_status) : null),
      _veld('Eigenaar-organisatie', d.eigenaar_organisatie_naam),
      _veld('Hostingmodel', d.hostingmodel ? typeLabel(d.hostingmodel) : null),
      _veld('Migratiepad', d.migratiepad ? typeLabel(d.migratiepad) : null),
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
  if (et === 'partij') {
    const adres = [d.straat_huisnummer, d.postcode, d.plaats].filter(Boolean).join(', ') || null
    return _velden([
      _veld('Aard', d.aard ? typeLabel(d.aard) : null),
      _veld('Functietitel', d.functietitel),
      _veld('Contactpersoon', d.contactpersoon),
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
    _veld('Status', d.lifecycle_status ? typeLabel(d.lifecycle_status) : null),
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
    if (et === 'applicatie') d = await api.applicaties.haal(id)
    else if (et === 'contract') d = await api.contracten.haal(id)
    else if (et === 'partij') d = await api.partijen.haal(id)
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

// Koppeling-popup (flow-edge) — ADR-023a Fase 4. Eén edge = een gericht applicatiepaar dat één
// of meer flows bundelt. Haal ALLE flows van het ONGEORDENDE paar op, sorteer op naam, en toon
// ze als master-detail (links lijst + richting-icoon, rechts detail). Geldt ook bij n=1.
async function openEdgePopup(edge) {
  if (!edge) return
  const bronNaam = nodePerId.value[edge.bron_id]?.naam || '?'
  const doelNaam = nodePerId.value[edge.doel_id]?.naam || '?'
  popupKind.value = 'edge'
  popupBadge.value = null
  // B2 — doorklik naar bron/doel-entiteit waar die een eigen detailscherm heeft.
  popupActies.value = [edge.bron_id, edge.doel_id]
    .map((nid) => {
      const node = nodePerId.value[nid]
      const l = _detailLink(node)
      return l ? { label: `Open ${node.naam} →`, fn: l.fn } : null
    })
    .filter(Boolean)
  popupMelding.value = null
  popupVelden.value = []
  popupFlows.value = []
  popupSelId.value = null
  popupOpen.value = true
  // ADR-031 — niet-flow ringen: directe velden uit de edge + node-namen (geen API-call).
  if (edge.ring !== 'applicaties') {
    popupLaden.value = false
    if (edge.ring === 'rollen') {
      popupTitel.value = edge.label || 'Rol'
      popupVelden.value = _velden([_veld('Partij', bronNaam), _veld('Object', doelNaam)])
    } else if (edge.ring === 'contracten') {
      popupTitel.value = 'Valt onder contract'
      popupVelden.value = _velden([_veld('Component', bronNaam), _veld('Contract', doelNaam)])
    } else if (edge.ring === 'infrastructuur') {
      popupTitel.value = 'Draait op'
      popupVelden.value = _velden([_veld('Component', doelNaam), _veld('Host', bronNaam)])
    } else if (edge.ring === 'gebruikers') {
      popupTitel.value = 'Gebruikt door'
      const gg = nodePerId.value[edge.doel_id]
      popupVelden.value = _velden([
        _veld('Applicatie', bronNaam),
        _veld('Gebruikersgroep', doelNaam),
        gg?.aantal_leden ? { label: 'Leden', waarde: String(gg.aantal_leden) } : null,
      ])
    }
    return
  }
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
    // LI021 — dubbelklik hercentreert; vanuit Geheel model / Impact-view schakelt dit naar ego
    // met deze node (ook partij/gebruikersgroep) als centrum.
    if (modus.value !== 'ego') modus.value = 'ego'
    selecteerNode(id)
    return
  }
  if (_tapTimer) clearTimeout(_tapTimer)
  _tapId = id
  _tapTimer = setTimeout(() => { _tapTimer = null; _tapId = null; openNodePopup(id) }, _DBLTAP_MS)
}

// Fullscreen-overlay (in-app): de hele view vult het venster via een CSS-klasse — GEEN
// remount, dus alle state (centrum/selectie/popup/set/filters) blijft behouden. Zoom/pan
// wordt expliciet bewaard (de ResizeObserver fit niet tijdens de toggle).
let _behoudViewport = false
function toggleFullscreen() {
  const z = cy?.zoom?.()
  const p = cy?.pan?.()
  _behoudViewport = true
  fullscreen.value = !fullscreen.value
  nextTick(() => {
    cy?.resize?.()
    if (typeof z === 'number' && p) { cy?.zoom?.(z); cy?.pan?.(p) }
    setTimeout(() => { _behoudViewport = false }, 200)
  })
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
function _nodeData(n) {
  const isGG = n.element_type === 'gebruikersgroep'
  let bg = isGG ? GG_STYLE.bg : lcStyle(n.lifecycle_status).bg
  let border = isGG
    ? GG_STYLE.border
    : kleurOpDomein.value && n.domein
      ? domeinKleur.value[n.domein]
      : lcStyle(n.lifecycle_status).border
  if (modus.value === 'impact' && !isGG) {
    if (inSet(n.id)) ({ bg, border } = INSET)
    else if (raakvlakken.value.has(n.id)) ({ bg, border } = RAAKVLAK)
  }
  // ADR-031 — gebruikersgroep: ledental als tweede labelregel (alleen bij >0); anders blokkade-vlag.
  const label = isGG
    ? (n.naam || '') + (n.aantal_leden > 0 ? `\n(${n.aantal_leden})` : '')
    : (n.naam || '') + (n.blokkades_open > 0 ? ' ⚠' : '')
  return { id: n.id, label, bg, border, txt: _txtColor(bg), shape: isGG ? 'ellipse' : 'round-rectangle' }
}
function _edgeData(e, i) {
  let lc = '#cbd5e1'
  let w = 1.5
  let ls = 'solid'
  if (modus.value === 'impact' && e.ring === 'applicaties') {
    const grens = actieveSet.value.has(e.bron_id) !== actieveSet.value.has(e.doel_id)
    const beide = actieveSet.value.has(e.bron_id) && actieveSet.value.has(e.doel_id)
    lc = grens ? '#ea580c' : beide ? '#2563eb' : '#cbd5e1'
    w = grens ? 3 : 2
  }
  // Koppelingsdetails op flow-edges: "koppeling · REST · → · 3×" (→ eenrichting, ↔ twee-/
  // bidirectioneel; "N×" alleen bij ≥2 samengetrokken koppelingen op dit paar — ADR-023a Fase 3).
  let label = ''
  if (e.ring === 'applicaties') {
    const pijl = e.richting === 'tweerichting' || e.richting === 'bidirectioneel' ? '↔' : '→'
    label = ['koppeling', e.protocol ? String(e.protocol).toUpperCase() : null, pijl, e.aantal >= 2 ? `${e.aantal}×` : null].filter(Boolean).join(' · ')
  } else {
    // ADR-031 — rol-naam / 'gebruikt door' / 'valt onder' / 'draait op' uit de edge-data.
    label = e.label || ''
  }
  // Fix 2 — geheel-model: geen edge-labels (te druk). Ego/impact: wel; zoom-drempel via _pasEdgeLabels().
  if (modus.value === 'geheel') label = ''
  return { id: `e${i}-${e.bron_id}-${e.doel_id}-${e.relatietype}`, source: e.bron_id, target: e.doel_id, ring: e.ring, lc, w, ls, label }
}
// LI020 — definitieve node-set voor het canvas. Een node is zichtbaar als:
//  • het ego-centrum (ego-modus), OF
//  • hij raakt minstens één ZICHTBARE (ring-aan) edge.
// Losse nodes (geen zichtbare edge) worden ALTIJD verborgen — incl. nodes waarvan alle edges in
// uitgevinkte ringen zitten. Dedup op id (defensief — voorkomt dubbele Cytoscape-node-ids).
const getekendeNodes = computed(() => {
  const metZichtbareEdge = new Set()
  zichtbareEdges.value.forEach((e) => { metZichtbareEdge.add(e.bron_id); metZichtbareEdge.add(e.doel_id) })
  const uniek = new Map()
  for (const n of zichtbareNodes.value) {
    if (uniek.has(n.id)) continue
    const egoCentrum = modus.value === 'ego' && n.id === egoStartId.value
    if (egoCentrum || metZichtbareEdge.has(n.id)) uniek.set(n.id, n)
  }
  return [...uniek.values()]
})

function _elementen() {
  const zn = getekendeNodes.value
  const znIds = new Set(zn.map((n) => n.id))
  const ze = zichtbareEdges.value.filter((e) => znIds.has(e.bron_id) && znIds.has(e.doel_id))
  return [
    ...zn.map((n) => ({ data: _nodeData(n), classes: n.element_type === 'gebruikersgroep' ? 'gg' : undefined })),
    ...ze.map((e, i) => ({ data: _edgeData(e, i) })),
  ]
}
const zichtbaarAantal = computed(() => getekendeNodes.value.length)

function _layout() {
  if (modus.value === 'ego') {
    return {
      name: 'concentric', concentric: (n) => (n.id() === egoStartId.value ? 10 : 5), levelWidth: () => 1,
      minNodeSpacing: 60, padding: 60, animate: true, animationDuration: 400, // Fix 2: meer ruimte
    }
  }
  // Fix 2: ruimere cose-spreiding → leesbaardere labels/relaties (impact + geheel).
  // Fix 3 — agressievere spreiding tegen node-overlap bij grotere grafen.
  return {
    name: 'cose', idealEdgeLength: 150, edgeElasticity: 100,
    nodeRepulsion: modus.value === 'geheel' ? 14000 : 9000,
    nodeOverlap: 20, componentSpacing: 100, gravity: 0.25, numIter: 1000,
    initialTemp: 200, coolingFactor: 0.99, minTemp: 1.0,
    padding: 60, randomize: false, animate: true, animationDuration: 600, fit: true,
  }
}

// Fix 2 — edge-labels alleen boven de zoom-drempel én buiten geheel-model (anti-overlap).
const _LABEL_ZOOM = 0.6
function _pasEdgeLabels() {
  if (!cy) return
  const toon = modus.value !== 'geheel' && (cy.zoom?.() ?? 1) > _LABEL_ZOOM
  cy.edges?.().style?.('text-opacity', toon ? 1 : 0)
}
async function tekenGraaf() {
  if (!cy) return
  await nextTick()
  await nextTick() // tweede tick voor (HMR-)edge cases waarin de layout nog niet geflusht is
  // Cytoscape meet zijn container soms op 0 (flex-hoogte nog niet gezet) → forceer een hoogte
  // zodat de graaf nooit op 0px initialiseert en zichtbaar blijft i.p.v. leeg.
  const el = containerRef.value
  if (el && el.offsetHeight === 0) el.style.minHeight = '500px'
  cy.elements().remove()
  cy.add(_elementen())
  cy.layout(_layout()).run()
  // Klein delay voor de browser-layout-flush, dán her-meten + passend maken.
  setTimeout(() => {
    cy?.resize?.()
    cy?.fit?.(undefined, 50)
    _pasEdgeLabels()
  }, 100)
}

const CY_STYLE = [
  {
    selector: 'node',
    style: {
      'background-color': 'data(bg)', 'border-color': 'data(border)', 'border-width': 2,
      label: 'data(label)', 'font-size': 11, color: 'data(txt)', 'text-valign': 'center', 'text-halign': 'center',
      width: 78, height: 28, shape: 'data(shape)', 'text-wrap': 'ellipsis', 'text-max-width': 70,
    },
  },
  // ADR-031 — gebruikersgroep-nodes: ronde vorm + wrap (ledental op tweede regel).
  { selector: 'node.gg', style: { shape: 'ellipse', 'text-wrap': 'wrap', width: 64, height: 64 } },
  {
    selector: 'edge',
    style: {
      width: 'data(w)', 'line-color': 'data(lc)', 'line-style': 'data(ls)',
      'target-arrow-shape': 'triangle', 'target-arrow-color': 'data(lc)', 'curve-style': 'bezier',
      // Koppelingsdetail-label (flow-edges): protocol + richting.
      label: 'data(label)', 'font-size': 8, color: 'var(--cd-color-text-muted)', 'text-wrap': 'none',
      'text-rotation': 'autorotate', 'text-background-color': '#fff', 'text-background-opacity': 0.8,
    },
  },
  // B1 — aangeklikte edge gemarkeerd zolang de popup open is (accentkleur + dikker).
  { selector: 'edge.sel-edge', style: { 'line-color': '#e67e22', 'target-arrow-color': '#e67e22', width: 4, 'z-index': 999, 'text-opacity': 1 } },
  // Fix 3: visuele markering van de geselecteerde node (klik op set-item / node).
  { selector: 'node:selected', style: { 'border-width': 4, 'border-color': '#f59e0b', 'border-style': 'solid' } },
]

let resizeObserver = null

onMounted(async () => {
  await laad()
  // ADR-025 deep-link: ?center=<applicatie-id>&modus=<ego|impact|geheel> (vanuit het applicatie-detail).
  // De center-applicatie wordt het ego-middelpunt + de actieve set, zodat de kaart erop centreert.
  const qModus = route.query?.modus ? String(route.query.modus) : null
  const qCenter = route.query?.center ? String(route.query.center) : null
  if (qModus && ['ego', 'impact', 'geheel'].includes(qModus)) modus.value = qModus
  if (qCenter) {
    actieveSet.value = new Set([qCenter])
    egoStartId.value = qCenter
    detailId.value = qCenter
  }
  await nextTick() // wacht tot de canvas-div in de DOM staat (en de flex-hoogte gezet is)
  if (containerRef.value) {
    cy = cytoscape({ container: containerRef.value, elements: [], style: CY_STYLE })
    // Enkele tap = popup (uitgesteld), dubbele tap = hercentreren — zie onNodeTap.
    cy.on('tap', 'node', (evt) => onNodeTap(evt.target.id()))
    // Tap op een koppeling (flow-edge) opent de koppeling-popup.
    cy.on('tap', 'edge', (evt) => {
      const src = evt.target.data('source')
      const tgt = evt.target.data('target')
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
    // Fix 2 — edge-labels tonen/verbergen op zoomniveau (anti-overlap).
    cy.on('zoom', _pasEdgeLabels)
    tekenGraaf()
    // Her-meten + passend maken bij containerwijzigingen (modus-wissel, sidebar, venster-resize).
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => {
        cy?.resize?.()
        if (_behoudViewport) return // fullscreen-toggle: zoom/pan behouden, niet fitten
        cy?.fit?.(undefined, 50)
      })
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

defineExpose({ openNodePopup, openEdgePopup, selecteerFlow, onNodeTap, sluitPopup, toggleFullscreen, fullscreen, popupOpen, _edgeData, groepeerPerOrg, grafNodes, grafEdges })

// Hertekenen bij elke state die de graaf raakt.
watch(
  [modus, zichtbareNodes, zichtbareEdges, actieveSet, kleurOpDomein, groepeerPerOrg],
  () => tekenGraaf(),
  { deep: false },
)

function setModus(m) {
  modus.value = m
  // Fix 1: Geheel model vult de actieve set met álle applicaties (de gebruiker ziet meteen
  // het volledige landschap; daarna verwijderen/filteren kan). Afpel-modus begint dus óók "vol".
  if (m === 'geheel') actieveSet.value = new Set(appNodes.value.map((n) => n.id))
}
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
    :class="['flex w-full flex-col', fullscreen ? 'fixed inset-0 z-[400] bg-[var(--cd-color-bg)]' : '']"
    data-testid="lk-wrapper"
    :style="fullscreen ? 'height: 100vh' : 'height: calc(100vh - 9rem)'"
  >
    <!-- Topbar: modus-toggle -->
    <div class="flex items-center gap-[var(--cd-space-sm)] border-b border-[var(--cd-color-border)] bg-white p-[var(--cd-space-sm)]">
      <div class="flex gap-1 rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-accent)] p-1">
        <button v-for="m in ['ego', 'impact', 'geheel']" :key="m" type="button" :data-testid="`lk-modus-${m}`" :aria-pressed="modus === m" :class="['rounded-[var(--cd-radius-btn)] px-[var(--cd-space-md)] py-1 text-[length:var(--cd-text-sm)]', modus === m ? 'bg-[var(--cd-color-primary)] text-white' : '']" @click="setModus(m)">
          {{ m === 'ego' ? 'Ego-view' : m === 'impact' ? 'Impact-view' : 'Geheel model' }}
        </button>
      </div>
      <span class="ml-auto text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]" data-testid="lk-zichtbaar-aantal">{{ zichtbaarAantal }} nodes zichtbaar</span>
    </div>

    <div class="flex min-h-0 flex-1">
      <!-- Linkerpaneel: zoek + filters + resultaten -->
      <aside class="flex w-60 flex-shrink-0 flex-col gap-[var(--cd-space-sm)] overflow-y-auto border-r border-[var(--cd-color-border)] bg-white p-[var(--cd-space-md)]" data-testid="lk-links">
        <input v-model="zoekterm" type="search" data-testid="lk-zoek" placeholder="🔍 Zoek naam/domein/leverancier…" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)]" />

        <select v-model="filterDomein" data-testid="lk-filter-domein" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)]">
          <option value="">Alle domeinen</option>
          <option v-for="d in domeinOpties" :key="d" :value="d">{{ typeLabel(d) }}</option>
        </select>
        <select v-model="filterLeverancier" data-testid="lk-filter-leverancier" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)]">
          <option value="">Alle leveranciers</option>
          <option v-for="l in leverancierOpties" :key="l" :value="l">{{ l }}</option>
        </select>
        <select v-model="filterHosting" data-testid="lk-filter-hosting" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)]">
          <option value="">Alle hosting</option>
          <option v-for="h in hostingOpties" :key="h" :value="h">{{ typeLabel(h) }}</option>
        </select>
        <select v-model="filterLifecycle" data-testid="lk-filter-lifecycle" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)]">
          <option value="">Alle lifecycle</option>
          <option v-for="lc in LIFECYCLE_OPTIES" :key="lc" :value="lc">{{ typeLabel(lc) }}</option>
        </select>

        <label v-if="modus === 'geheel'" class="flex items-center gap-2 text-[length:var(--cd-text-sm)]">
          <input type="checkbox" :checked="!opbouwModus" data-testid="lk-afpel-toggle" @change="opbouwModus = !opbouwModus" />Afpel-modus (begint vol)
        </label>

        <!-- Diepte-toggle (ego + geheel): 1 stap = directe buren, 2 stappen = ook indirecte. -->
        <div v-if="modus === 'ego' || modus === 'geheel'" class="flex flex-col gap-1" data-testid="lk-diepte">
          <p class="font-semibold text-[length:var(--cd-text-sm)]">Diepte</p>
          <div class="flex gap-1">
            <button type="button" data-testid="lk-diepte-1" :aria-pressed="diepte === 1" :class="['rounded-[var(--cd-radius-btn)] px-[var(--cd-space-sm)] py-0.5 text-[length:var(--cd-text-xs)]', diepte === 1 ? 'bg-[var(--cd-color-primary)] text-white' : 'bg-[var(--cd-color-accent)]']" @click="zetDiepte(1)">1 stap (direct)</button>
            <button type="button" data-testid="lk-diepte-2" :aria-pressed="diepte === 2" :class="['rounded-[var(--cd-radius-btn)] px-[var(--cd-space-sm)] py-0.5 text-[length:var(--cd-text-xs)]', diepte === 2 ? 'bg-[var(--cd-color-primary)] text-white' : 'bg-[var(--cd-color-accent)]']" @click="zetDiepte(2)">2 stappen</button>
          </div>
        </div>

        <!-- Fix 4 — ring-checkboxes in alle modi (globale laagfilters). Geen wrapper-<template>
             zonder directive: Vue rendert die niet → checkboxes verdwenen (LI018-regressie). -->
        <p class="font-semibold text-[length:var(--cd-text-sm)]">Ringen</p>
        <template v-for="r in RINGEN" :key="r">
          <label class="flex items-center gap-2 text-[length:var(--cd-text-sm)]">
            <input type="checkbox" :checked="ringAan.has(r)" :data-testid="`lk-ring-${r}`" @change="toggleRing(r)" />{{ RING_LABELS[r] || typeLabel(r) }}
          </label>
          <!-- ADR-031 — sub-granulariteit: alleen zichtbaar als de Gebruikers-ring aan staat. -->
          <label v-if="r === 'gebruikers' && ringAan.has('gebruikers')" class="ml-5 flex items-center gap-2 text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">
            <input type="checkbox" :checked="groepeerPerOrg" data-testid="lk-groepeer-org" @change="groepeerPerOrg = !groepeerPerOrg" />Groepeer per organisatie
          </label>
        </template>

        <p class="mt-[var(--cd-space-sm)] font-semibold text-[length:var(--cd-text-sm)]">Resultaten ({{ gefilterdeNodes.length }})</p>
        <ul class="flex flex-col gap-1" data-testid="lk-resultaten">
          <li v-for="n in gefilterdeNodes" :key="n.id" :data-testid="`lk-res-${n.id}`" :class="['flex items-center gap-1 rounded px-1 py-0.5 text-[length:var(--cd-text-sm)]', inSet(n.id) ? 'bg-[var(--cd-color-accent)]' : '']">
            <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: lcStyle(n.lifecycle_status).bg, border: `1px solid ${lcStyle(n.lifecycle_status).border}` }"></span>
            <button type="button" class="grow truncate text-left hover:underline" :data-testid="`lk-res-naam-${n.id}`" @click="selecteerNode(n.id)">{{ n.naam }}</button>
            <span v-if="n.blokkades_open > 0" :data-testid="`lk-res-blok-${n.id}`" title="Open blokkade(s)">⚠</span>
            <span v-if="n.hosting_model">{{ hostingIcoon(n.hosting_model) }}</span>
            <button type="button" class="text-[var(--cd-color-primary)]" :data-testid="`lk-res-set-${n.id}`" @click="toggleSet(n.id)">{{ inSet(n.id) ? '×' : '+' }}</button>
          </li>
          <li v-if="!gefilterdeNodes.length" class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">Geen resultaten.</li>
        </ul>
        <button type="button" data-testid="lk-voeg-alle" class="mt-1 rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-primary)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)] text-white" @click="voegAlleGefilterdeToe">+ Voeg alle gefilterde toe</button>
      </aside>

      <!-- Canvas — min-h-0 is kritiek: zonder negeert een flex-child de height:100% van de parent,
           waardoor Cytoscape op hoogte 0 initialiseert en de graaf leeg/onzichtbaar blijft. -->
      <div class="relative min-h-0 min-w-0 flex-1 bg-[var(--cd-color-surface)]">
        <!-- Inline min-height als harde vangrail: zelfs als de flex-hoogteketen faalt, krijgt
             Cytoscape een meetbare hoogte op het init-moment (anders blijft de graaf leeg). -->
        <div ref="containerRef" data-testid="lk-canvas" class="h-full w-full" style="min-height: 500px"></div>

        <!-- Tools (rechtsboven) -->
        <div class="absolute right-3 top-3 z-10 flex gap-1">
          <button type="button" data-testid="lk-centreer" class="rounded-[var(--cd-radius-btn)] bg-white/90 px-2 py-1 text-[length:var(--cd-text-sm)] shadow-[var(--cd-shadow-sm)]" @click="centreer">⊡ Centreer</button>
          <button type="button" data-testid="lk-kleur-domein" :aria-pressed="kleurOpDomein" :class="['rounded-[var(--cd-radius-btn)] px-2 py-1 text-[length:var(--cd-text-sm)] shadow-[var(--cd-shadow-sm)]', kleurOpDomein ? 'bg-[var(--cd-color-primary)] text-white' : 'bg-white/90']" @click="kleurOpDomein = !kleurOpDomein">Kleur op domein</button>
          <!-- Fullscreen-overlay (in-app): één toggle — vergroten ingebed, verkleinen in de overlay. -->
          <button type="button" :data-testid="fullscreen ? 'lk-fullscreen-sluit' : 'lk-fullscreen-open'" :aria-pressed="fullscreen" class="rounded-[var(--cd-radius-btn)] bg-white/90 px-2 py-1 text-[length:var(--cd-text-sm)] shadow-[var(--cd-shadow-sm)]" @click="toggleFullscreen">{{ fullscreen ? '✕ Verkleinen' : '⛶ Vergroten' }}</button>
        </div>

        <!-- Klik-detail-popup (koppeling of knoop) — gedeelde vorm; sluiten via knop, Escape
             of een tap op leeg canvas. Een nieuwe klik vervangt de inhoud. -->
        <div
          v-if="popupOpen"
          data-testid="lk-popup"
          role="dialog"
          aria-label="Detail"
          :class="['absolute left-3 top-3 z-20 max-w-[90%] rounded-[var(--cd-radius-card)] border border-[var(--cd-color-border)] bg-white p-[var(--cd-space-md)] shadow-[var(--cd-shadow-lg)]', popupKind === 'edge' ? 'w-[34rem]' : 'w-72']"
        >
          <div class="flex items-start justify-between gap-2">
            <div>
              <p v-if="popupBadge" data-testid="lk-popup-badge" class="text-[length:var(--cd-text-xs)] font-semibold uppercase text-[var(--cd-color-primary-700)]">{{ popupBadge }}</p>
              <p class="font-semibold" data-testid="lk-popup-titel">{{ popupTitel }}</p>
            </div>
            <button type="button" data-testid="lk-popup-sluit" aria-label="Sluiten" class="shrink-0 text-[var(--cd-color-text-muted)] hover:text-[var(--cd-color-text)]" @click="sluitPopup">✕</button>
          </div>
          <p v-if="popupLaden" data-testid="lk-popup-laden" class="mt-2 text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">Laden…</p>
          <dl v-if="popupVelden.length" data-testid="lk-popup-velden" class="mt-2 grid grid-cols-[auto_1fr] gap-x-[var(--cd-space-sm)] gap-y-0.5 text-[length:var(--cd-text-sm)]">
            <template v-for="v in popupVelden" :key="v.label">
              <dt class="text-[var(--cd-color-text-muted)]">{{ v.label }}</dt>
              <dd class="break-words">{{ v.waarde }}</dd>
            </template>
          </dl>
          <!-- Koppeling-popup (flow-edge) — master-detail: links de flow-lijst (naam + richting-
               icoon), rechts het detail van de geselecteerde flow. Ook bij n=1 (ADR-023a Fase 4). -->
          <div v-if="popupKind === 'edge' && popupFlows.length" data-testid="lk-popup-md" class="mt-2 flex gap-[var(--cd-space-md)]">
            <ul data-testid="lk-popup-lijst" class="w-2/5 shrink-0 flex flex-col gap-0.5 border-r border-[var(--cd-color-border)] pr-[var(--cd-space-sm)] text-[length:var(--cd-text-sm)]">
              <li v-for="f in popupFlows" :key="f.id">
                <button
                  type="button"
                  :data-testid="`lk-popup-flow-${f.id}`"
                  :aria-selected="popupGeselecteerd && f.id === popupGeselecteerd.id"
                  :class="['flex w-full items-center gap-1 rounded px-1 py-0.5 text-left', popupGeselecteerd && f.id === popupGeselecteerd.id ? 'bg-[var(--cd-color-accent)] font-semibold' : 'hover:bg-[var(--cd-color-accent)]']"
                  @click="selecteerFlow(f.id)"
                >
                  <span :class="['shrink-0', f.positie === 'uit' ? 'text-[var(--cd-color-success,#16a34a)]' : 'text-[var(--cd-color-danger)]']" :title="f.positie === 'uit' ? 'Uitgaand' : 'Inkomend'">{{ f.positie === 'uit' ? '→' : '←' }}</span>
                  <span class="grow truncate">{{ f.naam }}</span>
                </button>
              </li>
            </ul>
            <dl v-if="popupGeselecteerd" data-testid="lk-popup-detail" class="grid w-3/5 grid-cols-[auto_1fr] content-start gap-x-[var(--cd-space-sm)] gap-y-0.5 text-[length:var(--cd-text-sm)]">
              <dt class="col-span-2 font-semibold text-[length:var(--cd-text-base)]" data-testid="lk-popup-detail-naam">{{ popupGeselecteerd.naam }}</dt>
              <dt class="text-[var(--cd-color-text-muted)]">Tegenpartij</dt><dd class="break-words">{{ popupGeselecteerd.tegenNaam || '—' }}</dd>
              <dt class="text-[var(--cd-color-text-muted)]">Datastroom</dt><dd>{{ popupGeselecteerd.richting ? typeLabel(popupGeselecteerd.richting) : '—' }}</dd>
              <dt class="text-[var(--cd-color-text-muted)]">Protocol</dt><dd>{{ popupGeselecteerd.protocol ? typeLabel(popupGeselecteerd.protocol) : '—' }}</dd>
              <dt class="text-[var(--cd-color-text-muted)]">Impact bij verbreking</dt><dd>{{ popupGeselecteerd.impact ? typeLabel(popupGeselecteerd.impact) : '—' }}</dd>
              <template v-if="popupGeselecteerd.omschrijving"><dt class="text-[var(--cd-color-text-muted)]">Omschrijving</dt><dd class="break-words">{{ popupGeselecteerd.omschrijving }}</dd></template>
            </dl>
          </div>
          <p v-else-if="popupKind === 'edge' && !popupLaden && !popupMelding" data-testid="lk-popup-md-leeg" class="mt-2 text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">Geen koppelingen gevonden.</p>
          <p v-if="popupMelding" data-testid="lk-popup-melding" class="mt-2 text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">{{ popupMelding }}</p>
          <div v-if="popupActies.length" class="mt-2 flex flex-col items-start gap-1">
            <button v-for="(a, i) in popupActies" :key="i" type="button" :data-testid="i === 0 ? 'lk-popup-actie' : `lk-popup-actie-${i}`" class="rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-primary)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)] text-white" @click="a.fn">{{ a.label }}</button>
          </div>
        </div>

        <!-- Impact-samenvatting (overlay onderaan) -->
        <p v-if="modus === 'impact'" data-testid="impact-samenvatting" class="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-white px-[var(--cd-space-md)] py-1 text-[length:var(--cd-text-sm)] font-semibold shadow-[var(--cd-shadow-md)]">{{ impactSamenvatting }}</p>

        <p v-if="laden" data-testid="lk-laden" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[var(--cd-color-text-muted)]">Landschap laden…</p>
        <p v-else-if="fout" role="alert" data-testid="lk-fout" class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[var(--cd-color-danger)]">{{ fout }}</p>
        <p v-else-if="!heeftData" data-testid="lk-leeg" class="absolute left-1/2 top-1/2 max-w-md -translate-x-1/2 -translate-y-1/2 text-center text-[var(--cd-color-text-muted)]">Nog geen landschapsdata geregistreerd.</p>
      </div>

      <!-- Rechterpaneel: actieve set + detail + legenda -->
      <aside class="flex w-56 flex-shrink-0 flex-col gap-[var(--cd-space-md)] overflow-y-auto border-l border-[var(--cd-color-border)] bg-white p-[var(--cd-space-md)]" data-testid="lk-rechts">
        <div>
          <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">Actieve set ({{ actieveSet.size }})</p>
          <ul class="flex max-h-40 flex-col gap-1 overflow-y-auto" data-testid="lk-set">
            <li v-for="n in actieveSetNodes" :key="n.id" :data-testid="`lk-set-${n.id}`" class="flex items-center gap-1 text-[length:var(--cd-text-sm)]">
              <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: lcStyle(n.lifecycle_status).bg }"></span>
              <button type="button" class="grow truncate text-left hover:underline" @click="selecteerNode(n.id)">{{ n.naam }}</button>
              <span v-if="n.blokkades_open > 0">⚠</span>
              <button type="button" class="text-[var(--cd-color-danger)]" :data-testid="`lk-set-verwijder-${n.id}`" @click="toggleSet(n.id)">×</button>
            </li>
            <li v-if="!actieveSet.size" class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">Nog niets geselecteerd.</li>
          </ul>
        </div>

        <div class="border-t border-[var(--cd-color-border)] pt-[var(--cd-space-sm)]">
          <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">Detail</p>
          <div v-if="detailNode" data-testid="lk-detail" class="flex flex-col gap-1 text-[length:var(--cd-text-sm)]">
            <p class="font-semibold" data-testid="lk-detail-naam">{{ detailNode.naam }}</p>
            <!-- LI021 — partij: aard; gebruikersgroep: ledental; anders de component-velden. -->
            <p v-if="detailNode.element_type === 'partij'" data-testid="lk-detail-aard"><span class="text-[var(--cd-color-text-muted)]">Aard:</span> {{ detailNode.soort ? typeLabel(detailNode.soort) : '—' }}</p>
            <p v-else-if="detailNode.element_type === 'gebruikersgroep'"><span class="text-[var(--cd-color-text-muted)]">Leden:</span> {{ detailNode.aantal_leden ?? 0 }}</p>
            <template v-else>
              <p><span class="text-[var(--cd-color-text-muted)]">Domein:</span> {{ detailNode.domein || '—' }}</p>
              <p><span class="text-[var(--cd-color-text-muted)]">Leverancier:</span> {{ detailNode.leverancier_naam || '—' }}</p>
              <p><span class="text-[var(--cd-color-text-muted)]">Hosting:</span> {{ detailNode.hosting_model ? typeLabel(detailNode.hosting_model) : '—' }}</p>
              <p><span class="text-[var(--cd-color-text-muted)]">Lifecycle:</span> <span class="inline-block rounded px-1" :style="{ background: lcStyle(detailNode.lifecycle_status).bg }">{{ detailNode.lifecycle_status ? typeLabel(detailNode.lifecycle_status) : '—' }}</span></p>
              <p><span class="text-[var(--cd-color-text-muted)]">Blokkades:</span> {{ detailNode.blokkades_open }}</p>
            </template>
            <p><span class="text-[var(--cd-color-text-muted)]">Koppelingen:</span> {{ detailKoppelingen }}</p>
            <!-- ADR-025 v4 — migratieplaatsing (alleen tonen indien gevuld). -->
            <p v-if="detailNode.plateau_naam" data-testid="lk-detail-plateau">
              <span class="text-[var(--cd-color-text-muted)]">Plateau:</span> {{ detailNode.plateau_naam }}<template v-if="detailNode.plateau_dispositie"> · Dispositie: {{ detailNode.plateau_dispositie }}</template>
            </p>
            <button v-if="isApplicatie(detailNode)" type="button" data-testid="lk-detail-open" class="mt-1 rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-primary)] px-[var(--cd-space-sm)] py-1 text-white" @click="openApplicatie">Open applicatie →</button>
            <button type="button" :data-testid="`lk-detail-set`" class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1" @click="toggleSet(detailNode.id)">{{ inSet(detailNode.id) ? '× Verwijder uit set' : '+ Voeg toe aan set' }}</button>
          </div>
          <p v-else class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]" data-testid="lk-detail-leeg">Klik een node voor detail.</p>
        </div>

        <div class="border-t border-[var(--cd-color-border)] pt-[var(--cd-space-sm)]" data-testid="lk-legenda">
          <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">Legenda</p>
          <div class="flex flex-col gap-1 text-[length:var(--cd-text-sm)]">
            <span v-for="lc in LIFECYCLE_OPTIES.concat(['null'])" :key="lc" class="flex items-center gap-2">
              <span class="inline-block h-3 w-3 rounded-full" :style="{ background: lcStyle(lc).bg, border: `1px solid ${lcStyle(lc).border}` }"></span>{{ lc === 'null' ? 'geen profiel' : typeLabel(lc) }}
            </span>
            <span class="flex items-center gap-2">⚠ Open blokkade(s)</span>
            <span class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">Klik een node = detail</span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
