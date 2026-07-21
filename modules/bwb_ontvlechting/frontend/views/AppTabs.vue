<script setup>
/**
 * AppTabs — herbruikbare, toegankelijke tablist (WAI-ARIA tabs, CD022).
 *
 * Rendert ALLEEN de tablist (de `role="tab"`-knoppen); de ouder rendert de
 * bijbehorende `role="tabpanel"`-panelen (met `aria-labelledby` = de tab-id).
 * Gebruikt voor beide niveaus (top + categorie-sub-tabs). Automatische activatie
 * (WAI-ARIA-aanbeveling bij goedkope panelwissels — onze panelen blijven gemount):
 * pijltjes/Home/End verplaatsen focus én selectie; Enter/Space activeren de focus-tab.
 *
 * `--lk-`-tokens, geen `<style>`. id-conventie: `${idPrefix}-tab-${key}` /
 * `${idPrefix}-panel-${key}` (de ouder gebruikt dezelfde voor zijn panelen).
 *
 * VORM (LI048 snede 2): de tabvorm leeft volledig in de gedeelde klassen `.lk-tabrij`/
 * `.lk-tab` (main.css) — deze component kiest alleen de oriëntatie. Een tabblad draagt
 * dus GEEN knopvorm meer (omkadering, knopradius, `h-10`, gevulde gekozen-staat): bij
 * dertien tabbladen las die rij als dertien knoppen. De gekozen staat wordt gestyled op
 * `aria-selected`, zodat het toegankelijkheidsfeit en het zichtbare feit niet uiteen
 * kunnen lopen. Het bijbehorende werkvlak is `.lk-tabvlak` bij de ouder.
 */
const props = defineProps({
  tabs: { type: Array, required: true }, // [{ key, label }]
  modelValue: { type: [String, Number], default: null },
  ariaLabel: { type: String, required: true },
  orientation: { type: String, default: 'horizontal' }, // 'horizontal' | 'vertical'
  idPrefix: { type: String, required: true },
  /**
   * Diepte van de rij: '1' = de rij die het scherm stuurt, '2' = een sub-rij binnen een
   * gekozen groep. Niveau 2 is zichtbaar LICHTER (kleiner, geen accentbalk) — anders staan er
   * twee gelijkwaardige rijen en weet de gebruiker niet meer welke hem stuurt. Het gewicht
   * leeft in de BOUWSTEEN, niet op de aanroepplek: zo erft elke volgende sub-rij het, en ziet
   * het volgende scherm er niet weer anders uit (KERNLES LI038).
   */
  niveau: { type: String, default: '1' }, // '1' | '2'
})
const emit = defineEmits(['update:modelValue'])

function selecteer(key) {
  if (key !== props.modelValue) emit('update:modelValue', key)
}

function opToets(e, i) {
  const verticaal = props.orientation === 'vertical'
  const volgende = verticaal ? 'ArrowDown' : 'ArrowRight'
  const vorige = verticaal ? 'ArrowUp' : 'ArrowLeft'
  let doel = null
  if (e.key === volgende) doel = (i + 1) % props.tabs.length
  else if (e.key === vorige) doel = (i - 1 + props.tabs.length) % props.tabs.length
  else if (e.key === 'Home') doel = 0
  else if (e.key === 'End') doel = props.tabs.length - 1
  else if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    selecteer(props.tabs[i].key)
    return
  } else return
  e.preventDefault()
  const sleutel = props.tabs[doel].key
  selecteer(sleutel) // automatische activatie
  // focus verspringt naar de zojuist geactiveerde tab
  e.currentTarget.parentElement
    ?.querySelector(`[data-testid="${props.idPrefix}-tab-${sleutel}"]`)
    ?.focus?.()
}
</script>

<template>
  <div
    role="tablist"
    :aria-label="ariaLabel"
    :aria-orientation="orientation"
    :class="[
      'lk-tabrij',
      orientation === 'vertical' ? 'lk-tabrij-v' : 'lk-tabrij-h',
      niveau === '2' ? 'lk-tabrij-sub' : '',
    ]"
  >
    <button
      v-for="(t, i) in tabs"
      :id="`${idPrefix}-tab-${t.key}`"
      :key="t.key"
      type="button"
      role="tab"
      :aria-selected="t.key === modelValue"
      :aria-controls="`${idPrefix}-panel-${t.key}`"
      :tabindex="t.key === modelValue ? 0 : -1"
      :data-testid="`${idPrefix}-tab-${t.key}`"
      class="lk-tab"
      @click="selecteer(t.key)"
      @keydown="opToets($event, i)"
    >
      {{ t.label }}
    </button>
  </div>
</template>
