/**
 * LijstKop — de gedeelde kop van élk lijstscherm (LI048).
 *
 * Wat hier wordt geborgd is de VOLGORDE en de PLAATS, niet het uiterlijk: de consultant
 * loopt de hele dag van scherm naar scherm en moet de aanmaakknop nooit opnieuw zoeken.
 * Vandaar dat de toets die "de actie staat op dezelfde plek, ook zonder zoekveld" bewaakt
 * de belangrijkste van dit bestand is — dat is regel 3, en precies wat de handgebouwde
 * koppen niet deden.
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import LijstKop from '@/components/LijstKop.vue'

const kop = (w) => w.get('[data-testid="lijst-kop"]')

describe('LijstKop', () => {
  it('toont de schermnaam als h1 met het meegegeven id', () => {
    const w = mount(LijstKop, { props: { titel: 'Partijen', titelId: 'partijen-titel' } })
    const h1 = w.get('[data-testid="lijst-kop-titel"]')
    expect(h1.element.tagName).toBe('H1')
    expect(h1.text()).toBe('Partijen')
    // Het id draagt de `aria-labelledby` van de omliggende section — zonder dit id
    // heeft de sectie geen toegankelijke naam meer.
    expect(h1.attributes('id')).toBe('partijen-titel')
  })

  it('zet de slots in de vaste volgorde: naam · zoek · filter · actie', () => {
    const w = mount(LijstKop, {
      props: { titel: 'Componenten', titelId: 'c' },
      slots: {
        zoek: '<input data-testid="z" />',
        filter: '<button data-testid="f">Filter</button>',
        actie: '<button data-testid="a">Nieuw</button>',
      },
    })
    const volgorde = [...kop(w).element.children].map((el) => el.getAttribute('data-testid'))
    expect(volgorde).toEqual([
      'lijst-kop-titel',
      'lijst-kop-zoek',
      'lijst-kop-filter',
      'lijst-kop-actie',
    ])
  })

  it('de call-site kan de volgorde niet omdraaien', () => {
    // Slots in omgekeerde volgorde meegeven verandert niets — de bouwsteen bepaalt.
    const w = mount(LijstKop, {
      props: { titel: 'X', titelId: 'x' },
      slots: {
        actie: '<button>Nieuw</button>',
        filter: '<button>Filter</button>',
        zoek: '<input />',
      },
    })
    const volgorde = [...kop(w).element.children].map((el) => el.getAttribute('data-testid'))
    expect(volgorde.indexOf('lijst-kop-zoek')).toBeLessThan(volgorde.indexOf('lijst-kop-filter'))
    expect(volgorde.indexOf('lijst-kop-filter')).toBeLessThan(volgorde.indexOf('lijst-kop-actie'))
  })

  it('houdt de actie op dezelfde plek als het zoekveld ontbreekt (regel 3)', () => {
    // DE toets van dit bestand. Zou het lege zoekslot wegvallen, dan schuift de actie naar
    // links en staat hij per scherm ergens anders — precies wat de handgebouwde koppen deden.
    const zonder = mount(LijstKop, {
      props: { titel: 'X', titelId: 'x' },
      slots: { actie: '<button data-testid="a">Nieuw</button>' },
    })
    const zoekslot = zonder.get('[data-testid="lijst-kop-zoek"]')
    expect(zoekslot.exists()).toBe(true)
    // `flex-1` is wat de ruimte opvult; zonder die klasse valt de actie naar links.
    expect(zoekslot.classes()).toContain('flex-1')
    // De actie blijft het laatste kind, net als mét zoekveld.
    const kinderen = [...kop(zonder).element.children].map((el) => el.getAttribute('data-testid'))
    expect(kinderen[kinderen.length - 1]).toBe('lijst-kop-actie')
  })

  it('laat filter- en actieslot weg als de call-site ze niet vult', () => {
    // Een leeg kadertje met een rand of marge zou als een lege knop lezen.
    const w = mount(LijstKop, { props: { titel: 'X', titelId: 'x' } })
    expect(w.find('[data-testid="lijst-kop-filter"]').exists()).toBe(false)
    expect(w.find('[data-testid="lijst-kop-actie"]').exists()).toBe(false)
  })

  it('laat de schermnaam niet platdrukken door een lang zoekveld', () => {
    // De langste schermnaam mag niet worden afgekapt; het zoekveld krimpt, de naam niet.
    const w = mount(LijstKop, { props: { titel: 'Architectuur — lagen', titelId: 'x' } })
    expect(w.get('[data-testid="lijst-kop-titel"]').classes()).toContain('shrink-0')
    expect(w.get('[data-testid="lijst-kop-zoek"]').classes()).toContain('min-w-0')
  })
})
