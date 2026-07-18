/** Tests — VeldUitleg (velduitleg-fundament, slice 1): component + accessors. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import VeldUitleg from '@modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue'
import {
  optieUitleg,
  optieUitlegLijst,
  veldUitleg,
} from '@modules/bwb_ontvlechting/frontend/velduitleg'

function mountVU(props = {}) {
  return mount(VeldUitleg, { props: { veld: 'rol', ...props }, attachTo: document.body })
}
const knop = (w, veld = 'rol') => w.find(`[data-testid="uitleg-${veld}-knop"]`)
const paneel = (w, veld = 'rol') => w.find(`[data-testid="uitleg-${veld}-paneel"]`)

beforeEach(() => vi.clearAllMocks())
afterEach(() => vi.restoreAllMocks())

// ── Accessors (nette degradatie) ────────────────────────────────────────────────
describe('velduitleg-accessors', () => {
  it('veldUitleg geeft object of null', () => {
    expect(veldUitleg('rol')).toMatchObject({ uitleg: expect.any(String), vuistregel: expect.any(String) })
    expect(veldUitleg('componenttype')).toMatchObject({ uitleg: expect.any(String) })
    expect(veldUitleg('componenttype').vuistregel).toBeUndefined()
    expect(veldUitleg('bestaat_niet')).toBeNull()
  })
  it('optieUitleg geeft string of null zonder throw', () => {
    expect(typeof optieUitleg('componentrol', 'interne_applicatie')).toBe('string')
    expect(optieUitleg('componentrol', 'onbekende_key')).toBeNull()
    expect(optieUitleg('geen_set', 'x')).toBeNull()
  })
  it('optieUitlegLijst degradeert naar [] bij onbekende set en humaniseert de keys', () => {
    expect(optieUitlegLijst('geen_set')).toEqual([])
    const lijst = optieUitlegLijst('componentrol')
    expect(lijst).toHaveLength(4)
    expect(lijst[0]).toMatchObject({ key: 'interne_applicatie', label: 'Interne applicatie' })
  })
})

// ── Content-borging (slice 2 uitrol) ────────────────────────────────────────────
describe('velduitleg-content', () => {
  it('kernvelden hebben veld-uitleg', () => {
    // ADR-046 — `dispositie` is met het invoerveld vervallen; `levensfase` kwam erbij.
    for (const k of ['rol', 'score', 'componenttype', 'aard', 'beheerrol', 'levensfase',
      'migratiepad', 'archimate_element', 'archimate_laag', 'archimate_aspect', 'sleutel', 'volgorde',
      'eigenaar_organisatie_id', 'leverancier', 'gg_organisatie', 'draait_op', 'blokkade_status']) {
      expect(veldUitleg(k), k).not.toBeNull()
    }
    expect(veldUitleg('dispositie')).toBeNull() // afgebouwd — geen invoerveld meer
  })
  it('optie-sets dekken de verwachte keys', () => {
    expect(optieUitlegLijst('componentrol')).toHaveLength(4)
    expect(optieUitlegLijst('componenttype')).toHaveLength(8)
    expect(optieUitlegLijst('score')).toHaveLength(4)
    expect(optieUitlegLijst('beheerrol')).toHaveLength(9)
    expect(optieUitlegLijst('levensfase')).toHaveLength(3) // ADR-046 — vaste set van drie
    expect(optieUitlegLijst('archimate_element')).toHaveLength(18) // volledig (18/18)
    expect(optieUitlegLijst('archimate_laag')).toHaveLength(4)
    expect(optieUitlegLijst('archimate_aspect')).toHaveLength(3)
    expect(optieUitlegLijst('contracttype')).toHaveLength(3)
    expect(optieUitlegLijst('aard')).toHaveLength(4)             // ADR-038 — burger-aard verwijderd
  })
  it('nagelverde keys hebben nu uitleg; bewuste degradatie blijft', () => {
    expect(optieUitleg('archimate_element', 'device')).not.toBeNull() // set nu volledig
    expect(optieUitleg('blokkade_status', 'opgelost')).toBeNull() // auto-afgeleid, bewust geen keuze-uitleg
  })
})

// ── Popover-interactie ──────────────────────────────────────────────────────────
describe('VeldUitleg popover', () => {
  it('rendert een i-knop met het aria-patroon, paneel dicht', () => {
    const w = mountVU()
    const b = knop(w)
    expect(b.exists()).toBe(true)
    expect(b.attributes('aria-label')).toBe('Uitleg bij dit veld')
    expect(b.attributes('aria-expanded')).toBe('false')
    expect(b.attributes('aria-controls')).toBe('uitleg-rol-paneel')
    expect(paneel(w).isVisible()).toBe(false)
  })

  it('opent op klik', async () => {
    const w = mountVU()
    await knop(w).trigger('click')
    expect(knop(w).attributes('aria-expanded')).toBe('true')
    expect(paneel(w).isVisible()).toBe(true)
  })

  it('adopteert de gedeelde positioneringshulp: paneel is fixed (niet eigen absolute) — blijft in beeld', async () => {
    const w = mountVU()
    await knop(w).trigger('click')
    await flushPromises() // usePopoverPositie berekent op nextTick
    const p = paneel(w)
    expect(p.attributes('style') || '').toContain('position: fixed') // uit usePopoverPositie
    expect(p.classes()).not.toContain('absolute') // regressiewacht: niet terugvallen op eigen positionering
  })

  it('opent op focus', async () => {
    const w = mountVU()
    await knop(w).trigger('focus')
    expect(knop(w).attributes('aria-expanded')).toBe('true')
  })

  it('sluit op herhaalde trigger (klik-toggle)', async () => {
    const w = mountVU()
    await knop(w).trigger('click')
    await knop(w).trigger('click')
    expect(knop(w).attributes('aria-expanded')).toBe('false')
  })

  it('sluit op Escape en geeft focus terug aan de knop', async () => {
    const w = mountVU()
    await knop(w).trigger('click')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(knop(w).attributes('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(knop(w).element)
  })

  it('sluit op klik-buiten', async () => {
    const w = mountVU()
    await knop(w).trigger('click')
    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()
    expect(knop(w).attributes('aria-expanded')).toBe('false')
  })

  it('toont de per-optie discriminatie-regels wanneer opties is meegegeven', async () => {
    const w = mountVU({ opties: 'componentrol' })
    await knop(w).trigger('click')
    for (const key of ['interne_applicatie', 'interne_dataprovider', 'externe_dataprovider', 'koppelvlak']) {
      expect(w.find(`[data-testid="uitleg-rol-optie-${key}"]`).exists()).toBe(true)
    }
  })

  it('degradeert netjes zonder optie-uitleg (Type: alleen veld-uitleg, geen optie-regels, geen fout)', async () => {
    const w = mount(VeldUitleg, { props: { veld: 'componenttype' }, attachTo: document.body })
    await w.find('[data-testid="uitleg-componenttype-knop"]').trigger('click')
    const paneelEl = w.find('[data-testid="uitleg-componenttype-paneel"]')
    expect(paneelEl.isVisible()).toBe(true)
    expect(paneelEl.text()).toContain('Het componenttype bepaalt')
    expect(w.find('[data-testid^="uitleg-componenttype-optie-"]').exists()).toBe(false)
  })

  it('rendert niets voor een veld zonder enige content', () => {
    const w = mount(VeldUitleg, { props: { veld: 'bestaat_niet' } })
    expect(w.find('[data-testid="uitleg-bestaat_niet-knop"]').exists()).toBe(false)
    expect(w.find('[data-testid="uitleg-bestaat_niet-inline"]').exists()).toBe(false)
  })
})

// ── Slice 4c — norm-feit + injectie (besluiten 15-21) ───────────────────────────
function mountNorm(props, verplicht) {
  return mount(VeldUitleg, {
    props, attachTo: document.body,
    global: verplicht ? { provide: { normVerplicht: ref(verplicht) } } : {},
  })
}
describe('VeldUitleg — norm-feit (op de lat)', () => {
  it('normFeit dat verplicht is → de "telt mee"-passage, mét "opslaan kan wel zonder"', async () => {
    const w = mountNorm({ veld: 'eigenaar_organisatie_id', normFeit: 'eigenaar' }, { eigenaar: true })
    await w.find('[data-testid="uitleg-eigenaar_organisatie_id-knop"]').trigger('click')
    const lat = w.find('[data-testid="uitleg-eigenaar_organisatie_id-lat"]')
    expect(lat.exists()).toBe(true)
    expect(lat.text()).toContain('telt mee om dit systeem klaar te kunnen verklaren')
    expect(lat.text()).toContain('Opslaan kan wel zonder') // besluit 16 — geen sterretje-belofte
  })

  it('normFeit NIET verplicht → geen passage (beweegt mee met de norm)', async () => {
    const w = mountNorm({ veld: 'eigenaar_organisatie_id', normFeit: 'eigenaar' }, { eigenaar: false })
    await w.find('[data-testid="uitleg-eigenaar_organisatie_id-knop"]').trigger('click')
    expect(w.find('[data-testid="uitleg-eigenaar_organisatie_id-lat"]').exists()).toBe(false)
  })

  it('geen norm ge-provide → geen passage (backward-compatible; 75 views ongemoeid)', async () => {
    const w = mountNorm({ veld: 'eigenaar_organisatie_id', normFeit: 'eigenaar' }, null)
    await w.find('[data-testid="uitleg-eigenaar_organisatie_id-knop"]').trigger('click')
    expect(w.find('[data-testid="uitleg-eigenaar_organisatie_id-lat"]').exists()).toBe(false)
  })

  it('draagt de passage óók voor een feit zonder eigen veld-uitleg (sectiekop): de i verschijnt tóch', async () => {
    const w = mountNorm({ veld: 'koppelingen', normFeit: 'koppelingen' }, { koppelingen: true })
    const b = w.find('[data-testid="uitleg-koppelingen-knop"]')
    expect(b.exists()).toBe(true)
    await b.trigger('click')
    expect(w.find('[data-testid="uitleg-koppelingen-lat"]').text()).toContain('telt mee')
  })

  it('geen normFeit én geen veld-uitleg → rendert niets (geen kale i)', () => {
    const w = mount(VeldUitleg, { props: { veld: 'bestaat_niet' } })
    expect(w.find('[data-testid="uitleg-bestaat_niet-knop"]').exists()).toBe(false)
  })
})

// ── Inline-modus ────────────────────────────────────────────────────────────────
describe('VeldUitleg inline', () => {
  it('rendert een korte regel onder het veld, geen knop', () => {
    const w = mount(VeldUitleg, { props: { veld: 'biv_beschikbaarheid', inline: true } })
    const regel = w.find('[data-testid="uitleg-biv_beschikbaarheid-inline"]')
    expect(regel.exists()).toBe(true)
    expect(regel.text()).toContain('Beschikbaarheid')
    expect(regel.text()).toContain('Laag =')
    expect(w.find('[data-testid="uitleg-biv_beschikbaarheid-knop"]').exists()).toBe(false)
  })
})
