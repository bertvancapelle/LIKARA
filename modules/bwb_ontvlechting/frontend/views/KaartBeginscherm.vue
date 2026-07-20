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
  // Aantal componenten in de actieve set — voedt de "Toon op de kaart"-knop (label + disabled-staat).
  setGrootte: { type: Number, default: 0 },
  // LI046 — mag de gebruiker views beheren (bewerken/verwijderen)? Spiegelt de rol-gate van de parent
  // (medewerker/beheerder). Het viewsbeheer verhuisde hierheen; het leefde eerst in de linkerkolom.
  magViewsBeheren: { type: Boolean, default: false },
})
const emit = defineEmits(['voegComponentenToe', 'openView', 'bewerkView', 'verwijderView', 'toonHeleLandschap', 'sluit'])

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
  // Direct opruimen: zoekterm leeg + dropdown dicht, zodat de gebruiker niet handmatig hoeft te wissen.
  // (resultaten NIET legen — de reeds-toegevoegd-markering op de rij blijft zo correct als de
  // dropdown heropent; de dropdown is nu dicht via zoekOpen.)
  zoekterm.value = ''
  zoekOpen.value = false
}

// ── Via context (vier symmetrische secties) ──────────────────────────────────────
// ZoekSelect (server-side) + @keuze: één keuze → laad de onderliggende componenten → emit.
// Bewust ZoekSelect i.p.v. ZoekMultiSelect: de gebruikerscontext heeft GEEN enkelvoudige id
// (samengestelde sleutel organisatie_id+afdeling) en de "selecteer → laad → emit"-flow past op
// het @keuze-event. De accumulatie/dedup gebeurt in de parent-set (re-selecteren = stil overgeslagen).
const zoekLeveranciers = (params = {}) => api.partijen.lijst({ ...params, aard: 'externe_partij' })
const zoekContracten = (params = {}) => api.contracten.lijst(params)
const zoekEigenaars = (params = {}) => api.partijen.lijst({ ...params, aard: 'organisatie' })

