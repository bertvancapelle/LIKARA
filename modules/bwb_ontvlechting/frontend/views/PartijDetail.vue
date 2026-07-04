<script setup>
/**
 * PartijDetail — read-only weergave + acties (ADR-024 slice 2a; vervangt LeverancierDetail).
 *
 * Toont naam + aard + soort + contactvelden. De "Contracten"-sectie (tegenpartij-koppeling)
 * is alleen relevant voor een externe partij (leverancier) en wordt enkel daar getoond.
 * Rol-gating is affordance; de backend handhaaft. Verwijderen via bevestigings-Dialog;
 * een partij met contracten levert 409 `IN_GEBRUIK` → nette Toast.
 */
import { computed, reactive, ref, watch } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { useTerugNavigatie } from '@/composables/useTerugNavigatie'
import { api } from '@/api'
import { CONTRACTTYPE, CONTRACTTYPE_SEVERITY, PARTIJ_AARD, PARTIJ_SCOPE, REGISTER_FOUT, label } from '../labels'
import PartijRollenSectie from './PartijRollenSectie.vue'
import ObjectHistoriePaneel from './ObjectHistoriePaneel.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const { terugLabel, gaTerug } = useTerugNavigatie()
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
// ADR-038 — intern/extern als leesregel: bij organisatie/externe partij levert de read `scope`;
// afdeling/persoon dragen het niet (afgeleid) → geen regel.
const scopeLabel = computed(() => (partij.value?.scope ? label(PARTIJ_SCOPE, partij.value.scope) : null))

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

