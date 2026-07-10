/** Tests — procesKaartIngang (LI037 fase 3): de ÉNE bouwer van de proces→kaart-handoff.
 *  Klim naar de wortel (cyclus-veilig), boom-vervullers = rollup ∪ wortel-eigen regels (dedup),
 *  herkomst alleen bij een deelproces-ingang, en een lege boom geeft een lege componentIds. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { bouwProcesKaartHandoff } from '@modules/bwb_ontvlechting/frontend/procesKaartIngang'

const api = {
  processen: { haal: vi.fn(), rollup: vi.fn() },
  procesvervullingen: { lijst: vi.fn() },
}

const PROCESSEN = {
  vv: { id: 'vv', naam: 'Vergunningverlening', ouder_id: null },
  ab: { id: 'ab', naam: 'Aanvraag behandelen', ouder_id: 'vv' },
  bv: { id: 'bv', naam: 'Besluit vastleggen', ouder_id: 'ab' },
}

beforeEach(() => {
  vi.clearAllMocks()
  api.processen.haal.mockImplementation(async (id) => PROCESSEN[id])
  api.processen.rollup.mockResolvedValue([{ component_id: 'c1' }, { component_id: 'c2' }])
  api.procesvervullingen.lijst.mockResolvedValue([{ component_id: 'c2' }, { component_id: 'c3' }])
})

describe('bouwProcesKaartHandoff', () => {
  it('processtap-ingang: klimt twee stappen naar de wortel; vervullers = rollup ∪ wortel-eigen (dedup)', async () => {
    const p = await bouwProcesKaartHandoff(api, 'bv')
    expect(api.processen.rollup).toHaveBeenCalledWith('vv')
    expect(api.procesvervullingen.lijst).toHaveBeenCalledWith({ proces_id: 'vv' })
    expect(p).toEqual({
      componentIds: ['c1', 'c2', 'c3'],
      weergave: 'lagen',
      procesIngang: { wortelId: 'vv', wortelNaam: 'Vergunningverlening', herkomstId: 'bv', herkomstNaam: 'Besluit vastleggen' },
    })
  })

  it('hoofdproces-ingang: geen aparte herkomst (herkomst* = null)', async () => {
    const p = await bouwProcesKaartHandoff(api, 'vv')
    expect(p.procesIngang).toEqual({ wortelId: 'vv', wortelNaam: 'Vergunningverlening', herkomstId: null, herkomstNaam: null })
  })

  it('boom zonder ondersteunende systemen → lege componentIds (aanroeper toont de melding)', async () => {
    api.processen.rollup.mockResolvedValue([])
    api.procesvervullingen.lijst.mockResolvedValue([])
    const p = await bouwProcesKaartHandoff(api, 'ab')
    expect(p.componentIds).toEqual([])
  })

  it('cyclus-veilig: een (geconstrueerde) ouder-lus hangt nooit — de klim eindigt deterministisch', async () => {
    api.processen.haal.mockImplementation(async (id) => ({
      a: { id: 'a', naam: 'A', ouder_id: 'b' },
      b: { id: 'b', naam: 'B', ouder_id: 'a' },
    }[id]))
    const p = await bouwProcesKaartHandoff(api, 'a')
    expect(p.procesIngang.wortelId).toBe('b') // eerste her-bezochte = pseudo-wortel
    expect(p.procesIngang.herkomstId).toBe('a')
  })
})
