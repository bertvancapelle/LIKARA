<script setup>
/**
 * KaartBeginscherm — het 4-ingangen-vertrekpunt van de Landschapskaart (Fase B slice 2b, LI023).
 *
 * De kaart opent LEEG (LI021): de gebruiker bouwt een actieve set op via vier gelijkwaardige
 * ingangen i.p.v. "hier is alles, filter maar weg":
 *   1. Zoeken op component (hoofdroute) — server-side `/componenten` (type + zoekterm + filters).
 *   2. Via context — leverancier / contract / gebruikerscontext: selecteer → laad de onderliggende
 *      componenten → emit ze (de parent accumuleert in de set en dedupt).
 *   3. Opgeslagen views — als gelijkwaardige instap.
 *   4. "Toon het hele landschap" — bescheiden ontsnapping onderaan.
 *
 * Read-only & stateless: het component muteert niets zelf; het emit alleen componenten/views naar
 * de parent (LandschapskaartView), die de set/graaf beheert. Zodra de eerste component is toegevoegd
 * is de set niet meer leeg → de parent verlaat de 'leeg'-modus en dit scherm verdwijnt; de graaf +
 * "in beeld"-chips nemen de set-bewerking over.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '@/api'
import ZoekSelect from './ZoekSelect.vue'
import { humaniseer } from '../labels'

const props = defineProps({
  opgeslagenViews: { type: Array, default: () => [] },
  // Componenttype-opties voor de type-keuze (uit api.componenten.opties() → componenttype).
  componentOpties: { type: Array, default: () => [] },
  // Eigenaar-opties (organisatie-partijen); interface-compat — de eigenaar-picker zoekt server-side.
  eigenaarOpties: { type: Array, default: () => [] },
})
const emit = defineEmits(['voegComponentenToe', 'openView', 'toonHeleLandschap'])

// Gesloten enum-lijsten (≤10 vaste opties → native <select>, conform ZoekSelect-standaard).
const LAAG_OPTIES = ['application', 'technology', 'business', 'implementation_migration']
const HOSTING_OPTIES = ['on_premise', 'private_cloud', 'saas', 'iaas', 'paas', 'hybride', 'onbekend']

// ── Zoekroute (hoofdroute) ──────────────────────────────────────────────────────
const gekozenType = ref('applicatie') // standaard 'applicatie' (gewone type-filterwaarde, geen aparte ingang)
const zoekterm = ref('')
const resultaten = ref([])
const zoekLaden = ref(false)
const zoekOpen = ref(false)
const toegevoegd = ref(new Set()) // lokaal: welke resultaten al geëmit zijn (markering, geen dubbele)

// ── Filters (weggevouwen) ─────────────────────────────────────────────────────
const toonFilters = ref(false)
const filterLaag = ref('')
const filterHosting = ref('')
const eigenaarId = ref(null)
const filtersActief = computed(() => !!(filterLaag.value || filterHosting.value || eigenaarId.value))

function _zoekParams() {
  const p = {}
  if (gekozenType.value) p.componenttype = gekozenType.value
  const q = zoekterm.value.trim()
  if (q) p.zoek = q
  if (filterLaag.value) p.laag = filterLaag.value
  if (filterHosting.value) p.hostingmodel = filterHosting.value
  if (eigenaarId.value) p.eigenaar_organisatie_id = eigenaarId.value
  return p
}
async function zoek() {
  zoekLaden.value = true
  zoekOpen.value = true
  try {
    const r = await api.componenten.lijst(_zoekParams())
    resultaten.value = r?.items || []
  } catch {
    resultaten.value = [] // faalt zacht — geen crash op het beginscherm
  } finally {
    zoekLaden.value = false
  }
}
let _t = null
function zoekDebounced() {
  clearTimeout(_t)
  _t = setTimeout(zoek, 300)
}
function isToegevoegd(id) {
  return toegevoegd.value.has(id)
}
function voegResultaatToe(n) {
  if (!n?.id || isToegevoegd(n.id)) return
  toegevoegd.value = new Set(toegevoegd.value).add(n.id)
  emit('voegComponentenToe', [n])
}

// ── Via context (drie symmetrische secties) ──────────────────────────────────────
// ZoekSelect (server-side) + @keuze: één keuze → laad de onderliggende componenten → emit.
// Bewust ZoekSelect i.p.v. ZoekMultiSelect: de gebruikerscontext heeft GEEN enkelvoudige id
// (samengestelde sleutel organisatie_id+afdeling) en de "selecteer → laad → emit"-flow past op
// het @keuze-event. De accumulatie/dedup gebeurt in de parent-set (re-selecteren = stil overgeslagen).
const zoekLeveranciers = (params = {}) => api.partijen.lijst({ ...params, aard: 'externe_partij' })
const zoekContracten = (params = {}) => api.contracten.lijst(params)
const zoekEigenaars = (params = {}) => api.partijen.lijst({ ...params, aard: 'organisatie' })
// Contexten kent alléén `zoek` (geen keyset/limit) → strip de overige ZoekSelect-params en
// voorzie elke rij van een synthetische `_key` (idVeld) want er is geen enkelvoudige id-kolom.
const zoekContexten = async ({ zoek } = {}) => {
  const r = await api.gebruikersgroepen.contexten({ zoek })
  return (r || []).map((c) => ({ ...c, _key: `${c.organisatie_id || ''}|${c.afdeling || ''}` }))
}
function _contextLabel(c) {
  return `${c.organisatie_naam || '—'} — ${c.afdeling || '—'} (${c.aantal_componenten} componenten)`
}

function _emitComponenten(lijst, mapper) {
  const arr = Array.isArray(lijst) ? lijst : lijst?.items || []
  const comps = arr.map(mapper).filter((c) => c.id)
  if (comps.length) emit('voegComponentenToe', comps)
}
async function kiesLeverancier(item) {
  try {
    const r = await api.partijen.componentenViaContract(item.id)
    _emitComponenten(r, (c) => ({ id: c.component_id, naam: c.component_naam }))
  } catch { /* faalt zacht */ }
}
async function kiesContract(item) {
  try {
    const r = await api.contracten.componenten(item.id)
    _emitComponenten(r, (c) => ({ id: c.component_id, naam: c.component_naam, componenttype: c.componenttype }))
  } catch { /* faalt zacht */ }
}
async function kiesContext(item) {
  try {
    const r = await api.gebruikersgroepen.contextComponenten({
      organisatie_id: item.organisatie_id || undefined,
      afdeling: item.afdeling || undefined,
    })
    _emitComponenten(r, (c) => ({ id: c.component_id, naam: c.component_naam, componenttype: c.componenttype }))
  } catch { /* faalt zacht */ }
}

