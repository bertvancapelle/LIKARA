<script setup>
/**
 * KoppelingSectie — koppelingen van één applicatie (in ApplicatieDetail).
 *
 * ADR-023: een koppeling IS een `flow`-relatie in het unified relatiemodel. Deze sectie
 * leest/schrijft daarom via `/relaties` (relatietype="flow") i.p.v. het in de cutover
 * vervallen `/koppelingen`-endpoint. richting/protocol/impact_bij_verbreking leven in
 * `kenmerken` (jsonb); de tegenpartij-naam wordt client-side geresolveerd uit een
 * applicatie-namenkaart (de relatie-respons draagt geen endpoint-namen).
 *
 * Dialog-in-sectie. De API kent geen "bron OF doel"-filter, dus twee disjuncte calls
 * (DB-CHECK bron != doel → geen overlap): Uitgaand (deze applicatie = bron) en Inkomend
 * (= doel), elk met eigen keyset-cursor en eigen "Meer laden". Bron/doel via applicatie-
 * pickers; bron == doel client-side geweigerd; endpoints immutabel bij bewerken.
 * ADR-023a Fase 4 — elke koppeling heeft een verplichte `naam` (eerste, sorteerbare kolom;
 * server-side sort=naam per tabel, onafhankelijk). Een 409 KOPPELING_DUBBEL opent een
 * bevestigingsdialoog → hersubmit met `negeer_waarschuwing: true`.
 */
