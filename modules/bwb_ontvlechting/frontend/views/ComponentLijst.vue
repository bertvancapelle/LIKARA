<script setup>
/**
 * ComponentLijst — het verenigde werkscherm (ADR-021 W1 / CD054b). Eén ingang voor
 * de hele technische laag: applicatie-subtypen én kale infra (database, fileshare, …).
 *
 * Vaste kolommenset (voorspelbaar scherm): Naam · Type · Eigenaar · Hosting ·
 * Complexiteit · Prioriteit · Status — besturingsvelden tonen "—" voor typen zonder
 * beoordeling. Filterbalk gespiegeld aan de oude Applicaties-lijst: Status-checkboxes,
 * Type-select (catalogus), Hosting, Eigenaar-bevat, Naam-zoek. Keyset-"Meer laden".
 * Subtype-rijen linken naar ApplicatieDetail (rijk detail, één waarheid); overige naar
 * ComponentDetail. Een `?type=`-query (bv. via de /applicaties-redirect) preselecteert
 * het typefilter.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { useRoute, useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'
import {
  ARCHIMATE_ELEMENT,
  ARCHIMATE_LAAG,
  HOSTINGMODEL,
  LIFECYCLE,
  LIFECYCLE_SEVERITY,
  NIVEAU,
  label,
} from '../labels'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const magAanmaken = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

// Filters — gespiegeld aan de Applicaties-lijst (CD017), AND-gecombineerd.
const STATUS_OPTIES = ['concept', 'in_inventarisatie', 'geblokkeerd', 'migratieklaar']
const HOSTING_OPTIES = Object.keys(HOSTINGMODEL)
const typeOpties = ref([]) // [{ optie_sleutel, label, laag, archimate_element }]
const filterStatus = ref([])
const filterType = ref('') // '' = alle; kan via ?type= worden voorgezet
const filterLaag = ref('') // ADR-023 Fase C: '' = alle ArchiMate-lagen
const filterHosting = ref('')
// UX-B6-b — eigenaar-filter is een organisatie-keuze (FK) i.p.v. vrije tekst.
const filterEigenaarId = ref(null)
const filterZoek = ref('')
// ADR-027 slice 3 — dashboard-doorklik-filters (geen dropdown; uit de route-query). Een
// indicator-chip laat ze zien + wissen. `afwijking` impliceert server-side `klaarverklaring=klaar`.
const filterKlaarverklaring = ref('') // '' | 'klaar'
const filterAfwijking = ref(false)
function wisKlaarverklaringFilter() {
  filterKlaarverklaring.value = ''
  filterAfwijking.value = false
  laad({ reset: true })
}

// Organisatie-keuze (filter): server-side zoeken, beperkt tot aard=organisatie.
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })

// Server-side sortering (ADR-017) — null = server-default (created_at asc), niet
// meegestuurd. Spiegelt BlokkadeOverzichtView: @sort → sort/order + cursor-reset + refetch.
const sortVeld = ref(null)
const sortRichting = ref(null) // 'asc' | 'desc'
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)
// ArchiMate-laag-filteropties afgeleid uit de catalogus-typing (distinct lagen).
const laagOpties = computed(() => {
  const seen = new Map()
  for (const o of typeOpties.value) {
    if (o.laag && !seen.has(o.laag)) seen.set(o.laag, label(ARCHIMATE_LAAG, o.laag))
  }
  return [...seen.entries()].map(([waarde, tekst]) => ({ waarde, label: tekst }))
})
const heeftFilters = computed(
  () =>
    filterStatus.value.length > 0 ||
    !!filterType.value ||
    !!filterLaag.value ||
    !!filterHosting.value ||
    !!filterEigenaarId.value ||
    !!filterZoek.value.trim(),
)

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (filterStatus.value.length) params.status = filterStatus.value
    if (filterType.value) params.componenttype = filterType.value
    if (filterLaag.value) params.laag = filterLaag.value
    if (filterHosting.value) params.hostingmodel = filterHosting.value
    if (filterEigenaarId.value) params.eigenaar_organisatie_id = filterEigenaarId.value
    if (filterZoek.value.trim()) params.zoek = filterZoek.value.trim()
    if (filterAfwijking.value) params.afwijking = 1
    else if (filterKlaarverklaring.value) params.klaarverklaring = filterKlaarverklaring.value
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    const pagina = await api.componenten.lijst(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Er ging iets mis bij het laden van de componenten.'
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
  filterStatus.value = []
  filterType.value = ''
  filterLaag.value = ''
  filterHosting.value = ''
  filterEigenaarId.value = null
  filterZoek.value = ''
  herfilter()
}

function rijRoute(rij) {
  return rij.heeft_applicatie_subtype
    ? { name: 'applicatie-detail', params: { id: rij.id } }
    : { name: 'component-detail', params: { id: rij.id } }
}

const hosting = (c) => label(HOSTINGMODEL, c)
const niveau = (c) => (c ? label(NIVEAU, c) : '—')
const laagLabel = (c) => (c ? label(ARCHIMATE_LAAG, c) : '—')
const elementLabel = (c) => (c ? label(ARCHIMATE_ELEMENT, c) : '')
const lifecycleLabel = (c) => label(LIFECYCLE, c)
const lifecycleSeverity = (c) => LIFECYCLE_SEVERITY[c] || 'info'

onMounted(async () => {
  const q = String(route.query.type ?? '')
  if (q) filterType.value = q
  // Statusfilter via de URL voorzetten (dashboard-doorklik), zelfde patroon als ?type=.
  // Accepteert één of meerdere `status`-params; alleen geldige lifecycle-statussen.
  const statusQ = route.query.status
  const statussen = (Array.isArray(statusQ) ? statusQ : statusQ != null ? [statusQ] : [])
    .map(String)
    .filter((s) => STATUS_OPTIES.includes(s))
  if (statussen.length) filterStatus.value = statussen
  // ADR-027 slice 3 — klaarverklaring-doorklik vanaf het dashboard.
  if (String(route.query.afwijking ?? '') === '1') filterAfwijking.value = true
  else if (String(route.query.klaarverklaring ?? '') === 'klaar') filterKlaarverklaring.value = 'klaar'
  try {
    typeOpties.value = (await api.componenten.opties()).componenttype || []
  } catch {
    /* filterlijst optioneel — het overzicht laadt sowieso */
  }
  laad({ reset: true })
})
</script>

