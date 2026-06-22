<script setup>
/**
 * MigratiegereedheidSectie — leesblok + handeling voor de component-klaarverklaring (ADR-027 slice 2).
 *
 * Read-only leesblok "Migratiegereedheid" (status/wie/wanneer/reden + afwijkingssignaal) plus de
 * handel-Dialog (verplichte reden). Herbruikbaar: gemount op een component-/applicatie-detail met
 * `component-id`. De trigger-knop staat bewust in de knoppenrij van het ouder-scherm en roept
 * `openDialog()` aan (via een ref) — de sectie `defineExpose`t status + openDialog, zoals het
 * score→lifecycle-coördinatiepatroon. Klaar verklaren raakt de score NOOIT (apart oordeel).
 *
 * Het afwijkingssignaal hergebruikt de bestaande vragen-stand (`aantal-gescoord`/`aantal-vragen`
 * uit de ChecklistscoreSectie-ref van het ouder-scherm) — geen tweede telling.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Dialog, Tag, Textarea, useToast } from '@/primevue'
import { api } from '@/api'
import { KLAARVERKLARING_SEVERITY, KLAARVERKLARING_STATUS, REGISTER_FOUT, label } from '../labels'

const props = defineProps({
  componentId: { type: String, required: true },
  aantalGescoord: { type: Number, default: 0 },
  aantalVragen: { type: Number, default: 0 },
})

const toast = useToast()
const verklaring = ref(null) // de levende verklaring, of null
const dialogOpen = ref(false)
const bezig = ref(false)
const reden = ref('')
const fouten = reactive({})
const redenVeld = ref(null)
let laatsteTrigger = null

const status = computed(() => verklaring.value?.status ?? null)
const isKlaar = computed(() => status.value === 'klaar')
// De handeling maakt 'klaar' als het nog niet klaar is, en zet 'open' als het al klaar is.
const actieLabel = computed(() => (isKlaar.value ? 'Heropenen' : 'Klaar verklaren'))
// Afwijking: klaar verklaard terwijl nog niet alle vragen beantwoord zijn.
const openVragen = computed(() => Math.max(props.aantalVragen - props.aantalGescoord, 0))
const heeftAfwijking = computed(() => isKlaar.value && props.aantalVragen > 0 && openVragen.value > 0)
// In de dialog: toon de open-vragen-context wanneer de handeling het component klaar zet.
const toontVragenContext = computed(() => !isKlaar.value && props.aantalVragen > 0 && openVragen.value > 0)

function _toastFout(e) {
  const detail =
    (e?.code && REGISTER_FOUT[e.code] ? e?.message || REGISTER_FOUT[e.code] : null) ||
    { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }[e?.status] ||
    e?.message ||
    'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  try {
    const rijen = await api.klaarverklaringen.lijst({ component_id: props.componentId })
    verklaring.value = rijen[0] ?? null
  } catch (e) {
    verklaring.value = null
    _toastFout(e)
  }
}

function openDialog(event) {
  laatsteTrigger = event?.currentTarget ?? document.activeElement
  reden.value = ''
  Object.keys(fouten).forEach((k) => delete fouten[k])
  dialogOpen.value = true
}

function sluit() {
  dialogOpen.value = false
  if (laatsteTrigger?.focus) setTimeout(() => laatsteTrigger.focus(), 0)
}

function _serverveldfout(e) {
  if (e?.status === 422 && Array.isArray(e.detail)) {
    for (const d of e.detail) {
      const veld = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (veld === 'reden') {
        fouten.reden = d.msg || 'Ongeldige waarde.'
        return true
      }
    }
  }
  return false
}

async function bevestig() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!reden.value.trim()) {
    fouten.reden = 'Reden is verplicht.'
    return
  }
  bezig.value = true
  try {
    if (verklaring.value) {
      await api.klaarverklaringen.wijzigStatus(verklaring.value.id, {
        status: isKlaar.value ? 'open' : 'klaar',
        reden: reden.value.trim(),
      })
    } else {
      await api.klaarverklaringen.maak({ component_id: props.componentId, reden: reden.value.trim() })
    }
    await laad()
    toast.add({ severity: 'success', summary: 'Opgeslagen', detail: 'Migratiegereedheid bijgewerkt.', life: 3000 })
    sluit()
  } catch (e) {
    if (!_serverveldfout(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(laad)
defineExpose({ status, openDialog, herlaad: laad })

const _datum = (iso) => (iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : '')
</script>

<template>
  <div class="card" data-testid="mg-leesblok" aria-labelledby="mg-titel">
    <h3 id="mg-titel" class="mb-[var(--cd-space-sm)] font-semibold text-[var(--cd-color-text)]">Migratiegereedheid</h3>

    <Tag
      :value="label(KLAARVERKLARING_STATUS, status || 'open')"
      :severity="KLAARVERKLARING_SEVERITY[status || 'open']"
      data-testid="mg-status"
    />

    <p v-if="verklaring" data-testid="mg-door" class="mt-[var(--cd-space-sm)] text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
      door {{ verklaring.verklaard_door_naam || verklaring.verklaard_door || 'onbekend' }} · {{ _datum(verklaring.verklaard_op) }}
    </p>
    <p v-if="verklaring" data-testid="mg-reden" class="mt-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)] whitespace-pre-wrap">
      <span class="font-semibold">Reden:</span> {{ verklaring.reden }}
    </p>

    <p
      v-if="heeftAfwijking"
      role="status"
      data-testid="mg-afwijking"
      class="mt-[var(--cd-space-sm)] flex items-center gap-[var(--cd-space-xs)] rounded-[var(--cd-radius-input)] bg-[color-mix(in_srgb,var(--cd-color-warn)_12%,transparent)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)] text-[var(--cd-color-warn)]"
    >
      <span aria-hidden="true">⚠</span>
      Klaar verklaard terwijl {{ openVragen }} van {{ aantalVragen }} vragen nog open staan.
    </p>

    <!-- Handel-dialog (trigger staat in de knoppenrij van het ouder-scherm → openDialog()). -->
    <Dialog
      v-model:visible="dialogOpen"
      modal
      :closable="false"
      :header="actieLabel"
      data-testid="mg-dialog"
      @show="redenVeld?.$el?.focus?.() ?? redenVeld?.focus?.()"
      @hide="sluit"
    >
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[22rem]" data-testid="mg-form" @submit.prevent="bevestig">
        <p
          v-if="toontVragenContext"
          data-testid="mg-dialog-context"
          class="rounded-[var(--cd-radius-input)] bg-[var(--cd-color-accent)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]"
        >
          Let op: {{ openVragen }} van {{ aantalVragen }} vragen staan nog open.
        </p>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="mg-reden" class="font-semibold">Reden *</label>
          <Textarea
            id="mg-reden"
            ref="redenVeld"
            v-model="reden"
            rows="3"
            data-testid="mg-veld-reden"
            :aria-invalid="!!fouten.reden"
            aria-describedby="mg-fout-reden"
          />
          <span v-if="fouten.reden" id="mg-fout-reden" role="alert" data-testid="mg-fout-reden" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.reden }}</span>
        </div>
        <div class="flex justify-end gap-[var(--cd-space-md)]">
          <Button label="Annuleren" severity="secondary" data-testid="mg-annuleer" @click="sluit" />
          <Button :label="actieLabel" type="submit" :disabled="bezig" data-testid="mg-bevestig" />
        </div>
      </form>
    </Dialog>
  </div>
</template>
