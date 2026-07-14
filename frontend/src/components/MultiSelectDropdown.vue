<script setup>
/**
 * MultiSelectDropdown — generieke, toegankelijke checkbox-dropdown (platform-breed).
 *
 * Meervoudige selectie in dezelfde visuele stijl als de native `<select>`-dropdowns
 * (Type/Laag/Hosting): een trigger die de selectiestand toont en een paneel met
 * checkboxes opent. `v-model` is een **array** (plugt 1-op-1 op een bestaand array-filter).
 *
 * A11y: trigger = button met `aria-haspopup`/`aria-expanded`/`aria-controls`; opties als
 * echte checkboxes met zichtbare labels (kleur nooit de enige drager). Sluit op Escape
 * (focus terug naar trigger) en op buiten-klik. Labels via een `weergave`-functie zodat de
 * bestaande label-bron hergebruikt wordt (geen hardcoded labels).
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  opties: { type: Array, default: () => [] }, // waarden (strings); label via `weergave`
  weergave: { type: Function, default: (v) => String(v) },
  placeholder: { type: String, default: 'Alle' },
  ariaLabel: { type: String, default: null },
  id: { type: String, default: null },
  testid: { type: String, default: 'msd' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const root = ref(null)
const triggerRef = ref(null)
const panelId = computed(() => `${props.id || props.testid}-panel`)

const samenvatting = computed(() => {
  const n = props.modelValue.length
  if (n === 0) return props.placeholder
  if (n === 1) return props.weergave(props.modelValue[0])
  return `${n} geselecteerd`
})

function isGekozen(waarde) {
  return props.modelValue.includes(waarde)
}

function toggle(waarde) {
  const nieuw = isGekozen(waarde)
    ? props.modelValue.filter((v) => v !== waarde)
    : [...props.modelValue, waarde]
  emit('update:modelValue', nieuw)
  emit('change', nieuw)
}

function openen() {
  if (props.disabled) return
  open.value = true
}
function sluiten({ focusTrigger = false } = {}) {
  open.value = false
  if (focusTrigger) triggerRef.value?.focus?.()
}
function toggleOpen() {
  open.value ? sluiten() : openen()
}

function onTriggerKeydown(e) {
  if (e.key === 'Escape' && open.value) {
    sluiten({ focusTrigger: true })
    e.preventDefault()
  } else if ((e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') && !open.value) {
    openen()
    e.preventDefault()
  }
}

function onPanelKeydown(e) {
  if (e.key === 'Escape') {
    sluiten({ focusTrigger: true })
    e.preventDefault()
  }
}

// Buiten-klik sluit (document-listener alleen actief zolang open).
function onDocMousedown(e) {
  if (root.value && !root.value.contains(e.target)) sluiten()
}
watch(open, (isOpen) => {
  if (isOpen) document.addEventListener('mousedown', onDocMousedown)
  else document.removeEventListener('mousedown', onDocMousedown)
})
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocMousedown))
</script>

<template>
  <div ref="root" class="relative inline-block">
    <button
      ref="triggerRef"
      type="button"
      :data-testid="`${testid}-trigger`"
      :aria-label="ariaLabel"
      :aria-haspopup="true"
      :aria-expanded="open"
      :aria-controls="panelId"
      :disabled="disabled"
      class="lk-veld flex min-w-[10rem] items-center justify-between gap-[var(--lk-space-sm)] text-left"
      @click="toggleOpen"
      @keydown="onTriggerKeydown"
    >
      <span :class="modelValue.length ? '' : 'text-[var(--lk-color-text-muted)]'">{{ samenvatting }}</span>
      <span aria-hidden="true" class="text-[var(--lk-color-text-muted)]">▾</span>
    </button>

    <div
      v-if="open"
      :id="panelId"
      :data-testid="`${testid}-panel`"
      role="group"
      :aria-label="ariaLabel"
      class="absolute z-10 mt-1 min-w-full rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-sm)] shadow-[var(--lk-shadow-md)]"
      @keydown="onPanelKeydown"
    >
      <label
        v-for="o in opties"
        :key="o"
        :data-testid="`${testid}-optie-${o}`"
        class="flex items-center gap-[var(--lk-space-xs)] whitespace-nowrap rounded-[var(--lk-radius-nav)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)]"
      >
        <input
          type="checkbox"
          :data-testid="`${testid}-checkbox-${o}`"
          :value="o"
          :checked="isGekozen(o)"
          @change="toggle(o)"
        />
        {{ weergave(o) }}
      </label>
    </div>
  </div>
</template>
