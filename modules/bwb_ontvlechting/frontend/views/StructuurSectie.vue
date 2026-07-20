<script setup>
/**
 * StructuurSectie — de "Opbouw"-laag van één component (ADR-021 Besluit 6 / ADR-023 Fase C).
 *
 * Beide richtingen uit één lees-endpoint (`api.componenten.structuur(id)`, afgeleide
 * traversal over het unified relatiemodel):
 *  - "Draait op": waar dit component op steunt (dit component = de gehoste).
 *  - "Gebruikt door": wie op dit component steunt (dit component = de host).
 * Toevoegen legt altijd "dit component draait op [doel]" als **assignment**-relatie
 * (host→gehoste = bron→doel): bron = het gekozen doel (host), doel = dit component
 * (gehoste). Geschreven via de bestaande `relatie`-API; relatietype (assignment) en
 * richting vult de UI in — géén type-/laag-validatie (migratietool, geen EA-systeem;
 * ADR-023 Fase C). Endpoints/relatietype zijn immutabel → bewerken wijzigt alleen de
 * omschrijving. Doel-component via ZoekSelect (CD049) op `api.componenten.lijst`.
 * Subtype-buren (type `applicatie`) navigeren naar ApplicatieDetail, overige naar
 * ComponentDetail. De structuur voedt de engine NIET → mutaties verversen alleen de sectie.
 */
import { computed, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, Textarea, useToast } from '@/primevue'
import { detailRoute } from '@/detailIngang'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { REGISTER_FOUT, humaniseer } from '../labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({ componentId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()
const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))
// LI037 — destructief = het VERWIJDEREN-recht (beheerder-only per de RBAC-matrix; het
// endpoint eist Actie.VERWIJDEREN). Vooraf weren i.p.v. een 403 pas in de dialoog — het
// ADR-050 — een structuurrelatie (component-samenstelling / draait-op) is een uitspraak van
// de gemeente: wie 'm legt, neemt 'm terug → medewerker (geen aparte beheerder-gate meer).
const magVerwijderen = computed(() => auth.hasRole('medewerker', 'beheerder'))

// ADR-023 Fase C: het draait-op-relatietype is vast (assignment) — de UI biedt geen keuze.
const DRAAIT_OP_TYPE = 'assignment'

const draaitOp = ref([])
const gebruiktDoor = ref([])
const laden = ref(false)
const fout = ref(null)

const zoekComponenten = (params) => api.componenten.lijst(params)
const dialogOpen = ref(false)
const bewerkenId = ref(null)
const bezig = ref(false)
const eersteVeld = ref(null)
let laatsteTrigger = null

const form = reactive({ op_component_id: '', omschrijving: '' })
const fouten = reactive({})

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
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
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de opbouw mislukt.'
  } finally {
    laden.value = false
  }
}

// LI059 Slice 4 — één detailscherm voor élk type.
function buurRoute(rij) {
  return detailRoute('component', rij.component_id)
}

function _reset() {
  Object.assign(form, { op_component_id: '', omschrijving: '' })
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
  bewerkenId.value = rij.structuur_id
  Object.keys(fouten).forEach((k) => delete fouten[k])
  // Endpoints + relatietype zijn immutabel (ADR-023): alleen de omschrijving is wijzigbaar.
  Object.assign(form, { op_component_id: rij.component_id, omschrijving: rij.omschrijving || '' })
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
  return Object.keys(fouten).length === 0
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    if (bewerkenId.value) {
      // Alleen de omschrijving is wijzigbaar (endpoints/relatietype immutabel, ADR-023).
      await api.relaties.werkBij(bewerkenId.value, {
        omschrijving: form.omschrijving.trim() || null,
      })
    } else {
      // "Dit component draait op [doel]" → assignment, host→gehoste = bron→doel:
      // bron = het gekozen doel (host), doel = dit component (gehoste).
      await api.relaties.maak({
        bron_id: form.op_component_id,
        doel_id: props.componentId,
        relatietype: DRAAIT_OP_TYPE,
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
    await api.relaties.verwijder(teVerwijderen.value.structuur_id)
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
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-opbouw">Opbouw</h2>
      <Button v-if="mag" label="Draait-op toevoegen" severity="secondary" data-testid="st-toevoegen" class="ml-auto" @click="openNieuw" />
    </div>

    <p v-if="fout" role="alert" data-testid="st-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <!-- Draait op: dit component steunt op … -->
    <h3 class="font-semibold mt-[var(--lk-space-sm)]">Draait op</h3>
    <DataTable :value="draaitOp" data-testid="st-tabel-draait-op">
      <Column header="Component">
        <template #body="{ data }">
          <router-link :to="buurRoute(data)" class="text-[var(--lk-color-primary)] hover:underline">{{ data.naam }}</router-link>
        </template>
      </Column>
      <Column header="Type"><template #body="{ data }"><Tag :value="typeTag(data)" severity="secondary" /></template></Column>
      <Column header="Relatie"><template #body="{ data }">{{ data.relatietype_label }}</template></Column>
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--lk-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`st-bewerk-${data.structuur_id}`" @click="(e) => openBewerken(e, data)" />
            <Button v-if="magVerwijderen" label="Ontkoppelen" severity="danger" :data-testid="`st-ontkoppel-${data.structuur_id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="st-leeg-draait-op">Dit component draait niet op andere componenten.</span></template>
    </DataTable>

    <!-- Gebruikt door: wie steunt op dit component -->
    <h3 class="font-semibold mt-[var(--lk-space-md)]">Gebruikt door</h3>
    <DataTable :value="gebruiktDoor" data-testid="st-tabel-gebruikt-door">
      <Column header="Component">
        <template #body="{ data }">
          <router-link :to="buurRoute(data)" class="text-[var(--lk-color-primary)] hover:underline">{{ data.naam }}</router-link>
        </template>
      </Column>
      <Column header="Type"><template #body="{ data }"><Tag :value="typeTag(data)" severity="secondary" /></template></Column>
      <Column header="Relatie"><template #body="{ data }">{{ data.relatietype_label }}</template></Column>
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--lk-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`st-bewerk-${data.structuur_id}`" @click="(e) => openBewerken(e, data)" />
            <Button v-if="magVerwijderen" label="Ontkoppelen" severity="danger" :data-testid="`st-ontkoppel-${data.structuur_id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="st-leeg-gebruikt-door">Geen enkel component draait op dit component.</span></template>
    </DataTable>

    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="bewerkenId ? 'Draait-op bewerken' : 'Draait-op toevoegen'" data-testid="st-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="st-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <label for="st-doel" class="font-semibold">Draait op (component) *</label>
            <VeldUitleg veld="draait_op" />
          </div>
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
          <span v-if="fouten.op_component_id" role="alert" data-testid="st-fout-doel" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.op_component_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="st-omschrijving" class="font-semibold">Omschrijving</label>
          <Textarea id="st-omschrijving" v-model="form.omschrijving" rows="3" data-testid="st-veld-omschrijving" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="st-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Relatie ontkoppelen" data-testid="st-ontkoppel-dialog" @hide="onHide">
      <p class="mb-[var(--lk-space-md)] max-w-prose">Deze structuurrelatie met <strong>{{ teVerwijderen?.naam }}</strong> verwijderen? De componenten zelf blijven bestaan.</p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Ontkoppelen" severity="danger" data-testid="st-ontkoppel-bevestig" :disabled="bezig" @click="bevestigVerwijder" />
      </div>
    </Dialog>
  </section>
</template>
