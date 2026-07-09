/** Tests — OnderliggendeProcessenSectie (ADR-042 slice 5, samengevoegd blok):
 *  groepering per deelproces, kopje-doorklik, pad-bijschrift alleen bij diepere lagen,
 *  open-tenzij-groot, lege staten, read-only, toevoegknop in de blokkop. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: { processen: { rollup: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import OnderliggendeProcessenSectie from '@modules/bwb_ontvlechting/frontend/views/OnderliggendeProcessenSectie.vue'

const _KINDEREN = [
  { id: 'ab', naam: 'Aanvraag behandelen', toelichting: 'Werkproces.' },
  { id: 'tz', naam: 'Toezicht', toelichting: null },
]

const _regel = (id, comp, herkomstId, herkomstNaam, pad, takId, functie = 'Registreren') => ({
  vervulling_id: id,
  applicatiefunctie: functie.toLowerCase(),
  applicatiefunctie_label: functie,
  toelichting: null,
  component_id: `c-${comp}`,
  component_naam: comp,
  componenttype: 'applicatie',
  componenttype_label: 'Applicatie',
  proces_id: herkomstId,
  proces_naam: herkomstNaam,
  proces_pad: pad,
  tak_id: takId,
})

// Direct op deelproces ab + één laag dieper (bv onder ab); tak = ab voor beide.
const _REGELS = [
  _regel('r1', 'Zaaksysteem', 'ab', 'Aanvraag behandelen', ['Aanvraag behandelen'], 'ab'),
  _regel('r2', 'DMS', 'bv', 'Besluit vastleggen', ['Aanvraag behandelen', 'Besluit vastleggen'], 'ab', 'Archiveren'),
]

// 12 doorgerolde regels (12 unieke componenten) via 2 takken.
const _VEEL = Array.from({ length: 12 }, (_, i) => {
  const tak = _KINDEREN[i % 2]
  return _regel(`r${i}`, `Component-${String(i).padStart(2, '0')}`, tak.id, tak.naam, [tak.naam], tak.id)
})

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div/>' } },
      { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountSectie({ procesId = 'p1', kinderen = _KINDEREN, rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(OnderliggendeProcessenSectie, {
    props: { procesId, kinderen },
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  api.processen.rollup.mockResolvedValue([])
})
afterEach(() => vi.restoreAllMocks())

describe('OnderliggendeProcessenSectie — groepering per deelproces', () => {
  it('per direct deelproces een klikbaar kopje met toelichting; de regels gegroepeerd eronder', async () => {
    api.processen.rollup.mockResolvedValue(_REGELS)
    const w = await mountSectie()
    // Kopjes: beide deelprocessen, klikbaar, met toelichting.
    const groepAb = w.find('[data-testid="groep-ab"]')
    expect(groepAb.find('[data-testid="deelproces-link"]').attributes('href')).toContain('/processen/ab')
    expect(groepAb.text()).toContain('Werkproces.')
    // De regels van tak ab staan onder het ab-kopje.
    const regels = groepAb.find('[data-testid="groep-regels-ab"]')
    expect(regels.exists()).toBe(true)
    expect(regels.findAll('[data-testid^="rollup-regel-"]')).toHaveLength(2)
    // Een deelproces zonder eigen regels toont zijn kopje + rustige lege regel.
    const groepTz = w.find('[data-testid="groep-tz"]')
    expect(groepTz.find('[data-testid="deelproces-link"]').attributes('href')).toContain('/processen/tz')
    expect(groepTz.find('[data-testid="groep-leeg-tz"]').text()).toContain('Nog geen componenten')
  })

  it('pad-bijschrift alléén bij diepere lagen (de groepering ís de herkomst), klikbaar naar de herkomst', async () => {
    api.processen.rollup.mockResolvedValue(_REGELS)
    const w = await mountSectie()
    // r1 is direct op het deelproces zelf → géén bijschrift.
    expect(w.find('[data-testid="rollup-regel-r1"]').find('[data-testid="rollup-herkomst"]').exists()).toBe(false)
    // r2 komt een laag dieper → pad-bijschrift vanaf het deelproces, klikbaar.
    const herkomst = w.find('[data-testid="rollup-regel-r2"]').find('[data-testid="rollup-herkomst"]')
    expect(herkomst.text()).toContain('via › Besluit vastleggen')
    expect(herkomst.find('[data-testid="rollup-herkomst-link"]').attributes('href')).toContain('/processen/bv')
    // Het component zelf is klikbaar.
    expect(w.find('[data-testid="rollup-component-link"]').attributes('href')).toContain('/componenten/c-Zaaksysteem')
  })
})

describe('OnderliggendeProcessenSectie — open-tenzij-groot', () => {
  it('t/m de drempel direct open; boven de drempel gevouwen tot de telling, kopjes blijven staan', async () => {
    api.processen.rollup.mockResolvedValue(_VEEL)
    const w = await mountSectie()
    const wissel = w.find('[data-testid="rollup-wissel"]')
    expect(wissel.attributes('aria-expanded')).toBe('false')
    expect(wissel.text()).toContain('Nog 12 component(en) via 2 deelproces(sen)')
    // De kopjes (navigatie) blijven zichtbaar, de regels niet.
    expect(w.findAll('[data-testid="deelproces-link"]').length).toBe(2)
    expect(w.findAll('[data-testid^="rollup-regel-"]')).toHaveLength(0)
    await wissel.trigger('click')
    expect(w.find('[data-testid="rollup-wissel"]').attributes('aria-expanded')).toBe('true')
    expect(w.findAll('[data-testid^="rollup-regel-"]')).toHaveLength(12)
  })

  it('de telling telt componenten en herkomst-processen uniek (niet de regels)', async () => {
    // 11 regels, 6 unieke componenten via 2 herkomst-processen (meerdere functies per component).
    const regels = Array.from({ length: 11 }, (_, i) => {
      const tak = _KINDEREN[i % 2]
      return _regel(`r${i}`, `Comp-${i % 6}`, tak.id, tak.naam, [tak.naam], tak.id, i % 2 ? 'Raadplegen' : 'Registreren')
    })
    api.processen.rollup.mockResolvedValue(regels)
    const w = await mountSectie()
    expect(w.find('[data-testid="rollup-wissel"]').text()).toContain('Nog 6 component(en) via 2 deelproces(sen)')
  })

  it('onthoudt de uitklapstand via het lijststaat-patroon (bewaarde stand wint van de default)', async () => {
    sessionStorage.setItem('lijst-state:proces-onderliggend:p1', JSON.stringify({ open: false }))
    api.processen.rollup.mockResolvedValue(_REGELS)
    const w = await mountSectie()
    // 2 regels ⇒ default open, maar de bewaarde dichte stand wint.
    expect(w.findAll('[data-testid^="rollup-regel-"]')).toHaveLength(0)
    expect(w.find('[data-testid="rollup-wissel"]').attributes('aria-expanded')).toBe('false')
  })
})

describe('OnderliggendeProcessenSectie — acties + randen', () => {
  it('"+ Deelproces toevoegen" staat in de blokkop en meldt zich bij de ouder (dialog daar)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="deelproces-toevoegen"]').trigger('click')
    expect(w.emitted('toevoegen')).toHaveLength(1)
  })

  it('zonder schrijfrol geen toevoegknop (affordance; backend handhaaft)', async () => {
    const w = await mountSectie({ rollen: ['lezer'] })
    expect(w.find('[data-testid="deelproces-toevoegen"]').exists()).toBe(false)
  })

  it('doorgerolde regels hebben GEEN regel-acties (bewerken/verwijderen woont op de herkomst)', async () => {
    api.processen.rollup.mockResolvedValue(_REGELS)
    const w = await mountSectie()
    const sectie = w.find('[data-testid="onderliggend-sectie"]')
    expect(sectie.text()).not.toContain('Bewerken')
    expect(sectie.text()).not.toContain('Verwijderen')
  })

  it('lege staat zonder deelprocessen: rustige tekst, geen rollup-fetch, knop blijft', async () => {
    const w = await mountSectie({ kinderen: [] })
    expect(w.find('[data-testid="deelprocessen-leeg"]').text()).toContain('Nog geen deelprocessen')
    expect(w.find('[data-testid="deelproces-toevoegen"]').exists()).toBe(true)
    expect(api.processen.rollup).not.toHaveBeenCalled()
    expect(w.find('[data-testid="rollup-wissel"]').exists()).toBe(false)
  })

  it('deelprocessen zonder doorgerolde regels: kopjes zichtbaar, geen telling-regel', async () => {
    api.processen.rollup.mockResolvedValue([])
    const w = await mountSectie()
    expect(w.findAll('[data-testid="deelproces-link"]').length).toBe(2)
    expect(w.find('[data-testid="rollup-wissel"]').exists()).toBe(false)
    expect(w.find('[data-testid="groep-leeg-ab"]').exists()).toBe(true)
  })

  it('fout bij laden toont een MeldingBanner (geen stil falen)', async () => {
    api.processen.rollup.mockRejectedValue({ status: 500 })
    const w = await mountSectie()
    expect(w.find('[data-testid="rollup-fout"]').text()).toContain('mislukt')
  })
})
