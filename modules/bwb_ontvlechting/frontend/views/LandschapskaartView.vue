<script setup>
/**
 * LandschapskaartView — interactieve, read-only grafische landschapsweergave (ADR-025).
 *
 * Overlay-layout (Google-Maps-stijl): de SVG vult het volledige contentgebied; filters,
 * modus-toggle, samenvatting en node-tooltip zweven als absolute overlays erover. Het
 * filterpaneel is standaard ingeklapt. De viewBox volgt de werkelijke containerafmeting
 * (ResizeObserver), zodat de graaf full-bleed rendert zonder vervorming.
 *
 * Twee modi:
 *  - Ego-view: één startpunt (applicatie) centraal; buren gegroepeerd per ring; ring-/laagfilters.
 *  - Impact-view: applicaties als "migratieset"; blauw = in set, oranje = raakvlak; live samenvatting.
 *
 * Lifecycle-statuskleur = node-achtergrond; ringkleur = rand. Leunt op GET /landschapskaart
 * (volledige graaf in één call). Geen engine-aanraking (read-only).
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '@/api'
import { humaniseer } from '../labels'

// Lifecycle → node-achtergrond (spec ADR-025).
const LIFECYCLE_KLEUR = {
  concept: '#f1f5f9',
  in_inventarisatie: '#dbeafe',
  geblokkeerd: '#fee2e2',
  migratieklaar: '#dcfce7',
}
const NEUTRAAL = '#f8fafc'
function lifecycleKleur(status) {
  return LIFECYCLE_KLEUR[status] || NEUTRAAL
}

// Ring → randkleur.
const RING_KLEUR = {
  applicaties: '#2563eb',
  beheerorganisatie: '#7c3aed',
  contracten: '#d97706',
  infrastructuur: '#0891b2',
}
const RINGEN = ['applicaties', 'beheerorganisatie', 'contracten', 'infrastructuur']
const LAGEN = ['business', 'application', 'technology']

// ── State ───────────────────────────────────────────────────────────────────────
const nodes = ref([])
const edges = ref([])
const laden = ref(true)
const fout = ref(null)

const modus = ref('ego') // 'ego' | 'impact'
const filtersOpen = ref(false) // standaard ingeklapt
const ringAan = ref(new Set(RINGEN))
const laagAan = ref(new Set(LAGEN))
const startpuntId = ref(null)
const migratieSet = ref(new Set())
const hover = ref(null) // { naam, type, lifecycle, x, y }

// ── Canvas-afmeting via ResizeObserver (full-bleed; viewBox volgt de container) ───
const containerRef = ref(null)
const canvasW = ref(800)
const canvasH = ref(600)
const CX = computed(() => canvasW.value / 2)
const CY = computed(() => canvasH.value / 2)
let resizeObserver = null

onMounted(() => {
  laad()
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) canvasW.value = entry.contentRect.width
        if (entry.contentRect.height > 0) canvasH.value = entry.contentRect.height
      }
    })
    if (containerRef.value) resizeObserver.observe(containerRef.value)
  }
})
onUnmounted(() => resizeObserver?.disconnect())

// ── Data laden ────────────────────────────────────────────────────────────────
async function laad() {
  laden.value = true
  fout.value = null
  try {
    const data = await api.landschapskaart.haalGrafdata()
    nodes.value = data.nodes || []
    edges.value = data.edges || []
    const eersteApp = nodes.value.find((n) => n.element_type === 'applicatie')
    startpuntId.value = eersteApp ? eersteApp.id : null
  } catch (e) {
    fout.value = e?.message || 'Laden van de landschapskaart mislukt.'
  } finally {
    laden.value = false
  }
}

const nodePerId = computed(() => Object.fromEntries(nodes.value.map((n) => [n.id, n])))
const applicaties = computed(() => nodes.value.filter((n) => n.element_type === 'applicatie'))
const heeftData = computed(() => nodes.value.length > 0)

// ── Filters ───────────────────────────────────────────────────────────────────
function toggleRing(r) {
  const s = new Set(ringAan.value)
  s.has(r) ? s.delete(r) : s.add(r)
  ringAan.value = s
}
function toggleLaag(l) {
  const s = new Set(laagAan.value)
  s.has(l) ? s.delete(l) : s.add(l)
  laagAan.value = s
}
const ringActief = (r) => ringAan.value.has(r)
const laagActief = (l) => laagAan.value.has(l)

// ── Hover-tooltip ───────────────────────────────────────────────────────────────
function toonHover(node, x, y) {
  hover.value = { naam: node.naam, type: node.element_type, lifecycle: node.lifecycle_status, x, y }
}
function verbergHover() {
  hover.value = null
}

// ── Ego-view ────────────────────────────────────────────────────────────────────
const egoBuren = computed(() => {
  const sp = startpuntId.value
  if (!sp) return []
  const gevonden = new Map() // buur_id → ring
  for (const e of edges.value) {
    if (!ringAan.value.has(e.ring)) continue
    let buur = null
    if (e.bron_id === sp) buur = e.doel_id
    else if (e.doel_id === sp) buur = e.bron_id
    if (!buur) continue
    const node = nodePerId.value[buur]
    if (!node) continue
    if (node.laag && LAGEN.includes(node.laag) && !laagAan.value.has(node.laag)) continue
    if (!gevonden.has(buur)) gevonden.set(buur, e.ring)
  }
  return [...gevonden.entries()].map(([id, ring]) => ({ node: nodePerId.value[id], ring }))
})

const egoWeergave = computed(() => {
  const sp = nodePerId.value[startpuntId.value]
  if (!sp) return { center: null, buren: [], lijnen: [] }
  const buren = egoBuren.value
  const R = Math.max(120, Math.min(canvasW.value, canvasH.value) / 2 - 90)
  const posBuren = buren.map((b, i) => {
    const hoek = (2 * Math.PI * i) / Math.max(buren.length, 1) - Math.PI / 2
    return { ...b, x: CX.value + R * Math.cos(hoek), y: CY.value + R * Math.sin(hoek) }
  })
  const posPerId = Object.fromEntries(posBuren.map((b) => [b.node.id, b]))
  const lijnen = []
  for (const b of posBuren) {
    lijnen.push({ x1: CX.value, y1: CY.value, x2: b.x, y2: b.y, kleur: RING_KLEUR[b.ring], gestippeld: false, key: `c-${b.node.id}` })
  }
  for (const e of edges.value) {
    const a = posPerId[e.bron_id]
    const c = posPerId[e.doel_id]
    if (a && c) lijnen.push({ x1: a.x, y1: a.y, x2: c.x, y2: c.y, kleur: '#94a3b8', gestippeld: true, key: `r-${e.bron_id}-${e.doel_id}-${e.relatietype}` })
  }
  return { center: { ...sp, x: CX.value, y: CY.value }, buren: posBuren, lijnen }
})

// ── Impact-view ───────────────────────────────────────────────────────────────
function toggleMigratie(id) {
  const s = new Set(migratieSet.value)
  s.has(id) ? s.delete(id) : s.add(id)
  migratieSet.value = s
}
const appKoppelingen = computed(() =>
  edges.value.filter(
    (e) => e.ring === 'applicaties' && nodePerId.value[e.bron_id]?.element_type === 'applicatie' && nodePerId.value[e.doel_id]?.element_type === 'applicatie',
  ),
)
const grensKoppelingen = computed(() =>
  appKoppelingen.value.filter((e) => migratieSet.value.has(e.bron_id) !== migratieSet.value.has(e.doel_id)),
)
const raakvlakken = computed(() => {
  const s = new Set()
  for (const e of grensKoppelingen.value) {
    if (!migratieSet.value.has(e.bron_id)) s.add(e.bron_id)
    if (!migratieSet.value.has(e.doel_id)) s.add(e.doel_id)
  }
  return s
})
const impactSamenvatting = computed(
  () => `${migratieSet.value.size} in set · ${raakvlakken.value.size} raakvlakken · ${grensKoppelingen.value.length} grensoverschrijdende koppelingen`,
)

const impactWeergave = computed(() => {
  const apps = applicaties.value
  const kolommen = Math.max(1, Math.ceil(Math.sqrt(apps.length)))
  const dx = canvasW.value / (kolommen + 1)
  const rijen = Math.max(1, Math.ceil(apps.length / kolommen))
  const dy = canvasH.value / (rijen + 1)
  const pos = apps.map((n, i) => ({
    node: n,
    x: dx * ((i % kolommen) + 1),
    y: dy * (Math.floor(i / kolommen) + 1),
    inSet: migratieSet.value.has(n.id),
    raakvlak: raakvlakken.value.has(n.id),
  }))
  const posPerId = Object.fromEntries(pos.map((p) => [p.node.id, p]))
  const lijnen = appKoppelingen.value
    .map((e) => {
      const a = posPerId[e.bron_id]
      const b = posPerId[e.doel_id]
      if (!a || !b) return null
      const grens = migratieSet.value.has(e.bron_id) !== migratieSet.value.has(e.doel_id)
      const beide = migratieSet.value.has(e.bron_id) && migratieSet.value.has(e.doel_id)
      return { x1: a.x, y1: a.y, x2: b.x, y2: b.y, kleur: grens ? '#ea580c' : beide ? '#2563eb' : '#cbd5e1', key: `${e.bron_id}-${e.doel_id}` }
    })
    .filter(Boolean)
  return { pos, lijnen }
})

const typeLabel = (t) => humaniseer(t)
</script>

<template>
  <div
    ref="containerRef"
    data-testid="lk-container"
    class="relative w-full overflow-hidden rounded-[var(--cd-radius-card)] bg-[var(--cd-color-surface)]"
    style="height: calc(100vh - 9rem)"
  >
    <!-- Canvas: vult de volledige container -->
    <svg
      v-if="heeftData"
      :viewBox="`0 0 ${canvasW} ${canvasH}`"
      preserveAspectRatio="xMidYMid meet"
      data-testid="lk-svg"
      class="h-full w-full"
    >
      <!-- Ego-view -->
      <template v-if="modus === 'ego' && egoWeergave.center">
        <line v-for="l in egoWeergave.lijnen" :key="l.key" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" :stroke="l.kleur" :stroke-dasharray="l.gestippeld ? '4 4' : '0'" stroke-width="1.5" />
        <g v-for="b in egoWeergave.buren" :key="b.node.id" :data-testid="`lk-node-${b.node.id}`" class="cursor-pointer" @click="startpuntId = b.node.id" @mouseenter="toonHover(b.node, b.x, b.y)" @mouseleave="verbergHover">
          <rect :x="b.x - 60" :y="b.y - 18" width="120" height="36" rx="6" :fill="lifecycleKleur(b.node.lifecycle_status)" :stroke="RING_KLEUR[b.ring]" stroke-width="2" :data-fill="lifecycleKleur(b.node.lifecycle_status)" />
          <text :x="b.x" :y="b.y + 4" text-anchor="middle" class="text-[length:11px]">{{ b.node.naam }}</text>
        </g>
        <g :data-testid="`lk-node-${egoWeergave.center.id}`" @mouseenter="toonHover(egoWeergave.center, CX, CY)" @mouseleave="verbergHover">
          <rect :x="CX - 70" :y="CY - 20" width="140" height="40" rx="8" :fill="lifecycleKleur(egoWeergave.center.lifecycle_status)" stroke="#0f172a" stroke-width="3" :data-fill="lifecycleKleur(egoWeergave.center.lifecycle_status)" />
          <text :x="CX" :y="CY + 4" text-anchor="middle" class="text-[length:12px] font-semibold">{{ egoWeergave.center.naam }}</text>
        </g>
      </template>

      <!-- Impact-view -->
      <template v-else-if="modus === 'impact'">
        <line v-for="l in impactWeergave.lijnen" :key="l.key" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" :stroke="l.kleur" stroke-width="2" />
        <g v-for="p in impactWeergave.pos" :key="p.node.id" :data-testid="`lk-node-${p.node.id}`" class="cursor-pointer" @click="toggleMigratie(p.node.id)" @mouseenter="toonHover(p.node, p.x, p.y)" @mouseleave="verbergHover">
          <rect
            :x="p.x - 60" :y="p.y - 18" width="120" height="36" rx="6"
            :fill="p.inSet ? '#1e3a8a' : p.raakvlak ? '#fed7aa' : lifecycleKleur(p.node.lifecycle_status)"
            :stroke="p.inSet ? '#1e3a8a' : p.raakvlak ? '#ea580c' : '#cbd5e1'"
            stroke-width="2"
            :data-inset="p.inSet" :data-raakvlak="p.raakvlak"
          />
          <text :x="p.x" :y="p.y + 4" text-anchor="middle" :class="['text-[length:11px]', p.inSet ? 'fill-white' : '']">{{ p.node.naam }}</text>
        </g>
      </template>
    </svg>

    <!-- Modus-toggle (overlay, bovenaan gecentreerd) -->
    <div class="absolute top-3 left-1/2 z-10 flex -translate-x-1/2 gap-[var(--cd-space-sm)] rounded-[var(--cd-radius-btn)] bg-white/90 p-1 shadow-[var(--cd-shadow-md)]">
      <button type="button" data-testid="lk-modus-ego" :aria-pressed="modus === 'ego'" :class="['rounded-[var(--cd-radius-btn)] px-[var(--cd-space-md)] py-1', modus === 'ego' ? 'bg-[var(--cd-color-primary)] text-white' : '']" @click="modus = 'ego'">Ego-view</button>
      <button type="button" data-testid="lk-modus-impact" :aria-pressed="modus === 'impact'" :class="['rounded-[var(--cd-radius-btn)] px-[var(--cd-space-md)] py-1', modus === 'impact' ? 'bg-[var(--cd-color-primary)] text-white' : '']" @click="modus = 'impact'">Impact-view</button>
    </div>

    <!-- Filterknop (overlay, linksboven) -->
    <button
      type="button"
      data-testid="lk-filter-toggle"
      :aria-expanded="filtersOpen.toString()"
      class="absolute left-3 top-3 z-10 rounded-[var(--cd-radius-btn)] bg-white/90 px-[var(--cd-space-md)] py-1 shadow-[var(--cd-shadow-md)] hover:bg-white"
      @click="filtersOpen = !filtersOpen"
    >
      {{ filtersOpen ? '✕ Filters' : '⚙ Filters' }}
    </button>

    <!-- Filterpaneel (overlay, zweeft links onder de knop; standaard ingeklapt) -->
    <aside
      v-if="filtersOpen && heeftData"
      data-testid="lk-paneel"
      class="absolute left-3 top-12 z-10 w-52 rounded-[8px] bg-white p-[var(--cd-space-md)] shadow-[var(--cd-shadow-md)]"
    >
      <template v-if="modus === 'ego'">
        <label class="mb-[var(--cd-space-md)] block text-[length:var(--cd-text-sm)]">
          <span class="mb-1 block font-semibold">Startpunt</span>
          <select v-model="startpuntId" data-testid="lk-startpunt" class="w-full rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1">
            <option v-for="a in applicaties" :key="a.id" :value="a.id">{{ a.naam }}</option>
          </select>
        </label>
        <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">Ringen</p>
        <div class="mb-[var(--cd-space-md)] flex flex-col gap-1">
          <label v-for="r in RINGEN" :key="r" class="flex items-center gap-2 text-[length:var(--cd-text-sm)]">
            <input type="checkbox" :checked="ringActief(r)" :data-testid="`lk-ring-${r}`" @change="toggleRing(r)" />
            <span class="inline-block h-3 w-3 rounded-full" :style="{ background: RING_KLEUR[r] }"></span>{{ typeLabel(r) }}
          </label>
        </div>
        <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">ArchiMate-lagen</p>
        <div class="flex flex-col gap-1">
          <label v-for="l in LAGEN" :key="l" class="flex items-center gap-2 text-[length:var(--cd-text-sm)]">
            <input type="checkbox" :checked="laagActief(l)" :data-testid="`lk-laag-${l}`" @change="toggleLaag(l)" />{{ typeLabel(l) }}
          </label>
        </div>
      </template>

      <template v-else>
        <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">Migratieset</p>
        <p class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">Klik applicaties aan/uit.</p>
        <div class="flex max-h-72 flex-col gap-1 overflow-auto">
          <label v-for="a in applicaties" :key="a.id" class="flex items-center gap-2 text-[length:var(--cd-text-sm)]">
            <input type="checkbox" :checked="migratieSet.has(a.id)" :data-testid="`lk-migratie-${a.id}`" @change="toggleMigratie(a.id)" />{{ a.naam }}
          </label>
        </div>
      </template>
    </aside>

    <!-- Impact-samenvatting (overlay, onderaan gecentreerd) -->
    <p
      v-if="modus === 'impact' && heeftData"
      data-testid="impact-samenvatting"
      class="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-white px-[var(--cd-space-md)] py-1 text-[length:var(--cd-text-sm)] font-semibold shadow-[var(--cd-shadow-md)]"
    >
      {{ impactSamenvatting }}
    </p>

    <!-- Node-tooltip (overlay bij hover) -->
    <div
      v-if="hover"
      data-testid="lk-tooltip"
      class="pointer-events-none absolute z-20 rounded-[6px] bg-[var(--cd-color-text)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-xs)] text-white shadow-[var(--cd-shadow-md)]"
      :style="{ left: `${hover.x + 12}px`, top: `${hover.y - 8}px` }"
    >
      <span class="font-semibold">{{ hover.naam }}</span> · {{ typeLabel(hover.type) }}<template v-if="hover.lifecycle"> · {{ typeLabel(hover.lifecycle) }}</template>
    </div>

    <!-- Status-overlays -->
    <p v-if="fout" role="alert" data-testid="lk-fout" class="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 rounded-[var(--cd-radius-badge)] border border-[var(--cd-color-danger)] bg-white px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden" data-testid="lk-laden" class="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 text-[var(--cd-color-text-muted)]">Landschap laden…</p>
    <p v-else-if="!heeftData" data-testid="lk-leeg" class="absolute left-1/2 top-1/2 z-10 max-w-md -translate-x-1/2 -translate-y-1/2 text-center text-[var(--cd-color-text-muted)]">
      Nog geen landschapsdata geregistreerd. Voeg componenten, partijen, contracten en relaties toe om de kaart te vullen.
    </p>
  </div>
</template>
