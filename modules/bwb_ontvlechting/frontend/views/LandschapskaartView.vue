<script setup>
/**
 * LandschapskaartView — interactieve, read-only grafische landschapsweergave (ADR-025).
 *
 * Hybride layout per modus:
 *  - Ego-view: SVG full-bleed; filters zweven als inklapbaar overlay-paneel (Google-Maps-stijl),
 *    modus-toggle als overlay bovenaan-gecentreerd.
 *  - Impact-view: SVG vult de resterende breedte (flex-1); een VASTE rechterzijbalk (altijd
 *    zichtbaar) draagt de modus-toggle, migratieset-selectie, laagfilters en de lifecycle-legenda.
 *
 * De viewBox volgt de werkelijke canvasbreedte (ResizeObserver op de canvas-div, niet de wrapper),
 * zodat de graaf in beide modi correct full-bleed rendert. Lifecycle-statuskleur = node-achtergrond;
 * ringkleur = rand. Leunt op GET /landschapskaart. Geen engine-aanraking (read-only).
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

// Impact-kleuren (in-set / raakvlak) — gedeeld door de canvas-nodes én de legenda.
const INSET_KLEUR = '#1e3a8a'
const RAAKVLAK_KLEUR = '#fed7aa'
// Lifecycle-legenda (rechterzijbalk, impact-view).
const LEGENDA = [
  { label: 'migratieklaar', kleur: LIFECYCLE_KLEUR.migratieklaar },
  { label: 'geblokkeerd', kleur: LIFECYCLE_KLEUR.geblokkeerd },
  { label: 'in_inventarisatie', kleur: LIFECYCLE_KLEUR.in_inventarisatie },
  { label: 'concept', kleur: LIFECYCLE_KLEUR.concept },
  { label: 'geen profiel', kleur: NEUTRAAL },
]

// ── State ───────────────────────────────────────────────────────────────────────
const nodes = ref([])
const edges = ref([])
const laden = ref(true)
const fout = ref(null)

const modus = ref('ego') // 'ego' | 'impact'
const filtersOpen = ref(false) // ego-overlay: standaard ingeklapt
const ringAan = ref(new Set(RINGEN))
const laagAan = ref(new Set(LAGEN))
const startpuntId = ref(null)
const migratieSet = ref(new Set())
const hover = ref(null) // { naam, type, lifecycle, x, y }

// ── Canvas-afmeting via ResizeObserver op de CANVAS-div (flex-1) ─────────────────
const canvasRef = ref(null)
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
    if (canvasRef.value) resizeObserver.observe(canvasRef.value)
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
const allesGeselecteerd = computed(
  () => applicaties.value.length > 0 && applicaties.value.every((a) => migratieSet.value.has(a.id)),
)
function toggleAlles() {
  migratieSet.value = allesGeselecteerd.value ? new Set() : new Set(applicaties.value.map((a) => a.id))
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
  <div class="relative flex w-full" data-testid="lk-wrapper" style="height: calc(100vh - 9rem)">
    <!-- Canvas: vult de resterende breedte (flex-1); ResizeObserver meet hier de viewBox -->
    <div ref="canvasRef" data-testid="lk-canvas" class="relative flex-1 overflow-hidden rounded-[var(--cd-radius-card)] bg-[var(--cd-color-surface)]">
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
              :fill="p.inSet ? INSET_KLEUR : p.raakvlak ? RAAKVLAK_KLEUR : lifecycleKleur(p.node.lifecycle_status)"
              :stroke="p.inSet ? INSET_KLEUR : p.raakvlak ? '#ea580c' : '#cbd5e1'"
              stroke-width="2"
              :data-inset="p.inSet" :data-raakvlak="p.raakvlak"
            />
            <text :x="p.x" :y="p.y + 4" text-anchor="middle" :class="['text-[length:11px]', p.inSet ? 'fill-white' : '']">{{ p.node.naam }}</text>
          </g>
        </template>
      </svg>

      <!-- Ego-view overlays (modus-toggle + filterknop + inklapbaar paneel) -->
      <template v-if="modus === 'ego'">
        <div class="absolute top-3 left-1/2 z-10 flex -translate-x-1/2 gap-[var(--cd-space-sm)] rounded-[var(--cd-radius-btn)] bg-white/90 p-1 shadow-[var(--cd-shadow-md)]">
          <button type="button" data-testid="lk-modus-ego" aria-pressed="true" class="rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-primary)] px-[var(--cd-space-md)] py-1 text-white">Ego-view</button>
          <button type="button" data-testid="lk-modus-impact" aria-pressed="false" class="rounded-[var(--cd-radius-btn)] px-[var(--cd-space-md)] py-1" @click="modus = 'impact'">Impact-view</button>
        </div>

        <button
          type="button"
          data-testid="lk-filter-toggle"
          :aria-expanded="filtersOpen.toString()"
          class="absolute left-3 top-3 z-10 rounded-[var(--cd-radius-btn)] bg-white/90 px-[var(--cd-space-md)] py-1 shadow-[var(--cd-shadow-md)] hover:bg-white"
          @click="filtersOpen = !filtersOpen"
        >
          {{ filtersOpen ? '✕ Filters' : '⚙ Filters' }}
        </button>

        <aside
          v-if="filtersOpen && heeftData"
          data-testid="lk-paneel"
          class="absolute left-3 top-12 z-10 w-52 rounded-[8px] bg-white p-[var(--cd-space-md)] shadow-[var(--cd-shadow-md)]"
        >
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
        </aside>
      </template>

      <!-- Impact-samenvatting (overlay onderaan canvas) -->
      <p
        v-if="modus === 'impact' && heeftData"
        data-testid="impact-samenvatting"
        class="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-white px-[var(--cd-space-md)] py-1 text-[length:var(--cd-text-sm)] font-semibold shadow-[var(--cd-shadow-md)]"
      >
        {{ impactSamenvatting }}
      </p>

      <!-- Node-tooltip -->
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

    <!-- Impact-view: vaste rechterzijbalk (altijd zichtbaar in deze modus) -->
    <aside
      v-if="modus === 'impact'"
      data-testid="lk-sidebar"
      class="flex w-56 flex-shrink-0 flex-col gap-[var(--cd-space-md)] overflow-y-auto border-l border-[var(--cd-color-border)] bg-white p-[var(--cd-space-md)]"
    >
      <!-- Modus-toggle bovenaan de zijbalk -->
      <div class="flex gap-[var(--cd-space-sm)] rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-accent)] p-1">
        <button type="button" data-testid="lk-modus-ego" aria-pressed="false" class="flex-1 rounded-[var(--cd-radius-btn)] px-2 py-1 text-[length:var(--cd-text-sm)]" @click="modus = 'ego'">Ego-view</button>
        <button type="button" data-testid="lk-modus-impact" aria-pressed="true" class="flex-1 rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-primary)] px-2 py-1 text-[length:var(--cd-text-sm)] text-white">Impact-view</button>
      </div>

      <!-- Migratieset -->
      <div>
        <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">Migratieset</p>
        <div class="flex max-h-64 flex-col gap-1 overflow-y-auto">
          <label v-for="a in applicaties" :key="a.id" class="flex items-center gap-2 text-[length:var(--cd-text-sm)]">
            <input type="checkbox" :checked="migratieSet.has(a.id)" :data-testid="`lk-migratie-${a.id}`" @change="toggleMigratie(a.id)" />
            <span class="grow truncate">{{ a.naam }}</span>
            <span class="inline-block h-3 w-3 shrink-0 rounded-full" :style="{ background: lifecycleKleur(a.lifecycle_status) }" :title="a.lifecycle_status || 'geen profiel'"></span>
          </label>
          <p v-if="!applicaties.length" class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">Geen applicaties.</p>
        </div>
        <button type="button" data-testid="lk-alles-toggle" class="mt-1 text-[length:var(--cd-text-xs)] text-[var(--cd-color-primary)] hover:underline" @click="toggleAlles">
          {{ allesGeselecteerd ? 'Niets selecteren' : 'Alles selecteren' }}
        </button>
      </div>

      <!-- Laagfilters -->
      <div>
        <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">ArchiMate-lagen</p>
        <div class="flex flex-col gap-1">
          <label v-for="l in LAGEN" :key="l" class="flex items-center gap-2 text-[length:var(--cd-text-sm)]">
            <input type="checkbox" :checked="laagActief(l)" :data-testid="`lk-sidebar-laag-${l}`" @change="toggleLaag(l)" />{{ typeLabel(l) }}
          </label>
        </div>
      </div>

      <!-- Lifecycle-legenda -->
      <div data-testid="lk-legenda">
        <p class="mb-1 font-semibold text-[length:var(--cd-text-sm)]">Legenda</p>
        <div class="flex flex-col gap-1 text-[length:var(--cd-text-sm)]">
          <span class="flex items-center gap-2"><span class="inline-block h-3 w-3 rounded-sm" :style="{ background: INSET_KLEUR }"></span>In set</span>
          <span class="flex items-center gap-2"><span class="inline-block h-3 w-3 rounded-sm border border-[#ea580c]" :style="{ background: RAAKVLAK_KLEUR }"></span>Raakvlak</span>
          <span v-for="lg in LEGENDA" :key="lg.label" class="flex items-center gap-2"><span class="inline-block h-3 w-3 rounded-full border border-[var(--cd-color-border)]" :style="{ background: lg.kleur }"></span>{{ lg.label }}</span>
        </div>
      </div>
    </aside>
  </div>
</template>
