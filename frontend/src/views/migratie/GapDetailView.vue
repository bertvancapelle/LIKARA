<script setup>
/**
 * GapDetailView — migratielaag (ADR-023 Fase E/F): gap-detail + beheer.
 * UX-A4-4: wijzigen (naam/toelichting), verwijderen, leden koppelen/ontkoppelen (component/
 * contract), en de twee read-only readiness-cijfers (technisch + contractueel) die automatisch
 * meebewegen met de leden. Baseline-/doel-plateau liggen vast na aanmaken (immutabel, FK-conventie)
 * en worden read-only getoond. Registratie/migratielaag — engine onaangeroerd; readiness is puur
 * afgeleid (geen invoer, geen tweede bron).
 *
 * Rol-gating: wijzigen/koppelen = medewerker/beheerder; verwijderen + ontkoppelen = beheerder.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Tag, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'
import ObjectHistoriePaneel from '@modules/bwb_ontvlechting/frontend/views/ObjectHistoriePaneel.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const magBeheren = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

const gap = ref(null)
const leden = ref([])
const baselineNaam = ref(null)
const doelNaam = ref(null)
const laden = ref(true)
const fout = ref(null)
const bezig = ref(false)

const TYPE_LABEL = { component: 'Component', contract: 'Contract' }

function readinessTekst(cijfer) {
  if (!cijfer || cijfer.percentage === null || cijfer.percentage === undefined) {
    return 'Nog geen leden om gereedheid uit af te leiden'
  }
  return `${cijfer.aantal_klaar} van ${cijfer.aantal_totaal} (${cijfer.percentage}%)`
}

function _foutMelding(e) {
  if (e?.code === 'LID_BESTAAT') return 'Dit lid zit al in deze gap.'
  if (e?.code === 'ONGELDIG_LID') return e?.message || 'Alleen componenten en contracten kunnen lid zijn.'
  return (
    { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.' }[e?.status] ||
    e?.message ||
    'Er ging iets mis.'
  )
}
function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  toast.add({ severity: 'error', summary: 'Fout', detail: _foutMelding(e), life: 6000 })
}

async function laadLeden() {
  leden.value = await api.gaps.leden(props.id)
}
async function herlaadGap() {
  gap.value = await api.gaps.haal(props.id) // readiness zit in de detail-respons → beweegt mee
}
async function laad() {
  laden.value = true
  fout.value = null
  try {
    await herlaadGap()
    await laadLeden()
    const [b, d] = await Promise.all([
      api.plateaus.haal(gap.value.baseline_plateau_id).catch(() => null),
      api.plateaus.haal(gap.value.doel_plateau_id).catch(() => null),
    ])
    baselineNaam.value = b?.naam || null
    doelNaam.value = d?.naam || null
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'De gap kon niet worden geladen.'
  } finally {
    laden.value = false
  }
}

// ── Bewerken (naam/toelichting + baseline/doel, UX-A4-4-aanvulling) ──────────
const editOpen = ref(false)
const editForm = reactive({ naam: '', toelichting: '', baseline_plateau_id: '', doel_plateau_id: '' })
const editFouten = reactive({})
const zoekPlateaus = (params) => api.plateaus.lijst(params)
function openBewerken() {
  editForm.naam = gap.value?.naam || ''
  editForm.toelichting = gap.value?.toelichting || ''
  editForm.baseline_plateau_id = gap.value?.baseline_plateau_id || ''
  editForm.doel_plateau_id = gap.value?.doel_plateau_id || ''
  Object.keys(editFouten).forEach((k) => delete editFouten[k])
  editOpen.value = true
}
function _valideerEdit() {
  Object.keys(editFouten).forEach((k) => delete editFouten[k])
  if (!editForm.naam.trim()) editFouten.naam = 'Naam is verplicht.'
  if (!editForm.baseline_plateau_id) editFouten.baseline_plateau_id = 'Kies een baseline-plateau.'
  if (!editForm.doel_plateau_id) editFouten.doel_plateau_id = 'Kies een doel-plateau.'
  if (editForm.baseline_plateau_id && editForm.baseline_plateau_id === editForm.doel_plateau_id)
    editFouten.doel_plateau_id = 'Baseline en doel mogen niet hetzelfde plateau zijn.'
  return Object.keys(editFouten).length === 0
}
async function bevestigBewerken() {
  if (!_valideerEdit()) return
  bezig.value = true
  try {
    await api.gaps.werkBij(props.id, {
      naam: editForm.naam.trim(),
      toelichting: editForm.toelichting.trim() || null,
      baseline_plateau_id: editForm.baseline_plateau_id,
      doel_plateau_id: editForm.doel_plateau_id,
    })
    toast.add({ severity: 'success', summary: 'Opgeslagen', life: 3000 })
    editOpen.value = false
    await laad() // readiness + baseline/doel-namen bewegen mee
  } catch (e) {
    if (e?.code === 'BASELINE_GELIJK_AAN_DOEL') {
      editFouten.doel_plateau_id = 'Baseline en doel mogen niet hetzelfde plateau zijn.'
    } else if (e?.code === 'ONGELDIG_PLATEAU') {
      editFouten.baseline_plateau_id = 'Baseline en doel moeten een plateau zijn.'
    } else {
      _toastFout(e)
    }
  } finally {
    bezig.value = false
  }
}

// ── Verwijderen ──────────────────────────────────────────────────────────────
const verwijderOpen = ref(false)
async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.gaps.verwijder(props.id)
    toast.add({ severity: 'success', summary: 'Gap verwijderd', life: 3000 })
    router.push({ name: 'gap-lijst' })
  } catch (e) {
    verwijderOpen.value = false
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Lid koppelen / ontkoppelen ───────────────────────────────────────────────
const koppelOpen = ref(false)
const eersteVeld = ref(null)
const lidForm = reactive({ lidType: 'component', lid_id: '' })
const lidFout = ref(null)
const isContractLid = computed(() => lidForm.lidType === 'contract')
const zoekFunctie = computed(() => (isContractLid.value ? (p) => api.contracten.lijst(p) : (p) => api.componenten.lijst(p)))
const lidWeergave = (item) => (isContractLid.value ? `${item.contractnaam} — ${item.leverancier_naam}` : item.naam)

function openKoppelen() {
  lidForm.lidType = 'component'
  lidForm.lid_id = ''
  lidFout.value = null
  koppelOpen.value = true
}
function onLidTypeChange() {
  lidForm.lid_id = ''
}
function focusEerste() {
  setTimeout(() => eersteVeld.value?.focus?.(), 0)
}
async function bevestigKoppel() {
  if (!lidForm.lid_id) {
    lidFout.value = `Kies een ${isContractLid.value ? 'contract' : 'component'}.`
    return
  }
  bezig.value = true
  try {
    await api.gaps.voegLid(props.id, lidForm.lid_id)
    toast.add({ severity: 'success', summary: 'Lid gekoppeld', life: 3000 })
    koppelOpen.value = false
    await Promise.all([laadLeden(), herlaadGap()]) // readiness beweegt mee
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}
// LI035 regel-acties-patroon — ontkoppelen vraagt altijd bevestiging (gedeelde dialog).
const ontkoppelOpen = ref(false)
const teOntkoppelen = ref(null)
const ontkoppelBezig = ref(false)
function vraagOntkoppel(lid) {
  teOntkoppelen.value = lid
  ontkoppelOpen.value = true
}
async function bevestigOntkoppel() {
  ontkoppelBezig.value = true
  try {
    await api.gaps.verwijderLid(props.id, teOntkoppelen.value.id)
    ontkoppelOpen.value = false
    toast.add({ severity: 'success', summary: 'Ontkoppeld', life: 2500 })
    await Promise.all([laadLeden(), herlaadGap()])
  } catch (e) {
    ontkoppelOpen.value = false
    _toastFout(e)
  } finally {
    ontkoppelBezig.value = false
  }
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="gap-detail-titel">
    <router-link :to="{ name: 'gap-lijst' }" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline">
      ← Gaps
    </router-link>

    <p v-if="fout" role="alert" data-testid="gap-detail-fout" class="my-[var(--lk-space-md)] text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden" data-testid="gap-detail-laden" class="my-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>

    <template v-else-if="gap">
      <div class="mt-[var(--lk-space-sm)] mb-[var(--lk-space-sm)]">
        <div class="flex items-center gap-[var(--lk-space-md)]">
          <h1 id="gap-detail-titel" data-testid="gap-naam" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
            {{ gap.naam }}
          </h1>
          <ObjectHistoriePaneel entiteit-type="gap" :entiteit-id="props.id" class="ml-auto" />
          <Button v-if="magBeheren" label="Bewerken" data-testid="gap-bewerken" @click="openBewerken" />
          <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="gap-verwijderen" @click="verwijderOpen = true" />
        </div>
        <!-- Parent-context: baseline → doel-plateau als subtitel in de header. -->
        <p data-testid="gap-overgang" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Overgang:
          <router-link :to="{ name: 'plateau-detail', params: { id: gap.baseline_plateau_id } }" data-testid="gap-baseline-link" class="rounded px-1 text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)] hover:underline">{{ baselineNaam || 'baseline-plateau' }}</router-link>
          →
          <router-link :to="{ name: 'plateau-detail', params: { id: gap.doel_plateau_id } }" data-testid="gap-doel-link" class="rounded px-1 text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)] hover:underline">{{ doelNaam || 'doel-plateau' }}</router-link>
        </p>
      </div>
      <p v-if="gap.toelichting" class="mb-[var(--lk-space-md)] text-[var(--lk-color-text)]">{{ gap.toelichting }}</p>

      <div class="mb-[var(--lk-space-sm)] grid gap-[var(--lk-space-md)] sm:grid-cols-2">
        <div data-testid="readiness-technisch" class="rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]">
          <h2 class="mb-1 text-[length:var(--lk-text-sm)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Technische gereedheid</h2>
          <p class="text-[length:var(--lk-text-lg)]">{{ readinessTekst(gap.readiness_technisch) }}</p>
        </div>
        <div data-testid="readiness-contractueel" class="rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]">
          <h2 class="mb-1 text-[length:var(--lk-text-sm)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Contractuele gereedheid</h2>
          <p class="text-[length:var(--lk-text-lg)]">{{ readinessTekst(gap.readiness_contractueel) }}</p>
        </div>
      </div>
      <p data-testid="readiness-uitleg" class="mb-[var(--lk-space-lg)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
        Deze cijfers worden automatisch afgeleid uit de stand van de gekoppelde leden (technisch: componenten die migratieklaar
        zijn; contractueel: bevestigde contracten op het doel-plateau). Ze zijn niet handmatig te wijzigen.
      </p>

      <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
        <h2 class="text-[length:var(--lk-text-lg)] font-semibold">Leden</h2>
        <Button v-if="magBeheren" label="+ Lid koppelen" severity="secondary" data-testid="gap-lid-koppelen" class="ml-auto" @click="openKoppelen" />
      </div>
      <DataTable :value="leden" data-testid="gap-leden-tabel" class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]">
        <Column header="Type"><template #body="{ data }"><Tag :value="TYPE_LABEL[data.lid_element_type] || data.lid_element_type" severity="secondary" /></template></Column>
        <Column field="naam" header="Naam"><template #body="{ data }">{{ data.naam || '—' }}</template></Column>
        <Column header="">
          <template #body="{ data }">
            <Button v-if="magVerwijderen" label="Ontkoppelen" severity="danger" :data-testid="`gap-lid-ontkoppel-${data.id}`" @click="vraagOntkoppel(data)" />
          </template>
        </Column>
        <template #empty>
          <span data-testid="gap-leden-leeg">
            Deze gap heeft nog geen leden.
            <template v-if="magBeheren">Koppel een component of contract met “+ Lid koppelen”.</template>
          </span>
        </template>
      </DataTable>
    </template>

    <!-- Bewerken -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Gap bewerken" data-testid="gap-edit-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="gap-edit-form" @submit.prevent="bevestigBewerken">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ge-naam" class="font-semibold">Naam *</label>
          <InputText id="ge-naam" v-model="editForm.naam" data-testid="ge-naam" :aria-invalid="!!editFouten.naam" />
          <span v-if="editFouten.naam" role="alert" data-testid="ge-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.naam }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ge-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="ge-toelichting" v-model="editForm.toelichting" rows="3" data-testid="ge-toelichting" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ge-baseline" class="font-semibold">Baseline-plateau (vertreksituatie) *</label>
          <ZoekSelect id="ge-baseline" testid="ge-baseline-zoek" v-model="editForm.baseline_plateau_id" :zoek-functie="zoekPlateaus" :initieel-weergave="baselineNaam || ''" :invalid="!!editFouten.baseline_plateau_id" placeholder="Zoek een plateau…" />
          <span v-if="editFouten.baseline_plateau_id" role="alert" data-testid="ge-fout-baseline" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.baseline_plateau_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ge-doel" class="font-semibold">Doel-plateau (eindsituatie) *</label>
          <ZoekSelect id="ge-doel" testid="ge-doel-zoek" v-model="editForm.doel_plateau_id" :zoek-functie="zoekPlateaus" :initieel-weergave="doelNaam || ''" :invalid="!!editFouten.doel_plateau_id" placeholder="Zoek een plateau…" />
          <span v-if="editFouten.doel_plateau_id" role="alert" data-testid="ge-fout-doel" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.doel_plateau_id }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="ge-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Verwijderen -->
    <Dialog v-model:visible="verwijderOpen" modal header="Gap verwijderen" data-testid="gap-verwijder-dialog">
      <p class="mb-[var(--lk-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ gap?.naam }}</strong> wilt verwijderen? De leden-koppelingen vervallen; de
        componenten, contracten en plateaus zelf blijven bestaan.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="gap-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>

    <!-- Lid ontkoppelen — gedeelde bevestiging (LI035 regel-acties-patroon). -->
    <BevestigVerwijderDialog
      v-model:visible="ontkoppelOpen"
      kop="Lid ontkoppelen"
      :omschrijving="teOntkoppelen ? `${teOntkoppelen.naam || 'Dit lid'} uit deze gap ontkoppelen? Het object zelf blijft bestaan.` : ''"
      bevestig-label="Ontkoppelen"
      :bezig="ontkoppelBezig"
      testid="gap-lid-ontkoppel"
      @bevestig="bevestigOntkoppel"
    />

    <!-- Lid koppelen -->
    <Dialog v-model:visible="koppelOpen" modal :closable="false" header="Lid koppelen" data-testid="gap-lid-dialog" @show="focusEerste">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="gap-lid-form" @submit.prevent="bevestigKoppel">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gl-type" class="font-semibold">Type lid</label>
          <select id="gl-type" v-model="lidForm.lidType" data-testid="gl-type" class="lk-veld" @change="onLidTypeChange">
            <option value="component">Component</option>
            <option value="contract">Contract</option>
          </select>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gl-lid" class="font-semibold">{{ isContractLid ? 'Contract' : 'Component' }} *</label>
          <ZoekSelect
            id="gl-lid"
            ref="eersteVeld"
            :key="lidForm.lidType"
            testid="gap-lid-zoek"
            v-model="lidForm.lid_id"
            :zoek-functie="zoekFunctie"
            :weergave="lidWeergave"
            :invalid="!!lidFout"
            :placeholder="isContractLid ? 'Zoek een contract…' : 'Zoek een component…'"
          />
          <span v-if="lidFout" role="alert" data-testid="gap-lid-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ lidFout }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Koppelen" data-testid="gap-lid-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="koppelOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
