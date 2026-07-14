<script setup>
/**
 * ComponentFormulier — aanmaken/bewerken van ELK componenttype als OVERLAY (ADR-042 4b).
 *
 * Overlay-dialoog i.p.v. de losse pagina: de lijst/het detail blijft eronder zichtbaar.
 * Aanmaken en bewerken zijn identiek (bewerken voorgevuld, incl. `initieel-weergave` op de
 * eigenaar-picker). Twee kolommen (smal scherm → stapelen): links *Basis* + *Inzet en
 * eigenaarschap* (eigenaar + procesregels); rechts *Classificatie* (rol + BIV naast
 * elkaar) + *Plaatsing en migratie* (ADR-046: rij 1 = Levensfase naast Bedoeling, dan
 * hosting/complexiteit/prioriteit). Vaste voetbalk (Opslaan primary + Annuleren)
 * in het #footer-slot — scroll-gedrag en scroll-schaduw komen uit de Dialog-primitive
 * (preset-content is hét scroll-gebied); deze view bouwt géén eigen scroll-wrapper.
 *
 * Procesregels: bij AANMAKEN verzamelend (regels samenstellen met "+", kruisjes; ná het
 * component in één keer opgeslagen — faalt een regel, dan stáát het component en toont
 * een danger-banner de mislukte regels met "Opnieuw proberen"/"Sluiten"). Bij BEWERKEN
 * toont de sectie de bestaande regels direct-opslaand (ComponentProcessenSectie — zelfde
 * gedrag als het Overzicht, geen tweede semantiek).
 *
 * Annuleren met gewijzigde velden vraagt bevestiging ("wijzigingen gaan verloren?").
 * Type-vergrendeling (SUBTYPE_HEEFT_DATA) en de veld-/servervalidaties zijn ongewijzigd.
 */
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, InputText, Textarea, useToast } from '@/primevue'
import { api } from '@/api'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import MeldingBanner from '@/components/MeldingBanner.vue'
import { HOSTINGMODEL, LEVENSFASE, MIGRATIEPAD, NIVEAU, REGISTER_FOUT, label } from '../labels'
import { maakProcesZoeker } from '../procesZoek'
import ComponentProcessenSectie from './ComponentProcessenSectie.vue'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })
const { zoekFunctie: zoekProcessen, weergave: procesWeergave } = maakProcesZoeker(api)

const props = defineProps({
  visible: { type: Boolean, required: true },
  id: { type: String, default: null }, // null = nieuw component
})
const emit = defineEmits(['update:visible', 'opgeslagen'])

const toast = useToast()
const bewerken = computed(() => !!props.id)

const typeOpties = ref([])
const rolOpties = ref([])
const bivNiveaus = ref([])
const functies = ref([]) // applicatiefunctie-opties (verzamel-procesregels bij aanmaken)
const HOSTING_OPTIES = Object.keys(HOSTINGMODEL)
const laden = ref(false)
const bezig = ref(false)
const typeVergrendeld = ref(false)

const form = reactive({
  naam: '',
  componenttype: '',
  hostingmodel: 'onbekend',
  eigenaar_organisatie_id: null,
  eigenaar_organisatie_naam: '',
  beschrijving: '',
  migratiepad: '', // LI040 — '' = "nog niet vastgelegd" (payload null); geen verzonnen 'onbekend'
  levensfase: '', // ADR-046 — '' = "nog niet vastgelegd" (payload null); bewust GEEN default-fase
  complexiteit: '', // LI040 — een oordeel wordt gegeven, niet uitgedeeld ('' = payload null)
  prioriteit: '',
  componentrol: 'interne_applicatie',
  biv_beschikbaarheid: '',
  biv_integriteit: '',
  biv_vertrouwelijkheid: '',
})
const fouten = reactive({})

