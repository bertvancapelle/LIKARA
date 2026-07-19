<script setup>
/**
 * ContractFormulier — aanmaken/bewerken van een contract (ADR-020 contractregister).
 *
 * `contracttype = deelcontract` toont een mantel-select, client-side gefilterd op
 * type=mantelcontract én dezelfde leverancier (I1/I2-spiegeling; de backend handhaaft).
 * Dekking/kostenmodel als checkbox-groepen (actieve catalogus-opties, declaratieve set).
 * Datums vrij (B4, geen onderlinge validatie). Register-envelopes (ONGELDIGE_MANTEL/
 * LEVERANCIER_MISMATCH/MANTEL_IN_GEBRUIK) worden in-form + als Toast getoond.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Button, InputText, Textarea, useToast } from '@/primevue'
import { detailRoute } from '@/detailIngang'
import { useRouter } from '@/composables/router'
import { api } from '@/api'
import { CONTRACTTYPE, REGISTER_FOUT, label } from '../labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const toast = useToast()

const bewerken = computed(() => !!props.id)
const bezig = ref(false)

const dekkingOpties = ref([])
const kostenmodelOpties = ref([])
const TYPE_OPTIES = Object.keys(CONTRACTTYPE)
// Bewerken-modus: labels voor reeds-geselecteerde entiteit-velden (ZoekSelect, CD049).
const leverancierInitieel = ref('')
const mantelInitieel = ref('')
let _initFase = true

const form = reactive({
  leverancier_id: '',
  contracttype: '',
  mantelcontract_id: '',
  contractnaam: '',
  extern_contract_id: '',
  leverancier_contract_id: '',
  begindatum: '',
  einddatum: '',
  vernieuwingsdatum: '',
  omschrijving: '',
  toelichting: '',
})
const gekozenDekking = ref([])
const gekozenKostenmodel = ref([])
const fouten = reactive({})
const registerFout = ref(null)

const isDeel = computed(() => form.contracttype === 'deelcontract')

// ZoekSelect-koppelingen (CD049): server-side zoeken i.p.v. volledige dropdowns.
// ADR-024: de leverancier-picker (contractpartij) put uit de partijen met een TOEGESTANE aard —
// organisatie / organisatie_eenheid / externe_partij, nooit `persoon`/`burger`. Spiegelt exact de
// backend-regel (contract_service.TOEGESTANE_LEVERANCIER_AARDEN, 422 ONGELDIGE_PARTIJ): zo kan de
// gebruiker geen keuze maken die het systeem verwerpt. Term "leverancier" blijft in het contract-domein.
const LEVERANCIER_AARDEN = ['organisatie', 'organisatie_eenheid', 'externe_partij']
const zoekLeveranciers = (params) => api.partijen.lijst({ ...params, aard_in: LEVERANCIER_AARDEN })
const zoekMantels = (params) => api.contracten.lijst(params)
// Mantel client-side gespiegeld op type+leverancier (I1/I2); de backend blijft de waarheid.
const mantelFilters = computed(() => ({
  contracttype: 'mantelcontract',
  leverancier_id: form.leverancier_id || undefined,
}))

async function laadBronnen() {
  try {
    const opties = await api.contractconfig.opties()
    dekkingOpties.value = opties.dekking || []
    kostenmodelOpties.value = opties.kostenmodel || []
  } catch (e) {
    _toastFout(e)
  }
}

// Type≠deelcontract → mantel verbergen/leegmaken; leverancier gewijzigd → mantel reset
// (de mantel hoort bij één leverancier, I2). De ZoekSelect zoekt zelf server-side.
// Tijdens het initieel laden (bewerken) niet resetten — anders wist de Object.assign
// zijn eigen mantelcontract_id.
watch([() => form.contracttype, () => form.leverancier_id], ([, lev], [, oudLev]) => {
  if (_initFase) return
  if (!isDeel.value || lev !== oudLev) {
    form.mantelcontract_id = ''
    mantelInitieel.value = ''
  }
})

async function init() {
  await laadBronnen()
  if (bewerken.value) {
    try {
      const c = await api.contracten.haal(props.id)
      Object.assign(form, {
        leverancier_id: c.leverancier_id,
        contracttype: c.contracttype,
        mantelcontract_id: c.mantelcontract_id || '',
        contractnaam: c.contractnaam,
        extern_contract_id: c.extern_contract_id || '',
        leverancier_contract_id: c.leverancier_contract_id || '',
        begindatum: c.begindatum || '',
        einddatum: c.einddatum || '',
        vernieuwingsdatum: c.vernieuwingsdatum || '',
        omschrijving: c.omschrijving || '',
        toelichting: c.toelichting || '',
      })
      gekozenDekking.value = (c.dekking || []).map((o) => o.optie_sleutel)
      gekozenKostenmodel.value = (c.kostenmodel || []).map((o) => o.optie_sleutel)
      leverancierInitieel.value = c.leverancier_naam || ''
      if (c.mantelcontract_id) {
        try {
          const m = await api.contracten.haal(c.mantelcontract_id)
          mantelInitieel.value = m.contractnaam || ''
        } catch {
          /* mantel-naam optioneel; veld blijft leeg tot zoeken */
        }
      }
    } catch (e) {
      _toastFout(e)
    }
  }
  _initFase = false
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  registerFout.value = null
  if (!form.leverancier_id) fouten.leverancier_id = 'Kies een leverancier.'
  if (!form.contracttype) fouten.contracttype = 'Maak een keuze.'
  if (!form.contractnaam.trim()) fouten.contractnaam = 'Contractnaam is verplicht.'
  if (isDeel.value && !form.mantelcontract_id) fouten.mantelcontract_id = 'Kies een mantelcontract.'
  return Object.keys(fouten).length === 0
}

