<script setup>
/**
 * VerantwoordelijkheidSectie — rol-toewijzingen óp één object (ADR-024 slice 2b).
 *
 * Gemount op component-/applicatie-detail én contract-detail (`objectId` = component- of
 * contract-id). Toont per regel Rol · Partij · Aard; beheerders/medewerkers kunnen een
 * toewijzing toevoegen (zoekbare partij-dropdown over álle aarden + rol-dropdown uit de
 * beheerbare `beheerrol`-catalogus) en verwijderen. Eén partij kan meerdere rollen hebben —
 * elke rij is een losse toewijzing. Registratief; raakt de engine niet.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Dialog, Tag, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { PARTIJ_AARD, label } from '../labels'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({ objectId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()
const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const rolOpties = ref([])
const laden = ref(false)
const fout = ref(null)

const dialogOpen = ref(false)
const bezig = ref(false)
const eersteVeld = ref(null)
let laatsteTrigger = null
const form = reactive({ partij_id: '', rol: '' })
const fouten = reactive({})

const aardLabel = (a) => label(PARTIJ_AARD, a)
// Partij-keuze: server-side zoeken over álle aarden (geen aard-filter).
const zoekPartijen = (params) => api.partijen.lijst(params)
const partijWeergave = (p) => `${p.naam} — ${aardLabel(p.aard)}`

function _toastFout(e) {
  const detail =
    { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Deze toewijzing bestaat al.' }[
      e?.status
    ] ||
    e?.message ||
    'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    items.value = await api.roltoewijzingen.lijst({ object_id: props.objectId })
  } catch (e) {
    fout.value = e?.message || 'Laden van verantwoordelijkheden mislukt.'
  } finally {
    laden.value = false
  }
}

async function _zorgRolOpties() {
  if (rolOpties.value.length) return
  try {
    rolOpties.value = await api.roltoewijzingen.rollen()
  } catch (e) {
    _toastFout(e)
  }
}

function _reset() {
  Object.assign(form, { partij_id: '', rol: '' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

async function openToevoegen(e) {
  laatsteTrigger = e?.currentTarget ?? null
  await _zorgRolOpties()
  _reset()
  dialogOpen.value = true
}
function focusEerste() {
  setTimeout(() => eersteVeld.value?.focus?.(), 0)
}
function onHide() {
  laatsteTrigger?.focus?.()
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.partij_id) fouten.partij_id = 'Kies een partij.'
  if (!form.rol) fouten.rol = 'Kies een rol.'
  return Object.keys(fouten).length === 0
}

async function voegToe() {
  if (!valideer()) return
  bezig.value = true
  try {
    await api.roltoewijzingen.maak({ partij_id: form.partij_id, object_id: props.objectId, rol: form.rol })
    toast.add({ severity: 'success', summary: 'Toegewezen', life: 3000 })
    dialogOpen.value = false
    await laad()
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
    await api.roltoewijzingen.verwijder(teVerwijderen.value.toewijzing_id)
    toast.add({ severity: 'success', summary: 'Verwijderd', life: 3000 })
    verwijderOpen.value = false
    await laad()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(() => Promise.all([laad(), _zorgRolOpties()]))
defineExpose({ items, laad })
</script>

<template>
  <section class="card" aria-labelledby="sectie-verantwoordelijkheden" data-testid="vw-sectie">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-sm)]">
      <h2 id="sectie-verantwoordelijkheden" class="text-[length:var(--cd-text-lg)] font-semibold">
        Verantwoordelijkheden
      </h2>
      <Button v-if="mag" label="Toewijzing toevoegen" size="small" data-testid="vw-toevoegen" class="ml-auto" @click="openToevoegen" />
    </div>

    <p v-if="fout" role="alert" data-testid="vw-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>

    <table v-if="items.length" class="w-full text-[length:var(--cd-text-sm)]" data-testid="vw-tabel">
      <thead>
        <tr class="text-left text-[var(--cd-color-text-muted)]">
          <th class="py-[var(--cd-space-xs)]">Rol</th>
          <th>Partij</th>
          <th>Aard</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rij in items" :key="rij.toewijzing_id" class="border-t border-[var(--cd-color-border)]">
          <td class="py-[var(--cd-space-xs)] font-semibold">{{ rij.rol_label }}</td>
          <td>
            <router-link :to="{ name: 'partij-detail', params: { id: rij.partij_id } }" class="text-[var(--cd-color-primary)] hover:underline">{{ rij.partij_naam }}</router-link>
          </td>
          <td><Tag :value="aardLabel(rij.partij_aard)" severity="info" /></td>
          <td class="text-right">
            <Button v-if="mag" label="Verwijderen" size="small" severity="danger" :data-testid="`vw-verwijder-${rij.toewijzing_id}`" @click="(e) => vraagVerwijder(e, rij)" />
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!laden" data-testid="vw-leeg" class="text-[var(--cd-color-text-muted)]">Nog geen toegewezen verantwoordelijkheden.</p>

    <Dialog v-model:visible="dialogOpen" modal :closable="false" header="Verantwoordelijkheid toewijzen" data-testid="vw-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[22rem]" data-testid="vw-form" @submit.prevent="voegToe">
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="vw-partij" class="font-semibold">Partij *</label>
          <ZoekSelect
            id="vw-partij"
            ref="eersteVeld"
            testid="vw-veld-partij"
            v-model="form.partij_id"
            :zoek-functie="zoekPartijen"
            :weergave="partijWeergave"
            :invalid="!!fouten.partij_id"
            placeholder="Zoek een partij…"
          />
          <span v-if="fouten.partij_id" role="alert" data-testid="vw-fout-partij" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.partij_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="vw-rol" class="font-semibold">Rol *</label>
          <select id="vw-rol" v-model="form.rol" data-testid="vw-veld-rol" :aria-invalid="!!fouten.rol" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
            <option value="" disabled>— kies een rol —</option>
            <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
          </select>
          <span v-if="fouten.rol" role="alert" data-testid="vw-fout-rol" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.rol }}</span>
        </div>
        <div class="flex gap-[var(--cd-space-md)]">
          <Button type="submit" label="Toewijzen" data-testid="vw-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Toewijzing verwijderen" data-testid="vw-verwijder-dialog" @hide="onHide">
      <p class="mb-[var(--cd-space-md)] max-w-prose">
        De toewijzing <strong>{{ teVerwijderen?.rol_label }}</strong> van <strong>{{ teVerwijderen?.partij_naam }}</strong> verwijderen?
      </p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Verwijderen" severity="danger" data-testid="vw-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijder" />
      </div>
    </Dialog>
  </section>
</template>
