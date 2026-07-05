<script setup>
/**
 * ContactpersoonSelect (ADR-039) — kies het aanspreekpunt van een organisatie/externe partij:
 * een persoon die BIJ die partij hoort (persoon.organisatie_id == deze partij; de picker spiegelt
 * die backend-regel). Search-first: staat de juiste persoon er nog niet, dan maakt de gebruiker 'm
 * ter plekke aan via een klein inline-formulier (naam verplicht + functietitel/e-mail/telefoon/
 * mobiel/afdeling), zonder de flow te verlaten. De nieuwe persoon krijgt deze partij als thuis
 * (organisatie_id = deze partij) en wordt meteen als aanspreekpunt gekozen. Aanmaken alleen met recht.
 */
import { computed, ref } from 'vue'
import { InputText, useToast } from '@/primevue'
import { api } from '@/api'
import ZoekSelect from './ZoekSelect.vue'
import AfdelingSelect from './AfdelingSelect.vue'

const props = defineProps({
  partijId: { type: String, required: true },   // "deze partij" (organisatie/externe partij)
  modelValue: { type: String, default: null },  // contactpersoon_id
  initieelWeergave: { type: String, default: '' },
  magAanmaken: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
const toast = useToast()

// Persoon-picker: alleen personen die bij déze partij horen (spiegelt de service-regel; nooit een
// keuze die bij opslaan 422 oplevert).
const zoekPersonen = (params) =>
  api.partijen.lijst({ ...params, aard: 'persoon', organisatie_id: props.partijId })

const persoonKey = ref(0)
// De weergavenaam voor de ZoekSelect: volgt de (async binnenkomende) `initieelWeergave`-prop, of de
// naam van een net ter-plekke aangemaakte persoon (override). Reactief, zodat een label dat ná mount
// resolvet (bewerken) alsnog in het veld verschijnt.
const naAanmaakNaam = ref('')
const persoonInitieel = computed(() => naAanmaakNaam.value || props.initieelWeergave)

// Inline-aanmaak (search-first; onder de picker, geen popup-op-popup).
const aanmaakOpen = ref(false)
const bezig = ref(false)
const nieuw = ref({ naam: '', functietitel: '', email: '', telefoon: '', mobiel: '', afdeling_id: null })
const naamFout = ref('')

function onKies(id) {
  emit('update:modelValue', id || null)
}

function openAanmaak(query) {
  nieuw.value = { naam: query || '', functietitel: '', email: '', telefoon: '', mobiel: '', afdeling_id: null }
  naamFout.value = ''
  aanmaakOpen.value = true
}
function annuleerAanmaak() {
  aanmaakOpen.value = false
}

async function maakAan() {
  const naam = (nieuw.value.naam || '').trim()
  if (!naam) {
    naamFout.value = 'Naam is verplicht.'
    return
  }
  bezig.value = true
  try {
    const p = await api.partijen.maak({
      aard: 'persoon',
      naam,
      organisatie_id: props.partijId,
      afdeling_id: nieuw.value.afdeling_id || null,
      functietitel: nieuw.value.functietitel.trim() || null,
      email: nieuw.value.email.trim() || null,
      telefoon: nieuw.value.telefoon.trim() || null,
      mobiel: nieuw.value.mobiel.trim() || null,
    })
    naAanmaakNaam.value = p.naam
    persoonKey.value += 1 // remount → toon + selecteer de nieuwe persoon (bewijst 'in de lijst')
    emit('update:modelValue', p.id)
    aanmaakOpen.value = false
    toast.add({ severity: 'success', summary: 'Aanspreekpunt aangemaakt', life: 3000 })
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
      :key="persoonKey"
      testid="veld-contactpersoon"
      :model-value="props.modelValue"
      :zoek-functie="zoekPersonen"
      :initieel-weergave="persoonInitieel"
      placeholder="Zoek een persoon van deze partij…"
      @update:model-value="onKies"
    >
      <template #leeg="{ query }">
        <button
          v-if="magAanmaken"
          type="button"
          data-testid="cp-aanmaak-open"
          class="w-full text-left text-[var(--lk-color-primary)] hover:underline"
          @mousedown.prevent
          @click="openAanmaak(query)"
        >
          Geen persoon{{ query ? ` ‘${query}’` : '' }} gevonden — nieuwe contactpersoon aanmaken
        </button>
        <span v-else>Geen persoon gevonden.</span>
      </template>
    </ZoekSelect>

    <!-- Inline aanmaak-zijstap (niveau 1): getinte, omrande afbakening; naam voorgevuld met de zoekterm. -->
    <div
      v-if="aanmaakOpen"
      data-testid="cp-aanmaak-form"
      class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-primary-100)] bg-[var(--lk-color-primary-50)] p-[var(--lk-space-sm)] flex flex-col gap-[var(--lk-space-sm)]"
    >
      <span class="font-semibold text-[length:var(--lk-text-sm)]">Nieuwe contactpersoon</span>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cp-naam" class="text-[length:var(--lk-text-sm)] font-semibold">Naam *</label>
        <InputText id="cp-naam" v-model="nieuw.naam" data-testid="cp-naam" :aria-invalid="!!naamFout" aria-describedby="cp-naam-fout" />
        <span v-if="naamFout" id="cp-naam-fout" role="alert" data-testid="cp-naam-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ naamFout }}</span>
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cp-functie" class="text-[length:var(--lk-text-sm)]">Functietitel</label>
        <InputText id="cp-functie" v-model="nieuw.functietitel" data-testid="cp-functietitel" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cp-email" class="text-[length:var(--lk-text-sm)]">E-mail</label>
        <InputText id="cp-email" v-model="nieuw.email" data-testid="cp-email" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cp-tel" class="text-[length:var(--lk-text-sm)]">Telefoon</label>
        <InputText id="cp-tel" v-model="nieuw.telefoon" data-testid="cp-telefoon" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cp-mob" class="text-[length:var(--lk-text-sm)]">Mobiel</label>
        <InputText id="cp-mob" v-model="nieuw.mobiel" data-testid="cp-mobiel" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="cp-afd" class="text-[length:var(--lk-text-sm)]">Afdeling (binnen deze partij)</label>
        <!-- Genest aanmaakblok (niveau 2): een afdeling die nog niet bestaat kan hier ter plekke,
             één tint dieper. Afdeling = naam-only → bladniveau, geen laag 3. -->
        <AfdelingSelect
          id="cp-afd"
          testid="cp-afdeling"
          :partij-id="props.partijId"
          :model-value="nieuw.afdeling_id"
          :mag-aanmaken="props.magAanmaken"
          genest
          placeholder="Zoek een afdeling (optioneel)…"
          @update:model-value="(v) => (nieuw.afdeling_id = v || null)"
        />
      </div>
      <div class="flex gap-[var(--lk-space-md)]">
        <button
          type="button"
          data-testid="cp-aanmaak-bevestig"
          class="font-semibold text-[var(--lk-color-primary)] hover:underline disabled:opacity-60"
          :disabled="bezig"
          @click="maakAan"
        >
          Aanmaken en kiezen
        </button>
        <button
          type="button"
          data-testid="cp-aanmaak-annuleer"
          class="text-[var(--lk-color-text-muted)] hover:underline"
          @click="annuleerAanmaak"
        >
          Annuleren
        </button>
      </div>
    </div>
  </div>
</template>
