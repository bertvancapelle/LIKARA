/**
 * Tests — MultiSelectDropdown (generieke checkbox-dropdown).
 * Open/sluit, selecteren/deselecteren wijzigt de v-model-array, selectiestand in de
 * trigger, Escape + buiten-klik sluiten, weergave-functie voor labels.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'

import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue'

const OPTIES = ['concept', 'in_inventarisatie', 'geblokkeerd', 'migratieklaar']
const LABEL = { geblokkeerd: 'Geblokkeerd', concept: 'Concept' }

function maak({ modelValue = [] } = {}) {
  return mount(MultiSelectDropdown, {
    props: {
      modelValue,
      opties: OPTIES,
      weergave: (v) => LABEL[v] || v,
      placeholder: 'Alle',
      testid: 'ms',
    },
    attachTo: document.body,
  })
}

afterEach(() => vi.restoreAllMocks())

describe('MultiSelectDropdown', () => {
  it('toont de placeholder als niets is gekozen en opent op klik', async () => {
    const w = maak()
    expect(w.find('[data-testid="ms-trigger"]').text()).toContain('Alle')
    expect(w.find('[data-testid="ms-panel"]').exists()).toBe(false)
    await w.find('[data-testid="ms-trigger"]').trigger('click')
    expect(w.find('[data-testid="ms-panel"]').exists()).toBe(true)
    // één optie per waarde
    expect(w.findAll('[data-testid^="ms-checkbox-"]').length).toBe(OPTIES.length)
  })

  it('selecteren en deselecteren wijzigt de v-model-array', async () => {
    const w = maak()
    await w.find('[data-testid="ms-trigger"]').trigger('click')
    await w.find('[data-testid="ms-checkbox-geblokkeerd"]').trigger('change')
    expect(w.emitted('update:modelValue').at(-1)[0]).toEqual(['geblokkeerd'])
    expect(w.emitted('change')).toBeTruthy()

    // Met die waarde al gekozen: opnieuw togglen verwijdert hem.
    const w2 = maak({ modelValue: ['geblokkeerd'] })
    await w2.find('[data-testid="ms-trigger"]').trigger('click')
    await w2.find('[data-testid="ms-checkbox-geblokkeerd"]').trigger('change')
    expect(w2.emitted('update:modelValue').at(-1)[0]).toEqual([])
  })

  it('toont de selectiestand in de trigger (1 = label, >1 = "n geselecteerd")', () => {
    expect(maak({ modelValue: ['geblokkeerd'] }).find('[data-testid="ms-trigger"]').text()).toContain('Geblokkeerd')
    expect(maak({ modelValue: ['geblokkeerd', 'concept'] }).find('[data-testid="ms-trigger"]').text()).toContain('2 geselecteerd')
  })

  it('sluit op Escape (vanuit het paneel) en op buiten-klik', async () => {
    const w = maak()
    await w.find('[data-testid="ms-trigger"]').trigger('click')
    expect(w.find('[data-testid="ms-panel"]').exists()).toBe(true)
    await w.find('[data-testid="ms-panel"]').trigger('keydown', { key: 'Escape' })
    expect(w.find('[data-testid="ms-panel"]').exists()).toBe(false)

    // Buiten-klik: open opnieuw, dan een mousedown buiten de root.
    await w.find('[data-testid="ms-trigger"]').trigger('click')
    expect(w.find('[data-testid="ms-panel"]').exists()).toBe(true)
    document.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    await w.vm.$nextTick()
    expect(w.find('[data-testid="ms-panel"]').exists()).toBe(false)
  })
})
