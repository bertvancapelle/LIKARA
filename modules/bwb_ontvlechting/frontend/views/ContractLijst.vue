<script setup>
/**
 * ContractLijst — overzicht van contracten (ADR-020 contractregister).
 *
 * DataTable + keyset-paginering (ADR-017, v2n); filters leverancier + contracttype +
 * dekking + kostenmodel + `zoek` (AND-gecombineerd, CD041). Type als Tag.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { useLijstStaat } from '@/composables/useLijstStaat'
import { api } from '@/api'
import { CONTRACTTYPE, CONTRACTTYPE_SEVERITY, label } from '../labels'

const auth = useAuthStore()
const magAanmaken = computed(() => auth.hasRole('medewerker', 'beheerder'))

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

// Filter-bronnen (eenmalig geladen).
const leveranciers = ref([])
const dekkingOpties = ref([])
const kostenmodelOpties = ref([])
const TYPE_OPTIES = Object.keys(CONTRACTTYPE)

const filterLeverancier = ref('')
const filterType = ref('')
const filterDekking = ref('')
const filterKostenmodel = ref('')
const filterZoek = ref('')
const heeftFilters = computed(
  () =>
    !!filterLeverancier.value ||
    !!filterType.value ||
    !!filterDekking.value ||
    !!filterKostenmodel.value ||
    !!filterZoek.value.trim(),
)

// Lijststaat behouden bij terugnavigeren/F5 (lk-state-patroon; zie useLijstStaat).
// Gevalideerd herstel: onbekende waarden vallen stil terug op de default; bron-
// gedreven sleutels (leverancier/dekking/kostenmodel) worden ná laadBronnen geprund.
const SORTEERBARE_VELDEN = ['contractnaam', 'begindatum', 'einddatum']
const _tekst = (w) => typeof w === 'string'
const { herstel: herstelLijstStaat } = useLijstStaat(
  'contract-lijst',
  { filterLeverancier, filterType, filterDekking, filterKostenmodel, filterZoek, sortVeld, sortRichting },
  {
    valideer: {
      filterLeverancier: _tekst,
      filterType: (w) => w === '' || TYPE_OPTIES.includes(w),
      filterDekking: _tekst,
      filterKostenmodel: _tekst,
      filterZoek: _tekst,
      sortVeld: (w) => w === null || SORTEERBARE_VELDEN.includes(w),
      sortRichting: (w) => w === null || w === 'asc' || w === 'desc',
    },
  },
)

// Bron-gevalideerd herstel: een bewaarde waarde die niet (meer) in de geladen bronnen
// bestaat valt stil terug op de default (nooit een onzichtbaar actief filter).
// Alleen prunen als de bron daadwerkelijk geladen is (laadBronnen faalt stil).
function _pruneTegenBronnen() {
  if (leveranciers.value.length && filterLeverancier.value && !leveranciers.value.some((l) => l.id === filterLeverancier.value)) filterLeverancier.value = ''
  if (dekkingOpties.value.length && filterDekking.value && !dekkingOpties.value.some((o) => o.optie_sleutel === filterDekking.value)) filterDekking.value = ''
  if (kostenmodelOpties.value.length && filterKostenmodel.value && !kostenmodelOpties.value.some((o) => o.optie_sleutel === filterKostenmodel.value)) filterKostenmodel.value = ''
}

async function laadBronnen() {
  try {
    const [p, opties] = await Promise.all([
      api.leveranciers.lijst({ limit: 100 }),
      api.contractconfig.opties(),
    ])
    leveranciers.value = p.items
    dekkingOpties.value = opties.dekking || []
    kostenmodelOpties.value = opties.kostenmodel || []
  } catch {
    /* filterbronnen falen stil; de lijst zelf toont eigen foutstatus */
  }
}

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    if (filterLeverancier.value) params.leverancierId = filterLeverancier.value
    if (filterType.value) params.contracttype = filterType.value
    if (filterDekking.value) params.dekking = filterDekking.value
    if (filterKostenmodel.value) params.kostenmodel = filterKostenmodel.value
    if (filterZoek.value.trim()) params.zoek = filterZoek.value.trim()
    const pagina = await api.contracten.lijst(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van de contracten.'
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
  filterLeverancier.value = ''
  filterType.value = ''
  filterDekking.value = ''
  filterKostenmodel.value = ''
  filterZoek.value = ''
  herfilter()
}

