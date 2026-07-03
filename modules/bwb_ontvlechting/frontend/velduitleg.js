// Centrale, ontwikkelaar-beheerde veld-uitleg — naast labels.js, bereikbaar vanuit beide
// frontends via de `@modules`-alias (één bron, geen kopie per module). Houdt labels.js slank.
//
// - VELD_UITLEG: gesleuteld op veld-id (spiegelt VELD_LABELS in labels.js) → { uitleg, vuistregel? }.
//   Veld-niveau uitleg is de framing + vuistregel; geldt ongeacht welke opties er zijn.
// - OPTIE_UITLEG: gesleuteld op [set-naam][optie-key] (hergebruikt bestaande optie-keys uit
//   labels.js/catalogi) → discriminatie-regel per optie. Optioneel; alleen waar opties echt
//   discrimineren. Een ontbrekende optie-tooltip is géén fout — alleen tijdelijk geen extra uitleg.
//
// Nette degradatie: de accessors geven `null`/`[]` bij een ontbrekende sleutel — nooit een throw,
// nooit een geforceerde lege popover.

import { humaniseer } from './labels'

export const VELD_UITLEG = {
  // Component — Rol (ADR-028). Slice 1 referentie.
  rol: {
    uitleg:
      'De rol beantwoordt: wat is de functie van dit component in het gegevenslandschap — ' +
      'werken er mensen in, is het een gegevensbron, of verbindt het alleen?',
    vuistregel:
      'Werken er mensen in → interne applicatie. Komt er data uit binnen de organisatie → ' +
      'interne dataprovider. Komt de data van buiten → externe dataprovider. Verbindt het alleen → koppelvlak.',
  },

  // Component — BIV (ADR-028), inline-modus. Gedeelde framing, per as toegespitst.
  biv_beschikbaarheid: {
    uitleg:
      'Beschikbaarheid: hoe erg is het als dit component uitvalt of onbereikbaar is? Kies een ' +
      'niveau; leeg laten telt als niet-geclassificeerd en levert een signaal.',
    vuistregel:
      'Laag = beperkte impact · Midden = merkbare impact op de organisatie · Hoog = grote impact ' +
      'op burgers, continuïteit of een wettelijke plicht.',
  },
  biv_integriteit: {
    uitleg:
      'Integriteit: hoe erg is het als de gegevens in dit component onjuist of ongemerkt gewijzigd zijn?',
    vuistregel:
      'Laag = beperkte impact · Midden = merkbare impact op de organisatie · Hoog = grote impact ' +
      'op burgers, continuïteit of een wettelijke plicht.',
  },
  biv_vertrouwelijkheid: {
    uitleg:
      'Vertrouwelijkheid: hoe erg is het als onbevoegden inzage krijgen in de gegevens van dit component?',
    vuistregel:
      'Laag = beperkte impact · Midden = merkbare impact op de organisatie · Hoog = grote impact ' +
      'op burgers, continuïteit of een wettelijke plicht.',
  },

  // Component — Type. Bewust géén OPTIE_UITLEG → bewijst nette degradatie (alleen veld-uitleg).
  componenttype: {
    uitleg:
      'Het componenttype bepaalt hoe LIKARA dit component behandelt: of het op volledigheid wordt ' +
      'beoordeeld, en hoe het op de kaart verschijnt. Na de eerste registratie ligt het type vast — ' +
      'kies het bewust.',
  },
}

export const OPTIE_UITLEG = {
  // Set 'componentrol' — de vier rollen discrimineren; sleutel op de optie-keys (ADR-028).
  componentrol: {
    interne_applicatie:
      'Een eigen systeem waar de organisatie zelf mee werkt — met gebruikers en functionaliteit, ' +
      'geen puur doorgeefpunt. Standaardkeuze als geen van de andere beter past.',
    interne_dataprovider:
      'Een eigen bron die vooral gegevens levert aan andere interne systemen, meer dan dat er ' +
      'mensen rechtstreeks in werken.',
    externe_dataprovider:
      'Een bron buiten de eigen organisatie waar gegevens vandaan komen: een basisregistratie ' +
      '(BAG, BRP), een landelijke voorziening of een ketenpartner. De organisatie neemt de data af ' +
      'maar beheert het systeem niet zelf.',
    koppelvlak:
      'Een technische tussenlaag die twee kanten verbindt — adapter, API-gateway of middleware. ' +
      'Geen systeem waar je in werkt en geen echte gegevensbron, maar de verbinding ertussen.',
  },
}

// Veld-niveau uitleg: { uitleg, vuistregel? } of null (ontbrekend = geen extra uitleg).
export function veldUitleg(id) {
  return VELD_UITLEG[id] ?? null
}

// Optie-niveau uitleg voor één optie: string of null (nette degradatie op ontbrekende sleutel).
export function optieUitleg(set, key) {
  return OPTIE_UITLEG[set]?.[key] ?? null
}

// Alle optie-regels van een set als [{ key, label, uitleg }] voor de popover-lijst. Het label
// wordt uit de key gehumaniseerd (geen API-afhankelijkheid). Onbekende set → [] (degradatie).
export function optieUitlegLijst(set) {
  const map = OPTIE_UITLEG[set]
  if (!map) return []
  return Object.entries(map).map(([key, uitleg]) => ({ key, label: humaniseer(key), uitleg }))
}
