<script setup>
/**
 * DeliverableDetailView — migratielaag (ADR-023 Fase E/F): deliverable-detail + realisatieketen.
 * UX-A4-3: wijzigen/verwijderen + de keten beheren als losse, bewuste koppelingen (Besluit 8 —
 * niets wordt afgeleid). Twee koppel-secties: "Opgeleverd door werkpakketten" (werkpakket →
 * deliverable) en "Helpt realiseren (plateaus)" (deliverable → plateau). De keten is optioneel.
 * Registratie/migratielaag — engine onaangeroerd.
 *
 * Rol-gating: koppelen/wijzigen = medewerker/beheerder; verwijderen object = beheerder; ontkoppelen lid = medewerker (ADR-050).
 * Backend-validatie: 422 ONGELDIGE_REALISATIE (verkeerd type), 409 REALISATIE_BESTAAT (dubbel).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'
import ObjectHistoriePaneel from '@modules/bwb_ontvlechting/frontend/views/ObjectHistoriePaneel.vue'
import DetailKop from '@/components/DetailKop.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const magBeheren = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))
// ADR-050 — een realisatie-koppeling ontkoppelen is een registratie-feit (membership-uitspraak)
// → medewerker; de deliverable-OBJECT vernietigen blijft beheerder (magVerwijderen).
const magOntkoppelen = computed(() => auth.hasRole('medewerker', 'beheerder'))

const deliverable = ref(null)
const keten = ref({ werkpakketten: [], plateaus: [] })
const laden = ref(true)
const fout = ref(null)
const bezig = ref(false)

const zoekWerkpakketten = (params) => api.workPackages.lijst(params)
const zoekPlateaus = (params) => api.plateaus.lijst(params)

function _foutMelding(e) {
  if (e?.code === 'REALISATIE_BESTAAT') return 'Deze koppeling bestaat al.'
  if (e?.code === 'ONGELDIGE_REALISATIE') return e?.message || 'Dit element kan hier niet gekoppeld worden.'
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

async function laadKeten() {
  keten.value = await api.deliverables.keten(props.id)
}
async function laad() {
  laden.value = true
  fout.value = null
  try {
    deliverable.value = await api.deliverables.haal(props.id)
    await laadKeten()
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'De deliverable kon niet worden geladen.'
  } finally {
    laden.value = false
  }
}

// ── Bewerken ─────────────────────────────────────────────────────────────────
const editOpen = ref(false)
const editForm = reactive({ naam: '', toelichting: '' })
const editFout = ref(null)
function openBewerken() {
  editForm.naam = deliverable.value?.naam || ''
  editForm.toelichting = deliverable.value?.toelichting || ''
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
    deliverable.value = await api.deliverables.werkBij(props.id, {
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

// ── Verwijderen ──────────────────────────────────────────────────────────────
const verwijderOpen = ref(false)
async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.deliverables.verwijder(props.id)
    toast.add({ severity: 'success', summary: 'Deliverable verwijderd', life: 3000 })
    router.push({ name: 'deliverable-lijst' })
  } catch (e) {
    verwijderOpen.value = false
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Werkpakket koppelen / ontkoppelen ────────────────────────────────────────
const wpOpen = ref(false)
const wpKeuze = ref('')
const wpFout = ref(null)
function openWpKoppel() {
  wpKeuze.value = ''
  wpFout.value = null
  wpOpen.value = true
}
async function bevestigWpKoppel() {
  if (!wpKeuze.value) {
    wpFout.value = 'Kies een werkpakket.'
    return
  }
  bezig.value = true
  try {
    await api.deliverables.koppelWerkpakket(props.id, wpKeuze.value)
    toast.add({ severity: 'success', summary: 'Werkpakket gekoppeld', life: 3000 })
    wpOpen.value = false
    await laadKeten()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}
async function ontkoppelWp(rij) {
  try {
    await api.deliverables.ontkoppelWerkpakket(props.id, rij.relatie_id)
    toast.add({ severity: 'success', summary: 'Ontkoppeld', life: 2500 })
    await laadKeten()
  } catch (e) {
    _toastFout(e)
  }
}

// ── Plateau koppelen / ontkoppelen ───────────────────────────────────────────
const plOpen = ref(false)
const plKeuze = ref('')
const plFout = ref(null)
function openPlKoppel() {
  plKeuze.value = ''
  plFout.value = null
  plOpen.value = true
}
async function bevestigPlKoppel() {
  if (!plKeuze.value) {
    plFout.value = 'Kies een plateau.'
    return
  }
  bezig.value = true
  try {
    await api.deliverables.koppelPlateau(props.id, plKeuze.value)
    toast.add({ severity: 'success', summary: 'Plateau gekoppeld', life: 3000 })
    plOpen.value = false
    await laadKeten()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}
async function ontkoppelPl(rij) {
  try {
    await api.deliverables.ontkoppelPlateau(props.id, rij.relatie_id)
    toast.add({ severity: 'success', summary: 'Ontkoppeld', life: 2500 })
    await laadKeten()
  } catch (e) {
    _toastFout(e)
  }
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="del-detail-titel">
    <router-link :to="{ name: 'deliverable-lijst' }" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline">
      ← Deliverables
    </router-link>

    <p v-if="fout" role="alert" data-testid="del-detail-fout" class="my-[var(--lk-space-md)] text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden" data-testid="del-detail-laden" class="my-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>

    <template v-else-if="deliverable">
      <!-- LI040 — gedeelde DetailKop (was een eigen kopregel met Verwijderen naast Bewerken). -->
      <DetailKop :naam="deliverable.naam" titel-id="del-detail-titel">
        <template #acties>
          <Button v-if="magBeheren" label="Bewerken" data-testid="del-bewerken" @click="openBewerken" />
          <ObjectHistoriePaneel entiteit-type="deliverable" :entiteit-id="props.id" />
        </template>
        <template v-if="magVerwijderen" #destructief>
          <Button label="Verwijderen" severity="danger" data-testid="del-verwijderen" @click="verwijderOpen = true" />
        </template>
      </DetailKop>
      <p v-if="deliverable.toelichting" class="mb-[var(--lk-space-lg)] text-[var(--lk-color-text)]">{{ deliverable.toelichting }}</p>

      <!-- Opgeleverd door werkpakketten -->
      <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
        <h2>Opgeleverd door (werkpakketten)</h2>
        <Button v-if="magBeheren" label="+ Werkpakket koppelen" severity="secondary" data-testid="del-wp-koppelen" class="ml-auto" @click="openWpKoppel" />
      </div>
      <DataTable :value="keten.werkpakketten" data-testid="del-werkpakketten-tabel" class="mb-[var(--lk-space-lg)] bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]">
        <Column field="naam" header="Werkpakket">
          <template #body="{ data }">
            <router-link :to="{ name: 'work-package-detail', params: { id: data.element_id } }" class="text-[var(--lk-color-primary)] hover:underline">{{ data.naam }}</router-link>
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <Button v-if="magOntkoppelen" label="Ontkoppelen" severity="danger" :data-testid="`del-wp-ontkoppel-${data.relatie_id}`" @click="ontkoppelWp(data)" />
          </template>
        </Column>
        <template #empty>
          <span data-testid="del-werkpakketten-leeg">
            Nog geen werkpakket gekoppeld<template v-if="magBeheren"> — koppel er een met “+ Werkpakket koppelen”. De keten is optioneel.</template>
          </span>
        </template>
      </DataTable>

      <!-- Helpt realiseren (plateaus) -->
      <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
        <h2>Helpt realiseren (plateaus)</h2>
        <Button v-if="magBeheren" label="+ Plateau koppelen" severity="secondary" data-testid="del-pl-koppelen" class="ml-auto" @click="openPlKoppel" />
      </div>
      <DataTable :value="keten.plateaus" data-testid="del-plateaus-tabel" class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]">
        <Column field="naam" header="Plateau">
          <template #body="{ data }">
            <router-link :to="{ name: 'plateau-detail', params: { id: data.element_id } }" class="text-[var(--lk-color-primary)] hover:underline">{{ data.naam }}</router-link>
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <Button v-if="magOntkoppelen" label="Ontkoppelen" severity="danger" :data-testid="`del-pl-ontkoppel-${data.relatie_id}`" @click="ontkoppelPl(data)" />
          </template>
        </Column>
        <template #empty>
          <span data-testid="del-plateaus-leeg">
            Nog geen plateau gekoppeld<template v-if="magBeheren"> — koppel er een met “+ Plateau koppelen”. De keten is optioneel.</template>
          </span>
        </template>
      </DataTable>
    </template>

    <!-- Bewerken -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Deliverable bewerken" data-testid="del-edit-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="del-edit-form" @submit.prevent="bevestigBewerken">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="de-naam" class="font-semibold">Naam *</label>
          <InputText id="de-naam" v-model="editForm.naam" data-testid="de-naam" :aria-invalid="!!editFout" />
          <span v-if="editFout" role="alert" data-testid="de-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFout }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="de-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="de-toelichting" v-model="editForm.toelichting" rows="3" data-testid="de-toelichting" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="de-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Verwijderen -->
    <Dialog v-model:visible="verwijderOpen" modal header="Deliverable verwijderen" data-testid="del-verwijder-dialog">
      <p class="mb-[var(--lk-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ deliverable?.naam }}</strong> wilt verwijderen? De keten-koppelingen
        vervallen; de werkpakketten en plateaus zelf blijven bestaan.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="del-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>

    <!-- Werkpakket koppelen -->
    <Dialog v-model:visible="wpOpen" modal :closable="false" header="Werkpakket koppelen" data-testid="del-wp-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="del-wp-form" @submit.prevent="bevestigWpKoppel">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="dwp-veld" class="font-semibold">Werkpakket *</label>
          <ZoekSelect id="dwp-veld" testid="del-wp-zoek" v-model="wpKeuze" :zoek-functie="zoekWerkpakketten" :invalid="!!wpFout" placeholder="Zoek een werkpakket…" />
          <span v-if="wpFout" role="alert" data-testid="del-wp-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ wpFout }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Koppelen" data-testid="del-wp-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="wpOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Plateau koppelen -->
    <Dialog v-model:visible="plOpen" modal :closable="false" header="Plateau koppelen" data-testid="del-pl-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="del-pl-form" @submit.prevent="bevestigPlKoppel">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="dpl-veld" class="font-semibold">Plateau *</label>
          <ZoekSelect id="dpl-veld" testid="del-pl-zoek" v-model="plKeuze" :zoek-functie="zoekPlateaus" :invalid="!!plFout" placeholder="Zoek een plateau…" />
          <span v-if="plFout" role="alert" data-testid="del-pl-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ plFout }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Koppelen" data-testid="del-pl-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="plOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
