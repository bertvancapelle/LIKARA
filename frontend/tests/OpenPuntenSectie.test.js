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
// het getal in het tablabel als deze lijst. De sectie krijgt de data dus als prop.
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
  it('besluit 14: de teller in het filterlabel en de getoonde regels komen uit één bron', async () => {
    const w = await mountSectie(_respons({
      moet_nog: {
        aantal: 2,
        punten: [
          { feit: 'biv', route: { soort: 'veld', veld: 'biv' } },
          { feit: 'contract', route: { soort: 'tab', tab: 'contracten' } },
        ],
      },
    }))
    expect(w.find('[data-testid="op-filter-moet_nog"]').text()).toContain('Dit moet nog (2)')
    // Het getal op het filter en het aantal regels kunnen niet uiteenlopen: beide komen uit `aantal`
    // resp. `punten` van dezelfde respons, en de server garandeert dat die gelijk zijn.
    expect(w.findAll('[data-testid="op-lijst-moet_nog"] > li')).toHaveLength(2)
  })

  it('besluit 4: nul is een uitkomst — het blok blijft bestaan, toont 0 en zegt wát er niets open is', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="op-filter-moet_nog"]').text()).toContain('Dit moet nog (0)')
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
    await w.find('[data-testid="op-filter-valt_op"]').trigger('click')
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
    await w.find('[data-testid="op-filter-netjes"]').trigger('click')
    await flushPromises()
    expect(w.findAll('[data-norm-lat]')).toHaveLength(0)
  })

  // ── De verantwoordingszin — WIE én WANNEER, en eerlijk als de naam ontbreekt ────────────────
  it('LI047: zonder vastgelegde naam meldt de zin dát het ontbreekt — geen gat, geen "onbekend"', async () => {
    // Dit is de stand van het HELE demolandschap: nergens is een verklaarder vastgelegd. Een toets
    // die alleen de gevulde variant dekt, mist precies wat er misging ("klaar verklaard door .").
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 1, punten: [{ feit: 'biv', route: null }] },
      klaarverklaring: { verklaard_door: null, verklaard_op: '2026-07-18T09:30:00Z', bewust: [], verschoven: [] },
    }))
    const zin = w.find('[data-testid="op-kv-zin"]').text()
    expect(zin).toContain('wie dat deed is niet vastgelegd')
    expect(zin).toMatch(/18 jul/)          // het moment staat er wél
    expect(zin).not.toMatch(/door\s*\./)   // nooit "door ." — dat was de fout
    expect(zin).not.toContain('onbekend')  // geen niet-bestaande persoon
  })

  it('LI047: mét naam draagt de zin wie én wanneer', async () => {
    const w = await mountSectie(_respons({
      klaarverklaring: { verklaard_door: 'Jan de Vries', verklaard_op: '2026-07-18T09:30:00Z', bewust: [], verschoven: [] },
    }))
    const zin = w.find('[data-testid="op-kv-zin"]').text()
    expect(zin).toContain('Jan de Vries')
    expect(zin).toMatch(/18 jul/)
    // Een verantwoording zonder moment is geen verantwoording: je wilt weten of het besluit van
    // vorige week is of van twee jaar geleden.
    expect(zin).not.toContain('niet vastgelegd')
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
    expect(w.find('[data-testid="op-kv-zin"]').text()).toContain('consultant@likara.test')
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

// ── LI048 2c — de drie blokken zijn FILTERS, geen tabbladen ──────────────────────────────────
describe('OpenPuntenSectie — filtervorm (LI048 2c)', () => {
  it('de blokken dragen geen tab-semantiek: geen role=tab, geen aria-controls naar het niets', async () => {
    // Ze wáren als AppTabs gebouwd: `role="tablist"`/`role="tab"` met `aria-controls` naar
    // `open-punten-panel-*` — panelen die in deze sectie NIET bestaan (er is geen enkele
    // `role="tabpanel"`). Een schermlezer kondigde dus "tabblad 1 van 3" aan en verwees naar het
    // niets. Deze toets valt om zodra iemand er weer tabbladen van maakt.
    const w = await mountSectie()
    expect(w.findAll('[role="tab"]')).toHaveLength(0)
    expect(w.findAll('[role="tablist"]')).toHaveLength(0)
    expect(w.findAll('[aria-controls]')).toHaveLength(0)
    // Wat ze wél zijn: een groep toggle-knoppen over één lijst.
    expect(w.find('[data-testid="op-filters"]').attributes('role')).toBe('group')
  })

  it('een schakelaarstand draagt de gedeelde vorm en de indrukstaat in aria-pressed', async () => {
    const w = await mountSectie()
    const gekozen = w.find('[data-testid="op-filter-moet_nog"]')
    const rest = w.find('[data-testid="op-filter-netjes"]')
    // De vorm leeft in de gedeelde klasse, niet op de call-site …
    expect(gekozen.classes()).toContain('lk-schakelaar-stand')
    expect(rest.classes()).toContain('lk-schakelaar-stand')
    // … en géén tabvorm: een schakelaar is geen plek waar je heen gaat.
    for (const el of [gekozen, rest]) {
      expect(el.classes()).not.toContain('lk-tab')
    }
    // De staat leeft in ARIA (zoals bij de tabbladen in aria-selected), zodat het zichtbare feit
    // en het toegankelijkheidsfeit niet uiteen kunnen lopen — beide lezen dezelfde bron.
    expect(gekozen.attributes('aria-pressed')).toBe('true')
    expect(rest.attributes('aria-pressed')).toBe('false')
    expect(gekozen.classes()).toEqual(rest.classes())
  })

  it('klikken filtert de lijst — het wisselt geen paneel', async () => {
    const w = await mountSectie(_respons({
      netjes: { aantal: 1, punten: [{ feit: 'hosting', route: null }] },
    }))
    // Vóór de klik toont de sectie het moet_nog-filter; ná de klik dezelfde ene lijst met andere
    // inhoud — er is en blijft precies één lijst-element.
    await w.find('[data-testid="op-filter-netjes"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="op-filter-netjes"]').attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="op-filter-moet_nog"]').attributes('aria-pressed')).toBe('false')
    expect(w.findAll('[data-testid^="op-lijst-"]')).toHaveLength(1)
  })
})

// ── LI048 2d — één schakelaar, en de lijst hangt er niet los onder ───────────────────────────
describe('OpenPuntenSectie — schakelaarvorm (LI048 2d)', () => {
  it('de drie standen zitten in ÉÉN schakelaar, niet als losse knopjes naast elkaar', async () => {
    const w = await mountSectie()
    const groep = w.find('[data-testid="op-filters"]')
    expect(groep.classes()).toContain('lk-schakelaar')
    // Alle drie de standen zitten IN die ene groep — geen losse knopjes ernaast.
    expect(groep.findAll('.lk-schakelaar-stand')).toHaveLength(3)
  })

  it('onder de schakelaar staat één scheidingslijn — de lijst hangt er niet los onder', async () => {
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 1, punten: [{ feit: 'biv', route: null }] },
    }))
    // De streep hoort NIET op de schakelaar zelf (die sluit strak om de knopjes) maar op de
    // omhullende rij, zodat hij over de volle breedte loopt en kiezen van krijgen scheidt.
    const streep = w.find('.lk-schakelaar-streep')
    expect(streep.exists()).toBe(true)
    expect(streep.classes()).not.toContain('lk-schakelaar')
    // De schakelaar zit erbinnen; de lijst staat eronder.
    expect(streep.find('[data-testid="op-filters"]').exists()).toBe(true)
  })

  it('2d: de lijst draagt GEEN eigen achtergrondvulling — signaal hoort op wit', async () => {
    // In deze lijst staan de signalen (amber = bewust afgewogen, gedempt = verschoven lat, blauw
    // = Vastleggen). Een gekleurde vloer eronder zou daarmee concurreren — dezelfde reden waarom
    // het gekleurde tabbladvlak eerder is afgewezen. Deze toets valt om zodra iemand de lijst
    // (of zijn regels) een `bg-`/`lk-schakelaar`-vulling geeft.
    const w = await mountSectie(_respons({
      moet_nog: { aantal: 2, punten: [{ feit: 'biv', route: null }, { feit: 'contract', route: null }] },
    }))
    const lijst = w.find('[data-testid="op-lijst-moet_nog"]')
    expect(lijst.exists()).toBe(true)
    const vulling = (el) => el.classes().filter((c) => c.startsWith('bg-') || c.startsWith('lk-schakelaar'))
    expect(vulling(lijst), 'de lijst draagt een achtergrondvulling').toEqual([])
    for (const rij of lijst.findAll('li')) {
      expect(vulling(rij), 'een lijstregel draagt een achtergrondvulling').toEqual([])
    }
  })
})
