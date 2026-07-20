<script setup>
/**
 * ProcesDiagram — proces-only structuurbeeld (LI038 gate 1).
 *
 * Toont ALLEEN processen en hoe ze onder elkaar hangen — géén componenten, géén vervullers.
 * De component is bewust api-vrij: de volledige processet komt als prop van het processen-
 * scherm (één bron, geen tweede fetch), zoeken filtert client-side (zoekveld-norm) en de
 * focus-selectie (centrum + ouderketen boven + subboom beneden + zusjes opzij) komt uit de
 * gedeelde pure module `procesFocusSet` (procesBoom.js — één boom-definitie).
 *
 * Rendering volgt het kaart-preset-recept (ADR-040 render-eigenaar + LI036 meet-stap):
 * één opbouw → preset-layout op `procesBoomLayout`-posities → fit/centrering in de
 * stop-callback. Verbindingslijnen = uitsluitend echte `ouder_id`-relaties (geen stam tussen
 * losse wortels — de layout scheidt bomen per kolomgroep); een latere proces→proces-flowlaag
 * (spoor 2) kan als tweede edge-soort naast deze hiërarchie-edges aanhaken zonder herbouw.
 * De "geen ondersteunend systeem"-cue (subboom-semantiek) komt als `gapIds`-prop van de
 * ouder mee — dezelfde afleiding als de tree-view/kaart, geen tweede bron.
 *
 * ADR-043 blok 2 — STRUCTUUR-GENERIEK gemaakt (LI039-feitenrapport: props al vorm-generiek;
 * alleen de huid was proces-gebonden). Het beeld werkt op élke genestelde structuur met
 * platte `{id, naam, ouder_id}`-rijen; de proces-huid is de DEFAULT zodat het processen-
 * scherm ongewijzigd blijft (geen tweede kopie — de bouwsteen-kernles LI038):
 * - `items` = de generieke rijen-prop (valt terug op de historische `processen`-prop);
 *   rijen met `ouder_ids` (ADR-044, meervoudige plaatsingen) tekenen een lijn per ouder
 *   en de popup benoemt het meervoud; rijen met enkelvoudig `ouder_id` blijven identiek;
 * - `teksten` = de schermtaal (zoektitel/placeholder/leeg/wortel/landschap/detail/cue);
 * - `gapIds` = generieke RUSTIGE-CUE-set (dashed rand + popup-badge; het label komt uit
 *   `teksten.gap` — processen: "geen ondersteunend systeem", functies: vervallen-markering);
 * - `detailRoute` (null = geen detail-uitgang) + `metKaartUitgang` (functies: geen kaart);
 * - slot `popup-extra` voor scherm-eigen popup-inhoud (bv. definitie + herkomst).
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { Button } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import cytoscape from '@/composables/cytoscape'
import { useSleepbaar } from '@/composables/useSleepbaar'
import { procesBoomLayout, procesFocusSet, procesSubboomSet } from '../procesBoom'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({
  // Historische prop-naam (processen-scherm); nieuwe consumenten gebruiken `items`.
  processen: { type: Array, default: () => [] },
  // De volledige set (platte rijen mét ouder_id) — generieke naam; wint van `processen`.
  items: { type: Array, default: null },
  // Set van ids met de GAP-cue ("hier ontbreekt iets" — gestippelde rand + popup-badge,
  // label = teksten.gap), of null zolang de afleiding nog laadt — zelfde bron als de
  // tree-view-cue. De gestippelde rand is en blijft de taal van de gap-familie.
  gapIds: { type: Object, default: null },
  // LI039 blok C — Set van ids met de VERVALLEN-markering ("bestaat niet meer in het
  // referentiemodel"): een EIGEN kanaal naast gapIds, want beide toestanden kunnen
  // tegelijk gelden en moeten uit elkaar te houden blijven. Taal: solid rand in de
  // warning-kleur (knoop) + ⚠-badge (popup, label = teksten.vervallen).
  // Combinaties: gap = gestippeld gedempt · vervallen = solid warning · beide =
  // gestippeld in de warning-kleur.
  vervallenIds: { type: Object, default: null },
  // LI038 gate 3 — "Toon in procesbeeld" (Boom-rij-actie): open NEUTRAAL met dit item als
  // centrum (oranje, focus-beeld — géén inperking; dat is het dubbelklik-gebaar).
  initieelCentrumId: { type: String, default: null },
  // Scherm-taal (proces-defaults; zie _TEKSTEN) — consumenten overschrijven per sleutel.
  teksten: { type: Object, default: () => ({}) },
  // Detail-uitgang in de popup (named route met :id); null = geen detail-link.
  detailRoute: { type: String, default: 'proces-detail' },
  // LI039 UI-afronding v3 — generieke open-uitgang ZONDER route: label voor een
  // `openItem`-emit (bv. "Open functie →" → terug naar de Boom-rij). De POPUP ZELF
  // bestaat op grond van de INHOUD (v-if op het item) — uitgangen zijn optioneel en
  // hun afwezigheid mag de popup nooit laten wegvallen (regressie-geborgd).
  openLabel: { type: String, default: null },
  // Kaart-uitgang in de popup (proces-only handoff); functies hebben er geen.
  metKaartUitgang: { type: Boolean, default: true },
  // Root-testid (tests van beide consumenten blijven onderscheidbaar).
  testid: { type: String, default: 'proces-diagram' },
})

const _TEKSTEN = {
  zoekTitel: 'Zoek een proces',
  zoekPlaceholder: 'Zoek proces…',
  leeg: 'Zoek een proces om te beginnen.',
  wortel: 'Hoofdproces',
  landschap: 'Toon hele processenlandschap',
  detailLink: 'Open proces →',
  gap: 'geen ondersteunend component',
  vervallen: 'vervallen in het referentiemodel',
}
const T = computed(() => ({ ..._TEKSTEN, ...props.teksten }))
// De generieke rijen-bron: `items` wint; `processen` blijft de back-compat-naam.
const _rijen = computed(() => props.items ?? props.processen)
// LI038 gate 2 — de kaart-doorschakeling (handoff-bouwer = api-werk) leeft in de OUDER
// (ProcesLijst, spiegel van ProcesDetail.bekijkOpKaart); dit beeld blijft zelf api-vrij.
// Gate 3 — `centrumGewijzigd` houdt de ouder bij welk proces centraal staat, zodat een
// Boom↔Diagram-schakelwissel het laatste centrum behoudt (het gate-1-punt, nu gesloten).
const emit = defineEmits(['bekijkOpKaart', 'centrumGewijzigd', 'openItem'])

const auth = useAuthStore()
// Zelfde affordance-gating als de "Bekijk op kaart"-knop op ProcesDetail (backend handhaaft).
const magKaartZien = computed(() => auth.hasRole('viewer', 'medewerker', 'beheerder', 'auditor'))

// Spreiding van het boom-raster (roomier dan de kaart-proceszone: dit beeld staat op zichzelf).
const NODE_W = 210
const NODE_H = 110
// Concrete hexen mét token-spiegel: cytoscape resolvet geen CSS-custom-properties (LI037-patroon).
const SELECTIE_RAND = '#f59e0b' // = --lk-color-selectie ("kijk hier" — kaart/diagram/aanstip)
const KLEUR_RAND = '#94a3b8' // ~ --lk-color-text-muted (rustige knoop-/lijnrand)
const KLEUR_TEKST = '#1e293b' // ~ --lk-color-text
const KLEUR_VLAK = '#ffffff' // ~ --lk-color-surface
const KLEUR_WARNING = '#ba7517' // = --lk-color-warning (vervallen-markering, LI039 blok C)

const centrumId = ref(null)

const _byId = computed(() => new Map(_rijen.value.map((p) => [p.id, p])))
const naamVan = (id) => _byId.value.get(id)?.naam || String(id)
const alleIds = computed(() => new Set(_rijen.value.map((p) => p.id)))
// ADR-044 — meervoudige ouders: rijen met `ouder_ids` (bedrijfsfuncties: álle plaatsingen)
// leveren een edge per ouder; rijen met enkelvoudig `ouder_id` (processen) blijven exact
// zoals ze waren. De layout hangt de knoop onder zijn eerste ouder (de structuur-guard),
// maar ÁLLE plaatsings-lijnen worden getekend — het meervoud is zichtbaar in het beeld.
const _oudersLijst = (p) => (Array.isArray(p.ouder_ids) ? p.ouder_ids : (p.ouder_id ? [p.ouder_id] : []))
const hierEdges = computed(() =>
  _rijen.value.flatMap((p) => _oudersLijst(p).map((o) => ({ bron: p.id, doel: o }))))

// LI038 gate 2 — "Toon hele processenlandschap": de uitzoom-tegenhanger BINNEN dit beeld
// (alle bomen naast elkaar, nog steeds strikt proces-only). Een nieuwe proces-keuze zet het
// beeld terug op de focus rond dat centrum.
const heleLandschap = ref(false)
// LI038 gate 3 — dubbelklik-inzoom: gevoerd op PROCES-ids (subboom-scope), nooit op
// vervullers/componenten. null = geen inperking (focus- of hele-landschap-beeld).
const inzoomId = ref(null)

// De zichtbare set: het hele proceslandschap (alle bomen), de inzoom-scope (proces + subboom),
// of de focus rond het centrum. Leeg zolang er geen (bestaand) centrum gekozen is — het beeld
// opent leeg ("Zoek een proces om te beginnen."). Verdwijnt het centrum (bv. verwijderd in de
// Boom), dan valt de set vanzelf terug naar leeg (de afleidingen geven een lege set).
const zichtbareIds = computed(() => {
  if (heleLandschap.value) return new Set(alleIds.value)
  if (inzoomId.value) return procesSubboomSet(inzoomId.value, alleIds.value, hierEdges.value, naamVan)
  return procesFocusSet(centrumId.value, alleIds.value, hierEdges.value, naamVan)
})
// Alleen echte ouder→kind-relaties bínnen de focus-set worden getekend.
const zichtbareEdges = computed(() =>
  hierEdges.value.filter((e) => zichtbareIds.value.has(e.bron) && zichtbareIds.value.has(e.doel)))

// ── Zoeken (client-side over de al-geladen set; zoekveld-norm: partieel + hoofdletter-
// ongevoelig; identiteit "naam — ouder" zoals de proces-pickers elders) ──────────────────────
async function zoekProcessen(params = {}) {
  const term = (params.zoek || '').trim().toLowerCase()
  const items = _rijen.value
    .filter((p) => !term || p.naam.toLowerCase().includes(term))
    .map((p) => ({ ...p, ouder_naam: (p.ouder_id && _byId.value.get(p.ouder_id)?.naam) || null }))
    .sort((a, b) => a.naam.localeCompare(b.naam, 'nl'))
  return { items, volgende_cursor: null }
}
const procesWeergave = (p) => (p?.ouder_naam ? `${p.naam} — ${p.ouder_naam}` : (p?.naam ?? ''))
function kiesCentrum(item) {
  if (!item?.id) return
  centrumId.value = item.id
  heleLandschap.value = false // een nieuwe keuze zet het beeld terug op de focus
  inzoomId.value = null // gate 3 — een verse keuze heft een eerdere dubbelklik-inzoom op
  geselecteerdId.value = item.id // het gekozen proces draagt de oranje "kijk hier"-markering
  popupId.value = null // kiezen = navigeren, niet inspecteren — de popup hoort bij een klik
  _resetPopupPos() // nieuwe proceskeuze = verse context → popup terug op de standaardplek
  _pasSelectie() // ongewijzigde set (zelfde centrum opnieuw) hertekent niet → direct bijwerken
  emit('centrumGewijzigd', item.id)
}

// ── LI038 gate 2 — enkele klik = kijken: selectie + rustige popup ────────────────────────────
// De klik perkt niets in en wisselt geen weergave; dubbelklik-inzoom is gate 3.
const geselecteerdId = ref(null) // draagt de oranje selectie (knoop + aanliggende lijnen)
const popupId = ref(null) // de popup hoort bij een klik; null = dicht
const popupProces = computed(() => (popupId.value ? _byId.value.get(popupId.value) || null : null))
// Ouder-map over de volledige set (voor de plek-in-woorden; onafhankelijk van de focus-zeef).
// Bij meervoudige ouders (ADR-044) draagt de keten de EERSTE ouder — dezelfde die de
// structuur/layout gebruikt; het meervoud zelf wordt apart benoemd (popupOuders hieronder).
const _ouderVan = computed(() => {
  const m = new Map()
  for (const p of _rijen.value) {
    const ouders = _oudersLijst(p)
    if (ouders.length) m.set(p.id, ouders[0])
  }
  return m
})
// ADR-044 — álle directe ouders van de popup-knoop (gelijkwaardig, geen rangorde). Bij
// meervoud benoemt de popup dat expliciet ("staat onder X en Y") i.p.v. één keten.
const popupOuders = computed(() => {
  if (!popupId.value) return []
  const p = _byId.value.get(popupId.value)
  if (!p) return []
  return _oudersLijst(p).map((id) => _byId.value.get(id)).filter(Boolean)
})
// De ouderketen van de popup, van de wortel naar de directe ouder (visited-guard: nooit hangen).
const popupPad = computed(() => {
  if (!popupId.value) return []
  const keten = []
  const bezocht = new Set([popupId.value])
  let cur = _ouderVan.value.get(popupId.value)
  while (cur != null && !bezocht.has(cur)) {
    bezocht.add(cur)
    const p = _byId.value.get(cur)
    if (!p) break
    keten.unshift(p)
    cur = _ouderVan.value.get(cur)
  }
  return keten
})
const popupGap = computed(() => !!(popupId.value && props.gapIds?.has?.(popupId.value)))
// LI039 blok C — vervallen is een eigen feit naast de gap; beide badges kunnen samen staan.
const popupVervallen = computed(() => !!(popupId.value && props.vervallenIds?.has?.(popupId.value)))

// LI038 gate 2 v2 — versleepbare popup via de gedeelde `useSleepbaar`-bouwsteen (zelfde gedrag
// als de kaart-legenda/-popup: hele paneel is de greep, knoppen/links uitgezonderd; positie-init
// uit de DOM bij de eerste drag; null = de CSS-standaardplek rechtsboven). De positie reset
// wanneer de context leegt (popup sluit / nieuwe proceskeuze) — geen onthouden drift.
const {
  pos: popupPos, dragging: popupSleept,
  onMousedown: onPopupSleep, reset: _resetPopupPos,
} = useSleepbaar()

function selecteer(id) {
  if (!id || !_byId.value.has(id)) return
  geselecteerdId.value = id
  popupId.value = id
  _pasSelectie()
}
function sluitPopup() {
  popupId.value = null
  geselecteerdId.value = null // klik-naast: popup dicht én selectie weg
  _resetPopupPos() // popup dicht = terug naar de standaardplek
  _pasSelectie()
}
function toonHeleLandschap() {
  heleLandschap.value = true // verbreedt de blik BINNEN dit beeld — popup/selectie blijven
  inzoomId.value = null // uitzoomen heft de dubbelklik-inperking op
}

// ── LI038 gate 3 — dubbelklik = navigeren (inzoom op proces-ids) + history ───────────────────
// Dubbelklik-onderscheiding naar het kaart-_DBLTAP-patroon (zelfde drempel), maar de ENKELE
// klik handelt hier DIRECT af (popup zonder uitstel — gate-3-eis): de eerste tap van een
// dubbelklik toont dus heel even de popup, de tweede tap binnen de drempel zet 'm om in de
// inzoom. Bewuste omkering van de kaart-afweging (daar won geen-flikker; hier wint direct).
let _tapId = null
let _tapTijd = 0
const _DBLTAP_MS = 280
function onNodeTap(id) {
  const nu = Date.now()
  if (_tapId === id && nu - _tapTijd < _DBLTAP_MS) {
    _tapId = null
    zoomInOp(id)
    return
  }
  _tapId = id
  _tapTijd = nu
  selecteer(id) // enkele klik = kijken — direct (geen uitgestelde popup)
}
// De inzoom zelf: proces + volledige subboom als scope (procesSubboomSet — het proces-only
// pad; NOOIT het vervuller-/subgraaf-pad, dat bij 0 vervullers weigert). Werkt dus óók op een
// blad zonder kinderen én zonder vervullers: de scope is dan alleen het proces zelf.
function zoomInOp(id) {
  if (!id || !_byId.value.has(id)) return
  centrumId.value = id // het ingezoomde proces is het nieuwe centrum
  inzoomId.value = id
  heleLandschap.value = false
  geselecteerdId.value = id // oranje "kijk hier" op het nieuwe centrum
  popupId.value = null // navigeren, niet inspecteren
  _resetPopupPos()
  _pasSelectie()
  emit('centrumGewijzigd', id)
}

// Toestand-geschiedenis (browser-model: snapshot + cursor — het veld-agnostische kaart-patroon,
// hier gevoerd op de beeld-velden van dit diagram). Eén gebaar = één staat: de sig-watch vuurt
// per flush, dus de meervoudige mutaties van kiesCentrum/zoomInOp landen als één entry. De
// popup is momentaan en reist bewust NIET mee.
const historie = shallowRef([])
const cursor = ref(-1)
const _HIST_MAX = 50
let _historieKlaar = false
let _herstellen = false
const kanTerug = computed(() => cursor.value > 0)
function _maakToestand() {
  return {
    centrum: centrumId.value, inzoom: inzoomId.value,
    hele: heleLandschap.value, sel: geselecteerdId.value,
  }
}
const _toestandSig = computed(() => JSON.stringify(_maakToestand()))
watch(_toestandSig, () => {
  if (!_historieKlaar || _herstellen) return
  // Browser-model: een wijziging vanaf een teruggehaalde toestand knipt de vooruit-tak af.
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
  // Alleen toewijzen wat écht verandert (kaart-les: gelijkblijvende toestand = nul hertekening).
  if (centrumId.value !== t.centrum) {
    centrumId.value = t.centrum
    emit('centrumGewijzigd', t.centrum)
  }
  if (inzoomId.value !== t.inzoom) inzoomId.value = t.inzoom
  if (heleLandschap.value !== t.hele) heleLandschap.value = t.hele
  if (geselecteerdId.value !== t.sel) geselecteerdId.value = t.sel
  popupId.value = null // momentaan — een herstelde staat opent geen popup
  _pasSelectie() // sel kan wijzigen zonder hertekening (zelfde set) → direct bijwerken
  nextTick(() => { _herstellen = false })
}
function terugInHistorie() {
  if (!kanTerug.value) return
  cursor.value -= 1
  _herstelToestand(historie.value[cursor.value])
}

// ── Cytoscape (kaart-recept: composable-wrapper, min-h-vangrail, render-eigenaar) ────────────
const containerRef = ref(null)
let cy = null
let resizeObserver = null

const CY_STYLE = [
  {
    selector: 'node',
    style: {
      'background-color': KLEUR_VLAK, 'border-color': KLEUR_RAND, 'border-width': 2,
      shape: 'round-rectangle', // zelfde proces-silhouet als de kaart (vorm = type)
      label: 'data(label)', 'font-size': 14, color: KLEUR_TEKST,
      'text-valign': 'center', 'text-halign': 'center',
      width: 'label', height: 'label', 'text-wrap': 'wrap', 'text-max-width': 180,
      'padding-left': 16, 'padding-right': 16, 'padding-top': 10, 'padding-bottom': 10,
    },
  },
  // GAP-cue — zelfde rustige eerlijkheids-cue-taal als kaart/lijst (gestreepte rand,
  // geen alarmkleur); de selectie-regel hieronder wint (solid).
  { selector: 'node[?procesGap]', style: { 'border-style': 'dashed', 'border-width': 3 } },
  // VERVALLEN-markering (LI039 blok C) — eigen kanaal, eigen taal: solid rand in de
  // warning-kleur. NA de gap-regel: draagt een knoop beide toestanden, dan combineren
  // ze tot "gestippeld in de warning-kleur" (gap levert de streep, vervallen de kleur).
  { selector: 'node[?vervallenCue]', style: { 'border-color': KLEUR_WARNING, 'border-width': 3 } },
  // Hiërarchie-lijnen: rustig, geen pijl/label — hoogte codeert de diepte al.
  { selector: 'edge', style: { width: 1.5, 'line-color': KLEUR_RAND, 'curve-style': 'straight' } },
  // De selectie draagt de bestaande oranje "kijk hier"-taal: knoop + aanliggende lijnen
  // (zelfde kleurbron en klassen als de Landschapskaart).
  { selector: 'node.hl-node', style: { 'border-width': 3, 'border-color': SELECTIE_RAND, 'border-style': 'solid' } },
  { selector: 'edge.hl-edge', style: { 'line-color': SELECTIE_RAND, width: 2.5, 'z-index': 900 } },
]

// Selectie-highlight als runtime-klassen (nooit via relayout): de geselecteerde knoop + zijn
// aanliggende hiërarchie-lijnen. Ook aangeroepen vanuit de layout-stop (hertekening).
function _pasSelectie() {
  if (!cy) return
  cy.nodes?.()?.removeClass?.('hl-node')
  cy.edges?.()?.removeClass?.('hl-edge')
  if (!geselecteerdId.value) return
  const n = cy.getElementById?.(geselecteerdId.value)
  if (n?.length) {
    n.addClass?.('hl-node')
    n.connectedEdges?.()?.addClass?.('hl-edge')
  }
}

function _elementen() {
  const nodes = [...zichtbareIds.value].map((id) => ({
    data: {
      id, label: naamVan(id),
      // undefined (niet false) als de cue niet geldt: de CY-selectors `node[?…]` matchen
      // dan niet (zelfde conventie als de kaart-node-data). Twee ONAFHANKELIJKE kanalen.
      procesGap: props.gapIds?.has?.(id) ? true : undefined,
      vervallenCue: props.vervallenIds?.has?.(id) ? true : undefined,
    },
  }))
  const edges = zichtbareEdges.value.map((e, i) => ({
    data: { id: `h${i}`, source: e.bron, target: e.doel },
  }))
  return [...nodes, ...edges]
}

// Post-layout werk hoort in de stop-callback (ADR-040): her-meting + fit + selectie-markering.
function _naLayout() {
  cy?.resize?.()
  cy?.fit?.(undefined, 50)
  _pasSelectie()
}

function _layoutOpties() {
  // Meet-stap vóór de eerste frame (LI036 — de preset-layout meet zelf niets; zonder deze
  // stap heeft de eerste frame geen edge-endpointgeometrie en tekent hij géén lijnen).
  const ns = cy?.nodes?.()
  ns?.updateStyle?.()
  ns?.forEach?.((n) => n.layoutDimensions?.({ nodeDimensionsIncludeLabels: true }))
  const boom = procesBoomLayout(zichtbareIds.value, zichtbareEdges.value, naamVan)
  const positions = {}
  for (const id of zichtbareIds.value) {
    positions[id] = { x: (boom.kolom.get(id) ?? 0) * NODE_W, y: (boom.rij.get(id) ?? 0) * NODE_H }
  }
  return { name: 'preset', positions, animate: false, fit: true, padding: 60, stop: _naLayout }
}

async function tekenGraaf() {
  await nextTick(); await nextTick() // tweede tick voor Vite-HMR-randgevallen (kaart-recept)
  const el = containerRef.value
  if (!el || !cy) return
  if (el.offsetHeight === 0) { el.style.minHeight = '500px'; await nextTick() }
  cy.elements().remove()
  if (!zichtbareIds.value.size) return
  cy.add(_elementen())
  cy.layout(_layoutOpties()).run()
}

onMounted(async () => {
  cy = cytoscape({ container: containerRef.value, elements: [], style: CY_STYLE, maxZoom: 1.6 })
  // LI038 gate 2/3 — enkele klik = kijken (direct: selectie + popup), dubbelklik = navigeren
  // (inzoom); klik naast een knoop sluit. De onderscheiding zit in onNodeTap.
  cy.on?.('tap', 'node', (evt) => onNodeTap(evt?.target?.id?.()))
  cy.on?.('tap', (evt) => { if (evt?.target === cy) sluitPopup() })
  if (typeof ResizeObserver !== 'undefined') {
    // Maatwissel = resize + fit op de bestaande posities — nooit een re-layout (LI036-regel).
    resizeObserver = new ResizeObserver(() => { cy?.resize?.(); cy?.fit?.(undefined, 50) })
    resizeObserver.observe(containerRef.value)
  }
  // Gate 3 — "Toon in procesbeeld": neutraal openen op het meegegeven proces (focus, geen
  // inperking), VÓÓR het history-zaad zodat deze ingang-staat de wortel van de geschiedenis is.
  if (props.initieelCentrumId) kiesCentrum({ id: props.initieelCentrumId })
  await tekenGraaf()
  _zaaiHistorie()
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  cy?.destroy?.()
  cy = null
})

// Eén render-eigenaar: elke wijziging van de focus-set of van een cue-set hertekent via
// hetzelfde pad (gap en vervallen zijn onafhankelijke kanalen).
watch([zichtbareIds, () => props.gapIds, () => props.vervallenIds], () => { tekenGraaf() })

defineExpose({
  kiesCentrum, centrumId, zichtbareIds,
  // gate 2 — klik/popup/uitzoom (testbaar zonder echte cytoscape-events)
  selecteer, sluitPopup, toonHeleLandschap, geselecteerdId, popupId, heleLandschap,
  // gate 2 v2 — versleepbare popup (gedeelde useSleepbaar-bouwsteen)
  popupPos, popupSleept, onPopupSleep,
  // gate 3 — dubbelklik-inzoom (proces-ids) + history
  onNodeTap, zoomInOp, inzoomId, kanTerug, terugInHistorie, historie, cursor,
})
</script>

<template>
  <div :data-testid="props.testid" class="flex flex-col gap-[var(--lk-space-md)]">
    <div
      class="flex flex-wrap items-end gap-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]"
    >
      <label class="flex w-72 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">{{ T.zoekTitel }}</span>
        <ZoekSelect
          :zoek-functie="zoekProcessen"
          :weergave="procesWeergave"
          id-veld="id"
          :placeholder="T.zoekPlaceholder"
          testid="diagram-zoek"
          @keuze="kiesCentrum"
        />
      </label>
      <!-- LI038 gate 3 — "← Terug" door de beeld-geschiedenis (kaart-history-taal): zichtbaar
           zodra er een vorige stand is; dé terugweg uit een dubbelklik-inzoom. -->
      <button
        v-if="kanTerug"
        type="button"
        data-testid="diagram-terug"
        class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-1 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
        @click="terugInHistorie"
      >← Terug</button>
    </div>

    <div class="relative">
      <div
        ref="containerRef"
        data-testid="diagram-canvas"
        class="w-full rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] shadow-[var(--lk-shadow-sm)]"
        style="min-height: 500px; height: 65vh;"
      ></div>
      <p
        v-if="!zichtbareIds.size"
        data-testid="diagram-leeg"
        class="pointer-events-none absolute inset-0 flex items-center justify-center text-[var(--lk-color-text-muted)]"
      >
        {{ T.leeg }}
      </p>

      <!-- LI038 gate 2 (v2) — rustige, VERSLEEPBARE klik-popup (gedeelde useSleepbaar-bouwsteen,
           zelfde overlay-taal als de kaart: standaard rechtsboven, hele paneel = greep behalve
           knoppen/links, gesleept = viewport-positie): naam + plek in woorden + eerlijke gap-cue,
           met drie visueel gescheiden uitgangen. Strikt proces-only: geen componenten hier. -->
      <div
        v-if="popupProces"
        data-testid="diagram-popup"
        :style="popupPos.x !== null ? { position: 'fixed', left: popupPos.x + 'px', top: popupPos.y + 'px' } : {}"
        :class="[
          popupPos.x !== null ? 'z-30' : 'absolute right-3 top-3 z-10',
          popupSleept ? 'cursor-grabbing' : 'cursor-grab',
          'w-80 rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-md)]',
        ]"
        @mousedown="onPopupSleep"
      >
        <div class="flex items-start gap-[var(--lk-space-xs)]">
          <h2 class="font-semibold text-[var(--lk-color-primary)]" data-testid="diagram-popup-naam">{{ popupProces.naam }}</h2>
          <button
            type="button"
            aria-label="Sluit details"
            data-testid="diagram-popup-sluit"
            class="ml-auto leading-none text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            @click="sluitPopup"
          >×</button>
        </div>
        <!-- Plek in woorden. ADR-044 — bij MEERDERE plekken benoemt de popup het meervoud
             expliciet ("staat onder X en Y", alle gelijkwaardig, elk klikbaar); bij één
             plek de vertrouwde ouderketen van wortel naar directe ouder (elk klikbaar —
             dezelfde enkelklik-semantiek als op de kaartknoop). -->
        <p v-if="popupOuders.length > 1" data-testid="diagram-popup-plek" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          staat onder
          <template v-for="(v, i) in popupOuders" :key="v.id">
            <span v-if="i">{{ i === popupOuders.length - 1 ? ' en ' : ', ' }}</span>
            <button
              type="button"
              class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
              :data-testid="`diagram-popup-pad-${v.id}`"
              @click="selecteer(v.id)"
            >{{ v.naam }}</button>
          </template>
        </p>
        <p v-else-if="popupPad.length" data-testid="diagram-popup-plek" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          onder
          <template v-for="(v, i) in popupPad" :key="v.id">
            <span v-if="i"> › </span>
            <button
              type="button"
              class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
              :data-testid="`diagram-popup-pad-${v.id}`"
              @click="selecteer(v.id)"
            >{{ v.naam }}</button>
          </template>
        </p>
        <p v-else data-testid="diagram-popup-plek" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">{{ T.wortel }}</p>
        <!-- Eerlijke rustige cue — zelfde cue-taal als kaart/lijst (gelezen uit de gedeelde
             gapIds-afleiding, niet herafgeleid; het label komt uit de scherm-taal). -->
        <span
          v-if="popupGap"
          data-testid="diagram-popup-gap"
          class="mt-2 inline-block rounded-[var(--lk-radius-badge)] border border-dashed border-[var(--lk-color-border)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
        >{{ T.gap }}</span>
        <!-- Vervallen-markering (LI039 blok C) — eigen taal (warning, ⚠ + tekst; solid rand),
             naast en onderscheidbaar van de gestippelde gap-badge hierboven. De vorm laat de
             gate-2-telling ("— N applicaties hangen er nog aan") in de tekst passen. -->
        <span
          v-if="popupVervallen"
          data-testid="diagram-popup-vervallen"
          class="mt-2 flex items-start gap-1 rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-warning)] bg-[color-mix(in_srgb,var(--lk-color-warning)_12%,transparent)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-warning)]"
        ><span aria-hidden="true">⚠</span><span>{{ T.vervallen }}</span></span>
        <!-- Scherm-eigen popup-inhoud (ADR-043 blok 2: bv. definitie + herkomstvermelding). -->
        <slot name="popup-extra" :item="popupProces" />
        <!-- Uitgangen, visueel gescheiden: verbreden BINNEN dit beeld (knop) vs. de
             vertrek-navigaties (kaart = component-wereld; detailscherm) onder een deellijn. -->
        <div class="mt-[var(--lk-space-md)] flex flex-col gap-[var(--lk-space-sm)]">
          <Button
            :label="T.landschap"
            severity="secondary"
            data-testid="diagram-popup-landschap"
            :disabled="heleLandschap"
            @click="toonHeleLandschap"
          />
          <div
            v-if="(metKaartUitgang && magKaartZien) || detailRoute || openLabel"
            class="flex flex-col gap-[var(--lk-space-xs)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]"
          >
            <Button
              v-if="metKaartUitgang && magKaartZien"
              label="Bekijk op de kaart →"
              severity="secondary"
              data-testid="diagram-popup-kaart"
              @click="emit('bekijkOpKaart', popupProces)"
            />
            <router-link
              v-if="detailRoute"
              :to="{ name: detailRoute, params: { id: popupProces.id } }"
              data-testid="diagram-popup-open"
              class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >{{ T.detailLink }}</router-link>
            <!-- Route-loze open-uitgang (LI039 v3): de consument bepaalt de landing
                 (bv. terug naar de Boom-rij) via de openItem-emit. -->
            <button
              v-else-if="openLabel"
              type="button"
              data-testid="diagram-popup-open"
              class="text-left text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
              @click="emit('openItem', popupProces)"
            >{{ openLabel }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
