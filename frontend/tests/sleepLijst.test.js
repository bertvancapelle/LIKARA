/** Tests — useSleepLijst (LI050 W5): de gedeelde sleep-bouwsteen + de bronscan die een
 * tweede implementatie laat falen. */
import { describe, expect, it, vi } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { useSleepLijst } from '@/composables/useSleepLijst'

describe('useSleepLijst — de bouwsteen', () => {
  function maak(ids = ['a', 'b', 'c']) {
    const herschik = vi.fn(async () => {})
    const naSucces = vi.fn()
    const sleep = useSleepLijst({ haalIds: () => [...ids], herschik, naSucces })
    return { sleep, herschik, naSucces }
  }

  it('oppakken + loslaten herordent en bevestigt (bewaren gedelegeerd aan de consument)', async () => {
    const { sleep, herschik, naSucces } = maak()
    sleep.pak('c')
    await sleep.laatLos('a')
    expect(herschik).toHaveBeenCalledWith(['c', 'a', 'b'])
    expect(naSucces).toHaveBeenCalledTimes(1) // zichtbare bevestiging bij loslaten
  })

  it('loslaten op zichzelf of zonder oppakken is een no-op', async () => {
    const { sleep, herschik, naSucces } = maak()
    await sleep.laatLos('a') // niets opgepakt
    sleep.pak('b')
    await sleep.laatLos('b') // op zichzelf
    expect(herschik).not.toHaveBeenCalled()
    expect(naSucces).not.toHaveBeenCalled()
  })

  it('slepen tussen twee lijsten kan niet: een vreemd id is een no-op', async () => {
    const { sleep, herschik } = maak(['a', 'b'])
    sleep.pak('a')
    await sleep.laatLos('id-uit-een-andere-lijst')
    expect(herschik).not.toHaveBeenCalled()
    // En andersom: een vreemd opgepakt id landt nergens.
    sleep.pak('id-uit-een-andere-lijst')
    await sleep.laatLos('a')
    expect(herschik).not.toHaveBeenCalled()
  })

  it('annuleer laat de lijst met rust', async () => {
    const { sleep, herschik } = maak()
    sleep.pak('a')
    sleep.annuleer()
    await sleep.laatLos('c')
    expect(herschik).not.toHaveBeenCalled()
  })
})

describe('sleepLijst — bronscan (KERNLES LI038: één bouwsteen, geen nabouw)', () => {
  // Bereik AFGELEID, niet opgesomd: élk Vue-bestand met een @drop-handler in de template
  // is een sleep-lijst-consument en MOET de bouwsteen importeren. (De kaart-overlays
  // gebruiken useSleepbaar met muis-events, geen HTML5 @drop — die vallen er terecht buiten.)
  const WORTELS = [
    path.resolve(__dirname, '../src'),
    path.resolve(__dirname, '../../modules/bwb_ontvlechting/frontend'),
  ]

  function vueBestanden(map) {
    const uit = []
    for (const naam of fs.readdirSync(map, { withFileTypes: true })) {
      const vol = path.join(map, naam.name)
      if (naam.isDirectory()) uit.push(...vueBestanden(vol))
      else if (naam.name.endsWith('.vue')) uit.push(vol)
    }
    return uit
  }

  it('élk bestand met een @drop-handler gebruikt useSleepLijst — een eigen nabouw valt om', () => {
    const bestanden = WORTELS.flatMap(vueBestanden)
    expect(bestanden.length).toBeGreaterThan(50) // luid falen als het bereik stilletjes smaller wordt
    const overtreders = []
    for (const b of bestanden) {
      const bron = fs.readFileSync(b, 'utf8')
      if (bron.includes('@drop') && !bron.includes('useSleepLijst')) overtreders.push(b)
    }
    expect(overtreders, `sleep-lijst zonder de gedeelde bouwsteen: ${overtreders.join(', ')}`).toEqual([])
  })

  it('zelftest: de scan bijt op een nagebootste overtreder', () => {
    const nep = '<li @drop.prevent="eigenDrop(item.id)">'
    expect(nep.includes('@drop') && !nep.includes('useSleepLijst')).toBe(true)
  })

  it('beide lijsten in het beheerscherm hangen aantoonbaar aan de bouwsteen', () => {
    const bron = fs.readFileSync(
      path.resolve(__dirname, '../src/views/ChecklistConfigBeheer.vue'), 'utf8',
    )
    expect(bron).toContain("import { useSleepLijst } from '@/composables/useSleepLijst'")
    // Twee consumenten: categorieën én vragen — elk hun eigen instantie.
    expect(bron.match(/useSleepLijst\(\{/g)?.length).toBe(2)
    // Het getalveld is bewust weg (besluit Bert): slepen is de enige bediening.
    expect(bron).not.toContain('cfg-cat-volgorde-')
    expect(bron).not.toContain('cfg-nieuwe-categorie-volgorde')
  })
})
