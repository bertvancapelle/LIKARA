/** Tests — OpenPuntenSectie (LI047): "wat heeft dit component nog nodig?" */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

import OpenPuntenSectie from '@modules/bwb_ontvlechting/frontend/views/OpenPuntenSectie.vue'

const CID = 'comp-1'

const _respons = (over = {}) => ({
  component_id: CID,
  moet_nog: { aantal: 0, punten: [] },
  netjes: { aantal: 0, punten: [] },
  valt_op: { aantal: 0, punten: [] },
  klaarverklaring: null,
  ...over,
})

// LI047 snede 2 — de sectie laadt niet zelf: ComponentDetail is het ENE laadpunt en voedt zowel
// de teller op de kopknop als deze lijst. De sectie krijgt de data dus als prop.
async function mountSectie(data = _respons()) {
  const w = mount(OpenPuntenSectie, {
    props: { componentId: CID, data },
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }]] },
  })
  await flushPromises()
  return w
}

beforeEach(() => vi.clearAllMocks())

describe('OpenPuntenSectie', () => {
  it('besluit 14: de teller in de tabnaam en de getoonde regels komen uit één bron', async () => {
    const w = await mountSectie(_respons({
      moet_nog: {
        aantal: 2,
        punten: [
          { feit: 'biv', route: { soort: 'veld', veld: 'biv' } },
          { feit: 'contract', route: { soort: 'tab', tab: 'contracten' } },
        ],
      },
    }))
    expect(w.find('[data-testid="open-punten-tab-moet_nog"]').text()).toContain('Dit moet nog (2)')
    // Het getal in de tab en het aantal regels kunnen niet uiteenlopen: beide komen uit `aantal`
    // resp. `punten` van dezelfde respons, en de server garandeert dat die gelijk zijn.
    expect(w.findAll('[data-testid="op-lijst-moet_nog"] > li')).toHaveLength(2)
  })

  it('besluit 4: nul is een uitkomst — het blok blijft bestaan, toont 0 en zegt wát er niets open is', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="open-punten-tab-moet_nog"]').text()).toContain('Dit moet nog (0)')
    expect(w.find('[data-testid="op-leeg-moet_nog"]').exists()).toBe(true)
    expect(w.find('[data-testid="op-leeg-moet_nog"]').text()).toContain('niets meer open')
    // Geen lege staat die als storing leest: er staat een rustige regel, geen lijst.
    expect(w.find('[data-testid="op-lijst-moet_nog"]').exists()).toBe(false)
  })

  it('besluit 20: de feitnaam komt uit de gedeelde labelbron', async () => {
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 1, punten: [{ feit: 'bedoeling', route: null }] },
    }))
    // Niet de sleutel 'bedoeling' maar het gedeelde label — hetzelfde woord als op het scherm
    // waar je het vastlegt.
    expect(w.find('[data-testid="op-punt-bedoeling"]').text()).toContain('Bedoeling (migratiepad)')
  })

  it('besluit 3: de checklistregel is gebundeld tot één regel met het aantal', async () => {
    const w = await mountSectie(_respons({
      valt_op: {
        aantal: 1,
        punten: [{ soort: 'checklist_nee_deels', aantal: 7, route: { soort: 'tab', tab: 'checklist' } }],
      },
    }))
    await w.find('[data-testid="open-punten-tab-valt_op"]').trigger('click')
    await flushPromises()
    const regel = w.find('[data-testid="op-punt-checklist_nee_deels"]')
    expect(regel.text()).toContain('7 checklistantwoorden')
    // Eén regel, niet zeven — anders verdrinken de feiten die er echt toe doen.
    expect(w.findAll('[data-testid="op-lijst-valt_op"] > li')).toHaveLength(1)
  })

  it('besluit 8: een punt zonder invoerplek krijgt géén knop maar een eerlijke melding', async () => {
    const w = await mountSectie(_respons({
      moet_nog: {
        aantal: 2,
        punten: [
          { feit: 'koppelingen', route: null }, // fileshare: het tabblad bestaat daar niet
          { feit: 'contract', route: { soort: 'tab', tab: 'contracten' } },
        ],
      },
    }))
    expect(w.find('[data-testid="op-ga-koppelingen"]').exists()).toBe(false)
    expect(w.find('[data-testid="op-geen-route-koppelingen"]').exists()).toBe(true)
    expect(w.find('[data-testid="op-ga-contract"]').exists()).toBe(true)
  })

  it('besluit 8: klikken meldt de route naar boven — het scherm bepaalt de landing', async () => {
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 1, punten: [{ feit: 'biv', route: { soort: 'veld', veld: 'biv' } }] },
    }))
    await w.find('[data-testid="op-ga-biv"]').trigger('click')
    expect(w.emitted('ga-naar')[0]).toEqual([{ soort: 'veld', veld: 'biv' }])
  })

  it('besluit 21: de norm-aanduiding staat één keer boven het blok, niet per rij', async () => {
    const w = await mountSectie(_respons({
      moet_nog: {
        aantal: 3,
        punten: [{ feit: 'biv', route: null }, { feit: 'eigenaar', route: null }, { feit: 'contract', route: null }],
      },
    }))
    // Drie punten, één aanduiding — niet drie keer dezelfde zin.
    expect(w.findAll('[data-norm-lat]')).toHaveLength(1)
    expect(w.find('[data-testid="op-norm-aanduiding"]').text()).toContain('verplicht gesteld')
  })

  it('besluit 21: het netjes-blok draagt de norm-aanduiding NIET (die feiten zijn niet verplicht)', async () => {
    const w = await mountSectie(_respons({
      netjes: { aantal: 1, punten: [{ feit: 'hosting', route: null }] },
    }))
    await w.find('[data-testid="open-punten-tab-netjes"]').trigger('click')
    await flushPromises()
    expect(w.findAll('[data-norm-lat]')).toHaveLength(0)
  })

  it('besluiten 15-17: na klaarverklaring blijven de punten staan, en bewust/verschoven zijn gescheiden', async () => {
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 2, punten: [{ feit: 'biv', route: null }, { feit: 'bedoeling', route: null }] },
      klaarverklaring: {
        verklaard_door: 'consultant@likara.test',
        verklaard_op: '2026-07-01T10:00:00Z',
        bewust: ['biv'],
        verschoven: ['bedoeling'],
      },
    }))
    // Besluit 15 — de punten verdwijnen niet.
    expect(w.findAll('[data-testid="op-lijst-moet_nog"] > li')).toHaveLength(2)
    // Besluit 16 — de toon is verantwoording, mét wie.
    expect(w.find('[data-testid="op-klaarverklaring"]').text()).toContain('consultant@likara.test')
    // Besluit 17 — twee groepen, gescheiden. LIKARA schrijft geen besluit toe aan wie het niet nam.
    expect(w.find('[data-testid="op-kv-bewust"]').text()).toContain('BIV-classificatie')
    expect(w.find('[data-testid="op-kv-verschoven"]').text()).toContain('Bedoeling (migratiepad)')
    expect(w.find('[data-testid="op-kv-bewust"]').text()).not.toContain('Bedoeling')
  })

  it('besluit 18: zonder klaarverklaring is het één neutrale lijst — geen bewust/verschoven-blok', async () => {
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 1, punten: [{ feit: 'biv', route: null }] },
    }))
    expect(w.find('[data-testid="op-klaarverklaring"]').exists()).toBe(false)
  })

  it('besluit 5: "Dit moet nog" staat bij binnenkomst open', async () => {
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 1, punten: [{ feit: 'biv', route: null }] },
      netjes: { aantal: 1, punten: [{ feit: 'hosting', route: null }] },
    }))
    expect(w.find('[data-testid="op-lijst-moet_nog"]').exists()).toBe(true)
    expect(w.find('[data-testid="op-lijst-netjes"]').exists()).toBe(false)
  })
})
