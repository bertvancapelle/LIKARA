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
import { detailRoute } from '@/detailIngang'
import { useAuthStore } from '@/store/auth'
import { useLijstStaat } from '@/composables/useLijstStaat'
import { api } from '@/api'
import { PARTIJ_AARD, label } from '@modules/bwb_ontvlechting/frontend/labels'
import IdentiteitLabel from '@modules/bwb_ontvlechting/frontend/views/IdentiteitLabel.vue'

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

// Lijststaat behouden bij terugnavigeren/F5 (lk-state-patroon; zie useLijstStaat).
// Gevalideerd herstel: onbekende waarden vallen stil terug op de default.
const SORTEERBARE_VELDEN = ['naam', 'aard', 'plaats']
const _tekst = (w) => typeof w === 'string'
const { herstel: herstelLijstStaat } = useLijstStaat(
  'partij-lijst',
  { filterAard, filterZoek, sortVeld, sortRichting },
  {
    valideer: {
      filterAard: (w) => AARD_OPTIES.some((o) => o.waarde === w),
      filterZoek: _tekst,
      sortVeld: (w) => w === null || SORTEERBARE_VELDEN.includes(w),
      sortRichting: (w) => w === null || w === 'asc' || w === 'desc',
    },
  },
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
    if (filterZoek.value.trim()) params.zoek = filterZoek.value.trim()
    if (filterAard.value) params.aard = filterAard.value
    const pagina = await api.partijen.lijst(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van de partijen.'
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

onMounted(() => {
  // Geen doorklik-query op Partijen → de bewaarde staat mag altijd terug.
  herstelLijstStaat()
  laad({ reset: true })
})
</script>

<template>
  <section aria-labelledby="partijen-titel">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-md)]">
      <h1
        id="partijen-titel"
        class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]"
      >
        Partijen
      </h1>
      <router-link
        v-if="magAanmaken"
        :to="{ name: 'partij-nieuw' }"
        data-testid="nieuwe-partij"
        class="ml-auto inline-flex items-center rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-white text-[length:var(--lk-text-sm)] font-semibold hover:bg-[#2D6DB5] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
      >
        Nieuwe partij
      </router-link>
    </div>

    <div
      data-testid="filterbalk"
      class="mb-[var(--lk-space-md)] flex flex-wrap items-end gap-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Aard</span>
        <select
          v-model="filterAard"
          data-testid="filter-aard"
          aria-label="Filter op aard"
          class="lk-veld"
          @change="herfilter"
        >
          <option v-for="o in AARD_OPTIES" :key="o.waarde" :value="o.waarde">{{ o.tekst }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Naam</span>
        <input
          v-model="filterZoek"
          type="search"
          maxlength="255"
          data-testid="filter-zoek"
          aria-label="Zoek op partijnaam"
          placeholder="zoeken…"
          class="lk-veld"
          @input="herfilterDebounced"
        />
      </label>
      <button
        v-if="heeftFilters"
        type="button"
        data-testid="filters-wissen"
        class="ml-auto rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
        @click="wisFilters"
      >
        Filters wissen
      </button>
    </div>

    <p
      v-if="fout"
      role="alert"
      data-testid="lijst-fout"
      class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]"
    >
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="partijen-tabel"
      class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="naam" header="Naam" sortable>
        <template #body="{ data }">
          <router-link
            :to="detailRoute('partij', data.id)"
            data-testid="rij-link"
            class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            <!-- LI040: afdeling/persoon toont zijn volledige identiteit (cross-org lijst);
                 het deel na de naam gedempt — nooit ingekort. -->
            <IdentiteitLabel :naam="data.naam" :afdeling="data.afdeling_naam" :organisatie="data.organisatie_naam" />
          </router-link>
        </template>
      </Column>
      <Column field="aard" header="Aard" sortable>
        <template #body="{ data }">
          <span data-testid="rij-aard">{{ aardLabel(data.aard) }}</span>
        </template>
      </Column>
      <Column field="plaats" header="Plaats" sortable>
        <template #body="{ data }">{{ data.plaats || '—' }}</template>
      </Column>
      <Column header="Aanspreekpunt">
        <template #body="{ data }">
          <router-link
            v-if="data.contactpersoon_id"
            :to="detailRoute('partij', data.contactpersoon_id)"
            data-testid="rij-contactpersoon-link"
            class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >{{ data.contactpersoon_naam || '—' }}</router-link>
          <span v-else class="text-[var(--lk-color-text-muted)]">—</span>
        </template>
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

    <div class="mt-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <Button
        v-if="cursor"
        label="Meer laden"
        severity="secondary"
        data-testid="meer-laden"
        :disabled="laden"
        @click="laad()"
      />
      <span v-if="laden && items.length" data-testid="lijst-laden" class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">Laden…</span>
    </div>
  </section>
</template>