// LI019 — componenten van deze leverancier via de contract-keten (alleen externe partij).
const leverancierComponenten = ref([])
async function laadLeverancierComponenten() {
  try {
    leverancierComponenten.value = await api.partijen.componentenViaContract(props.id)
  } catch {
    leverancierComponenten.value = [] // optioneel; de partij zelf is leidend
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

// Leden-overzicht — server-side ADR-017 (lazy + keyset + @sort), in TWEE aparte secties:
// Afdelingen (aard=organisatie_eenheid) en Personen (aard=persoon), elk met eigen state +
// aard-filter. De "hoort bij"-filter (organisatie_id resp. afdeling_id) gaat in elke fetch.
const afdelingen = reactive({ items: [], cursor: null, laden: false, sortVeld: 'naam', sortRichting: 'asc' })
const personen = reactive({ items: [], cursor: null, laden: false, sortVeld: 'naam', sortRichting: 'asc' })
const afdelingenFilter = ref(null) // { organisatie_id, aard:'organisatie_eenheid' }
const personenFilter = ref(null)   // { organisatie_id|afdeling_id, aard:'persoon' }
const primeSort = (s) => (s.sortRichting === 'asc' ? 1 : -1)

async function _naam(id) {
  if (!id) return null
  try { return (await api.partijen.haal(id)).naam } catch { return null }
}

async function _laadSectie(state, filter, reset) {
  if (!filter) return
  state.laden = true
  try {
    const pagina = await api.partijen.lijst({
      ...filter, sort: state.sortVeld, order: state.sortRichting,
      limit: 25, after: reset ? undefined : state.cursor,
    })
    state.items = reset ? pagina.items : state.items.concat(pagina.items)
    state.cursor = pagina.volgende_cursor
  } catch {
    if (reset) state.items = []
  } finally {
    state.laden = false
  }
}
const laadAfdelingen = (reset = false) => _laadSectie(afdelingen, afdelingenFilter.value, reset)
const laadPersonen = (reset = false) => _laadSectie(personen, personenFilter.value, reset)

function _onSort(state, laad, event) {
  state.sortVeld = event.sortField
  state.sortRichting = event.sortOrder === 1 ? 'asc' : 'desc'
  state.cursor = null
  laad(true)
}
const onAfdelingenSort = (e) => _onSort(afdelingen, laadAfdelingen, e)
const onPersonenSort = (e) => _onSort(personen, laadPersonen, e)

async function laadSamenhang() {
  const p = partij.value
  if (!p) return
  if (isOrganisatieAchtig.value) {
    afdelingenFilter.value = { organisatie_id: p.id, aard: 'organisatie_eenheid' }
    personenFilter.value = { organisatie_id: p.id, aard: 'persoon' }
    await Promise.all([laadAfdelingen(true), laadPersonen(true)])
  } else if (isAfdeling.value) {
    personenFilter.value = { afdeling_id: p.id, aard: 'persoon' }
    await laadPersonen(true)
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

async function herlaad() {
  // Reset afgeleide state zodat navigatie naar een andere partij niets ouds laat staan.
  ouderOrgNaam.value = null
  ouderAfdelingNaam.value = null
  afdelingen.items = []; afdelingen.cursor = null; afdelingenFilter.value = null
  personen.items = []; personen.cursor = null; personenFilter.value = null
  contracten.value = []; contractenCursor.value = null
  leverancierComponenten.value = []
  await laad()
  if (isExternePartij.value) {
    await laadContracten({ reset: true })
    await laadLeverancierComponenten()
  }
  await laadSamenhang()
}
// Navigatie partij-detail → partij-detail hergebruikt de component-instance; een watch op
// props.id (immediate) herlaadt het scherm bij elke id-wissel (vervangt onMounted).
watch(() => props.id, () => herlaad(), { immediate: true })

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
    <button v-if="terugLabel" type="button" data-testid="terug-knop" class="mb-[var(--lk-space-md)] inline-flex items-center text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]" @click="gaTerug">{{ terugLabel }}</button>
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--lk-color-danger)]">{{ fout }}</p>

    <template v-if="partij">
      <div class="mb-[var(--lk-space-md)]">
        <div class="flex items-center gap-[var(--lk-space-md)]">
          <h1 id="partij-detail-titel" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
            {{ partij.naam }}
          </h1>
          <Tag data-testid="detail-aard" :value="aardLabel(partij.aard)" severity="info" />
        </div>
        <!-- Parent-context als subtitelregel in de header (ADR-024) -->
        <p v-if="ouderOrgNaam" data-testid="partij-hoortbij" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Hoort bij:
          <router-link :to="{ name: 'partij-detail', params: { id: partij.organisatie_id } }" data-testid="hoortbij-org-link" class="rounded px-1 text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)] hover:underline">{{ ouderOrgNaam }}</router-link><span v-if="ouderAfdelingNaam"> › <router-link :to="{ name: 'partij-detail', params: { id: partij.afdeling_id } }" data-testid="hoortbij-afd-link" class="rounded px-1 text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)] hover:underline">{{ ouderAfdelingNaam }}</router-link></span>
        </p>
      </div>

      <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--lk-space-lg)] gap-y-[var(--lk-space-sm)]">
        <!-- ADR-038 — intern/extern (alleen bij organisatie/externe partij; afgeleid bij afdeling/persoon). -->
        <template v-if="scopeLabel">
          <dt class="font-semibold">Intern of extern</dt>
          <dd data-testid="detail-scope">{{ scopeLabel }}</dd>
        </template>
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

      <div class="mt-[var(--lk-space-lg)] flex flex-wrap gap-[var(--lk-space-md)]">
        <ObjectHistoriePaneel :key="props.id" entiteit-type="partij" :entiteit-id="props.id" />
        <Button
          v-if="magBewerken"
          label="Bewerken"
          data-testid="bewerken-knop"
          @click="router.push({ name: 'partij-bewerken', params: { id: props.id } })"
        />
        <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="verwijder-knop" @click="verwijderDialog = true" />
      </div>

      <!-- Onderdelen ("hoort bij", andere kant) — gesplitst in Afdelingen + Personen -->
      <template v-if="heeftLeden">
        <!-- Afdelingen — alleen onder een organisatie(-achtige) -->
        <section v-if="isOrganisatieAchtig" class="card mt-[var(--lk-space-lg)]" data-testid="partij-afdelingen-sectie" aria-labelledby="sectie-partij-afdelingen">
          <div class="flex items-center gap-[var(--lk-space-sm)] mb-[var(--lk-space-sm)]">
            <h2 id="sectie-partij-afdelingen" class="text-[length:var(--lk-text-lg)] font-semibold">Afdelingen</h2>
            <Button v-if="magAanmaken" label="+ Afdeling" severity="secondary" data-testid="lid-afdeling" class="ml-auto" @click="nieuwLid('organisatie_eenheid')" />
          </div>
          <DataTable :value="afdelingen.items" data-testid="partij-afdelingen-tabel" lazy :sort-field="afdelingen.sortVeld" :sort-order="primeSort(afdelingen)" @sort="onAfdelingenSort">
            <Column field="naam" header="Naam" sortable>
              <template #body="{ data }">
                <router-link :to="{ name: 'partij-detail', params: { id: data.id } }" data-testid="partij-afdeling-link" class="text-[var(--lk-color-primary)] hover:underline">{{ data.naam }}</router-link>
              </template>
            </Column>
            <template #empty><span data-testid="partij-afdelingen-leeg">Geen afdelingen.</span></template>
          </DataTable>
          <div v-if="afdelingen.cursor" class="mt-[var(--lk-space-sm)]">
            <Button label="Meer laden" severity="secondary" data-testid="afdelingen-meer-laden" :loading="afdelingen.laden" @click="laadAfdelingen()" />
          </div>
        </section>

        <!-- Personen — onder een organisatie of afdeling; met e-mail + telefoon -->
        <section class="card mt-[var(--lk-space-lg)]" data-testid="partij-personen-sectie" aria-labelledby="sectie-partij-personen">
          <div class="flex items-center gap-[var(--lk-space-sm)] mb-[var(--lk-space-sm)]">
            <h2 id="sectie-partij-personen" class="text-[length:var(--lk-text-lg)] font-semibold">Personen</h2>
            <Button v-if="magAanmaken" label="+ Persoon" severity="secondary" data-testid="lid-persoon" class="ml-auto" @click="nieuwLid('persoon')" />
          </div>
          <DataTable :value="personen.items" data-testid="partij-personen-tabel" lazy :sort-field="personen.sortVeld" :sort-order="primeSort(personen)" @sort="onPersonenSort">
            <Column field="naam" header="Naam" sortable>
              <template #body="{ data }">
                <router-link :to="{ name: 'partij-detail', params: { id: data.id } }" data-testid="partij-persoon-link" class="text-[var(--lk-color-primary)] hover:underline">{{ data.naam }}</router-link>
              </template>
            </Column>
            <Column header="E-mail"><template #body="{ data }">{{ data.email || '—' }}</template></Column>
            <Column header="Telefoon"><template #body="{ data }">{{ data.telefoon || '—' }}</template></Column>
            <template #empty><span data-testid="partij-personen-leeg">Geen personen.</span></template>
          </DataTable>
          <div v-if="personen.cursor" class="mt-[var(--lk-space-sm)]">
            <Button label="Meer laden" severity="secondary" data-testid="personen-meer-laden" :loading="personen.laden" @click="laadPersonen()" />
          </div>
        </section>
      </template>

      <!-- ADR-024 slice 2b — rollen die deze partij vervult op objecten (alleen-lezen) -->
      <div class="mt-[var(--lk-space-lg)]">
        <PartijRollenSectie :key="props.id" :partij-id="props.id" />
      </div>

      <!-- Contracten (tegenpartij-koppeling) — alleen voor een externe partij -->
      <section v-if="isExternePartij" class="card mt-[var(--lk-space-lg)]" aria-labelledby="sectie-partij-contracten" data-testid="partij-contracten-sectie">
        <h2 id="sectie-partij-contracten" class="text-[length:var(--lk-text-lg)] font-semibold mb-[var(--lk-space-sm)]">Contracten</h2>
        <DataTable :value="contracten" data-testid="partij-contracten-tabel">
          <Column header="Contractnaam">
            <template #body="{ data }">
              <router-link :to="{ name: 'contract-detail', params: { id: data.id } }" data-testid="partij-contract-link" class="text-[var(--lk-color-primary)] hover:underline">{{ data.contractnaam }}</router-link>
            </template>
          </Column>
          <Column header="Type"><template #body="{ data }"><Tag :value="label(CONTRACTTYPE, data.contracttype)" :severity="CONTRACTTYPE_SEVERITY[data.contracttype] || 'info'" /></template></Column>
          <Column header="Begindatum"><template #body="{ data }">{{ data.begindatum || '—' }}</template></Column>
          <Column header="Einddatum"><template #body="{ data }">{{ data.einddatum || '—' }}</template></Column>
          <template #empty><span data-testid="partij-contracten-leeg">Geen contracten van deze partij.</span></template>
        </DataTable>
        <Button v-if="contractenCursor" label="Meer laden" severity="secondary" data-testid="partij-contracten-meer" :disabled="contractenLaden" class="mt-[var(--lk-space-sm)]" @click="laadContracten()" />
      </section>

      <!-- LI019 — Componenten via de contract-keten — alleen voor een externe partij (leverancier) -->
      <section v-if="isExternePartij" class="card mt-[var(--lk-space-lg)]" aria-labelledby="sectie-partij-componenten" data-testid="partij-componenten-sectie">
        <h2 id="sectie-partij-componenten" class="text-[length:var(--lk-text-lg)] font-semibold mb-[var(--lk-space-sm)]">Componenten</h2>
        <ul v-if="leverancierComponenten.length" class="flex flex-col gap-[var(--lk-space-xs)]">
          <li v-for="r in leverancierComponenten" :key="`${r.component_id}-${r.contract_id}`" :data-testid="`partij-component-${r.component_id}`" class="text-[length:var(--lk-text-sm)]">
            <router-link :to="{ name: 'component-detail', params: { id: r.component_id } }" data-testid="partij-component-link" class="text-[var(--lk-color-primary)] hover:underline">{{ r.component_naam }}</router-link>
            <span class="text-[var(--lk-color-text-muted)]"> (via {{ r.contract_naam }})</span>
          </li>
        </ul>
        <p v-else data-testid="partij-componenten-leeg" class="text-[var(--lk-color-text-muted)]">Geen componenten via een contract van deze leverancier.</p>
      </section>
    </template>

    <Dialog v-model:visible="verwijderDialog" modal header="Partij verwijderen" data-testid="verwijder-dialog">
      <p class="mb-[var(--lk-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ partij?.naam }}</strong> wilt verwijderen? Een partij met
        gekoppelde contracten kan niet worden verwijderd.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="verwijder-annuleer" @click="verwijderDialog = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>
  </section>
</template>
