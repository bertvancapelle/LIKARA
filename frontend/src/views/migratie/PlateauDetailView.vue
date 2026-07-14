<script setup>
/**
 * PlateauDetailView — migratielaag (ADR-023 Fase E/F): plateau-detail + ledenbeheer.
 * UX-A4-1: wijzigen/verwijderen van het plateau en koppelen/ontkoppelen van leden
 * (component én contract) met dispositie; bij een contract-lid de contractuele bevestiging.
 * Leunt op de bestaande plateau-CRUD + leden-endpoints. Registratie/migratielaag — raakt de
 * engine (lifecycle/score/blokkade) niet.
 *
 * Rol-gating (affordance; backend handhaaft): wijzigen/koppelen/dispositie = medewerker/
 * beheerder (PLATEAU·AANMAKEN/WIJZIGEN); verwijderen plateau + ontkoppelen lid = beheerder
 * (PLATEAU·VERWIJDEREN).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Tag, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'
import ObjectHistoriePaneel from '@modules/bwb_ontvlechting/frontend/views/ObjectHistoriePaneel.vue'
import VeldUitleg from '@modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const magBeheren = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

const plateau = ref(null)
const leden = ref([])
const dispositieOpties = ref([])
const laden = ref(true)
const fout = ref(null)

const TYPE_LABEL = { component: 'Component', contract: 'Contract' }

function formatDatum(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }).format(d)
}

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  const detail =
    { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Dit lid zit al in dit plateau.' }[
      e?.status
    ] ||
    e?.message ||
    'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laadLeden() {
  leden.value = await api.plateaus.leden(props.id)
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    plateau.value = await api.plateaus.haal(props.id)
    await laadLeden()
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Het plateau kon niet worden geladen.'
  } finally {
    laden.value = false
  }
}

async function _zorgDisposities() {
  if (dispositieOpties.value.length) return
  try {
    dispositieOpties.value = await api.plateaus.disposities()
  } catch (e) {
    _toastFout(e)
  }
}

// ── Plateau bewerken ─────────────────────────────────────────────────────────
const editOpen = ref(false)
const bezig = ref(false)
const editForm = reactive({ naam: '', toelichting: '' })
const editFout = ref(null)

function openBewerken() {
  editForm.naam = plateau.value?.naam || ''
  editForm.toelichting = plateau.value?.toelichting || ''
  editFout.value = null
  editOpen.value = true
}
async function bevestigBewerken() {
  if (!editForm.naam.trim()) {
    editFout.value = 'Naam is verplicht.'
    return
  }
  bezig.value = true
  try {
    plateau.value = await api.plateaus.werkBij(props.id, {
      naam: editForm.naam.trim(),
      toelichting: editForm.toelichting.trim() || null,
    })
    toast.add({ severity: 'success', summary: 'Opgeslagen', life: 3000 })
    editOpen.value = false
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Plateau verwijderen ──────────────────────────────────────────────────────
const verwijderOpen = ref(false)
async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.plateaus.verwijder(props.id)
    toast.add({ severity: 'success', summary: 'Plateau verwijderd', life: 3000 })
    router.push({ name: 'plateau-lijst' })
  } catch (e) {
    verwijderOpen.value = false
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Lid koppelen ─────────────────────────────────────────────────────────────
const koppelOpen = ref(false)
const eersteVeld = ref(null)
let laatsteTrigger = null
const lidForm = reactive({
  lidType: 'component',
  lid_id: '',
  dispositie: '',
  contractueel_bevestigd: false,
  bevestigd_aantal_gebruikers: '',
})
const lidFouten = reactive({})
const isContractLid = computed(() => lidForm.lidType === 'contract')

const zoekComponenten = (params) => api.componenten.lijst(params)
const zoekContracten = (params) => api.contracten.lijst(params)
const zoekFunctie = computed(() => (isContractLid.value ? zoekContracten : zoekComponenten))
const lidWeergave = (item) =>
  isContractLid.value ? `${item.contractnaam} — ${item.leverancier_naam}` : item.naam

function onLidTypeChange() {
  lidForm.lid_id = '' // reset de keuze bij het wisselen van bron (component ↔ contract)
}

async function openKoppelen(e) {
  laatsteTrigger = e?.currentTarget ?? null
  await _zorgDisposities()
  Object.assign(lidForm, {
    lidType: 'component', lid_id: '', dispositie: '',
    contractueel_bevestigd: false, bevestigd_aantal_gebruikers: '',
  })
  Object.keys(lidFouten).forEach((k) => delete lidFouten[k])
  koppelOpen.value = true
}
function focusEerste() {
  setTimeout(() => eersteVeld.value?.focus?.(), 0)
}
function onHide() {
  laatsteTrigger?.focus?.()
}
function valideerLid() {
  Object.keys(lidFouten).forEach((k) => delete lidFouten[k])
  if (!lidForm.lid_id) lidFouten.lid_id = `Kies een ${isContractLid.value ? 'contract' : 'component'}.`
  if (!lidForm.dispositie) lidFouten.dispositie = 'Kies een dispositie.'
  return Object.keys(lidFouten).length === 0
}
async function bevestigKoppel() {
  if (!valideerLid()) return
  bezig.value = true
  try {
    const data = { lid_id: lidForm.lid_id, dispositie: lidForm.dispositie }
    if (isContractLid.value) {
      data.contractueel_bevestigd = lidForm.contractueel_bevestigd
      const n = Number.parseInt(lidForm.bevestigd_aantal_gebruikers, 10)
      if (!Number.isNaN(n)) data.bevestigd_aantal_gebruikers = n
    }
    await api.plateaus.voegLid(props.id, data)
    toast.add({ severity: 'success', summary: 'Lid gekoppeld', life: 3000 })
    koppelOpen.value = false
    await laadLeden()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Lid: dispositie wijzigen (inline) + ontkoppelen ──────────────────────────
async function wijzigDispositie(lid, event) {
  const nieuw = event.target.value
  try {
    await api.plateaus.werkLid(props.id, lid.id, { dispositie: nieuw })
    toast.add({ severity: 'success', summary: 'Dispositie gewijzigd', life: 2500 })
    await laadLeden()
  } catch (e) {
    _toastFout(e)
    await laadLeden() // herstel de getoonde waarde bij fout
  }
}

const ontkoppelOpen = ref(false)
const teOntkoppelen = ref(null)
function vraagOntkoppel(e, lid) {
  laatsteTrigger = e?.currentTarget ?? null
  teOntkoppelen.value = lid
  ontkoppelOpen.value = true
}
async function bevestigOntkoppel() {
  bezig.value = true
  try {
    await api.plateaus.verwijderLid(props.id, teOntkoppelen.value.id)
    toast.add({ severity: 'success', summary: 'Ontkoppeld', life: 3000 })
    ontkoppelOpen.value = false
    await laadLeden()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(() => {
  laad()
  if (auth.hasRole('medewerker', 'beheerder')) _zorgDisposities() // voor de inline dispositie-select
})
</script>

<template>
  <section aria-labelledby="plateau-detail-titel">
    <router-link :to="{ name: 'plateau-lijst' }" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline">
      ← Plateaus
    </router-link>

    <p v-if="fout" role="alert" data-testid="plateau-detail-fout" class="my-[var(--lk-space-md)] text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden" data-testid="plateau-detail-laden" class="my-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>

    <template v-else-if="plateau">
      <div class="mt-[var(--lk-space-sm)] mb-[var(--lk-space-sm)] flex items-center gap-[var(--lk-space-md)]">
        <h1 id="plateau-detail-titel" data-testid="plateau-naam" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
          {{ plateau.naam }}
        </h1>
        <ObjectHistoriePaneel entiteit-type="plateau" :entiteit-id="props.id" class="ml-auto" />
        <Button v-if="magBeheren" label="Bewerken" data-testid="plateau-bewerken" @click="openBewerken" />
        <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="plateau-verwijderen" @click="verwijderOpen = true" />
      </div>
      <p v-if="plateau.toelichting" class="mb-[var(--lk-space-lg)] text-[var(--lk-color-text)]">{{ plateau.toelichting }}</p>

      <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
        <h2 class="text-[length:var(--lk-text-lg)] font-semibold">Leden</h2>
        <Button v-if="magBeheren" label="+ Lid koppelen" severity="secondary" data-testid="lid-koppelen" class="ml-auto" @click="openKoppelen" />
      </div>

      <DataTable :value="leden" data-testid="plateau-leden-tabel" class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]">
        <Column header="Naam"><template #body="{ data }">{{ data.lid_naam || '—' }}</template></Column>
        <Column header="Type"><template #body="{ data }">{{ TYPE_LABEL[data.lid_element_type] || data.lid_element_type }}</template></Column>
        <Column header="Dispositie">
          <template #body="{ data }">
            <select
              v-if="magBeheren"
              :value="data.dispositie"
              :data-testid="`lid-dispositie-${data.id}`"
              :aria-label="`Dispositie van ${data.lid_naam || data.lid_id}`"
              class="lk-veld"
              @change="(e) => wijzigDispositie(data, e)"
            >
              <option v-for="o in dispositieOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
              <option v-if="!dispositieOpties.some((o) => o.optie_sleutel === data.dispositie)" :value="data.dispositie">{{ data.dispositie_label || data.dispositie }}</option>
            </select>
            <Tag v-else :value="data.dispositie_label || data.dispositie" severity="info" />
          </template>
        </Column>
        <Column header="Contractueel bevestigd">
          <template #body="{ data }">
            <span v-if="data.lid_element_type !== 'contract'" class="text-[var(--lk-color-text-muted)]">n.v.t.</span>
            <Tag v-else :value="data.contractueel_bevestigd ? 'Bevestigd' : 'Niet bevestigd'" :severity="data.contractueel_bevestigd ? 'success' : 'warning'" data-testid="lid-bevestiging" />
          </template>
        </Column>
        <Column header="Aantal gebruikers"><template #body="{ data }">{{ data.bevestigd_aantal_gebruikers ?? '—' }}</template></Column>
        <Column header="Bevestigd door"><template #body="{ data }">{{ data.bevestigd_door_naam || data.bevestigd_door || '—' }}</template></Column>
        <Column header="Bevestigd op"><template #body="{ data }">{{ formatDatum(data.bevestigd_op) }}</template></Column>
        <Column header="">
          <template #body="{ data }">
            <Button v-if="magVerwijderen" label="Ontkoppelen" severity="danger" :data-testid="`lid-ontkoppel-${data.id}`" @click="(e) => vraagOntkoppel(e, data)" />
          </template>
        </Column>
        <template #empty>
          <span data-testid="plateau-leden-leeg">
            Dit plateau heeft nog geen leden.
            <template v-if="magBeheren">Koppel een component of contract met “+ Lid koppelen”.</template>
          </span>
        </template>
      </DataTable>
    </template>

    <!-- Plateau bewerken -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Plateau bewerken" data-testid="plateau-edit-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="plateau-edit-form" @submit.prevent="bevestigBewerken">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="pe-naam" class="font-semibold">Naam *</label>
          <InputText id="pe-naam" v-model="editForm.naam" data-testid="pe-naam" :aria-invalid="!!editFout" />
          <span v-if="editFout" role="alert" data-testid="pe-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFout }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="pe-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="pe-toelichting" v-model="editForm.toelichting" rows="3" data-testid="pe-toelichting" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="pe-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Plateau verwijderen -->
    <Dialog v-model:visible="verwijderOpen" modal header="Plateau verwijderen" data-testid="plateau-verwijder-dialog">
      <p class="mb-[var(--lk-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ plateau?.naam }}</strong> wilt verwijderen? De leden-koppelingen
        vervallen; de componenten en contracten zelf blijven bestaan.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="plateau-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>

    <!-- Lid koppelen -->
    <Dialog v-model:visible="koppelOpen" modal :closable="false" header="Lid koppelen" data-testid="lid-koppel-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="lid-koppel-form" @submit.prevent="bevestigKoppel">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="lk-type" class="font-semibold">Type lid</label>
          <select id="lk-type" v-model="lidForm.lidType" data-testid="lk-type" class="lk-veld" @change="onLidTypeChange">
            <option value="component">Component</option>
            <option value="contract">Contract</option>
          </select>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="lk-lid" class="font-semibold">{{ isContractLid ? 'Contract' : 'Component' }} *</label>
          <ZoekSelect
            id="lk-lid"
            ref="eersteVeld"
            :key="lidForm.lidType"
            testid="lk-veld-lid"
            v-model="lidForm.lid_id"
            :zoek-functie="zoekFunctie"
            :weergave="lidWeergave"
            :invalid="!!lidFouten.lid_id"
            :placeholder="isContractLid ? 'Zoek een contract…' : 'Zoek een component…'"
          />
          <span v-if="lidFouten.lid_id" role="alert" data-testid="lk-fout-lid" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ lidFouten.lid_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <label for="lk-dispositie" class="font-semibold">Dispositie *</label>
            <VeldUitleg veld="dispositie" opties="dispositie" />
          </div>
          <select id="lk-dispositie" v-model="lidForm.dispositie" data-testid="lk-dispositie" :aria-invalid="!!lidFouten.dispositie" class="lk-veld">
            <option value="" disabled>— kies een dispositie —</option>
            <option v-for="o in dispositieOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
          </select>
          <span v-if="lidFouten.dispositie" role="alert" data-testid="lk-fout-dispositie" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ lidFouten.dispositie }}</span>
        </div>

        <!-- Contractuele bevestiging — alleen voor een contract-lid -->
        <fieldset v-if="isContractLid" class="flex flex-col gap-[var(--lk-space-sm)] border border-[var(--lk-color-border)] rounded-[var(--lk-radius-input)] p-[var(--lk-space-md)]" data-testid="lk-bevestiging">
          <legend class="font-semibold px-[var(--lk-space-xs)]"><span class="inline-flex items-center gap-[var(--lk-space-xs)]">Contractuele bevestiging <VeldUitleg veld="contractueel_bevestigd" /></span></legend>
          <label class="flex items-center gap-[var(--lk-space-sm)]">
            <input type="checkbox" v-model="lidForm.contractueel_bevestigd" data-testid="lk-bevestigd" />
            <span>Contractueel bevestigd (wie/wanneer wordt automatisch vastgelegd)</span>
          </label>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <label for="lk-aantal" class="font-semibold">Aantal gebruikers / licenties</label>
            <input id="lk-aantal" v-model="lidForm.bevestigd_aantal_gebruikers" type="number" min="0" data-testid="lk-aantal" class="lk-veld w-40" />
          </div>
        </fieldset>

        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Koppelen" data-testid="lk-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="koppelOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Lid ontkoppelen -->
    <Dialog v-model:visible="ontkoppelOpen" modal header="Lid ontkoppelen" data-testid="lid-ontkoppel-dialog" @hide="onHide">
      <p class="mb-[var(--lk-space-md)] max-w-prose">
        <strong>{{ teOntkoppelen?.lid_naam }}</strong> uit dit plateau ontkoppelen? Het component/contract zelf blijft bestaan.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="ontkoppelOpen = false" />
        <Button label="Ontkoppelen" severity="danger" data-testid="lid-ontkoppel-bevestig" :disabled="bezig" @click="bevestigOntkoppel" />
      </div>
    </Dialog>
  </section>
</template>
