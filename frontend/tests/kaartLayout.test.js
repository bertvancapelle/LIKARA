/** Layout-borging (ADR-040 F1 layout-stap) — met de ECHTE cytoscape (niet de gemockte composable).
 *  Regressie op het "knopen vallen samen"-defect: de deterministische, niet-geanimeerde concentric-
 *  layout moet elke node een EIGEN positie geven op een dichte graaf (parallelle eigenaar+gebruikt-
 *  edges die de degree opblazen). De config hieronder spiegelt `_layout()` in LandschapskaartView.vue. */
import { describe, expect, it } from 'vitest'
import cytoscape from 'cytoscape'

// Spiegel van de Overzicht-config in LandschapskaartView.vue::_layout (modus 'geheel'): CENTRUMLOZE,
// deterministische built-in `grid` (geen ster; geen externe plugin). avoidOverlap + labelgrootte houden
// de knopen uit elkaar.
const GRID_GEHEEL = {
  name: 'grid',
  avoidOverlap: true,
  avoidOverlapPadding: 24,
  nodeDimensionsIncludeLabels: true,
  condense: false,
  padding: 40,
  animate: false,
}

// Dichte, representatieve graaf: een ster + 8 organisatie↔applicatie-paren met TWEE parallelle edges
// (eigenaar + gebruikt) — precies de structuur die de degree opblies en de samenval uitlokte.
function denseElements() {
  const els = []
  for (let i = 0; i < 24; i++) els.push({ data: { id: 'n' + i, label: 'Knoop ' + i + '\napplicatie' } })
  let e = 0
  const push = (s, t, rt) => els.push({ data: { id: `e${e++}-n${s}-n${t}-${rt}`, source: 'n' + s, target: 'n' + t } })
  for (let i = 1; i < 24; i++) push(0, i, 'flow') // ster vanaf n0 (hoge degree)
  for (let k = 1; k <= 8; k++) { push(k, k + 10, 'eigenaar'); push(k, k + 10, 'gebruikt') } // parallelle paren
  return els
}

describe('kaart-layout (ADR-040 F1 — geen samenvallende posities)', () => {
  const mkCy = () => cytoscape({
    headless: true,
    style: [{ selector: 'node', style: { label: 'data(label)', width: 'label', height: 'label', 'text-wrap': 'wrap', 'text-max-width': 180 } }],
    elements: denseElements(),
  })
  const posSig = (cy) => cy.nodes().map((n) => `${Math.round(n.position().x)},${Math.round(n.position().y)}`)

  it('Overzicht (grid): elke node een eigen positie (geen overlap) én deterministisch', () => {
    const cy = mkCy()
    cy.layout(GRID_GEHEEL).run()
    const posities = posSig(cy)
    const uniek = new Set(posities)
    // Kernassertie: geen twee nodes op dezelfde coördinaat → "source/target overlap" is onmogelijk.
    expect(uniek.size).toBe(cy.nodes().length)
    expect(cy.nodes().every((n) => Number.isFinite(n.position().x) && Number.isFinite(n.position().y))).toBe(true)
    // Deterministisch: een tweede identieke run geeft dezelfde posities (geen naschuiven/random).
    const cy2 = mkCy()
    cy2.layout(GRID_GEHEEL).run()
    expect(posSig(cy2)).toEqual(posities)
  })

  it('bij één centrum (praatplaat-config) krijgen de kring-knopen distincte posities', () => {
    const CENTRUM = 'c'
    const cy = cytoscape({
      headless: true,
      style: [{ selector: 'node', style: { label: 'data(label)', width: 'label', height: 'label' } }],
      elements: [
        { data: { id: CENTRUM, label: 'Centrum' } },
        ...Array.from({ length: 12 }, (_, i) => ({ data: { id: 'b' + i, label: 'Buur ' + i } })),
        ...Array.from({ length: 12 }, (_, i) => ({ data: { id: 'e' + i, source: CENTRUM, target: 'b' + i } })),
      ],
    })
    cy.layout({
      name: 'concentric', concentric: (n) => (n.id() === CENTRUM ? 10 : 5), levelWidth: () => 1,
      minNodeSpacing: 25, spacingFactor: 1.0, padding: 40, nodeDimensionsIncludeLabels: true, animate: false,
    }).run()
    const uniek = new Set(cy.nodes().map((n) => `${Math.round(n.position().x)},${Math.round(n.position().y)}`))
    expect(uniek.size).toBe(cy.nodes().length)
  })

  it('Praatplaat-ellips: de kring uitrekken naar de vensterverhouding maakt ’m breder dan hoog, zonder overlap', () => {
    // Spiegel van _ellipsPraatplaat: ná de concentric-plaatsing x/y schalen rond het centrum. In een
    // liggend venster fx>fy → bredere ellips. (De ratio volgt in de browser cy.width()/cy.height() —
    // headless heeft geen container, dus die koppeling is een browsercheck-criterium.)
    const CENTRUM = 'c'
    const cy = cytoscape({
      headless: true,
      style: [{ selector: 'node', style: { width: 140, height: 50 } }],
      elements: [
        { data: { id: CENTRUM } },
        ...Array.from({ length: 17 }, (_, i) => ({ data: { id: 'b' + i } })),
        ...Array.from({ length: 17 }, (_, i) => ({ data: { id: 'e' + i, source: CENTRUM, target: 'b' + i } })),
      ],
    })
    cy.layout({
      name: 'concentric', concentric: (n) => (n.id() === CENTRUM ? 10 : 5), levelWidth: () => 1,
      minNodeSpacing: 25, spacingFactor: 1.0, nodeDimensionsIncludeLabels: true, animate: false,
    }).run()
    const bbCirkel = cy.elements().boundingBox()
    expect(bbCirkel.w / bbCirkel.h).toBeCloseTo(1.0, 0) // concentric ≈ cirkel

    // Uitrekken langs de bredere as (fx = 1.5, fy = 1), rond het centrum — nooit comprimeren.
    const cp = cy.getElementById(CENTRUM).position()
    const fx = 1.5, fy = 1
    cy.nodes().forEach((n) => {
      const p = n.position()
      n.position({ x: cp.x + (p.x - cp.x) * fx, y: cp.y + (p.y - cp.y) * fy })
    })
    const bbEllips = cy.elements().boundingBox()
    expect(bbEllips.w).toBeGreaterThan(bbEllips.h) // ellips: breder dan hoog
    // Geen overlap-regressie: alle posities blijven distinct (uitrekken beweegt knopen alleen uit elkaar).
    const uniek = new Set(cy.nodes().map((n) => `${Math.round(n.position().x)},${Math.round(n.position().y)}`))
    expect(uniek.size).toBe(cy.nodes().length)
  })
})
