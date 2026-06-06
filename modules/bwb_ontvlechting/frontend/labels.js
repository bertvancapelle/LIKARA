// Nederlandse labels voor de Applicatie-enums — frontend-presentatiezaak.
// De backend levert alleen de waarden (codes); een waarde zonder expliciet label
// valt terug op een gehumaniseerde code, zodat een nieuwe backend-waarde nooit
// "leeg" in de UI verschijnt.

export function humaniseer(code) {
  if (code == null) return ''
  const tekst = String(code).replace(/_/g, ' ')
  return tekst.charAt(0).toUpperCase() + tekst.slice(1)
}

export function label(map, code) {
  return map[code] ?? humaniseer(code)
}

export const LIFECYCLE = {
  concept: 'Concept',
  in_inventarisatie: 'In inventarisatie',
  checklist_compleet: 'Checklist compleet',
  geblokkeerd: 'Geblokkeerd',
  migratieklaar: 'Migratieklaar',
}

export const HOSTINGMODEL = {
  on_premise: 'On-premise',
  private_cloud: 'Private cloud',
  saas: 'SaaS',
  iaas: 'IaaS',
  paas: 'PaaS',
  hybride: 'Hybride',
  onbekend: 'Onbekend',
}

export const MIGRATIEPAD = {
  lift_and_shift: 'Lift-and-shift',
  herbouw: 'Herbouw',
  vervangen: 'Vervangen',
  uitfaseren: 'Uitfaseren',
  tijdelijk_gedeeld: 'Tijdelijk gedeeld',
  onbekend: 'Onbekend',
}

export const NIVEAU = {
  laag: 'Laag',
  midden: 'Midden',
  hoog: 'Hoog',
}

// Lifecycle-status → Tag-severity (Tag-preset kent info/success/warn/danger).
export const LIFECYCLE_SEVERITY = {
  concept: 'info',
  in_inventarisatie: 'warn',
  checklist_compleet: 'info',
  geblokkeerd: 'danger',
  migratieklaar: 'success',
}
