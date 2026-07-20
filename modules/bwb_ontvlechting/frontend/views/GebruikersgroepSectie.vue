<script setup>
/**
 * GebruikersgroepSectie — gebruikersgroepen van één component (in ComponentDetail).
 * ADR-055: élk componenttype dat werk ondersteunt, niet alleen applicaties.
 * Dialog-in-sectie (zie DatatypeSectie voor de motivatie). UX-B6-a: `organisatie` is een
 * optionele, zoekbare verwijzing naar een organisatie-partij (geen vrije tekst meer).
 */
import { computed, nextTick, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, useToast } from '@/primevue'
import { detailRoute } from '@/detailIngang'
import { useAuthStore } from '@/store/auth'
import { useAanstip } from '@/composables/useToonNieuweRij'
import { api } from '@/api'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'
import AfdelingSelect from './AfdelingSelect.vue'
import IdentiteitLabel from './IdentiteitLabel.vue'

// Organisatie-keuze: server-side zoeken, beperkt tot organisaties (ADR-038 — burger-doelgroepen
// zijn gewone externe organisaties; de aparte `burger`-aard bestaat niet meer).
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard_in: ['organisatie'] })
// De afdeling-keuze (incl. soepel zoeken + ter-plekke-aanmaken) loopt via de gedeelde AfdelingSelect.

const props = defineProps({ componentId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()

const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))
// LI037 — destructief = het VERWIJDEREN-recht (beheerder-only per de RBAC-matrix; het
// endpoint eist Actie.VERWIJDEREN). Vooraf weren i.p.v. een 403 pas in de dialoog — het
// bestaande detailscherm-patroon (magVerwijderen).
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)

// LI039 blok B — korte "kijk hier"-aanstip op een zojuist toegevoegde rij (gedeelde bouwsteen).
const { aangestiptId, aanstip } = useAanstip()
const rijKlasse = (data) => (data?.id === aangestiptId.value ? 'lk-aangestipt' : '')

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
// Afdeling-veld verschijnt zodra een organisatie is gekozen (ADR-038 — de picker sourcet alleen
// `aard=organisatie`; de aparte burger-aard bestaat niet meer, dus een aard-check is overbodig).
const toonAfdeling = computed(() => !!form.organisatie_id)

function _resetAfdeling() {
  form.afdeling_id = null
  afInitieel.value = ''
  afdelingKey.value += 1
}

async function onOrgKies(id) {
  form.organisatie_id = id || null
  _resetAfdeling()  // een afdeling van de oude organisatie is niet meer geldig
  orgNaam.value = ''
  if (id) {
    try { const p = await api.partijen.haal(id); orgNaam.value = p.naam } catch { /* niet kritisch */ }
  }
}

