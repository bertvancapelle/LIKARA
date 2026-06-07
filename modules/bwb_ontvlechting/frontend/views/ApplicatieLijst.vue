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

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
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
        <span v-if="eersteGeladen && !laden" data-testid="lijst-leeg">
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