import { computed, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, Tag, Textarea, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { IMPACT_SEVERITY, IMPACT_VERBREKING, KOPPELPROTOCOL, KOPPELRICHTING, label } from '../labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({ applicatieId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()

const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

// B4 — gecureerde labels (gelijk aan de tabel ernaast), geen uit-veldnaam-afgeleide tekst.
const VELD_LABEL = { richting: 'Richting', protocol: 'Protocol', impact_bij_verbreking: 'Impact bij verbreking' }
const OPTIE_MAP = { richting: KOPPELRICHTING, protocol: KOPPELPROTOCOL, impact_bij_verbreking: IMPACT_VERBREKING }
// Velduitleg-sleutels per flow-kenmerk (alleen richting heeft ook optie-uitleg).
const UITLEG_KEY = { richting: 'koppelrichting', protocol: 'koppelprotocol', impact_bij_verbreking: 'impact_verbreking' }
const UITLEG_OPTIES = { richting: 'koppelrichting' }

// Elke richting heeft een eigen keyset-cursor + eigen sort-state (server-side paginering +
// sortering via /relaties; Uitgaand en Inkomend sorteren onafhankelijk — ADR-023a Fase 4).
const uitgaand = reactive({ items: [], cursor: null, laden: false, sort: null, order: 'asc' })
const inkomend = reactive({ items: [], cursor: null, laden: false, sort: null, order: 'asc' })
const fout = ref(null)

// Bron/doel-pickers: server-side zoeken (CD049). `dezeAppNaam` + bron/doel-initieel
// leveren de weergavelabels voor de reeds-gekozen waarden (default-bron / bewerken).
// LI059 Slice 4 — applicaties zijn componenten met type 'applicatie' (geen /applicaties-facade meer).
const zoekApplicaties = (params) => api.componenten.lijst({ ...params, componenttype: 'applicatie' })
const dezeAppNaam = ref('')
const bronInitieel = ref('')
const doelInitieel = ref('')

// Applicatie-namenkaart (id → naam) — voor de tegenpartij-kolom (de flow-relatie draagt
// geen endpoint-namen). Eenmalig geladen; flow-koppelingen lopen tussen applicaties.
const appNamen = ref(null)
const appNaam = (id) => appNamen.value?.[id] ?? ''
async function _zorgAppNamen() {
  if (appNamen.value) return
  try {
    const p = await api.componenten.lijst({ limit: 100, componenttype: 'applicatie' })
    appNamen.value = Object.fromEntries((p.items || []).map((a) => [a.id, a.naam]))
  } catch (e) {
    appNamen.value = {}
    _toastFout(e)
  }
}

// Eén flow-relatie → de koppeling-weergavevorm die de tabel/het formulier verwacht.
function _naarKoppeling(r) {
  const tegen = r.bron_id === props.applicatieId ? r.doel_id : r.bron_id
  const k = r.kenmerken || {}
  return {
    id: r.id,
    naam: r.naam,
    bron_applicatie_id: r.bron_id,
    doel_applicatie_id: r.doel_id,
    tegenpartij_naam: appNaam(tegen),
    richting: k.richting,
    protocol: k.protocol,
    impact_bij_verbreking: k.impact_bij_verbreking,
    omschrijving: r.omschrijving,
  }
}

const dialogOpen = ref(false)
const bewerkenId = ref(null)
const bezig = ref(false)
const opties = ref({ richting: [], protocol: [], impact_bij_verbreking: [] })
const form = reactive({
  naam: '',
  bron_applicatie_id: '',
  doel_applicatie_id: '',
  richting: '',
  protocol: '',
  impact_bij_verbreking: '',
  omschrijving: '',
})
const fouten = reactive({})
const eersteVeld = ref(null)
let laatsteTrigger = null

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  const per = { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Deze koppeling bestaat al of is ongeldig.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

async function _laadRichting(state, params, reset) {
  state.laden = true
  try {
    const after = reset ? undefined : state.cursor
    const p = await api.relaties.lijst({
      relatietype: 'flow', ...params, limit: 25, after,
      sort: state.sort || undefined, order: state.sort ? state.order : undefined,
    })
    const mapped = (p.items || []).map(_naarKoppeling)
    state.items = reset ? mapped : state.items.concat(mapped)
    state.cursor = p.volgende_cursor
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van koppelingen mislukt.'
  } finally {
    state.laden = false
  }
}
const laadUitgaand = (reset = false) => _laadRichting(uitgaand, { bron_id: props.applicatieId }, reset)
const laadInkomend = (reset = false) => _laadRichting(inkomend, { doel_id: props.applicatieId }, reset)

// Server-side kolomsortering per tabel (alleen naam) — @sort → sort/order + cursor-reset + refetch.
function _onSort(state, laad, e) {
  state.sort = e.sortField || null
  state.order = e.sortOrder === 1 ? 'asc' : 'desc'
  state.cursor = null
  laad(true)
}
const onSortUitgaand = (e) => _onSort(uitgaand, laadUitgaand, e)
const onSortInkomend = (e) => _onSort(inkomend, laadInkomend, e)
const primeSortOrder = (state) => (state.sort ? (state.order === 'asc' ? 1 : -1) : 0)

async function laadBeide() {
  fout.value = null
  await _zorgAppNamen() // namenkaart vóór het mappen van de tegenpartij-kolom
  laadUitgaand(true)
  laadInkomend(true)
}

async function _laadOptiesEenmalig() {
  // richting/protocol/impact zijn vaste enums (flow-kenmerken) — opties uit de label-maps,
  // geen apart opties-endpoint meer.
  if (!opties.value.richting.length) {
    opties.value = {
      richting: Object.keys(KOPPELRICHTING),
      protocol: Object.keys(KOPPELPROTOCOL),
      impact_bij_verbreking: Object.keys(IMPACT_VERBREKING),
    }
  }
  await _zorgAppNamen()
  if (!dezeAppNaam.value) dezeAppNaam.value = appNaam(props.applicatieId)
}

function _reset() {
  Object.assign(form, {
    naam: '',
    bron_applicatie_id: props.applicatieId, // default: deze applicatie als bron
    doel_applicatie_id: '',
    richting: '',
    protocol: '',
    impact_bij_verbreking: '',
    omschrijving: '',
  })
  bronInitieel.value = dezeAppNaam.value
  doelInitieel.value = ''
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

async function openNieuw(e) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = null
  await _laadOptiesEenmalig()
  _reset()
  dialogOpen.value = true
}

async function openBewerken(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = rij.id
  await _laadOptiesEenmalig()
  Object.keys(fouten).forEach((k) => delete fouten[k])
  Object.assign(form, {
    naam: rij.naam || '',
    bron_applicatie_id: rij.bron_applicatie_id,
    doel_applicatie_id: rij.doel_applicatie_id,
    richting: rij.richting,
    protocol: rij.protocol,
    impact_bij_verbreking: rij.impact_bij_verbreking,
    omschrijving: rij.omschrijving || '',
  })
  // bron/doel zijn immutabel bij bewerken; één zijde is deze applicatie, de andere
  // de tegenpartij (server-geleverde `tegenpartij_naam`).
  const bronIsDeze = rij.bron_applicatie_id === props.applicatieId
  bronInitieel.value = bronIsDeze ? dezeAppNaam.value : rij.tegenpartij_naam
  doelInitieel.value = bronIsDeze ? rij.tegenpartij_naam : dezeAppNaam.value
  dialogOpen.value = true
}

function focusEerste() {
  // Ná de focustrap van PrimeVue Dialog (die anders de sluitknop focust).
  setTimeout(() => eersteVeld.value?.focus?.(), 0) // ZoekSelect exposeert focus()
}
function onHide() {
  laatsteTrigger?.focus?.()
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.naam.trim()) fouten.naam = 'Geef de koppeling een naam.'
  if (!form.bron_applicatie_id) fouten.bron_applicatie_id = 'Kies een bron-component.'
  if (!form.doel_applicatie_id) fouten.doel_applicatie_id = 'Kies een doel-component.'
  if (form.bron_applicatie_id && form.bron_applicatie_id === form.doel_applicatie_id)
    fouten.doel_applicatie_id = 'Bron en doel moeten verschillen.'
  for (const v of ['richting', 'protocol', 'impact_bij_verbreking']) if (!form[v]) fouten[v] = 'Maak een keuze.'
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

const _kenmerken = () => ({
  richting: form.richting,
  protocol: form.protocol,
  impact_bij_verbreking: form.impact_bij_verbreking,
})

// Eén aanmaak-call; `extra` voegt bv. `negeer_waarschuwing: true` toe bij de DUBBEL-hersubmit.
function _maakKoppeling(extra = {}) {
  return api.relaties.maak({
    bron_id: form.bron_applicatie_id,
    doel_id: form.doel_applicatie_id,
    relatietype: 'flow',
    naam: form.naam.trim(),
    kenmerken: _kenmerken(),
    omschrijving: form.omschrijving.trim() || null,
    ...extra,
  })
}

function _gelukt() {
  toast.add({ severity: 'success', summary: bewerkenId.value ? 'Opgeslagen' : 'Toegevoegd', life: 3000 })
  dialogOpen.value = false
  laadBeide() // ververs beide richtingen (relevante richting is altijd inbegrepen)
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    if (bewerkenId.value) {
      // endpoints + relatietype immutabel → alleen naam/kenmerken/omschrijving wijzigen
      await api.relaties.werkBij(bewerkenId.value, {
        naam: form.naam.trim(),
        kenmerken: _kenmerken(),
        omschrijving: form.omschrijving.trim() || null,
      })
    } else {
      await _maakKoppeling()
    }
    _gelukt()
  } catch (e) {
    // 409 KOPPELING_DUBBEL → bevestigingsdialoog (geen fout-toast); overige 409 → bestaand gedrag.
    if (!bewerkenId.value && e?.status === 409 && e?.code === 'KOPPELING_DUBBEL') {
      dubbelOpen.value = true
      return
    }
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// "Toch aanmaken" → hersubmit dezelfde data met de overrule-vlag.
const dubbelOpen = ref(false)
async function bevestigDubbel() {
  bezig.value = true
  try {
    await _maakKoppeling({ negeer_waarschuwing: true })
    dubbelOpen.value = false
    _gelukt()
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
    await api.relaties.verwijder(teVerwijderen.value.id)
    toast.add({ severity: 'success', summary: 'Verwijderd', life: 3000 })
    verwijderOpen.value = false
    laadBeide()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

laadBeide()
</script>

<template>
  <section class="card" aria-labelledby="sectie-koppelingen">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-koppelingen" class="text-[length:var(--lk-text-lg)] font-semibold">Koppelingen</h2>
      <Button v-if="mag" label="Toevoegen" severity="secondary" data-testid="kp-toevoegen" class="ml-auto" @click="openNieuw" />
    </div>

    <p v-if="fout" role="alert" data-testid="kp-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <!-- Uitgaand: deze applicatie = bron -->
    <h3 class="font-semibold mt-[var(--lk-space-sm)]">Uitgaand (dit component is bron)</h3>
    <DataTable
      :value="uitgaand.items"
      lazy
      :sort-field="uitgaand.sort"
      :sort-order="primeSortOrder(uitgaand)"
      data-testid="kp-tabel-uitgaand"
      @sort="onSortUitgaand"
    >
      <Column field="naam" header="Naam" sortable><template #body="{ data }">{{ data.naam || '—' }}</template></Column>
      <Column header="Rol"><template #body>Bron</template></Column>
      <Column header="Tegenpartij (doel)"><template #body="{ data }">{{ data.tegenpartij_naam }}</template></Column>
      <Column header="Richting"><template #body="{ data }"><Tag :value="label(KOPPELRICHTING, data.richting)" /></template></Column>
      <Column header="Protocol"><template #body="{ data }">{{ label(KOPPELPROTOCOL, data.protocol) }}</template></Column>
      <Column header="Impact"><template #body="{ data }"><Tag :value="label(IMPACT_VERBREKING, data.impact_bij_verbreking)" :severity="IMPACT_SEVERITY[data.impact_bij_verbreking] || 'info'" /></template></Column>
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--lk-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`kp-bewerk-${data.id}`" @click="(e) => openBewerken(e, data)" />
            <Button label="Verwijderen" severity="danger" :data-testid="`kp-verwijder-${data.id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="kp-leeg-uitgaand">Geen uitgaande koppelingen.</span></template>
    </DataTable>
    <Button v-if="uitgaand.cursor" label="Meer laden" severity="secondary" data-testid="kp-meer-uitgaand" :disabled="uitgaand.laden" class="mt-[var(--lk-space-sm)]" @click="laadUitgaand()" />

    <!-- Inkomend: deze applicatie = doel -->
    <h3 class="font-semibold mt-[var(--lk-space-md)]">Inkomend (dit component is doel)</h3>
    <DataTable
      :value="inkomend.items"
      lazy
      :sort-field="inkomend.sort"
      :sort-order="primeSortOrder(inkomend)"
      data-testid="kp-tabel-inkomend"
      @sort="onSortInkomend"
    >
      <Column field="naam" header="Naam" sortable><template #body="{ data }">{{ data.naam || '—' }}</template></Column>
      <Column header="Rol"><template #body>Doel</template></Column>
      <Column header="Tegenpartij (bron)"><template #body="{ data }">{{ data.tegenpartij_naam }}</template></Column>
      <Column header="Richting"><template #body="{ data }"><Tag :value="label(KOPPELRICHTING, data.richting)" /></template></Column>
      <Column header="Protocol"><template #body="{ data }">{{ label(KOPPELPROTOCOL, data.protocol) }}</template></Column>
      <Column header="Impact"><template #body="{ data }"><Tag :value="label(IMPACT_VERBREKING, data.impact_bij_verbreking)" :severity="IMPACT_SEVERITY[data.impact_bij_verbreking] || 'info'" /></template></Column>
      <Column header="">
        <template #body="{ data }">
          <div v-if="mag" class="flex gap-[var(--lk-space-sm)]">
            <Button label="Bewerken" severity="secondary" :data-testid="`kp-bewerk-${data.id}`" @click="(e) => openBewerken(e, data)" />
            <Button label="Verwijderen" severity="danger" :data-testid="`kp-verwijder-${data.id}`" @click="(e) => vraagVerwijder(e, data)" />
          </div>
        </template>
      </Column>
      <template #empty><span data-testid="kp-leeg-inkomend">Geen inkomende koppelingen.</span></template>
    </DataTable>
    <Button v-if="inkomend.cursor" label="Meer laden" severity="secondary" data-testid="kp-meer-inkomend" :disabled="inkomend.laden" class="mt-[var(--lk-space-sm)]" @click="laadInkomend()" />

    <!-- Aanmaken/bewerken -->
    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="bewerkenId ? 'Koppeling bewerken' : 'Koppeling toevoegen'" data-testid="kp-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="kp-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="kp-naam" class="font-semibold">Naam *</label>
          <input
            id="kp-naam"
            ref="eersteVeld"
            v-model="form.naam"
            data-testid="kp-veld-naam"
            :aria-invalid="!!fouten.naam"
            aria-describedby="kp-fout-naam"
            class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
          />
          <span v-if="fouten.naam" id="kp-fout-naam" role="alert" data-testid="kp-fout-naam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.naam }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="kp-bron" class="font-semibold">Bron-component *</label>
          <ZoekSelect
            id="kp-bron"
            testid="kp-veld-bron"
            v-model="form.bron_applicatie_id"
            :zoek-functie="zoekApplicaties"
            :initieel-weergave="bronInitieel"
            :disabled="!!bewerkenId"
            :invalid="!!fouten.bron_applicatie_id"
            placeholder="Zoek een component…"
          />
          <span v-if="fouten.bron_applicatie_id" role="alert" data-testid="kp-fout-bron" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.bron_applicatie_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="kp-doel" class="font-semibold">Doel-component *</label>
          <ZoekSelect
            id="kp-doel"
            testid="kp-veld-doel"
            v-model="form.doel_applicatie_id"
            :zoek-functie="zoekApplicaties"
            :initieel-weergave="doelInitieel"
            :disabled="!!bewerkenId"
            :invalid="!!fouten.doel_applicatie_id"
            aria-describedby="kp-fout-doel"
            placeholder="Zoek een component…"
          />
          <span v-if="fouten.doel_applicatie_id" id="kp-fout-doel" role="alert" data-testid="kp-fout-doel" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.doel_applicatie_id }}</span>
        </div>
        <div v-for="veld in ['richting', 'protocol', 'impact_bij_verbreking']" :key="veld" class="flex flex-col gap-[var(--lk-space-xs)]">
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <label :for="`kp-${veld}`" class="font-semibold">{{ VELD_LABEL[veld] }} *</label>
            <VeldUitleg :veld="UITLEG_KEY[veld]" :opties="UITLEG_OPTIES[veld] || null" />
          </div>
          <select :id="`kp-${veld}`" v-model="form[veld]" :data-testid="`kp-veld-${veld}`" :aria-invalid="!!fouten[veld]" class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white">
            <option value="" disabled>— maak een keuze —</option>
            <option v-for="c in opties[veld]" :key="c" :value="c">{{ label(OPTIE_MAP[veld], c) }}</option>
          </select>
          <span v-if="fouten[veld]" role="alert" :data-testid="`kp-fout-${veld}`" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten[veld] }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="kp-omschrijving" class="font-semibold">Omschrijving</label>
          <Textarea id="kp-omschrijving" v-model="form.omschrijving" rows="3" data-testid="kp-veld-omschrijving" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="kp-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Koppeling verwijderen" data-testid="kp-verwijder-dialog" @hide="onHide">
      <p class="mb-[var(--lk-space-md)] max-w-prose">Deze koppeling definitief verwijderen?</p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Verwijderen" severity="danger" data-testid="kp-verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijder" />
      </div>
    </Dialog>

    <!-- KOPPELING_DUBBEL: bevestig een tweede vergelijkbare koppeling (ADR-023a). Het
         aanmaakformulier blijft open (data behouden) zodat Annuleren terugvalt op bewerken. -->
    <Dialog v-model:visible="dubbelOpen" modal header="Vergelijkbare koppeling bestaat al" data-testid="kp-dubbel-dialog">
      <p class="mb-[var(--lk-space-md)] max-w-prose">Er bestaat al een koppeling van dit type tussen deze componenten. Wil je toch een tweede aanmaken?</p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="kp-dubbel-annuleren" @click="dubbelOpen = false" />
        <Button label="Toch aanmaken" data-testid="kp-dubbel-bevestig" :disabled="bezig" @click="bevestigDubbel" />
      </div>
    </Dialog>
  </section>
</template>
