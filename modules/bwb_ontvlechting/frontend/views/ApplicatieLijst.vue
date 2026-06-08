<script setup>
/**
 * ApplicatieLijst — overzicht van applicaties (BWB-ontvlechtingsmodule).
 *
 * DataTable met server-side sorteerbare keyset-paginering (ADR-017): kolommen
 * `sortable`, `@sort` → refetch met `sort`/`order` + **cursor-reset**; "Meer laden"
 * (o.b.v. `volgende_cursor`) blijft binnen de actieve sortering. Lazy-modus zodat
 * de tabel niet zelf client-side sorteert. Lifecycle-status read-only als Tag.
 * Navigatie naar detail via een toetsenbord-toegankelijke link op de naam.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { HOSTINGMODEL, LIFECYCLE, LIFECYCLE_SEVERITY, NIVEAU, label } from '../labels'

const auth = useAuthStore()
const magAanmaken = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

// Sortering — null = server-default (created_at asc), niet expliciet meegestuurd
// (backwards-compatible). PrimeVue gebruikt sortOrder 1/-1; de API asc/desc.
const sortVeld = ref(null)
const sortRichting = ref(null) // 'asc' | 'desc'
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)

// Filters (CD017) — AND-gecombineerd, alle optioneel. Lege selectie = geen filter.
const STATUS_OPTIES = ['concept', 'in_inventarisatie', 'geblokkeerd', 'migratieklaar']
const HOSTING_OPTIES = Object.keys(HOSTINGMODEL)
const filterStatus = ref([]) // array van geselecteerde statussen
const filterHosting = ref('') // '' = alle
const filterEigenaar = ref('')
const filterZoek = ref('')
const heeftFilters = computed(
  () =>
    filterStatus.value.length > 0 ||
    !!filterHosting.value ||
    !!filterEigenaar.value.trim() ||
    !!filterZoek.value.trim(),
)

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    if (filterStatus.value.length) params.status = filterStatus.value
    if (filterHosting.value) params.hostingmodel = filterHosting.value
    if (filterEigenaar.value.trim()) params.eigenaar = filterEigenaar.value.trim()
    if (filterZoek.value.trim()) params.zoek = filterZoek.value.trim()
    const pagina = await api.applicaties.lijst(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Er ging iets mis bij het laden van de applicaties.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

function onSort(event) {
  // Nieuwe sortering → cursor resetten en vanaf pagina 1 opnieuw ophalen.
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

// Elke filterwijziging reset de cursor en haalt vanaf pagina 1 opnieuw op.
function herfilter() {
  cursor.value = null
  laad({ reset: true })
}

// Debounce voor de tekstvelden (geen request per toetsaanslag).
let _zoekTimer = null
function herfilterDebounced() {
  clearTimeout(_zoekTimer)
  _zoekTimer = setTimeout(herfilter, 300)
}

function wisFilters() {
  filterStatus.value = []
  filterHosting.value = ''
  filterEigenaar.value = ''
  filterZoek.value = ''
  herfilter()
}

const hosting = (c) => label(HOSTINGMODEL, c)
const niveau = (c) => label(NIVEAU, c)
const lifecycleLabel = (c) => label(LIFECYCLE, c)
const lifecycleSeverity = (c) => LIFECYCLE_SEVERITY[c] || 'info'

onMounted(() => laad({ reset: true }))
</script>

<template>
  <section aria-labelledby="applicaties-titel">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <h1
        id="applicaties-titel"
        class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        Applicaties
      </h1>
      <router-link
        v-if="magAanmaken"
        :to="{ name: 'applicatie-nieuw' }"
        data-testid="nieuwe-applicatie"
        class="ml-auto inline-flex items-center rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-primary)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-white text-[length:var(--cd-text-sm)] font-semibold hover:bg-[#2D6DB5] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
      >
        Nieuwe applicatie
      </router-link>
    </div>

    <!-- Filterbalk (CD017) — AND-gecombineerd; elke wijziging reset de cursor. -->
    <div
      data-testid="filterbalk"
      class="mb-[var(--cd-space-md)] flex flex-wrap items-end gap-[var(--cd-space-md)] rounded-[var(--cd-radius-card)] bg-[var(--cd-color-surface)] p-[var(--cd-space-md)] shadow-[var(--cd-shadow-sm)]"
    >
      <fieldset class="flex flex-col gap-[var(--cd-space-xs)]">
        <legend class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">
          Status
        </legend>
        <div class="flex flex-wrap gap-[var(--cd-space-md)]">
          <label
            v-for="s in STATUS_OPTIES"
            :key="s"
            class="flex items-center gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]"
          >
            <input
              v-model="filterStatus"
              type="checkbox"
              :value="s"
              :data-testid="`filter-status-${s}`"
              @change="herfilter"
            />
            {{ lifecycleLabel(s) }}
          </label>
        </div>
      </fieldset>

      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Hosting</span>
        <select
          v-model="filterHosting"
          data-testid="filter-hosting"
          aria-label="Filter op hostingmodel"
          class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="h in HOSTING_OPTIES" :key="h" :value="h">{{ hosting(h) }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Eigenaar</span>
        <input
          v-model="filterEigenaar"
          type="search"
          maxlength="120"
          data-testid="filter-eigenaar"
          aria-label="Filter op eigenaar-organisatie"
          placeholder="bevat…"
          class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          @input="herfilterDebounced"
        />
      </label>

      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Naam</span>
        <input
          v-model="filterZoek"
          type="search"
          maxlength="100"
          data-testid="filter-zoek"
          aria-label="Zoek op applicatienaam"
          placeholder="zoeken…"
          class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          @input="herfilterDebounced"
        />
      </label>

      <button
        v-if="heeftFilters"
        type="button"
        data-testid="filters-wissen"
        class="ml-auto rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] px-[var(--cd-space-md)] py-1 text-[length:var(--cd-text-sm)] hover:bg-[var(--cd-color-accent)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
        @click="wisFilters"
      >
        Filters wissen
      </button>
    </div>

    <p
      v-if="fout"
      role="alert"
      data-testid="lijst-fout"
      class="mb-[var(--cd-space-md)] rounded-[var(--cd-radius-badge)] border border-[var(--cd-color-danger)] bg-[var(--cd-color-danger)]/10 px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-danger)]"
    >
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="applicaties-tabel"
      class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="naam" header="Naam" sortable>
        <template #body="{ data }">
          <router-link
            :to="{ name: 'applicatie-detail', params: { id: data.id } }"
            data-testid="rij-link"
            class="text-[var(--cd-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
        </template>
      </Column>
      <Column field="eigenaar_organisatie" header="Eigenaar" sortable />
      <Column header="Hosting" sort-field="hostingmodel" sortable>
        <template #body="{ data }">{{ hosting(data.hostingmodel) }}</template>
      </Column>
      <Column header="Complexiteit" sort-field="complexiteit" sortable>
        <template #body="{ data }">{{ niveau(data.complexiteit) }}</template>
      </Column>
      <Column header="Prioriteit" sort-field="prioriteit" sortable>
        <template #body="{ data }">{{ niveau(data.prioriteit) }}</template>
      </Column>
      <Column header="Status" sort-field="lifecycle_status" sortable>
        <template #body="{ data }">
          <Tag
            :value="lifecycleLabel(data.lifecycle_status)"
            :severity="lifecycleSeverity(data.lifecycle_status)"
          />
        </template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden && heeftFilters" data-testid="lijst-geen-match">
          Geen applicaties komen overeen met de filters.
        </span>
        <span v-else-if="eersteGeladen && !laden" data-testid="lijst-leeg">
          Er zijn nog geen applicaties in deze tenant.
        </span>
        <span v-else data-testid="lijst-laden-leeg">Laden…</span>
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
      <span v-if="laden && items.length" data-testid="lijst-laden" class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]">
        Laden…
      </span>
    </div>
  </section>
</template>
