/**
 * procesKaartIngang — de ÉNE bouwer van de proces→kaart-handoff (LI037 fase 3, ADR-034 besluit 4).
 *
 * Beide ingangen ("Bekijk op kaart" op ProcesDetail én "Via proces" op het KaartBeginscherm)
 * bouwen hun payload hier: gegeven een (deel)proces klimt de bouwer cyclus-veilig naar het
 * HOOFDPROCES (`ouder_id`-keten, visited-set) en verzamelt de vervullende componenten van de
 * VOLLEDIGE boom (subboom-rollup + de eigen regels van de wortel — dezelfde leespaden als de
 * proces-schermen; geen eigen boom-definitie). De kaart opent daarmee exact het beeld dat een
 * component-ingang ook zou geven (de fase-1-subboom-projectie doet de rest), in Lagen, neutraal,
 * met de herkomst benoemd.
 *
 * Retour: `{ componentIds, weergave: 'lagen', procesIngang: { wortelId, wortelNaam, herkomstId,
 * herkomstNaam } }` — `herkomst*` is null wanneer de gebruiker op het hoofdproces zelf instapte.
 * `componentIds` kan leeg zijn (een boom zonder enig ondersteunend systeem): de aanroeper toont
 * dan een rustige melding i.p.v. een lege kaart.
 */
export async function bouwProcesKaartHandoff(api, procesId) {
  const gekozen = await api.processen.haal(procesId)
  // Klim naar de wortel — visited-set: een leestraversal mag nooit kunnen hangen.
  const bezocht = new Set([gekozen.id])
  let wortel = gekozen
  while (wortel.ouder_id && !bezocht.has(wortel.ouder_id)) {
    bezocht.add(wortel.ouder_id)
    wortel = await api.processen.haal(wortel.ouder_id)
  }
  // Vervullers van de hele boom: doorgerolde subboom-regels + de eigen regels van de wortel
  // (de rollup sluit die laatste bewust uit — zie procesvervulling_service.rollup_voor_proces).
  const [rollup, eigen] = await Promise.all([
    api.processen.rollup(wortel.id),
    api.procesvervullingen.lijst({ proces_id: wortel.id }),
  ])
  const componentIds = [...new Set([
    ...(rollup || []).map((r) => String(r.component_id)),
    ...(eigen || []).map((r) => String(r.component_id)),
  ])]
  const opWortel = String(wortel.id) === String(gekozen.id)
  return {
    componentIds,
    weergave: 'lagen',
    procesIngang: {
      wortelId: String(wortel.id),
      wortelNaam: wortel.naam,
      herkomstId: opWortel ? null : String(gekozen.id),
      herkomstNaam: opWortel ? null : gekozen.naam,
    },
  }
}
