/**
 * Icoon — de tekens van LIKARA (LI048).
 *
 * De scherpste toets van dit bestand is `een aangeroepen teken bestaat ook echt`. Het defect dat
 * deze slice opruimde was precies dat: `icon="pi pi-info-circle"` verwees naar een klasse die
 * nergens in het project bestond, dus er rendert al maanden niets — zonder dat iets het meldde.
 * Een stille lege render is de faalmodus die geen enkele suite vangt, tenzij je er expliciet op
 * toetst (zie likara-werkprotocol: de niet-geresolvede-component-les).
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import Icoon, { TEKENS } from '@/components/Icoon.vue'

describe('Icoon', () => {
  it('rendert een zichtbaar teken voor elke bekende naam', () => {
    for (const naam of Object.keys(TEKENS)) {
      const w = mount(Icoon, { props: { naam } })
      const svg = w.get('svg')
      expect(svg.attributes('data-icoon')).toBe(naam)
      // Niet "er staat een <svg>" maar "er staat iets IN die svg" — een leeg kader is precies
      // de stille lege render waar dit bestand tegen bestaat.
      expect(w.findAll('path').length).toBeGreaterThan(0)
      for (const pad of w.findAll('path')) {
        expect(pad.attributes('d')).toBeTruthy()
      }
    }
  })

  it('erft kleur en grootte van de knop waarin het staat', () => {
    // Een vaste kleur of pixelmaat laat het teken uit de pas lopen met de tekst ernaast, en dan
    // valt een knoppenrij visueel uiteen — het probleem van de lijstkop eerder deze sessie.
    const svg = mount(Icoon, { props: { naam: 'kaart' } }).get('svg')
    expect(svg.attributes('stroke')).toBe('currentColor')
    expect(svg.attributes('width')).toBe('1em')
    expect(svg.attributes('height')).toBe('1em')
  })

  it('is zelf onzichtbaar voor een schermlezer', () => {
    // De naam hoort op de KNOP, niet op het pad — anders leest een schermlezer de tekst dubbel
    // of noemt hij de knop "knop".
    const svg = mount(Icoon, { props: { naam: 'geschiedenis' } }).get('svg')
    expect(svg.attributes('aria-hidden')).toBe('true')
    expect(svg.attributes('focusable')).toBe('false')
  })

  it('DE REGEL: alleen wegwijzers (en handvatten) krijgen een teken, handelingen niet', () => {
    // De grens ligt niet bij de lengte van het woord maar bij wat er gebeurt als je verkeerd
    // klikt. Een wegwijzer brengt je ergens heen (één klik terug); een handeling verandert iets.
    // Verschijnt hier ooit 'verwijderen' of 'bewerken', dan is die grens ongemerkt verschoven —
    // en dat mag alleen met een expliciet besluit, niet als bijvangst van "consistentie".
    // ADR-056/LI051 (expliciet besluit Bert): 'greep' is de derde soort — een HANDVAT.
    // Geen klikdoel, dus de verkeerd-klikken-maat is er niet op van toepassing; P9 blijft
    // onverkort gelden voor knoppen.
    expect(Object.keys(TEKENS).sort()).toEqual(['geschiedenis', 'greep', 'kaart'])
    for (const handeling of ['bewerken', 'verwijderen', 'heropenen', 'klaarverklaren', 'start']) {
      expect(TEKENS).not.toHaveProperty(handeling)
    }
  })

  it('elk teken draagt een titel, zodat de call-site een naam kan overnemen', () => {
    for (const [naam, teken] of Object.entries(TEKENS)) {
      expect(teken.titel, naam).toBeTruthy()
    }
  })
})
