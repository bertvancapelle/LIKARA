<script setup>
/**
 * PartijRollenSectie — rollen die één partij vervult op objecten (ADR-024 slice 2b + DC013).
 *
 * Gemount op partij-detail. Toont op welke componenten/contracten de partij een rol heeft
 * (Object · Type · Rol). Beheerders/medewerkers kunnen hier óók een rol toevoegen — symmetrisch
 * met VerantwoordelijkheidSectie (daar is de partij vast en kies je het object; hier is de partij
 * vast en kies je het object). Zelfde roltoewijzing-endpoint. Registratief; raakt de engine niet.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, useToast } from '@/primevue'
import { detailRoute } from '@/detailIngang'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { humaniseer } from '../labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({ partijId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()
const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const rolOpties = ref([])
const laden = ref(false)

// Object-type → detail-route (subtype-componenten linken net als elders naar component-detail).
const objectRoute = (rij) =>
  rij.object_type === 'contract'
    ? detailRoute('contract', rij.object_id)
    : detailRoute('component', rij.object_id)
const typeLabel = (t) => humaniseer(t)

// Object-keuze: één zoekveld over componenten ÉN contracten (de twee toegestane object-typen).
// Beide endpoints leveren {items}; we mappen naar een uniforme {id, naam, soort}-vorm.
async function zoekObjecten(params) {
  const [comp, con] = await Promise.all([
    api.componenten.lijst({ ...params }),
    api.contracten.lijst({ ...params }),
  ])
  const compItems = (comp?.items ?? []).map((c) => ({ id: c.id, naam: c.naam, soort: 'Component' }))
  const conItems = (con?.items ?? []).map((c) => ({ id: c.id, naam: c.contractnaam, soort: 'Contract' }))
  return [...compItems, ...conItems]
}
const objectWeergave = (o) => `${o.naam} — ${o.soort}`

const dialogOpen = ref(false)
const bezig = ref(false)
const eersteVeld = ref(null)
let laatsteTrigger = null
const form = reactive({ object_id: '', rol: '' })
const fouten = reactive({})

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
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
  try {
    items.value = await api.roltoewijzingen.lijst({ partij_id: props.partijId })
  } catch {
    items.value = []
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
  Object.assign(form, { object_id: '', rol: '' })
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
  if (!form.object_id) fouten.object_id = 'Kies een object.'
  if (!form.rol) fouten.rol = 'Kies een rol.'
  return Object.keys(fouten).length === 0
}

async function voegToe() {
  if (!valideer()) return
  bezig.value = true
  try {
    await api.roltoewijzingen.maak({ partij_id: props.partijId, object_id: form.object_id, rol: form.rol })
    toast.add({ severity: 'success', summary: 'Toegewezen', life: 3000 })
    dialogOpen.value = false
    await laad()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(laad)
const heeftRijen = computed(() => items.value.length > 0)
defineExpose({ items, laad })
</script>

<template>
  <section class="card" aria-labelledby="sectie-partij-rollen" data-testid="pr-sectie">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-partij-rollen" class="text-[length:var(--lk-text-lg)] font-semibold">
        Rollen op objecten
      </h2>
      <Button v-if="mag" label="Rol toevoegen" severity="secondary" data-testid="pr-toevoegen" class="ml-auto" @click="openToevoegen" />
    </div>

    <DataTable :value="items" data-testid="pr-tabel">
      <Column header="Object">
        <template #body="{ data }">
          <router-link :to="objectRoute(data)" data-testid="pr-object-link" class="text-[var(--lk-color-primary)] hover:underline">{{ data.object_naam }}</router-link>
        </template>
      </Column>
      <Column header="Type"><template #body="{ data }"><Tag :value="typeLabel(data.object_type)" severity="secondary" /></template></Column>
      <Column header="Rol"><template #body="{ data }">{{ data.rol_label }}</template></Column>
      <template #empty><span data-testid="pr-leeg">Deze partij heeft nog geen rollen op objecten. Voeg er een toe met "Rol toevoegen", of wijs een rol toe vanaf een component of een contract.</span></template>
    </DataTable>

    <Dialog v-model:visible="dialogOpen" modal :closable="false" header="Rol toewijzen aan deze partij" data-testid="pr-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="pr-form" @submit.prevent="voegToe">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="pr-object" class="font-semibold">Object *</label>
          <ZoekSelect
            id="pr-object"
            ref="eersteVeld"
            testid="pr-veld-object"
            v-model="form.object_id"
            :zoek-functie="zoekObjecten"
            :weergave="objectWeergave"
            :invalid="!!fouten.object_id"
            placeholder="Zoek een component of contract…"
          />
          <span v-if="fouten.object_id" role="alert" data-testid="pr-fout-object" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.object_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <label for="pr-rol" class="font-semibold">Rol *</label>
            <VeldUitleg veld="beheerrol" opties="beheerrol" />
          </div>
          <select id="pr-rol" v-model="form.rol" data-testid="pr-veld-rol" :aria-invalid="!!fouten.rol" class="lk-veld">
            <option value="" disabled>— kies een rol —</option>
            <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
          </select>
          <span v-if="fouten.rol" role="alert" data-testid="pr-fout-rol" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.rol }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Toewijzen" data-testid="pr-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
