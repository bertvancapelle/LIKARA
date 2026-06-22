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

// ADR-029 — toewijsbare gebruikersrollen bij aanmaak (gesloten lijst; beheerder buiten KILARA).
export const GEBRUIKER_ROL = {
  medewerker: 'Medewerker',
  viewer: 'Viewer',
}

// ADR-029 Fase 3a — audit-spoor: leesbare labels voor handeling + entiteit-type (humanize-fallback
// vangt onbekende/nieuwe waarden op, zodat het spoor nooit "leeg" toont).
export const AUDIT_ACTIE = {
  create: 'Aangemaakt',
  update: 'Gewijzigd',
  delete: 'Verwijderd',
  derive: 'Afgeleid',
}

export const AUDIT_ENTITEIT = {
  applicatie: 'Applicatie',
  component: 'Component',
  component_profiel: 'Componentprofiel',
  contract: 'Contract',
  partij: 'Partij',
  roltoewijzing: 'Roltoewijzing',
  gebruiker_persoon: 'Gebruiker',
  blokkade: 'Blokkade',
  checklistscore: 'Checklistscore',
  component_klaarverklaring: 'Klaarverklaring',
  relatie: 'Relatie',
  plateau: 'Plateau',
  work_package: 'Werkpakket',
  deliverable: 'Deliverable',
  gap: 'Gap',
}

// ADR-029 objecthistorie — NL-labels voor de veldnamen die in de `wijziging`-diff voorkomen.
// Pragmatisch (de gangbare gelogde kolommen); een onbekend veld valt terug op `humaniseer`.
// `*_id`-verwijzingen tonen een leesbaar label; de WAARDE blijft de gelogde id (geen id→naam-
// resolutie in deze slice — dat vergt een lookup per veld; bewuste afbakening).
export const VELD_LABELS = {
  naam: 'Naam',
  omschrijving: 'Omschrijving',
  beschrijving: 'Beschrijving',
  lifecycle_status: 'Levensfase',
  status: 'Status',
  reden: 'Reden',
  hostingmodel: 'Hostingmodel',
  migratiepad: 'Migratiepad',
  complexiteit: 'Complexiteit',
  prioriteit: 'Prioriteit',
  rol: 'Rol',
  aard: 'Aard',
  functietitel: 'Functietitel',
  verklaard_door: 'Verklaard door',
  verklaard_door_sub: 'Verklaard door (sleutel)',
  contractueel_bevestigd: 'Contractueel bevestigd',
  eigenaar_organisatie_id: 'Eigenaar organisatie',
  organisatie_id: 'Organisatie',
  afdeling_id: 'Afdeling',
  mantelcontract_id: 'Mantelcontract',
  leverancier_id: 'Leverancier',
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

// ── ADR-023 ArchiMate-typing (componentcatalogus) ────────────────────────────

// Laag-label voor de componentlijst/-detail (read-only typing uit de catalogus).
export const ARCHIMATE_LAAG = {
  business: 'Business',
  application: 'Applicatie',
  technology: 'Technologie',
  implementation_migration: 'Implementatie & migratie',
}

// ArchiMate-aspect (structuur/gedrag). F-2: cross-element laagprojectie.
export const ARCHIMATE_ASPECT = {
  active: 'Actieve structuur',
  passive: 'Passieve structuur',
  behavior: 'Gedrag',
}

// Element-label (verfijning binnen de laag). Een onbekende waarde valt via de
// humanize-fallback netjes terug (geen lege cel).
export const ARCHIMATE_ELEMENT = {
  application_component: 'Applicatiecomponent',
  system_software: 'Systeemsoftware',
  node: 'Node',
  data_object: 'Data-object',
  business_actor: 'Business actor',
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

// Score → kleur (ÉÉN gedeelde bron, overal consistent): Ja groen · Deels oranje ·
// Nee rood · N.v.t. neutraal/grijs. Tailwind tekstkleur-classes op de --cd-tokens.
// Kleur is nooit de enige drager — de scoretekst (Ja/Deels/Nee) blijft zichtbaar
// (zie ScoreBadge / het checklist-keuzeveld). Onbekend/leeg ⇒ geen kleur.
export const SCORE_KLEUR = {
  ja: 'text-[var(--cd-color-success)]',
  deels: 'text-[var(--cd-color-warning)]',
  nee: 'text-[var(--cd-color-danger)]',
  nvt: 'text-[var(--cd-color-text-muted)]',
}

// Helper: de kleur-class voor een score (leeg/onbekend ⇒ ''). Single source = SCORE_KLEUR.
export function scoreKleur(code) {
  return SCORE_KLEUR[code] ?? ''
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

// ── ADR-027 migratiegereedheid (component-klaarverklaring) — niet-scorend, los van lifecycle ──
export const KLAARVERKLARING_STATUS = {
  klaar: 'Klaar verklaard',
  open: 'Nog niet klaar verklaard',
}

export const KLAARVERKLARING_SEVERITY = {
  klaar: 'success',
  open: 'secondary',
}

// ── ADR-020 contractregister ─────────────────────────────────────────────────

export const CONTRACTTYPE = {
  mantelcontract: 'Mantelcontract',
  deelcontract: 'Deelcontract',
  los_contract: 'Los contract',
}

// ADR-024 slice 2a — aard van een partij (betrokkene). "organisatie_eenheid" = afdeling.
export const PARTIJ_AARD = {
  externe_partij: 'Externe partij',
  organisatie: 'Organisatie',
  organisatie_eenheid: 'Afdeling',
  persoon: 'Persoon',
  burger: 'Burger',
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
