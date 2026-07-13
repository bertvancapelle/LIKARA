/**
 * procesBoom — gedeelde pure proces-boom-opbouw + boom-layout (LI037, ADR-034 §Proces-diepte).
 *
 * Drie exports, één definitie van de boom-semantiek:
 * - `procesBoomStructuur` — de STRUCTUUR (wortels + ouder-/kinderen-maps, deterministisch
 *   gesorteerd op naam→id, cyclus-/dubbele-ouder-guard). Render-agnostisch: de kaart bouwt er
 *   zijn cytoscape-posities op, het Processen-lijstscherm zijn DOM-tree (tree-view gate 1) —
 *   géén derde boom-opbouw ernaast.
 * - `procesBoomLayout` — de kaart-LAYOUT bovenop die structuur: rij = diepte (wortel = 0),
 *   kolommen per boom aaneengesloten met een lege kolom ertussen, ouder gecentreerd boven zijn
 *   kinderen, bladeren op opeenvolgende kolommen.
 * - `procesFocusSet` — de FOCUS-SELECTIE van het proces-only structuurbeeld (LI038): gegeven
 *   een centrum de ouderketen tot de wortel (boven) + de volledige subboom (beneden) + de
 *   zusjes (opzij, zónder hun subbomen). Zelfde structuur-bron, geen tweede boom-definitie.
 * - `procesSubboomSet` — de INZOOM-SCOPE (LI038 gate 3, dubbelklik): uitsluitend het proces
 *   + zijn volledige subboom (géén keten/zusjes — inzoomen perkt écht in).
 *
 * Bewust een gedeelde PURE module (geen Vue/cytoscape-import): `kaartLayout.test.js` borgt met
 * de ÉCHTE cytoscape dat de posities distinct + deterministisch zijn — geen test-spiegel die
 * kan driften.
 *
 * @param {Set<string>} ids       zichtbare proces-knoop-ids (de zone/het register)
 * @param {Array<{bron: string, doel: string}>} hierEdges  hiërarchie-paren kind→ouder
 * @param {(id: string) => string} naamVan  naam-resolver (sorteersleutel; fallback = id)
 */
export function procesBoomStructuur(ids, hierEdges, naamVan = (id) => String(id)) {
  const ouderVan = new Map()
  const kinderenVan = new Map()
  if (!ids || !ids.size) return { wortels: [], ouderVan, kinderenVan }
  for (const e of hierEdges || []) {
    if (!ids.has(e.bron) || !ids.has(e.doel) || ouderVan.has(e.bron)) continue
    ouderVan.set(e.bron, e.doel)
    if (!kinderenVan.has(e.doel)) kinderenVan.set(e.doel, [])
    kinderenVan.get(e.doel).push(e.bron)
  }
  const sorteer = (a, b) => (naamVan(a) || '').localeCompare(naamVan(b) || '', 'nl') || String(a).localeCompare(String(b))
  for (const lijst of kinderenVan.values()) lijst.sort(sorteer)
  // Wortels = knopen zonder ouder in de zone (incl. losse knopen en de pseudo-wortel bij een
  // datacyclus — de backend geeft de wortel bewust géén eigen hiërarchie-edge).
  const wortels = [...ids].filter((id) => !ouderVan.has(id)).sort(sorteer)
  return { wortels, ouderVan, kinderenVan }
}

/**
 * meervoudBoomStructuur — de MEERVOUDIGE-OUDERS-variant (ADR-044: de bedrijfsfunctieboom
 * leeft in plaatsingen; één functie kan onder meerdere ouders staan, alle gelijkwaardig).
 *
 * Zelfde module, zelfde sorteer-/determinisme-semantiek als `procesBoomStructuur` — maar
 * ZONDER de dubbele-ouder-guard: élke (kind, ouder)-plaatsing telt (dubbele identieke
 * paren worden ontdubbeld). `procesBoomStructuur` blijft ongewijzigd de bron voor de
 * één-ouder-werelden (processen, kaart-proceszone) waar één ouder de waarheid ís.
 *
 * Let op voor lopers over deze structuur: het is een DAG — een kind kan onder meerdere
 * ouders (en dus meermaals in een render) verschijnen. Elke traversal draagt zijn eigen
 * pad-guard zodat een (niet zou mogen bestaan) datakring nooit hangt.
 *
 * @param {Set<string>} ids
 * @param {Array<{bron: string, doel: string}>} hierEdges  plaatsings-paren kind→ouder
 * @param {(id: string) => string} naamVan
 * @returns {{ wortels: string[], oudersVan: Map<string, string[]>, kinderenVan: Map<string, string[]> }}
 */
export function meervoudBoomStructuur(ids, hierEdges, naamVan = (id) => String(id)) {
  const oudersVan = new Map()
  const kinderenVan = new Map()
  if (!ids || !ids.size) return { wortels: [], oudersVan, kinderenVan }
  const gezien = new Set()
  for (const e of hierEdges || []) {
    if (!ids.has(e.bron) || !ids.has(e.doel) || e.bron === e.doel) continue
    const paar = `${e.bron}\u0000${e.doel}`
    if (gezien.has(paar)) continue
    gezien.add(paar)
    if (!oudersVan.has(e.bron)) oudersVan.set(e.bron, [])
    oudersVan.get(e.bron).push(e.doel)
    if (!kinderenVan.has(e.doel)) kinderenVan.set(e.doel, [])
    kinderenVan.get(e.doel).push(e.bron)
  }
  const sorteer = (a, b) => (naamVan(a) || '').localeCompare(naamVan(b) || '', 'nl') || String(a).localeCompare(String(b))
  for (const lijst of kinderenVan.values()) lijst.sort(sorteer)
  for (const lijst of oudersVan.values()) lijst.sort(sorteer)
  const wortels = [...ids].filter((id) => !oudersVan.has(id)).sort(sorteer)
  return { wortels, oudersVan, kinderenVan }
}