// LI033 — "via organisatie" (inzoom-flow). Kies een organisatie → de VOLLEDIGE set applicaties die zij
// gebruikt uit de ene bron (het grove feit, grof-only incluis) → emit ze; de kaart opent als overzicht
// met de gebruikt-lijnen. Vervangt de oude gemengde (organisatie, afdeling)-paren-picker.
// LI033b — de afdeling-sub-picker is hier vervallen (was dood: additief-subset op het beginscherm).
// Afdeling-inzoom leeft op de afdeling-PartijDetail → "Toon op de landschapskaart".
const zoekOrganisaties = (params = {}) => api.partijen.lijst({ ...params, aard: 'organisatie' })

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
// LI033 — organisatie gekozen: laad haar volledige applicatieset (grove feit, grof-only incluis) en
// emit die (grof-only mee → de kaart markeert 'nog niet verfijnd').
async function kiesOrganisatie(item) {
  const orgId = item?.id
  if (!orgId) return
  try {
    const r = await api.organisatiegebruik.lijstVoorOrganisatie({ organisatie_id: orgId })
    _emitComponenten(r, (c) => ({
      id: c.component_id, naam: c.component_naam, componenttype: c.componenttype,
      grofOnly: c.verfijnd === false, // "nog niet verfijnd" → rustige kaart-markering
    }))
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

defineExpose({ zoek, zoekterm, gekozenType, filterLaag, filterHosting, eigenaarId, resultaten, toonFilters, zoekOpen })
</script>

<template>
  <div
    ref="wortel"
    data-testid="lk-beginscherm"
    class="flex flex-col"
  >
    <!-- Vaste actiebalk bovenaan (niet-scrollend): alleen zichtbaar zodra er ≥1 component is
         gekozen. Geen disabled-staat meer — bij een lege set is de knop simpelweg verborgen. -->
    <div
      v-if="setGrootte > 0"
      class="shrink-0 border-b border-[var(--lk-color-border)] bg-[var(--lk-color-bg)] px-[var(--lk-space-lg)] py-[var(--lk-space-sm)]"
    >
      <button
        type="button"
        data-testid="toon-op-kaart-knop"
        class="w-full rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-2 text-white"
        @click="emit('sluit')"
      >
        Toon {{ setGrootte }} component{{ setGrootte === 1 ? '' : 'en' }} op de kaart
      </button>
    </div>

    <!-- Scrollbare content -->
    <div class="flex-1 overflow-y-auto px-[var(--lk-space-lg)] py-[var(--lk-space-md)]">
    <div class="mx-auto flex w-full max-w-2xl flex-col gap-[var(--lk-space-lg)]">
      <header class="flex flex-col gap-1">
        <h2>Begin je verkenning</h2>
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Zoek een component, kies via leverancier, contract of gebruikerscontext, open een opgeslagen view — of toon het hele landschap.
        </p>
      </header>

      <!-- 1 — Zoekroute (hoofdroute): type-filter + zoekterm → aanvinkbare resultatenlijst -->
      <section class="flex flex-col gap-[var(--lk-space-sm)]">
        <p class="text-[length:var(--lk-text-sm)] font-semibold">Zoek een component</p>
        <div class="relative flex gap-[var(--lk-space-sm)]">
          <select
            v-model="gekozenType"
            data-testid="kb-type"
            aria-label="Componenttype"
            class="lk-veld"
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
            class="lk-veld grow"
            @focus="zoekOpen = true"
            @input="zoekDebounced"
          />

          <!-- Uitklapbare, aanvinkbare resultatenlijst (multi-select) -->
          <ul
            v-show="zoekOpen && (zoekLaden || resultaten.length)"
            data-testid="kb-resultaten"
            class="absolute left-0 right-0 top-full z-10 mt-1 max-h-72 overflow-auto rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] shadow-[var(--lk-shadow-md)]"
          >
            <li v-if="zoekLaden" class="px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Laden…</li>
            <li
              v-for="n in resultaten"
              v-else
              :key="n.id"
              :data-testid="`kb-res-${n.id}`"
              class="px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]"
            >
              <label class="flex cursor-pointer items-center gap-2" :class="isToegevoegd(n.id) ? 'text-[var(--lk-color-text-muted)]' : ''">
                <input
                  type="checkbox"
                  :data-testid="`kb-res-check-${n.id}`"
                  :checked="isToegevoegd(n.id)"
                  :disabled="isToegevoegd(n.id)"
                  @change="voegResultaatToe(n)"
                />
                <span class="grow truncate">{{ n.naam }}</span>
                <span v-if="isToegevoegd(n.id)" class="shrink-0 text-[var(--lk-color-primary)]" title="In de set">✓</span>
              </label>
            </li>
            <li v-if="!zoekLaden && !resultaten.length" class="px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Geen resultaten.</li>
          </ul>
        </div>

        <!-- Filters (weggevouwen): verfijnen dezelfde /componenten-query (AND) -->
        <div>
          <button
            type="button"
            data-testid="kb-filters-toggle"
            class="flex items-center gap-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline"
            :aria-expanded="toonFilters ? 'true' : 'false'"
            @click="toonFilters = !toonFilters"
          >
            + Filters
            <span v-if="filtersActief" data-testid="kb-filters-badge" class="rounded-full bg-[var(--lk-color-primary)] px-1.5 text-[length:var(--lk-text-xs)] text-white">actief</span>
          </button>
          <div v-if="toonFilters" data-testid="kb-filters" class="mt-[var(--lk-space-sm)] flex flex-wrap items-end gap-[var(--lk-space-md)]">
            <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
              <span class="font-semibold">Laag</span>
              <select v-model="filterLaag" data-testid="kb-filter-laag" class="lk-veld" @change="zoek">
                <option value="">alle</option>
                <option v-for="l in LAAG_OPTIES" :key="l" :value="l">{{ humaniseer(l) }}</option>
              </select>
            </label>
            <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
              <span class="font-semibold">Hosting</span>
              <select v-model="filterHosting" data-testid="kb-filter-hosting" class="lk-veld" @change="zoek">
                <option value="">alle</option>
                <option v-for="h in HOSTING_OPTIES" :key="h" :value="h">{{ humaniseer(h) }}</option>
              </select>
            </label>
            <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
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

      <!-- 2 — Via context: vier symmetrische secties -->
      <section class="flex flex-col gap-[var(--lk-space-md)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]">
        <p class="text-[length:var(--lk-text-sm)] font-semibold">Of kies via context</p>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span>Leverancier</span>
          <ZoekSelect :zoek-functie="zoekLeveranciers" :weergave="(p) => p.naam" id-veld="id" placeholder="Zoek leverancier…" testid="kb-leverancier" @keuze="kiesLeverancier" />
        </label>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span>Contract</span>
          <ZoekSelect :zoek-functie="zoekContracten" :weergave="(c) => c.naam" id-veld="id" placeholder="Zoek contract…" testid="kb-contract" @keuze="kiesContract" />
        </label>
        <!-- LI033 — kies een organisatie → de volledige set applicaties die zij gebruikt (grof-only
             incluis); de kaart opent als overzicht met de gebruikt-lijnen. Eén bron, gedeeld met het
             blok. LI033b — afdeling-inzoom leeft op de afdeling-PartijDetail → "Toon op de kaart". -->
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span>Organisatie</span>
          <ZoekSelect :zoek-functie="zoekOrganisaties" :weergave="(p) => p.naam" id-veld="id" placeholder="Zoek organisatie…" testid="kb-organisatie" @keuze="kiesOrganisatie" />
        </label>
        <!-- ADR-043 gate 4 slice 2 — de "Via proces"-ingang is vervallen met de proceslaan (G1);
             de kaart opent op componenten/organisaties en toont de bedrijfsfunctie-laan als verrijking. -->
      </section>

      <!-- 3 — Opgeslagen views (gelijkwaardige ingang) -->
      <section v-if="opgeslagenViews.length" data-testid="kb-views" class="flex flex-col gap-[var(--lk-space-sm)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]">
        <p class="text-[length:var(--lk-text-sm)] font-semibold">Opgeslagen views</p>
        <ul class="flex flex-col gap-1">
          <li
            v-for="v in opgeslagenViews"
            :key="v.id"
            :data-testid="`kb-view-row-${v.id}`"
            class="flex items-center gap-2 rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-2 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)]"
          >
            <button type="button" :data-testid="`kb-view-${v.id}`" class="grow truncate text-left" :title="v.naam" @click="emit('openView', v)">{{ v.naam }}</button>
            <span v-if="!v.is_eigenaar && v.gedeeld" :data-testid="`kb-view-gedeeld-${v.id}`" class="shrink-0 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">gedeeld door {{ v.maker_naam || '—' }}</span>
            <template v-if="v.is_eigenaar && magViewsBeheren">
              <button type="button" class="shrink-0 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)]" :data-testid="`kb-view-bewerk-${v.id}`" aria-label="View bewerken" title="Bewerken" @click="emit('bewerkView', v)">✎</button>
              <button type="button" class="shrink-0 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-danger)]" :data-testid="`kb-view-verwijder-${v.id}`" aria-label="View verwijderen" title="Verwijderen" @click="emit('verwijderView', v)">×</button>
            </template>
          </li>
        </ul>
      </section>

      <!-- Lege staat: geen views, niets gezocht -->
      <p v-if="toonLegeStaat" data-testid="kb-leeg" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
        Zoek een component om te beginnen.
      </p>

      <!-- 4 — Bescheiden ontsnapping: het hele landschap (onderaan de scrollbare content). -->
      <div class="pt-[var(--lk-space-sm)]">
        <button
          type="button"
          data-testid="lk-toon-hele-landschap"
          class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] hover:underline"
          @click="emit('toonHeleLandschap')"
        >
          Of toon het hele landschap →
        </button>
      </div>
    </div>
    </div>
  </div>
</template>
