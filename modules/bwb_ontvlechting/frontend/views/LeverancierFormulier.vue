<script setup>
/**
 * LeverancierFormulier — aanmaken (geen `id`) of bewerken (`id` via route-prop).
 *
 * Puur registratief: alleen `naam` verplicht; adres-, contact- en omschrijvingsvelden
 * vrij. GEEN formaatvalidatie op email/telefoon (ADR-020 B-besluit). 422-veldfouten
 * van de backend worden op de juiste velden gezet.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { api } from '@/api'

const props = defineProps({ id: { type: String, default: null } })
const router = useRouter()
const toast = useToast()

const bewerken = computed(() => !!props.id)
const bezig = ref(false)

const VELDEN = [
  'naam', 'straat_huisnummer', 'postcode', 'plaats',
  'contactpersoon', 'telefoon', 'mobiel', 'email', 'omschrijving',
]
const form = reactive(Object.fromEntries(VELDEN.map((v) => [v, ''])))
const fouten = reactive({})

async function init() {
  if (!bewerken.value) return
  try {
    const l = await api.leveranciers.haal(props.id)
    for (const v of VELDEN) form[v] = l[v] || ''
  } catch (e) {
    _toastFout(e)
  }
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.naam.trim()) fouten.naam = 'Naam is verplicht.'
  else if (form.naam.trim().length > 255) fouten.naam = 'Maximaal 255 tekens.'
  return Object.keys(fouten).length === 0
}

function _payload() {
  const uit = {}
  for (const v of VELDEN) {
    const w = form[v].trim()
    uit[v] = v === 'naam' ? w : w || null
  }
  return uit
}

function _serverveldfouten(e) {
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let t = false
    for (const d of e.detail) {
      const veld = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (veld && veld in form) {
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
      ? await api.leveranciers.werkBij(props.id, data)
      : await api.leveranciers.maak(data)
    toast.add({ severity: 'success', summary: bewerken.value ? 'Wijzigingen opgeslagen' : 'Leverancier aangemaakt', life: 3000 })
    router.push({ name: 'leverancier-detail', params: { id: res.id } })
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

function annuleer() {
  if (bewerken.value) router.push({ name: 'leverancier-detail', params: { id: props.id } })
  else router.push({ name: 'leverancier-lijst' })
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
  <section aria-labelledby="lev-form-titel">
    <h1
      id="lev-form-titel"
      class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)] mb-[var(--cd-space-lg)]"
    >
      {{ bewerken ? 'Externe partij bewerken' : 'Nieuwe externe partij' }}
    </h1>

    <form class="card flex flex-col gap-[var(--cd-space-md)] max-w-2xl" data-testid="leverancier-form" @submit.prevent="opslaan">
      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="lf-naam" class="font-semibold">Naam *</label>
        <InputText id="lf-naam" v-model="form.naam" data-testid="veld-naam" :aria-invalid="!!fouten.naam" aria-describedby="fout-naam" />
        <span v-if="fouten.naam" id="fout-naam" role="alert" data-testid="fout-naam" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.naam }}</span>
      </div>

      <div v-for="v in TEKSTVELDEN" :key="v.veld" class="flex flex-col gap-[var(--cd-space-xs)]">
        <label :for="`lf-${v.veld}`" class="font-semibold">{{ v.label }}</label>
        <InputText :id="`lf-${v.veld}`" v-model="form[v.veld]" :data-testid="`veld-${v.veld}`" :aria-invalid="!!fouten[v.veld]" :aria-describedby="`fout-${v.veld}`" />
        <span v-if="fouten[v.veld]" :id="`fout-${v.veld}`" role="alert" :data-testid="`fout-${v.veld}`" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten[v.veld] }}</span>
      </div>

      <div class="flex flex-col gap-[var(--cd-space-xs)]">
        <label for="lf-omschrijving" class="font-semibold">Omschrijving</label>
        <Textarea id="lf-omschrijving" v-model="form.omschrijving" rows="3" data-testid="veld-omschrijving" />
      </div>

      <div class="flex gap-[var(--cd-space-md)] mt-[var(--cd-space-sm)]">
        <Button type="submit" label="Opslaan" data-testid="opslaan-knop" :disabled="bezig" />
        <Button type="button" label="Annuleren" severity="secondary" data-testid="annuleer-knop" @click="annuleer" />
      </div>
    </form>
  </section>
</template>