/**
 * Boom-layout van de kaart-proceszone: per knoop een (rij, kolom)-plek.
 * @returns {{ rij: Map<string, number>, kolom: Map<string, number>, rijen: number, kolommen: number }}
 */
export function procesBoomLayout(ids, hierEdges, naamVan = (id) => String(id)) {
  const rij = new Map()
  const kolom = new Map()
  if (!ids || !ids.size) return { rij, kolom, rijen: 1, kolommen: 1 }

  const { wortels, kinderenVan } = procesBoomStructuur(ids, hierEdges, naamVan)
  const sorteer = (a, b) => (naamVan(a) || '').localeCompare(naamVan(b) || '', 'nl') || String(a).localeCompare(String(b))

  let volgendeKolom = 0
  let maxRij = 0
  const bezoek = (id, diepte, pad) => {
    if (pad.has(id)) return // cyclus-guard: nooit hangen
    pad.add(id)
    rij.set(id, diepte)
    if (diepte > maxRij) maxRij = diepte
    // Kinderen zijn al deterministisch gesorteerd in de structuur; de pad-filter behoudt de orde.
    const ks = (kinderenVan.get(id) || []).filter((k) => !pad.has(k))
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

/**
 * Focus-selectie voor het proces-only structuurbeeld (LI038 gate 1): welke proces-knopen
 * horen bij "dit proces centraal"? Boven = de ouderketen tot de wortel, beneden = de
 * volledige subboom van het centrum, opzij = de zusjes (kinderen van dezelfde directe
 * ouder) — bewust ZONDER de subbomen van die zusjes (opzij is context, geen onderwerp).
 * Een wortel-centrum heeft geen ouder en dus geen zusjes (andere wortels horen er niet bij).
 * Cyclus-veilig (visited-guards); een onbekend centrum geeft een lege set.
 *
 * @param {string} centrumId
 * @param {Set<string>} ids       alle proces-ids (de volledige set)
 * @param {Array<{bron: string, doel: string}>} hierEdges  hiërarchie-paren kind→ouder
 * @param {(id: string) => string} naamVan
 * @returns {Set<string>} de zichtbare focus-ids (leeg als het centrum niet bestaat)
 */
/**
 * Inzoom-scope voor het proces-only structuurbeeld (LI038 gate 3): het proces zelf + zijn
 * volledige subboom (alle niveaus), zónder ouderketen of zusjes — de dubbelklik perkt écht
 * in. Werkt ook op een blad (scope = alleen het proces zelf). Cyclus-veilig (visited-guard);
 * een onbekend centrum geeft een lege set.
 *
 * @param {string} centrumId
 * @param {Set<string>} ids       alle proces-ids (de volledige set)
 * @param {Array<{bron: string, doel: string}>} hierEdges  hiërarchie-paren kind→ouder
 * @param {(id: string) => string} naamVan
 * @returns {Set<string>}
 */
export function procesSubboomSet(centrumId, ids, hierEdges, naamVan = (id) => String(id)) {
  if (!centrumId || !ids || !ids.has(centrumId)) return new Set()
  const { kinderenVan } = procesBoomStructuur(ids, hierEdges, naamVan)
  const scope = new Set([centrumId])
  let frontier = [centrumId]
  while (frontier.length) {
    const volgende = []
    for (const p of frontier) {
      for (const k of kinderenVan.get(p) || []) {
        if (!scope.has(k)) {
          scope.add(k)
          volgende.push(k)
        }
      }
    }
    frontier = volgende
  }
  return scope
}

export function procesFocusSet(centrumId, ids, hierEdges, naamVan = (id) => String(id)) {
  if (!centrumId || !ids || !ids.has(centrumId)) return new Set()
  const { ouderVan, kinderenVan } = procesBoomStructuur(ids, hierEdges, naamVan)
  const focus = new Set([centrumId])
  // Boven — ouderketen tot de wortel (visited-guard: een datakring mag nooit hangen).
  let cur = ouderVan.get(centrumId)
  while (cur != null && !focus.has(cur)) {
    focus.add(cur)
    cur = ouderVan.get(cur)
  }
  // Opzij — zusjes: de kinderen van de directe ouder (het centrum zit er al in).
  const ouder = ouderVan.get(centrumId)
  if (ouder != null) for (const z of kinderenVan.get(ouder) || []) focus.add(z)
  // Beneden — de volledige subboom van het centrum (BFS, visited-guard). Bewust alléén
  // vanaf het centrum: zusjes-subbomen blijven buiten beeld.
  const bezocht = new Set([centrumId])
  let frontier = [centrumId]
  while (frontier.length) {
    const volgende = []
    for (const p of frontier) {
      for (const k of kinderenVan.get(p) || []) {
        if (!bezocht.has(k)) {
          bezocht.add(k)
          focus.add(k)
          volgende.push(k)
        }
      }
    }
    frontier = volgende
  }
  return focus
}
