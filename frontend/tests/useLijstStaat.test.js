/**
 * Tests — useLijstStaat (lijststaat behouden bij terugnavigeren; lk-state-patroon LI034).
 *
 * Gedekt: bewaren (incl. beforeunload-pad + listener-opruiming), gevalideerd herstel
 * (vorm- én domeinvalidatie), corrupte/onbereikbare sessionStorage stil, wis.
 * De precedentie (doorklik-query wint) is scherm-verantwoordelijkheid en wordt in de
 * view-tests bewezen (PartijLijst/ComponentLijst/ContractLijst/BlokkadeOverzichtView).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useLijstStaat } from '@/composables/useLijstStaat'

const KEY = 'lijst-state:test'

// Elke harnas-wrapper na de test unmounten — anders blijven beforeunload-listeners
// van eerdere instanties leven en schrijven die mee bij een latere dispatch.
const _wrappers = []

function maakHarnas({ valideer } = {}) {
  let ctx = null
  const Comp = defineComponent({
    setup() {
      const filterA = ref('')
      const filterLijst = ref([])
      const sortVeld = ref(null)
      const api = useLijstStaat('test', { filterA, filterLijst, sortVeld }, { valideer })
      ctx = { filterA, filterLijst, sortVeld, ...api }
      return () => null
    },
  })
  const wrapper = mount(Comp)
  _wrappers.push(wrapper)
  return { wrapper, ctx }
}

beforeEach(() => sessionStorage.clear())
afterEach(() => {
  while (_wrappers.length) _wrappers.pop().unmount()
  vi.restoreAllMocks()
})

describe('useLijstStaat', () => {
  it('bewaar schrijft de actuele veldwaarden als JSON onder lijst-state:<sleutel>', () => {
    const { ctx } = maakHarnas()
    ctx.filterA.value = 'organisatie'
    ctx.filterLijst.value = ['a', 'b']
    ctx.sortVeld.value = 'naam'
    ctx.bewaar()
    expect(JSON.parse(sessionStorage.getItem(KEY))).toEqual({
      filterA: 'organisatie',
      filterLijst: ['a', 'b'],
      sortVeld: 'naam',
    })
  })

  it('herstel zet bewaarde waarden terug in de refs en meldt true', () => {
    sessionStorage.setItem(KEY, JSON.stringify({ filterA: 'x', filterLijst: ['y'], sortVeld: 'naam' }))
    const { ctx } = maakHarnas()
    expect(ctx.herstel()).toBe(true)
    expect(ctx.filterA.value).toBe('x')
    expect(ctx.filterLijst.value).toEqual(['y'])
    expect(ctx.sortVeld.value).toBe('naam')
  })

  it('herstel zonder bewaarde staat meldt false en laat defaults staan', () => {
    const { ctx } = maakHarnas()
    expect(ctx.herstel()).toBe(false)
    expect(ctx.filterA.value).toBe('')
  })

  it('domeinvalidator: ongeldige waarde blijft stil op de default, geldige velden herstellen wél', () => {
    sessionStorage.setItem(KEY, JSON.stringify({ filterA: 'bestaat_niet', sortVeld: 'naam' }))
    const { ctx } = maakHarnas({ valideer: { filterA: (w) => w === 'geldig' } })
    expect(ctx.herstel()).toBe(true)
    expect(ctx.filterA.value).toBe('') // geweigerd → default
    expect(ctx.sortVeld.value).toBe('naam') // ongevalideerd veld herstelt gewoon
  })

  it('vormvalidatie: objecten en geneste arrays worden geweigerd (stale/corrupt → default)', () => {
    sessionStorage.setItem(
      KEY,
      JSON.stringify({ filterA: { hack: 1 }, filterLijst: [['genest']], sortVeld: 'naam' }),
    )
    const { ctx } = maakHarnas()
    ctx.herstel()
    expect(ctx.filterA.value).toBe('')
    expect(ctx.filterLijst.value).toEqual([])
    expect(ctx.sortVeld.value).toBe('naam')
  })

  it('corrupte JSON in de storage → herstel meldt false zonder te gooien', () => {
    sessionStorage.setItem(KEY, '{niet-json')
    const { ctx } = maakHarnas()
    expect(() => ctx.herstel()).not.toThrow()
    expect(ctx.herstel()).toBe(false)
  })

  it('bewaar faalt stil als sessionStorage gooit (bv. niet beschikbaar)', () => {
    const { ctx } = maakHarnas()
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota')
    })
    expect(() => ctx.bewaar()).not.toThrow()
  })

  it('wis verwijdert de bewaarde staat', () => {
    sessionStorage.setItem(KEY, JSON.stringify({ filterA: 'x' }))
    const { ctx } = maakHarnas()
    ctx.wis()
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })

  it('beforeunload bewaart de actuele staat (F5-pad, kaart-les LI034); unmount ruimt de listener op', () => {
    const { wrapper, ctx } = maakHarnas()
    ctx.filterA.value = 'voor-reload'
    window.dispatchEvent(new Event('beforeunload'))
    expect(JSON.parse(sessionStorage.getItem(KEY)).filterA).toBe('voor-reload')
    // Na unmount schrijft een beforeunload niet meer (listener opgeruimd, geen lek).
    wrapper.unmount()
    sessionStorage.clear()
    window.dispatchEvent(new Event('beforeunload'))
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })
})
