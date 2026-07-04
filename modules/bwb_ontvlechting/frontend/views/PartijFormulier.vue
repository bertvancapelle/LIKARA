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
import { useRouter, useRoute } from '@/composables/router'
import { api } from '@/api'
import { PARTIJ_AARD, label } from '@modules/bwb_ontvlechting/frontend/labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const route = useRoute()
const toast = useToast()

const bewerken = computed(() => !!props.id)
const bezig = ref(false)

const AARD_OPTIES = ['externe_partij', 'organisatie', 'organisatie_eenheid', 'persoon']
const aardLabel = (a) => label(PARTIJ_AARD, a)

const VELDEN = [
  'naam', 'straat_huisnummer', 'postcode', 'plaats',
  'contactpersoon', 'telefoon', 'mobiel', 'email', 'functietitel', 'omschrijving',
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
// Weergavelabels voor de reeds-gekozen waarden (bewerken / vanuit-query) — ZoekSelect heeft het
// item zelf nog niet geladen. CD049: server-side zoekend, geen voor-geladen kandidatenlijst.
const orgInitieel = ref('')
const afdInitieel = ref('')
const heeftOrgOuder = computed(() => ['persoon', 'organisatie_eenheid'].includes(aard.value))
const magAfdeling = computed(() => aard.value === 'persoon')

// Zoekfuncties (server-side; ZoekSelect roept ze met { zoek, limit, ...extraFilters } aan).
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })
const zoekAfdelingen = (params) =>
  api.partijen.lijst({ ...params, aard: 'organisatie_eenheid', organisatie_id: organisatieId.value })

// Gebruiker kiest een (andere) organisatie → reset de nu mogelijk niet-passende afdelingkeuze.
function onOrgKies(val) {
  organisatieId.value = val || ''
  afdelingId.value = ''
  afdInitieel.value = ''
}

// Labels voor reeds-gezette ouder-ids ophalen (bewerken/vanuit-query) → ZoekSelect toont ze.
async function _zetInitieelLabels() {
  if (organisatieId.value) {
    try { orgInitieel.value = (await api.partijen.haal(organisatieId.value)).naam } catch { /* label niet kritisch */ }
  }
  if (afdelingId.value) {
    try { afdInitieel.value = (await api.partijen.haal(afdelingId.value)).naam } catch { /* idem */ }
  }
}

