<script setup>
/**
 * AuditTrailView — audit-spoor lezen (ADR-029 Fase 3a). Beheerder/auditor beantwoordt
 * "wie deed wat, wanneer, op welk onderdeel". Correlatie-gegroepeerde gebeurtenissen
 * (nieuwste eerst, keyset "Meer laden"); de driver-handeling vat de gebeurtenis samen,
 * afgeleide gevolgen worden als telling getoond (volledige diff-weergave is een follow-up).
 *
 * Filters v1 (AND): naam (vrije-tekst-fragment → backend resolveert naam→sub), periode (van/tot),
 * component (ZoekSelect), handeling. Backend handhaaft AUDITLOG.LEZEN; nav is affordance.
 * `--cd-`-tokens, geen `<style>`.
 */
import { reactive, ref } from 'vue'
import { Button, Column, DataTable, InputText } from '@/primevue'
import { api } from '@/api'
import { AUDIT_ACTIE, AUDIT_ENTITEIT, label } from '@modules/bwb_ontvlechting/frontend/labels'
import ZoekSelect from './ZoekSelect.vue'

const gebeurtenissen = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const filters = reactive({ actor_naam: '', component_id: '', actie: '', van: '', tot: '' })

const zoekComponenten = (params) => api.componenten.lijst({ ...params })

const _datum = (iso) =>
  iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : ''

function _driver(g) {
  return (g.records && g.records[0]) || {}
}
function _afgeleid(g) {
  const n = (g.records?.length || 1) - 1
  return n > 0 ? ` (+${n} afgeleid)` : ''
}

function _params(extra = {}) {
  const p = { limit: 25 }
  if (filters.actor_naam.trim()) p.actor_naam = filters.actor_naam.trim()
  if (filters.component_id) p.component_id = filters.component_id
  if (filters.actie) p.actie = filters.actie
  if (filters.van) p.van = new Date(filters.van).toISOString()
  if (filters.tot) p.tot = new Date(filters.tot).toISOString()
  return { ...p, ...extra }
}

async function laad({ meer = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const pagina = await api.auditlog.lijst(_params(meer && cursor.value ? { after: cursor.value } : {}))
    const items = pagina.items || []
    gebeurtenissen.value = meer ? [...gebeurtenissen.value, ...items] : items
    cursor.value = pagina.volgende_cursor || null
  } catch (e) {
    fout.value = e?.message || 'Laden van het auditspoor mislukt.'
  } finally {
    laden.value = false
  }
}

function pasToe() {
  cursor.value = null // filterwijziging → terug naar de eerste pagina
  laad()
}

function wis() {
  Object.assign(filters, { actor_naam: '', component_id: '', actie: '', van: '', tot: '' })
  pasToe()
}

laad()
</script>

<template>
  <section aria-labelledby="audit-titel">
    <h1 id="audit-titel" class="text-[length:var(--cd-text-xl)] font-semibold mb-[var(--cd-space-md)]">Auditlog</h1>

    <!-- Filterbalk -->
    <div class="flex flex-wrap items-end gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="filter-naam" class="text-[length:var(--cd-text-sm)] font-semibold">Naam</label>
        <InputText id="filter-naam" v-model="filters.actor_naam" data-testid="filter-naam" placeholder="Naam (deel)…" @keyup.enter="pasToe" />
      </div>
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="filter-van" class="text-[length:var(--cd-text-sm)] font-semibold">Van</label>
        <input id="filter-van" v-model="filters.van" type="date" data-testid="filter-van" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)]" @change="pasToe" />
      </div>
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="filter-tot" class="text-[length:var(--cd-text-sm)] font-semibold">Tot</label>
        <input id="filter-tot" v-model="filters.tot" type="date" data-testid="filter-tot" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)]" @change="pasToe" />
      </div>
      <div class="flex flex-col gap-[var(--cd-space-xs)] min-w-[14rem]">
        <label for="filter-component" class="text-[length:var(--cd-text-sm)] font-semibold">Onderdeel</label>
        <ZoekSelect v-model="filters.component_id" :zoek-functie="zoekComponenten" placeholder="Zoek een component…" testid="filter-component" @update:modelValue="pasToe" />
      </div>
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="filter-actie" class="text-[length:var(--cd-text-sm)] font-semibold">Handeling</label>
        <select id="filter-actie" v-model="filters.actie" data-testid="filter-actie" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white" @change="pasToe">
          <option value="">Alle</option>
          <option v-for="a in ['create', 'update', 'delete', 'derive']" :key="a" :value="a">{{ label(AUDIT_ACTIE, a) }}</option>
        </select>
      </div>
      <Button label="Zoeken" size="small" data-testid="audit-toepassen" @click="pasToe" />
      <Button label="Wissen" severity="secondary" size="small" data-testid="audit-wissen" @click="wis" />
    </div>

    <p v-if="fout" role="alert" data-testid="audit-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>

    <DataTable :value="gebeurtenissen" data-testid="audit-tabel" class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]">
      <template #empty>
        <span data-testid="audit-leeg" class="text-[var(--cd-color-text-muted)]">{{ laden ? 'Laden…' : 'Geen gebeurtenissen gevonden.' }}</span>
      </template>
      <Column header="Wie"><template #body="{ data }"><span data-testid="audit-wie">{{ data.actor_naam || data.actor_email || '—' }}</span></template></Column>
      <Column header="Wanneer"><template #body="{ data }">{{ _datum(data.tijdstip) }}</template></Column>
      <Column header="Onderdeel"><template #body="{ data }">{{ label(AUDIT_ENTITEIT, _driver(data).entiteit_type) }}</template></Column>
      <Column header="Handeling"><template #body="{ data }">{{ label(AUDIT_ACTIE, _driver(data).actie) }}{{ _afgeleid(data) }}</template></Column>
    </DataTable>

    <div v-if="cursor" class="mt-[var(--cd-space-md)] flex justify-center">
      <Button label="Meer laden" severity="secondary" :disabled="laden" data-testid="audit-meer" @click="laad({ meer: true })" />
    </div>
  </section>
</template>
