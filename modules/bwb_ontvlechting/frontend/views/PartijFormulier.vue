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
import { detailRoute } from '@/detailIngang'
import { useRouter, useRoute } from '@/composables/router'
import { api } from '@/api'
import { PARTIJ_AARD, label } from '@modules/bwb_ontvlechting/frontend/labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'
import ContactpersoonSelect from './ContactpersoonSelect.vue'
import AfdelingSelect from './AfdelingSelect.vue'
import { useAuthStore } from '@/store/auth'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const route = useRoute()
const toast = useToast()
const auth = useAuthStore()

const bewerken = computed(() => !!props.id)
const bezig = ref(false)

const AARD_OPTIES = ['externe_partij', 'organisatie', 'organisatie_eenheid', 'persoon']
const aardLabel = (a) => label(PARTIJ_AARD, a)

// ADR-038 — intern/extern. Kiesbaar bij een organisatie (default extern); vast "extern" bij een
// externe partij; niet getoond bij afdeling/persoon (die erven van hun organisatie).
const SCOPE_OPTIES = [
  { waarde: 'intern', label: 'Intern', subtekst: 'Onze eigen organisatie.' },
  { waarde: 'extern', label: 'Extern', subtekst: 'Partij buiten onze organisatie.' },
]
const scope = ref('extern')
const magScope = computed(() => aard.value === 'organisatie')       // kiesbaar
const scopeVast = computed(() => aard.value === 'externe_partij')   // vast "extern"

const VELDEN = [
  'naam', 'straat_huisnummer', 'postcode', 'plaats',
  'telefoon', 'mobiel', 'email', 'functietitel', 'omschrijving',
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

// ADR-039 — aanspreekpunt (persoon van déze partij). Alleen op organisatie/externe partij, én alleen
// in bewerk-modus: een persoon kan pas bij een partij horen nadat die partij bestaat (bij aanmaken
// bestaat de partij-id nog niet, dus zijn er geen kandidaten).
const contactpersoonId = ref('')
const cpInitieel = ref('')
const magAanmaakContactpersoon = computed(() => auth.hasRole('medewerker', 'beheerder'))
// LI032 — afdeling ter plekke aanmaken (zelfde recht als een lid toevoegen).
const magAanmaakAfdeling = computed(() => auth.hasRole('medewerker', 'beheerder'))
const isPartijMetAanspreekpunt = computed(() => ['organisatie', 'externe_partij'].includes(aard.value))
const magContactpersoon = computed(() => bewerken.value && isPartijMetAanspreekpunt.value)
function onContactpersoon(id) {
  contactpersoonId.value = id || ''
}

// Zoekfunctie voor de organisatie-picker (server-side). De afdeling-picker zoekt zelf (AfdelingSelect).
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })

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
    scope.value = p.scope || 'extern'  // ADR-038 — voorvullen bij bewerken (organisatie/externe partij)
    organisatieId.value = p.organisatie_id || ''
    afdelingId.value = p.afdeling_id || ''
    // ADR-039 — aanspreekpunt voorvullen (id + naam voor de ZoekSelect-weergave).
    contactpersoonId.value = p.contactpersoon_id || ''
    if (contactpersoonId.value) {
      try { cpInitieel.value = (await api.partijen.haal(contactpersoonId.value)).naam } catch { /* label niet kritisch */ }
    }
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
  // ADR-038 — intern/extern: de gekozen waarde bij een organisatie; vast "extern" bij een externe
  // partij; niets (null) bij afdeling/persoon (afgeleid; de backend weigert er een waarde op).
  uit.scope = magScope.value ? scope.value : scopeVast.value ? 'extern' : null
  // Lidmaatschap: organisatie alleen voor persoon/afdeling; afdeling alleen voor persoon.
  uit.organisatie_id = heeftOrgOuder.value ? organisatieId.value || null : null
  uit.afdeling_id = magAfdeling.value ? afdelingId.value || null : null
  // ADR-039 — aanspreekpunt alleen bij bewerken van een organisatie/externe partij (edit-only).
  if (magContactpersoon.value) uit.contactpersoon_id = contactpersoonId.value || null
  // `aard` alleen bij aanmaken (vast daarna; Update kent geen aard → extra='forbid').
  if (!bewerken.value) uit.aard = aard.value
  return uit
}

