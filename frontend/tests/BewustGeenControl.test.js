/** Tests — BewustGeenControl (ADR-052 slice 2): "vastgesteld: geen koppelingen/contract". */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { componentBevindingen: { lijst: vi.fn(), maak: vi.fn(), verwijder: vi.fn() } },
}))
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
import BewustGeenControl from '@modules/bwb_ontvlechting/frontend/views/BewustGeenControl.vue'

async function mountCtl(props = {}) {
  const w = mount(BewustGeenControl, {
    props: {
      componentId: 'c-1', soort: 'koppelingen', onderwerp: 'koppelingen',
      heeftEcht: false, mag: true, ...props,
    },
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService] },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.componentBevindingen.lijst.mockResolvedValue([])
})
afterEach(() => vi.restoreAllMocks())

describe('BewustGeenControl (ADR-052 slice 2)', () => {
  it('geen registratie + geen bevinding → "nog niet vastgesteld" + zet-knop (medewerker)', async () => {
    const w = await mountCtl()
    expect(w.find('[data-testid="bewustgeen-open-koppelingen"]').exists()).toBe(true)
    expect(w.find('[data-testid="bewustgeen-vastgesteld-koppelingen"]').exists()).toBe(false)
    expect(w.find('[data-testid="bewustgeen-zet-koppelingen"]').exists()).toBe(true)
  })

  it('bestaande bevinding → "vastgesteld: geen" + intrek-knop (onderscheid zichtbaar)', async () => {
    api.componentBevindingen.lijst.mockResolvedValue([{ soort: 'koppelingen' }])
    const w = await mountCtl()
    expect(w.find('[data-testid="bewustgeen-vastgesteld-koppelingen"]').text()).toContain('geen koppelingen')
    expect(w.find('[data-testid="bewustgeen-intrek-koppelingen"]').exists()).toBe(true)
    expect(w.find('[data-testid="bewustgeen-open-koppelingen"]').exists()).toBe(false)
  })

  it('zetten roept de api aan (component + soort) en toont daarna "vastgesteld"', async () => {
    api.componentBevindingen.maak.mockResolvedValue({})
    const w = await mountCtl()
    await w.find('[data-testid="bewustgeen-zet-koppelingen"]').trigger('click')
    await flushPromises()
    expect(api.componentBevindingen.maak).toHaveBeenCalledWith('c-1', { soort: 'koppelingen' })
    expect(toastSucces).toHaveBeenCalled()
    expect(w.find('[data-testid="bewustgeen-vastgesteld-koppelingen"]').exists()).toBe(true)
  })

  it('intrekken roept de api aan met component + soort', async () => {
    api.componentBevindingen.lijst.mockResolvedValue([{ soort: 'contract' }])
    api.componentBevindingen.verwijder.mockResolvedValue(null)
    const w = await mountCtl({ soort: 'contract', onderwerp: 'contract' })
    await w.find('[data-testid="bewustgeen-intrek-contract"]').trigger('click')
    await flushPromises()
    expect(api.componentBevindingen.verwijder).toHaveBeenCalledWith('c-1', 'contract')
  })

  it('real wins: bij een echte registratie toont de control niets (geen tegenspraak)', async () => {
    const w = await mountCtl({ heeftEcht: true })
    expect(w.find('[data-testid="bewustgeen-koppelingen"]').exists()).toBe(false)
  })

  it('viewer (mag=false) ziet de tekst maar geen knoppen', async () => {
    const w = await mountCtl({ mag: false })
    expect(w.find('[data-testid="bewustgeen-open-koppelingen"]').exists()).toBe(true)
    expect(w.find('[data-testid="bewustgeen-zet-koppelingen"]').exists()).toBe(false)
  })
})
