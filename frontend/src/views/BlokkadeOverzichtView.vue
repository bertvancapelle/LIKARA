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
    <div class="flex items-center flex-wrap gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <h1
        id="blokkades-titel"
        class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        Blokkades
      </h1>
      <label class="ml-auto flex items-center gap-[var(--cd-space-sm)] text-[length:var(--cd-text-sm)]">
        <span class="text-[var(--cd-color-text-muted)]">Status</span>
        <select
          v-model="statusFilter"
          data-testid="status-filter"
          aria-label="Filter op blokkade-status"
          class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
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
      class="mb-[var(--cd-space-md)] rounded-[var(--cd-radius-badge)] border border-[var(--cd-color-danger)] bg-[var(--cd-color-danger)]/10 px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-danger)]"
    >
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="blokkades-tabel"
      class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="applicatie_naam" header="Applicatie" sortable>
        <template #body="{ data }">
          <router-link
            :to="{ name: 'applicatie-detail', params: { id: data.applicatie_id } }"
            data-testid="blokkade-app-link"
            class="text-[var(--cd-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          >
            {{ data.applicatie_naam }}
          </router-link>
        </template>
      </Column>
      <Column field="vraag_code" header="Vraag" sortable />
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

    <div class="mt-[var(--cd-space-md)] flex items-center gap-[var(--cd-space-md)]">
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
        class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]"
      >
        Laden…
      </span>
    </div>
  </section>
</template>