function _serverveldfouten(e) {
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let t = false
    for (const d of e.detail) {
      const veld = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (veld && (veld in form || ['aard', 'soort', 'scope', 'organisatie_id', 'afdeling_id', 'contactpersoon_id'].includes(veld))) {
        fouten[veld] = d.msg || 'Ongeldige waarde.'
        t = true
      }
    }
    return t
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
    router.push(detailRoute('partij', doelId))
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

function annuleer() {
  if (bewerken.value) router.push(detailRoute('partij', props.id))
  else router.push({ name: 'partij-lijst' })
}

onMounted(init)

const TEKSTVELDEN = [
  { veld: 'straat_huisnummer', label: 'Straat en huisnummer' },
  { veld: 'postcode', label: 'Postcode' },
  { veld: 'plaats', label: 'Plaats' },
  { veld: 'telefoon', label: 'Telefoon' },
  { veld: 'mobiel', label: 'Mobiel' },
  { veld: 'email', label: 'E-mail' },
]
</script>

<template>
  <section aria-labelledby="partij-form-titel">
    <h1
      id="partij-form-titel"
      class="text-[var(--lk-color-primary)] mb-[var(--lk-space-lg)]"
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
          class="lk-veld"
        >
          <option value="">— kies —</option>
          <option v-for="a in AARD_OPTIES" :key="a" :value="a">{{ aardLabel(a) }}</option>
        </select>
        <span v-else data-testid="aard-readonly" class="text-[var(--lk-color-text-muted)]">{{ aardLabel(aard) }} (vast)</span>
        <span v-if="fouten.aard" role="alert" data-testid="fout-aard" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.aard }}</span>
      </div>

      <!-- ADR-038 — intern/extern: kiesbaar bij een organisatie (default extern), vast bij een externe
           partij, niet getoond bij afdeling/persoon (afgeleid van de organisatie). -->
      <div v-if="magScope" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="veld-scope-wrap">
        <span class="font-semibold">Intern of extern</span>
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Markeer je eigen organisatie als intern. Deelnemende organisaties, partners en burger-doelgroepen zijn extern.
        </p>
        <div class="flex gap-[var(--lk-space-md)]">
          <label
            v-for="opt in SCOPE_OPTIES"
            :key="opt.waarde"
            :data-testid="`scope-optie-${opt.waarde}`"
            class="flex-1 cursor-pointer rounded-[var(--lk-radius-input)] border p-[var(--lk-space-sm)] flex flex-col gap-[2px]"
            :class="scope === opt.waarde ? 'border-[var(--lk-color-primary)] bg-[var(--lk-color-accent)]' : 'border-[var(--lk-color-border)]'"
          >
            <span class="flex items-center gap-[var(--lk-space-xs)]">
              <input type="radio" name="scope" :value="opt.waarde" v-model="scope" :data-testid="`scope-radio-${opt.waarde}`" />
              <span class="font-semibold">{{ opt.label }}</span>
            </span>
            <span class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">{{ opt.subtekst }}</span>
          </label>
        </div>
      </div>
      <div v-else-if="scopeVast" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="veld-scope-vast">
        <span class="font-semibold">Intern of extern</span>
        <span class="text-[var(--lk-color-text-muted)]">Extern — vast (een externe partij is altijd extern).</span>
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
        <!-- LI032 — afdeling die nog niet bestaat kan hier ter plekke aangemaakt worden (binnen de
             gekozen organisatie), zodat het veld niet doodloopt. -->
        <AfdelingSelect
          id="pf-afdeling"
          testid="veld-afdeling"
          :key="organisatieId"
          v-model="afdelingId"
          :partij-id="organisatieId"
          :initieel-weergave="afdInitieel"
          :mag-aanmaken="magAanmaakAfdeling"
          :org-naam="orgInitieel"
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
          class="lk-veld"
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

      <!-- ADR-039 — aanspreekpunt: een persoon die bij deze partij hoort. Alleen bij organisatie/
           externe partij; edit-only (bij aanmaken bestaat de partij nog niet, dus geen kandidaten). -->
      <div v-if="magContactpersoon" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="veld-contactpersoon-wrap">
        <label class="font-semibold">Aanspreekpunt</label>
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Kies een persoon die bij deze partij hoort, of maak er ter plekke een aan.</p>
        <ContactpersoonSelect
          :partij-id="props.id"
          :model-value="contactpersoonId"
          :initieel-weergave="cpInitieel"
          :mag-aanmaken="magAanmaakContactpersoon"
          @update:model-value="onContactpersoon"
        />
        <span v-if="fouten.contactpersoon_id" role="alert" data-testid="fout-contactpersoon_id" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.contactpersoon_id }}</span>
      </div>
      <p v-else-if="!bewerken && isPartijMetAanspreekpunt" data-testid="contactpersoon-hint" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
        Een aanspreekpunt kies je nadat de partij is aangemaakt (het aanspreekpunt is een persoon die bij deze partij hoort).
      </p>

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
