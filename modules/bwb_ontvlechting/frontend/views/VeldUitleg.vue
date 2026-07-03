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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { optieUitlegLijst, veldUitleg } from '../velduitleg'

const props = defineProps({
  veld: { type: String, required: true },
  // Set-naam voor OPTIE_UITLEG (per-optie regels in de popover); leeg = geen optie-uitleg.
  opties: { type: String, default: null },
  // Inline-modus: korte regel onder het veld i.p.v. popover.
  inline: { type: Boolean, default: false },
  testid: { type: String, default: null },
})

const tid = computed(() => props.testid || `uitleg-${props.veld}`)
const info = computed(() => veldUitleg(props.veld)) // { uitleg, vuistregel } | null
const optieLijst = computed(() => (props.opties ? optieUitlegLijst(props.opties) : []))
const heeftContent = computed(() => !!info.value || optieLijst.value.length > 0)

const open = ref(false)
const knop = ref(null)
const paneelId = computed(() => `${tid.value}-paneel`)

// Onderdruk de focus-open tijdens een programmatische focus-terugkeer (anders heropent sluit()
// het paneel meteen weer via @focus).
let onderdrukFocus = false

function toggle() {
  open.value = !open.value
}
function onFocus() {
  if (!onderdrukFocus) open.value = true
}
function sluit(focusTerug = true) {
  if (!open.value) return
  open.value = false
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
      :id="paneelId"
      role="region"
      aria-label="Uitleg bij dit veld"
      :data-testid="`${tid}-paneel`"
      class="absolute left-0 top-6 z-20 w-72 max-w-[80vw] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-sm)] shadow-[var(--lk-shadow-md)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text)]"
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
    </div>
  </span>
</template>
