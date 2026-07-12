/** Tests — useToonNieuweRij (LI039 blok B + UI-afronding punt 2).
 *
 * Gedrag, geen payload: het pad naar een nieuwe rij klapt open; een verbergende
 * zoekterm wijkt ZICHTBAAR (melding, dooft bij eigen invoer); en de rij komt in
 * beeld — maar alléén als hij daarbuiten stond (een verspringend scherm zonder
 * reden is zelf verwarrend).
 */
import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { scrolNaarRij, useAanstip, useToonInBoom } from '@/composables/useToonNieuweRij'

const _el = ({ top, bottom, height = bottom - top }) => ({
  getBoundingClientRect: () => ({ top, bottom, height }),
  scrollIntoView: vi.fn(),
})

describe('scrolNaarRij — alleen scrollen als het nodig is (punt 2)', () => {
  it('rij volledig in beeld → NIETS bewegen', () => {
    vi.stubGlobal('innerHeight', 800)
    const el = _el({ top: 100, bottom: 140 })
    expect(scrolNaarRij(el)).toBe(false)
    expect(el.scrollIntoView).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('rij buiten beeld → zachte scroll naar het midden (context eromheen)', () => {
    vi.stubGlobal('innerHeight', 800)
    const el = _el({ top: 1900, bottom: 1940 })
    expect(scrolNaarRij(el)).toBe(true)
    expect(el.scrollIntoView).toHaveBeenCalledWith({ block: 'center', behavior: 'smooth' })
    vi.unstubAllGlobals()
  })

  it('deels boven de bovenrand telt óók als buiten beeld', () => {
    vi.stubGlobal('innerHeight', 800)
    const el = _el({ top: -20, bottom: 20 })
    expect(scrolNaarRij(el)).toBe(true)
    vi.unstubAllGlobals()
  })

  it('geen element → geen fout, geen scroll', () => {
    expect(scrolNaarRij(null)).toBe(false)
  })
})

describe('useAanstip — de aanstip is de "kijk hier"-drager', () => {
  it('zet aangestiptId en dooft na de timer', () => {
    vi.useFakeTimers()
    const { aangestiptId, aanstip } = useAanstip(1000)
    aanstip('x1')
    expect(aangestiptId.value).toBe('x1')
    vi.advanceTimersByTime(1100)
    expect(aangestiptId.value).toBe(null)
    vi.useRealTimers()
  })
})

describe('useToonInBoom — pad open + zoekterm wijkt zichtbaar', () => {
  function maak({ term = '', matchtId = null } = {}) {
    const openTakken = ref([])
    const zoekterm = ref(term)
    const ouders = { kind: 'ouder', ouder: 'wortel' } // kind → ouder → wortel
    const boom = useToonInBoom({
      openTakken,
      zoekterm,
      matcht: (id) => id === matchtId,
      ouderVan: (id) => ouders[id] ?? null,
      wijkTekst: 'Zoekterm opzij gezet.',
    })
    return { openTakken, zoekterm, ...boom }
  }

  it('klapt de volledige ouderketen open (ook een dichte ouder)', async () => {
    const { openTakken, toonRij } = maak()
    toonRij('kind')
    expect(openTakken.value).toContain('ouder')
    expect(openTakken.value).toContain('wortel')
  })

  it('zoekterm die de rij zou verbergen wijkt ZICHTBAAR — en de melding dooft bij eigen invoer', async () => {
    const { zoekterm, wijkMelding, toonRij } = maak({ term: 'klant' })
    toonRij('kind') // matcht niet → term wijkt
    expect(zoekterm.value).toBe('')
    await nextTick() // de interne guard-watch verwerkt de eigen wijziging
    expect(wijkMelding.value).toBe('Zoekterm opzij gezet.')
    // De gebruiker raakt het zoekveld weer aan → de melding hoort te verdwijnen.
    zoekterm.value = 'x'
    await nextTick()
    expect(wijkMelding.value).toBe(null)
  })

  it('zoekterm die de rij WEL toont blijft gewoon staan (geen onnodige wijk)', async () => {
    const { zoekterm, wijkMelding, toonRij } = maak({ term: 'klant', matchtId: 'kind' })
    toonRij('kind')
    expect(zoekterm.value).toBe('klant')
    await nextTick()
    expect(wijkMelding.value).toBe(null)
  })
})
