/**
 * Tests — ScoreBadge + scoreKleur (onderdeel 3): één gedeelde score-kleurbron.
 * Ja groen · Deels oranje · Nee rood · N.v.t. grijs; tekst altijd zichtbaar (a11y).
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import ScoreBadge from '@modules/bwb_ontvlechting/frontend/views/ScoreBadge.vue'
import { SCORE_KLEUR, scoreKleur } from '@modules/bwb_ontvlechting/frontend/labels'

describe('scoreKleur (gedeelde bron)', () => {
  it('mapt elke score op de juiste --cd-kleur', () => {
    expect(scoreKleur('ja')).toBe('text-[var(--cd-color-success)]')
    expect(scoreKleur('deels')).toBe('text-[var(--cd-color-warning)]')
    expect(scoreKleur('nee')).toBe('text-[var(--cd-color-danger)]')
    expect(scoreKleur('nvt')).toBe('text-[var(--cd-color-text-muted)]')
    expect(scoreKleur('onbekend')).toBe('') // geen kleur voor onbekend/leeg
    expect(scoreKleur(null)).toBe('')
  })

  it('SCORE_KLEUR is de single source (alle vier de scores gedekt)', () => {
    expect(Object.keys(SCORE_KLEUR).sort()).toEqual(['deels', 'ja', 'nee', 'nvt'])
  })
})

describe('ScoreBadge', () => {
  it.each([
    ['ja', 'Ja', 'text-[var(--cd-color-success)]'],
    ['deels', 'Deels', 'text-[var(--cd-color-warning)]'],
    ['nee', 'Nee', 'text-[var(--cd-color-danger)]'],
    ['nvt', 'N.v.t.', 'text-[var(--cd-color-text-muted)]'],
  ])('toont %s gekleurd mét zichtbare tekst (a11y)', (score, tekst, klasse) => {
    const w = mount(ScoreBadge, { props: { score } })
    const span = w.find(`[data-testid="score-badge-${score}"]`)
    expect(span.exists()).toBe(true)
    expect(span.text()).toBe(tekst) // tekst is altijd de drager, niet alleen kleur
    expect(span.classes()).toContain(klasse)
  })

  it('toont een neutraal streepje zonder score', () => {
    const w = mount(ScoreBadge, { props: { score: null } })
    expect(w.find('[data-testid^="score-badge-"]').exists()).toBe(false)
    expect(w.text()).toBe('—')
  })
})
