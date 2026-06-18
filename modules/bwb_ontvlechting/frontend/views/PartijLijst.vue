<script setup>
/**
 * PartijLijst — overzicht van partijen/betrokkenen (ADR-024 slice 2a; vervangt LeverancierLijst).
 *
 * Eén scherm voor alle aarden (externe partij / organisatie / afdeling / persoon) met een
 * aard-filter + aard-kolom. DataTable + server-side sorteerbare keyset-paginering (ADR-017),
 * `zoek`-filter, "Meer laden", detail-link op de naam. Puur registratief — geen lifecycle/status.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { PARTIJ_AARD, label } from '@modules/bwb_ontvlechting/frontend/labels'

const auth = useAuthStore()
const magAanmaken = computed(() => auth.hasRole('medewerker', 'beheerder'))

const AARD_OPTIES = [
  { waarde: '', tekst: 'Alle aarden' },
  { waarde: 'externe_partij', tekst: 'Externe partij' },
  { waarde: 'organisatie', tekst: 'Organisatie' },
  { waarde: 'organisatie_eenheid', tekst: 'Afdeling' },
  { waarde: 'persoon', tekst: 'Persoon' },
]
const aardLabel = (a) => label(PARTIJ_AARD, a)

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

const sortVeld = ref(null)
const sortRichting = ref(null)
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)
const filterZoek = ref('')
const filterAard = ref('')
const heeftFilters = computed(() => !!filterZoek.value.trim() || !!filterAard.value)

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    if (filterZoek.value.trim()) params.zoek = filterZoek.value.trim()
    if (filterAard.value) params.aard = filterAard.value
    const pagina = await api.partijen.lijst(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Er ging iets mis bij het laden van de partijen.'
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

function herfilter() {
  cursor.value = null
  laad({ reset: true })
}

let _zoekTimer = null
function herfilterDebounced() {
  clearTimeout(_zoekTimer)
  _zoekTimer = setTimeout(herfilter, 300)
}
function wisFilters() {
  filterZoek.value = ''
  filterAard.value = ''
  cursor.value = null
  laad({ reset: true })
}

onMounted(() => laad({ reset: true }))
</script>

<template>
  <section aria-labelledby="partijen-titel">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <h1
        id="partijen-titel"
        class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        Partijen
      </h1>
      <router-link
        v-if="magAanmaken"
        :to="{ name: 'partij-nieuw' }"
        data-testid="nieuwe-partij"
        class="ml-auto inline-flex items-center rounded-[var(--cd-radius-btn)] bg-[var(--cd-color-primary)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-white text-[length:var(--cd-text-sm)] font-semibold hover:bg-[#2D6DB5] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
      >
        Nieuwe partij
      </router-link>
    </div>

    <div
      data-testid="filterbalk"
      class="mb-[var(--cd-space-md)] flex flex-wrap items-end gap-[var(--cd-space-md)] rounded-[var(--cd-radius-card)] bg-[var(--cd-color-surface)] p-[var(--cd-space-md)] shadow-[var(--cd-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Aard</span>
        <select
          v-model="filterAard"
          data-testid="filter-aard"
          aria-label="Filter op aard"
          class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          @change="herfilter"
        >
          <option v-for="o in AARD_OPTIES" :key="o.waarde" :value="o.waarde">{{ o.tekst }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Naam</span>
        <input
          v-model="filterZoek"
          type="search"
          maxlength="255"
          data-testid="filter-zoek"
          aria-label="Zoek op partijnaam"
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
      data-testid="partijen-tabel"
      class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="naam" header="Naam" sortable>
        <template #body="{ data }">
          <router-link
            :to="{ name: 'partij-detail', params: { id: data.id } }"
            data-testid="rij-link"
            class="text-[var(--cd-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
        </template>
      </Column>
      <Column header="Aard">
        <template #body="{ data }">
          <span data-testid="rij-aard">{{ aardLabel(data.aard) }}</span>
        </template>
      </Column>
      <Column field="plaats" header="Plaats" sortable>
        <template #body="{ data }">{{ data.plaats || '—' }}</template>
      </Column>
      <Column header="Contactpersoon">
        <template #body="{ data }">{{ data.contactpersoon || '—' }}</template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden && heeftFilters" data-testid="lijst-geen-match">
          Geen partijen komen overeen met de filters.
        </span>
        <span v-else-if="eersteGeladen && !laden" data-testid="lijst-leeg">
          Er zijn nog geen partijen in deze tenant.
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
      <span v-if="laden && items.length" data-testid="lijst-laden" class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]">Laden…</span>
    </div>
  </section>
</template>
