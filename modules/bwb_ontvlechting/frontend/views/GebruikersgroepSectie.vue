<script setup>
/**
 * GebruikersgroepSectie — gebruikersgroepen van één applicatie (in ApplicatieDetail).
 * Dialog-in-sectie (zie DatatypeSectie voor de motivatie). UX-B6-a: `organisatie` is een
 * optionele, zoekbare verwijzing naar een organisatie-partij (geen vrije tekst meer).
 */
import { computed, nextTick, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

// Organisatie-keuze: server-side zoeken, beperkt tot organisaties + burgers (aard_in).
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard_in: ['organisatie', 'burger'] })
// Afdeling-keuze: alleen organisatie_eenheden binnen de gekozen organisatie.
const zoekAfdelingen = (params) =>
  api.partijen.lijst({ ...params, aard: 'organisatie_eenheid', organisatie_id: form.organisatie_id })

const props = defineProps({ applicatieId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()

const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)

// Sortering (CD020) — null = server-default (created_at asc), niet meegestuurd.
const sortVeld = ref(null)
const sortRichting = ref(null) // 'asc' | 'desc'
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)

const dialogOpen = ref(false)
const bewerkenId = ref(null)
const bezig = ref(false)
// ADR-036a — afdeling is een structurele verwijzing (`afdeling_id`) naar een organisatie_eenheid-
// partij; geen vrije tekst meer. `afInitieel` = de naam voor de ZoekSelect in bewerk-modus.
const form = reactive({ organisatie_id: null, afdeling_id: null, aantal_gebruikers: '' })
const fouten = reactive({})
const eersteVeld = ref(null)
let laatsteTrigger = null

const orgAard = ref(null)
const orgNaam = ref('')
// Voorvul-naam voor de organisatie-ZoekSelect in bewerk-modus (ADR-036: organisatie leeft op het
// grove feit; de read levert `organisatie_naam` mee — zonder deze prop bleef het veld leeg terwijl
// `organisatie_id` wél gezet was: verwarrend en risico op ongemerkte ontkoppeling).
const orgInitieel = ref('')
// Sleutel om de organisatie-ZoekSelect te remounten (dialog-instantie leeft voort; zonder remount
// blijft de vorige `gekozenLabel` staan bij een volgende bewerk-actie).
const orgKey = ref(0)
const afInitieel = ref('')
// Sleutel om de afdeling-ZoekSelect te remounten bij org-wissel of ter-plekke-aanmaken.
const afdelingKey = ref(0)
// Afdeling-veld alleen bij een échte organisatie (geen burger, geen org-loze groep) — spiegelt de
// backend-regel dat een organisatie-loze groep geen afdeling draagt.
const toonAfdeling = computed(() => !!form.organisatie_id && orgAard.value === 'organisatie')

// Search-first: ter-plekke aanmaken leeft in de LEGE zoekstaat van de afdeling-picker. `aanmaakBevestig`
// = de zoekterm waarvoor de inline bevestiging open staat.
const aanmaakBevestig = ref('')
const afdelingBezig = ref(false)

function _resetAfdeling() {
  form.afdeling_id = null
  afInitieel.value = ''
  aanmaakBevestig.value = ''
  afdelingKey.value += 1
}

async function onOrgKies(id) {
  form.organisatie_id = id || null
  _resetAfdeling()  // een afdeling van de oude organisatie is niet meer geldig
  orgAard.value = null
  orgNaam.value = ''
  if (id) {
    try { const p = await api.partijen.haal(id); orgAard.value = p.aard; orgNaam.value = p.naam } catch { /* niet kritisch */ }
  }
}

function onAfdelingKies(id) {
  form.afdeling_id = id || null
}

// Aanmaken vanuit de lege-zoekstaat: de naam is vastgeklonken aan de zoekterm (geen apart tekstveld).
async function maakNieuweAfdeling(naam) {
  const n = (naam || '').trim()
  if (!n || !form.organisatie_id) return
  afdelingBezig.value = true
  try {
    const p = await api.partijen.maak({ aard: 'organisatie_eenheid', naam: n, organisatie_id: form.organisatie_id })
    form.afdeling_id = p.id
    afInitieel.value = p.naam       // toon + selecteer de nieuwe afdeling (remount bewijst 'in de lijst')
    aanmaakBevestig.value = ''
    afdelingKey.value += 1
  } catch (e) {
    _toastFout(e)
  } finally {
    afdelingBezig.value = false
  }
}

