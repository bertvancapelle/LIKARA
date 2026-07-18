<script setup>
/**
 * VeldUitleg — herbruikbare veld-uitleg naast een formulierlabel.
 *
 * Twee modi:
 *  - popover (default): een 'i'-knop die op klik én focus een paneel opent met de veld-uitleg
 *    (framing + optionele vuistregel) en — indien een `opties`-set is meegegeven — de per-optie
 *    discriminatie-regels. Sluit op Escape, klik-buiten en herhaalde trigger; focus keert terug
 *    naar de knop.
 *  - inline (`inline`-prop): een korte regel ónder het veld i.p.v. een verstopte popover, voor de
 *    zwaarste velden (precedent: de hint onder Volgorde in BivConfigBeheer).
 *
 * A11y-patroon gemodelleerd op ZoekSelect (from-scratch overlay: aria-expanded, Escape, klik-buiten,
 * focus-terugkeer, --lk-tokens). PrimeVue draait Unstyled en levert geen Tooltip/Popover-primitive.
 *
 * Nette degradatie: geen veld-uitleg én geen optie-uitleg → rendert niets (geen lege 'i').
 */
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { usePopoverPositie } from '@/composables/popoverPositie'
import { optieUitlegLijst, veldUitleg } from '../velduitleg'

const props = defineProps({
  veld: { type: String, required: true },
  // Set-naam voor OPTIE_UITLEG (per-optie regels in de popover); leeg = geen optie-uitleg.
  opties: { type: String, default: null },
  // Inline-modus: korte regel onder het veld i.p.v. popover.
  inline: { type: Boolean, default: false },
  // ADR-052 slice 4c (besluiten 15-21) — de norm-FEIT-sleutel, NIET een plek-boolean. De bouwsteen
  // beslist zélf of de "telt mee om klaar te verklaren; opslaan kan wel zonder"-passage verschijnt,
  // uit de ge-provide norm-stand. Zo draagt elk feit precies ÉÉN aanduiding (besluit 21): een view
  // kan er niet ongemerkt een tweede voor hetzelfde feit bijzetten. De aanduiding hangt aan de norm
  // (verschijnt/verdwijnt met de lat), niet aan of het feit is ingevuld.
  normFeit: { type: String, default: null },
  testid: { type: String, default: null },
})

const LAT_PASSAGE = 'Dit feit telt mee om dit systeem klaar te kunnen verklaren. Opslaan kan wel zonder.'
// De norm-stand ({feit: verplicht}) wordt door het SCHERM ge-provide (ComponentFormulier/-Detail via
// useNormLat). Elders (geen provide) → lege map → geen aanduiding. Backward-compatible.
const normVerplicht = inject('normVerplicht', ref({}))

const tid = computed(() => props.testid || `uitleg-${props.veld}`)
const info = computed(() => veldUitleg(props.veld)) // { uitleg, vuistregel } | null
const optieLijst = computed(() => (props.opties ? optieUitlegLijst(props.opties) : []))
const opDeLat = computed(() => !!props.normFeit && !!(normVerplicht.value || {})[props.normFeit])
const heeftUitlegBoven = computed(() => !!info.value || optieLijst.value.length > 0)
const heeftContent = computed(() => heeftUitlegBoven.value || opDeLat.value)

const open = ref(false)
const knop = ref(null)
const paneel = ref(null)
const paneelId = computed(() => `${tid.value}-paneel`)

// ADR-052 slice 4c — de gedeelde positioneer-bouwsteen: `fixed`, flipt boven/onder + klemt binnen
// beeld (geen eigen positioneringslogica; geen tweede implementatie). Zo valt het paneel — inclusief
// de norm-passage eronder — nooit buiten beeld, ook onderaan een scrollende Dialog (die klipt anders
// via `overflow-y-auto`). A11y (Escape/klik-buiten/focus-terug) blijft hieronder bij VeldUitleg.
const { stijl, open: posOpen, sluit: posSluit } = usePopoverPositie(paneel)

