<script setup>
/**
 * LeverancierDetail — read-only weergave + acties (ADR-020 contractregister).
 *
 * Rol-gating is affordance; de backend handhaaft. Verwijderen via bevestigings-Dialog;
 * een leverancier met contracten levert 409 `IN_GEBRUIK` → nette Toast.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { CONTRACTTYPE, CONTRACTTYPE_SEVERITY, REGISTER_FOUT, label } from '../labels'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()

const leverancier = ref(null)
const fout = ref(null)
const bezig = ref(false)
const verwijderDialog = ref(false)

const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

// §4 — contractenketen leverancier → contracten (read-only, keyset).
const contracten = ref([])
const contractenCursor = ref(null)
const contractenLaden = ref(false)

async function laadContracten({ reset = false } = {}) {
  contractenLaden.value = true
  try {
    const p = await api.contracten.lijst({
      leverancierId: props.id,
      limit: 25,
      after: reset ? undefined : contractenCursor.value,
    })
    contracten.value = reset ? p.items : contracten.value.concat(p.items)
    contractenCursor.value = p.volgende_cursor
  } catch {
    /* contractenketen optioneel; leverancier zelf is leidend */
  } finally {
    contractenLaden.value = false
  }
}

function _toastFout(e) {
  const detail =
    e?.status === 409
      ? e?.message || REGISTER_FOUT[e?.code] || 'Deze leverancier is nog in gebruik.'
      : { 403: 'Je hebt geen rechten voor deze actie.', 404: 'De leverancier is niet (meer) gevonden.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  fout.value = null
  try {
    leverancier.value = await api.leveranciers.haal(props.id)
  } catch (e) {
    fout.value = e?.status === 404 ? 'Deze leverancier bestaat niet (meer).' : e?.message || 'Er ging iets mis.'
    _toastFout(e)
  }
}

async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.leveranciers.verwijder(props.id)
    verwijderDialog.value = false
    toast.add({ severity: 'success', summary: 'Externe partij verwijderd', life: 3000 })
    router.push({ name: 'leverancier-lijst' })
  } catch (e) {
    verwijderDialog.value = false
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(async () => {
  await laad()
  if (leverancier.value) await laadContracten({ reset: true })
})

const RIJEN = [
  { veld: 'straat_huisnummer', label: 'Straat en huisnummer' },
  { veld: 'postcode', label: 'Postcode' },
  { veld: 'plaats', label: 'Plaats' },
  { veld: 'contactpersoon', label: 'Contactpersoon' },
  { veld: 'telefoon', label: 'Telefoon' },
  { veld: 'mobiel', label: 'Mobiel' },
  { veld: 'email', label: 'E-mail' },
  { veld: 'omschrijving', label: 'Omschrijving' },
]
</script>

<template>
  <section aria-labelledby="lev-detail-titel">
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--cd-color-danger)]">{{ fout }}</p>

    <template v-if="leverancier">
      <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
        <h1 id="lev-detail-titel" class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]">
          {{ leverancier.naam }}
        </h1>
      </div>

      <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-lg)] gap-y-[var(--cd-space-sm)]">
        <template v-for="r in RIJEN" :key="r.veld">
          <dt class="font-semibold">{{ r.label }}</dt>
          <dd class="whitespace-pre-wrap">{{ leverancier[r.veld] || '—' }}</dd>
        </template>
      </dl>

      <div class="mt-[var(--cd-space-lg)] flex flex-wrap gap-[var(--cd-space-md)]">
        <Button
          v-if="magBewerken"
          label="Bewerken"
          data-testid="bewerken-knop"
          @click="router.push({ name: 'leverancier-bewerken', params: { id: props.id } })"
        />
        <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="verwijder-knop" @click="verwijderDialog = true" />
      </div>

      <!-- §4 — contracten van deze leverancier (read-only, keyset) -->
      <section class="card mt-[var(--cd-space-lg)]" aria-labelledby="sectie-lev-contracten" data-testid="lev-contracten-sectie">
        <h2 id="sectie-lev-contracten" class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]">Contracten</h2>
        <DataTable :value="contracten" data-testid="lev-contracten-tabel">
          <Column header="Contractnaam">
            <template #body="{ data }">
              <router-link :to="{ name: 'contract-detail', params: { id: data.id } }" data-testid="lev-contract-link" class="text-[var(--cd-color-primary)] hover:underline">{{ data.contractnaam }}</router-link>
            </template>
          </Column>
          <Column header="Type"><template #body="{ data }"><Tag :value="label(CONTRACTTYPE, data.contracttype)" :severity="CONTRACTTYPE_SEVERITY[data.contracttype] || 'info'" /></template></Column>
          <Column header="Begindatum"><template #body="{ data }">{{ data.begindatum || '—' }}</template></Column>
          <Column header="Einddatum"><template #body="{ data }">{{ data.einddatum || '—' }}</template></Column>
          <template #empty><span data-testid="lev-contracten-leeg">Geen contracten van deze leverancier.</span></template>
        </DataTable>
        <Button v-if="contractenCursor" label="Meer laden" size="small" severity="secondary" data-testid="lev-contracten-meer" :disabled="contractenLaden" class="mt-[var(--cd-space-sm)]" @click="laadContracten()" />
      </section>
    </template>

    <Dialog v-model:visible="verwijderDialog" modal header="Externe partij verwijderen" data-testid="verwijder-dialog">
      <p class="mb-[var(--cd-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ leverancier?.naam }}</strong> wilt verwijderen? Een
        leverancier met gekoppelde contracten kan niet worden verwijderd.
      </p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="verwijder-annuleer" @click="verwijderDialog = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>
  </section>
</template>
