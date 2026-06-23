<script setup>
/**
 * ContractDetail — read-only weergave + acties (ADR-020 contractregister).
 *
 * Toont de geresolveerde dekking-/kostenmodel-labels als Tags (uit de Read-resolutie,
 * incl. inactieve sleutels). Een deelcontract linkt naar zijn mantelcontract.
 * Verwijderen via Dialog; een mantel met deelcontracten of een gekoppeld contract
 * levert 409 `IN_GEBRUIK` → nette Toast. (Overzichten mantel→deel = Fase D2.)
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { useTerugNavigatie } from '@/composables/useTerugNavigatie'
import { api } from '@/api'
import {
  CONTRACTTYPE,
  CONTRACTTYPE_SEVERITY,
  LIFECYCLE,
  LIFECYCLE_SEVERITY,
  REGISTER_FOUT,
  label,
} from '../labels'
import VerantwoordelijkheidSectie from './VerantwoordelijkheidSectie.vue'
import ObjectHistoriePaneel from './ObjectHistoriePaneel.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const { terugLabel, gaTerug } = useTerugNavigatie()
const toast = useToast()
const auth = useAuthStore()

const contract = ref(null)
const fout = ref(null)
const bezig = ref(false)
const verwijderDialog = ref(false)

// Read-only register-overzichten (CD044 §1/§2).
const deelcontracten = ref([])
const gekoppeldeApps = ref([])
const mantelNaam = ref(null) // naam van het mantelcontract (parent-context in de header)
const isMantel = computed(() => contract.value?.contracttype === 'mantelcontract')

const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

function _toastFout(e) {
  const detail =
    e?.status === 409
      ? e?.message || REGISTER_FOUT[e?.code] || 'Dit contract is nog in gebruik.'
      : { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Het contract is niet (meer) gevonden.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  fout.value = null
  try {
    contract.value = await api.contracten.haal(props.id)
  } catch (e) {
    fout.value = e?.status === 404 ? 'Dit contract bestaat niet (meer).' : e?.message || 'Er ging iets mis.'
    _toastFout(e)
    return
  }
  // Overzichten (read-only). Falen stil — het contract zelf is leidend.
  try {
    gekoppeldeApps.value = await api.contracten.applicaties(props.id)
    deelcontracten.value =
      contract.value.contracttype === 'mantelcontract'
        ? await api.contracten.deelcontracten(props.id)
        : []
    // Parent-context: naam van het mantelcontract (deelcontract → mantel).
    mantelNaam.value = contract.value.mantelcontract_id
      ? (await api.contracten.haal(contract.value.mantelcontract_id).catch(() => null))?.contractnaam || null
      : null
  } catch {
    /* overzichten optioneel */
  }
}

