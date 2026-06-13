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

// `checklist_compleet` is transient (ADR-013 B4) en wordt nooit als ruststatus
// getoond; valt via de humanize-fallback op een generiek label terug.
export const LIFECYCLE = {
  concept: 'Concept',
  in_inventarisatie: 'In inventarisatie',
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
  geblokkeerd: 'danger',
  migratieklaar: 'success',
}

// ── Child-entiteiten ─────────────────────────────────────────────────────────

export const DATATYPE_CATEGORIE = {
  gestructureerd_db: 'Gestructureerde database',
  documenten: 'Documenten',
  email: 'E-mail',
  spatial: 'Spatial / geo',
  binair: 'Binair',
  combinatie: 'Combinatie',
}

export const KOPPELRICHTING = {
  eenrichting: 'Eenrichting',
  tweerichting: 'Tweerichting',
}

export const KOPPELPROTOCOL = {
  api: 'API',
  bestandsuitwisseling: 'Bestandsuitwisseling',
  database_link: 'Database-link',
  middleware: 'Middleware',
  overig: 'Overig',
}

export const IMPACT_VERBREKING = {
  laag: 'Laag',
  midden: 'Midden',
  hoog: 'Hoog',
  kritiek: 'Kritiek',
}

export const IMPACT_SEVERITY = {
  laag: 'info',
  midden: 'warn',
  hoog: 'warn',
  kritiek: 'danger',
}

// ── Lifecycle (Checklistscore/Blokkade) ──────────────────────────────────────

export const SCORE = {
  ja: 'Ja',
  deels: 'Deels',
  nee: 'Nee',
  nvt: 'N.v.t.',
}

export const SCORE_SEVERITY = {
  ja: 'success',
  deels: 'warn',
  nee: 'danger',
  nvt: 'info',
}

export const BLOKKADE_STATUS = {
  open: 'Open',
  in_behandeling: 'In behandeling',
  opgelost: 'Opgelost',
}

export const BLOKKADE_STATUS_SEVERITY = {
  open: 'danger',
  in_behandeling: 'warn',
  opgelost: 'success',
}

// ── ADR-020 contractregister ─────────────────────────────────────────────────

export const CONTRACTTYPE = {
  mantelcontract: 'Mantelcontract',
  deelcontract: 'Deelcontract',
  los_contract: 'Los contract',
}

export const CONTRACTTYPE_SEVERITY = {
  mantelcontract: 'info',
  deelcontract: 'warn',
  los_contract: 'success',
}

// Register-foutcodes → leesbare context-melding (de backend levert ook `bericht`;
// dit is de fallback/samenvatting voor Toast/in-form).
export const REGISTER_FOUT = {
  ONGELDIGE_MANTEL: 'Het gekozen mantelcontract is ongeldig voor dit type.',
  LEVERANCIER_MISMATCH: 'Een deelcontract erft de leverancier van zijn mantel.',
  MANTEL_IN_GEBRUIK: 'Dit mantelcontract heeft deelcontracten; wijziging niet toegestaan.',
  IN_GEBRUIK: 'Dit record is nog in gebruik en kan niet worden verwijderd.',
  KOPPELING_BESTAAT: 'Deze applicatie is al aan dit contract gekoppeld.',
  ONGELDIGE_OPTIE: 'De gekozen optie is onbekend of niet actief.',
  // ADR-021 (CD054) — componenten + structuurgraaf.
  GEBRUIK_APPLICATIE_PAD: 'Componenten van het type applicatie beheer je via de applicatie zelf.',
  SUBTYPE_BESCHERMD: 'Dit component is een applicatie-subtype en wordt via de applicatie beheerd.',
  // ADR-022 Fase C — toestand-gebaseerde type-lock (fallback; de server levert een
  // bericht met de concrete tellingen).
  SUBTYPE_HEEFT_DATA: 'Type vergrendeld: dit component bevat al gegevens en kan niet van type wisselen.',
  ZELFVERWIJZING: 'Een component kan geen structuurrelatie met zichzelf hebben.',
  RELATIE_BESTAAT: 'Deze structuurrelatie bestaat al.',
}