// ── Lege staat ───────────────────────────────────────────────────────────────
const toonLegeStaat = computed(
  () => !props.opgeslagenViews.length && !resultaten.value.length && !zoekterm.value.trim(),
)

// Dropdown sluiten bij klik buiten / Escape.
const wortel = ref(null)
function _opBuitenklik(e) {
  if (wortel.value && !wortel.value.contains(e.target)) zoekOpen.value = false
}
function _opEscape(e) {
  if (e.key === 'Escape') zoekOpen.value = false
}
onMounted(() => {
  document.addEventListener('mousedown', _opBuitenklik)
  document.addEventListener('keydown', _opEscape)
})
onBeforeUnmount(() => {
  clearTimeout(_t)
  document.removeEventListener('mousedown', _opBuitenklik)
  document.removeEventListener('keydown', _opEscape)
})

defineExpose({ zoek, zoekterm, gekozenType, filterLaag, filterHosting, eigenaarId, resultaten, toonFilters })
</script>

<template>
  <div
    ref="wortel"
    data-testid="lk-beginscherm"
    class="flex flex-col gap-[var(--cd-space-lg)] overflow-y-auto p-[var(--cd-space-lg)]"
  >
    <div class="mx-auto flex w-full max-w-2xl flex-col gap-[var(--cd-space-lg)]">
      <header class="flex flex-col gap-1">
        <h2 class="text-[length:var(--cd-text-lg)] font-semibold">Begin je verkenning</h2>
        <p class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
          Zoek een component, kies via leverancier, contract of gebruikerscontext, open een opgeslagen view — of toon het hele landschap.
        </p>
      </header>

      <!-- 1 — Zoekroute (hoofdroute): type-filter + zoekterm → aanvinkbare resultatenlijst -->
      <section class="flex flex-col gap-[var(--cd-space-sm)]">
        <p class="text-[length:var(--cd-text-sm)] font-semibold">Zoek een component</p>
        <div class="relative flex gap-[var(--cd-space-sm)]">
          <select
            v-model="gekozenType"
            data-testid="kb-type"
            aria-label="Componenttype"
            class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] bg-white px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)]"
            @change="zoek"
          >
            <option v-for="o in componentOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label || humaniseer(o.optie_sleutel) }}</option>
          </select>
          <input
            v-model="zoekterm"
            type="search"
            data-testid="kb-zoek"
            placeholder="🔍 Zoek op naam…"
            aria-label="Zoek component"
            class="grow rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-sm)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
            @focus="zoekOpen = true"
            @input="zoekDebounced"
          />

          <!-- Uitklapbare, aanvinkbare resultatenlijst (multi-select) -->
          <ul
            v-show="zoekOpen && (zoekLaden || resultaten.length)"
            data-testid="kb-resultaten"
            class="absolute left-0 right-0 top-full z-10 mt-1 max-h-72 overflow-auto rounded-[var(--cd-radius-card)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] shadow-[var(--cd-shadow-md)]"
          >
            <li v-if="zoekLaden" class="px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">Laden…</li>
            <li
              v-for="n in resultaten"
              v-else
              :key="n.id"
              :data-testid="`kb-res-${n.id}`"
              class="px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]"
            >
              <label class="flex cursor-pointer items-center gap-2" :class="isToegevoegd(n.id) ? 'text-[var(--cd-color-text-muted)]' : ''">
                <input
                  type="checkbox"
                  :data-testid="`kb-res-check-${n.id}`"
                  :checked="isToegevoegd(n.id)"
                  :disabled="isToegevoegd(n.id)"
                  @change="voegResultaatToe(n)"
                />
                <span class="grow truncate">{{ n.naam }}</span>
                <span v-if="isToegevoegd(n.id)" class="shrink-0 text-[var(--cd-color-primary)]" title="In de set">✓</span>
              </label>
            </li>
            <li v-if="!zoekLaden && !resultaten.length" class="px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">Geen resultaten.</li>
          </ul>
        </div>

        <!-- Filters (weggevouwen): verfijnen dezelfde /componenten-query (AND) -->
        <div>
          <button
            type="button"
            data-testid="kb-filters-toggle"
            class="flex items-center gap-1 text-[length:var(--cd-text-sm)] text-[var(--cd-color-primary)] hover:underline"
            :aria-expanded="toonFilters ? 'true' : 'false'"
            @click="toonFilters = !toonFilters"
          >
            + Filters
            <span v-if="filtersActief" data-testid="kb-filters-badge" class="rounded-full bg-[var(--cd-color-primary)] px-1.5 text-[length:var(--cd-text-xs)] text-white">actief</span>
          </button>
          <div v-if="toonFilters" data-testid="kb-filters" class="mt-[var(--cd-space-sm)] flex flex-wrap items-end gap-[var(--cd-space-md)]">
            <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
              <span class="font-semibold">Laag</span>
              <select v-model="filterLaag" data-testid="kb-filter-laag" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] bg-white px-[var(--cd-space-sm)] py-1" @change="zoek">
                <option value="">alle</option>
                <option v-for="l in LAAG_OPTIES" :key="l" :value="l">{{ humaniseer(l) }}</option>
              </select>
            </label>
            <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
              <span class="font-semibold">Hosting</span>
              <select v-model="filterHosting" data-testid="kb-filter-hosting" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] bg-white px-[var(--cd-space-sm)] py-1" @change="zoek">
                <option value="">alle</option>
                <option v-for="h in HOSTING_OPTIES" :key="h" :value="h">{{ humaniseer(h) }}</option>
              </select>
            </label>
            <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
              <span class="font-semibold">Eigenaar</span>
              <div class="w-56">
                <ZoekSelect
                  v-model="eigenaarId"
                  :zoek-functie="zoekEigenaars"
                  :weergave="(p) => p.naam"
                  id-veld="id"
                  placeholder="Zoek organisatie…"
                  testid="kb-eigenaar"
                  @update:model-value="zoek"
                />
              </div>
            </label>
          </div>
        </div>
      </section>

      <!-- 2 — Via context: drie symmetrische secties -->
      <section class="flex flex-col gap-[var(--cd-space-md)] border-t border-[var(--cd-color-border)] pt-[var(--cd-space-md)]">
        <p class="text-[length:var(--cd-text-sm)] font-semibold">Of kies via context</p>
        <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
          <span>Leverancier</span>
          <ZoekSelect :zoek-functie="zoekLeveranciers" :weergave="(p) => p.naam" id-veld="id" placeholder="Zoek leverancier…" testid="kb-leverancier" @keuze="kiesLeverancier" />
        </label>
        <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
          <span>Contract</span>
          <ZoekSelect :zoek-functie="zoekContracten" :weergave="(c) => c.naam" id-veld="id" placeholder="Zoek contract…" testid="kb-contract" @keuze="kiesContract" />
        </label>
        <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
          <span>Gebruikerscontext</span>
          <ZoekSelect :zoek-functie="zoekContexten" :weergave="_contextLabel" id-veld="_key" placeholder="Zoek organisatie of afdeling…" testid="kb-context" @keuze="kiesContext" />
        </label>
      </section>

      <!-- 3 — Opgeslagen views (gelijkwaardige ingang) -->
      <section v-if="opgeslagenViews.length" data-testid="kb-views" class="flex flex-col gap-[var(--cd-space-sm)] border-t border-[var(--cd-color-border)] pt-[var(--cd-space-md)]">
        <p class="text-[length:var(--cd-text-sm)] font-semibold">Opgeslagen views</p>
        <ul class="flex flex-col gap-1">
          <li v-for="v in opgeslagenViews" :key="v.id">
            <button
              type="button"
              :data-testid="`kb-view-${v.id}`"
              class="flex w-full items-center gap-2 rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] px-[var(--cd-space-md)] py-2 text-left text-[length:var(--cd-text-sm)] hover:bg-[var(--cd-color-accent)]"
              @click="emit('openView', v)"
            >
              <span class="grow truncate">{{ v.naam }}</span>
              <span v-if="!v.is_eigenaar && v.gedeeld" class="shrink-0 text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">gedeeld door {{ v.maker_naam || '—' }}</span>
            </button>
          </li>
        </ul>
      </section>

      <!-- Lege staat: geen views, niets gezocht -->
      <p v-if="toonLegeStaat" data-testid="kb-leeg" class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
        Zoek een component om te beginnen.
      </p>

      <!-- 4 — Bescheiden ontsnapping: het hele landschap -->
      <div class="border-t border-[var(--cd-color-border)] pt-[var(--cd-space-md)]">
        <button
          type="button"
          data-testid="lk-toon-hele-landschap"
          class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)] hover:text-[var(--cd-color-primary)] hover:underline"
          @click="emit('toonHeleLandschap')"
        >
          Of toon het hele landschap →
        </button>
      </div>
    </div>
  </div>
</template>