function _toastFout(e) {
  const per = { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { applicatie_id: props.applicatieId, limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    const p = await api.gebruikersgroepen.lijst(params)
    items.value = reset ? p.items : items.value.concat(p.items)
    cursor.value = p.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Laden van gebruikersgroepen mislukt.'
  } finally {
    laden.value = false
  }
}

function onSort(event) {
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

function _reset() {
  Object.assign(form, { organisatie_id: null, afdeling_id: null, aantal_gebruikers: '' })
  orgAard.value = null
  orgNaam.value = ''
  orgInitieel.value = ''
  orgKey.value += 1
  _resetAfdeling()
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

function openNieuw(e) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = null
  _reset()
  dialogOpen.value = true
}

async function openBewerken(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = rij.id
  _reset()
  Object.assign(form, {
    organisatie_id: rij.organisatie_id ?? null,
    afdeling_id: rij.afdeling_id ?? null,
    aantal_gebruikers: rij.aantal_gebruikers ?? '',
  })
  orgInitieel.value = rij.organisatie_naam || ''  // de organisatie-naam tonen in de ZoekSelect (ADR-036)
  orgKey.value += 1
  afInitieel.value = rij.afdeling || ''  // de afdeling-partij-naam tonen in de ZoekSelect
  afdelingKey.value += 1
  dialogOpen.value = true
  if (form.organisatie_id) {
    try { const p = await api.partijen.haal(form.organisatie_id); orgAard.value = p.aard; orgNaam.value = p.naam } catch { /* idem */ }
  }
}

function focusEerste() {
  // Ná de focustrap van PrimeVue Dialog (die anders de sluitknop focust). ZoekSelect
  // exposeert een focus()-methode; val anders terug op het root-element.
  setTimeout(() => {
    const c = eersteVeld.value
    if (c?.focus) c.focus()
    else (c?.$el ?? c)?.focus?.()
  }, 0)
}
function onHide() {
  laatsteTrigger?.focus?.()
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  // UX-B6-a — organisatie optioneel; ADR-036a — afdeling is een verwijzing (geen lengtecheck).
  if (form.aantal_gebruikers !== '' && form.aantal_gebruikers !== null) {
    const n = Number(form.aantal_gebruikers)
    if (!Number.isInteger(n) || n < 0) fouten.aantal_gebruikers = 'Geheel getal ≥ 0.'
  }
  return Object.keys(fouten).length === 0
}

function _serverveldfouten(e) {
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let t = false
    for (const d of e.detail) {
      const v = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (v && v in form) {
        fouten[v] = d.msg || 'Ongeldige waarde.'
        t = true
      }
    }
    return t
  }
  return false
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    const data = {
      organisatie_id: form.organisatie_id || null,
      // ADR-036a — alleen een afdeling meesturen als er een organisatie is (org-loos → geen afdeling).
      afdeling_id: toonAfdeling.value ? (form.afdeling_id || null) : null,
      aantal_gebruikers: form.aantal_gebruikers === '' ? null : Number(form.aantal_gebruikers),
    }
    if (bewerkenId.value) await api.gebruikersgroepen.werkBij(bewerkenId.value, data)
    else await api.gebruikersgroepen.maak({ ...data, applicatie_id: props.applicatieId })
    toast.add({ severity: 'success', summary: bewerkenId.value ? 'Opgeslagen' : 'Toegevoegd', life: 3000 })
    dialogOpen.value = false
    await laad({ reset: true })
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
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
    await api.gebruikersgroepen.verwijder(teVerwijderen.value.id)
    toast.add({ severity: 'success', summary: 'Verwijderd', life: 3000 })
    verwijderOpen.value = false
    await laad({ reset: true })
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

laad({ reset: true })
</script>

<template>
  <section class="card" aria-labelledby="sectie-gebruikersgroepen">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-gebruikersgroepen" class="text-[length:var(--lk-text-lg)] font-semibold">Gebruikersgroepen</h2>
      <Button v-if="mag" label="Toevoegen" severity="secondary" data-testid="gg-toevoegen" class="ml-auto" @click="openNieuw" />
    </div>

    <p v-if="fout" role="alert" data-testid="gg-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="gg-tabel"
      @sort="onSort"
    >
      <Column field="organisatie" header="Organisatie" sortable>
        <template #body="{ data }">
          <router-link
            v-if="data.organisatie_id"
            :to="{ name: 'partij-detail', params: { id: data.organisatie_id } }"
            :data-testid="`gg-org-link-${data.id}`"
            class="text-[var(--lk-color-primary)] hover:underline"
          >
            {{ data.organisatie_naam }}
          </router-link>
          <span v-else class="text-[var(--lk-color-text-muted)]">—</span>
        </template>
      </Column>
      <Column field="afdeling" header="Afdeling" sortable />
      <Column field="aantal_gebruikers" header="Aantal gebruikers" sortable />
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--lk-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`gg-bewerk-${data.id}`" @click="(e) => openBewerken(e, data)" />
            <Button label="Verwijderen" severity="danger" :data-testid="`gg-verwijder-${data.id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="gg-leeg">Nog geen gebruikersgroepen.</span></template>
    </DataTable>

    <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="gg-meer" :disabled="laden" class="mt-[var(--lk-space-sm)]" @click="laad()" />

    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="bewerkenId ? 'Gebruikersgroep bewerken' : 'Gebruikersgroep toevoegen'" data-testid="gg-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[20rem]" data-testid="gg-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gg-organisatie" class="font-semibold">Organisatie</label>
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <div class="flex-1">
          <ZoekSelect
            id="gg-organisatie"
            ref="eersteVeld"
            :key="orgKey"
            testid="gg-veld-organisatie"
            :model-value="form.organisatie_id"
            :zoek-functie="zoekOrganisaties"
            :initieel-weergave="orgInitieel"
            :invalid="!!fouten.organisatie_id"
            placeholder="Zoek een organisatie (optioneel)…"
            @update:model-value="onOrgKies"
          />
            </div>
            <VeldUitleg veld="gg_organisatie" />
          </div>
          <span v-if="fouten.organisatie_id" id="gg-fout-organisatie" role="alert" data-testid="gg-fout-organisatie" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.organisatie_id }}</span>
        </div>
        <!-- Afdeling (ADR-036a): kies een bestaande organisatie_eenheid van de organisatie, of maak er
             ter plekke een aan. Alleen bij een échte organisatie (geen burger, geen org-loze groep). -->
        <div v-if="toonAfdeling" class="flex flex-col gap-[var(--lk-space-xs)]">
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <label for="gg-afdeling" class="font-semibold">Afdeling</label>
            <VeldUitleg veld="gg_afdeling" />
          </div>
          <!-- Search-first: bij een lege zoekuitkomst verschijnt (met aanmaakrecht) de aanmaak-actie
               ín de dropdown, contextueel met de zoekterm + organisatie; met inline bevestiging. -->
          <ZoekSelect
            id="gg-afdeling"
            :key="`${form.organisatie_id}-${afdelingKey}`"
            testid="gg-veld-afdeling"
            :model-value="form.afdeling_id"
            :zoek-functie="zoekAfdelingen"
            :initieel-weergave="afInitieel"
            placeholder="Zoek een afdeling (optioneel)…"
            @update:model-value="onAfdelingKies"
          >
            <template #leeg="{ query }">
              <template v-if="mag && query">
                <button
                  v-if="aanmaakBevestig !== query"
                  type="button" data-testid="gg-afd-aanmaak"
                  class="w-full text-left text-[var(--lk-color-primary)] hover:underline"
                  @mousedown.prevent @click="aanmaakBevestig = query"
                >Geen afdeling ‘{{ query }}’ gevonden — ‘{{ query }}’ aanmaken onder {{ orgNaam }}</button>
                <div v-else class="flex flex-col gap-[var(--lk-space-xs)]">
                  <span class="text-[var(--lk-color-text)]">Weet je zeker? Dit maakt een nieuwe afdeling die overal herbruikbaar is.</span>
                  <span class="flex gap-[var(--lk-space-md)]">
                    <button
                      type="button" data-testid="gg-afd-aanmaak-bevestig"
                      class="font-semibold text-[var(--lk-color-primary)] hover:underline disabled:opacity-60"
                      :disabled="afdelingBezig" @mousedown.prevent @click="maakNieuweAfdeling(query)"
                    >‘{{ query }}’ aanmaken</button>
                    <button type="button" class="text-[var(--lk-color-text-muted)] hover:underline" @mousedown.prevent @click="aanmaakBevestig = ''">Annuleren</button>
                  </span>
                </div>
              </template>
              <span v-else>Geen afdeling gevonden.</span>
            </template>
          </ZoekSelect>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gg-aantal" class="font-semibold">Aantal gebruikers</label>
          <InputText id="gg-aantal" v-model="form.aantal_gebruikers" type="number" min="0" data-testid="gg-veld-aantal" :aria-invalid="!!fouten.aantal_gebruikers" aria-describedby="gg-fout-aantal" />
          <span v-if="fouten.aantal_gebruikers" id="gg-fout-aantal" role="alert" data-testid="gg-fout-aantal" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.aantal_gebruikers }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="gg-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Gebruikersgroep verwijderen" data-testid="gg-verwijder-dialog" @hide="onHide">
      <p class="mb-[var(--lk-space-md)] max-w-prose">Deze gebruikersgroep definitief verwijderen?</p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Verwijderen" severity="danger" data-testid="gg-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijder" />
      </div>
    </Dialog>
  </section>
</template>
