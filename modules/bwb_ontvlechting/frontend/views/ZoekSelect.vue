<script setup>
/**
 * ZoekSelect — generieke, toegankelijke server-side zoek-combobox (CD049).
 *
 * Voor entiteit-keuzevelden die onbegrensd groeien (leverancier, contract, applicatie).
 * Tekstinvoer → gedebouncede server-zoek via `zoekFunctie({ zoek, limit, ...extraFilters })`
 * (de bestaande api.js-lijstmethodes, met CD017-`zoek`-escaping server-side). Toont de eerste
 * ~10 resultaten; bij méér een "verfijn"-regel. Leeg veld → eerste pagina als startlijst, dus
 * kleine datasets gedragen zich als een gewone dropdown.
 *
 * A11y: combobox-patroon (role=combobox, aria-expanded/controls/activedescendant; ↑/↓/Enter/
 * Escape). Werkt binnen een Dialog-focustrap. Foutstaat via aria-invalid/aria-describedby.
 *
 * LI038 gate 1 v2 — een gekozen waarde is een LABEL, nooit een zoekfilter: openen (focus ÉN
 * klik-op-al-gefocust-veld) toont altijd de volledige startlijst met de tekst geselecteerd
 * (eerste aanslag vervangt), en het ×-wis-gebaar maakt "ik wil een ander item" één handeling.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const VENSTER = 10 // toon maximaal 10; vraag er 11 op om "meer" te detecteren

const props = defineProps({
  zoekFunctie: { type: Function, required: true },
  modelValue: { type: [String, Number, null], default: null },
  // (item) => weergavetekst. Default: item.naam.
  weergave: { type: Function, default: (item) => item?.naam ?? '' },
  idVeld: { type: String, default: 'id' },
  // Label voor de reeds-geselecteerde waarde (bewerken-modus; item nog niet geladen).
  initieelWeergave: { type: String, default: '' },
  placeholder: { type: String, default: 'Zoeken…' },
  disabled: { type: Boolean, default: false },
  extraFilters: { type: Object, default: () => ({}) },
  invalid: { type: Boolean, default: false },
  ariaDescribedby: { type: String, default: null },
  id: { type: String, default: null },
  // data-testid-prefix (uniek per instantie wanneer meerdere ZoekSelects in één form staan).
  testid: { type: String, default: 'zs' },
  // Multi-select-modus (ZoekMultiSelect): na een keuze het veld leegmaken en open houden i.p.v.
  // sluiten, zodat snel meerdere keuzes achter elkaar kunnen. Sluiten gebeurt dan via blur/Escape.
  heropenNaKeuze: { type: Boolean, default: false },
  // Vaste optie onderaan de dropdown (gescheiden van de zoekresultaten met een lijn). Een item
  // zoals { [idVeld]: '…', <weergaveveld>: '…' }; selecteert net als een gewoon resultaat.
  vasteOptie: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'keuze'])

const inputRef = ref(null)
const query = ref('')
const gekozenLabel = ref('')

// Voor Dialog-autofocus (secties openen een ZoekSelect als eerste veld).
defineExpose({ focus: () => inputRef.value?.focus() })
const open = ref(false)
const resultaten = ref([])
const meer = ref(false)
const laden = ref(false)
const fout = ref(null)
const actieveIndex = ref(-1)
const listboxId = computed(() => `${props.id || 'zs'}-listbox`)
const optieId = (i) => `${props.id || 'zs'}-optie-${i}`
// Navigeerbare items = zoekresultaten + (optioneel) de vaste onderste optie.
const navItems = computed(() => (props.vasteOptie ? [...resultaten.value, props.vasteOptie] : resultaten.value))

function _label(item) {
  return props.weergave(item)
}

async function zoek(term) {
  laden.value = true
  fout.value = null
  try {
    // `term` expliciet meegegeven (bv. '' bij openen → volledige startlijst); anders de getypte query.
    const zoekterm = (term ?? query.value).trim() || undefined
    const params = { zoek: zoekterm, limit: VENSTER + 1, ...props.extraFilters }
    const pagina = await props.zoekFunctie(params)
    const items = Array.isArray(pagina) ? pagina : pagina?.items ?? []
    meer.value = items.length > VENSTER
    resultaten.value = items.slice(0, VENSTER)
    actieveIndex.value = resultaten.value.length ? 0 : -1
  } catch (e) {
    // Nooit de rauwe foutcode tonen. Bij een verlopen sessie (401) leidt de centrale vangrail
    // (api.js) al naar login → geen melding hier; overige fouten krijgen een generieke tekst.
    fout.value = e?.status === 401 ? '' : 'Zoeken mislukt.'
    resultaten.value = []
    meer.value = false
  } finally {
    laden.value = false
  }
}

let _timer = null
function zoekDebounced() {
  clearTimeout(_timer)
  _timer = setTimeout(zoek, 300)
}
onBeforeUnmount(() => clearTimeout(_timer))

function openen() {
  if (props.disabled) return
  open.value = true
  // Bij openen ALTIJD de volledige (scope-)startlijst tonen — nooit filteren op een voorgevulde
  // waarde (LI032). De input-tekst selecteren zodat de eerste toetsaanslag de prefill vervangt.
  inputRef.value?.select?.()
  zoek('') // expliciet lege term → startlijst, ook als er een label voorgevuld is
}

function _herstelWeergave() {
  // Half-getypte zoekterm zonder selectie → terug naar de gekozen waarde.
  query.value = gekozenLabel.value
}

function sluiten() {
  open.value = false
  _herstelWeergave()
}

function selecteer(item) {
  emit('update:modelValue', item[props.idVeld])
  emit('keuze', item)
  if (props.heropenNaKeuze) {
    // Multi-select: veld leegmaken en lijst open houden voor de volgende keuze.
    gekozenLabel.value = ''
    query.value = ''
    actieveIndex.value = -1
    zoek()
  } else {
    gekozenLabel.value = _label(item)
    query.value = gekozenLabel.value
    open.value = false
  }
}

function onInput() {
  open.value = true
  zoekDebounced()
}

// LI038 gate 1 v2 — een klik op het veld opent de volledige startlijst óók als het veld al
// focus had (direct ná een keuze houdt de input focus door de mousedown.prevent op de optie;
// het @focus-pad vuurt dan niet en typen zou aan de gekozen naam plakken → filter-slot).
// Guard op `open`: een klik om de cursor te verplaatsen tijdens het typen reset niets.
function onClick() {
  if (!open.value) openen()
}

// LI038 gate 1 v2 — zichtbaar "opnieuw zoeken"-gebaar: wis de keuze/zoekterm en toon de
// volledige startlijst. Geërfd door élk (voorgevuld) picker-veld. De consument hoort de wis
// via `update:modelValue(null)`; wie alleen op @keuze luistert (bv. het proces-diagram)
// behoudt zijn huidige beeld tot een nieuwe keuze — precies de bedoeling.
function wis() {
  gekozenLabel.value = ''
  query.value = ''
  emit('update:modelValue', null)
  inputRef.value?.focus()
  if (!open.value) openen()
}

function onBlur() {
  // Sta toe dat een klik op een optie eerst afhandelt.
  setTimeout(() => {
    if (open.value) sluiten()
  }, 150)
}

function onKeydown(e) {
  if (['ArrowDown', 'ArrowUp'].includes(e.key) && !open.value) {
    openen()
    e.preventDefault()
    return
  }
  if (e.key === 'ArrowDown') {
    actieveIndex.value = Math.min(actieveIndex.value + 1, navItems.value.length - 1)
    e.preventDefault()
  } else if (e.key === 'ArrowUp') {
    actieveIndex.value = Math.max(actieveIndex.value - 1, 0)
    e.preventDefault()
  } else if (e.key === 'Enter') {
    if (open.value && actieveIndex.value >= 0 && navItems.value[actieveIndex.value]) {
      selecteer(navItems.value[actieveIndex.value])
      e.preventDefault()
    }
  } else if (e.key === 'Escape') {
    if (open.value) {
      sluiten()
      e.preventDefault()
    }
  }
}

// Bewerken-modus / externe reset: spiegel modelValue → weergave.
watch(
  () => props.modelValue,
  (v) => {
    if (v == null || v === '') {
      gekozenLabel.value = ''
      query.value = ''
    } else if (!gekozenLabel.value) {
      gekozenLabel.value = props.initieelWeergave
      query.value = props.initieelWeergave
    }
  },
  { immediate: true },
)
// Initieel label kan ná modelValue binnenkomen (async laden in bewerken-modus).
watch(
  () => props.initieelWeergave,
  (label) => {
    if (label && props.modelValue != null && !gekozenLabel.value) {
      gekozenLabel.value = label
      query.value = label
    }
  },
)
</script>

<template>
  <div class="relative">
    <input
      :id="props.id"
      ref="inputRef"
      v-model="query"
      type="text"
      role="combobox"
      autocomplete="off"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-controls="listboxId"
      :aria-activedescendant="open && actieveIndex >= 0 ? optieId(actieveIndex) : null"
      :aria-invalid="props.invalid || undefined"
      :aria-describedby="props.ariaDescribedby || undefined"
      :placeholder="props.placeholder"
      :disabled="props.disabled"
      :data-testid="`${props.testid}-input`"
      class="w-full rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] pr-7 bg-white disabled:opacity-60 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
      @focus="openen"
      @click="onClick"
      @input="onInput"
      @blur="onBlur"
      @keydown="onKeydown"
    />
    <!-- LI038 gate 1 v2 — wis-gebaar (één handeling voor "ik wil een ander item"): zichtbaar
         zodra er iets te wissen valt. mousedown.prevent houdt de focus op de input (geen
         blur-sluiting), zoals de opties hieronder. -->
    <button
      v-if="query && !props.disabled"
      type="button"
      aria-label="Wis en zoek opnieuw"
      :data-testid="`${props.testid}-wis`"
      class="absolute right-2 top-1/2 -translate-y-1/2 leading-none text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
      @mousedown.prevent
      @click="wis"
    >×</button>

    <ul
      v-show="open"
      :id="listboxId"
      role="listbox"
      :data-testid="`${props.testid}-listbox`"
      class="absolute z-10 mt-1 max-h-72 w-full overflow-auto rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] shadow-[var(--lk-shadow-md)]"
    >
      <li v-if="laden" :data-testid="`${props.testid}-laden`" class="px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">
        Laden…
      </li>
      <li v-else-if="fout" role="alert" :data-testid="`${props.testid}-fout`" class="px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">
        {{ fout }}
      </li>
      <template v-else>
        <li
          v-for="(item, i) in resultaten"
          :id="optieId(i)"
          :key="item[props.idVeld]"
          role="option"
          :aria-selected="item[props.idVeld] === props.modelValue ? 'true' : 'false'"
          :data-testid="`${props.testid}-optie-${item[props.idVeld]}`"
          :class="[
            'cursor-pointer px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]',
            i === actieveIndex ? 'bg-[var(--lk-color-accent)]' : 'hover:bg-[var(--lk-color-accent)]',
          ]"
          @mousedown.prevent="selecteer(item)"
          @mousemove="actieveIndex = i"
        >
          <!-- Optionele item-opmaak (scoped slot); default = de kale weergavetekst. -->
          <slot name="optie" :item="item" :label="_label(item)">{{ _label(item) }}</slot>
        </li>
        <li v-if="!resultaten.length" :data-testid="`${props.testid}-leeg`" class="px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">
          <!-- Lege-zoekstaat: een consument kan hier een contextuele actie renderen (bv. aanmaken op
               de zoekterm). Default = "Geen resultaten." De `query` (getrimd) is de huidige zoekterm. -->
          <slot name="leeg" :query="query.trim()">Geen resultaten.</slot>
        </li>
        <li v-if="meer" :data-testid="`${props.testid}-meer`" class="border-t border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-xs)]">
          Meer resultaten — verfijn je zoekopdracht.
        </li>
        <li
          v-if="vasteOptie"
          :id="optieId(resultaten.length)"
          role="option"
          :aria-selected="vasteOptie[props.idVeld] === props.modelValue ? 'true' : 'false'"
          :data-testid="`${props.testid}-optie-${vasteOptie[props.idVeld]}`"
          :class="[
            'cursor-pointer border-t border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)] italic',
            resultaten.length === actieveIndex ? 'bg-[var(--lk-color-accent)]' : 'hover:bg-[var(--lk-color-accent)]',
          ]"
          @mousedown.prevent="selecteer(vasteOptie)"
          @mousemove="actieveIndex = resultaten.length"
        >
          {{ _label(vasteOptie) }}
        </li>
      </template>
    </ul>
  </div>
</template>
