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
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { Button } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import cytoscape from '@/composables/cytoscape'
import { useSleepbaar } from '@/composables/useSleepbaar'
import { procesBoomLayout, procesFocusSet, procesSubboomSet } from '../procesBoom'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({
  // De volledige processet (platte rijen mét ouder_id) — geleverd door ProcesLijst.
  processen: { type: Array, required: true },
  // Set van proces-ids waarvan de héle subboom geen ondersteuning draagt (of null zolang de
  // afleiding nog laadt) — zelfde bron als de tree-view-cue.
  gapIds: { type: Object, default: null },
  // LI038 gate 3 — "Toon in procesbeeld" (Boom-rij-actie): open NEUTRAAL met dit proces als
  // centrum (oranje, focus-beeld — géén inperking; dat is het dubbelklik-gebaar).
  initieelCentrumId: { type: String, default: null },
})
// LI038 gate 2 — de kaart-doorschakeling (handoff-bouwer = api-werk) leeft in de OUDER
// (ProcesLijst, spiegel van ProcesDetail.bekijkOpKaart); dit beeld blijft zelf api-vrij.
// Gate 3 — `centrumGewijzigd` houdt de ouder bij welk proces centraal staat, zodat een
// Boom↔Diagram-schakelwissel het laatste centrum behoudt (het gate-1-punt, nu gesloten).
const emit = defineEmits(['bekijkOpKaart', 'centrumGewijzigd'])

const auth = useAuthStore()
// Zelfde affordance-gating als de "Bekijk op kaart"-knop op ProcesDetail (backend handhaaft).
const magKaartZien = computed(() => auth.hasRole('viewer', 'medewerker', 'beheerder', 'auditor'))

// Spreiding van het boom-raster (roomier dan de kaart-proceszone: dit beeld staat op zichzelf).
const NODE_W = 210
const NODE_H = 110
// Concrete hexen mét token-spiegel: cytoscape resolvet geen CSS-custom-properties (LI037-patroon).
const SELECTIE_RAND = '#f59e0b' // zelfde oranje als de Landschapskaart-selectie ("kijk hier")
const KLEUR_RAND = '#94a3b8' // ~ --lk-color-text-muted (rustige knoop-/lijnrand)
const KLEUR_TEKST = '#1e293b' // ~ --lk-color-text
const KLEUR_VLAK = '#ffffff' // ~ --lk-color-surface

const centrumId = ref(null)

const _byId = computed(() => new Map(props.processen.map((p) => [p.id, p])))
const naamVan = (id) => _byId.value.get(id)?.naam || String(id)
const alleIds = computed(() => new Set(props.processen.map((p) => p.id)))
const hierEdges = computed(() =>
  props.processen.filter((p) => p.ouder_id).map((p) => ({ bron: p.id, doel: p.ouder_id })))

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
  const items = props.processen
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
const _ouderVan = computed(() => {
  const m = new Map()
  for (const p of props.processen) if (p.ouder_id) m.set(p.id, p.ouder_id)
  return m
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
  // "Geen ondersteunend systeem" — zelfde rustige eerlijkheids-cue-taal als kaart/lijst
  // (gestreepte rand, geen alarmkleur); de selectie-regel hieronder wint (solid).
  { selector: 'node[?procesGap]', style: { 'border-style': 'dashed', 'border-width': 3 } },
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
      // undefined (niet false) als er geen gat is: de CY-selector `node[?procesGap]` matcht
      // dan niet (zelfde conventie als de kaart-node-data).
      procesGap: props.gapIds?.has?.(id) ? true : undefined,
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

// Eén render-eigenaar: elke wijziging van de focus-set of de gap-cue hertekent via hetzelfde pad.
watch([zichtbareIds, () => props.gapIds], () => { tekenGraaf() })

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
  <div data-testid="proces-diagram" class="flex flex-col gap-[var(--lk-space-md)]">
    <div
      class="flex flex-wrap items-end gap-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]"
    >
      <label class="flex w-72 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Zoek een proces</span>
        <ZoekSelect
          :zoek-functie="zoekProcessen"
          :weergave="procesWeergave"
          id-veld="id"
          placeholder="Zoek proces…"
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
        Zoek een proces om te beginnen.
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
        <!-- Plek in woorden: de ouderketen van wortel naar directe ouder, elk klikbaar
             (klik = die knoop inspecteren — dezelfde enkelklik-semantiek als op de kaartknoop). -->
        <p v-if="popupPad.length" data-testid="diagram-popup-plek" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
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
        <p v-else data-testid="diagram-popup-plek" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Hoofdproces</p>
        <!-- Eerlijke gap-cue — zelfde subboom-semantiek en cue-taal als kaart/lijst (gelezen
             uit de gedeelde gapIds-afleiding, niet herafgeleid). -->
        <span
          v-if="popupGap"
          data-testid="diagram-popup-gap"
          class="mt-2 inline-block rounded-[var(--lk-radius-badge)] border border-dashed border-[var(--lk-color-border)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
        >geen ondersteunend systeem</span>
        <!-- Drie uitgangen, visueel gescheiden: verbreden BINNEN dit beeld (knop) vs. de twee
             vertrek-navigaties (kaart = component-wereld; detailscherm) onder een deellijn. -->
        <div class="mt-[var(--lk-space-md)] flex flex-col gap-[var(--lk-space-sm)]">
          <Button
            label="Toon hele processenlandschap"
            severity="secondary"
            data-testid="diagram-popup-landschap"
            :disabled="heleLandschap"
            @click="toonHeleLandschap"
          />
          <div class="flex flex-col gap-[var(--lk-space-xs)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]">
            <Button
              v-if="magKaartZien"
              label="Bekijk op de kaart →"
              severity="secondary"
              data-testid="diagram-popup-kaart"
              @click="emit('bekijkOpKaart', popupProces)"
            />
            <router-link
              :to="{ name: 'proces-detail', params: { id: popupProces.id } }"
              data-testid="diagram-popup-open"
              class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >Open proces →</router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
