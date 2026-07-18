/** Tests — MigratiegereedheidSectie (ADR-027 slice 2): leesblok + afwijkingssignaal + handel-dialog. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    klaarverklaringen: { lijst: vi.fn(), maak: vi.fn(), wijzigStatus: vi.fn() },
    componentNormen: { status: vi.fn() },
  },
}))

import { api } from '@/api'
import MigratiegereedheidSectie from '@modules/bwb_ontvlechting/frontend/views/MigratiegereedheidSectie.vue'

const COMP = 'comp-1'
const KLAAR = {
  id: 'kv-1', component_id: COMP, status: 'klaar', reden: 'gecoördineerd en akkoord',
  verklaard_door: 'piet@bwb.nl', verklaard_op: '2026-06-19T10:00:00+00:00',
}
const OPEN = { ...KLAAR, id: 'kv-2', status: 'open', reden: 'heropend' }

async function mountSectie({ verklaring = null, aantalGescoord = 89, aantalVragen = 89, normOpen = [] } = {}) {
  api.klaarverklaringen.lijst.mockResolvedValue(verklaring ? [verklaring] : [])
  api.componentNormen.status.mockResolvedValue({
    feiten: Object.fromEntries(normOpen.map((f) => [f, 'niet_vastgesteld'])),
  })
  const w = mount(MigratiegereedheidSectie, {
    props: { componentId: COMP, aantalGescoord, aantalVragen },
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => vi.restoreAllMocks())

describe('MigratiegereedheidSectie — leesblok', () => {
  it('toont "Nog niet klaar verklaard" zonder verklaring; geen wie/reden', async () => {
    const w = await mountSectie({ verklaring: null })
    expect(w.find('[data-testid="mg-status"]').text()).toContain('Nog niet klaar verklaard')
    expect(w.find('[data-testid="mg-door"]').exists()).toBe(false)
    expect(w.find('[data-testid="mg-reden"]').exists()).toBe(false)
  })

  it('toont status + wie/wanneer bij een klaar-verklaring; géén permanente reden (ADR-052 slice 3c)', async () => {
    const w = await mountSectie({ verklaring: KLAAR })
    expect(w.find('[data-testid="mg-status"]').text()).toContain('Klaar verklaard')
    expect(w.find('[data-testid="mg-door"]').text()).toContain('piet@bwb.nl')
    // Reden hoort achter de waarschuwing, niet permanent bij de status.
    expect(w.find('[data-testid="mg-reden"]').exists()).toBe(false)
  })

  it('geen waarschuwing → niets klikbaars: geen amber regel, geen venster in beeld', async () => {
    const w = await mountSectie({ verklaring: KLAAR, aantalGescoord: 89, aantalVragen: 89 })
    expect(w.find('[data-testid="mg-afwijking"]').exists()).toBe(false)
    expect(w.find('[data-testid="mg-norm-open"]').exists()).toBe(false)
    expect(w.find('[data-testid="mg-verantwoording"]').exists()).toBe(false)
  })

  it('afwijkingssignaal: alleen bij klaar + onvolledige vragen-stand', async () => {
    // klaar + onvolledig → signaal
    let w = await mountSectie({ verklaring: KLAAR, aantalGescoord: 77, aantalVragen: 89 })
    expect(w.find('[data-testid="mg-afwijking"]').exists()).toBe(true)
    expect(w.find('[data-testid="mg-afwijking"]').text()).toContain('12 van 89')
    // klaar + volledig → geen signaal
    w = await mountSectie({ verklaring: KLAAR, aantalGescoord: 89, aantalVragen: 89 })
    expect(w.find('[data-testid="mg-afwijking"]').exists()).toBe(false)
    // open + onvolledig → geen signaal
    w = await mountSectie({ verklaring: OPEN, aantalGescoord: 77, aantalVragen: 89 })
    expect(w.find('[data-testid="mg-afwijking"]').exists()).toBe(false)
  })
})

describe('MigratiegereedheidSectie — dialog', () => {
  it('lege reden → veldfout, geen API-call', async () => {
    const w = await mountSectie({ verklaring: null })
    w.vm.openDialog()
    await flushPromises()
    await w.find('[data-testid="mg-form"]').trigger('submit')
    expect(w.find('[data-testid="mg-fout-reden"]').exists()).toBe(true)
    expect(api.klaarverklaringen.maak).not.toHaveBeenCalled()
  })

  it('eerste keer klaar verklaren → maak({component_id, reden}) + leesblok ververst', async () => {
    api.klaarverklaringen.maak.mockResolvedValueOnce({ id: 'kv-new' })
    const w = await mountSectie({ verklaring: null })
    const lijstVoor = api.klaarverklaringen.lijst.mock.calls.length
    w.vm.openDialog()
    await flushPromises()
    await w.find('[data-testid="mg-veld-reden"]').setValue('beoordeeld')
    await w.find('[data-testid="mg-form"]').trigger('submit')
    await flushPromises()
    expect(api.klaarverklaringen.maak).toHaveBeenCalledWith({ component_id: COMP, reden: 'beoordeeld' })
    expect(api.klaarverklaringen.lijst.mock.calls.length).toBe(lijstVoor + 1) // refetch na succes
  })

  it('dialog toont de open-vragen-context bij klaar verklaren (onvolledig)', async () => {
    const w = await mountSectie({ verklaring: null, aantalGescoord: 80, aantalVragen: 89 })
    w.vm.openDialog()
    await flushPromises()
    expect(w.find('[data-testid="mg-dialog-context"]').text()).toContain('9 van 89')
  })

  it('heropenen vanuit klaar → wijzigStatus(id, {status:open})', async () => {
    api.klaarverklaringen.wijzigStatus.mockResolvedValueOnce({ id: KLAAR.id })
    const w = await mountSectie({ verklaring: KLAAR })
    w.vm.openDialog()
    await flushPromises()
    await w.find('[data-testid="mg-veld-reden"]').setValue('toch nog niet af')
    await w.find('[data-testid="mg-form"]').trigger('submit')
    await flushPromises()
    expect(api.klaarverklaringen.wijzigStatus).toHaveBeenCalledWith(KLAAR.id, { status: 'open', reden: 'toch nog niet af' })
  })

  it('klaar verklaren vanuit open → wijzigStatus(id, {status:klaar})', async () => {
    api.klaarverklaringen.wijzigStatus.mockResolvedValueOnce({ id: OPEN.id })
    const w = await mountSectie({ verklaring: OPEN })
    w.vm.openDialog()
    await flushPromises()
    await w.find('[data-testid="mg-veld-reden"]').setValue('nu wel af')
    await w.find('[data-testid="mg-form"]').trigger('submit')
    await flushPromises()
    expect(api.klaarverklaringen.wijzigStatus).toHaveBeenCalledWith(OPEN.id, { status: 'klaar', reden: 'nu wel af' })
  })
})

describe('MigratiegereedheidSectie — ADR-029 naam-resolutie', () => {
  it('toont de geresolveerde naam i.p.v. de e-mail', async () => {
    const w = await mountSectie({ verklaring: { ...KLAAR, verklaard_door_naam: 'Piet Paulusma' } })
    const door = w.find('[data-testid="mg-door"]').text()
    expect(door).toContain('Piet Paulusma')
    expect(door).not.toContain('piet@bwb.nl')
  })

  it('valt terug op de e-mail als er geen naam is', async () => {
    const w = await mountSectie({ verklaring: { ...KLAAR, verklaard_door_naam: null } })
    expect(w.find('[data-testid="mg-door"]').text()).toContain('piet@bwb.nl')
  })
})

describe('MigratiegereedheidSectie — norm-afwijking (ADR-052 slice 3)', () => {
  it('badge (live): klaar verklaard + open verplichte feiten → mg-norm-open, feiten benoemd', async () => {
    const w = await mountSectie({ verklaring: KLAAR, normOpen: ['eigenaar', 'biv'] })
    const b = w.find('[data-testid="mg-norm-open"]')
    expect(b.exists()).toBe(true)
    expect(b.text()).toContain('Eigenaar-organisatie')
    expect(b.text()).toContain('BIV-classificatie')
  })

  it('badge dooft: klaar verklaard + geen open feiten → geen mg-norm-open', async () => {
    const w = await mountSectie({ verklaring: KLAAR, normOpen: [] })
    expect(w.find('[data-testid="mg-norm-open"]').exists()).toBe(false)
  })

  it('geen badge bij een open (niet-klaar) verklaring, ook met open feiten', async () => {
    const w = await mountSectie({ verklaring: OPEN, normOpen: ['eigenaar'] })
    expect(w.find('[data-testid="mg-norm-open"]').exists()).toBe(false)
  })

  it('dialog mét open feiten: benoemt ze + "Toch klaar verklaren" + "Eerst aanvullen"', async () => {
    const w = await mountSectie({ verklaring: null, normOpen: ['contract'] })
    w.vm.openDialog()
    await flushPromises()
    expect(w.find('[data-testid="mg-dialog-norm"]').text()).toContain('Contract')
    expect(w.find('[data-testid="mg-bevestig"]').text()).toContain('Toch klaar verklaren')
    expect(w.find('[data-testid="mg-annuleer"]').text()).toContain('Eerst aanvullen')
  })

  it('geen drempel: dialog zónder open feiten → geen norm-blok, gewone knoppen', async () => {
    const w = await mountSectie({ verklaring: null, normOpen: [] })
    w.vm.openDialog()
    await flushPromises()
    expect(w.find('[data-testid="mg-dialog-norm"]').exists()).toBe(false)
    expect(w.find('[data-testid="mg-bevestig"]').text()).toContain('Klaar verklaren')
    expect(w.find('[data-testid="mg-annuleer"]').text()).toContain('Annuleren')
  })
})

describe('MigratiegereedheidSectie — verantwoordingsvenster (ADR-052 slice 3b)', () => {
  it('klik op de checklist-regel opent het venster met de reden — leesbaar, geen UUID', async () => {
    const w = await mountSectie({
      verklaring: { ...KLAAR, verklaard_door_naam: 'Piet Paulusma' },
      aantalGescoord: 77,
    })
    expect(w.find('[data-testid="mg-verantwoording"]').attributes('style') || '').toContain('display: none')
    await w.find('[data-testid="mg-afwijking"]').trigger('click')
    const v = w.find('[data-testid="mg-verantwoording"]')
    expect(v.attributes('style') || '').not.toContain('display: none')
    expect(v.find('[data-testid="mg-verantwoording-reden"]').text()).toContain('gecoördineerd en akkoord')
    // wie/wanneer staat al bij de status → niet herhaald in het venster
    expect(v.find('[data-testid="mg-verantwoording-door"]').exists()).toBe(false)
    expect(w.find('[data-testid="mg-door"]').text()).toContain('Piet Paulusma')
    expect(v.text()).not.toContain('kv-1') // geen sleutel/UUID
    expect(v.text()).not.toContain(COMP)
  })

  it('beide amber regels openen HETZELFDE venster (één klaarverklaring = één besluit)', async () => {
    const w = await mountSectie({
      verklaring: { ...KLAAR, open_feiten: ['biv', 'eigenaar'] },
      aantalGescoord: 77,
      normOpen: ['biv', 'eigenaar'],
    })
    expect(w.find('[data-testid="mg-afwijking"]').exists()).toBe(true)
    expect(w.find('[data-testid="mg-norm-open"]').exists()).toBe(true)
    // Precies één venster in de DOM, gedeeld door beide ingangen.
    expect(w.findAll('[data-testid="mg-verantwoording"]').length).toBe(1)
    await w.find('[data-testid="mg-norm-open"]').trigger('click')
    expect(w.find('[data-testid="mg-verantwoording"]').attributes('style') || '').not.toContain('display: none')
  })

  it('toont de bevroren snapshot met leesbare feit-labels (niet de ruwe sleutels)', async () => {
    const w = await mountSectie({
      verklaring: { ...KLAAR, open_feiten: ['biv', 'eigenaar'] },
      aantalGescoord: 77,
    })
    await w.find('[data-testid="mg-afwijking"]').trigger('click')
    const snap = w.find('[data-testid="mg-verantwoording-snapshot"]')
    expect(snap.text()).toContain('BIV-classificatie')
    expect(snap.text()).toContain('Eigenaar-organisatie')
    expect(snap.text()).not.toContain('biv') // ruwe sleutel niet zichtbaar
  })

  it('geen reden opgegeven → rustige tekst i.p.v. leeg vak', async () => {
    const w = await mountSectie({ verklaring: { ...KLAAR, reden: '' }, aantalGescoord: 77 })
    await w.find('[data-testid="mg-afwijking"]').trigger('click')
    expect(w.find('[data-testid="mg-verantwoording-reden"]').text()).toContain('Geen reden opgegeven')
  })

  it('venster is puur read-only: geen acties/knoppen erin (ook voor de viewer)', async () => {
    const w = await mountSectie({ verklaring: KLAAR, aantalGescoord: 77 })
    await w.find('[data-testid="mg-afwijking"]').trigger('click')
    expect(w.find('[data-testid="mg-verantwoording"]').findAll('button').length).toBe(0)
  })
})