async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.contracten.verwijder(props.id)
    verwijderDialog.value = false
    toast.add({ severity: 'success', summary: 'Contract verwijderd', life: 3000 })
    router.push({ name: 'contract-lijst' })
  } catch (e) {
    verwijderDialog.value = false
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(laad)
const typeLabel = (c) => label(CONTRACTTYPE, c)
</script>

<template>
  <section aria-labelledby="contract-detail-titel">
    <button v-if="terugLabel" type="button" data-testid="terug-knop" class="mb-[var(--cd-space-md)] inline-flex items-center text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)] hover:text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]" @click="gaTerug">{{ terugLabel }}</button>
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--cd-color-danger)]">{{ fout }}</p>

    <template v-if="contract">
      <div class="mb-[var(--cd-space-md)]">
        <div class="flex items-center gap-[var(--cd-space-md)]">
          <h1 id="contract-detail-titel" class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]">
            {{ contract.contractnaam }}
          </h1>
          <Tag data-testid="detail-type" :value="typeLabel(contract.contracttype)" :severity="CONTRACTTYPE_SEVERITY[contract.contracttype] || 'info'" />
        </div>
        <!-- Parent-context: deelcontract → mantelcontract (alleen indien aanwezig). -->
        <p v-if="contract.mantelcontract_id" data-testid="contract-valt-onder" class="mt-1 text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
          Valt onder
          <router-link :to="{ name: 'contract-detail', params: { id: contract.mantelcontract_id } }" data-testid="valt-onder-link" class="rounded px-1 text-[var(--cd-color-primary)] hover:bg-[var(--cd-color-accent)] hover:underline">{{ mantelNaam || 'mantelcontract' }}</router-link>
        </p>
      </div>

      <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-lg)] gap-y-[var(--cd-space-sm)]">
        <dt class="font-semibold">Leverancier</dt>
        <dd>{{ contract.leverancier_naam }}</dd>
        <template v-if="contract.mantelcontract_id">
          <dt class="font-semibold">Mantelcontract</dt>
          <dd>
            <router-link
              :to="{ name: 'contract-detail', params: { id: contract.mantelcontract_id } }"
              data-testid="mantel-link"
              class="text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
            >
              {{ mantelNaam || 'Naar mantelcontract' }}
            </router-link>
          </dd>
        </template>
        <dt class="font-semibold">Extern contract-ID</dt>
        <dd>{{ contract.extern_contract_id || '—' }}</dd>
        <dt class="font-semibold">Leverancier-kenmerk</dt>
        <dd>{{ contract.leverancier_contract_id || '—' }}</dd>
        <dt class="font-semibold">Begindatum</dt>
        <dd>{{ contract.begindatum || '—' }}</dd>
        <dt class="font-semibold">Einddatum</dt>
        <dd>{{ contract.einddatum || '—' }}</dd>
        <dt class="font-semibold">Vernieuwingsdatum</dt>
        <dd>{{ contract.vernieuwingsdatum || '—' }}</dd>
        <dt class="font-semibold">Dekking</dt>
        <dd data-testid="detail-dekking" class="flex flex-wrap gap-[var(--cd-space-xs)]">
          <Tag v-for="o in contract.dekking" :key="o.optie_sleutel" :value="o.label" :severity="o.actief ? 'info' : 'secondary'" />
          <span v-if="!contract.dekking?.length">—</span>
        </dd>
        <dt class="font-semibold">Kostenmodel</dt>
        <dd data-testid="detail-kostenmodel" class="flex flex-wrap gap-[var(--cd-space-xs)]">
          <Tag v-for="o in contract.kostenmodel" :key="o.optie_sleutel" :value="o.label" :severity="o.actief ? 'info' : 'secondary'" />
          <span v-if="!contract.kostenmodel?.length">—</span>
        </dd>
        <dt class="font-semibold">Omschrijving</dt>
        <dd class="whitespace-pre-wrap">{{ contract.omschrijving || '—' }}</dd>
        <dt class="font-semibold">Toelichting</dt>
        <dd class="whitespace-pre-wrap">{{ contract.toelichting || '—' }}</dd>
      </dl>

      <div class="mt-[var(--cd-space-lg)] flex flex-wrap gap-[var(--cd-space-md)]">
        <ObjectHistoriePaneel entiteit-type="contract" :entiteit-id="props.id" />
        <Button v-if="magBewerken" label="Bewerken" data-testid="bewerken-knop" @click="router.push({ name: 'contract-bewerken', params: { id: props.id } })" />
        <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="verwijder-knop" @click="verwijderDialog = true" />
      </div>

      <!-- §1 — deelcontracten (alleen bij een mantelcontract) -->
      <section
        v-if="isMantel"
        class="card mt-[var(--cd-space-lg)]"
        aria-labelledby="sectie-deelcontracten"
        data-testid="deelcontracten-sectie"
      >
        <h2 id="sectie-deelcontracten" class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]">
          Deelcontracten
        </h2>
        <DataTable :value="deelcontracten" data-testid="deelcontracten-tabel">
          <Column header="Contractnaam">
            <template #body="{ data }">
              <router-link :to="{ name: 'contract-detail', params: { id: data.id } }" data-testid="deel-link" class="text-[var(--cd-color-primary)] hover:underline">{{ data.contractnaam }}</router-link>
            </template>
          </Column>
          <Column header="Leverancier"><template #body="{ data }">{{ data.leverancier_naam }}</template></Column>
          <Column header="Begindatum"><template #body="{ data }">{{ data.begindatum || '—' }}</template></Column>
          <Column header="Einddatum"><template #body="{ data }">{{ data.einddatum || '—' }}</template></Column>
          <Column header="Dekking">
            <template #body="{ data }">
              <span class="flex flex-wrap gap-[var(--cd-space-xs)]">
                <Tag v-for="o in data.dekking" :key="o.optie_sleutel" :value="o.label" :severity="o.actief ? 'info' : 'secondary'" />
                <span v-if="!data.dekking?.length">—</span>
              </span>
            </template>
          </Column>
          <Column header="Applicaties">
            <template #body="{ data }">
              <span class="flex flex-wrap gap-x-[var(--cd-space-sm)]">
                <router-link v-for="a in data.applicaties" :key="a.id" :to="{ name: 'applicatie-detail', params: { id: a.id } }" :data-testid="`deel-app-${a.id}`" class="text-[var(--cd-color-primary)] hover:underline">{{ a.naam }}</router-link>
                <span v-if="!data.applicaties?.length">—</span>
              </span>
            </template>
          </Column>
          <template #empty><span data-testid="deelcontracten-leeg">Geen deelcontracten.</span></template>
        </DataTable>
      </section>

      <!-- §2 — direct gekoppelde applicaties (elk contracttype) -->
      <section
        class="card mt-[var(--cd-space-lg)]"
        aria-labelledby="sectie-gekoppelde-apps"
        data-testid="gekoppelde-apps-sectie"
      >
        <h2 id="sectie-gekoppelde-apps" class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]">
          Gekoppelde applicaties
        </h2>
        <DataTable :value="gekoppeldeApps" data-testid="gekoppelde-apps-tabel">
          <Column header="Applicatie">
            <template #body="{ data }">
              <router-link :to="{ name: 'applicatie-detail', params: { id: data.applicatie_id } }" data-testid="app-link" class="text-[var(--cd-color-primary)] hover:underline">{{ data.applicatie_naam }}</router-link>
            </template>
          </Column>
          <Column header="Rol"><template #body="{ data }">{{ data.relatie_rol_label }}</template></Column>
          <Column header="Status">
            <template #body="{ data }"><Tag :value="label(LIFECYCLE, data.lifecycle_status)" :severity="LIFECYCLE_SEVERITY[data.lifecycle_status] || 'info'" /></template>
          </Column>
          <template #empty><span data-testid="gekoppelde-apps-leeg">Geen gekoppelde applicaties.</span></template>
        </DataTable>
      </section>

      <!-- ADR-024 slice 2b — verantwoordelijkheden (rol-toewijzing), náást de leverancier-weergave -->
      <div class="mt-[var(--cd-space-lg)]">
        <VerantwoordelijkheidSectie :object-id="props.id" />
      </div>
    </template>

    <Dialog v-model:visible="verwijderDialog" modal header="Contract verwijderen" data-testid="verwijder-dialog">
      <p class="mb-[var(--cd-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ contract?.contractnaam }}</strong> wilt verwijderen? Een
        mantelcontract met deelcontracten of een aan applicaties gekoppeld contract kan niet
        worden verwijderd.
      </p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="verwijder-annuleer" @click="verwijderDialog = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>
  </section>
</template>
