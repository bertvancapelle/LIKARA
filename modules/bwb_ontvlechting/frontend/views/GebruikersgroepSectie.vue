<script setup>
/**
 * GebruikersgroepSectie — gebruikersgroepen van één applicatie (in ApplicatieDetail).
 * Dialog-in-sectie (zie DatatypeSectie voor de motivatie). UX-B6-a: `organisatie` is een
 * optionele, zoekbare verwijzing naar een organisatie-partij (geen vrije tekst meer).
 */
import { computed, nextTick, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import ZoekSelect from './ZoekSelect.vue'

// Organisatie-keuze: server-side zoeken, beperkt tot partijen met aard=organisatie.
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })

const props = defineProps({ applicatieId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()

const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)

// Sortering (CD020) — null = server-default (created_at asc), niet meegestuurd.
const sortVeld = ref(null)
const sortRichting = ref(null) // 'asc' | 'desc'
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)

const dialogOpen = ref(false)
const bewerkenId = ref(null)
const bezig = ref(false)
const form = reactive({ organisatie_id: null, afdeling: '', aantal_gebruikers: '' })
const fouten = reactive({})
const eersteVeld = ref(null)
let laatsteTrigger = null

function _toastFout(e) {
  const per = { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { applicatie_id: props.applicatieId, limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    const p = await api.gebruikersgroepen.lijst(params)
    items.value = reset ? p.items : items.value.concat(p.items)
    cursor.value = p.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Laden van gebruikersgroepen mislukt.'
  } finally {
    laden.value = false
  }
}

function onSort(event) {
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

function _reset() {
  Object.assign(form, { organisatie_id: null, afdeling: '', aantal_gebruikers: '' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

function openNieuw(e) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = null
  _reset()
  dialogOpen.value = true
}

function openBewerken(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = rij.id
  _reset()
  Object.assign(form, {
    organisatie_id: rij.organisatie_id ?? null,
    afdeling: rij.afdeling || '',
    aantal_gebruikers: rij.aantal_gebruikers ?? '',
  })
  dialogOpen.value = true
}

function focusEerste() {
  // Ná de focustrap van PrimeVue Dialog (die anders de sluitknop focust). ZoekSelect
  // exposeert een focus()-methode; val anders terug op het root-element.
  setTimeout(() => {
    const c = eersteVeld.value
    if (c?.focus) c.focus()
    else (c?.$el ?? c)?.focus?.()
  }, 0)
}
function onHide() {
  laatsteTrigger?.focus?.()
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  // UX-B6-a — organisatie is optioneel (verwijzing); geen verplicht-/lengtecheck meer.
  if (form.afdeling && form.afdeling.trim().length > 255) fouten.afdeling = 'Maximaal 255 tekens.'
  if (form.aantal_gebruikers !== '' && form.aantal_gebruikers !== null) {
    const n = Number(form.aantal_gebruikers)
    if (!Number.isInteger(n) || n < 0) fouten.aantal_gebruikers = 'Geheel getal ≥ 0.'
  }
  return Object.keys(fouten).length === 0
}

function _serverveldfouten(e) {
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let t = false
    for (const d of e.detail) {
      const v = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (v && v in form) {
        fouten[v] = d.msg || 'Ongeldige waarde.'
        t = true
      }
    }
    return t
  }
  return false
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    const data = {
      organisatie_id: form.organisatie_id || null,
      afdeling: form.afdeling.trim() || null,
      aantal_gebruikers: form.aantal_gebruikers === '' ? null : Number(form.aantal_gebruikers),
    }
    if (bewerkenId.value) await api.gebruikersgroepen.werkBij(bewerkenId.value, data)
    else await api.gebruikersgroepen.maak({ ...data, applicatie_id: props.applicatieId })
    toast.add({ severity: 'success', summary: bewerkenId.value ? 'Opgeslagen' : 'Toegevoegd', life: 3000 })
    dialogOpen.value = false
    await laad({ reset: true })
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

const verwijderOpen = ref(false)
const teVerwijderen = ref(null)
function vraagVerwijder(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  teVerwijderen.value = rij
  verwijderOpen.value = true
}
async function bevestigVerwijder() {
  bezig.value = true
  try {
    await api.gebruikersgroepen.verwijder(teVerwijderen.value.id)
    toast.add({ severity: 'success', summary: 'Verwijderd', life: 3000 })
    verwijderOpen.value = false
    await laad({ reset: true })
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

laad({ reset: true })
</script>

<template>
  <section class="card" aria-labelledby="sectie-gebruikersgroepen">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-sm)]">
      <h2 id="sectie-gebruikersgroepen" class="text-[length:var(--cd-text-lg)] font-semibold">Gebruikersgroepen</h2>
      <Button v-if="mag" label="Toevoegen" severity="secondary" data-testid="gg-toevoegen" class="ml-auto" @click="openNieuw" />
    </div>

    <p v-if="fout" role="alert" data-testid="gg-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="gg-tabel"
      @sort="onSort"
    >
      <Column field="organisatie" header="Organisatie" sortable>
        <template #body="{ data }">
          <router-link
            v-if="data.organisatie_id"
            :to="{ name: 'partij-detail', params: { id: data.organisatie_id } }"
            :data-testid="`gg-org-link-${data.id}`"
            class="text-[var(--cd-color-primary)] hover:underline"
          >
            {{ data.organisatie_naam }}
          </router-link>
          <span v-else class="text-[var(--cd-color-text-muted)]">—</span>
        </template>
      </Column>
      <Column field="afdeling" header="Afdeling" sortable />
      <Column field="aantal_gebruikers" header="Aantal gebruikers" sortable />
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--cd-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`gg-bewerk-${data.id}`" @click="(e) => openBewerken(e, data)" />
            <Button label="Verwijderen" severity="danger" :data-testid="`gg-verwijder-${data.id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="gg-leeg">Nog geen gebruikersgroepen.</span></template>
    </DataTable>

    <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="gg-meer" :disabled="laden" class="mt-[var(--cd-space-sm)]" @click="laad()" />

    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="bewerkenId ? 'Gebruikersgroep bewerken' : 'Gebruikersgroep toevoegen'" data-testid="gg-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[20rem]" data-testid="gg-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gg-organisatie" class="font-semibold">Organisatie</label>
          <ZoekSelect
            id="gg-organisatie"
            ref="eersteVeld"
            testid="gg-veld-organisatie"
            v-model="form.organisatie_id"
            :zoek-functie="zoekOrganisaties"
            :invalid="!!fouten.organisatie_id"
            placeholder="Zoek een organisatie (optioneel)…"
          />
          <span v-if="fouten.organisatie_id" id="gg-fout-organisatie" role="alert" data-testid="gg-fout-organisatie" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.organisatie_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gg-afdeling" class="font-semibold">Afdeling</label>
          <InputText id="gg-afdeling" v-model="form.afdeling" data-testid="gg-veld-afdeling" />
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gg-aantal" class="font-semibold">Aantal gebruikers</label>
          <InputText id="gg-aantal" v-model="form.aantal_gebruikers" type="number" min="0" data-testid="gg-veld-aantal" :aria-invalid="!!fouten.aantal_gebruikers" aria-describedby="gg-fout-aantal" />
          <span v-if="fouten.aantal_gebruikers" id="gg-fout-aantal" role="alert" data-testid="gg-fout-aantal" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.aantal_gebruikers }}</span>
        </div>
        <div class="flex gap-[var(--cd-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="gg-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Gebruikersgroep verwijderen" data-testid="gg-verwijder-dialog" @hide="onHide">
      <p class="mb-[var(--cd-space-md)] max-w-prose">Deze gebruikersgroep definitief verwijderen?</p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Verwijderen" severity="danger" data-testid="gg-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijder" />
      </div>
    </Dialog>
  </section>
</template>