function onAfdelingKies(id) {
  form.afdeling_id = id || null
}

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  const per = { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { component_id: props.componentId, limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    const p = await api.gebruikersgroepen.lijst(params)
    items.value = reset ? p.items : items.value.concat(p.items)
    cursor.value = p.volgende_cursor
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van gebruikersgroepen mislukt.'
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
    try { const p = await api.partijen.haal(form.organisatie_id); orgNaam.value = p.naam } catch { /* idem */ }
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
  // ADR-038 — organisatie is verplicht (client-side afgevangen vóór submit; backend borgt het ook).
  if (!form.organisatie_id) fouten.organisatie_id = 'Kies een organisatie.'
  // ADR-036a — afdeling is een verwijzing (geen lengtecheck).
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
      // ADR-038 — organisatie is verplicht (client-side afgevangen in valideer()).
      organisatie_id: form.organisatie_id,
      // ADR-036a — afdeling optioneel; alleen meesturen als er een organisatie (dus afdeling-veld) is.
      afdeling_id: toonAfdeling.value ? (form.afdeling_id || null) : null,
      aantal_gebruikers: form.aantal_gebruikers === '' ? null : Number(form.aantal_gebruikers),
    }
    if (bewerkenId.value) {
      await api.gebruikersgroepen.werkBij(bewerkenId.value, data)
      toast.add({ severity: 'success', summary: 'Opgeslagen', life: 3000 })
      dialogOpen.value = false
      await laad({ reset: true })
    } else {
      // LI039 blok B — het nieuwe item is HOE DAN OOK zichtbaar: vooraan invoegen mét
      // de aanstip als drager van de uitleg — niet achter "Meer laden" (created_at asc
      // → nieuw landt achteraan). De volgende verse laadbeurt toont de natuurlijke volgorde.
      const nieuw = await api.gebruikersgroepen.maak({ ...data, component_id: props.componentId })
      toast.add({ severity: 'success', summary: 'Toegevoegd', life: 3000 })
      dialogOpen.value = false
      items.value = [nieuw, ...items.value.filter((i) => i.id !== nieuw.id)]
      aanstip(nieuw.id)
    }
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
    <div class="lk-kop-rij gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-gebruikersgroepen">Gebruikersgroepen</h2>
      <VeldUitleg veld="gebruikersgroep" norm-feit="gebruikersgroep" />
      <Button v-if="mag" label="Toevoegen" severity="secondary" data-testid="gg-toevoegen" class="ml-auto" @click="openNieuw" />
    </div>

    <p v-if="fout" role="alert" data-testid="gg-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      :row-class="rijKlasse"
      data-testid="gg-tabel"
      @sort="onSort"
    >
      <Column field="organisatie" header="Organisatie" sortable>
        <template #body="{ data }">
          <router-link
            v-if="data.organisatie_id"
            :to="detailRoute('partij', data.organisatie_id)"
            :data-testid="`gg-org-link-${data.id}`"
            class="text-[var(--lk-color-primary)] hover:underline"
          >
            {{ data.organisatie_naam }}
          </router-link>
          <span v-else class="text-[var(--lk-color-text-muted)]">—</span>
        </template>
      </Column>
      <Column field="afdeling" header="Afdeling" sortable>
        <template #body="{ data }">
          <!-- LI040: identiteit nooit ingekort — óók niet met de organisatie-kolom ernaast. -->
          <IdentiteitLabel v-if="data.afdeling" :naam="data.afdeling" :organisatie="data.organisatie_naam" />
          <span v-else class="text-[var(--lk-color-text-muted)]">—</span>
        </template>
      </Column>
      <Column field="aantal_gebruikers" header="Aantal gebruikers" sortable />
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--lk-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`gg-bewerk-${data.id}`" @click="(e) => openBewerken(e, data)" />
            <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" :data-testid="`gg-verwijder-${data.id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="gg-leeg">Nog geen gebruikersgroepen.</span></template>
    </DataTable>

    <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="gg-meer" :disabled="laden" class="mt-[var(--lk-space-sm)]" @click="laad()" />

    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="bewerkenId ? 'Gebruikersgroep bewerken' : 'Gebruikersgroep toevoegen'" data-testid="gg-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[20rem]" data-testid="gg-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gg-organisatie" class="font-semibold">Organisatie *</label>
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
            aria-describedby="gg-fout-organisatie"
            placeholder="Zoek een organisatie…"
            @update:model-value="onOrgKies"
          />
            </div>
            <VeldUitleg veld="gg_organisatie" />
          </div>
          <span v-if="fouten.organisatie_id" id="gg-fout-organisatie" role="alert" data-testid="gg-fout-organisatie" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.organisatie_id }}</span>
        </div>
        <!-- Afdeling (ADR-036a / LI032): kies een bestaande organisatie_eenheid van de organisatie, of
             maak er ter plekke een aan — via de gedeelde AfdelingSelect (getinte omrande aanmaak-zijstap,
             soepel zoeken vóór dubbel). Verschijnt zodra er een organisatie is. -->
        <div v-if="toonAfdeling" class="flex flex-col gap-[var(--lk-space-xs)]">
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <label for="gg-afdeling" class="font-semibold">Afdeling</label>
            <VeldUitleg veld="gg_afdeling" />
          </div>
          <AfdelingSelect
            id="gg-afdeling"
            testid="gg-afdeling"
            :key="`${form.organisatie_id}-${afdelingKey}`"
            :model-value="form.afdeling_id"
            :partij-id="form.organisatie_id"
            :initieel-weergave="afInitieel"
            :mag-aanmaken="mag"
            :org-naam="orgNaam"
            placeholder="Zoek een afdeling (optioneel)…"
            @update:model-value="onAfdelingKies"
          />
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
