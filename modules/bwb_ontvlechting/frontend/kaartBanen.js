// LI046 / ADR-054-vervolg — HOEDANIGHEID + BAAN-VERDELING (de zuivere beslissing; de render leeft
// in LandschapskaartView). "Wat je niet ziet, kun je niet aanklikken": lopen er tussen twee knopen
// meerdere relaties, dan krijgt ELKE hoedanigheid een eigen baan, zodat ze niet op dezelfde plek
// vallen. Binnen dezelfde hoedanigheid telt een teller (zoals flow al deed met "N×").
//
// STRUCTUREEL, geen per-ring-afspraak: de fan wordt puur op het KNOOPPAAR berekend (ring-agnostisch),
// en de hoedanigheid is DEFAULT het relatietype zelf → een nieuwe soort/ring erft het gedrag zonder
// dat hier een tak bij hoeft. De enige samenvatting is `roltoewijzing` → één 'beheer'-baan (de rollen
// blijven leesbaar in het label / de popup): functioneel- en technisch beheer zijn losse feiten, geen
// "beheer · 2×" dat wist wie wat doet, maar ook geen elf banen die onleesbaar waaieren.

// ≤ dit aantal beheerrollen → toon de namen in het label; daarboven → teller "N beheerrollen".
// Grens op labelbreedte: twee rol-namen ("Functioneel beheer + Technisch beheer") passen nog leesbaar
// op een hover-label; drie of meer worden te breed. Het volledige lijstje blijft in de klik-popup.
export const BEHEER_LABEL_MAX = 2

// px control-point-afstand per baan (symmetrische waaier). Browsercheck-afstembaar.
export const BAAN_STAP = 22

// Elke relatiesoort is zijn eigen hoedanigheid; alle beheerrollen vallen samen onder 'beheer'.
export function hoedanigheidVan(relatietype) {
  return relatietype === 'roltoewijzing' ? 'beheer' : relatietype
}

// Het leesbare baan-label van een gegroepeerde hoedanigheid.
//  - beheer: de rol-namen (≤ BEHEER_LABEL_MAX) óf een teller "N beheerrollen";
//  - overig: het bestaande edge-label van het eerste lid (flow bevat daar al zijn eigen "N×").
export function baanLabel(groep) {
  if (groep.hoedanigheid === 'beheer') {
    const rollen = groep.leden.map((l) => l.label).filter(Boolean)
    return rollen.length <= BEHEER_LABEL_MAX ? rollen.join(' + ') : `${rollen.length} beheerrollen`
  }
  return groep.leden[0]?.label || ''
}

// Zuivere beslissing (LI044-patroon: test de BESLISSING, niet de render). Neemt de logische edges
// (met `bron_id`, `doel_id`, `relatietype`, `label`) en geeft per hoedanigheid-groep een baan-plek:
// { bron_id, doel_id, hoedanigheid, leden[], baan, banen, cpd }. Twee hoedanigheden tussen hetzelfde
// (ongeordende) paar krijgen NOOIT dezelfde `cpd` in dezelfde geometrische richting → geen overlap.
export function baanVerdeling(edges, stap = BAAN_STAP) {
  // 1) Groepeer per (bron, doel, hoedanigheid): beheerrollen + meervoudige flows vallen samen.
  const groepen = new Map()
  for (const e of edges || []) {
    const h = hoedanigheidVan(e.relatietype)
    const k = `${e.bron_id} ${e.doel_id} ${h}`
    if (!groepen.has(k)) groepen.set(k, { bron_id: e.bron_id, doel_id: e.doel_id, hoedanigheid: h, leden: [] })
    groepen.get(k).leden.push(e)
  }
  // 2) Verdeel de groepen per ONGEORDEND paar over banen (stabiele volgorde op hoedanigheid).
  const perPaar = new Map()
  for (const g of groepen.values()) {
    const s = String(g.bron_id)
    const t = String(g.doel_id)
    const pk = s < t ? `${s} ${t}` : `${t} ${s}`
    if (!perPaar.has(pk)) perPaar.set(pk, [])
    perPaar.get(pk).push(g)
  }
  const uit = []
  for (const groep of perPaar.values()) {
    groep.sort((x, y) => (x.hoedanigheid < y.hoedanigheid ? -1 : x.hoedanigheid > y.hoedanigheid ? 1 : 0))
    const n = groep.length
    groep.forEach((g, i) => {
      const basis = (i - (n - 1) / 2) * stap // symmetrische waaier rond de rechte lijn
      // Richting-correctie: cytoscape's control-point-distance is relatief aan bron→doel. Door de
      // afstand te spiegelen voor een edge waarvan de bron NIET de canonieke (kleinste) id is, komt
      // ELKE baan op een vaste geometrische plek — óók de tegengestelde richting (A→B vs B→A) valt
      // zo op eigen banen i.p.v. op elkaar.
      const richting = String(g.bron_id) < String(g.doel_id) ? 1 : -1
      uit.push({ ...g, baan: i, banen: n, cpd: basis * richting })
    })
  }
  return uit
}