function _payload() {
  return {
    leverancier_id: form.leverancier_id,
    contracttype: form.contracttype,
    mantelcontract_id: isDeel.value ? form.mantelcontract_id : null,
    contractnaam: form.contractnaam.trim(),
    extern_contract_id: form.extern_contract_id.trim() || null,
    leverancier_contract_id: form.leverancier_contract_id.trim() || null,
    begindatum: form.begindatum || null,
    einddatum: form.einddatum || null,
    vernieuwingsdatum: form.vernieuwingsdatum || null,
    omschrijving: form.omschrijving.trim() || null,
    toelichting: form.toelichting.trim() || null,
    dekking: [...gekozenDekking.value],
    kostenmodel: [...gekozenKostenmodel.value],
  }
}

function _serverfout(e) {
  // Native Pydantic-veldfouten (422 met detail-array).
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let t = false
    for (const d of e.detail) {
      const v = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (v && v in form) {
        fouten[v] = d.msg || 'Ongeldige waarde.'
        t = true
      }
    }
    if (t) return true
  }
  // Register-envelopes (422/409 met fout.code) → in-form op het relevante veld + alert.
  if (e?.code && REGISTER_FOUT[e.code]) {
    const veldMap = {
      ONGELDIGE_MANTEL: 'mantelcontract_id',
      LEVERANCIER_MISMATCH: 'leverancier_id',
      MANTEL_IN_GEBRUIK: 'contracttype',
    }
    const veld = veldMap[e.code]
    const tekst = e.message || REGISTER_FOUT[e.code]
    if (veld) fouten[veld] = tekst
    registerFout.value = tekst
    return true
  }
  return false
}

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  const per = { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    const data = _payload()
    const res = bewerken.value
      ? await api.contracten.werkBij(props.id, data)
      : await api.contracten.maak(data)
    toast.add({ severity: 'success', summary: bewerken.value ? 'Wijzigingen opgeslagen' : 'Contract aangemaakt', life: 3000 })
    router.push(detailRoute('contract', res.id))
  } catch (e) {
    if (!_serverfout(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

function annuleer() {
  if (bewerken.value) router.push(detailRoute('contract', props.id))
  else router.push({ name: 'contract-lijst' })
}

onMounted(init)

const DATUMVELDEN = [
  { veld: 'begindatum', label: 'Begindatum' },
  { veld: 'einddatum', label: 'Einddatum' },
  { veld: 'vernieuwingsdatum', label: 'Vernieuwingsdatum' },
]
const TEKSTVELDEN = [
  { veld: 'extern_contract_id', label: 'Extern contract-ID' },
  { veld: 'leverancier_contract_id', label: 'Leverancier-contractkenmerk' },
]
const typeLabel = (c) => label(CONTRACTTYPE, c)
</script>

<template>
  <section aria-labelledby="contract-form-titel">
    <h1 id="contract-form-titel" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)] mb-[var(--lk-space-lg)]">
      {{ bewerken ? 'Contract bewerken' : 'Nieuw contract' }}
    </h1>

    <p v-if="registerFout" role="alert" data-testid="register-fout" class="mb-[var(--lk-space-md)] max-w-2xl rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">
      {{ registerFout }}
    </p>

    <form class="card flex flex-col gap-[var(--lk-space-md)] max-w-2xl" data-testid="contract-form" @submit.prevent="opslaan">
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="cf-leverancier" class="font-semibold">Leverancier *</label>
          <VeldUitleg veld="leverancier" />
        </div>
        <ZoekSelect
          id="cf-leverancier"
          testid="veld-leverancier"
          v-model="form.leverancier_id"
          :zoek-functie="zoekLeveranciers"
          :initieel-weergave="leverancierInitieel"
          :invalid="!!fouten.leverancier_id"
          aria-describedby="fout-leverancier"
          placeholder="Zoek een leverancier…"
        />
        <span v-if="fouten.leverancier_id" id="fout-leverancier" role="alert" data-testid="fout-leverancier_id" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.leverancier_id }}</span>
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="cf-type" class="font-semibold">Contracttype *</label>
          <VeldUitleg veld="contracttype" opties="contracttype" />
        </div>
        <select id="cf-type" v-model="form.contracttype" data-testid="veld-contracttype" :aria-invalid="!!fouten.contracttype" class="lk-veld">
          <option value="" disabled>— maak een keuze —</option>
          <option v-for="t in TYPE_OPTIES" :key="t" :value="t">{{ typeLabel(t) }}</option>
        </select>
        <span v-if="fouten.contracttype" role="alert" data-testid="fout-contracttype" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.contracttype }}</span>
      </div>

      <div v-if="isDeel" class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="cf-mantel" class="font-semibold">Mantelcontract *</label>
          <VeldUitleg veld="mantelcontract" />
        </div>
        <ZoekSelect
          id="cf-mantel"
          testid="veld-mantelcontract"
          v-model="form.mantelcontract_id"
          :zoek-functie="zoekMantels"
          :extra-filters="mantelFilters"
          :initieel-weergave="mantelInitieel"
          :invalid="!!fouten.mantelcontract_id"
          aria-describedby="fout-mantel"
          placeholder="Zoek een mantelcontract van deze leverancier…"
        />
        <span v-if="fouten.mantelcontract_id" id="fout-mantel" role="alert" data-testid="fout-mantelcontract_id" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.mantelcontract_id }}</span>
        <span v-else class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">Een deelcontract erft de leverancier van zijn mantel.</span>
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cf-naam" class="font-semibold">Contractnaam *</label>
        <InputText id="cf-naam" v-model="form.contractnaam" data-testid="veld-contractnaam" :aria-invalid="!!fouten.contractnaam" aria-describedby="fout-contractnaam" />
        <span v-if="fouten.contractnaam" id="fout-contractnaam" role="alert" data-testid="fout-contractnaam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.contractnaam }}</span>
      </div>

      <div v-for="v in TEKSTVELDEN" :key="v.veld" class="flex flex-col gap-[var(--lk-space-xs)]">
        <label :for="`cf-${v.veld}`" class="font-semibold">{{ v.label }}</label>
        <InputText :id="`cf-${v.veld}`" v-model="form[v.veld]" :data-testid="`veld-${v.veld}`" />
      </div>

      <fieldset class="flex flex-col gap-[var(--lk-space-xs)]">
        <legend class="font-semibold"><span class="inline-flex items-center gap-[var(--lk-space-xs)]">Dekking <VeldUitleg veld="dekking" opties="dekking" /></span></legend>
        <label v-for="o in dekkingOpties" :key="o.optie_sleutel" class="flex items-center gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <input v-model="gekozenDekking" type="checkbox" :value="o.optie_sleutel" :data-testid="`dekking-${o.optie_sleutel}`" />
          {{ o.label }}
        </label>
      </fieldset>

      <fieldset class="flex flex-col gap-[var(--lk-space-xs)]">
        <legend class="font-semibold"><span class="inline-flex items-center gap-[var(--lk-space-xs)]">Kostenmodel <VeldUitleg veld="kostenmodel" opties="kostenmodel" /></span></legend>
        <label v-for="o in kostenmodelOpties" :key="o.optie_sleutel" class="flex items-center gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <input v-model="gekozenKostenmodel" type="checkbox" :value="o.optie_sleutel" :data-testid="`kostenmodel-${o.optie_sleutel}`" />
          {{ o.label }}
        </label>
      </fieldset>

      <div v-for="d in DATUMVELDEN" :key="d.veld" class="flex flex-col gap-[var(--lk-space-xs)]">
        <label :for="`cf-${d.veld}`" class="font-semibold">{{ d.label }}</label>
        <input :id="`cf-${d.veld}`" v-model="form[d.veld]" type="date" :data-testid="`veld-${d.veld}`" class="lk-veld" />
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cf-omschrijving" class="font-semibold">Omschrijving</label>
        <Textarea id="cf-omschrijving" v-model="form.omschrijving" rows="2" data-testid="veld-omschrijving" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cf-toelichting" class="font-semibold">Toelichting</label>
        <Textarea id="cf-toelichting" v-model="form.toelichting" rows="3" data-testid="veld-toelichting" />
      </div>

      <div class="flex gap-[var(--lk-space-md)] mt-[var(--lk-space-sm)]">
        <Button type="submit" label="Opslaan" data-testid="opslaan-knop" :disabled="bezig" />
        <Button type="button" label="Annuleren" severity="secondary" data-testid="annuleer-knop" @click="annuleer" />
      </div>
    </form>
  </section>
</template>