<template>
  <section aria-labelledby="componenten-titel">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <h1
        id="componenten-titel"
        class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        Componenten
      </h1>
      <Button
        v-if="magAanmaken"
        label="Nieuw component"
        data-testid="nieuw-component"
        class="ml-auto"
        @click="router.push({ name: 'component-nieuw' })"
      />
    </div>

    <!-- Filterbalk (CD017) — AND-gecombineerd; elke wijziging reset de cursor. -->
    <div
      data-testid="filterbalk"
      class="mb-[var(--cd-space-md)] flex flex-wrap items-end gap-[var(--cd-space-md)] rounded-[var(--cd-radius-card)] bg-[var(--cd-color-surface)] p-[var(--cd-space-md)] shadow-[var(--cd-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Status</span>
        <!-- Multi-select dropdown (zelfde stijl als Type/Laag/Hosting); meervoudige
             selectie behouden (filterStatus blijft een array → server-side IN). -->
        <MultiSelectDropdown
          v-model="filterStatus"
          :opties="STATUS_OPTIES"
          :weergave="lifecycleLabel"
          placeholder="Alle"
          aria-label="Filter op status"
          testid="filter-status"
          @change="herfilter"
        />
      </label>

      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Type</span>
        <select
          v-model="filterType"
          data-testid="filter-type"
          aria-label="Filter op componenttype"
          class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="o in typeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Laag</span>
        <select
          v-model="filterLaag"
          data-testid="filter-laag"
          aria-label="Filter op ArchiMate-laag"
          class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="o in laagOpties" :key="o.waarde" :value="o.waarde">{{ o.label }}</option>
        </select>
      </label>

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
        <ZoekSelect
          testid="filter-eigenaar"
          v-model="filterEigenaarId"
          :zoek-functie="zoekOrganisaties"
          placeholder="Kies een organisatie…"
          @update:model-value="herfilter"
        />
      </label>

      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Naam</span>
        <input
          v-model="filterZoek"
          type="search"
          maxlength="100"
          data-testid="filter-zoek"
          aria-label="Zoek op componentnaam"
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

    <!-- ADR-027 slice 3 — actieve klaarverklaring-doorklik (dashboard) als wisbare chip. -->
    <div
      v-if="filterKlaarverklaring || filterAfwijking"
      data-testid="klaarverklaring-filter-chip"
      class="mb-[var(--cd-space-md)] inline-flex items-center gap-[var(--cd-space-sm)] rounded-[var(--cd-radius-badge)] bg-[var(--cd-color-accent)] px-[var(--cd-space-md)] py-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]"
    >
      <span>{{ filterAfwijking ? 'Klaar verklaard, checklist nog niet compleet' : 'Klaar verklaard' }}</span>
      <button type="button" data-testid="klaarverklaring-filter-wis" aria-label="Filter wissen" class="font-semibold hover:underline" @click="wisKlaarverklaringFilter">×</button>
    </div>

    <!-- Server-side sortering (ADR-017): lazy + @sort → sort/order + cursor-reset.
         Laag is bewust NIET sorteerbaar (afgeleide ArchiMate-projectie, geen kolom). -->
    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="componenten-tabel"
      class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="naam" header="Naam" sortable>
        <template #body="{ data }">
          <router-link
            :to="rijRoute(data)"
            data-testid="rij-link"
            class="text-[var(--cd-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
        </template>
      </Column>
      <Column header="Type" sort-field="componenttype" sortable>
        <template #body="{ data }">
          <Tag :value="data.componenttype_label" :severity="data.heeft_applicatie_subtype ? 'info' : 'secondary'" />
        </template>
      </Column>
      <Column header="Laag">
        <template #body="{ data }">
          <span data-testid="rij-laag">{{ laagLabel(data.laag) }}</span>
          <span
            v-if="elementLabel(data.archimate_element)"
            class="block text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]"
          >
            {{ elementLabel(data.archimate_element) }}
          </span>
        </template>
      </Column>
      <Column header="Eigenaar" sort-field="eigenaar" sortable>
        <template #body="{ data }">
          <router-link
            v-if="data.eigenaar_organisatie_id"
            :to="{ name: 'partij-detail', params: { id: data.eigenaar_organisatie_id } }"
            :data-testid="`comp-eigenaar-org-link-${data.id}`"
            class="text-[var(--cd-color-primary)] hover:underline"
          >{{ data.eigenaar_organisatie_naam }}</router-link>
          <span v-else>—</span>
        </template>
      </Column>
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
          <Tag v-if="data.lifecycle_status" :value="lifecycleLabel(data.lifecycle_status)" :severity="lifecycleSeverity(data.lifecycle_status)" />
          <span v-else data-testid="status-leeg">—</span>
        </template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden && heeftFilters" data-testid="lijst-geen-match">
          Geen componenten komen overeen met de filters.
        </span>
        <span v-else-if="eersteGeladen && !laden" data-testid="lijst-leeg">
          Er zijn nog geen componenten in deze tenant.
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
