/**
 * procesBoom — pure boom-layout van de proceszone (LI037 fase 2, ADR-034 §Proces-diepte besluit 2).
 *
 * Berekent per proces-knoop een (rij, kolom)-plek: rij = diepte in de `proces_hierarchie`-boom
 * (wortel = 0), kolommen per boom aaneengesloten (groepering: twee bomen lopen niet in elkaar
 * over — tussen bomen zit één lege kolom). Een ouder staat gecentreerd boven zijn kinderen
 * (midpoint), bladeren krijgen opeenvolgende kolommen. Deterministisch (kinderen/wortels op
 * naam, dan id) en cyclus-veilig (pad-guard — de backend levert geen edge-lussen, maar een
 * leestraversal mag nooit kunnen hangen).
 *
 * Bewust een gedeelde PURE module (geen Vue): de view gebruikt 'm voor de Lagen-posities en
 * `kaartLayout.test.js` borgt met de ÉCHTE cytoscape dat de posities distinct + deterministisch
 * zijn — één definitie, geen test-spiegel die kan driften.
 *
 * @param {Set<string>} ids       zichtbare proces-knoop-ids (de proceszone)
 * @param {Array<{bron: string, doel: string}>} hierEdges  hiërarchie-edges kind→ouder
 * @param {(id: string) => string} naamVan  naam-resolver (sorteersleutel; fallback = id)
 * @returns {{ rij: Map<string, number>, kolom: Map<string, number>, rijen: number, kolommen: number }}
 */
export function procesBoomLayout(ids, hierEdges, naamVan = (id) => String(id)) {
  const rij = new Map()
  const kolom = new Map()
  if (!ids || !ids.size) return { rij, kolom, rijen: 1, kolommen: 1 }

  const ouderVan = new Map()
  const kinderenVan = new Map()
  for (const e of hierEdges || []) {
    if (!ids.has(e.bron) || !ids.has(e.doel) || ouderVan.has(e.bron)) continue
    ouderVan.set(e.bron, e.doel)
    if (!kinderenVan.has(e.doel)) kinderenVan.set(e.doel, [])
    kinderenVan.get(e.doel).push(e.bron)
  }
  const sorteer = (a, b) => (naamVan(a) || '').localeCompare(naamVan(b) || '', 'nl') || String(a).localeCompare(String(b))
  // Wortels = knopen zonder ouder in de zone (incl. losse knopen en de pseudo-wortel bij een
  // datacyclus — de backend geeft de wortel bewust géén eigen hiërarchie-edge).
  const wortels = [...ids].filter((id) => !ouderVan.has(id)).sort(sorteer)

  let volgendeKolom = 0
  let maxRij = 0
  const bezoek = (id, diepte, pad) => {
    if (pad.has(id)) return // cyclus-guard: nooit hangen
    pad.add(id)
    rij.set(id, diepte)
    if (diepte > maxRij) maxRij = diepte
    const ks = (kinderenVan.get(id) || []).filter((k) => !pad.has(k)).sort(sorteer)
    if (!ks.length) {
      kolom.set(id, volgendeKolom)
      volgendeKolom += 1
    } else {
      for (const k of ks) bezoek(k, diepte + 1, pad)
      const xs = ks.map((k) => kolom.get(k)).filter((x) => x != null)
      kolom.set(id, xs.length ? (Math.min(...xs) + Math.max(...xs)) / 2 : (volgendeKolom += 1) - 1)
    }
    pad.delete(id)
  }
  for (const w of wortels) {
    bezoek(w, 0, new Set())
    volgendeKolom += 1 // boom-tussenruimte: de volgende boom begint een kolom verder
  }
  // Vangnet: een knoop die alleen via een (geconstrueerde) cyclus bereikbaar is en geen wortel
  // werd, krijgt alsnog een eigen plek (nooit een gat in de posities).
  for (const id of [...ids].sort(sorteer)) {
    if (!rij.has(id)) {
      rij.set(id, 0)
      kolom.set(id, volgendeKolom)
      volgendeKolom += 2
    }
  }
  return { rij, kolom, rijen: maxRij + 1, kolommen: Math.max(1, volgendeKolom - 1) }
}
