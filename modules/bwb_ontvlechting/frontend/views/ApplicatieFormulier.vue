<script setup>
/**
 * ApplicatieFormulier — aanmaken (geen `id`) of bewerken (`id` via route-prop).
 *
 * Dropdowns worden gevoed door `applicaties.opties()` (single source); de NL-labels
 * komen uit labels.js (humanize-fallback). Client-validatie spiegelt de
 * backend-schemas; 422-veldfouten van de backend worden op de juiste velden gezet.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { api } from '@/api'
import { HOSTINGMODEL, MIGRATIEPAD, NIVEAU, label } from '../labels'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const toast = useToast()

const bewerken = computed(() => !!props.id)
const opties = ref({ hostingmodel: [], migratiepad: [], complexiteit: [], prioriteit: [] })
const laden = ref(false)
const bezig = ref(false)

const form = reactive({
  naam: '',
  beschrijving: '',
  hostingmodel: '',
  eigenaar_organisatie: '',
  eigenaar_naam: '',
  leverancier: '',
  migratiepad: '',
  complexiteit: '',
  prioriteit: '',
})
const fouten = reactive({})

const enumLabel = { hostingmodel: HOSTINGMODEL, migratiepad: MIGRATIEPAD, complexiteit: NIVEAU, prioriteit: NIVEAU }
function optieLabel(veld, code) {
  return label(enumLabel[veld], code)
}

async function init() {
  laden.value = true
  try {
    opties.value = await api.applicaties.opties()
    if (bewerken.value) {
      const a = await api.applicaties.haal(props.id)
      Object.assign(form, {
        naam: a.naam,
        beschrijving: a.beschrijving || '',
        hostingmodel: a.hostingmodel,
        eigenaar_organisatie: a.eigenaar_organisatie,
        eigenaar_naam: a.eigenaar_naam || '',
        leverancier: a.leverancier || '',
        migratiepad: a.migratiepad,
        complexiteit: a.complexiteit,
        prioriteit: a.prioriteit,
      })
    }
  } catch (e) {
    _toastFout(e)
  } finally {
    laden.value = false
  }
}

function _wis() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

function valideer() {
  _wis()
  if (!form.naam.trim()) fouten.naam = 'Naam is verplicht.'
  else if (form.naam.trim().length > 255) fouten.naam = 'Maximaal 255 tekens.'

  if (!form.eigenaar_organisatie.trim()) fouten.eigenaar_organisatie = 'Eigenaar-organisatie is verplicht.'
  else if (form.eigenaar_organisatie.trim().length > 120) fouten.eigenaar_organisatie = 'Maximaal 120 tekens.'

  for (const veld of ['hostingmodel', 'migratiepad', 'complexiteit', 'prioriteit']) {
    if (!form[veld]) fouten[veld] = 'Maak een keuze.'
  }
  return Object.keys(fouten).length === 0
}

function _payload() {
  return {
    naam: form.naam.trim(),
    beschrijving: form.beschrijving.trim() || null,
    hostingmodel: form.hostingmodel,
    eigenaar_organisatie: form.eigenaar_organisatie.trim(),
    eigenaar_naam: form.eigenaar_naam.trim() || null,
    leverancier: form.leverancier.trim() || null,
    migratiepad: form.migratiepad,
    complexiteit: form.complexiteit,
    prioriteit: form.prioriteit,
  }
}

function _serverveldfouten(e) {
  // FastAPI 422: { detail: [{ loc: [..., veld], msg }] }
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let toegepast = false
    for (const d of e.detail) {
      const veld = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (veld && veld in form) {
        fouten[veld] = d.msg || 'Ongeldige waarde.'
        toegepast = true
      }
    }
    return toegepast
  }
  return false
}

function _toastFout(e) {
  const perStatus = {
    403: 'Je hebt geen rechten voor deze actie.',
    404: 'Niet gevonden.',
    409: e?.message || 'Conflict.',
  }
  toast.add({
    severity: 'error',
    summary: 'Fout',
    detail: perStatus[e?.status] || e?.message || 'Er ging iets mis.',
    life: 5000,
  })
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    const data = _payload()
    const resultaat = bewerken.value
      ? await api.applicaties.werkBij(props.id, data)
      : await api.applicaties.maak(data)
    toast.add({
      severity: 'success',
      summary: bewerken.value ? 'Wijzigingen opgeslagen' : 'Applicatie aangemaakt',
      life: 3000,
    })
    router.push({ name: 'applicatie-detail', params: { id: resultaat.id } })
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

function annuleer() {
  if (bewerken.value) router.push({ name: 'applicatie-detail', params: { id: props.id } })
  else router.push({ name: 'applicatie-lijst' })
}

onMounted(init)
</script>

<template>
  <section aria-labelledby="form-titel">
    <h1
      id="form-titel"
      class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)] mb-[var(--cd-space-lg)]"
    >
      {{ bewerken ? 'Applicatie bewerken' : 'Nieuwe applicatie' }}
    </h1>

    <form class="card flex flex-col gap-[var(--cd-space-md)] max-w-2xl" data-testid="applicatie-form" @submit.prevent="opslaan">
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-naam" class="font-semibold">Naam *</label>
        <InputText id="f-naam" v-model="form.naam" data-testid="veld-naam" :aria-invalid="!!fouten.naam" aria-describedby="fout-naam" />
        <span v-if="fouten.naam" id="fout-naam" role="alert" data-testid="fout-naam" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.naam }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-eigenaar-org" class="font-semibold">Eigenaar-organisatie *</label>
        <InputText id="f-eigenaar-org" v-model="form.eigenaar_organisatie" data-testid="veld-eigenaar-organisatie" :aria-invalid="!!fouten.eigenaar_organisatie" aria-describedby="fout-eigenaar-organisatie" />
        <span v-if="fouten.eigenaar_organisatie" id="fout-eigenaar-organisatie" role="alert" data-testid="fout-eigenaar-organisatie" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.eigenaar_organisatie }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-eigenaar-naam" class="font-semibold">Eigenaar (naam)</label>
        <InputText id="f-eigenaar-naam" v-model="form.eigenaar_naam" data-testid="veld-eigenaar-naam" />
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-leverancier" class="font-semibold">Leverancier</label>
        <InputText id="f-leverancier" v-model="form.leverancier" data-testid="veld-leverancier" />
      </div>

      <div
        v-for="veld in ['hostingmodel', 'migratiepad', 'complexiteit', 'prioriteit']"
        :key="veld"
        class="flex flex-col gap-[var(--cd-space-xs)]"
      >
        <label :for="`f-${veld}`" class="font-semibold capitalize">{{ veld }} *</label>
        <select
          :id="`f-${veld}`"
          v-model="form[veld]"
          :data-testid="`veld-${veld}`"
          :aria-invalid="!!fouten[veld]"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        >
          <option value="" disabled>— maak een keuze —</option>
          <option v-for="code in opties[veld]" :key="code" :value="code">
            {{ optieLabel(veld, code) }}
          </option>
        </select>
        <span v-if="fouten[veld]" role="alert" :data-testid="`fout-${veld}`" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten[veld] }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-beschrijving" class="font-semibold">Beschrijving</label>
        <Textarea id="f-beschrijving" v-model="form.beschrijving" rows="4" data-testid="veld-beschrijving" />
      </div>

      <div class="flex gap-[var(--cd-space-md)] mt-[var(--cd-space-sm)]">
        <Button type="submit" label="Opslaan" data-testid="opslaan-knop" :disabled="bezig" />
        <Button type="button" label="Annuleren" severity="secondary" data-testid="annuleer-knop" @click="annuleer" />
      </div>
    </form>
  </section>
</template>
