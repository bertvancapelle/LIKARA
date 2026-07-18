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
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { usePopoverPositie } from '@/composables/popoverPositie'
import { Button, Dialog, Tag, Textarea, useToast } from '@/primevue'
import { api } from '@/api'
import { KLAARVERKLARING_SEVERITY, KLAARVERKLARING_STATUS, NORM_FEIT_LABEL, REGISTER_FOUT, label } from '../labels'

const props = defineProps({
  componentId: { type: String, required: true },
  aantalGescoord: { type: Number, default: 0 },
  aantalVragen: { type: Number, default: 0 },
})

const toast = useToast()
const verklaring = ref(null) // de levende verklaring, of null
// ADR-052 slice 3 — LIVE norm-status: de verplichte feiten die NU niet vastgesteld zijn (badge =
// nu; de bevroren snapshot leeft op de klaarverklaring zelf). Eén norm-definitie, twee peildata.
const normOpen = ref([])
// Slice 4a (besluiten 8-11) — het onderscheid, LIVE afgeleid uit één backend-bron (afwijking):
// bewust = bij het verklaren afgewogen (amber); verschoven = de lat verschoof sindsdien (neutraal).
const bewust = ref([])
const verschoven = ref([])
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
// ADR-052 slice 3/4a — norm-afwijking. De DIALOG toont alle nu-open verplichte feiten (normOpen);
// de BADGES splitsen tussen bewust (amber) en verschoven (neutraal) — besluiten 8-11.
const normOpenLabels = computed(() => normOpen.value.map((f) => label(NORM_FEIT_LABEL, f)))
const bewustLabels = computed(() => bewust.value.map((f) => label(NORM_FEIT_LABEL, f)))
const verschovenLabels = computed(() => verschoven.value.map((f) => label(NORM_FEIT_LABEL, f)))
const heeftNormAfwijking = computed(() => isKlaar.value && bewust.value.length > 0)      // amber (bewust)
const heeftVerschovenLat = computed(() => isKlaar.value && verschoven.value.length > 0)  // neutraal
const toontNormAfwijking = computed(() => !isKlaar.value && normOpen.value.length > 0)   // in de dialog
// Drempel hangt aan de AFWIJKING, niet aan de handeling (ADR-052 besluit 5 / L1a-uitzondering).
const bevestigLabel = computed(() => (toontNormAfwijking.value ? 'Toch klaar verklaren' : actieLabel.value))

// ── ADR-052 slice 3b — verantwoordingsvenster (klik op een amber regel) ─────────────────────────
// Reden/wie/wanneer + de BEVROREN snapshot (open_feiten bij het verklaren). Beide amber regels
// (checklist + norm) openen HETZELFDE venster — één klaarverklaring = één besluit. Van-scratch
// overlay (PrimeVue Unstyled), a11y-patroon gemodelleerd op VeldUitleg (Escape/klik-buiten/focus-terug).
const verantwoordingOpen = ref(false)
const verantwoordingWortel = ref(null)
const verantwoordingPaneel = ref(null)
const PANEEL_ID = 'mg-verantwoording-paneel'
let _vTrigger = null
// Gedeelde positioneer-bouwsteen: flipt boven/onder + klemt binnen beeld (position: fixed).
const { stijl: verantwoordingStijl, open: _posOpen, sluit: _posSluit } = usePopoverPositie(verantwoordingPaneel)
// De bevroren snapshot van de klaarverklaring, met leesbare labels (niet de ruwe sleutels).
const snapshotLabels = computed(() => (verklaring.value?.open_feiten || []).map((f) => label(NORM_FEIT_LABEL, f)))

function openVerantwoording(e) {
  _vTrigger = e?.currentTarget ?? document.activeElement
  verantwoordingOpen.value = true
  _posOpen(_vTrigger)
}
function sluitVerantwoording(focusTerug = true) {
  if (!verantwoordingOpen.value) return
  verantwoordingOpen.value = false
  _posSluit()
  if (focusTerug && _vTrigger?.focus) _vTrigger.focus()
}
function _vKeydown(e) {
  if (verantwoordingOpen.value && e.key === 'Escape') sluitVerantwoording(true)
}
function _vClick(e) {
  if (!verantwoordingOpen.value) return
  const w = verantwoordingWortel.value
  if (w && !w.contains(e.target)) sluitVerantwoording(false)
}

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  const detail =
    (e?.code && REGISTER_FOUT[e.code] ? e?.message || REGISTER_FOUT[e.code] : null) ||
    { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }[e?.status] ||
    e?.message ||
    'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function _laadNorm() {
  try {
    const ns = await api.componentNormen.status(props.componentId)
    normOpen.value = Object.entries(ns?.feiten || {})
      .filter(([, s]) => s === 'niet_vastgesteld')
      .map(([f]) => f)
  } catch {
    normOpen.value = []  // norm niet leesbaar → geen badge/afwijking tonen (fail-safe, geen ruis)
  }
  try {
    const af = await api.componentNormen.afwijking(props.componentId)  // bewust vs. verschoven (één bron)
    bewust.value = af?.bewust || []
    verschoven.value = af?.verschoven || []
  } catch {
    bewust.value = []
    verschoven.value = []
  }
}

