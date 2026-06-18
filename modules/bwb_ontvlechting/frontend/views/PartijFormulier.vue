<script setup>
/**
 * PartijFormulier — aanmaken (geen `id`) of bewerken (`id` via route-prop). ADR-024 slice 2a.
 *
 * Eén formulier voor alle aarden. Bij aanmaken kiest de gebruiker de **aard** (verplicht);
 * daarna ligt de aard vast (read-only bij bewerken — niet in de Update-payload). `naam`
 * verplicht; overige contactvelden vrij; `soort` optioneel (platform-catalogus). GEEN
 * formaatvalidatie op email/telefoon. 422-veldfouten worden op de juiste velden gezet.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { api } from '@/api'
import { PARTIJ_AARD, label } from '@modules/bwb_ontvlechting/frontend/labels'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const toast = useToast()

const bewerken = computed(() => !!props.id)
const bezig = ref(false)

const AARD_OPTIES = ['externe_partij', 'organisatie', 'organisatie_eenheid', 'persoon']
const aardLabel = (a) => label(PARTIJ_AARD, a)

const VELDEN = [
  'naam', 'straat_huisnummer', 'postcode', 'plaats',
  'contactpersoon', 'telefoon', 'mobiel', 'email', 'omschrijving',
]
const form = reactive(Object.fromEntries(VELDEN.map((v) => [v, ''])))
const aard = ref('')      // verplicht bij aanmaken; vast daarna
const soort = ref('')     // optioneel
const soortOpties = ref([])
const fouten = reactive({})

// ADR-024 slice 2a-bis — "hoort bij". Persoon/afdeling horen verplicht bij een organisatie;
// persoon optioneel ook bij een afdeling binnen die organisatie.
const organisatieId = ref('')
const afdelingId = ref('')
const orgKandidaten = ref([])       // organisatie-achtige partijen (organisatie + externe_partij)
const afdelingKandidaten = ref([])  // afdelingen binnen de gekozen organisatie
const heeftOrgOuder = computed(() => ['persoon', 'organisatie_eenheid'].includes(aard.value))
const magAfdeling = computed(() => aard.value === 'persoon')

async function _laadOrgKandidaten() {
  try {
    const [orgs, externe] = await Promise.all([
      api.partijen.lijst({ aard: 'organisatie', limit: 100 }),
      api.partijen.lijst({ aard: 'externe_partij', limit: 100 }),
    ])
    orgKandidaten.value = [...orgs.items, ...externe.items]
  } catch {
    orgKandidaten.value = []
  }
}

async function _laadAfdelingen() {
  if (!organisatieId.value) {
    afdelingKandidaten.value = []
    return
  }
  try {
    const r = await api.partijen.lijst({ aard: 'organisatie_eenheid', organisatie_id: organisatieId.value, limit: 100 })
    afdelingKandidaten.value = r.items
  } catch {
    afdelingKandidaten.value = []
  }
}

// Gebruiker wisselt de organisatie → reset de (nu mogelijk niet-passende) afdelingkeuze en
// herlaad de afdelingen. (Geen watch: zou de edit-initialisatie hieronder verstoren.)
async function onOrgChange() {
  afdelingId.value = ''
  await _laadAfdelingen()
}

async function init() {
  await _laadOrgKandidaten()
  try {
    soortOpties.value = await api.partijen.soorten()
  } catch {
    // soort niet kritisch; dropdown blijft leeg
  }
  if (!bewerken.value) return
  try {
    const p = await api.partijen.haal(props.id)
    for (const v of VELDEN) form[v] = p[v] || ''
    aard.value = p.aard || ''
    soort.value = p.soort || ''
    organisatieId.value = p.organisatie_id || ''
    await _laadAfdelingen()                 // ná het zetten van de organisatie (geen watch-reset)
    afdelingId.value = p.afdeling_id || ''
  } catch (e) {
    _toastFout(e)
  }
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.naam.trim()) fouten.naam = 'Naam is verplicht.'
  else if (form.naam.trim().length > 255) fouten.naam = 'Maximaal 255 tekens.'
  if (!bewerken.value && !aard.value) fouten.aard = 'Kies een aard.'
  // "hoort bij": organisatie verplicht voor persoon/afdeling.
  if (heeftOrgOuder.value && !organisatieId.value) fouten.organisatie_id = 'Kies een organisatie.'
  return Object.keys(fouten).length === 0
}

function _payload() {
  const uit = {}
  for (const v of VELDEN) {
    const w = form[v].trim()
    uit[v] = v === 'naam' ? w : w || null
  }
  uit.soort = soort.value || null
  // Lidmaatschap: organisatie alleen voor persoon/afdeling; afdeling alleen voor persoon.
  uit.organisatie_id = heeftOrgOuder.value ? organisatieId.value || null : null
  uit.afdeling_id = magAfdeling.value ? afdelingId.value || null : null
  // `aard` alleen bij aanmaken (vast daarna; Update kent geen aard → extra='forbid').
  if (!bewerken.value) uit.aard = aard.value
  return uit
}

function _serverveldfouten(e) {
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let t = false
    for (const d of e.detail) {
      const veld = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (veld && (veld in form || ['aard', 'soort', 'organisatie_id', 'afdeling_id'].includes(veld))) {
        fouten[veld] = d.msg || 'Ongeldige waarde.'
        t = true
      }
    }
    return t
  }
  return false
}

function _toastFout(e) {
  const per = { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  try {
    const data = _payload()
    const res = bewerken.value
      ? await api.partijen.werkBij(props.id, data)
      : await api.partijen.maak(data)
    toast.add({ severity: 'success', summary: bewerken.value ? 'Wijzigingen opgeslagen' : 'Partij aangemaakt', life: 3000 })
    router.push({ name: 'partij-detail', params: { id: res.id } })
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

function annuleer() {
  if (bewerken.value) router.push({ name: 'partij-detail', params: { id: props.id } })
  else router.push({ name: 'partij-lijst' })
}

onMounted(init)

const TEKSTVELDEN = [
  { veld: 'straat_huisnummer', label: 'Straat en huisnummer' },
  { veld: 'postcode', label: 'Postcode' },
  { veld: 'plaats', label: 'Plaats' },
  { veld: 'contactpersoon', label: 'Contactpersoon' },
  { veld: 'telefoon', label: 'Telefoon' },
  { veld: 'mobiel', label: 'Mobiel' },
  { veld: 'email', label: 'E-mail' },
]
</script>

<template>
  <section aria-labelledby="partij-form-titel">
    <h1
      id="partij-form-titel"
      class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)] mb-[var(--cd-space-lg)]"
    >
      {{ bewerken ? 'Partij bewerken' : 'Nieuwe partij' }}
    </h1>

    <form class="card flex flex-col gap-[var(--cd-space-md)] max-w-2xl" data-testid="partij-form" @submit.prevent="opslaan">
      <!-- Aard: keuze bij aanmaken, vast (read-only) bij bewerken -->
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="pf-aard" class="font-semibold">Aard *</label>
        <select
          v-if="!bewerken"
          id="pf-aard"
          v-model="aard"
          data-testid="veld-aard"
          :aria-invalid="!!fouten.aard"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        >
          <option value="">— kies —</option>
          <option v-for="a in AARD_OPTIES" :key="a" :value="a">{{ aardLabel(a) }}</option>
        </select>
        <span v-else data-testid="aard-readonly" class="text-[var(--cd-color-text-muted)]">{{ aardLabel(aard) }} (vast)</span>
        <span v-if="fouten.aard" role="alert" data-testid="fout-aard" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.aard }}</span>
      </div>

      <!-- "Hoort bij": organisatie verplicht voor persoon/afdeling; afdeling optioneel voor persoon -->
      <div v-if="heeftOrgOuder" class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="pf-organisatie" class="font-semibold">Organisatie *</label>
        <select
          id="pf-organisatie"
          v-model="organisatieId"
          data-testid="veld-organisatie"
          :aria-invalid="!!fouten.organisatie_id"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
          @change="onOrgChange"
        >
          <option value="">— kies —</option>
          <option v-for="o in orgKandidaten" :key="o.id" :value="o.id">{{ o.naam }} ({{ aardLabel(o.aard) }})</option>
        </select>
        <span v-if="fouten.organisatie_id" role="alert" data-testid="fout-organisatie_id" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.organisatie_id }}</span>
      </div>

      <div v-if="magAfdeling" class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="pf-afdeling" class="font-semibold">Afdeling (optioneel)</label>
        <select
          id="pf-afdeling"
          v-model="afdelingId"
          data-testid="veld-afdeling"
          :disabled="!organisatieId"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-50"
        >
          <option value="">— geen —</option>
          <option v-for="a in afdelingKandidaten" :key="a.id" :value="a.id">{{ a.naam }}</option>
        </select>
        <span v-if="fouten.afdeling_id" role="alert" data-testid="fout-afdeling_id" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.afdeling_id }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="pf-naam" class="font-semibold">Naam *</label>
        <InputText id="pf-naam" v-model="form.naam" data-testid="veld-naam" :aria-invalid="!!fouten.naam" aria-describedby="fout-naam" />
        <span v-if="fouten.naam" id="fout-naam" role="alert" data-testid="fout-naam" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.naam }}</span>
      </div>

      <!-- Soort: optioneel (platform-catalogus) -->
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="pf-soort" class="font-semibold">Soort</label>
        <select
          id="pf-soort"
          v-model="soort"
          data-testid="veld-soort"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        >
          <option value="">— geen —</option>
          <option v-for="o in soortOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
        <span v-if="fouten.soort" role="alert" data-testid="fout-soort" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.soort }}</span>
      </div>

      <div v-for="v in TEKSTVELDEN" :key="v.veld" class="flex flex-col gap-[var(--cd-space-xs)]">
        <label :for="`pf-${v.veld}`" class="font-semibold">{{ v.label }}</label>
        <InputText :id="`pf-${v.veld}`" v-model="form[v.veld]" :data-testid="`veld-${v.veld}`" :aria-invalid="!!fouten[v.veld]" :aria-describedby="`fout-${v.veld}`" />
        <span v-if="fouten[v.veld]" :id="`fout-${v.veld}`" role="alert" :data-testid="`fout-${v.veld}`" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten[v.veld] }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="pf-omschrijving" class="font-semibold">Omschrijving</label>
        <Textarea id="pf-omschrijving" v-model="form.omschrijving" rows="3" data-testid="veld-omschrijving" />
      </div>

      <div class="flex gap-[var(--cd-space-md)] mt-[var(--cd-space-sm)]">
        <Button type="submit" label="Opslaan" data-testid="opslaan-knop" :disabled="bezig" />
        <Button type="button" label="Annuleren" severity="secondary" data-testid="annuleer-knop" @click="annuleer" />
      </div>
    </form>
  </section>
</template>
