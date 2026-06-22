<script setup>
/**
 * PartijDetail — read-only weergave + acties (ADR-024 slice 2a; vervangt LeverancierDetail).
 *
 * Toont naam + aard + soort + contactvelden. De "Contracten"-sectie (tegenpartij-koppeling)
 * is alleen relevant voor een externe partij (leverancier) en wordt enkel daar getoond.
 * Rol-gating is affordance; de backend handhaaft. Verwijderen via bevestigings-Dialog;
 * een partij met contracten levert 409 `IN_GEBRUIK` → nette Toast.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { CONTRACTTYPE, CONTRACTTYPE_SEVERITY, PARTIJ_AARD, REGISTER_FOUT, label } from '../labels'
import PartijRollenSectie from './PartijRollenSectie.vue'
import ObjectHistoriePaneel from './ObjectHistoriePaneel.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()

const partij = ref(null)
const fout = ref(null)
const bezig = ref(false)
const verwijderDialog = ref(false)

const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))
// PARTIJ·AANMAKEN — medewerker + beheerder (inhoud-patroon). Affordance voor "lid toevoegen".
const magAanmaken = computed(() => auth.hasRole('medewerker', 'beheerder'))

// UX-A2/A3 — lid toevoegen vanaf de plek waar het lid leeft, met voorgevulde context.
// Vanaf een organisatie(-achtige): organisatie = deze partij. Vanaf een afdeling: organisatie
// = de organisatie van de afdeling, afdeling = deze partij (aard altijd persoon).
function nieuwLid(aard) {
  const query = { aard }
  if (isAfdeling.value) {
    query.organisatie_id = partij.value.organisatie_id
    query.afdeling_id = partij.value.id
  } else {
    query.organisatie_id = partij.value.id
  }
  router.push({ name: 'partij-nieuw', query })
}
const isExternePartij = computed(() => partij.value?.aard === 'externe_partij')
const aardLabel = (a) => label(PARTIJ_AARD, a)

// Contractenketen — alleen voor een externe partij (tegenpartij-koppeling, read-only keyset).
const contracten = ref([])
const contractenCursor = ref(null)
const contractenLaden = ref(false)

async function laadContracten({ reset = false } = {}) {
  contractenLaden.value = true
  try {
    const p = await api.contracten.lijst({
      leverancier_id: props.id,
      limit: 25,
      after: reset ? undefined : contractenCursor.value,
    })
    contracten.value = reset ? p.items : contracten.value.concat(p.items)
    contractenCursor.value = p.volgende_cursor
  } catch {
    /* contractenketen optioneel; de partij zelf is leidend */
  } finally {
    contractenLaden.value = false
  }
}

// ADR-024 slice 2a-bis — "hoort bij", van twee kanten. Organisatie(-achtig) → onderdelen
// (afdelingen + personen); afdeling → personen + de organisatie; persoon → org (+ afdeling).
const isOrganisatieAchtig = computed(() => ['organisatie', 'externe_partij'].includes(partij.value?.aard))
const isAfdeling = computed(() => partij.value?.aard === 'organisatie_eenheid')
const isPersoon = computed(() => partij.value?.aard === 'persoon')
const heeftLeden = computed(() => isOrganisatieAchtig.value || isAfdeling.value)
const ouderOrgNaam = ref(null)
const ouderAfdelingNaam = ref(null)

// Leden-overzicht — server-side ADR-017 (lazy + keyset + @sort), zoals ComponentLijst. De
// filter (organisatie_id voor een organisatie; afdeling_id voor een afdeling) gaat in elke fetch.
const leden = ref([])
const ledenFilter = ref(null)        // { organisatie_id } | { afdeling_id }
const ledenCursor = ref(null)
const ledenLaden = ref(false)
const ledenSortVeld = ref('naam')
const ledenSortRichting = ref('asc')
const ledenPrimeSortOrder = computed(() => (ledenSortRichting.value === 'asc' ? 1 : -1))

async function _naam(id) {
  if (!id) return null
  try { return (await api.partijen.haal(id)).naam } catch { return null }
}