const BIV_VELDEN = [
  { veld: 'biv_beschikbaarheid', label: 'Beschikbaarheid' },
  { veld: 'biv_integriteit', label: 'Integriteit' },
  { veld: 'biv_vertrouwelijkheid', label: 'Vertrouwelijkheid' },
]
// ADR-046 — Levensfase en Bedoeling zijn twee aparte vragen ("draait het?" / "waar gaat
// het heen?") en staan NAAST ELKAAR op de eerste rij van het 2-koloms grid. Levensfase
// heeft een expliciete leeg-optie ("nog niet vastgelegd") en géén default-fase.
const TRANSITIE_VELDEN = [
  { veld: 'levensfase', label: 'Levensfase', opties: LEVENSFASE, leegLabel: '— nog niet vastgelegd —' },
  // LI040 — de bedoeling mag óók leeg: geen verzonnen 'Onbekend' meer (één leegte-taal).
  { veld: 'migratiepad', label: 'Bedoeling', opties: MIGRATIEPAD, leegLabel: '— nog niet vastgelegd —' },
  { veld: 'hostingmodel', label: 'Hostingmodel', opties: HOSTINGMODEL },
  // LI040 — oordelen mogen leeg blijven: geen gratis 'Midden' meer (één leegte-taal).
  { veld: 'complexiteit', label: 'Complexiteit', opties: NIVEAU, leegLabel: '— nog niet vastgelegd —' },
  { veld: 'prioriteit', label: 'Prioriteit', opties: NIVEAU, leegLabel: '— nog niet vastgelegd —' },
]
const PLAATSING_VELDEN = computed(() => TRANSITIE_VELDEN.map((t) => ({ ...t, uitleg: t.veld })))
const hosting = (c) => label(HOSTINGMODEL, c)
const optieLabel = (map, code) => label(map, code)