// Onderdruk de focus-open tijdens een programmatische focus-terugkeer (anders heropent sluit()
// het paneel meteen weer via @focus).
let onderdrukFocus = false

function openen() {
  open.value = true
  posOpen(knop.value)
}
function toggle() {
  if (open.value) sluit(false)
  else openen()
}
function onFocus() {
  if (!onderdrukFocus) openen()
}
function sluit(focusTerug = true) {
  if (!open.value) return
  open.value = false
  posSluit()
  if (focusTerug && knop.value) {
    onderdrukFocus = true
    knop.value.focus()
    onderdrukFocus = false
  }
}
function onDocKeydown(e) {
  if (open.value && e.key === 'Escape') sluit(true)
}
function onDocClick(e) {
  if (!open.value) return
  const wortel = knop.value?.parentElement
  if (wortel && !wortel.contains(e.target)) sluit(false)
}
onMounted(() => {
  document.addEventListener('keydown', onDocKeydown, true)
  document.addEventListener('click', onDocClick, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onDocKeydown, true)
  document.removeEventListener('click', onDocClick, true)
})
</script>

<template>
  <!-- Inline-modus: korte regel(s) onder het veld. -->
  <p
    v-if="inline && heeftContent"
    :data-testid="`${tid}-inline`"
    class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]"
  >
    <span v-if="info && info.uitleg">{{ info.uitleg }}</span>
    <span v-if="info && info.vuistregel" class="block">{{ info.vuistregel }}</span>
    <span
      v-if="opDeLat"
      data-norm-lat
      :data-testid="`${tid}-lat`"
      :class="['block', heeftUitlegBoven ? 'mt-[var(--lk-space-xs)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-xs)]' : '']"
    >{{ LAT_PASSAGE }}</span>
  </p>

  <!-- Popover-modus: 'i'-knop + klik/focus-open paneel. -->
  <span v-else-if="!inline && heeftContent" class="relative inline-flex">
    <button
      ref="knop"
      type="button"
      :data-testid="`${tid}-knop`"
      aria-label="Uitleg bij dit veld"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-controls="paneelId"
      class="inline-flex h-5 w-5 items-center justify-center rounded-full border border-[var(--lk-color-border)] text-[length:var(--lk-text-xs)] font-semibold text-[var(--lk-color-primary)] leading-none focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
      @mousedown.prevent
      @click="toggle"
      @focus="onFocus"
    >i</button>

    <div
      v-show="open"
      ref="paneel"
      :id="paneelId"
      role="region"
      aria-label="Uitleg bij dit veld"
      :data-testid="`${tid}-paneel`"
      :style="stijl"
      class="z-30 w-72 max-w-[80vw] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-sm)] shadow-[var(--lk-shadow-md)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text)]"
    >
      <p v-if="info && info.uitleg">{{ info.uitleg }}</p>
      <p v-if="info && info.vuistregel" class="mt-[var(--lk-space-xs)] text-[var(--lk-color-text-muted)]">
        {{ info.vuistregel }}
      </p>
      <dl v-if="optieLijst.length" class="mt-[var(--lk-space-sm)] flex flex-col gap-[var(--lk-space-xs)]">
        <div v-for="o in optieLijst" :key="o.key" :data-testid="`${tid}-optie-${o.key}`">
          <dt class="font-semibold">{{ o.label }}</dt>
          <dd class="text-[var(--lk-color-text-muted)]">{{ o.uitleg }}</dd>
        </div>
      </dl>
      <!-- Slice 4c — de norm-passage onder een scheidingslijn (besluit 17: boven = veld, onder = lat). -->
      <p
        v-if="opDeLat"
        data-norm-lat
        :data-testid="`${tid}-lat`"
        :class="['text-[var(--lk-color-text-muted)]', heeftUitlegBoven ? 'mt-[var(--lk-space-sm)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)]' : '']"
      >{{ LAT_PASSAGE }}</p>
    </div>
  </span>
</template>
