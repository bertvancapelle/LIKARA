<script setup>
/**
 * WorkPackageDetailView — migratielaag (ADR-023 Fase E/F): werkpakket-detail + beheer.
 * UX-A4-2: wijzigen (naam/toelichting/bovenliggend), verwijderen, en sub-werkpakketten.
 * Een sub-werkpakket toevoegen gebeurt via "+ Sub-werkpakket" — een dialog op dit detail dat
 * dit werkpakket als bovenliggend voorvult (A2/A3-prefill-lijn) en op de pagina blijft, zodat
 * de nieuwe regel meteen in de subboom verschijnt. Registratie/migratielaag — engine onaangeroerd.
 *
 * De backend handhaaft cycluspreventie (422 CYCLISCHE_HIERARCHIE) en weigert verwijderen bij
 * subpakketten (409 HEEFT_SUBPAKKETTEN); die worden hier als begrijpelijke melding getoond.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'
import ObjectHistoriePaneel from '@modules/bwb_ontvlechting/frontend/views/ObjectHistoriePaneel.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const magBeheren = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

const wp = ref(null)
const ouder = ref(null)
const subboom = ref([])
const laden = ref(true)
const fout = ref(null)
const bezig = ref(false)

const directeSubpakketten = computed(() => subboom.value.filter((i) => i.niveau === 1))
const zoekWerkpakketten = (params) => api.workPackages.lijst(params)

function _foutMelding(e) {
  if (e?.code === 'CYCLISCHE_HIERARCHIE')
    return 'Een werkpakket kan niet onder zichzelf of een onderliggend werkpakket vallen.'
  if (e?.code === 'HEEFT_SUBPAKKETTEN')
    return 'Dit werkpakket heeft onderliggende werkpakketten; ontkoppel of verwijder die eerst.'
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

async function laad() {
  laden.value = true
  fout.value = null
  try {
    wp.value = await api.workPackages.haal(props.id)
    subboom.value = await api.workPackages.subboom(props.id)
    ouder.value = wp.value.bovenliggend_id
      ? await api.workPackages.haal(wp.value.bovenliggend_id).catch(() => null)
      : null
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Het werkpakket kon niet worden geladen.'
  } finally {
    laden.value = false
  }
}
async function herlaadSubboom() {
  subboom.value = await api.workPackages.subboom(props.id)
}

// ── Bewerken (naam/toelichting/bovenliggend) ─────────────────────────────────
const editOpen = ref(false)
const editForm = reactive({ naam: '', toelichting: '', bovenliggend_id: '' })
const editFout = ref(null)

function openBewerken() {
  editForm.naam = wp.value?.naam || ''
  editForm.toelichting = wp.value?.toelichting || ''
  editForm.bovenliggend_id = wp.value?.bovenliggend_id || ''
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
    await api.workPackages.werkBij(props.id, {
      naam: editForm.naam.trim(),
      toelichting: editForm.toelichting.trim() || null,
      bovenliggend_id: editForm.bovenliggend_id || null,
    })
    toast.add({ severity: 'success', summary: 'Opgeslagen', life: 3000 })
    editOpen.value = false
    await laad()
  } catch (e) {
    _toastFout(e) // incl. cyclus-melding; blijf op het scherm
  } finally {
    bezig.value = false
  }
}

// ── Verwijderen ──────────────────────────────────────────────────────────────
const verwijderOpen = ref(false)
async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.workPackages.verwijder(props.id)
    toast.add({ severity: 'success', summary: 'Werkpakket verwijderd', life: 3000 })
    router.push({ name: 'work-package-lijst' })
  } catch (e) {
    verwijderOpen.value = false
    _toastFout(e) // incl. "heeft subpakketten"-melding; blijf op het scherm
  } finally {
    bezig.value = false
  }
}

// ── Sub-werkpakket toevoegen (dit werkpakket als bovenliggend) ───────────────
const subOpen = ref(false)
const subForm = reactive({ naam: '', toelichting: '' })
const subFout = ref(null)

function openSub() {
  subForm.naam = ''
  subForm.toelichting = ''
  subFout.value = null
  subOpen.value = true
}
async function bevestigSub() {
  if (!subForm.naam.trim()) {
    subFout.value = 'Naam is verplicht.'
    return
  }
  bezig.value = true
  try {
    await api.workPackages.maak({
      naam: subForm.naam.trim(),
      toelichting: subForm.toelichting.trim() || null,
      bovenliggend_id: props.id,
    })
    toast.add({ severity: 'success', summary: 'Sub-werkpakket toegevoegd', life: 3000 })
    subOpen.value = false
    await herlaadSubboom()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="wp-detail-titel">
    <router-link :to="{ name: 'work-package-lijst' }" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline">
      ← Werkpakketten
    </router-link>

    <p v-if="fout" role="alert" data-testid="wp-detail-fout" class="my-[var(--lk-space-md)] text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden" data-testid="wp-detail-laden" class="my-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>

    <template v-else-if="wp">
      <div class="mt-[var(--lk-space-sm)] mb-[var(--lk-space-sm)]">
        <div class="flex items-center gap-[var(--lk-space-md)]">
          <h1 id="wp-detail-titel" data-testid="wp-naam" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
            {{ wp.naam }}
          </h1>
          <ObjectHistoriePaneel entiteit-type="work_package" :entiteit-id="props.id" class="ml-auto" />
          <Button v-if="magBeheren" label="Bewerken" data-testid="wp-bewerken" @click="openBewerken" />
          <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="wp-verwijderen" @click="verwijderOpen = true" />
        </div>
        <!-- Parent-context: bovenliggend werkpakket als subtitel (alleen als niet top-niveau). -->
        <p v-if="wp.bovenliggend_id" data-testid="wp-ouder" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Onderdeel van
          <router-link :to="{ name: 'work-package-detail', params: { id: wp.bovenliggend_id } }" data-testid="wp-ouder-link" class="rounded px-1 text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)] hover:underline">{{ ouder?.naam || 'bovenliggend pakket' }}</router-link>
        </p>
      </div>
      <p v-if="wp.toelichting" class="mb-[var(--lk-space-md)] text-[var(--lk-color-text)]">{{ wp.toelichting }}</p>

      <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
        <h2 class="text-[length:var(--lk-text-lg)] font-semibold">Subpakketten ({{ directeSubpakketten.length }} direct)</h2>
        <Button v-if="magBeheren" label="+ Sub-werkpakket" severity="secondary" data-testid="wp-sub-toevoegen" class="ml-auto" @click="openSub" />
      </div>
      <DataTable :value="subboom" data-testid="wp-subboom-tabel" class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]">
        <Column field="naam" header="Naam">
          <template #body="{ data }">
            <router-link :to="{ name: 'work-package-detail', params: { id: data.id } }" class="text-[var(--lk-color-primary)] hover:underline">
              {{ data.naam }}
            </router-link>
          </template>
        </Column>
        <Column field="niveau" header="Niveau" />
        <Column header="Pad"><template #body="{ data }">{{ data.pad.join(' › ') }}</template></Column>
        <template #empty>
          <span data-testid="wp-subboom-leeg">
            Dit werkpakket heeft nog geen subpakketten.
            <template v-if="magBeheren">Voeg er een toe met “+ Sub-werkpakket”.</template>
          </span>
        </template>
      </DataTable>
    </template>

    <!-- Bewerken -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Werkpakket bewerken" data-testid="wp-edit-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="wp-edit-form" @submit.prevent="bevestigBewerken">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="we-naam" class="font-semibold">Naam *</label>
          <InputText id="we-naam" v-model="editForm.naam" data-testid="we-naam" :aria-invalid="!!editFout" />
          <span v-if="editFout" role="alert" data-testid="we-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFout }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="we-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="we-toelichting" v-model="editForm.toelichting" rows="3" data-testid="we-toelichting" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="we-bovenliggend" class="font-semibold">Bovenliggend werkpakket (leeg = top-niveau)</label>
          <ZoekSelect
            id="we-bovenliggend"
            testid="we-veld-bovenliggend"
            v-model="editForm.bovenliggend_id"
            :zoek-functie="zoekWerkpakketten"
            :initieel-weergave="ouder?.naam || ''"
            placeholder="Zoek een bovenliggend werkpakket…"
          />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="we-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Verwijderen -->
    <Dialog v-model:visible="verwijderOpen" modal header="Werkpakket verwijderen" data-testid="wp-verwijder-dialog">
      <p class="mb-[var(--lk-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ wp?.naam }}</strong> wilt verwijderen? Een werkpakket met
        onderliggende werkpakketten kan niet worden verwijderd.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="wp-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>

    <!-- Sub-werkpakket toevoegen -->
    <Dialog v-model:visible="subOpen" modal :closable="false" header="Sub-werkpakket toevoegen" data-testid="wp-sub-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="wp-sub-form" @submit.prevent="bevestigSub">
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Onder: <strong>{{ wp?.naam }}</strong>
        </p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ws-naam" class="font-semibold">Naam *</label>
          <InputText id="ws-naam" v-model="subForm.naam" data-testid="ws-naam" :aria-invalid="!!subFout" />
          <span v-if="subFout" role="alert" data-testid="ws-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ subFout }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ws-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="ws-toelichting" v-model="subForm.toelichting" rows="3" data-testid="ws-toelichting" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Toevoegen" data-testid="ws-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="subOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