function _toastFout(e) {
  if (e?.status === 401) return
  const detail =
    e?.code && REGISTER_FOUT[e.code]
      ? e?.message || REGISTER_FOUT[e.code]
      : { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

// ── Verzamel-procesregels (alleen bij AANMAKEN) ──────────────────────────────
const procesRegels = ref([]) // [{ proces_id, proces_weergave, applicatiefunctie, functie_label, toelichting }]
const regelProcesId = ref(null)
const regelProces = ref(null) // het gekozen item (voor de weergave in het lijstje)
const regelFunctie = ref('')
const regelToelichting = ref('')
const regelFout = ref(null)
const regelPickerKey = ref(0)
const regelOpslaanFout = ref(null) // danger-banner: mislukte regels ná component-aanmaak
const aangemaaktId = ref(null) // component staat al; retry slaat alleen nog regels op

function voegRegelToe() {
  regelFout.value = null
  if (!regelProcesId.value || !regelFunctie.value) {
    regelFout.value = 'Kies een proces én een applicatiefunctie.'
    return
  }
  const dubbel = procesRegels.value.some(
    (r) => r.proces_id === regelProcesId.value && r.applicatiefunctie === regelFunctie.value,
  )
  if (dubbel) {
    regelFout.value = 'Deze combinatie staat al in het lijstje.'
    return
  }
  procesRegels.value = [...procesRegels.value, {
    proces_id: regelProcesId.value,
    proces_weergave: procesWeergave(regelProces.value) || 'proces',
    applicatiefunctie: regelFunctie.value,
    functie_label: functies.value.find((f) => f.optie_sleutel === regelFunctie.value)?.label || regelFunctie.value,
    toelichting: regelToelichting.value.trim() || null,
  }]
  regelProcesId.value = null
  regelProces.value = null
  regelFunctie.value = ''
  regelToelichting.value = ''
  regelPickerKey.value += 1
}
function verwijderRegel(i) {
  procesRegels.value = procesRegels.value.filter((_, idx) => idx !== i)
}

// ── Init + dirty-tracking (annuleren-bevestiging) ────────────────────────────
let _schoneStand = ''
const _snapshot = () => JSON.stringify(form) + `|regels:${procesRegels.value.length}`
const isGewijzigd = () => _snapshot() !== _schoneStand

async function init() {
  laden.value = true
  Object.keys(fouten).forEach((k) => delete fouten[k])
  regelOpslaanFout.value = null
  aangemaaktId.value = null
  procesRegels.value = []
  regelFout.value = null
  typeVergrendeld.value = false
  Object.assign(form, {
    naam: '', componenttype: '', hostingmodel: 'onbekend',
    eigenaar_organisatie_id: null, eigenaar_organisatie_naam: '', beschrijving: '',
    migratiepad: '', levensfase: '', complexiteit: '', prioriteit: '',
    componentrol: 'interne_applicatie',
    biv_beschikbaarheid: '', biv_integriteit: '', biv_vertrouwelijkheid: '',
  })
  try {
    const opties = await api.componenten.opties()
    typeOpties.value = opties.componenttype || []
    rolOpties.value = opties.componentrol_opties || []
    bivNiveaus.value = opties.biv_niveaus || []
    if (!bewerken.value) {
      try {
        functies.value = await api.procesvervullingen.functies()
      } catch { functies.value = [] }
    }
    if (bewerken.value) {
      const c = await api.componenten.haal(props.id)
      typeVergrendeld.value = c.type_wijzigbaar === false
      Object.assign(form, {
        naam: c.naam,
        componenttype: c.componenttype,
        hostingmodel: c.hostingmodel,
        eigenaar_organisatie_id: c.eigenaar_organisatie_id ?? null,
        eigenaar_organisatie_naam: c.eigenaar_organisatie_naam || '',
        beschrijving: c.beschrijving || '',
        migratiepad: c.migratiepad ?? '',
        levensfase: c.levensfase ?? '',
        complexiteit: c.complexiteit ?? '',
        prioriteit: c.prioriteit ?? '',
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
    _schoneStand = _snapshot()
  }
}
watch(() => props.visible, (open) => { if (open) init() }, { immediate: true })

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
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
    // LI040/ADR-046 — '' = "nog niet vastgelegd" → expliciet null (wist ook een eerdere waarde).
    migratiepad: form.migratiepad || null,
    levensfase: form.levensfase || null,
    complexiteit: form.complexiteit || null,
    prioriteit: form.prioriteit || null,
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

async function _slaRegelsOp(componentId) {
  const mislukt = []
  for (const regel of procesRegels.value) {
    try {
      await api.procesvervullingen.maak({
        component_id: componentId,
        proces_id: regel.proces_id,
        applicatiefunctie: regel.applicatiefunctie,
        toelichting: regel.toelichting,
      })
    } catch (e) {
      if (e?.status === 401) throw e
      mislukt.push({ regel, reden: e?.code === 'VERVULLING_BESTAAT' ? 'bestaat al' : (e?.message || 'mislukt') })
    }
  }
  return mislukt
}

async function opslaan() {
  if (!valideer()) return
  bezig.value = true
  regelOpslaanFout.value = null
  try {
    let resultaat
    if (bewerken.value) {
      resultaat = await api.componenten.werkBij(props.id, _payload())
    } else if (aangemaaktId.value) {
      // Retry-pad: het component stáát al (eerdere regel-fout) — alleen de regels opnieuw.
      resultaat = { id: aangemaaktId.value }
    } else {
      resultaat = await api.componenten.maak(_payload())
      aangemaaktId.value = resultaat.id
    }
    // Verzamelde procesregels ná het component opslaan (alleen aanmaken-pad).
    if (!bewerken.value && procesRegels.value.length) {
      const mislukt = await _slaRegelsOp(resultaat.id)
      if (mislukt.length) {
        // Component staat; geslaagde regels weg uit het lijstje, mislukte leesbaar tonen.
        const misluktSet = new Set(mislukt.map((m) => m.regel))
        procesRegels.value = procesRegels.value.filter((r) => misluktSet.has(r))
        regelOpslaanFout.value =
          `Het component is aangemaakt, maar ${mislukt.length} proceskoppeling(en) konden niet worden ` +
          `opgeslagen: ${mislukt.map((m) => `"${m.regel.functie_label}" in ${m.regel.proces_weergave} (${m.reden})`).join('; ')}. ` +
          'Probeer opnieuw of sluit — het component blijft bestaan.'
        return // overlay blijft open; Opslaan = alleen de resterende regels opnieuw
      }
    }
    toast.add({
      severity: 'success',
      summary: bewerken.value ? 'Wijzigingen opgeslagen' : 'Component aangemaakt',
      life: 3000,
    })
    _schoneStand = _snapshot()
    emit('opgeslagen', resultaat)
    emit('update:visible', false)
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Annuleren — bevestiging bij gewijzigde velden ────────────────────────────
const annuleerBevestigOpen = ref(false)
function annuleer() {
  // Ná een gedeeltelijk geslaagde aanmaak (component staat al) is sluiten géén verlies
  // van het component — wel van de resterende regels; dat zegt de banner al.
  if (aangemaaktId.value) {
    emit('opgeslagen', { id: aangemaaktId.value })
    emit('update:visible', false)
    return
  }
  if (isGewijzigd()) {
    annuleerBevestigOpen.value = true
    return
  }
  emit('update:visible', false)
}
function bevestigAnnuleren() {
  annuleerBevestigOpen.value = false
  emit('update:visible', false)
}
</script>

<template>
  <!-- Breedte: het Dialog-preset capt élke dialog op max-w-lg (512px) — voor deze
       twee-koloms-overlay bewust per instantie overschreven met !important-utilities
       (anders wint de preset-cap en drukken de kolommen samen; browserbevinding 4b). -->
  <Dialog
    :visible="visible"
    modal
    :closable="false"
    :header="bewerken ? 'Component bewerken' : 'Nieuw component'"
    data-testid="component-form-overlay"
    class="!w-[min(60rem,95vw)] !max-w-[min(60rem,95vw)]"
    @update:visible="(v) => (v ? emit('update:visible', v) : annuleer())"
  >
    <!-- GEEN eigen scroll-wrapper hier: het preset-content is hét scroll-gebied (met
         eigen padding, zodat veldranden en focus-ringen niet tegen de scrollrand
         clippen) en draagt de scroll-schaduw; de voetbalk staat in het #footer-slot
         en blijft dus altijd in beeld (browserbevindingen 4b). -->
    <form id="component-form-el" data-testid="component-form" @submit.prevent="opslaan">
      <div class="grid grid-cols-1 gap-[var(--lk-space-lg)] md:grid-cols-2">
        <!-- ── Linkerkolom: Basis + Inzet en eigenaarschap ─────────────── -->
        <div class="flex flex-col gap-[var(--lk-space-md)]">
          <h3 class="font-semibold text-[var(--lk-color-primary)]">Basis</h3>
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
              class="lk-veld"
            >
              <option value="" disabled>— maak een keuze —</option>
              <option v-for="o in typeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
            </select>
            <span v-if="typeVergrendeld" data-testid="type-vergrendeld-hint" class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">
              Type vergrendeld: dit component bevat al gegevens. Verwijder het component om het type te wijzigen.
            </span>
            <span v-if="fouten.componenttype" role="alert" data-testid="fout-componenttype" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.componenttype }}</span>
          </div>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <label for="f-beschrijving" class="font-semibold">Beschrijving</label>
            <Textarea id="f-beschrijving" v-model="form.beschrijving" rows="3" data-testid="veld-beschrijving" />
          </div>

          <h3 class="mt-[var(--lk-space-sm)] font-semibold text-[var(--lk-color-primary)]">Inzet en eigenaarschap</h3>
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

          <!-- Procesregels: aanmaken = verzamelend; bewerken = direct-opslaand (zelfde
               semantiek als het Overzicht — de sectie is dezelfde bouwsteen). -->
          <template v-if="bewerken">
            <ComponentProcessenSectie v-if="visible" :component-id="props.id" :component-naam="form.naam" />
          </template>
          <div v-else class="flex flex-col gap-[var(--lk-space-sm)]" data-testid="regels-verzamelaar">
            <div class="flex items-center gap-[var(--lk-space-xs)]">
              <span class="font-semibold">Vervult een rol in</span>
              <VeldUitleg veld="applicatiefunctie" testid="uitleg-applicatiefunctie-form" />
            </div>
            <MeldingBanner v-if="regelOpslaanFout" soort="danger" :tekst="regelOpslaanFout" testid="regels-opslaanfout" />
            <ul v-if="procesRegels.length" class="divide-y divide-[var(--lk-color-border)]" data-testid="regels-lijst">
              <li v-for="(r, i) in procesRegels" :key="`${r.proces_id}-${r.applicatiefunctie}`" class="flex items-baseline gap-[var(--lk-space-sm)] py-[var(--lk-space-xs)]">
                <span class="min-w-0 text-[length:var(--lk-text-sm)]">
                  <em>{{ r.functie_label }}</em> in {{ r.proces_weergave }}
                  <span v-if="r.toelichting" class="text-[var(--lk-color-text-muted)]"> — {{ r.toelichting }}</span>
                </span>
                <button
                  type="button"
                  :data-testid="`regel-verwijder-${i}`"
                  :aria-label="`Verwijder regel ${r.functie_label} in ${r.proces_weergave}`"
                  class="ml-auto shrink-0 font-semibold text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-danger)]"
                  @click="verwijderRegel(i)"
                >×</button>
              </li>
            </ul>
            <div class="flex flex-wrap items-end gap-[var(--lk-space-sm)]">
              <label class="flex min-w-[12rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
                <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Proces</span>
                <ZoekSelect
                  :key="regelPickerKey"
                  v-model="regelProcesId"
                  :zoek-functie="zoekProcessen"
                  :weergave="procesWeergave"
                  placeholder="Zoek een proces…"
                  testid="regel-proces"
                  @keuze="(p) => (regelProces = p)"
                />
              </label>
              <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
                <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Applicatiefunctie</span>
                <select v-model="regelFunctie" data-testid="regel-functie" class="lk-veld">
                  <option value="">— kies —</option>
                  <option v-for="f in functies" :key="f.optie_sleutel" :value="f.optie_sleutel">{{ f.label }}</option>
                </select>
              </label>
              <label class="flex min-w-[10rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
                <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Toelichting</span>
                <input v-model="regelToelichting" type="text" maxlength="500" data-testid="regel-toelichting" class="lk-veld" />
              </label>
              <Button type="button" label="+" data-testid="regel-toevoegen" severity="secondary" aria-label="Voeg procesregel toe" @click="voegRegelToe" />
            </div>
            <span v-if="regelFout" role="alert" data-testid="regel-fout" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-danger)]">{{ regelFout }}</span>
            <p class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
              De regels worden na het aanmaken van het component in één keer opgeslagen.
            </p>
          </div>
        </div>

        <!-- ── Rechterkolom: Classificatie + Plaatsing en migratie ────────── -->
        <div class="flex flex-col gap-[var(--lk-space-md)]">
          <h3 class="font-semibold text-[var(--lk-color-primary)]">Classificatie</h3>
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
              class="lk-veld"
            >
              <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
            </select>
            <span v-if="fouten.componentrol" role="alert" data-testid="fout-componentrol" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.componentrol }}</span>
          </div>
          <fieldset class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] p-[var(--lk-space-sm)]" data-testid="biv-blok">
            <legend class="px-[var(--lk-space-xs)] font-semibold">BIV-classificatie</legend>
            <!-- De drie aspecten naast elkaar (smal scherm → stapelen). -->
            <div class="grid grid-cols-1 gap-[var(--lk-space-sm)] sm:grid-cols-3">
              <div v-for="b in BIV_VELDEN" :key="b.veld" class="flex flex-col gap-[var(--lk-space-xs)]">
                <div class="flex items-center gap-[var(--lk-space-xs)]">
                  <label :for="`f-${b.veld}`" class="text-[length:var(--lk-text-sm)]">{{ b.label }}</label>
                  <VeldUitleg :veld="b.veld" />
                </div>
                <select
                  :id="`f-${b.veld}`"
                  v-model="form[b.veld]"
                  :data-testid="`veld-${b.veld}`"
                  class="lk-veld w-full min-w-0"
                >
                  <option value="">—</option>
                  <option v-for="n in bivNiveaus" :key="n.optie_sleutel" :value="n.optie_sleutel">{{ n.label }}</option>
                </select>
              </div>
            </div>
            <span v-if="fouten.biv" role="alert" data-testid="fout-biv" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.biv }}</span>
          </fieldset>

          <h3 class="mt-[var(--lk-space-sm)] font-semibold text-[var(--lk-color-primary)]">Plaatsing en migratie</h3>
          <!-- ADR-046 — rij 1: Levensfase ("draait het?") NAAST Bedoeling ("waar gaat het
               heen?"); daarna hosting/complexiteit/prioriteit. Smal scherm → stapelen. -->
          <div class="grid grid-cols-1 gap-[var(--lk-space-sm)] sm:grid-cols-2" data-testid="plaatsing-blok">
            <div v-for="p in PLAATSING_VELDEN" :key="p.veld" class="flex flex-col gap-[var(--lk-space-xs)]">
              <div class="flex items-center gap-[var(--lk-space-xs)]">
                <label :for="`f-${p.veld}`" class="font-semibold text-[length:var(--lk-text-sm)]">{{ p.label }}</label>
                <VeldUitleg :veld="p.uitleg" />
              </div>
              <select
                :id="`f-${p.veld}`"
                v-model="form[p.veld]"
                :data-testid="`veld-${p.veld}`"
                class="lk-veld w-full min-w-0"
              >
                <!-- Leeg-optie (alleen levensfase): "nog niet vastgelegd" is een geldige,
                     opslagbare stand — leeg ≠ fout (ADR-046 vormkeuze B). -->
                <option v-if="p.leegLabel" value="">{{ p.leegLabel }}</option>
                <option v-for="code in Object.keys(p.opties)" :key="code" :value="code">{{ optieLabel(p.opties, code) }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </form>

    <!-- Vaste voetbalk in het #footer-slot — buiten het scroll-gebied, altijd in beeld.
         `form="component-form-el"` houdt Opslaan een echte submit van het formulier
         (Enter in een veld blijft dus ook gewoon opslaan). -->
    <template #footer>
      <div class="flex w-full gap-[var(--lk-space-md)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]" data-testid="form-voetbalk">
        <Button type="submit" form="component-form-el" :label="aangemaaktId ? 'Opnieuw proberen' : 'Opslaan'" data-testid="opslaan-knop" :disabled="bezig || laden" />
        <Button type="button" :label="aangemaaktId ? 'Sluiten' : 'Annuleren'" severity="secondary" data-testid="annuleer-knop" @click="annuleer" />
      </div>
    </template>

    <!-- Annuleren-bevestiging bij gewijzigde velden. -->
    <BevestigVerwijderDialog
      v-model:visible="annuleerBevestigOpen"
      kop="Wijzigingen verwerpen?"
      omschrijving="Je hebt velden ingevuld of gewijzigd die nog niet zijn opgeslagen. Sluiten zonder opslaan?"
      bevestig-label="Verwerpen"
      testid="form-annuleer"
      @bevestig="bevestigAnnuleren"
    />
  </Dialog>
</template>
