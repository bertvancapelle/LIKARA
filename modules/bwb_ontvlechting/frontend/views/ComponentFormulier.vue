<script setup>
/**
 * ComponentFormulier — aanmaken/bewerken van ELK componenttype (LI059 Slice 4).
 *
 * Eén formulier voor alle typen. De drie transitie-attributen (migratiepad/complexiteit/
 * prioriteit) zijn component-breed (LI057) en dus voor élk type instelbaar; opties uit
 * labels.js (defaults onbekend/midden/midden). Componenttype-opties komen uit
 * /componenten/opties (catalogus); hostingmodel/migratiepad/complexiteit/prioriteit uit de
 * enum-maps. Naam + type zijn verplicht; overige velden optioneel. Opslaan opent altijd het
 * generieke ComponentDetail (ook voor type `applicatie` — convergente aanmaak). Het TYPE
 * wijzigen van een component mét gegevens is server-side geblokkeerd (SUBTYPE_HEEFT_DATA):
 * de select is dan vergrendeld met uitleg (verwijderen om het type te wijzigen).
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { api } from '@/api'
import { HOSTINGMODEL, MIGRATIEPAD, NIVEAU, REGISTER_FOUT, label } from '../labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

// Eigenaar-organisatie: server-side zoeken, beperkt tot partijen met aard=organisatie (UX-B6-b).
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const toast = useToast()

const bewerken = computed(() => !!props.id)
const typeOpties = ref([]) // [{ optie_sleutel, label }] — incl. 'applicatie' (convergent)
// ADR-028 — rol-opties (kan groeien) + BIV-niveaus (ordinaal: laag → hoog), uit /componenten/opties.
const rolOpties = ref([])
const bivNiveaus = ref([])
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
  beschrijving: '',
  // LI057/LI059 — component-brede transitie-attributen (élk type); defaults conform ComponentCreate.
  migratiepad: 'onbekend',
  complexiteit: 'midden',
  prioriteit: 'midden',
  // ADR-028 — rol staat standaard op Intern (server-default); BIV leeg = niet geclassificeerd.
  componentrol: 'interne_applicatie',
  biv_beschikbaarheid: '',
  biv_integriteit: '',
  biv_vertrouwelijkheid: '',
})
const fouten = reactive({})

// ADR-028 — de drie BIV-aspecten (single source voor labels + template-loop).
const BIV_VELDEN = [
  { veld: 'biv_beschikbaarheid', label: 'Beschikbaarheid' },
  { veld: 'biv_integriteit', label: 'Integriteit' },
  { veld: 'biv_vertrouwelijkheid', label: 'Vertrouwelijkheid' },
]

const hosting = (c) => label(HOSTINGMODEL, c)

// LI059 Slice 4 — de drie transitie-selects (opties uit de enum-maps; single source labels.js).
const TRANSITIE_VELDEN = [
  { veld: 'migratiepad', label: 'Migratiepad', opties: MIGRATIEPAD },
  { veld: 'complexiteit', label: 'Complexiteit', opties: NIVEAU },
  { veld: 'prioriteit', label: 'Prioriteit', opties: NIVEAU },
]
const transitieLabel = (map, code) => label(map, code)

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
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
    // ADR-028 — rol-opties + BIV-niveaus (ordinaal) voor de dropdowns.
    rolOpties.value = opties.componentrol_opties || []
    bivNiveaus.value = opties.biv_niveaus || []
    if (bewerken.value) {
      // LI059 Slice 4 — élk type (incl. applicatie) wordt hier bewerkt; geen subtype-redirect meer.
      const c = await api.componenten.haal(props.id)
      typeVergrendeld.value = c.type_wijzigbaar === false
      Object.assign(form, {
        naam: c.naam,
        componenttype: c.componenttype,
        hostingmodel: c.hostingmodel,
        eigenaar_organisatie_id: c.eigenaar_organisatie_id ?? null,
        eigenaar_organisatie_naam: c.eigenaar_organisatie_naam || '',
        beschrijving: c.beschrijving || '',
        migratiepad: c.migratiepad ?? 'onbekend',
        complexiteit: c.complexiteit ?? 'midden',
        prioriteit: c.prioriteit ?? 'midden',
        // ADR-028 — huidige rol + BIV (leeg = niet geclassificeerd).
        componentrol: c.componentrol ?? 'interne_applicatie',
        biv_beschikbaarheid: c.biv_beschikbaarheid ?? '',
        biv_integriteit: c.biv_integriteit ?? '',
        biv_vertrouwelijkheid: c.biv_vertrouwelijkheid ?? '',
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
    beschrijving: form.beschrijving.trim() || null,
    migratiepad: form.migratiepad,
    complexiteit: form.complexiteit,
    prioriteit: form.prioriteit,
    // ADR-028 — rol altijd meegeven; een lege BIV-keuze → null (registratiegat).
    componentrol: form.componentrol,
    biv_beschikbaarheid: form.biv_beschikbaarheid || null,
    biv_integriteit: form.biv_integriteit || null,
    biv_vertrouwelijkheid: form.biv_vertrouwelijkheid || null,
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
  // ADR-028 — code-gebaseerde 422 (DB-lookup-validatie) op het juiste veld tonen.
  if (e?.status === 422 && e?.code === 'ONGELDIGE_ROL') {
    fouten.componentrol = e?.message || 'Kies een geldige rol.'
    return true
  }
  if (e?.status === 422 && e?.code === 'ONGELDIGE_BIV') {
    fouten.biv = e?.message || 'Kies een geldige BIV-waarde.'
    return true
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
    // LI059 Slice 4 — één beleving: élk type (incl. applicatie) opent op het generieke ComponentDetail.
    toast.add({
      severity: 'success',
      summary: bewerken.value ? 'Wijzigingen opgeslagen' : 'Component aangemaakt',
      life: 3000,
    })
    router.push({ name: 'component-detail', params: { id: resultaat.id } })
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
      class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)] mb-[var(--lk-space-lg)]"
    >
      {{ bewerken ? 'Component bewerken' : 'Nieuw component' }}
    </h1>

    <form class="card flex flex-col gap-[var(--lk-space-md)] max-w-2xl" data-testid="component-form" @submit.prevent="opslaan">
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="f-naam" class="font-semibold">Naam *</label>
        <InputText id="f-naam" v-model="form.naam" data-testid="veld-naam" :aria-invalid="!!fouten.naam" aria-describedby="fout-naam" />
        <span v-if="fouten.naam" id="fout-naam" role="alert" data-testid="fout-naam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.naam }}</span>
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="f-componenttype" class="font-semibold">Type *</label>
          <VeldUitleg veld="componenttype" opties="componenttype" />
        </div>
        <select
          id="f-componenttype"
          v-model="form.componenttype"
          data-testid="veld-componenttype"
          :aria-invalid="!!fouten.componenttype"
          :disabled="typeVergrendeld"
          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white disabled:opacity-60"
        >
          <option value="" disabled>— maak een keuze —</option>
          <option v-for="o in typeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
        <span
          v-if="typeVergrendeld"
          data-testid="type-vergrendeld-hint"
          class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]"
        >
          Type vergrendeld: dit component bevat al gegevens. Verwijder het component om het type te wijzigen.
        </span>
        <span v-if="fouten.componenttype" role="alert" data-testid="fout-componenttype" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.componenttype }}</span>
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="f-hostingmodel" class="font-semibold">Hostingmodel</label>
          <VeldUitleg veld="hostingmodel" />
        </div>
        <select
          id="f-hostingmodel"
          v-model="form.hostingmodel"
          data-testid="veld-hostingmodel"
          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
        >
          <option v-for="h in HOSTING_OPTIES" :key="h" :value="h">{{ hosting(h) }}</option>
        </select>
      </div>

      <!-- ADR-028 — componentrol (default Intern) + optionele BIV-classificatie. -->
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="f-componentrol" class="font-semibold">Rol</label>
          <VeldUitleg veld="rol" opties="componentrol" />
        </div>
        <select
          id="f-componentrol"
          v-model="form.componentrol"
          data-testid="veld-componentrol"
          :aria-invalid="!!fouten.componentrol"
          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
        >
          <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
        <span v-if="fouten.componentrol" role="alert" data-testid="fout-componentrol" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.componentrol }}</span>
      </div>

      <fieldset class="flex flex-col gap-[var(--lk-space-xs)] border border-[var(--lk-color-border)] rounded-[var(--lk-radius-input)] p-[var(--lk-space-sm)]" data-testid="biv-blok">
        <legend class="font-semibold px-[var(--lk-space-xs)]">BIV-classificatie</legend>
        <div
          v-for="b in BIV_VELDEN"
          :key="b.veld"
          class="flex flex-col gap-[var(--lk-space-xs)]"
        >
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <label :for="`f-${b.veld}`">{{ b.label }}</label>
            <VeldUitleg :veld="b.veld" />
          </div>
          <select
            :id="`f-${b.veld}`"
            v-model="form[b.veld]"
            :data-testid="`veld-${b.veld}`"
            class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
          >
            <option value="">— Niet geclassificeerd —</option>
            <option v-for="n in bivNiveaus" :key="n.optie_sleutel" :value="n.optie_sleutel">{{ n.label }}</option>
          </select>
        </div>
        <span v-if="fouten.biv" role="alert" data-testid="fout-biv" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.biv }}</span>
      </fieldset>

      <!-- LI059 Slice 4 — transitie-attributen (component-breed, élk type). -->
      <div
        v-for="t in TRANSITIE_VELDEN"
        :key="t.veld"
        class="flex flex-col gap-[var(--lk-space-xs)]"
      >
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label :for="`f-${t.veld}`" class="font-semibold">{{ t.label }}</label>
          <VeldUitleg :veld="t.veld" />
        </div>
        <select
          :id="`f-${t.veld}`"
          v-model="form[t.veld]"
          :data-testid="`veld-${t.veld}`"
          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
        >
          <option v-for="code in Object.keys(t.opties)" :key="code" :value="code">
            {{ transitieLabel(t.opties, code) }}
          </option>
        </select>
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <label for="f-eigenaar-org" class="font-semibold">Eigenaar-organisatie</label>
          <VeldUitleg veld="eigenaar_organisatie_id" />
        </div>
        <ZoekSelect
          id="f-eigenaar-org"
          testid="veld-eigenaar-organisatie"
          v-model="form.eigenaar_organisatie_id"
          :initieel-weergave="form.eigenaar_organisatie_naam"
          :zoek-functie="zoekOrganisaties"
          placeholder="Zoek een organisatie (optioneel)…"
        />
      </div>

      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="f-beschrijving" class="font-semibold">Beschrijving</label>
        <Textarea id="f-beschrijving" v-model="form.beschrijving" rows="4" data-testid="veld-beschrijving" />
      </div>

      <div class="flex gap-[var(--lk-space-md)] mt-[var(--lk-space-sm)]">
        <Button type="submit" label="Opslaan" data-testid="opslaan-knop" :disabled="bezig" />
        <Button type="button" label="Annuleren" severity="secondary" data-testid="annuleer-knop" @click="annuleer" />
      </div>
    </form>
  </section>
</template>