async function laadLeden({ reset = false } = {}) {
  if (!ledenFilter.value) return
  ledenLaden.value = true
  try {
    const pagina = await api.partijen.lijst({
      ...ledenFilter.value,
      sort: ledenSortVeld.value,
      order: ledenSortRichting.value,
      limit: 25,
      after: reset ? undefined : ledenCursor.value,
    })
    leden.value = reset ? pagina.items : leden.value.concat(pagina.items)
    ledenCursor.value = pagina.volgende_cursor
  } catch {
    if (reset) leden.value = []
  } finally {
    ledenLaden.value = false
  }
}

function onLedenSort(event) {
  ledenSortVeld.value = event.sortField
  ledenSortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  ledenCursor.value = null
  laadLeden({ reset: true })
}

async function laadSamenhang() {
  const p = partij.value
  if (!p) return
  if (isOrganisatieAchtig.value) {
    ledenFilter.value = { organisatie_id: p.id }
    await laadLeden({ reset: true })
  } else if (isAfdeling.value) {
    ledenFilter.value = { afdeling_id: p.id }
    await laadLeden({ reset: true })
    ouderOrgNaam.value = await _naam(p.organisatie_id)
  } else if (isPersoon.value) {
    ouderOrgNaam.value = await _naam(p.organisatie_id)
    ouderAfdelingNaam.value = await _naam(p.afdeling_id)
  }
}

