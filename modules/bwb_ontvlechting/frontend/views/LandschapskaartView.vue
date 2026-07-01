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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from '@/composables/router'
import cytoscape from '@/composables/cytoscape'
import { api } from '@/api'
import { useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { humaniseer } from '../labels'
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
const RINGEN = ['applicaties', 'samenstelling', 'rollen', 'eigenaar', 'gebruikers', 'contracten', 'infrastructuur', 'organisatiestructuur']
// ADR-024 — context-ring "Organisatiestructuur" (persoon-met-rol → afdeling → organisatie); standaard
// UIT (zie ringAan), want context, niet de hoofdvraag van de kaart.
const RING_DEFAULT_UIT = new Set(['organisatiestructuur'])
// ADR-031 — leesbare ring-namen. Backend levert ring='beheerorganisatie' → bij laden gemapt op 'rollen'.
const RING_LABELS = {
  applicaties: 'Componenten',
  samenstelling: 'Samenstelling', // ADR-033 1b — "onderdeel van" (component↔component aggregatie)
  rollen: 'Rollen & beheer',
  eigenaar: 'Eigendom', // LI036 — "is eigendom van" (eigenaar-organisatie → component)
  gebruikers: 'Gebruikers',
  contracten: 'Contracten',
  infrastructuur: 'Infrastructuur',
  organisatiestructuur: 'Organisatiestructuur', // ADR-024 — "hoort bij" (persoon → afdeling → organisatie)
}
// LI019 1d-v2 — swimlane-lanes: definitie (label + bandkleur) + default-volgorde (van boven naar
// beneden). De volgorde is gebruiker-herschikbaar (drag-drop) en wordt in sessionStorage bewaard.
const LANE_DEF = {
  rollen: { label: 'Rollen & beheer', bg: '#fef9c3' },
  gebruikers: { label: 'Gebruikers', bg: '#f0fdf4' },
  componenten: { label: 'Componenten', bg: '#eff6ff' },
  infrastructuur: { label: 'Infrastructuur', bg: '#f0f9ff' },
  overig: { label: 'Overig', bg: '#f8fafc' },
  contracten: { label: 'Contracten', bg: '#faf5ff' },
}
const DEFAULT_LANE_VOLGORDE = ['rollen', 'gebruikers', 'componenten', 'infrastructuur', 'overig', 'contracten']
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
// Oranje van de geselecteerd-component-rand (node:selected). ADR-033 1c hergebruikt deze ene waarde
// voor de focus-rand én de impact-edges in de Impact-verkenner (één bron — geen nieuwe hexwaarde).
const SELECTIE_RAND = '#f59e0b'
// Deterministische domeinkleuren (border in "kleur op domein"-modus).
const DOMEIN_PALET = ['#2563eb', '#d97706', '#0891b2', '#7c3aed', '#16a34a', '#db2777', '#65a30d', '#dc2626']

// ── State ───────────────────────────────────────────────────────────────────────
const nodes = ref([])
const edges = ref([])
const laden = ref(true)
const fout = ref(null)

const layoutModus = ref('radiaal') // LI019 1d — 'radiaal' (concentric) | 'swimlane' (preset lanes)
const laneVolgorde = ref([...DEFAULT_LANE_VOLGORDE]) // LI019 1d-v2 — gebruiker-herschikbare lanevolgorde
const verbergLegeLanes = ref(false) // LI019 1d-v2 — lege lanes verbergen voor een compactere weergave
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
// ADR-033 — de weergavemodus is AFGELEID uit de actieve set (geen handmatige view-tabs meer):
// lege set → Geheel model; 1 component → Ego-view; ≥2 componenten → Impact-verkenner.
const modus = computed(() => {
  // Fase B — een lege set is niet langer "geheel model": leeg = beginscherm ('leeg'), tenzij de
  // bewuste "hele landschap"-actie aanstaat (dan de volledige plaat = 'geheel'). Leegte blijft op de
  // RUWE set-grootte (nooit blanken bij een niet-lege set die nog laadt).
  if (actieveSet.value.size === 0) return heleLandschap.value ? 'geheel' : 'leeg'
  // LI052 — ego vs impact op de GERESOLVEERDE leden (set-ids die de subgraaf echt als node opleverde),
  // niet de ruwe set-grootte: een niet-resolvend (spook-)id mag de modus niet spurieus naar Impact
  // tillen. Vóór de eerste fetch is nodePerId nog leeg → val terug op Ego (n<2), nooit Impact.
  let n = 0
  for (const id of actieveSet.value) if (nodePerId.value[id]) n += 1
  return n >= 2 ? 'impact' : 'ego'
})
const egoStartId = ref(null)
const detailId = ref(null)
const opbouwModus = ref(true) // geheel-model: true=insluiten (begint leeg), false=afpellen (begint vol)
const kleurOpDomein = ref(false)
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
      const eersteApp = nodes.value.find(isApplicatie)
      egoStartId.value = eersteApp ? eersteApp.id : null
      // LI053 — "Organisaties in beeld" staan standaard aan; de organisatieNodes-watch seedt dat
      // (in élke modus), zolang de gebruiker de balk niet zelf heeft aangeraakt.
      tekenVoortgang.value = null
      // Fase B — "toon hele landschap" is een verse verkennings-wortel: hef de history opnieuw op
      // (na de flush van de scope-default) zodat die default geen losse "terug"-stap wordt.
      nextTick(() => { if (gen === _laadGen && _historieKlaar) _zaaiHistorie() })
    }
  } catch (e) {
    if (gen === _laadGen) {
      fout.value = e?.message || 'Laden van de landschapskaart mislukt.'
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

// ── Organisaties in beeld (LI053) — de balk bestuurt UITSLUITEND de organisatie-overlay ──────────
// Een vinkje toont/verbergt de organisatie-node ÉN haar (per-org) gebruikersgroepen. Componenten,
// infra, contracten, personen en externe partijen vallen er NOOIT onder — die blijven altijd staan.
// Default AAN: zolang de gebruiker de balk niet zelf heeft aangeraakt, staan alle aanwezige
// organisaties aangevinkt (reactief bij elke (her)laad, in élke modus). Na de eerste toggle blijft
// de keuze staan; "Begin opnieuw" en een history-herstel zetten dat weer los/vast.
const scopeOrgs = ref(new Set())   // aangevinkte organisatie-ids
const organisatieNodes = computed(() => nodes.value.filter(_isOrg))
const _scopeAangeraakt = ref(false) // false → scope volgt automatisch "alle organisaties aan"
watch(organisatieNodes, (orgs) => {
  if (_scopeAangeraakt.value) return
  scopeOrgs.value = new Set(orgs.map((o) => o.id))
}, { immediate: true })
function toggleScopeOrg(id) {
  _scopeAangeraakt.value = true // de gebruiker bepaalt vanaf nu zelf → niet meer auto-defaulten
  const s = new Set(scopeOrgs.value)
  s.has(id) ? s.delete(id) : s.add(id)
  scopeOrgs.value = s
}
function _inScope(n) {
  // Scope bestuurt uitsluitend de organisatie-overlay — geldt IDENTIEK in Ego/Impact/Geheel.
  if (actieveSet.value.has(n.id)) return true             // set-lid (focus) → altijd zichtbaar
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

// ── Zoeken + filteren ─────────────────────────────────────────────────────────
// LI028 — `filterActief` stuurt UITSLUITEND het graafpad (zichtbareNodes). De vrije zoekterm hoort
// hier BEWUST NIET bij: die voedt alleen de resultatenlijst (`_matcht` → `gefilterdeNodes`). Anders
// zou typen de graaf-tak omschakelen (ego/impact → context-buren via _metContext; geheel → opbouw/
// afpel) en het aantal nodes veranderen zonder dat er een chip is toegevoegd.
const filterActief = computed(
  () =>
    !!(
      filterTypes.value.length ||
      filterLeveranciers.value.length ||
      filterHosting.value.length ||
      filterLifecycle.value.length
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
  return true
}
const _huidigeFilters = () => ({
  types: filterTypes.value, lev: filterLeveranciers.value, host: filterHosting.value, life: filterLifecycle.value,
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
let _filterSnap = { types: [], lev: [], host: [], life: [] }
function _commitFilterSnap() {
  _filterSnap = {
    types: [...filterTypes.value], lev: [...filterLeveranciers.value],
    host: [...filterHosting.value], life: [...filterLifecycle.value],
  }
}
watch([filterTypes, filterLeveranciers, filterHosting, filterLifecycle], () => {
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
const zichtbareNodes = computed(() => {
  // LI019 1c — de filterselects gelden in ALLE modi. LI019 1d-v4 — bij een actief filter komen de
  // context-buren (niet-flow ringen) van de gematchte componenten mee, zodat de ringen zichtbaar blijven.
  // ADR-024 scope: de organisatie-scope is een extra zeef VÓÓR de weergave (alleen application-
  // componenten; niets aangevinkt → alles). Filters/ringen/selectie werken daarbinnen ongewijzigd door.
  const alle = grafNodes.value.filter(_inScope)
  if (modus.value === 'ego') {
    if (!filterActief.value) return alle.filter((n) => egoZichtbaarIds.value.has(n.id))
    const matched = new Set(alle.filter((n) => egoZichtbaarIds.value.has(n.id) && _filterMatch(n)).map((n) => n.id))
    const zichtbaar = _metContext(matched)
    return alle.filter((n) => zichtbaar.has(n.id))
  }
  if (modus.value === 'impact') {
    // ADR-033 1c — de Impact-verkenner is nu een graaf op het canvas: de focus + hun directe
    // geraakte buren (één laag, vier relaties). De focus blijft altijd zichtbaar; een actief filter
    // verfijnt alleen de buren.
    const ids = impactZichtbaarIds.value
    if (!filterActief.value) return alle.filter((n) => ids.has(n.id))
    return alle.filter((n) => ids.has(n.id) && (huidigeFocusSet.value.has(n.id) || _filterMatch(n)))
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
})
const zichtbareNodeIds = computed(() => new Set(zichtbareNodes.value.map((n) => n.id)))
const zichtbareEdges = computed(() =>
  grafEdges.value.filter(
    // Fix 4 — ringAan filtert de edges in ALLE modi (niet meer alleen ego/geheel).
    (e) => zichtbareNodeIds.value.has(e.bron_id) && zichtbareNodeIds.value.has(e.doel_id) && ringAan.value.has(e.ring),
  ),
)

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
}
function voegAlleGefilterdeToe() {
  const s = new Set(actieveSet.value)
  for (const n of gefilterdeNodes.value) s.add(n.id)
  actieveSet.value = s
  heleLandschap.value = false
}
// Fase B slice 2b (LI023) — het beginscherm levert componenten via zijn ingangen (zoek/leverancier/
// contract/gebruikerscontext). Voeg ze toe aan de set (al-aanwezige ids stil overgeslagen → geen
// duplicaten); de set-watch haalt vervolgens de subgraaf van de bijgewerkte set op.
function voegComponentenToeAanSet(componenten) {
  const s = new Set(actieveSet.value)
  for (const c of componenten || []) if (c?.id) s.add(c.id)
  actieveSet.value = s
  heleLandschap.value = false
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
// Fase B — "Begin opnieuw" = de enige harde reset: set leeg, hele-landschap-vlag uit. De
// herfetch-watch leegt vervolgens de graaf (beginscherm-tak) → terug naar het lege beginscherm.
function wisSet() {
  actieveSet.value = new Set()
  heleLandschap.value = false
  beginschermOpen.value = true // "Begin opnieuw"/"Wis alles" = volledige reset → terug naar het beginscherm
  beginschermSleutel.value += 1 // LI052 — forceer een verse picker (buffer/vinkjes/zoekresultaten leeg)
  _scopeAangeraakt.value = false // LI053 — verse start → "Organisaties in beeld" weer default AAN
  legendaPos.value = { x: null, y: null } // LI025 — legenda terug naar standaardpositie
  detailPos.value = { x: null, y: null } // LI033 — detail-paneel terug naar standaardpositie
}
// Fase B — bewuste "toon het hele landschap"-actie: leegt de set en zet de hele-landschap-vlag,
// waarna de herfetch-watch de volledige graaf laadt (mét voortgangsteller).
function toonHeleLandschap() {
  toonStartscherm.value = false
  actieveSet.value = new Set()
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

// ── Impact-verkenner (ADR-033) — drill-down over de transitieve koppelingsketen ──────
// De basis is de actieve set; elke drill-down legt één extra focus-stap bovenop (stack).
// De verkenningsstaat wordt NIET bewaard (slice 2 bewaart later alleen de startselectie).
const drillPad = ref([]) // node-ids waar achtereenvolgens in is ingezoomd
// Vlag: een history-herstel (terug/vooruit) is bezig — onderdruk de afgeleide neven-effecten
// (drill-reset hieronder + filter-dialog + push) zodat de herstelde toestand niet wordt
// overschreven of dubbel-gepusht.
let _herstellen = false
// Vlag: de eerstvolgende (her)tekening komt uit een herstel → zonder layout-animatie tekenen,
// zodat rap terug/vooruit geen 400ms-animaties opstapelt (de hang). Geconsumeerd in tekenGraaf.
let _herstelZonderAnimatie = false
// Een wijziging van de actieve set reset de verkenning naar de basis; bij precies 1 component
// centreert de Ego-view op die component (afgeleide modus).
watch(
  () => [...actieveSet.value].sort().join('|'),
  () => {
    if (_herstellen) return // bij history-herstel blijft de herstelde drill/ego staan
    drillPad.value = []
    if (actieveSet.value.size === 1) {
      egoStartId.value = [...actieveSet.value][0]
      _recenterPending = true
    }
  },
)
const huidigeFocus = computed(() =>
  drillPad.value.length ? [drillPad.value[drillPad.value.length - 1]] : [...actieveSet.value],
)
const huidigeFocusSet = computed(() => new Set(huidigeFocus.value))
const topbalkNodes = computed(() => huidigeFocus.value.map((id) => nodePerId.value[id]).filter(Boolean))
// ADR-033 1b — impact volgt de VIER migratie-relaties (koppelt-met / draait-op / gebruikt-door /
// onderdeel-van), uitsluitend uit de expliciet geregistreerde kaart-edges (ADR-023 besluit 7).
// Contract (association), beheerrol (roltoewijzing) en datatype propageren NIET — die blijven
// louter zichtbare context in de graph en tellen niet als "geraakt bij migratie".
const IMPACT_RINGEN = new Set(['applicaties', 'infrastructuur', 'gebruikers', 'samenstelling'])
// Directe buren van een node langs de vier impact-relaties — ongericht (beide kanten), zodat
// host↔gehoste, geheel↔onderdeel en koppelt-met in beide richtingen meekomen.
function _impactBuren(id) {
  const s = new Set()
  for (const e of grafEdges.value) {
    if (!IMPACT_RINGEN.has(e.ring)) continue
    if (e.bron_id === id) s.add(e.doel_id)
    else if (e.doel_id === id) s.add(e.bron_id)
  }
  return s
}
// Directe impact: ÉÉN laag rond de huidige focus (geen transitieve BFS meer). Dieper kijken
// gebeurt door te klikken (drill-down). De focus zelf valt buiten de lijst; op naam gesorteerd.
const impactDirect = computed(() => {
  const focus = new Set(huidigeFocus.value)
  const geraakt = new Set()
  for (const id of focus) {
    for (const buur of _impactBuren(id)) {
      if (!focus.has(buur)) geraakt.add(buur)
    }
  }
  return [...geraakt]
    .map((id) => nodePerId.value[id])
    .filter(Boolean)
    .sort((a, b) => (a.naam || '').localeCompare(b.naam || '', 'nl'))
})
const impactGeraaktAantal = computed(() => impactDirect.value.length)
// ADR-033 1c — de impact-subgraaf op het canvas = de focus + hun directe geraakte buren (één laag).
const impactZichtbaarIds = computed(
  () => new Set([...huidigeFocus.value, ...impactDirect.value.map((n) => n.id)]),
)
function drillNaar(id) {
  if (!nodePerId.value[id]) return
  drillPad.value = [...drillPad.value, id]
  detailId.value = id
}
function stapTerug() {
  if (drillPad.value.length) drillPad.value = drillPad.value.slice(0, -1)
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
  if (detailNode.value) router.push({ name: 'applicatie-detail', params: { id: detailNode.value.id } })
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
    const node = cy.getElementById?.(String(sel))
    if (node && node.length) {
      node.addClass?.('hl-node')
      node.connectedEdges?.()?.addClass?.('hl-edge')
    }
  } catch { /* gemockte cytoscape in tests → no-op */ }
}
watch(geselecteerdNodeId, _pasSelectieHighlight)

// Enkelklik op een knoop: inspecteren = detail tonen + alléén z'n incidente lijnen highlighten.
// Géén hercentreren/drill (dat is dubbelklik). Werkt consistent in elke weergave.
function inspecteerNode(id) {
  geselecteerdNodeId.value = id
  openNodePopup(id) // zet detailId + toont het detail (zoals nu)
}

// ── Toestand-geschiedenis (browser-model: lineair + cursor) ─────────────────────────
// Heen-en-weer door bezochte kaarttoestanden met een cursor. Eén toestand = selectie/
// centrering (actieve set + geselecteerde/ingezoomde node + impact-drill) + ring-instellingen
// (welke ringen aan, "Groepeer per organisatie") + filters (type/leverancier/hosting/lifecycle,
// zoekterm, "Focus op actieve set"). Zoom/pan tellen NIET (puur kijkhoek → geen entry).
// De impact-drill is gewoon één toestand-entry — geen tweede terug-mechanisme. Werkgeheugen
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
    drill: [...drillPad.value], ego: egoStartId.value,
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
  drill: drillPad.value, ego: egoStartId.value,
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
  if (!arrGelijk(drillPad.value, t.drill)) drillPad.value = [...t.drill]
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
  _scopeAangeraakt.value = true // LI053 — een herstelde toestand is bewust → niet auto-terug-defaulten
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
    case 'applicatie': return { label: 'Open component →', fn: () => router.push({ name: 'applicatie-detail', params: { id } }) }
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
  // ADR-033 — deselecteren: de node-selectie + z'n incidente-lijn-highlight vervallen → alles neutraal.
  geselecteerdNodeId.value = null
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
    } else if (edge.ring === 'samenstelling') {
      // ADR-033 1b — samenstelling: bron=geheel → doel=onderdeel ("bestaat uit").
      popupTitel.value = 'Samenstelling'
      popupVelden.value = _velden([_veld('Geheel', bronNaam), _veld('Onderdeel', doelNaam)])
    } else if (edge.ring === 'organisatiestructuur') {
      // ADR-024 — hoort bij: bron (persoon/afdeling) → doel (afdeling/organisatie).
      popupTitel.value = 'Hoort bij'
      popupVelden.value = _velden([_veld('Onderdeel', bronNaam), _veld('Hoort bij', doelNaam)])
    } else if (edge.ring === 'gebruikers') {
      popupTitel.value = 'Gebruikt door'
      const gg = nodePerId.value[edge.doel_id]
      popupVelden.value = _velden([
        _veld('Component', bronNaam),
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
    legendaTypeFilter.value = null // LI025 — dieper verkennen heft de legenda-dim op (schone focus)
    // ADR-033 — DUBBELklik = dieper verkennen (uniform per nodetype):
    //  - Impact-verkenner: inzoomen op een directe buur (drill-down; "← terug" blijft);
    //  - ego/geheel: focus op deze knoop alleen → Ego-view, hercentreren (bestaand gedrag).
    if (modus.value === 'impact' && !huidigeFocusSet.value.has(id)) {
      drillNaar(id)
    } else {
      actieveSet.value = new Set([id])
      selecteerNode(id)
    }
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
// remount, dus alle state (centrum/selectie/popup/set/filters) blijft behouden. Zoom/pan
// wordt expliciet bewaard (de ResizeObserver fit niet tijdens de toggle).
let _behoudViewport = false
let _recenterPending = false // LI019 1d-v4 (bug 5) — true ná een expliciete ego-recenter (dubbelklik/set-klik)
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
// LI019 Taak 3 — element_types die géén componenttype zijn (gebruikt door het TYPE-FILTER, dat
// alleen op componenttypes werkt). NB: het type-LABEL onder de node verschijnt sinds de
// vorm-per-type-slice voor ÁLLE typen (zie `_typeRegelVoor`), dit blijft puur de filter-scoping.
const GEEN_COMPONENTTYPE = new Set(['partij', 'gebruikersgroep', 'contract'])
const _heeftTypeLabel = (n) => !!n.element_type && !GEEN_COMPONENTTYPE.has(n.element_type)

// ── Vorm per node-type (kleur blijft status) — ÉÉN gedeelde bron, gelezen door graph + swimlane ──
// Alleen native, labelvriendelijke Cytoscape-vormen; de in de praktijk dicht-bij-elkaar liggende
// paren (leverancier/contract, burger/persoon, afdeling/organisatie) krijgen een echt ander silhouet.
const _AARD_VORM = {
  persoon: 'ellipse',            // individu = ovaal
  organisatie: 'hexagon',        // organisatie-koepel
  organisatie_eenheid: 'cut-rectangle', // afdeling — duidelijk anders dan organisatie-hexagon
  externe_partij: 'rhomboid',    // leverancier — schuin blok, duidelijk anders dan contract-tag
  burger: 'pentagon',            // burger — duidelijk anders dan persoon-ovaal
}
function _vormVoorType(n) {
  if (n.element_type === 'gebruikersgroep') return 'octagon'        // groep/rol-badge
  if (n.element_type === 'contract') return 'tag'                   // label/"document"
  if (n.element_type === 'partij') return _AARD_VORM[n.soort] || 'round-rectangle'
  if (n.laag === 'technology') return 'barrel'                      // infrastructuur = cilinder
  return 'round-rectangle'                                          // component (application)
}
// Vormen die een ruimer bounding-box nodig hebben om het (tweeregelige) label te bevatten.
const _SHAPE_KLASSE = (shape) =>
  (shape === 'ellipse' || shape === 'barrel') ? 'rond'
  : (shape === 'hexagon' || shape === 'octagon' || shape === 'pentagon') ? 'veelhoek'
  : null

// Leesbare type-aanduiding (tweede labelregel) voor ÁLLE typen — naast de vorm het tekstsignaal.
const _AARD_LABEL = {
  persoon: 'Persoon', organisatie: 'Organisatie', organisatie_eenheid: 'Afdeling',
  externe_partij: 'Leverancier', burger: 'Burger',
}
function _typeRegelVoor(n) {
  if (n.element_type === 'partij') return _AARD_LABEL[n.soort] || 'Partij'
  if (n.element_type === 'gebruikersgroep') return 'Gebruikersgroep'
  if (n.element_type === 'contract') return 'Contract'
  if (n.laag === 'technology') return 'Infrastructuur'
  return typeLabel(n.element_type) // componenttype, bv. "Applicatie" / "Database"
}

// Legenda-glyphs: CSS-benaderingen van de Cytoscape-vormen (clip-path / border-radius). Neutrale
// grijze vulling — kleur blijft voorbehouden aan status; deze glyphs tonen alléén de vorm→type-uitleg.
const VORM_LEGENDA = [
  { label: 'Component', stijl: { borderRadius: '3px' } },
  { label: 'Infrastructuur', stijl: { borderRadius: '50% / 35%' } },
  { label: 'Contract', stijl: { clipPath: 'polygon(0 0,80% 0,100% 50%,80% 100%,0 100%)' } },
  { label: 'Persoon', stijl: { borderRadius: '50%' } },
  { label: 'Gebruikersgroep', stijl: { clipPath: 'polygon(30% 0,70% 0,100% 30%,100% 70%,70% 100%,30% 100%,0 70%,0 30%)' } },
  { label: 'Organisatie', stijl: { clipPath: 'polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)' } },
  { label: 'Afdeling', stijl: { clipPath: 'polygon(15% 0,85% 0,100% 15%,100% 85%,85% 100%,15% 100%,0 85%,0 15%)' } },
  { label: 'Leverancier', stijl: { clipPath: 'polygon(22% 0,100% 0,78% 100%,0 100%)' } },
  { label: 'Burger', stijl: { clipPath: 'polygon(50% 0,100% 38%,82% 100%,18% 100%,0 38%)' } },
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
  // Component = de round-rectangle-glyph: alles wat geen gg/contract/partij/technology is.
  Component: (n) => n.element_type !== 'gebruikersgroep' && n.element_type !== 'contract' && n.element_type !== 'partij' && n.laag !== 'technology',
  Infrastructuur: (n) => n.laag === 'technology',
  Contract: (n) => n.element_type === 'contract',
  Gebruikersgroep: (n) => n.element_type === 'gebruikersgroep',
  Persoon: (n) => n.element_type === 'partij' && n.soort === 'persoon',
  Organisatie: (n) => n.element_type === 'partij' && n.soort === 'organisatie',
  Afdeling: (n) => n.element_type === 'partij' && n.soort === 'organisatie_eenheid',
  Leverancier: (n) => n.element_type === 'partij' && n.soort === 'externe_partij',
  Burger: (n) => n.element_type === 'partij' && n.soort === 'burger',
}
function _legendaMatch(n, label) {
  const f = _LEGENDA_MATCH[label]
  return f ? f(n) : true
}
// Dim alle nodes die NIET bij het gekozen type horen (lk-dim). Mirror van _pasSelectieHighlight:
// optional-chaining houdt de gemockte cytoscape in tests veilig. Wordt ook na (her)tekenen
// aangeroepen (tekenGraaf) zodat de dim na een redraw behouden blijft.
function _pasLegendaDim() {
  if (!cy) return
  try {
    const type = legendaTypeFilter.value
    if (!type) { cy.nodes?.()?.removeClass?.('lk-dim'); return }
    cy.nodes?.()?.forEach?.((node) => {
      const past = _legendaMatch(node.data?.() || {}, type)
      node[past ? 'removeClass' : 'addClass']?.('lk-dim')
    })
  } catch { /* gemockte cytoscape in tests → no-op */ }
}
watch(legendaTypeFilter, _pasLegendaDim)

// LI025 — floating/draggable legenda. Standaard rechtsonder (CSS-fallback, x/y = null); slepen zet
// een absolute viewport-positie. Reset naar standaard bij "Begin opnieuw" (wisSet).
const legendaPos = ref({ x: null, y: null })
const legendaDragging = ref(false)
let _dragOffset = { x: 0, y: 0 }
function onLegendaMousedown(e) {
  if (e.target?.closest?.('button, input')) return // knoppen/inputs in de legenda werken gewoon
  // LI034 — init vanuit de werkelijke DOM-positie (anders springt het paneel bij de eerste beweging).
  if (legendaPos.value.x === null) {
    const r = e.currentTarget?.getBoundingClientRect?.()
    if (r) legendaPos.value = { x: r.left, y: r.top }
  }
  legendaDragging.value = true
  _dragOffset = { x: e.clientX - (legendaPos.value.x ?? 0), y: e.clientY - (legendaPos.value.y ?? 0) }
  e.preventDefault?.()
}
function onLegendaMousemove(e) {
  if (!legendaDragging.value) return
  legendaPos.value = { x: e.clientX - _dragOffset.x, y: e.clientY - _dragOffset.y }
}
function onLegendaMouseup() { legendaDragging.value = false }
onMounted(() => {
  document.addEventListener('mousemove', onLegendaMousemove)
  document.addEventListener('mouseup', onLegendaMouseup)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onLegendaMousemove)
  document.removeEventListener('mouseup', onLegendaMouseup)
})

// LI033 — sleepbaar detail-paneel (zelfde patroon als de legenda). null = standaard in de sidebar;
// slepen zet een absolute viewport-positie. Reset naar standaard bij "Begin opnieuw" (wisSet).
const detailPos = ref({ x: null, y: null })
const detailDragging = ref(false)
let _detailDragOffset = { x: 0, y: 0 }
function onDetailMousedown(e) {
  if (e.target?.closest?.('button, a, input')) return // knoppen/links/inputs werken gewoon
  // LI034 — initialiseer de positie vanuit de werkelijke DOM-positie als nog niet gesleept; anders
  // behandelt `?? 0` de CSS-positie als (0,0) → het paneel springt naar de hoek bij de eerste beweging.
  if (detailPos.value.x === null) {
    const r = e.currentTarget?.getBoundingClientRect?.()
    if (r) detailPos.value = { x: r.left, y: r.top }
  }
  detailDragging.value = true
  _detailDragOffset = { x: e.clientX - (detailPos.value.x ?? 0), y: e.clientY - (detailPos.value.y ?? 0) }
  e.preventDefault?.()
}
function onDetailMousemove(e) {
  if (!detailDragging.value) return
  detailPos.value = { x: e.clientX - _detailDragOffset.x, y: e.clientY - _detailDragOffset.y }
}
function onDetailMouseup() { detailDragging.value = false }
onMounted(() => {
  document.addEventListener('mousemove', onDetailMousemove)
  document.addEventListener('mouseup', onDetailMouseup)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onDetailMousemove)
  document.removeEventListener('mouseup', onDetailMouseup)
})

// LI019 1d-v5 — swimlane-indeling, afgeleid uit bestaande node-velden. Robuust voor de werkelijke
// data: ÉLK element_type dat geen partij/contract/gebruikersgroep is, is een componenttype →
// componenten (technology-laag → infrastructuur). Zo belanden application-componenten nóóit meer in
// "Overig", ook als `laag` ontbreekt of een componenttype geen application-laag-typing heeft (bug 1).
function _laneVan(n) {
  const et = n.element_type
  if (et === 'gebruikersgroep') return 'gebruikers'
  if (et === 'contract') return 'contracten'
  if (et === 'partij') return 'rollen'
  if (!et) return 'overig'
  return n.laag === 'technology' ? 'infrastructuur' : 'componenten'
}
// Aantal zichtbare nodes per lane (voor lege-lane-detectie en x-spreiding).
const _laneTelling = computed(() => {
  const c = {}
  for (const n of getekendeNodes.value) { const l = _laneVan(n); c[l] = (c[l] || 0) + 1 }
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
const laneLayout = computed(() => {
  const perLane = {}
  for (const n of getekendeNodes.value) {
    const key = _laneVan(n)
    ;(perLane[key] ||= []).push(n)
  }
  let top = 0
  return zichtbareLanes.value.map((l, index) => {
    const nodes = (perLane[l.key] || []).slice().sort((a, b) => (a.naam || '').localeCompare(b.naam || ''))
    const rows = Math.max(1, Math.ceil(nodes.length / LANE_COLS))
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
  // KLEUR = STATUS (ongewijzigd): lifecycle-tint (of GG-vast/domeinkleur). Vorm staat hier los van.
  let bg = isGG ? GG_STYLE.bg : lcStyle(n.lifecycle_status).bg
  let border = isGG
    ? GG_STYLE.border
    : kleurOpDomein.value && n.domein
      ? domeinKleur.value[n.domein]
      : lcStyle(n.lifecycle_status).border
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
  } else {
    // ADR-031 — rol-naam / 'gebruikt door' / 'valt onder' / 'draait op' uit de edge-data.
    label = e.label || ''
  }
  // LI023 — labels staan default verborgen (text-opacity:0) en verschijnen bij hover (alle modi).
  return { id: `e${i}-${e.bron_id}-${e.doel_id}-${e.relatietype}`, source: e.bron_id, target: e.doel_id, ring: e.ring, lc, w, ls, label }
}
// LI020 — definitieve node-set voor het canvas (IDENTIEK voor radiaal én swimlane — swimlane is
// enkel een andere layout, geen andere set). Een node is zichtbaar als: het ego-centrum (ego-modus),
// OF hij raakt minstens één ZICHTBARE (ring-aan) edge. Losse nodes (registratiegaps) zijn standaard
// verborgen; de toggle "Toon registratiegaps" (LI019 1d-v7) neemt ze óók mee. Dedup op id.
const getekendeNodes = computed(() => {
  const metZichtbareEdge = new Set()
  zichtbareEdges.value.forEach((e) => { metZichtbareEdge.add(e.bron_id); metZichtbareEdge.add(e.doel_id) })
  // LI027 — focus op actieve set: beperk tot de set-nodes (altijd) + hun directe buren via een zichtbare edge.
  let focusIds = null
  if (focusOpSet.value && actieveSet.value.size > 0) {
    focusIds = new Set(actieveSet.value)
    zichtbareEdges.value.forEach((e) => {
      if (actieveSet.value.has(e.bron_id)) focusIds.add(e.doel_id)
      if (actieveSet.value.has(e.doel_id)) focusIds.add(e.bron_id)
    })
  }
  const uniek = new Map()
  for (const n of zichtbareNodes.value) {
    if (uniek.has(n.id)) continue
    if (focusIds) {
      if (focusIds.has(n.id)) uniek.set(n.id, n) // focus-modus: set-nodes + directe buren
      continue
    }
    const egoCentrum = modus.value === 'ego' && n.id === egoStartId.value
    // ADR-033 1c — de impact-focus is altijd zichtbaar (ook zonder zichtbare edge), zoals het ego-centrum.
    const impactFocus = modus.value === 'impact' && huidigeFocusSet.value.has(n.id)
    // LI019 1d-v8 — in SWIMLANE valt de edge-aanwezigheidseis weg: elke node hoort in een lane, dus
    // toon álle nodes uit zichtbareNodes (de radiaal-data). De edge-filter is enkel voor radiaal
    // (losse nodes zweven daar rond). `toonRegistratiegaps` doet dit ook in radiaal.
    if (layoutModus.value === 'swimlane' || toonRegistratiegaps.value || egoCentrum || impactFocus || metZichtbareEdge.has(n.id)) uniek.set(n.id, n)
  }
  return [...uniek.values()]
})

// LI019 1d-v2 — geen compound-parents meer: lanes zijn een HTML-overlay (zie laneBanden/bandPx),
// niet langer cytoscape-nodes. Daardoor renderen edges tussen lanes weer normaal (correctie 3).
function _elementen() {
  const zn = getekendeNodes.value
  const znIds = new Set(zn.map((n) => n.id))
  const ze = zichtbareEdges.value.filter((e) => znIds.has(e.bron_id) && znIds.has(e.doel_id))
  return [
    ...zn.map((n) => { const d = _nodeData(n); return { data: d, classes: _SHAPE_KLASSE(d.shape) || undefined } }),
    ...ze.map((e, i) => ({ data: _edgeData(e, i) })),
  ]
}
const zichtbaarAantal = computed(() => getekendeNodes.value.length)

// LI019 1d (Taak 4) — ná de layout(-animatie): bij radiaal-Ego centreren op het centrum-component,
// anders fit op het geheel. Wordt als layout-`stop`-callback gebruikt voor élke layout, zodat een
// wijziging (filter/ring/selectie/view/layout) automatisch herpositioneert + centreert. Raakt geen
// reactieve state aan → geen layout-her-trigger-loop. Respecteert de fullscreen-viewport-behoud-vlag.
function _naLayout() {
  if (!cy || _behoudViewport) return
  // LI019 1d-v4 (bug 5) — centreer alléén op het ego-centrum ná een expliciete recenter (dubbelklik/
  // set-klik); bij elke andere wijziging (m.n. een filter die de node-set verandert) → fit op het
  // geheel, zodat de zichtbare nodes altijd in beeld komen.
  if (_recenterPending && layoutModus.value === 'radiaal' && modus.value === 'ego' && egoStartId.value) {
    _recenterPending = false
    const c = cy.getElementById?.(String(egoStartId.value))
    if (c && c.length) { cy.center?.(c); updateBands(); return }
  }
  _recenterPending = false // recenter-verzoek geconsumeerd (bv. in swimlane waar niet gecentreerd wordt)
  cy.fit?.(undefined, 50)
  updateBands()
}
// LI019 1d-v6 — swimlane-posities: nodes in een GRID per lane (LANE_COLS kolommen, wrappend over
// meerdere rijen), gecentreerd per rij. Begrensde breedte → geen extreme uitzoom (kernoorzaak B).
// Object-map {nodeId:{x,y}} (Cytoscape lookt id zelf op).
function _swimlanePositions() {
  const pos = {}
  for (const lane of laneLayout.value) {
    const { nodes, top } = lane
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
  if (!cy || layoutModus.value !== 'swimlane') { bandPx.value = []; return }
  const zoom = cy.zoom?.() || 1
  const pan = cy.pan?.() || { x: 0, y: 0 }
  bandPx.value = laneBanden.value.map((b) => ({ top: b.top * zoom + pan.y, height: b.height * zoom }))
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
function _layout(geenAnimatie = false, vorigePosities = null) {
  // `geenAnimatie` (bij history-herstel): teken direct, zonder de 400ms-animatie — voorkomt dat
  // snel terug/vooruit animaties opstapelt. De stop-callback (_naLayout) kadert daarna één keer.
  const anim = geenAnimatie ? { animate: false } : { animate: true, animationDuration: 400 }
  // LI019 1d (Taak 2) — Swimlanes: custom preset-posities per lane (0 nieuwe dependencies).
  // `positions` als object-map {nodeId: {x,y}} (Cytoscape doet de id-lookup zelf) — géén callback
  // met `node.id` (= de id-METHODE, niet de string). animate:false + fit:true geeft een direct,
  // correct geplaatst raster; de stop-callback fit + sync't de overlay als vangrail.
  if (layoutModus.value === 'swimlane') {
    return { name: 'preset', positions: _swimlanePositions(), animate: false, fit: true, padding: 60, stop: _naLayout }
  }
  // LI032 — positie-stabiele re-render: al-geplaatste nodes blijven op hun vorige plek; alléén
  // nieuwe nodes krijgen een positie. Voorkomt dat de hele graaf herschikt bij het toevoegen van
  // één component. Geldt voor de radiale modi (swimlane heeft eigen preset). Bij de eerste/verse
  // render (geen vorige posities) valt het terug op de normale modus-layout hieronder.
  if (vorigePosities && vorigePosities.size) {
    const gefixeerd = []
    cy.nodes().forEach((n) => {
      const p = vorigePosities.get(n.id())
      if (p) gefixeerd.push({ nodeId: n.id(), position: p })
    })
    const totaal = cy.nodes().length
    if (totaal > 0 && gefixeerd.length === totaal) {
      // Niets structureel nieuws → behoud de posities exact (geen reshuffle bij b.v. ring-toggle).
      const positions = {}
      gefixeerd.forEach((g) => { positions[g.nodeId] = g.position })
      return { name: 'preset', positions, animate: false, fit: false, stop: _naLayout }
    }
    if (gefixeerd.length > 0) {
      // Mix oud+nieuw → fcose plaatst de nieuwe nodes; de bestaande blijven gefixeerd op hun plek.
      return {
        name: 'fcose', quality: 'proof', randomize: false, idealEdgeLength: 120, nodeRepulsion: 8000,
        fixedNodeConstraint: gefixeerd, ...anim, stop: _naLayout,
      }
    }
  }
  // LI019 1d (Taak 3) — Radiaal/Ego: concentric met het geselecteerde component centraal.
  if (modus.value === 'ego') {
    return {
      name: 'concentric', concentric: (n) => (n.id() === egoStartId.value ? 10 : 5), levelWidth: () => 1,
      minNodeSpacing: 80, spacingFactor: 1.5, padding: 60, ...anim, stop: _naLayout,
    }
  }
  // ADR-033 1c / LI030 — Impact-verkenner: fcose (force-directed) minimaliseert kruisende lijnen.
  // De set-nodes (ankerpunten) worden op een vaste, gespreide positie gefixeerd → prominent en
  // stabiel; de context-nodes ordenen zich eromheen. Deterministisch (randomize:false) → consistente
  // plaatsing. `cy.add()` is al gedraaid (tekenGraaf), dus getElementById vindt de getekende set.
  if (modus.value === 'impact') {
    const fixedNodeConstraint = [...actieveSet.value]
      .filter((id) => cy.getElementById(id).length)
      .map((id, i) => ({ nodeId: id, position: { x: i * 220, y: 0 } }))
    return {
      name: 'fcose', quality: 'proof', randomize: false,
      idealEdgeLength: 120, nodeRepulsion: 8000,
      fixedNodeConstraint, padding: 60, ...anim, stop: _naLayout,
    }
  }
  // LI019 1d (Taak 3) — Radiaal/Geheel+Impact: concentric op koppelingsdichtheid (meer koppelingen
  // → dichter bij het centrum).
  return {
    name: 'concentric', concentric: (n) => n.degree(false), levelWidth: () => 2,
    minNodeSpacing: 80, spacingFactor: 1.5, padding: 50, ...anim, stop: _naLayout,
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
  // LI032 — leg de huidige node-posities vast vóór de remove (na remove zijn ze weg), zodat de
  // her-layout bestaande nodes op hun plek kan fixeren en alleen nieuwe nodes herplaatst.
  const vorigePosities = new Map()
  cy.nodes().forEach((n) => vorigePosities.set(n.id(), { ...n.position() }))
  cy.elements().remove()
  cy.add(_elementen())
  cy.layout(_layout(_geenAnim, vorigePosities)).run()
  // Klein delay voor de browser-layout-flush, dán her-meten + passend maken.
  setTimeout(() => {
    cy?.resize?.()
    cy?.fit?.(undefined, 50)
    updateBands()
    _pasSelectieHighlight() // ADR-033 — na een (her)tekening de selectie-highlight opnieuw aanbrengen
    _pasLegendaDim() // LI025 — en de legenda-dim (nieuwe node-objecten dragen de klasse nog niet)
  }, 100)
}

const CY_STYLE = [
  {
    selector: 'node',
    style: {
      'background-color': 'data(bg)', 'border-color': 'data(border)', 'border-width': 2,
      label: 'data(label)', 'font-size': 11, color: 'data(txt)', 'text-valign': 'center', 'text-halign': 'center',
      // Vorm-per-type-slice — elk type heeft nu een tweeregelig label (naam + type): wrap aan,
      // hoogte volgt het label, ruime padding zodat de type-regel onder de naam past.
      width: 'label', height: 'label', shape: 'data(shape)', 'text-wrap': 'wrap', 'text-max-width': 150,
      'padding-left': 12, 'padding-right': 12, 'padding-top': 6, 'padding-bottom': 6,
    },
  },
  // Ronde vormen (ellipse/barrel) clippen het label aan de randen → ruimere padding.
  { selector: 'node.rond', style: { 'padding-left': 18, 'padding-right': 18, 'padding-top': 12, 'padding-bottom': 12 } },
  // Veelhoeken (hexagon/octagon/pentagon) knijpen het label aan de hoeken → ruimere padding.
  { selector: 'node.veelhoek', style: { 'padding-left': 16, 'padding-right': 16, 'padding-top': 12, 'padding-bottom': 12 } },
  {
    selector: 'edge',
    style: {
      width: 'data(w)', 'line-color': 'data(lc)', 'line-style': 'data(ls)',
      'target-arrow-shape': 'triangle', 'target-arrow-color': 'data(lc)', 'curve-style': 'bezier',
      // Koppelingsdetail-label (flow-edges): protocol + richting.
      label: 'data(label)', 'font-size': 8, color: 'var(--lk-color-text-muted)', 'text-wrap': 'none',
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
  { selector: 'node.lk-dim', style: { opacity: 0.35 } },
  // Fix 3: visuele markering van de geselecteerde node (klik op set-item / node).
  { selector: 'node:selected', style: { 'border-width': 4, 'border-color': SELECTIE_RAND, 'border-style': 'solid' } },
]

let resizeObserver = null

// LI022 — kaart-UI-state bewaren over navigatie heen (sessionStorage; transient UI-state, geen Pinia).
const _LK_STATE_KEY = 'lk-state'
function _bewaarKaartState() {
  try {
    sessionStorage.setItem(_LK_STATE_KEY, JSON.stringify({
      // ADR-033 — de modus is afgeleid; bewaar de ACTIEVE SET zodat het beeld (geheel/ego/impact)
      // behouden blijft bij terugnavigatie. De oude `modus`-sleutel is vervallen (geen dode sleutel).
      actieveSet: [...actieveSet.value],
      // LI019 swimlane-parkeren — layoutModus niet meer bewaard (altijd 'radiaal').
      laneVolgorde: laneVolgorde.value,
      verbergLegeLanes: verbergLegeLanes.value,
      toonRegistratiegaps: toonRegistratiegaps.value,
      egoStartId: egoStartId.value,
      ringAan: [...ringAan.value],
      groepeerPerOrg: groepeerPerOrg.value,
    }))
  } catch { /* sessionStorage niet beschikbaar — negeren */ }
}
function _herstelKaartState() {
  let s = null
  try { s = JSON.parse(sessionStorage.getItem(_LK_STATE_KEY) || 'null') } catch { s = null }
  if (!s) return
  // ADR-033 — herstel de actieve set (de modus volgt eruit). Fase B: de graaf is bij mount nog niet
  // geladen (set-gestuurd) → herstel de set as-is; de daaropvolgende `herlaadGraaf` haalt de subgraaf
  // van die set op.
  if (Array.isArray(s.actieveSet) && s.actieveSet.length) actieveSet.value = new Set(s.actieveSet)
  // LI019 swimlane-parkeren — layoutModus NIET meer herstellen: altijd 'radiaal' (de enige actieve layout).
  // Lanevolgorde herstellen mits een geldige permutatie van de bekende lanes (anders default).
  if (Array.isArray(s.laneVolgorde)) {
    const geldig = s.laneVolgorde.filter((k) => LANE_DEF[k])
    if (DEFAULT_LANE_VOLGORDE.every((k) => geldig.includes(k))) laneVolgorde.value = geldig
  }
  if (typeof s.verbergLegeLanes === 'boolean') verbergLegeLanes.value = s.verbergLegeLanes
  if (typeof s.toonRegistratiegaps === 'boolean') toonRegistratiegaps.value = s.toonRegistratiegaps
  if (Array.isArray(s.ringAan)) ringAan.value = new Set(s.ringAan.filter((r) => RINGEN.includes(r)))
  if (typeof s.groepeerPerOrg === 'boolean') groepeerPerOrg.value = s.groepeerPerOrg
  // egoStartId herstellen (de subgraaf-fetch laadt die node mee als hij nog bestaat).
  if (s.egoStartId) egoStartId.value = s.egoStartId
}
onBeforeRouteLeave(_bewaarKaartState)

onMounted(async () => {
  // Fase B — geen onvoorwaardelijke full-graph-laad meer: eerst catalogus + views, dán de set/staat
  // bepalen, dán pas de bijbehorende graaf laden (lege set → beginscherm, niets laden).
  // LI019 1b — componenttype-catalogus voor het type-filter (faalt zacht: leeg → niets te kiezen).
  try {
    typeCatalogus.value = (await api.componenten.opties())?.componenttype || []
  } catch {
    typeCatalogus.value = []
  }
  // ADR-033 slice 2c — opgeslagen views laden (faalt zacht). Voedt de views-lijst + het startscherm.
  await laadViews()
  // ADR-033 — deep-link ?center=<applicatie-id> (vanuit het applicatie-detail): de component
  // wordt als enige in de actieve set gezet → Ego-view (afgeleide modus), centraal op de kaart.
  // De oude ?modus-param is vervallen (de modus volgt voortaan de actieve set) en wordt genegeerd.
  const qCenter = route.query?.center ? String(route.query.center) : null
  if (qCenter) {
    // Expliciete deep-link heeft voorrang op bewaarde state.
    actieveSet.value = new Set([qCenter])
    egoStartId.value = qCenter
    detailId.value = qCenter
    // ADR-025 — "Bekijk op kaart": het beginscherm overslaan en direct de ego-view tonen.
    beginschermOpen.value = false
  } else {
    _herstelKaartState()
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
    cy.on('tap', 'node', (evt) => onNodeTap(evt.target.id()))
    // LI019 1d-v2 — houd de swimlane-band-overlay synchroon met pan/zoom/resize.
    cy.on('pan zoom resize', updateBands)
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
    // LI023 — edge-labels verschijnen bij hover (en blijven zichtbaar bij een geselecteerde edge).
    cy.on('mouseover', 'edge', (evt) => evt.target.style('text-opacity', 1))
    cy.on('mouseout', 'edge', (evt) => { if (!evt.target.hasClass('sel-edge')) evt.target.style('text-opacity', 0) })
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

defineExpose({ openNodePopup, openEdgePopup, selecteerFlow, onNodeTap, sluitPopup, toggleFullscreen, fullscreen, popupOpen, _edgeData, groepeerPerOrg, grafNodes, grafEdges, zichtbareNodes, zichtbareEdges, layoutModus, _laneVan, _swimlanePositions, _layout, laneVolgorde, verbergLegeLanes, laneBanden, getekendeNodes, _herschikLane, toonRegistratiegaps, setLayoutModus, modus, actieveSet, toggleSet, kiesComponent, drillPad, drillNaar, stapTerug, huidigeFocus, huidigeFocusSet, topbalkNodes, impactDirect, impactGeraaktAantal, impactZichtbaarIds, _nodeData, geselecteerdNodeId, _edgeGehighlight, inspecteerNode, historie, cursor, kanTerug, kanVooruit, terugInHistorie, vooruitInHistorie, _vormVoorType, legendaOpen, toggleLegenda, scopeOrgs, organisatieNodes, toggleScopeOrg, _inScope, opgeslagenViews, magViewsBeheren, toonStartscherm, openView, openOpslaan, openBewerk, bewaarView, verwijderView, beginMetHeleKaart, viewDialogOpen, viewNaam, viewGedeeld, laadViews, heleLandschap, beginscherm, beginschermOpen, tekenVoortgang, toonHeleLandschap, herlaadGraaf, wisSet, voegComponentenToeAanSet, actieveSetNodes, componentBuren, voegBurenToe, voegContextComponentenToe, geselecteerdNodeBuren, detailNode, _relayoutTeller, legendaTypeFilter, toggleLegendaFilter, _legendaMatch, legendaPos, legendaDragging, onLegendaMousedown, onLegendaMousemove, onLegendaMouseup, detailPos, detailDragging, onDetailMousedown, onDetailMousemove, onDetailMouseup })

// LI023 — generieke re-layout: herpositioneer zodra de WERKELIJK GETEKENDE node-samenstelling
// wijzigt. De id-compositie van `getekendeNodes` vangt álle oorzaken (scope/ring/zoekfilter/nieuwe
// subgraaf) ÉN de gevallen die alleen `getekendeNodes` raken maar niet `zichtbareNodes` — m.n.
// "Focus op actieve set" (`focusOpSet`), die de vorige zichtbareNodes-watch miste. Daarnaast
// hertekenen bij wijzigingen die de node-id-set níét veranderen maar wél een redraw vergen:
// edges (ring-toggle die enkel edges raakt), layout-modus, kleur-op-domein, swimlane-opties.
// Gedebounced (250ms) → snelle opeenvolgende wijzigingen leiden tot één relayout (geen flikker,
// geen dubbele layout). De initiële layout blijft de directe `tekenGraaf()` in onMounted/herlaadGraaf.
function _debounce(fn, ms) {
  let t
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms) }
}
function _hertekenNu() {
  if (!_mountKlaar || !cy) return // niet vóór de eerste render / vóór cy bestaat
  _relayoutTeller.value++
  tekenGraaf()
}
const _hertekenGedebounced = _debounce(_hertekenNu, 250)
watch(
  [
    () => getekendeNodes.value.map((n) => n.id).join('|'), // de werkelijk getekende node-set
    zichtbareEdges, modus, layoutModus, kleurOpDomein, groepeerPerOrg, verbergLegeLanes, laneVolgorde, toonRegistratiegaps,
  ],
  () => {
    // History-herstel (terug/vooruit) relayout't DIRECT — zonder debounce — zodat tekenGraaf de
    // `_herstelZonderAnimatie`-vlag synchroon consumeert (de hang-fix). Overige wijzigingen
    // gedebounced (250ms) → snelle opeenvolgende changes coalesceren tot één relayout.
    if (_herstellen) _hertekenNu()
    else _hertekenGedebounced()
  },
  { deep: false },
)

function setLayoutModus(m) {
  layoutModus.value = m // de teken-watch herpositioneert + centreert (Taak 4)
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
    :class="['flex w-full flex-col', fullscreen ? 'fixed inset-0 z-[400] bg-[var(--lk-color-bg)]' : '']"
    data-testid="lk-wrapper"
    :style="fullscreen ? 'height: 100vh' : 'height: calc(100vh - 9rem)'"
  >
    <!-- ADR-033 — Topbar: de weergave is AFGELEID uit de actieve set (geen handmatige tabs).
         Deze indicator toont alleen wélke weergave nu actief is; kiezen doe je via selecteren. -->
    <div class="flex items-center gap-[var(--lk-space-sm)] border-b border-[var(--lk-color-border)] bg-white p-[var(--lk-space-sm)]">
      <p data-testid="lk-weergave-indicator" class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] font-semibold text-white">
        {{ modus === 'geheel' ? 'Geheel model' : modus === 'ego' ? 'Ego-view' : modus === 'impact' ? 'Impact-verkenner' : 'Beginscherm' }}
      </p>
      <span class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Weergave volgt je selectie</span>
      <!-- Fase B — "Begin opnieuw": enige harde reset → terug naar het lege beginscherm. -->
      <!-- LI052 — altijd zichtbaar/bruikbaar (ook op het beginscherm: daar idempotent) → gegarandeerd verse start. -->
      <button type="button" data-testid="lk-begin-opnieuw" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)]" @click="wisSet">Begin opnieuw</button>
      <span class="ml-auto text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="lk-zichtbaar-aantal">{{ zichtbaarAantal }} in beeld</span>
    </div>

    <!-- Fase B slice 2b (LI023) — "in beeld"-chips: één chip per component in de set (≥1), zichtbaar
         buiten het beginscherm (ego/impact). Tweede set-bewerkingsplek naast de context-routes;
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

        <input v-model="zoekterm" type="search" data-testid="lk-zoek" placeholder="🔍 Zoek naam/domein/leverancier…" class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)]" />

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
            class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
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
          <span class="font-semibold">Lifecycle</span>
          <ZoekMultiSelect
            v-model="filterLifecycle"
            :zoek-functie="zoekLifecycle"
            :weergave="(o) => o.label"
            id-veld="sleutel"
            :chip-label="(v) => typeLabel(v)"
            :vaste-optie="{ sleutel: ZONDER, label: 'Zonder lifecycle' }"
            placeholder="Zoek lifecycle…"
            testid="lk-filter-lifecycle"
          />
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

        <!-- LI019 1d-v7 — registratiegaps: standaard toont de kaart (radiaal én swimlane) dezelfde
             node-set (edge-rakend). Aan = óók losse nodes zonder relatie (registratiegaps). -->
        <label class="mt-[var(--lk-space-sm)] flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input type="checkbox" v-model="toonRegistratiegaps" data-testid="lk-registratiegaps" />Toon registratiegaps
        </label>
        <!-- LI019 1d-v3 — swimlane-optie: lege lanes verbergen. De lanevolgorde wijzig je nu door de
             lane-header op het canvas te verslepen (geen zijbalk-lijst meer). -->
        <label v-if="layoutModus === 'swimlane'" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input type="checkbox" v-model="verbergLegeLanes" data-testid="lk-verberg-lege" />Verberg lege lanes
        </label>

      </aside>

      <!-- Midden: "Organisaties in beeld"-balk bovenin + het kaart-canvas eronder. -->
      <div class="flex min-h-0 min-w-0 flex-1 flex-col">
        <!-- LI053 — de balk bestuurt UITSLUITEND de organisatie-overlay: een vinkje toont/verbergt de
             organisatie-node + haar gebruikersgroepen. Componenten worden nooit geraakt. Default alle
             aan. Geldt identiek in Ego/Impact/Geheel. -->
        <div
          v-if="organisatieNodes.length"
          data-testid="lk-scopebalk" role="group" aria-label="Organisaties in beeld"
          class="flex flex-wrap items-center gap-x-[var(--lk-space-md)] gap-y-1 border-b border-[var(--lk-color-border)] bg-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)]"
        >
          <span class="text-[length:var(--lk-text-sm)] font-semibold">Organisaties in beeld:</span>
          <label v-for="o in organisatieNodes" :key="o.id" class="flex items-center gap-1 text-[length:var(--lk-text-sm)]">
            <input type="checkbox" :checked="scopeOrgs.has(o.id)" :data-testid="`lk-scope-org-${o.id}`" @change="toggleScopeOrg(o.id)" />{{ o.naam }}
          </label>
        </div>

      <!-- Canvas — min-h-0 is kritiek: zonder negeert een flex-child de height:100% van de parent,
           waardoor Cytoscape op hoogte 0 initialiseert en de graaf leeg/onzichtbaar blijft. -->
      <div class="relative min-h-0 min-w-0 flex-1 bg-[var(--lk-color-surface)]">
        <!-- LI019 1d-v4 — swimlane-banden in TWEE HTML-lagen ROND het canvas (geen compound-nodes,
             zodat Cytoscape uitsluitend gewone nodes + edges bevat — edges en node-clicks werken
             normaal). (1) band-ACHTERGRONDEN onder het canvas (z-0, niet-interactief, translucent). -->
        <div v-if="layoutModus === 'swimlane'" class="pointer-events-none absolute inset-0 z-0 overflow-hidden" data-testid="lk-lanes" aria-hidden="true">
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
             ringen, filters). De impact-drill loopt via dezelfde geschiedenis — geen aparte drill-terug.
             "← Terug naar Landschapskaart" (de kaart verlaten) is een andere actie en blijft elders. -->
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
            <!-- Kleur = status -->
            <div data-testid="lk-legenda-status" class="mt-[var(--lk-space-sm)] flex flex-col gap-1 border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]">
              <p class="text-[length:var(--lk-text-xs)] font-semibold text-[var(--lk-color-text-muted)]">Kleur = status</p>
              <span v-for="lc in LIFECYCLE_OPTIES.concat(['null'])" :key="lc" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
                <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: lcStyle(lc).bg, border: `1px solid ${lcStyle(lc).border}` }"></span>{{ lc === 'null' ? 'geen profiel' : typeLabel(lc) }}
              </span>
              <span class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">⚠ Open blokkade(s)</span>
            </div>
          </div>
        </div>

        <!-- (2) lane-HEADERS BOVEN het canvas (z-[5]). De container is pointer-events-none → node-
             clicks gaan ongehinderd naar het canvas; alleen de header-span vangt pointer-events af
             (versleepbaar). De lege-lane-tekst zit ook hier zodat ze leesbaar boven het canvas staat. -->
        <div v-if="layoutModus === 'swimlane'" class="pointer-events-none absolute inset-0 z-[5] overflow-hidden" data-testid="lk-lane-headers">
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
          <!-- LI019 1d — layout-wisselaar: Radiaal (concentric) ↔ Swimlanes (lane-banden).
               LI019 swimlane-parkeren — UI verborgen (v-if="false"); Radiaal is de enige actieve layout.
               De swimlane-logica blijft in de code voor een toekomstige herwrite. -->
          <div v-if="false" class="flex gap-0.5 rounded-[var(--lk-radius-btn)] bg-white/90 p-0.5 shadow-[var(--lk-shadow-sm)]" data-testid="lk-layout-toggle">
            <button type="button" data-testid="lk-layout-radiaal" :aria-pressed="layoutModus === 'radiaal'" :class="['rounded-[var(--lk-radius-btn)] px-2 py-1 text-[length:var(--lk-text-sm)]', layoutModus === 'radiaal' ? 'bg-[var(--lk-color-primary)] text-white' : '']" @click="setLayoutModus('radiaal')">Radiaal</button>
            <button type="button" data-testid="lk-layout-swimlane" :aria-pressed="layoutModus === 'swimlane'" :class="['rounded-[var(--lk-radius-btn)] px-2 py-1 text-[length:var(--lk-text-sm)]', layoutModus === 'swimlane' ? 'bg-[var(--lk-color-primary)] text-white' : '']" @click="setLayoutModus('swimlane')">Swimlanes</button>
          </div>
          <button type="button" data-testid="lk-centreer" class="rounded-[var(--lk-radius-btn)] bg-white/90 px-2 py-1 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)]" @click="centreer">⊡ Centreer</button>
          <button type="button" data-testid="lk-kleur-domein" :aria-pressed="kleurOpDomein" :class="['rounded-[var(--lk-radius-btn)] px-2 py-1 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)]', kleurOpDomein ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-white/90']" @click="kleurOpDomein = !kleurOpDomein">Kleur op domein</button>
          <!-- Fullscreen-overlay (in-app): één toggle — vergroten ingebed, verkleinen in de overlay. -->
          <button type="button" :data-testid="fullscreen ? 'lk-fullscreen-sluit' : 'lk-fullscreen-open'" :aria-pressed="fullscreen" class="rounded-[var(--lk-radius-btn)] bg-white/90 px-2 py-1 text-[length:var(--lk-text-sm)] shadow-[var(--lk-shadow-sm)]" @click="toggleFullscreen">{{ fullscreen ? '✕ Verkleinen' : '⛶ Vergroten' }}</button>
        </div>

        <!-- Klik-detail-popup (koppeling of knoop) — gedeelde vorm; sluiten via knop, Escape
             of een tap op leeg canvas. Een nieuwe klik vervangt de inhoud. -->
        <div
          v-if="popupOpen"
          data-testid="lk-popup"
          role="dialog"
          aria-label="Detail"
          :class="['absolute left-3 top-3 z-20 max-w-[90%] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-white p-[var(--lk-space-md)] shadow-[var(--lk-shadow-lg)]', popupKind === 'edge' ? 'w-[34rem]' : 'w-72']"
        >
          <div class="flex items-start justify-between gap-2">
            <div>
              <p v-if="popupBadge" data-testid="lk-popup-badge" class="text-[length:var(--lk-text-xs)] font-semibold uppercase text-[var(--lk-color-primary-700)]">{{ popupBadge }}</p>
              <p class="font-semibold" data-testid="lk-popup-titel">{{ popupTitel }}</p>
            </div>
            <button type="button" data-testid="lk-popup-sluit" aria-label="Sluiten" class="shrink-0 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-text)]" @click="sluitPopup">✕</button>
          </div>
          <p v-if="popupLaden" data-testid="lk-popup-laden" class="mt-2 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Laden…</p>
          <dl v-if="popupVelden.length" data-testid="lk-popup-velden" class="mt-2 grid grid-cols-[auto_1fr] gap-x-[var(--lk-space-sm)] gap-y-0.5 text-[length:var(--lk-text-sm)]">
            <template v-for="v in popupVelden" :key="v.label">
              <dt class="text-[var(--lk-color-text-muted)]">{{ v.label }}</dt>
              <dd class="break-words">{{ v.waarde }}</dd>
            </template>
          </dl>
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
          <p v-else-if="popupKind === 'edge' && !popupLaden && !popupMelding" data-testid="lk-popup-md-leeg" class="mt-2 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Geen koppelingen gevonden.</p>
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
          <div
            v-if="detailNode"
            data-testid="lk-detail"
            :style="detailPos.x !== null ? { position: 'fixed', left: detailPos.x + 'px', top: detailPos.y + 'px', zIndex: 30 } : {}"
            :class="['flex flex-col gap-1 text-[length:var(--lk-text-sm)]', detailPos.x !== null ? 'w-56 rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-white p-[var(--lk-space-sm)] shadow-[var(--lk-shadow-lg)]' : '', detailDragging ? 'cursor-grabbing' : 'cursor-grab']"
            @mousedown="onDetailMousedown"
          >
            <p class="font-semibold" data-testid="lk-detail-naam">{{ detailNode.naam }}</p>
            <!-- LI021 — partij: aard; gebruikersgroep: ledental; anders de component-velden. -->
            <p v-if="detailNode.element_type === 'partij'" data-testid="lk-detail-aard"><span class="text-[var(--lk-color-text-muted)]">Aard:</span> {{ detailNode.soort ? typeLabel(detailNode.soort) : '—' }}</p>
            <p v-else-if="detailNode.element_type === 'gebruikersgroep'"><span class="text-[var(--lk-color-text-muted)]">Leden:</span> {{ detailNode.aantal_leden ?? 0 }}</p>
            <template v-else>
              <p><span class="text-[var(--lk-color-text-muted)]">Domein:</span> {{ detailNode.domein || '—' }}</p>
              <p><span class="text-[var(--lk-color-text-muted)]">Leverancier:</span> {{ detailNode.leverancier_naam || '—' }}</p>
              <p><span class="text-[var(--lk-color-text-muted)]">Hosting:</span> {{ detailNode.hosting_model ? typeLabel(detailNode.hosting_model) : '—' }}</p>
              <p><span class="text-[var(--lk-color-text-muted)]">Lifecycle:</span> <span class="inline-block rounded px-1" :style="{ background: lcStyle(detailNode.lifecycle_status).bg }">{{ detailNode.lifecycle_status ? typeLabel(detailNode.lifecycle_status) : '—' }}</span></p>
              <p><span class="text-[var(--lk-color-text-muted)]">Blokkades:</span> {{ detailNode.blokkades_open }}</p>
            </template>
            <p><span class="text-[var(--lk-color-text-muted)]">Koppelingen:</span> {{ detailKoppelingen }}</p>
            <!-- ADR-025 v4 — migratieplaatsing (alleen tonen indien gevuld). -->
            <p v-if="detailNode.plateau_naam" data-testid="lk-detail-plateau">
              <span class="text-[var(--lk-color-text-muted)]">Plateau:</span> {{ detailNode.plateau_naam }}<template v-if="detailNode.plateau_dispositie"> · Dispositie: {{ detailNode.plateau_dispositie }}</template>
            </p>
            <button v-if="isApplicatie(detailNode)" type="button" data-testid="lk-detail-open" class="mt-1 rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-sm)] py-1 text-white" @click="openApplicatie">Open component →</button>
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
            class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1"
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
        <button type="button" data-testid="lk-startscherm-hele-kaart" class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-2 text-white" @click="beginMetHeleKaart">Begin met de hele kaart →</button>
      </div>
    </div>
  </div>
</template>
