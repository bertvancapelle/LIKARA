<script setup>
/**
 * DatatypeSectie — datatypes van één applicatie, embedded in ApplicatieDetail.
 *
 * Bewust afwijkend van het Applicatie-CRUD-patroon (dat volledige routes gebruikt):
 * child-entiteiten zijn subordinate aan de ouder en blijven in de detail-context,
 * dus lijst + aanmaken/bewerken/verwijderen via een Dialog-in-sectie. `applicatie_id`
 * komt uit de sectie-context (prop), nooit als handmatig invoerveld.
 */
import { computed, nextTick, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Tag, Textarea, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { DATATYPE_CATEGORIE, label } from '../labels'
import VeldUitleg from './VeldUitleg.vue'

const props = defineProps({ applicatieId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()

const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)

// Sortering (CD020) — null = server-default (created_at asc), niet meegestuurd
// (backwards-compatible). PrimeVue gebruikt sortOrder 1/-1; de API asc/desc.
const sortVeld = ref(null)
const sortRichting = ref(null) // 'asc' | 'desc'
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)

const dialogOpen = ref(false)
const bewerkenId = ref(null)
const bezig = ref(false)
const opties = ref({ categorie: [] })
const form = reactive({ categorie: '', omschrijving: '', omvang_indicatie: '' })
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
    const p = await api.datatypes.lijst(params)
    items.value = reset ? p.items : items.value.concat(p.items)
    cursor.value = p.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Laden van datatypes mislukt.'
  } finally {
    laden.value = false
  }
}

function onSort(event) {
  // Nieuwe sortering → cursor resetten en vanaf pagina 1 opnieuw ophalen.
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

async function _laadOptiesEenmalig() {
  if (opties.value.categorie.length) return
  try {
    opties.value = await api.datatypes.opties()
  } catch (e) {
    _toastFout(e)
  }
}

function _reset() {
  Object.assign(form, { categorie: '', omschrijving: '', omvang_indicatie: '' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

async function openNieuw(e) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = null
  _reset()
  await _laadOptiesEenmalig()
  dialogOpen.value = true
}

async function openBewerken(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = rij.id
  _reset()
  Object.assign(form, {
    categorie: rij.categorie,
    omschrijving: rij.omschrijving || '',
    omvang_indicatie: rij.omvang_indicatie || '',
  })
  await _laadOptiesEenmalig()
  dialogOpen.value = true
}

function focusEerste() {
  // Ná de focustrap van PrimeVue Dialog (die anders de sluitknop focust).
  setTimeout(() => {
    const el = eersteVeld.value?.$el ?? eersteVeld.value
    el?.focus?.()
  }, 0)
}

function onHide() {
  laatsteTrigger?.focus?.()
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.categorie) fouten.categorie = 'Maak een keuze.'
  if (form.omvang_indicatie && form.omvang_indicatie.trim().length > 255)
    fouten.omvang_indicatie = 'Maximaal 255 tekens.'
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
      categorie: form.categorie,
      omschrijving: form.omschrijving.trim() || null,
      omvang_indicatie: form.omvang_indicatie.trim() || null,
    }
    if (bewerkenId.value) await api.datatypes.werkBij(bewerkenId.value, data)
    else await api.datatypes.maak({ ...data, applicatie_id: props.applicatieId })
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
    await api.datatypes.verwijder(teVerwijderen.value.id)
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
  <section class="card" aria-labelledby="sectie-datatypes">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-datatypes" class="text-[length:var(--lk-text-lg)] font-semibold">Datatypes</h2>
      <Button v-if="mag" label="Toevoegen" severity="secondary" data-testid="dt-toevoegen" class="ml-auto" @click="openNieuw" />
    </div>

    <p v-if="fout" role="alert" data-testid="dt-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="dt-tabel"
      @sort="onSort"
    >
      <Column header="Categorie" sort-field="categorie" sortable>
        <template #body="{ data }"><Tag :value="label(DATATYPE_CATEGORIE, data.categorie)" /></template>
      </Column>
      <Column field="omschrijving" header="Omschrijving" sortable />
      <Column field="omvang_indicatie" header="Omvang" sortable />
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--lk-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`dt-bewerk-${data.id}`" @click="(e) => openBewerken(e, data)" />
            <Button label="Verwijderen" severity="danger" :data-testid="`dt-verwijder-${data.id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="dt-leeg">Nog geen datatypes.</span></template>
    </DataTable>

    <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="dt-meer" :disabled="laden" class="mt-[var(--lk-space-sm)]" @click="laad()" />

    <!-- Aanmaken/bewerken -->
    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="bewerkenId ? 'Datatype bewerken' : 'Datatype toevoegen'" data-testid="dt-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[20rem]" data-testid="dt-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="dt-categorie" class="font-semibold">Categorie *</label>
          <div class="flex items-center gap-[var(--lk-space-xs)]">
          <select id="dt-categorie" ref="eersteVeld" autofocus v-model="form.categorie" data-testid="dt-veld-categorie" :aria-invalid="!!fouten.categorie" aria-describedby="dt-fout-categorie" class="flex-1 rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white">
            <option value="" disabled>— maak een keuze —</option>
            <option v-for="c in opties.categorie" :key="c" :value="c">{{ label(DATATYPE_CATEGORIE, c) }}</option>
          </select>
            <VeldUitleg veld="datatype_categorie" />
          </div>
          <span v-if="fouten.categorie" id="dt-fout-categorie" role="alert" data-testid="dt-fout-categorie" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.categorie }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="dt-omvang" class="font-semibold">Omvang-indicatie</label>
          <InputText id="dt-omvang" v-model="form.omvang_indicatie" data-testid="dt-veld-omvang" :aria-invalid="!!fouten.omvang_indicatie" aria-describedby="dt-fout-omvang" />
          <span v-if="fouten.omvang_indicatie" id="dt-fout-omvang" role="alert" data-testid="dt-fout-omvang" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.omvang_indicatie }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="dt-omschrijving" class="font-semibold">Omschrijving</label>
          <Textarea id="dt-omschrijving" v-model="form.omschrijving" rows="3" data-testid="dt-veld-omschrijving" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="dt-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Verwijderen -->
    <Dialog v-model:visible="verwijderOpen" modal header="Datatype verwijderen" data-testid="dt-verwijder-dialog" @hide="onHide">
      <p class="mb-[var(--lk-space-md)] max-w-prose">Dit datatype definitief verwijderen?</p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Verwijderen" severity="danger" data-testid="dt-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijder" />
      </div>
    </Dialog>
  </section>
</template>
