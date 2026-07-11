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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import cytoscape from '@/composables/cytoscape'
import { procesBoomLayout, procesFocusSet } from '../procesBoom'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({
  // De volledige processet (platte rijen mét ouder_id) — geleverd door ProcesLijst.
  processen: { type: Array, required: true },
  // Set van proces-ids waarvan de héle subboom geen ondersteuning draagt (of null zolang de
  // afleiding nog laadt) — zelfde bron als de tree-view-cue.
  gapIds: { type: Object, default: null },
})

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

// De zichtbare focus-set: leeg zolang er geen (bestaand) centrum gekozen is — het beeld opent
// leeg ("Zoek een proces om te beginnen."). Verdwijnt het centrum (bv. verwijderd in de Boom),
// dan valt de set vanzelf terug naar leeg (procesFocusSet geeft een lege set).
const zichtbareIds = computed(() =>
  procesFocusSet(centrumId.value, alleIds.value, hierEdges.value, naamVan))
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
  if (item?.id) centrumId.value = item.id
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
  // Het centrum draagt de bestaande oranje selectie-taal ("kijk hier").
  { selector: 'node.hl-node', style: { 'border-width': 3, 'border-color': SELECTIE_RAND, 'border-style': 'solid' } },
]

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

// Post-layout werk hoort in de stop-callback (ADR-040): her-meting + fit + centrum-markering.
function _naLayout() {
  cy?.resize?.()
  cy?.fit?.(undefined, 50)
  cy?.nodes?.()?.removeClass?.('hl-node')
  const c = centrumId.value ? cy?.getElementById?.(centrumId.value) : null
  if (c?.length) c.addClass?.('hl-node')
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
  if (typeof ResizeObserver !== 'undefined') {
    // Maatwissel = resize + fit op de bestaande posities — nooit een re-layout (LI036-regel).
    resizeObserver = new ResizeObserver(() => { cy?.resize?.(); cy?.fit?.(undefined, 50) })
    resizeObserver.observe(containerRef.value)
  }
  await tekenGraaf()
})
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  cy?.destroy?.()
  cy = null
})

// Eén render-eigenaar: elke wijziging van de focus-set of de gap-cue hertekent via hetzelfde pad.
watch([zichtbareIds, () => props.gapIds], () => { tekenGraaf() })

defineExpose({ kiesCentrum, centrumId, zichtbareIds })
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
    </div>
  </div>
</template>
