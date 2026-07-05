/**
 * Herbruikbare param-filterende `api.partijen.lijst`-mock (LI032 — picker-integratienorm).
 *
 * Waarom: de standaard-mock in scherm-tests geeft een VASTE set terug en negeert de
 * `aard`/`scope`/`organisatie_id`/`zoek`-params. Daardoor faalt een picker die de VERKEERDE bron
 * aanroept (afdelingen i.p.v. organisaties, extern i.p.v. intern, ongescoopt) nooit in een test —
 * de fout komt pas in de browser boven. Deze helper filtert net als de backend, zodat een
 * verkeerde bron/aard/scope meteen door de test valt.
 *
 * Gebruik:
 *   api.partijen.lijst.mockImplementation(partijLijstFake())
 *   // open de organisatie-picker → assert dat ALLEEN organisaties (intern) verschijnen;
 *   // open de afdeling-picker → assert dat ALLEEN afdelingen van de gekozen organisatie verschijnen.
 */

// Kleine, expliciete dataset: twee interne + één externe organisatie, afdelingen per organisatie.
export function maakPartijDataset() {
  return [
    { id: 'org-bvowb', naam: 'BvoWB', aard: 'organisatie', scope: 'intern' },
    { id: 'org-rid', naam: 'RID Rivierenland', aard: 'organisatie', scope: 'intern' },
    { id: 'org-tiel', naam: 'Gemeente Tiel', aard: 'organisatie', scope: 'extern' },
    { id: 'afd-be', naam: 'Beheer & Exploitatie', aard: 'organisatie_eenheid', organisatie_id: 'org-bvowb' },
    { id: 'afd-iv', naam: 'Informatievoorziening', aard: 'organisatie_eenheid', organisatie_id: 'org-bvowb' },
    { id: 'afd-sd', naam: 'Servicedesk', aard: 'organisatie_eenheid', organisatie_id: 'org-rid' },
    { id: 'afd-pa', naam: 'Projecten & Advies', aard: 'organisatie_eenheid', organisatie_id: 'org-rid' },
  ]
}

// Bouwt een `(params) => Promise<{items}>` die filtert op aard/aard_in/scope/organisatie_id/zoek.
export function partijLijstFake(dataset = maakPartijDataset()) {
  return (params = {}) => {
    let items = dataset
    if (params.aard) items = items.filter((p) => p.aard === params.aard)
    if (params.aard_in) items = items.filter((p) => params.aard_in.includes(p.aard))
    if (params.scope) items = items.filter((p) => p.scope === params.scope)
    if (params.organisatie_id) items = items.filter((p) => p.organisatie_id === params.organisatie_id)
    if (params.zoek) {
      const t = String(params.zoek).toLowerCase()
      items = items.filter((p) => p.naam.toLowerCase().includes(t))
    }
    return Promise.resolve({ items, volgende_cursor: null })
  }
}
