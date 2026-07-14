/** Tests — ComponentConfigBeheer (platform-beheer componentcatalogus, ADR-021 fase C). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    platformComponentconfig: {
      lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), typeringOpties: vi.fn(),
    },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ComponentConfigBeheer from '@/views/ComponentConfigBeheer.vue'

const _opties = () => [
  { id: 1, dimensie: 'componenttype', optie_sleutel: 'applicatie', label: 'Applicatie', volgorde: 0, actief: true, archimate_element: 'application_component', archimate_laag: 'application', archimate_aspect: 'active', checklist_dragend: true, ondersteunt_werk: true },
  { id: 2, dimensie: 'componenttype', optie_sleutel: 'database', label: 'Database', volgorde: 1, actief: true, archimate_element: 'system_software', archimate_laag: 'technology', archimate_aspect: 'active', checklist_dragend: false, ondersteunt_werk: false },
  { id: 3, dimensie: 'componenttype', optie_sleutel: 'oud', label: 'Oud', volgorde: 2, actief: false, archimate_element: 'node', archimate_laag: 'technology', archimate_aspect: 'active', checklist_dragend: false },
  { id: 4, dimensie: 'structuurrelatie_type', optie_sleutel: 'draait_op', label: 'Draait op', volgorde: 0, actief: true },
  // ADR-027 Deel 4 — archimate_relatie-rijen met (code-eigen) kenmerk_definitie voor de read-only viewer.
  { id: 5, dimensie: 'archimate_relatie', optie_sleutel: 'flow', label: 'Flow', volgorde: 4, actief: true, kenmerk_definitie: { protocol: { type: 'enum', enum: 'koppelprotocol' }, richting: { type: 'enum', enum: 'koppelrichting' } } },
  { id: 6, dimensie: 'archimate_relatie', optie_sleutel: 'composition', label: 'Composition', volgorde: 0, actief: true, kenmerk_definitie: {} },
]

const _typering = () => ({
  elementen: ['application_component', 'system_software', 'node'],
  lagen: ['application', 'technology', 'business'],
  aspecten: ['active', 'passive', 'behavior'],
})

async function mountBeheer({ rollen = ['platformbeheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'b@platform.nl', roles: rollen }
  auth.sessionType = 'platform'
  const w = mount(ComponentConfigBeheer, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformComponentconfig.lijst.mockResolvedValue(_opties())
  api.platformComponentconfig.typeringOpties.mockResolvedValue(_typering())
})
afterEach(() => vi.restoreAllMocks())

describe('ComponentConfigBeheer — render', () => {
  it('toont twee dimensies; gedeactiveerde rij onderscheiden', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="cat-sectie-componenttype"]').exists()).toBe(true)
    expect(w.find('[data-testid="cat-sectie-structuurrelatie_type"]').exists()).toBe(true)
    expect(w.text()).toContain('Database')
    expect(w.find('[data-testid="cat-rij-3"]').classes()).toContain('opacity-50')
    expect(w.find('[data-testid="cat-status-3"]').text()).toContain('Gedeactiveerd')
  })

  it('systeem-sleutel applicatie: Systeem-Tag, geen deactiveer-toggle', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="cat-systeem-1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cat-deactiveer-1"]').exists()).toBe(false)
    // bewerken (label/volgorde) blijft wél beschikbaar op de systeem-rij
    expect(w.find('[data-testid="cat-bewerk-1"]').exists()).toBe(true)
    // een gewoon type heeft wél een deactiveer-knop
    expect(w.find('[data-testid="cat-deactiveer-2"]').exists()).toBe(true)
  })

  it('biedt nergens een verwijder-affordance', async () => {
    const w = await mountBeheer()
    expect(w.findAll('[data-testid*="verwijder"]').length).toBe(0)
    expect(w.html()).not.toContain('Verwijderen')
    expect(api.platformComponentconfig.verwijder).toBeUndefined()
  })
})

describe('ComponentConfigBeheer — flows', () => {
  it('toevoegen: sleutel-patroonvalidatie + 409 in-form', async () => {
    const w = await mountBeheer()
    await w.find('[data-testid="cat-toevoegen-componenttype"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="cat-add-sleutel"]').setValue('ETL Tool')
    await w.find('[data-testid="cat-add-label"]').setValue('ETL-tool')
    await w.find('[data-testid="cat-add-form"]').trigger('submit')
    expect(w.find('[data-testid="cat-add-fout-optie_sleutel"]').exists()).toBe(true)
    expect(api.platformComponentconfig.maak).not.toHaveBeenCalled()

    api.platformComponentconfig.maak.mockRejectedValueOnce({ status: 409, code: 'CONFIGURATIE_CONFLICT', message: 'bestaat al' })
    await w.find('[data-testid="cat-add-sleutel"]').setValue('etl_tool')
    // ADR-026: componenttype vereist een volledige typering vóór submit.
    await w.find('[data-testid="cat-add-element"]').setValue('system_software')
    await w.find('[data-testid="cat-add-laag"]').setValue('technology')
    await w.find('[data-testid="cat-add-aspect"]').setValue('active')
    await w.find('[data-testid="cat-add-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="cat-add-formfout"]').exists()).toBe(true)
    expect(api.platformComponentconfig.maak).toHaveBeenCalledWith(
      expect.objectContaining({
        dimensie: 'componenttype', optie_sleutel: 'etl_tool',
        archimate_element: 'system_software', archimate_laag: 'technology', archimate_aspect: 'active',
      }),
    )
  })

  it('bewerken: dimensie en sleutel read-only', async () => {
    const w = await mountBeheer()
    await w.find('[data-testid="cat-bewerk-2"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cat-edit-sleutel-readonly"]').text()).toContain('database')
    expect(w.find('[data-testid="cat-edit-dimensie-readonly"]').text()).toContain('Componenttypen')
    expect(w.find('input[data-testid="cat-edit-sleutel"]').exists()).toBe(false)
  })

  it('deactiveren: bevestiging + werkBij actief=false', async () => {
    api.platformComponentconfig.werkBij.mockResolvedValueOnce({ ..._opties()[1], actief: false })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-deactiveer-2"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cat-deact-uitleg"]').text()).toContain('blijven leesbaar')
    await w.find('[data-testid="cat-deact-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.platformComponentconfig.werkBij).toHaveBeenCalledWith(2, { actief: false })
  })
})

describe('ComponentConfigBeheer — ADR-026 typering', () => {
  it('toont element/laag/aspect-kolommen voor componenttype, niet voor structuurrelatie', async () => {
    const w = await mountBeheer()
    // componenttype-rij draagt de typering-cellen
    expect(w.find('[data-testid="cat-element-2"]').text()).toContain('system_software')
    expect(w.find('[data-testid="cat-laag-2"]').text()).toContain('technology')
    expect(w.find('[data-testid="cat-aspect-2"]').text()).toContain('active')
    // structuurrelatie-rij heeft géén typering-cellen
    expect(w.find('[data-testid="cat-element-4"]').exists()).toBe(false)
  })

  it('toevoegen componenttype: typering-dropdowns verplicht', async () => {
    const w = await mountBeheer()
    await w.find('[data-testid="cat-toevoegen-componenttype"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cat-add-element"]').exists()).toBe(true)
    await w.find('[data-testid="cat-add-sleutel"]').setValue('etl_tool')
    await w.find('[data-testid="cat-add-label"]').setValue('ETL')
    await w.find('[data-testid="cat-add-form"]').trigger('submit')
    await flushPromises()
    // zonder typering ⇒ validatiefout, geen call
    expect(w.find('[data-testid="cat-add-fout-archimate_element"]').exists()).toBe(true)
    expect(api.platformComponentconfig.maak).not.toHaveBeenCalled()
  })

  it('toevoegen structuurrelatie: géén typering-dropdowns', async () => {
    const w = await mountBeheer()
    await w.find('[data-testid="cat-toevoegen-structuurrelatie_type"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cat-add-element"]').exists()).toBe(false)
  })

  it('bewerken componenttype: typering vooringevuld + meegestuurd', async () => {
    api.platformComponentconfig.werkBij.mockResolvedValueOnce({ ..._opties()[1], archimate_element: 'node' })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-bewerk-2"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cat-edit-element"]').element.value).toBe('system_software')
    await w.find('[data-testid="cat-edit-element"]').setValue('node')
    await w.find('[data-testid="cat-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformComponentconfig.werkBij).toHaveBeenCalledWith(2, expect.objectContaining({
      archimate_element: 'node', archimate_laag: 'technology', archimate_aspect: 'active',
    }))
  })
})

describe('ComponentConfigBeheer — rol-gating', () => {
  it('platformoperator: alles read-only', async () => {
    const w = await mountBeheer({ rollen: ['platformoperator'] })
    expect(w.find('[data-testid="cat-toevoegen-componenttype"]').exists()).toBe(false)
    expect(w.find('[data-testid="cat-bewerk-2"]').exists()).toBe(false)
    expect(w.find('[data-testid="cat-deactiveer-2"]').exists()).toBe(false)
    expect(w.text()).toContain('Database')  // catalogus zelf wél zichtbaar
  })
})

describe('ComponentConfigBeheer — ADR-027 checklist_dragend-toggle + kenmerk-viewer', () => {
  it('toont de Checklist-status per componenttype (Ja/Nee)', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="cat-dragend-1"]').text()).toContain('Ja') // applicatie
    expect(w.find('[data-testid="cat-dragend-2"]').text()).toContain('Nee') // database
  })

  it('aanmaken van een componenttype stuurt checklist_dragend mee', async () => {
    api.platformComponentconfig.maak.mockResolvedValue({ id: 9, dimensie: 'componenttype', optie_sleutel: 'middleware', label: 'Middleware', volgorde: 3, actief: true, archimate_element: 'system_software', archimate_laag: 'technology', archimate_aspect: 'active', checklist_dragend: true })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-toevoegen-componenttype"]').trigger('click')
    await w.find('[data-testid="cat-add-sleutel"]').setValue('middleware')
    await w.find('[data-testid="cat-add-label"]').setValue('Middleware')
    await w.find('[data-testid="cat-add-element"]').setValue('system_software')
    await w.find('[data-testid="cat-add-laag"]').setValue('technology')
    await w.find('[data-testid="cat-add-aspect"]').setValue('active')
    await w.find('[data-testid="cat-add-checklist_dragend"]').setValue(true)
    await w.find('[data-testid="cat-add-ondersteunt_werk"]').setValue(true)
    await w.find('[data-testid="cat-add-form"]').trigger('submit')
    await flushPromises()
    // ADR-045 besluit 4 — de volledige inrichting in één handeling: BEIDE vlaggen in de
    // Create-payload (het pad dat vóór deze slice op 422 extra_forbidden stukliep).
    expect(api.platformComponentconfig.maak).toHaveBeenCalledWith(expect.objectContaining({ optie_sleutel: 'middleware', checklist_dragend: true, ondersteunt_werk: true }))
  })

  it('bewerken stuurt checklist_dragend mee (toggle uit)', async () => {
    api.platformComponentconfig.werkBij.mockResolvedValue({ ..._opties()[0], checklist_dragend: false })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-bewerk-1"]').trigger('click')
    await w.find('[data-testid="cat-edit-checklist_dragend"]').setValue(false)
    await w.find('[data-testid="cat-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformComponentconfig.werkBij).toHaveBeenCalledWith(1, expect.objectContaining({ checklist_dragend: false }))
  })

  it('ADR-045: toont de Ondersteunt-werk-status per componenttype (Ja/Nee)', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="cat-werk-1"]').text()).toContain('Ja') // applicatie
    expect(w.find('[data-testid="cat-werk-2"]').text()).toContain('Nee') // database
  })

  it('ADR-045: bewerken stuurt ondersteunt_werk mee (toggle uit)', async () => {
    api.platformComponentconfig.werkBij.mockResolvedValue({ ..._opties()[0], ondersteunt_werk: false })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-bewerk-1"]').trigger('click')
    await w.find('[data-testid="cat-edit-ondersteunt_werk"]').setValue(false)
    await w.find('[data-testid="cat-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformComponentconfig.werkBij).toHaveBeenCalledWith(1, expect.objectContaining({ ondersteunt_werk: false }))
  })

  it('kenmerk-viewer toont read-only de kenmerken per relatietype; géén bewerk-affordance', async () => {
    const w = await mountBeheer()
    const viewer = w.find('[data-testid="cat-kenmerk-viewer"]')
    expect(viewer.exists()).toBe(true)
    expect(w.find('[data-testid="cat-kenmerk-flow-protocol"]').text()).toContain('enum')
    expect(w.find('[data-testid="cat-kenmerk-flow-richting"]').exists()).toBe(true)
    expect(w.find('[data-testid="cat-kenmerk-leeg-composition"]').exists()).toBe(true) // kale relatie
    // read-only: geen toevoeg/bewerk-knoppen of inputs binnen de viewer
    expect(viewer.find('button').exists()).toBe(false)
    expect(viewer.find('input').exists()).toBe(false)
  })
})
