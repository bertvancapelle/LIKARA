/** Tests — DetailKop (LI040): de acties horen bij het object, niet bij het einde van
 * de pagina. Zichtbare-tekst-asserts (geen "rendert"-checks). */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import DetailKop from '@/components/DetailKop.vue'

const mountKop = (props = {}, slots = {}) =>
  mount(DetailKop, { props: { naam: 'Zaaksysteem', ...props }, slots })

describe('DetailKop', () => {
  it('toont de naam als h1 met het gegeven titel-id (aria-anker)', () => {
    const w = mountKop({ titelId: 'component-titel' })
    const h1 = w.find('h1#component-titel')
    expect(h1.exists()).toBe(true)
    expect(h1.text()).toBe('Zaaksysteem')
  })

  it('acties staan in de kop-actiezone; destructief in een EIGEN, gescheiden zone', () => {
    const w = mountKop({}, {
      acties: '<button data-testid="bewerken-knop">Bewerken</button><button>Geschiedenis</button>',
      destructief: '<button data-testid="verwijder-knop">Verwijderen</button>',
    })
    const acties = w.find('[data-testid="detail-kop-acties"]')
    expect(acties.exists()).toBe(true)
    expect(acties.text()).toContain('Bewerken')
    expect(acties.text()).toContain('Geschiedenis')
    // Destructief: apart blok mét visuele scheiding (rand + afstand) — een misklik
    // naast Bewerken mag geen object wissen.
    const destructief = w.find('[data-testid="detail-kop-destructief"]')
    expect(destructief.exists()).toBe(true)
    expect(destructief.text()).toBe('Verwijderen')
    expect(destructief.classes().join(' ')).toContain('border-l')
    expect(destructief.find('[data-testid="verwijder-knop"]').exists()).toBe(true)
  })

  it('zonder acties-slots rendert er géén lege actiezone', () => {
    const w = mountKop()
    expect(w.find('[data-testid="detail-kop-acties"]').exists()).toBe(false)
  })

  it('een lange naam wordt NOOIT afgekapt: wrap-klassen, geen truncate/ellipsis', () => {
    const lang = 'Gemeenschappelijke-basisregistratie-personen-bevragingsvoorziening West Betuwe'
    const w = mountKop({ naam: lang })
    const h1 = w.find('[data-testid="detail-kop-naam"]')
    expect(h1.text()).toBe(lang) // volledige tekst — identiteit wordt nooit ingekort
    const klassen = h1.classes().join(' ')
    expect(klassen).toContain('break-words')
    expect(klassen).not.toContain('truncate')
    expect(klassen).not.toContain('ellipsis')
    // De kop-rij wrapt zodat de acties bereikbaar blijven bij elke breedte.
    expect(w.find('[data-testid="detail-kop"] > div').classes()).toContain('flex-wrap')
  })

  it('badges en subtitel krijgen hun eigen plek (identiteit links, context eronder)', () => {
    const w = mountKop({}, {
      badges: '<span data-testid="badge">Applicatie</span>',
      subtitel: '<p data-testid="sub">Hoort bij: BvoWB</p>',
    })
    expect(w.find('[data-testid="badge"]').text()).toBe('Applicatie')
    expect(w.find('[data-testid="sub"]').text()).toBe('Hoort bij: BvoWB')
  })
})