const typeLabel = (c) => label(CONTRACTTYPE, c)
const typeSeverity = (c) => CONTRACTTYPE_SEVERITY[c] || 'info'

onMounted(async () => {
  // Geen doorklik-query op Contracten → de bewaarde staat mag altijd terug.
  const hersteld = herstelLijstStaat()
  await laadBronnen()
  if (hersteld) _pruneTegenBronnen()
  await laad({ reset: true })
})
</script>

<template>
  <section aria-labelledby="contracten-titel">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-md)]">
      <h1 id="contracten-titel" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
        Contracten
      </h1>
      <router-link
        v-if="magAanmaken"
        :to="{ name: 'contract-nieuw' }"
        data-testid="nieuw-contract"
        class="ml-auto inline-flex items-center rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-white text-[length:var(--lk-text-sm)] font-semibold hover:bg-[#2D6DB5] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
      >
        Nieuw contract
      </router-link>
    </div>

    <div
      data-testid="filterbalk"
      class="mb-[var(--lk-space-md)] flex flex-wrap items-end gap-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Leverancier</span>
        <select v-model="filterLeverancier" data-testid="filter-leverancier" aria-label="Filter op leverancier" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="l in leveranciers" :key="l.id" :value="l.id">{{ l.naam }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Type</span>
        <select v-model="filterType" data-testid="filter-type" aria-label="Filter op contracttype" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="t in TYPE_OPTIES" :key="t" :value="t">{{ typeLabel(t) }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Dekking</span>
        <select v-model="filterDekking" data-testid="filter-dekking" aria-label="Filter op dekking" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="o in dekkingOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Kostenmodel</span>
        <select v-model="filterKostenmodel" data-testid="filter-kostenmodel" aria-label="Filter op kostenmodel" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="o in kostenmodelOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Naam</span>
        <input v-model="filterZoek" type="search" maxlength="255" data-testid="filter-zoek" aria-label="Zoek op contractnaam" placeholder="zoeken…" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1" @input="herfilterDebounced" />
      </label>
      <button v-if="heeftFilters" type="button" data-testid="filters-wissen" class="ml-auto rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)]" @click="wisFilters">
        Filters wissen
      </button>
    </div>

    <p v-if="fout" role="alert" data-testid="lijst-fout" class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="contracten-tabel"
      class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="contractnaam" header="Contractnaam" sortable>
        <template #body="{ data }">
          <router-link :to="{ name: 'contract-detail', params: { id: data.id } }" data-testid="rij-link" class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]">
            {{ data.contractnaam }}
          </router-link>
        </template>
      </Column>
      <Column header="Leverancier"><template #body="{ data }">{{ data.leverancier_naam }}</template></Column>
      <Column header="Type"><template #body="{ data }"><Tag :value="typeLabel(data.contracttype)" :severity="typeSeverity(data.contracttype)" /></template></Column>
      <Column field="begindatum" header="Begindatum" sortable><template #body="{ data }">{{ data.begindatum || '—' }}</template></Column>
      <Column field="einddatum" header="Einddatum" sortable><template #body="{ data }">{{ data.einddatum || '—' }}</template></Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden && heeftFilters" data-testid="lijst-geen-match">Geen contracten komen overeen met de filters.</span>
        <span v-else-if="eersteGeladen && !laden" data-testid="lijst-leeg">Er zijn nog geen contracten in deze tenant.</span>
        <span v-else data-testid="lijst-laden-leeg">Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="meer-laden" :disabled="laden" @click="laad()" />
      <span v-if="laden && items.length" data-testid="lijst-laden" class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">Laden…</span>
    </div>
  </section>
</template>
