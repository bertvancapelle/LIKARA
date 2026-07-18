<script setup>
/**
 * BewustGeenControl — ADR-052 slice 2. De consultant spreekt uit: "vastgesteld — dit component
 * heeft geen <koppelingen/contract>". Een BEVINDING, streng onderscheiden van "nog niet vastgesteld".
 *
 * Gedeelde bouwsteen (n≥2): gebruikt door KoppelingSectie én ContractSectie — één mechanisme, geen
 * parallel. Volgt de taal/kleur van de bedrijfsfunctie-"bewust niets" (grijs `--lk-color-text-muted`,
 * ⊘ = een afgerond besluit). **Real wins:** is er een échte registratie (`heeftEcht`), dan toont dit
 * niets — de lijst spreekt (nooit een tegenspraak op het scherm). Rol: registratie-feit → medewerker+
 * (`mag`); de backend handhaaft.
 */
import { ref, watch } from 'vue'
import { Button, useToast } from '@/primevue'
import { toastSucces } from '@/meldingen'
import { api } from '@/api'

const props = defineProps({
  componentId: { type: String, required: true },
  soort: { type: String, required: true },        // 'koppelingen' | 'contract'
  onderwerp: { type: String, required: true },    // leesbaar, bv. 'koppelingen' / 'contract'
  heeftEcht: { type: Boolean, default: false },   // echte registratie aanwezig → real wins
  mag: { type: Boolean, default: false },         // medewerker+ (registratie-feit)
})
const emit = defineEmits(['gewijzigd'])

const toast = useToast()
const gezet = ref(false)  // staat de "bewust geen"-bevinding?
const bezig = ref(false)

async function laad() {
  try {
    const rijen = await api.componentBevindingen.lijst(props.componentId)
    gezet.value = (rijen || []).some((r) => r.soort === props.soort)
  } catch {
    gezet.value = false
  }
}
watch(() => props.componentId, laad, { immediate: true })

async function zetGeen() {
  bezig.value = true
  try {
    await api.componentBevindingen.maak(props.componentId, { soort: props.soort })
    gezet.value = true
    toastSucces(toast, `Vastgelegd: geen ${props.onderwerp}`)
    emit('gewijzigd')
  } catch (e) {
    if (e?.status === 409) toast?.add?.({ severity: 'warn', summary: e?.message || 'Er is al een registratie.', life: 3500 })
    else if (e?.status !== 401) toast?.add?.({ severity: 'error', summary: 'Vastleggen mislukt.', life: 3000 })
    await laad()
  } finally {
    bezig.value = false
  }
}

async function trekIn() {
  bezig.value = true
  try {
    await api.componentBevindingen.verwijder(props.componentId, props.soort)
    gezet.value = false
    toastSucces(toast, 'Bevinding ingetrokken')
    emit('gewijzigd')
  } catch (e) {
    if (e?.status !== 401) toast?.add?.({ severity: 'error', summary: 'Intrekken mislukt.', life: 3000 })
  } finally {
    bezig.value = false
  }
}
</script>

<template>
  <!-- Real wins: bij een echte registratie tonen we niets (de lijst spreekt; geen tegenspraak). -->
  <div
    v-if="!heeftEcht"
    :data-testid="`bewustgeen-${soort}`"
    class="flex flex-wrap items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
  >
    <template v-if="gezet">
      <span :data-testid="`bewustgeen-vastgesteld-${soort}`">⊘ Vastgesteld: dit component heeft geen {{ onderwerp }}.</span>
      <Button
        v-if="mag" label="Intrekken" outlined :disabled="bezig"
        :data-testid="`bewustgeen-intrek-${soort}`" @click="trekIn"
      />
    </template>
    <template v-else>
      <span :data-testid="`bewustgeen-open-${soort}`">Nog niet vastgesteld of dit component {{ onderwerp }} heeft.</span>
      <Button
        v-if="mag" :label="`Vastleggen: geen ${onderwerp}`" outlined :disabled="bezig"
        :data-testid="`bewustgeen-zet-${soort}`" @click="zetGeen"
      />
    </template>
  </div>
</template>
