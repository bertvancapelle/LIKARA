<script setup>
/**
 * ArchitectuurView — cross-element laagprojectie (ADR-023 Fase F / F-2).
 *
 * Read-only landschapslens over álle element-typen: per element de ArchiMate-laag,
 * het aspect en het element-type, filterbaar op laag/aspect/type. Leunt volledig op
 * `GET /architectuur/elementen` (server-side filters + keyset-paginering). Labels via
 * de bestaande ArchiMate-maps; geen client-side typing-logica.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { api } from '@/api'
import { ARCHIMATE_ASPECT, ARCHIMATE_ELEMENT, ARCHIMATE_LAAG, humaniseer, label } from '@modules/bwb_ontvlechting/frontend/labels'
import ArchitectuurLagenView from './ArchitectuurLagenView.vue'

// Filteropties: lagen + aspecten uit de label-maps; element-typen vast (de ElementType-enum).
const LAAG_OPTIES = Object.keys(ARCHIMATE_LAAG)
const ASPECT_OPTIES = Object.keys(ARCHIMATE_ASPECT)
const TYPE_OPTIES = [
  'component', 'datatype', 'gebruikersgroep', 'contract', 'partij',
  'plateau', 'gap', 'work_package', 'deliverable',
]

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

const filterLaag = ref('')
const filterAspect = ref('')
const filterType = ref('')

// LI025 — weergave-toggle: 'lagen' (visuele bands, default) of 'tabel' (bestaande DataTable).
// localStorage is in sommige (test-)omgevingen niet beschikbaar → guarded.
function _leesWeergave() {
  try { return localStorage.getItem('arch-weergave') || 'lagen' } catch { return 'lagen' }
}
const weergave = ref(_leesWeergave())

// Server-side sortering (ADR-017): sort/order → param + cursor-reset + refetch (B2).
const sortVeld = ref(null)
const sortRichting = ref('asc')
const primeSortOrder = computed(() => (sortVeld.value ? (sortRichting.value === 'asc' ? 1 : -1) : 0))

const laagLabel = (c) => (c ? label(ARCHIMATE_LAAG, c) : '—')
const aspectLabel = (c) => (c ? label(ARCHIMATE_ASPECT, c) : '—')
const elementLabel = (c) => (c ? label(ARCHIMATE_ELEMENT, c) : '—')
const typeLabel = (c) => humaniseer(c)

// Rij-doorklik naar het detail per element-type (B2). Typen zonder eigen detailpagina
// (datatype/gebruikersgroep — die leven als sectie onder een applicatie) krijgen geen link.
const ROUTE_PER_TYPE = {
  component: 'component-detail',
  contract: 'contract-detail',
  partij: 'partij-detail',
  plateau: 'plateau-detail',
  gap: 'gap-detail',
  work_package: 'work-package-detail',
  deliverable: 'deliverable-detail',
}
const elementRoute = (rij) =>
  ROUTE_PER_TYPE[rij.element_type] ? { name: ROUTE_PER_TYPE[rij.element_type], params: { id: rij.id } } : null

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (filterLaag.value) params.laag = filterLaag.value
    if (filterAspect.value) params.aspect = filterAspect.value
    if (filterType.value) params.type = filterType.value
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    const pagina = await api.architectuur.elementen(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van het architectuuroverzicht.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

function herfilter() {
  cursor.value = null
  laad({ reset: true })
}

// Sorteerklik (server-side): zet sort/order, reset de cursor en herlaad vanaf pagina 1.
function onSort(event) {
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

function setWeergave(m) {
  weergave.value = m
  try { localStorage?.setItem?.('arch-weergave', m) } catch { /* localStorage niet beschikbaar */ }
  if (m === 'tabel' && !eersteGeladen.value) laad({ reset: true })
}

// De tabel laadt alleen wanneer die actief is; de lagenweergave laadt zijn eigen (volledige) set.
onMounted(() => { if (weergave.value === 'tabel') laad({ reset: true }) })
</script>

<template>
  <section aria-labelledby="arch-titel">
    <h1
      id="arch-titel"
      class="mb-[var(--lk-space-md)] text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]"
    >
      Architectuur — lagen
    </h1>

    <!-- LI025 — weergave-toggle Lagen/Tabel (default Lagen). -->
    <div class="mb-[var(--lk-space-md)] flex w-fit gap-1 rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-accent)] p-1">
      <button v-for="m in ['lagen', 'tabel']" :key="m" type="button" :data-testid="`arch-weergave-${m}`" :aria-pressed="weergave === m" :class="['rounded-[var(--lk-radius-btn)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)]', weergave === m ? 'bg-[var(--lk-color-primary)] text-white' : '']" @click="setWeergave(m)">{{ m === 'lagen' ? 'Lagen' : 'Tabel' }}</button>
    </div>

    <ArchitectuurLagenView v-if="weergave === 'lagen'" />
    <template v-else>
    <div
      data-testid="arch-filterbalk"
      class="mb-[var(--lk-space-md)] flex flex-wrap items-end gap-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Laag</span>
        <select v-model="filterLaag" data-testid="arch-filter-laag" aria-label="Filter op ArchiMate-laag" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="l in LAAG_OPTIES" :key="l" :value="l">{{ laagLabel(l) }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Aspect</span>
        <select v-model="filterAspect" data-testid="arch-filter-aspect" aria-label="Filter op ArchiMate-aspect" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="a in ASPECT_OPTIES" :key="a" :value="a">{{ aspectLabel(a) }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Type</span>
        <select v-model="filterType" data-testid="arch-filter-type" aria-label="Filter op element-type" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="t in TYPE_OPTIES" :key="t" :value="t">{{ typeLabel(t) }}</option>
        </select>
      </label>
    </div>

    <p v-if="fout" role="alert" data-testid="arch-fout" class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      data-testid="arch-tabel"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]"
      @sort="onSort"
    >
      <Column header="Naam" sort-field="naam" sortable>
        <template #body="{ data }">
          <router-link
            v-if="elementRoute(data)"
            :to="elementRoute(data)"
            :data-testid="`arch-link-${data.id}`"
            class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
          <span v-else class="font-medium">{{ data.naam }}</span>
          <span v-if="data.naam_secundair" class="block text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
            {{ data.naam_secundair }}
          </span>
        </template>
      </Column>
      <Column header="Type" sort-field="type" sortable>
        <template #body="{ data }">{{ typeLabel(data.element_type) }}</template>
      </Column>
      <Column header="Laag" sort-field="laag" sortable>
        <template #body="{ data }"><Tag :value="laagLabel(data.laag)" severity="info" /></template>
      </Column>
      <Column header="Aspect" sort-field="aspect" sortable>
        <template #body="{ data }">{{ aspectLabel(data.aspect) }}</template>
      </Column>
      <Column header="Soort" sort-field="soort" sortable>
        <template #body="{ data }">{{ elementLabel(data.archimate_element) }}</template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden" data-testid="arch-leeg">
          Geen elementen voor de gekozen filters.
        </span>
        <span v-else>Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--lk-space-md)]">
      <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="arch-meer-laden" :disabled="laden" @click="laad()" />
    </div>
    </template>
  </section>
</template>
