<script setup>
/**
 * BlokkadeOverzichtView — tenant-breed blokkadesoverzicht (CD016, #12).
 *
 * Platform-view die module-data (BWB-blokkades) consumeert — zelfde precedent als
 * DashboardView; presentatie (labels/severity) via de cross-root-barrel
 * `@modules/bwb_ontvlechting/frontend/labels`. Server-side sorteerbaar (ADR-017):
 * DataTable in lazy-modus, `@sort` → sort/order + cursor-reset + refetch; "Meer
 * laden" blijft binnen de actieve sortering/filter. Statusfilter reset eveneens de
 * cursor. Geen client-side sorteren of filteren.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { api } from '@/api'
import { BLOKKADE_STATUS, BLOKKADE_STATUS_SEVERITY, label } from '@modules/bwb_ontvlechting/frontend/labels'

const route = useRoute()

const STATUS_OPTIES = [
  { waarde: 'actief', tekst: 'Actief (open + in behandeling)' },
  { waarde: 'open', tekst: 'Open' },
  { waarde: 'in_behandeling', tekst: 'In behandeling' },
  { waarde: 'opgelost', tekst: 'Opgelost' },
  { waarde: 'alle', tekst: 'Alle' },
]
const _geldigeStatus = STATUS_OPTIES.map((o) => o.waarde)

const statusFilter = ref(
  _geldigeStatus.includes(route.query.status) ? route.query.status : 'actief',
)
// Default-sortering reflecteert de server-default (applicatie_naam asc).
const sortVeld = ref('applicatie_naam')
const sortRichting = ref('asc')
const primeSortOrder = computed(() => (sortRichting.value === 'asc' ? 1 : -1))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const pagina = await api.blokkades.overzicht({
      limit: 25,
      after: reset ? undefined : cursor.value,
      status: statusFilter.value,
      sort: sortVeld.value,
      order: sortRichting.value,
    })
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Er ging iets mis bij het laden van de blokkades.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

function onSort(event) {
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

function onFilterWijziging() {
  cursor.value = null
  laad({ reset: true })
}

// ADR-024-vervolg: categorie-nr uit de vraag-code (bv. "2.7" → 2) voor de deep-link naar
// het juiste checklist-categorie-tabblad; analoog aan BlokkadeSectie.categorieVan.
function categorieVan(code) {
  const nr = Number.parseInt(String(code ?? '').split('.')[0], 10)
  return Number.isInteger(nr) ? nr : undefined
}

// ADR-024-vervolg: type-onafhankelijke doorklik. Applicatie → de rijke applicatie-detail
// (met checklist-tab/categorie); elk ander checklist-dragend type → het generieke
// component-detail (tabloos). `markeer` markeert de veroorzakende checklistvraag.
function detailDoel(data, { markeer = false } = {}) {
  const isApplicatie = data.componenttype === 'applicatie'
  const query = {}
  if (markeer) {
    query.markeer = data.vraag_code
    if (isApplicatie) {
      query.tab = 'checklist'
      query.cat = categorieVan(data.vraag_code)
    }
  }
  return {
    // LI059 Slice 4 — één detailscherm; de checklist-deep-link (tab/cat) werkt op ComponentDetail.
    name: 'component-detail',
    params: { id: data.component_id },
    query,
  }
}

const statusLabel = (c) => label(BLOKKADE_STATUS, c)
const statusSeverity = (c) => BLOKKADE_STATUS_SEVERITY[c] || 'info'

function formatDatum(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }).format(d)
}

onMounted(() => laad({ reset: true }))
</script>

<template>
  <section aria-labelledby="blokkades-titel">
    <div class="flex items-center flex-wrap gap-[var(--lk-space-md)] mb-[var(--lk-space-md)]">
      <h1
        id="blokkades-titel"
        class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]"
      >
        Blokkades
      </h1>
      <label class="ml-auto flex items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
        <span class="text-[var(--lk-color-text-muted)]">Status</span>
        <select
          v-model="statusFilter"
          data-testid="status-filter"
          aria-label="Filter op blokkade-status"
          class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          @change="onFilterWijziging"
        >
          <option v-for="o in STATUS_OPTIES" :key="o.waarde" :value="o.waarde">{{ o.tekst }}</option>
        </select>
      </label>
    </div>

    <p
      v-if="fout"
      role="alert"
      data-testid="overzicht-fout"
      class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]"
    >
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="blokkades-tabel"
      class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="applicatie_naam" header="Component" sortable>
        <template #body="{ data }">
          <router-link
            :to="detailDoel(data)"
            data-testid="blokkade-app-link"
            class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            {{ data.applicatie_naam }}
          </router-link>
          <span data-testid="blokkade-type" class="ml-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
            {{ data.componenttype_label }}
          </span>
        </template>
      </Column>
      <Column field="vraag_code" header="Vraag" sortable>
        <template #body="{ data }">
          <router-link
            :to="detailDoel(data, { markeer: true })"
            data-testid="blokkade-vraag-link"
            class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            {{ data.vraag_code }}
          </router-link>
        </template>
      </Column>
      <Column header="Status" sort-field="status" sortable>
        <template #body="{ data }">
          <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" />
        </template>
      </Column>
      <Column header="Toelichting" sort-field="toelichting" sortable>
        <template #body="{ data }">
          <span class="block max-w-[24ch] truncate" :title="data.toelichting || ''">
            {{ data.toelichting || '—' }}
          </span>
        </template>
      </Column>
      <Column header="Eigenaar" sort-field="eigenaar" sortable>
        <template #body="{ data }">{{ data.eigenaar || '—' }}</template>
      </Column>
      <Column header="Opgelost op" sort-field="opgelost_op" sortable>
        <template #body="{ data }">{{ formatDatum(data.opgelost_op) }}</template>
      </Column>
      <Column header="Gewijzigd" sort-field="gewijzigd_op" sortable>
        <template #body="{ data }">{{ formatDatum(data.gewijzigd_op) }}</template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden" data-testid="overzicht-leeg">
          Geen blokkades voor de gekozen status.
        </span>
        <span v-else data-testid="overzicht-laden-leeg">Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <Button
        v-if="cursor"
        label="Meer laden"
        severity="secondary"
        data-testid="meer-laden"
        :disabled="laden"
        @click="laad()"
      />
      <span
        v-if="laden && items.length"
        data-testid="overzicht-laden"
        class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]"
      >
        Laden…
      </span>
    </div>
  </section>
</template>
