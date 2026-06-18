<script setup>
/**
 * ComponentFormulier — aanmaken/bewerken van een component (ADR-021 W1 / CD054b).
 *
 * Convergente aanmaak: het type `applicatie` is wél kiesbaar — opslaan maakt atomair
 * het applicatie-subtype (backend) en leidt door naar ApplicatieDetail, waar de
 * checklist direct zichtbaar is. Overige typen → ComponentDetail. Componenttype-opties
 * komen uit /componenten/opties (catalogus); hostingmodel uit de enum. Naam + type zijn
 * verplicht; overige velden optioneel. Het TYPE wijzigen van/naar applicatie blijft
 * beschermd (backend SUBTYPE_BESCHERMD) — daarom redirect bewerken van een subtype hier
 * naar ApplicatieDetail.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { api } from '@/api'
import { HOSTINGMODEL, REGISTER_FOUT, label } from '../labels'
import ZoekSelect from './ZoekSelect.vue'

// Eigenaar-organisatie: server-side zoeken, beperkt tot partijen met aard=organisatie (UX-B6-b).
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const toast = useToast()

const bewerken = computed(() => !!props.id)
const typeOpties = ref([]) // [{ optie_sleutel, label }] — incl. 'applicatie' (convergent)
const HOSTING_OPTIES = Object.keys(HOSTINGMODEL)
const laden = ref(false)
const bezig = ref(false)
// ADR-022 Fase C: server-hint — bij een "gevuld" component is het type vergrendeld.
// De PATCH herevalueert server-side; dit is enkel UI-affordance.
const typeVergrendeld = ref(false)

const form = reactive({
  naam: '',
  componenttype: '',
  hostingmodel: 'onbekend',
  eigenaar_organisatie_id: null,
  eigenaar_organisatie_naam: '',  // initieel label voor de ZoekSelect (bewerken-modus)
  eigenaar_naam: '',
  leverancier: '',
  beschrijving: '',
})
const fouten = reactive({})

const hosting = (c) => label(HOSTINGMODEL, c)

function _toastFout(e) {
  const detail =
    e?.code && REGISTER_FOUT[e.code]
      ? e?.message || REGISTER_FOUT[e.code]
      : { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function init() {
  laden.value = true
  try {
    const opties = await api.componenten.opties()
    // Convergente aanmaak (CD054b W1): 'applicatie' is wél kiesbaar.
    typeOpties.value = opties.componenttype || []
    if (bewerken.value) {
      const c = await api.componenten.haal(props.id)
      if (c.heeft_applicatie_subtype) {
        // Subtypen bewerk je op de applicatie zelf — niet hier.
        toast.add({ severity: 'info', summary: 'Applicatie-component', detail: 'Bewerk dit via de applicatie.', life: 4000 })
        router.replace({ name: 'applicatie-detail', params: { id: props.id } })
        return
      }
      typeVergrendeld.value = c.type_wijzigbaar === false
      Object.assign(form, {
        naam: c.naam,
        componenttype: c.componenttype,
        hostingmodel: c.hostingmodel,
        eigenaar_organisatie_id: c.eigenaar_organisatie_id ?? null,
        eigenaar_organisatie_naam: c.eigenaar_organisatie_naam || '',
        eigenaar_naam: c.eigenaar_naam || '',
        leverancier: c.leverancier || '',
        beschrijving: c.beschrijving || '',
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
  if (!form.componenttype) fouten.componenttype = 'Maak een keuze.'
  return Object.keys(fouten).length === 0
}

function _payload() {
  return {
    naam: form.naam.trim(),
    componenttype: form.componenttype,
    hostingmodel: form.hostingmodel,
    eigenaar_organisatie_id: form.eigenaar_organisatie_id || null,
    eigenaar_naam: form.eigenaar_naam.trim() || null,
    leverancier: form.leverancier.trim() || null,
    beschrijving: form.beschrijving.trim() || null,
  }
}

function _serverveldfouten(e) {
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

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    const data = _payload()
    const resultaat = bewerken.value
      ? await api.componenten.werkBij(props.id, data)
      : await api.componenten.maak(data)
    // Convergentie: een applicatie-(sub)type opent op ApplicatieDetail (checklist direct
    // zichtbaar); shared-PK ⇒ resultaat.id is zowel component- als applicatie-id.
    const naarApplicatie = resultaat.heeft_applicatie_subtype || form.componenttype === 'applicatie'
    toast.add({
      severity: 'success',
      summary: bewerken.value ? 'Wijzigingen opgeslagen' : naarApplicatie ? 'Applicatie aangemaakt' : 'Component aangemaakt',
      life: 3000,
    })
    router.push({
      name: naarApplicatie ? 'applicatie-detail' : 'component-detail',
      params: { id: resultaat.id },
    })
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

function annuleer() {
  if (bewerken.value) router.push({ name: 'component-detail', params: { id: props.id } })
  else router.push({ name: 'component-lijst' })
}

onMounted(init)
</script>

<template>
  <section aria-labelledby="form-titel">
    <h1
      id="form-titel"
      class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)] mb-[var(--cd-space-lg)]"
    >
      {{ bewerken ? 'Component bewerken' : 'Nieuw component' }}
    </h1>

    <form class="card flex flex-col gap-[var(--cd-space-md)] max-w-2xl" data-testid="component-form" @submit.prevent="opslaan">
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-naam" class="font-semibold">Naam *</label>
        <InputText id="f-naam" v-model="form.naam" data-testid="veld-naam" :aria-invalid="!!fouten.naam" aria-describedby="fout-naam" />
        <span v-if="fouten.naam" id="fout-naam" role="alert" data-testid="fout-naam" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.naam }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-componenttype" class="font-semibold">Type *</label>
        <select
          id="f-componenttype"
          v-model="form.componenttype"
          data-testid="veld-componenttype"
          :aria-invalid="!!fouten.componenttype"
          :disabled="typeVergrendeld"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60"
        >
          <option value="" disabled>— maak een keuze —</option>
          <option v-for="o in typeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
        <span
          v-if="typeVergrendeld"
          data-testid="type-vergrendeld-hint"
          class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]"
        >
          Type vergrendeld: dit component bevat al gegevens. Verwijder het component om het type te wijzigen.
        </span>
        <span v-if="fouten.componenttype" role="alert" data-testid="fout-componenttype" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.componenttype }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-hostingmodel" class="font-semibold">Hostingmodel</label>
        <select
          id="f-hostingmodel"
          v-model="form.hostingmodel"
          data-testid="veld-hostingmodel"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        >
          <option v-for="h in HOSTING_OPTIES" :key="h" :value="h">{{ hosting(h) }}</option>
        </select>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-eigenaar-org" class="font-semibold">Eigenaar-organisatie</label>
        <ZoekSelect
          id="f-eigenaar-org"
          testid="veld-eigenaar-organisatie"
          v-model="form.eigenaar_organisatie_id"
          :initieel-weergave="form.eigenaar_organisatie_naam"
          :zoek-functie="zoekOrganisaties"
          placeholder="Zoek een organisatie (optioneel)…"
        />
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-eigenaar-naam" class="font-semibold">Eigenaar (naam)</label>
        <InputText id="f-eigenaar-naam" v-model="form.eigenaar_naam" data-testid="veld-eigenaar-naam" />
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="f-leverancier" class="font-semibold">Leverancier</label>
        <InputText id="f-leverancier" v-model="form.leverancier" data-testid="veld-leverancier" aria-describedby="f-leverancier-help" />
        <p id="f-leverancier-help" data-testid="leverancier-help" class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">
          Vrije inventarisatie-notitie (interne/feitelijke benaming). Staat los van de contractuele
          leverancier — die leg je vast via het contract.
        </p>
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
