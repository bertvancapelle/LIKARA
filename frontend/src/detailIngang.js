// De ENE ingang naar een detailscherm (LI046, besluit Bert: "je landt bij het feit
// waar je vandaan kwam"). Elke navigatie naar een detailscherm — mét of zónder
// aanleiding — bouwt zijn route hier; nergens anders leeft een detail-route-naam.
// De dekkingsscan (tests/detailIngang.scan.test.js) faalt op elk bestand dat er
// tóch een eigen literal op nahoudt.
//
// - `objectType` is de canonieke element-/objectsoort ('component', 'contract',
//   'partij', …). Een soort zónder detailscherm geeft `null` terug: geen
//   route-belofte zonder landingsplek (besluit 2). De aanroeper toont dan geen link.
// - `bedrijfsfunctie` heeft geen detailscherm (besluit 4): de route opent de
//   bedrijfsfunctielijst met focus op die functie (`?focus=<id>`).
// - De aanleiding leeft in de URL (deelbaar, herstelbaar, overleeft F5) en vertaalt
//   naar de bestaande landingsplekken van het detailscherm: `tab` · `cat` ·
//   `markeer` (checklistvraag) · `bewerk` (overlay). Een onbekende sleutel is een
//   LUIDE fout (zelfde conventie als `_filterQuery` in api.js) — een aanleiding kan
//   niet stil wegvallen of stil een niet-bestaande landing beloven.

const ROUTE_PER_TYPE = {
  component: 'component-detail',
  contract: 'contract-detail',
  partij: 'partij-detail',
  plateau: 'plateau-detail',
  gap: 'gap-detail',
  work_package: 'work-package-detail',
  deliverable: 'deliverable-detail',
}

// Slice 1: de bestaande query-taal van ComponentDetail. Slice 2: het veld-anker (`veld`).
const AANLEIDING_SLEUTELS = new Set(['tab', 'cat', 'markeer', 'bewerk', 'veld'])

// LI046 slice 2 (besluit B) — velden op het Overzicht met een eerlijke landing (markering +
// bewerkknop ernaast). Een onbekend veld is een LUIDE fout: liever geen link dan een link
// die nergens op uitkomt — een producent (open-punten-overzicht) merkt het dan direct.
export const VELD_ANKERS = Object.freeze(['eigenaar', 'biv', 'levensfase', 'bedoeling', 'beschrijving'])

export function detailRoute(objectType, id, aanleiding = null) {
  if (id == null) return null
  if (objectType === 'bedrijfsfunctie') {
    return { name: 'bedrijfsfunctie-lijst', query: { focus: String(id) } }
  }
  const name = ROUTE_PER_TYPE[objectType]
  if (!name) return null
  const route = { name, params: { id } }
  if (aanleiding != null) {
    const query = {}
    for (const [sleutel, waarde] of Object.entries(aanleiding)) {
      if (!AANLEIDING_SLEUTELS.has(sleutel)) {
        throw new Error(`detailIngang: onbekende aanleiding-sleutel '${sleutel}'`)
      }
      if (waarde === undefined || waarde === null || waarde === '') continue
      if (sleutel === 'veld' && !VELD_ANKERS.includes(String(waarde))) {
        throw new Error(`detailIngang: onbekend veld-anker '${waarde}' (geen landingsplek)`)
      }
      query[sleutel] = String(waarde)
    }
    if (Object.keys(query).length) route.query = query
  }
  return route
}