async function init() {
  try {
    soortOpties.value = await api.partijen.soorten()
  } catch {
    // soort niet kritisch; dropdown blijft leeg
  }
  if (!bewerken.value) {
    // Aanmaken vanaf een organisatie/afdeling (UX-A2/A3): aard + ouder-context voorgevuld
    // uit de route-query (bv. ?aard=persoon&organisatie_id=…&afdeling_id=…). De velden blijven
    // zichtbaar/wijzigbaar — geen verborgen dwang; de gebruiker hoeft niets terug te zoeken.
    const q = route.query || {}
    if (q.aard && AARD_OPTIES.includes(String(q.aard))) aard.value = String(q.aard)
    if (q.organisatie_id) {
      organisatieId.value = String(q.organisatie_id)
      if (q.afdeling_id) afdelingId.value = String(q.afdeling_id)
      await _zetInitieelLabels()           // ná het zetten van de ids (ZoekSelect-weergave)
    }
    return
  }
  try {
    const p = await api.partijen.haal(props.id)
    for (const v of VELDEN) form[v] = p[v] || ''
    aard.value = p.aard || ''
    soort.value = p.soort || ''
    organisatieId.value = p.organisatie_id || ''
    afdelingId.value = p.afdeling_id || ''
    await _zetInitieelLabels()             // ná het zetten van de ids (ZoekSelect-weergave)
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
    // UX-A2/A3 — kwam de gebruiker via "+ Afdeling/Persoon" met ouder-context binnen, keer dan
    // terug naar de ouder (afdeling vóór organisatie) zodat de nieuwe regel meteen in de leden-
    // lijst staat en het volgende lid direct toegevoegd kan worden. Anders: naar de nieuwe partij.
    let doelId = res.id
    if (!bewerken.value) {
      const q = route.query || {}
      doelId = q.afdeling_id ? String(q.afdeling_id) : q.organisatie_id ? String(q.organisatie_id) : res.id
    }
    router.push({ name: 'partij-detail', params: { id: doelId } })
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
      class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)] mb-[var(--lk-space-lg)]"
    >
      {{ bewerken ? 'Partij bewerken' : 'Nieuwe partij' }}
    </h1>

    <form class="card flex flex-col gap-[var(--lk-space-md)] max-w-2xl" data-testid="partij-form" @submit.prevent="opslaan">
      <!-- Aard: keuze bij aanmaken, vast (read-only) bij bewerken -->
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="pf-aard" class="font-semibold">Aard *</label>
          <VeldUitleg veld="aard" opties="aard" />
        </div>
        <select
          v-if="!bewerken"
          id="pf-aard"
          v-model="aard"
          data-testid="veld-aard"
          :aria-invalid="!!fouten.aard"
          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
        >
          <option value="">— kies —</option>
          <option v-for="a in AARD_OPTIES" :key="a" :value="a">{{ aardLabel(a) }}</option>
        </select>
        <span v-else data-testid="aard-readonly" class="text-[var(--lk-color-text-muted)]">{{ aardLabel(aard) }} (vast)</span>
        <span v-if="fouten.aard" role="alert" data-testid="fout-aard" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.aard }}</span>
      </div>

      <!-- "Hoort bij": organisatie verplicht voor persoon/afdeling; afdeling optioneel voor persoon.
           CD049/ZoekSelect-standaard: server-side zoekend (onbegrensd), geen voor-geladen lijst. -->
      <div v-if="heeftOrgOuder" class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="pf-organisatie" class="font-semibold">Organisatie *</label>
          <VeldUitleg veld="partij_organisatie" />
        </div>
        <ZoekSelect
          id="pf-organisatie"
          testid="veld-organisatie"
          :model-value="organisatieId"
          :zoek-functie="zoekOrganisaties"
          :initieel-weergave="orgInitieel"
          :invalid="!!fouten.organisatie_id"
          aria-describedby="fout-organisatie_id"
          placeholder="Zoek een organisatie…"
          @update:model-value="onOrgKies"
        />
        <span v-if="fouten.organisatie_id" id="fout-organisatie_id" role="alert" data-testid="fout-organisatie_id" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.organisatie_id }}</span>
      </div>

      <div v-if="magAfdeling && organisatieId" class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="pf-afdeling" class="font-semibold">Afdeling (optioneel)</label>
          <VeldUitleg veld="partij_afdeling" />
        </div>
        <ZoekSelect
          id="pf-afdeling"
          testid="veld-afdeling"
          :key="organisatieId"
          v-model="afdelingId"
          :zoek-functie="zoekAfdelingen"
          :initieel-weergave="afdInitieel"
          :invalid="!!fouten.afdeling_id"
          aria-describedby="fout-afdeling_id"
          placeholder="Zoek een afdeling…"
        />
        <span v-if="fouten.afdeling_id" id="fout-afdeling_id" role="alert" data-testid="fout-afdeling_id" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.afdeling_id }}</span>
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="pf-naam" class="font-semibold">Naam *</label>
        <InputText id="pf-naam" v-model="form.naam" data-testid="veld-naam" :aria-invalid="!!fouten.naam" aria-describedby="fout-naam" />
        <span v-if="fouten.naam" id="fout-naam" role="alert" data-testid="fout-naam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.naam }}</span>
      </div>

      <!-- Soort: optioneel (platform-catalogus) -->
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="pf-soort" class="font-semibold">Soort</label>
          <VeldUitleg veld="soort" opties="partijsoort" />
        </div>
        <select
          id="pf-soort"
          v-model="soort"
          data-testid="veld-soort"
          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
        >
          <option value="">— geen —</option>
          <option v-for="o in soortOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
        <span v-if="fouten.soort" role="alert" data-testid="fout-soort" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.soort }}</span>
      </div>

      <div v-for="v in TEKSTVELDEN" :key="v.veld" class="flex flex-col gap-[var(--lk-space-xs)]">
        <label :for="`pf-${v.veld}`" class="font-semibold">{{ v.label }}</label>
        <InputText :id="`pf-${v.veld}`" v-model="form[v.veld]" :data-testid="`veld-${v.veld}`" :aria-invalid="!!fouten[v.veld]" :aria-describedby="`fout-${v.veld}`" />
        <span v-if="fouten[v.veld]" :id="`fout-${v.veld}`" role="alert" :data-testid="`fout-${v.veld}`" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten[v.veld] }}</span>
      </div>

      <!-- ADR-024 (Optie 1) — functietitel uitsluitend voor een persoon. -->
      <div v-if="aard === 'persoon'" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="veld-functietitel-wrap">
        <label for="pf-functietitel" class="font-semibold">Functietitel (optioneel)</label>
        <InputText id="pf-functietitel" v-model="form.functietitel" data-testid="veld-functietitel" :aria-invalid="!!fouten.functietitel" aria-describedby="fout-functietitel" />
        <span v-if="fouten.functietitel" id="fout-functietitel" role="alert" data-testid="fout-functietitel" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.functietitel }}</span>
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="pf-omschrijving" class="font-semibold">Omschrijving</label>
        <Textarea id="pf-omschrijving" v-model="form.omschrijving" rows="3" data-testid="veld-omschrijving" />
      </div>

      <div class="flex gap-[var(--lk-space-md)] mt-[var(--lk-space-sm)]">
        <Button type="submit" label="Opslaan" data-testid="opslaan-knop" :disabled="bezig" />
        <Button type="button" label="Annuleren" severity="secondary" data-testid="annuleer-knop" @click="annuleer" />
      </div>
    </form>
  </section>
</template>