function _toastFout(e) {
  const detail =
    e?.status === 409
      ? e?.message || REGISTER_FOUT[e?.code] || 'Deze partij is nog in gebruik.'
      : { 403: 'Je hebt geen rechten voor deze actie.', 404: 'De partij is niet (meer) gevonden.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  fout.value = null
  try {
    partij.value = await api.partijen.haal(props.id)
  } catch (e) {
    fout.value = e?.status === 404 ? 'Deze partij bestaat niet (meer).' : e?.message || 'Er ging iets mis.'
    _toastFout(e)
  }
}

async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.partijen.verwijder(props.id)
    verwijderDialog.value = false
    toast.add({ severity: 'success', summary: 'Partij verwijderd', life: 3000 })
    router.push({ name: 'partij-lijst' })
  } catch (e) {
    verwijderDialog.value = false
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(async () => {
  await laad()
  if (isExternePartij.value) await laadContracten({ reset: true })
  await laadSamenhang()
})

const RIJEN = [
  { veld: 'soort', label: 'Soort' },
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
  <section aria-labelledby="partij-detail-titel">
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--cd-color-danger)]">{{ fout }}</p>

    <template v-if="partij">
      <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
        <h1 id="partij-detail-titel" class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]">
          {{ partij.naam }}
        </h1>
        <Tag data-testid="detail-aard" :value="aardLabel(partij.aard)" severity="info" />
      </div>

      <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-lg)] gap-y-[var(--cd-space-sm)]">
        <template v-for="r in RIJEN" :key="r.veld">
          <dt class="font-semibold">{{ r.label }}</dt>
          <dd class="whitespace-pre-wrap">{{ partij[r.veld] || '—' }}</dd>
        </template>
        <!-- ADR-024 (Optie 1) — functietitel alleen voor een persoon, en alleen indien gevuld. -->
        <template v-if="isPersoon && partij.functietitel">
          <dt class="font-semibold">Functietitel</dt>
          <dd data-testid="detail-functietitel">{{ partij.functietitel }}</dd>
        </template>
      </dl>

      <!-- Hoort bij (afdeling/persoon) -->
      <p v-if="ouderOrgNaam" data-testid="partij-hoortbij" class="mt-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]">
        Hoort bij: <strong>{{ ouderOrgNaam }}</strong><span v-if="ouderAfdelingNaam"> — afdeling {{ ouderAfdelingNaam }}</span>
      </p>

      <div class="mt-[var(--cd-space-lg)] flex flex-wrap gap-[var(--cd-space-md)]">
        <ObjectHistoriePaneel entiteit-type="partij" :entiteit-id="props.id" />
        <Button
          v-if="magBewerken"
          label="Bewerken"
          data-testid="bewerken-knop"
          @click="router.push({ name: 'partij-bewerken', params: { id: props.id } })"
        />
        <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="verwijder-knop" @click="verwijderDialog = true" />
      </div>

      <!-- Onderdelen/personen ("hoort bij", andere kant) — organisatie/externe partij of afdeling -->
      <section v-if="heeftLeden" class="card mt-[var(--cd-space-lg)]" data-testid="partij-leden-sectie" aria-labelledby="sectie-partij-leden">
        <div class="flex items-center gap-[var(--cd-space-sm)] mb-[var(--cd-space-sm)]">
          <h2 id="sectie-partij-leden" class="text-[length:var(--cd-text-lg)] font-semibold">
            {{ isAfdeling ? 'Personen in deze afdeling' : 'Afdelingen en personen' }}
          </h2>
          <template v-if="magAanmaken">
            <Button
              v-if="!isAfdeling"
              label="+ Afdeling"
              severity="secondary"
              data-testid="lid-afdeling"
              class="ml-auto"
              @click="nieuwLid('organisatie_eenheid')"
            />
            <Button
              label="+ Persoon"
              severity="secondary"
              data-testid="lid-persoon"
              :class="isAfdeling ? 'ml-auto' : ''"
              @click="nieuwLid('persoon')"
            />
          </template>
        </div>
        <!-- Server-side sortering (ADR-017): lazy + @sort → sort/order + cursor-reset + refetch. -->
        <DataTable
          :value="leden"
          data-testid="partij-leden-tabel"
          lazy
          :sort-field="ledenSortVeld"
          :sort-order="ledenPrimeSortOrder"
          @sort="onLedenSort"
        >
          <Column field="naam" header="Naam" sortable>
            <template #body="{ data }">
              <router-link :to="{ name: 'partij-detail', params: { id: data.id } }" data-testid="partij-lid-link" class="text-[var(--cd-color-primary)] hover:underline">{{ data.naam }}</router-link>
            </template>
          </Column>
          <Column field="aard" header="Aard" sortable><template #body="{ data }"><Tag :value="aardLabel(data.aard)" severity="info" /></template></Column>
          <template #empty><span data-testid="partij-leden-leeg">Nog geen onderliggende partijen.</span></template>
        </DataTable>
        <div v-if="ledenCursor" class="mt-[var(--cd-space-sm)]">
          <Button label="Meer laden" severity="secondary" data-testid="leden-meer-laden" :loading="ledenLaden" @click="laadLeden()" />
        </div>
      </section>

      <!-- ADR-024 slice 2b — rollen die deze partij vervult op objecten (alleen-lezen) -->
      <div class="mt-[var(--cd-space-lg)]">
        <PartijRollenSectie :partij-id="props.id" />
      </div>

      <!-- Contracten (tegenpartij-koppeling) — alleen voor een externe partij -->
      <section v-if="isExternePartij" class="card mt-[var(--cd-space-lg)]" aria-labelledby="sectie-partij-contracten" data-testid="partij-contracten-sectie">
        <h2 id="sectie-partij-contracten" class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]">Contracten</h2>
        <DataTable :value="contracten" data-testid="partij-contracten-tabel">
          <Column header="Contractnaam">
            <template #body="{ data }">
              <router-link :to="{ name: 'contract-detail', params: { id: data.id } }" data-testid="partij-contract-link" class="text-[var(--cd-color-primary)] hover:underline">{{ data.contractnaam }}</router-link>
            </template>
          </Column>
          <Column header="Type"><template #body="{ data }"><Tag :value="label(CONTRACTTYPE, data.contracttype)" :severity="CONTRACTTYPE_SEVERITY[data.contracttype] || 'info'" /></template></Column>
          <Column header="Begindatum"><template #body="{ data }">{{ data.begindatum || '—' }}</template></Column>
          <Column header="Einddatum"><template #body="{ data }">{{ data.einddatum || '—' }}</template></Column>
          <template #empty><span data-testid="partij-contracten-leeg">Geen contracten van deze partij.</span></template>
        </DataTable>
        <Button v-if="contractenCursor" label="Meer laden" severity="secondary" data-testid="partij-contracten-meer" :disabled="contractenLaden" class="mt-[var(--cd-space-sm)]" @click="laadContracten()" />
      </section>
    </template>

    <Dialog v-model:visible="verwijderDialog" modal header="Partij verwijderen" data-testid="verwijder-dialog">
      <p class="mb-[var(--cd-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ partij?.naam }}</strong> wilt verwijderen? Een partij met
        gekoppelde contracten kan niet worden verwijderd.
      </p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="verwijder-annuleer" @click="verwijderDialog = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>
  </section>
</template>
