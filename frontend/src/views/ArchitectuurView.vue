<script setup>
/**
 * ArchitectuurView — cross-element laagprojectie (ADR-023 Fase F / F-2).
 *
 * Read-only landschapslens over álle element-typen: per element de ArchiMate-laag,
 * het aspect en het element-type, filterbaar op laag/aspect/type. Leunt volledig op
 * `GET /architectuur/elementen` (server-side filters + keyset-paginering). Labels via
 * de bestaande ArchiMate-maps; geen client-side typing-logica.
 */
import { onMounted, ref } from 'vue'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { api } from '@/api'
import { ARCHIMATE_ASPECT, ARCHIMATE_ELEMENT, ARCHIMATE_LAAG, humaniseer, label } from '@modules/bwb_ontvlechting/frontend/labels'

// Filteropties: lagen + aspecten uit de label-maps; element-typen vast (de ElementType-enum).
const LAAG_OPTIES = Object.keys(ARCHIMATE_LAAG)
const ASPECT_OPTIES = Object.keys(ARCHIMATE_ASPECT)
const TYPE_OPTIES = [
  'component', 'datatype', 'gebruikersgroep', 'contract',
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

const laagLabel = (c) => (c ? label(ARCHIMATE_LAAG, c) : '—')
const aspectLabel = (c) => (c ? label(ARCHIMATE_ASPECT, c) : '—')
const elementLabel = (c) => (c ? label(ARCHIMATE_ELEMENT, c) : '—')
const typeLabel = (c) => humaniseer(c)

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (filterLaag.value) params.laag = filterLaag.value
    if (filterAspect.value) params.aspect = filterAspect.value
    if (filterType.value) params.type = filterType.value
    const pagina = await api.architectuur.elementen(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Er ging iets mis bij het laden van het architectuuroverzicht.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

function herfilter() {
  cursor.value = null
  laad({ reset: true })
}

onMounted(() => laad({ reset: true }))
</script>

<template>
  <section aria-labelledby="arch-titel">
    <h1
      id="arch-titel"
      class="mb-[var(--cd-space-md)] text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
    >
      Architectuur — lagen
    </h1>

    <div
      data-testid="arch-filterbalk"
      class="mb-[var(--cd-space-md)] flex flex-wrap items-end gap-[var(--cd-space-md)] rounded-[var(--cd-radius-card)] bg-[var(--cd-color-surface)] p-[var(--cd-space-md)] shadow-[var(--cd-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Laag</span>
        <select v-model="filterLaag" data-testid="arch-filter-laag" aria-label="Filter op ArchiMate-laag" class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="l in LAAG_OPTIES" :key="l" :value="l">{{ laagLabel(l) }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Aspect</span>
        <select v-model="filterAspect" data-testid="arch-filter-aspect" aria-label="Filter op ArchiMate-aspect" class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="a in ASPECT_OPTIES" :key="a" :value="a">{{ aspectLabel(a) }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        <span class="text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">Type</span>
        <select v-model="filterType" data-testid="arch-filter-type" aria-label="Filter op element-type" class="rounded-[var(--cd-radius-btn)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] px-[var(--cd-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]" @change="herfilter">
          <option value="">Alle</option>
          <option v-for="t in TYPE_OPTIES" :key="t" :value="t">{{ typeLabel(t) }}</option>
        </select>
      </label>
    </div>

    <p v-if="fout" role="alert" data-testid="arch-fout" class="mb-[var(--cd-space-md)] rounded-[var(--cd-radius-badge)] border border-[var(--cd-color-danger)] bg-[var(--cd-color-danger)]/10 px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-danger)]">
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      data-testid="arch-tabel"
      class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
    >
      <Column header="Naam">
        <template #body="{ data }">
          <span class="font-medium">{{ data.naam }}</span>
          <span v-if="data.naam_secundair" class="block text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">
            {{ data.naam_secundair }}
          </span>
        </template>
      </Column>
      <Column header="Type">
        <template #body="{ data }">{{ typeLabel(data.element_type) }}</template>
      </Column>
      <Column header="Laag">
        <template #body="{ data }"><Tag :value="laagLabel(data.laag)" severity="info" /></template>
      </Column>
      <Column header="Aspect">
        <template #body="{ data }">{{ aspectLabel(data.aspect) }}</template>
      </Column>
      <Column header="ArchiMate-element">
        <template #body="{ data }">{{ elementLabel(data.archimate_element) }}</template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden" data-testid="arch-leeg">
          Geen elementen voor de gekozen filters.
        </span>
        <span v-else>Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--cd-space-md)]">
      <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="arch-meer-laden" :disabled="laden" @click="laad()" />
    </div>
  </section>
</template>
