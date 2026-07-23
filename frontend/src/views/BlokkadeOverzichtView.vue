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
import { useLijstStaat } from '@/composables/useLijstStaat'
import { api } from '@/api'
import { detailRoute } from '@/detailIngang'
import { BLOKKADE_STATUS, BLOKKADE_STATUS_SEVERITY, label } from '@modules/bwb_ontvlechting/frontend/labels'
import LijstKop from '@/components/LijstKop.vue'

const route = useRoute()

const STATUS_OPTIES = [
  { waarde: 'actief', tekst: 'Actief (open + in behandeling)' },
  { waarde: 'open', tekst: 'Open' },
  { waarde: 'in_behandeling', tekst: 'In behandeling' },
  { waarde: 'opgelost', tekst: 'Opgelost' },
  { waarde: 'alle', tekst: 'Alle' },
]
const _geldigeStatus = STATUS_OPTIES.map((o) => o.waarde)

// Doorklik-query (dashboard → ?status=…): wint van de bewaarde lijststaat (kaart-lijn).
const _queryStatus = _geldigeStatus.includes(route.query.status) ? route.query.status : null
const statusFilter = ref(_queryStatus ?? 'actief')
// Default-sortering reflecteert de server-default (applicatie_naam asc).
const sortVeld = ref('applicatie_naam')
const sortRichting = ref('asc')
const primeSortOrder = computed(() => (sortRichting.value === 'asc' ? 1 : -1))

// Lijststaat behouden bij terugnavigeren/F5 (lk-state-patroon; zie useLijstStaat).
const SORTEERBARE_VELDEN = ['applicatie_naam', 'categorie_volgorde', 'status', 'toelichting', 'verantwoordelijke_naam', 'opgelost_op', 'gewijzigd_op']
const { herstel: herstelLijstStaat } = useLijstStaat(
  'blokkades',
  { statusFilter, sortVeld, sortRichting },
  {
    valideer: {
      statusFilter: (w) => _geldigeStatus.includes(w),
      sortVeld: (w) => SORTEERBARE_VELDEN.includes(w),
      sortRichting: (w) => w === 'asc' || w === 'desc',
    },
  },
)

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
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van de blokkades.'
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

// ADR-024-vervolg: type-onafhankelijke doorklik. Applicatie → de rijke applicatie-detail
// (met checklist-tab/categorie); elk ander checklist-dragend type → het generieke
// component-detail (tabloos). `markeer` markeert de veroorzakende checklistvraag.
function detailDoel(data, { markeer = false } = {}) {
  const isApplicatie = data.componenttype === 'applicatie'
  // LI046 — via de gedeelde ingang; de aanleiding (markeer/tab/cat) vertaalt naar exact
  // dezelfde query als voorheen (LI059 Slice 4: de checklist-deep-link werkt op ComponentDetail).
  // LI050: de categorie komt uit de blokkade-read (`categorie_id`, via de vraag zelf) —
  // nooit meer uit de code-prefix (die breekt stil zodra volgorde en code uiteenlopen).
  const aanleiding = markeer
    ? {
        markeer: data.vraag_code,
        ...(isApplicatie && data.categorie_id ? { tab: 'checklist', cat: data.categorie_id } : {}),
      }
    : null
  return detailRoute('component', data.component_id, aanleiding)
}

const statusLabel = (c) => label(BLOKKADE_STATUS, c)
const statusSeverity = (c) => BLOKKADE_STATUS_SEVERITY[c] || 'info'

function formatDatum(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }).format(d)
}

onMounted(() => {
  // Precedentie: doorklik-query > bewaarde staat > kale defaults (query vervangt de
  // bewaarde staat volledig — geen oude sortering onder een aangeklikte selectie).
  if (!_queryStatus) herstelLijstStaat()
  laad({ reset: true })
})
</script>

<template>
  <section aria-labelledby="blokkades-titel">
    <!-- LI048 snede 2 — de gedeelde kop. Het statusfilter stond al in de kop-rij en blijft
         daar: het bepaalt WELKE blokkades je ziet, en dat is precies wat in de kop hoort. Het
         gaat naar het filter-slot, dus het staat op dezelfde plek als de Filter-knop elders. -->
    <LijstKop titel="Blokkades" titel-id="blokkades-titel">
      <template #filter>
        <label class="flex items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
          <span class="text-[var(--lk-color-text-muted)]">Status</span>
          <select
            v-model="statusFilter"
            data-testid="status-filter"
            aria-label="Filter op blokkade-status"
            class="lk-veld"
            @change="onFilterWijziging"
          >
            <option v-for="o in STATUS_OPTIES" :key="o.waarde" :value="o.waarde">{{ o.tekst }}</option>
          </select>
        </label>
      </template>
    </LijstKop>

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
      <!-- LI050 (W4): de kolom toont de vraagTEKST; sorteren gaat op de categorie-volgorde
           (de code is intern: hij blijft het markeer-anker in de deeplink). -->
      <Column field="vraag" header="Vraag" sort-field="categorie_volgorde" sortable>
        <template #body="{ data }">
          <router-link
            :to="detailDoel(data, { markeer: true })"
            data-testid="blokkade-vraag-link"
            class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            {{ data.vraag }}
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
      <!-- ADR-037: afgeleide verantwoordelijke van het antwoord (read-only; "persoon — afdeling"). -->
      <Column header="Verantwoordelijke" sort-field="verantwoordelijke_naam" sortable>
        <template #body="{ data }">
          <span v-if="data.verantwoordelijke_naam">
            {{ data.verantwoordelijke_naam }}<template v-if="data.verantwoordelijke_afdeling"> — {{ data.verantwoordelijke_afdeling }}</template>
          </span>
          <span v-else>—</span>
        </template>
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