async function laad() {
  try {
    const rijen = await api.klaarverklaringen.lijst({ component_id: props.componentId })
    verklaring.value = rijen[0] ?? null
  } catch (e) {
    verklaring.value = null
    _toastFout(e)
  }
  await _laadNorm()
}

function openDialog(event) {
  laatsteTrigger = event?.currentTarget ?? document.activeElement
  reden.value = ''
  Object.keys(fouten).forEach((k) => delete fouten[k])
  _laadNorm()  // verse norm-status bij het openen (feiten kunnen intussen zijn aangevuld)
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

onMounted(() => {
  laad()
  document.addEventListener('keydown', _vKeydown, true)
  document.addEventListener('click', _vClick, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', _vKeydown, true)
  document.removeEventListener('click', _vClick, true)
})
defineExpose({ status, openDialog, herlaad: laad })

const _datum = (iso) => (iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : '')
</script>

<template>
  <div class="card" data-testid="mg-leesblok" aria-labelledby="mg-titel">
    <h3 id="mg-titel" class="mb-[var(--lk-space-sm)] font-semibold text-[var(--lk-color-text)]">Migratiegereedheid</h3>

    <Tag
      :value="label(KLAARVERKLARING_STATUS, status || 'open')"
      :severity="KLAARVERKLARING_SEVERITY[status || 'open']"
      data-testid="mg-status"
    />

    <!-- ADR-052 slice 3c — bij de status alleen wie/wanneer; de reden verschijnt achter de
         waarschuwing (klik), niet permanent in beeld. -->
    <p v-if="verklaring" data-testid="mg-door" class="mt-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
      door {{ verklaring.verklaard_door_naam || verklaring.verklaard_door || 'onbekend' }} · {{ _datum(verklaring.verklaard_op) }}
    </p>

    <!-- ADR-052 slice 3b — de amber regels zijn klikbaar en openen HETZELFDE verantwoordingsvenster
         (reden/wie/wanneer + bevroren snapshot). Eén klaarverklaring = één besluit → één venster.
         De regels blijven LIVE (checklist-stand resp. norm-stand); het venster toont de bevroren
         stand bij het verklaren. -->
    <div
      v-if="heeftAfwijking || heeftNormAfwijking"
      ref="verantwoordingWortel"
      class="relative mt-[var(--lk-space-sm)] flex flex-col gap-[var(--lk-space-xs)]"
    >
      <button
        v-if="heeftAfwijking"
        type="button"
        data-testid="mg-afwijking"
        :aria-expanded="verantwoordingOpen ? 'true' : 'false'"
        :aria-controls="PANEEL_ID"
        aria-label="Klaar verklaard met afwijking — bekijk de verantwoording"
        class="flex w-full items-center gap-[var(--lk-space-xs)] rounded-[var(--lk-radius-input)] bg-[color-mix(in_srgb,var(--lk-color-warning)_12%,transparent)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-left text-[length:var(--lk-text-sm)] text-[var(--lk-color-warning)] underline decoration-dotted underline-offset-2 hover:bg-[color-mix(in_srgb,var(--lk-color-warning)_18%,transparent)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-warning)]"
        @click="openVerantwoording"
      >
        <span aria-hidden="true">⚠</span>
        <span>Klaar verklaard terwijl {{ openVragen }} van {{ aantalVragen }} vragen nog open staan.</span>
      </button>

      <!-- Norm-afwijking (LIVE): dooft zodra de feiten alsnog worden vastgesteld (historie blijft). -->
      <button
        v-if="heeftNormAfwijking"
        type="button"
        data-testid="mg-norm-open"
        :aria-expanded="verantwoordingOpen ? 'true' : 'false'"
        :aria-controls="PANEEL_ID"
        aria-label="Klaar verklaard met openstaande verplichte feiten — bekijk de verantwoording"
        class="flex w-full items-start gap-[var(--lk-space-xs)] rounded-[var(--lk-radius-input)] bg-[color-mix(in_srgb,var(--lk-color-warning)_12%,transparent)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-left text-[length:var(--lk-text-sm)] text-[var(--lk-color-warning)] underline decoration-dotted underline-offset-2 hover:bg-[color-mix(in_srgb,var(--lk-color-warning)_18%,transparent)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-warning)]"
        @click="openVerantwoording"
      >
        <span aria-hidden="true">⚠</span>
        <span>Klaar verklaard, maar {{ bewust.length }} verplicht{{ bewust.length === 1 ? ' feit is' : 'e feiten zijn' }} nog niet vastgesteld: {{ bewustLabels.join(', ') }}.</span>
      </button>

      <!-- Gedeeld verantwoordingsvenster (read-only, ook voor de viewer). Toont juist wat je nog
           NIET zag: de reden + de bevroren stand bij het verklaren (wie/wanneer staat al bij de
           status). Positie via de gedeelde bouwsteen (fixed, flipt/klemt binnen beeld). -->
      <div
        v-show="verantwoordingOpen"
        ref="verantwoordingPaneel"
        :id="PANEEL_ID"
        role="region"
        aria-label="Verantwoording van de klaarverklaring"
        data-testid="mg-verantwoording"
        :style="verantwoordingStijl"
        class="z-20 w-80 max-w-[90vw] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-sm)] shadow-[var(--lk-shadow-md)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text)]"
      >
        <p class="font-semibold">Verantwoording</p>
        <p data-testid="mg-verantwoording-reden" class="mt-[var(--lk-space-xs)] whitespace-pre-wrap">
          <template v-if="verklaring && verklaring.reden">{{ verklaring.reden }}</template>
          <span v-else class="text-[var(--lk-color-text-muted)] italic">Geen reden opgegeven.</span>
        </p>
        <div v-if="snapshotLabels.length" data-testid="mg-verantwoording-snapshot" class="mt-[var(--lk-space-sm)]">
          <p class="text-[var(--lk-color-text-muted)]">Nog niet vastgesteld bij het verklaren:</p>
          <ul class="mt-[var(--lk-space-xs)] list-disc pl-[var(--lk-space-md)]">
            <li v-for="f in snapshotLabels" :key="f">{{ f }}</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Slice 4a (besluiten 2/3/4) — VERSCHOVEN LAT: neutraal, gedempt grijs, géén amber. Staat
         náást de amber verantwoording (besluit 3: beide tonen). De lat verschoof ná het verklaren —
         een uitnodiging om opnieuw te kijken, geen verwijt. -->
    <div
      v-if="heeftVerschovenLat"
      data-testid="mg-verschoven-lat"
      class="mt-[var(--lk-space-sm)] rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
    >
      <p class="flex items-start gap-[var(--lk-space-xs)]">
        <span aria-hidden="true">↔</span>
        <span>Deze verklaring is destijds beoordeeld tegen de lat die toen gold<template v-if="bewust.length === 0"> en was toen compleet</template>.</span>
      </p>
      <p class="mt-[var(--lk-space-xs)]" data-testid="mg-verschoven-tekst">
        <template v-if="verschoven.length === 1">Sindsdien is <strong>{{ verschovenLabels[0] }}</strong> verplicht gesteld — daar is hier nog niet naar gekeken.</template>
        <template v-else>Sindsdien zijn deze verplicht gesteld — daar is hier nog niet naar gekeken:</template>
      </p>
      <ul v-if="verschoven.length > 1" class="mt-[var(--lk-space-xs)] list-disc pl-[var(--lk-space-md)]">
        <li v-for="f in verschovenLabels" :key="f" :data-testid="`mg-verschoven-feit-${f}`">{{ f }}</li>
      </ul>
    </div>

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
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="mg-form" @submit.prevent="bevestig">
        <p
          v-if="toontVragenContext"
          data-testid="mg-dialog-context"
          class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-accent)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]"
        >
          Let op: {{ openVragen }} van {{ aantalVragen }} vragen staan nog open.
        </p>
        <!-- ADR-052 slice 3 — de norm in beeld bij het verklaren: welke verplichte feiten nog niet
             vastgesteld zijn. De machine houdt niets tegen; de consultant beslist bewust. -->
        <div
          v-if="toontNormAfwijking"
          data-testid="mg-dialog-norm"
          class="rounded-[var(--lk-radius-input)] bg-[color-mix(in_srgb,var(--lk-color-warning)_12%,transparent)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]"
        >
          <p class="font-semibold text-[var(--lk-color-warning)]">Nog niet vastgesteld (tenant-norm):</p>
          <ul class="ml-[var(--lk-space-md)] list-disc">
            <li v-for="f in normOpenLabels" :key="f" :data-testid="`mg-norm-feit-${f}`">{{ f }}</li>
          </ul>
          <p class="mt-[var(--lk-space-xs)] text-[var(--lk-color-text-muted)]">
            Je kunt tóch klaar verklaren (bewust besluit, wordt vastgelegd) of eerst aanvullen.
          </p>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
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
          <span v-if="fouten.reden" id="mg-fout-reden" role="alert" data-testid="mg-fout-reden" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.reden }}</span>
        </div>
        <div class="flex justify-end gap-[var(--lk-space-md)]">
          <Button :label="toontNormAfwijking ? 'Eerst aanvullen' : 'Annuleren'" severity="secondary" data-testid="mg-annuleer" @click="sluit" />
          <Button :label="bevestigLabel" type="submit" :disabled="bezig" data-testid="mg-bevestig" />
        </div>
      </form>
    </Dialog>
  </div>
</template>
