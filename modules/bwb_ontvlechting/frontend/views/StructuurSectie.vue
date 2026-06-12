<script setup>
/**
 * StructuurSectie — de "Opbouw"-laag van één component (ADR-021 Besluit 6).
 *
 * Beide richtingen uit één endpoint (`api.componenten.structuur(id)`):
 *  - "Draait op": waar dit component op steunt (dit component is `component_id`).
 *  - "Gebruikt door": wie op dit component steunt (dit component is `op_component_id`).
 * Een relatie toevoegen maakt altijd "dit component draait op [doel]" (component_id =
 * dit component). Doel-component via ZoekSelect (CD049) op `api.componenten.lijst`;
 * relatietype uit de actieve `structuurrelatie_type`-catalogus. Subtype-buren (type
 * `applicatie`) navigeren naar ApplicatieDetail, overige naar ComponentDetail.
 * De structuur voedt de engine NIET (ADR-021) → mutaties verversen alleen de sectie.
 */
import { computed, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, Textarea, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { REGISTER_FOUT, humaniseer } from '../labels'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({ componentId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()
const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const draaitOp = ref([])
const gebruiktDoor = ref([])
const laden = ref(false)
const fout = ref(null)

const zoekComponenten = (params) => api.componenten.lijst(params)
const relatieOpties = ref([]) // [{ optie_sleutel, label }]
const dialogOpen = ref(false)
const bewerkenId = ref(null)
const bezig = ref(false)
const eersteVeld = ref(null)
let laatsteTrigger = null

const form = reactive({ op_component_id: '', relatietype: '', omschrijving: '' })
const fouten = reactive({})

function _toastFout(e) {
  const detail =
    e?.code && REGISTER_FOUT[e.code]
      ? e?.message || REGISTER_FOUT[e.code]
      : { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    const overzicht = await api.componenten.structuur(props.componentId)
    draaitOp.value = overzicht.draait_op || []
    gebruiktDoor.value = overzicht.gebruikt_door || []
  } catch (e) {
    fout.value = e?.message || 'Laden van de opbouw mislukt.'
  } finally {
    laden.value = false
  }
}

async function _zorgRelatieOpties() {
  if (relatieOpties.value.length) return
  try {
    relatieOpties.value = (await api.componenten.opties()).structuurrelatie_type || []
  } catch (e) {
    _toastFout(e)
  }
}

// Buur-navigatie: subtype (type applicatie) → ApplicatieDetail; overige → ComponentDetail.
function buurRoute(rij) {
  return rij.componenttype === 'applicatie'
    ? { name: 'applicatie-detail', params: { id: rij.component_id } }
    : { name: 'component-detail', params: { id: rij.component_id } }
}

function _reset() {
  Object.assign(form, { op_component_id: '', relatietype: '', omschrijving: '' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

async function openNieuw(e) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = null
  await _zorgRelatieOpties()
  _reset()
  dialogOpen.value = true
}

async function openBewerken(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = rij.structuur_id
  await _zorgRelatieOpties()
  Object.keys(fouten).forEach((k) => delete fouten[k])
  // Het doel-component is immutabel bij bewerken; alleen relatietype/omschrijving wijzigen.
  Object.assign(form, { op_component_id: rij.component_id, relatietype: rij.relatietype, omschrijving: rij.omschrijving || '' })
  dialogOpen.value = true
}

function focusEerste() {
  setTimeout(() => eersteVeld.value?.focus?.(), 0) // ZoekSelect exposeert focus()
}
function onHide() {
  laatsteTrigger?.focus?.()
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!bewerkenId.value && !form.op_component_id) fouten.op_component_id = 'Kies een component.'
  if (!form.relatietype) fouten.relatietype = 'Kies een relatietype.'
  return Object.keys(fouten).length === 0
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    if (bewerkenId.value) {
      await api.componentStructuren.werkBij(bewerkenId.value, {
        relatietype: form.relatietype,
        omschrijving: form.omschrijving.trim() || null,
      })
    } else {
      await api.componentStructuren.maak({
        component_id: props.componentId, // dit component draait op het gekozen doel
        op_component_id: form.op_component_id,
        relatietype: form.relatietype,
        omschrijving: form.omschrijving.trim() || null,
      })
    }
    toast.add({ severity: 'success', summary: bewerkenId.value ? 'Opgeslagen' : 'Toegevoegd', life: 3000 })
    dialogOpen.value = false
    await laad() // alleen de sectie — de structuur voedt de engine niet
  } catch (e) {
    _toastFout(e)
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
    await api.componentStructuren.verwijder(teVerwijderen.value.structuur_id)
    toast.add({ severity: 'success', summary: 'Ontkoppeld', life: 3000 })
    verwijderOpen.value = false
    await laad()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

const typeTag = (rij) => humaniseer(rij.componenttype)

defineExpose({ laad })
laad()
</script>

<template>
  <section class="card" aria-labelledby="sectie-opbouw">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-sm)]">
      <h2 id="sectie-opbouw" class="text-[length:var(--cd-text-lg)] font-semibold">Opbouw</h2>
      <Button v-if="mag" label="Relatie toevoegen" size="small" data-testid="st-toevoegen" class="ml-auto" @click="openNieuw" />
    </div>

    <p v-if="fout" role="alert" data-testid="st-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>

    <!-- Draait op: dit component steunt op … -->
    <h3 class="font-semibold mt-[var(--cd-space-sm)]">Draait op</h3>
    <DataTable :value="draaitOp" data-testid="st-tabel-draait-op">
      <Column header="Component">
        <template #body="{ data }">
          <router-link :to="buurRoute(data)" class="text-[var(--cd-color-primary)] hover:underline">{{ data.naam }}</router-link>
        </template>
      </Column>
      <Column header="Type"><template #body="{ data }"><Tag :value="typeTag(data)" severity="secondary" /></template></Column>
      <Column header="Relatie"><template #body="{ data }">{{ data.relatietype_label }}</template></Column>
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--cd-space-sm)]">
            <Button label="Bewerken" size="small" severity="secondary" :data-testid="`st-bewerk-${data.structuur_id}`" @click="(e) => openBewerken(e, data)" />
            <Button label="Ontkoppelen" size="small" severity="danger" :data-testid="`st-ontkoppel-${data.structuur_id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="st-leeg-draait-op">Dit component draait niet op andere componenten.</span></template>
    </DataTable>

    <!-- Gebruikt door: wie steunt op dit component -->
    <h3 class="font-semibold mt-[var(--cd-space-md)]">Gebruikt door</h3>
    <DataTable :value="gebruiktDoor" data-testid="st-tabel-gebruikt-door">
      <Column header="Component">
        <template #body="{ data }">
          <router-link :to="buurRoute(data)" class="text-[var(--cd-color-primary)] hover:underline">{{ data.naam }}</router-link>
        </template>
      </Column>
      <Column header="Type"><template #body="{ data }"><Tag :value="typeTag(data)" severity="secondary" /></template></Column>
      <Column header="Relatie"><template #body="{ data }">{{ data.relatietype_label }}</template></Column>
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--cd-space-sm)]">
            <Button label="Bewerken" size="small" severity="secondary" :data-testid="`st-bewerk-${data.structuur_id}`" @click="(e) => openBewerken(e, data)" />
            <Button label="Ontkoppelen" size="small" severity="danger" :data-testid="`st-ontkoppel-${data.structuur_id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="st-leeg-gebruikt-door">Geen enkel component draait op dit component.</span></template>
    </DataTable>

    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="bewerkenId ? 'Relatie bewerken' : 'Relatie toevoegen'" data-testid="st-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[22rem]" data-testid="st-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="st-doel" class="font-semibold">Draait op (component) *</label>
          <ZoekSelect
            id="st-doel"
            ref="eersteVeld"
            testid="st-veld-doel"
            v-model="form.op_component_id"
            :zoek-functie="zoekComponenten"
            :disabled="!!bewerkenId"
            :invalid="!!fouten.op_component_id"
            placeholder="Zoek een component…"
          />
          <span v-if="fouten.op_component_id" role="alert" data-testid="st-fout-doel" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.op_component_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="st-relatietype" class="font-semibold">Relatietype *</label>
          <select id="st-relatietype" v-model="form.relatietype" data-testid="st-veld-relatietype" :aria-invalid="!!fouten.relatietype" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
            <option value="" disabled>— kies een relatietype —</option>
            <option v-for="o in relatieOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
          </select>
          <span v-if="fouten.relatietype" role="alert" data-testid="st-fout-relatietype" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.relatietype }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="st-omschrijving" class="font-semibold">Omschrijving</label>
          <Textarea id="st-omschrijving" v-model="form.omschrijving" rows="3" data-testid="st-veld-omschrijving" />
        </div>
        <div class="flex gap-[var(--cd-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="st-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Relatie ontkoppelen" data-testid="st-ontkoppel-dialog" @hide="onHide">
      <p class="mb-[var(--cd-space-md)] max-w-prose">Deze structuurrelatie met <strong>{{ teVerwijderen?.naam }}</strong> verwijderen? De componenten zelf blijven bestaan.</p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Ontkoppelen" severity="danger" data-testid="st-ontkoppel-bevestig" :disabled="bezig" @click="bevestigVerwijder" />
      </div>
    </Dialog>
  </section>
</template>
