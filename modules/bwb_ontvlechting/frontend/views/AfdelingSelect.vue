<script setup>
/**
 * AfdelingSelect (LI032) — kies een afdeling (organisatie_eenheid) van een partij, met search-first
 * ter-plekke-aanmaken zodat het veld nooit doodloopt. Staat de afdeling er nog niet, dan maakt de
 * gebruiker 'm aan (naam = zoekterm) zonder de flow te verlaten; de nieuwe afdeling landt binnen déze
 * partij (organisatie_id = partijId) en wordt meteen gekozen. Soepel zoeken (ilike) voorkomt dubbelen.
 * Aanmaken alleen met recht. `genest` = het aanmaakblok zit ín een ander aanmaakblok → één tint dieper
 * (max twee niveaus; een afdeling is bladniveau — naam-only, geen verder keuzeveld → geen laag 3).
 */
import { computed, ref } from 'vue'
import { InputText, useToast } from '@/primevue'
import { api } from '@/api'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({
  partijId: { type: String, required: true },   // de organisatie waarbinnen de afdeling hoort
  modelValue: { type: String, default: null },  // afdeling_id
  initieelWeergave: { type: String, default: '' },
  magAanmaken: { type: Boolean, default: false },
  orgNaam: { type: String, default: '' },        // contexttekst "aanmaken onder <org>"
  genest: { type: Boolean, default: false },     // aanmaakblok binnen een ander aanmaakblok → dieper
  placeholder: { type: String, default: 'Zoek een afdeling…' },
  id: { type: String, default: null },
  testid: { type: String, default: 'afd' },
})
const emit = defineEmits(['update:modelValue'])
const toast = useToast()

const zoekAfdelingen = (params) =>
  api.partijen.lijst({ ...params, aard: 'organisatie_eenheid', organisatie_id: props.partijId })

const afdKey = ref(0)
const naAanmaakNaam = ref('')
const afdInitieel = computed(() => naAanmaakNaam.value || props.initieelWeergave)

const aanmaakOpen = ref(false)
const bezig = ref(false)
const nieuwNaam = ref('')
const naamFout = ref('')

// Niveau-tint: 1 (primary-50) of, genest, 2 (primary-100, één stap dieper). Max twee niveaus.
const blokTint = computed(() =>
  props.genest ? 'bg-[var(--lk-color-primary-100)]' : 'bg-[var(--lk-color-primary-50)]',
)

function onKies(id) {
  emit('update:modelValue', id || null)
}
function openAanmaak(query) {
  nieuwNaam.value = query || ''
  naamFout.value = ''
  aanmaakOpen.value = true
}
function annuleerAanmaak() {
  aanmaakOpen.value = false
}
async function maakAan() {
  const naam = (nieuwNaam.value || '').trim()
  if (!naam) {
    naamFout.value = 'Naam is verplicht.'
    return
  }
  bezig.value = true
  try {
    const a = await api.partijen.maak({ aard: 'organisatie_eenheid', naam, organisatie_id: props.partijId })
    naAanmaakNaam.value = a.naam
    afdKey.value += 1 // remount → toon + selecteer de nieuwe afdeling
    emit('update:modelValue', a.id)
    aanmaakOpen.value = false
    toast.add({ severity: 'success', summary: 'Afdeling aangemaakt', life: 3000 })
  } catch (e) {
    if (e?.status !== 401) { // 401 → centrale vangrail leidt al naar login (geen rauwe code)
      const per = { 403: 'Geen rechten voor deze actie.', 409: e?.message || 'Conflict.' }
      toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
    }
  } finally {
    bezig.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-[var(--lk-space-xs)]">
    <ZoekSelect
      :key="afdKey"
      :id="props.id"
      :testid="props.testid"
      :model-value="props.modelValue"
      :zoek-functie="zoekAfdelingen"
      :initieel-weergave="afdInitieel"
      :placeholder="props.placeholder"
      @update:model-value="onKies"
    >
      <template #leeg="{ query }">
        <button
          v-if="magAanmaken"
          type="button"
          :data-testid="`${props.testid}-aanmaak-open`"
          class="w-full text-left text-[var(--lk-color-primary)] hover:underline"
          @mousedown.prevent
          @click="openAanmaak(query)"
        >
          Geen afdeling{{ query ? ` ‘${query}’` : '' }} gevonden — nieuwe afdeling aanmaken{{ orgNaam ? ` onder ${orgNaam}` : '' }}
        </button>
        <span v-else>Geen afdeling gevonden.</span>
      </template>
    </ZoekSelect>

    <!-- Inline aanmaak-zijstap: getinte, omrande afbakening; `genest` = één tint dieper (max 2 niveaus). -->
    <div
      v-if="aanmaakOpen"
      :data-testid="`${props.testid}-aanmaak-form`"
      class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-primary-100)] p-[var(--lk-space-sm)] flex flex-col gap-[var(--lk-space-sm)]"
      :class="blokTint"
    >
      <span class="font-semibold text-[length:var(--lk-text-sm)]">Nieuwe afdeling</span>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label :for="`${props.testid}-naam`" class="text-[length:var(--lk-text-sm)] font-semibold">Naam *</label>
        <InputText :id="`${props.testid}-naam`" v-model="nieuwNaam" :data-testid="`${props.testid}-naam`" :aria-invalid="!!naamFout" />
        <span v-if="naamFout" role="alert" :data-testid="`${props.testid}-naam-fout`" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ naamFout }}</span>
      </div>
      <div class="flex gap-[var(--lk-space-md)]">
        <button
          type="button"
          :data-testid="`${props.testid}-aanmaak-bevestig`"
          class="font-semibold text-[var(--lk-color-primary)] hover:underline disabled:opacity-60"
          :disabled="bezig"
          @click="maakAan"
        >
          Aanmaken en kiezen
        </button>
        <button
          type="button"
          :data-testid="`${props.testid}-aanmaak-annuleer`"
          class="text-[var(--lk-color-text-muted)] hover:underline"
          @click="annuleerAanmaak"
        >
          Annuleren
        </button>
      </div>
    </div>
  </div>
</template>
