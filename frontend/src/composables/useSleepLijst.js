/**
 * useSleepLijst — dé gedeelde bouwsteen voor het herordenen van een lijst door slepen
 * (LI050, besluit Bert: slepen is de ENIGE bediening — geen pijltjes, geen getalveld;
 * dat is een expliciet besluit, geen vergeten alternatief).
 *
 * Wat de bouwsteen draagt: oppakken, loslaten, de nieuwe volgorde berekenen, het bewaren
 * delegeren en de zichtbare bevestiging bij loslaten aftrappen. Meer niet:
 * - hij weet niet WAT er opgeslagen wordt — `herschik(ids)` levert de consument;
 * - hij staat NIET toe dat er tussen twee lijsten gesleept wordt (een vreemd id
 *   resolvet niet binnen de eigen lijst → no-op);
 * - hij beslist NIET wie mag slepen — de consument zet `draggable` alleen op wie het
 *   recht al draagt (beheerder-only erft van de bestaande knip).
 *
 * Waarom een bouwsteen (KERNLES LI038): drie losse implementaties bewaren op drie
 * momenten en bevestigen op drie manieren — dat verschil ziet niemand tot een
 * gebruiker erover valt. Elke volgende sleep-lijst (keuzelijsten = derde consument)
 * haakt hier aan; een eigen nabouw valt om op de bronscan (`sleepLijst.scan.test.js`).
 *
 * Gebruik (HTML5 drag & drop, binnen één lijst):
 *   const sleep = useSleepLijst({
 *     haalIds: () => items.value.map((i) => i.id),
 *     herschik: async (ids) => { ...bewaar per id de nieuwe volgorde... },
 *     naSucces: () => toast.add({ severity: 'success', ... }),   // bevestiging bij loslaten
 *   })
 *   <li draggable="true" @dragstart="sleep.pak(item.id)"
 *       @dragover.prevent @drop.prevent="sleep.laatLos(item.id)">
 */
import { h, ref } from 'vue'

import Icoon from '@/components/Icoon.vue'

/**
 * SleepGreep — de zichtbare handgreep van de sleep-bouwsteen (ADR-056/LI051, besluit
 * Bert): slepen was alleen te ontdekken door met de muis over een rij te gaan; nu
 * draagt élke versleepbare rij een greep die in rust zichtbaar is — gedempt, links.
 *
 * Hoort bij de bouwsteen, niet bij een lijst: elke consument van `useSleepLijst`
 * plaatst hem op zijn versleepbare rijen (de bronscan in `sleepLijst.test.js` dwingt
 * dat af — een sleep-lijst zonder greep faalt de suite). De CONSUMENT gate't op wie
 * mag slepen, met dezelfde conditie als `draggable` — een greep die niets doet is
 * een belofte die het scherm niet waarmaakt.
 *
 * `mee` = kleurt mee met een geselecteerde rij (de selectie blijft één geheel).
 */
export const SleepGreep = {
  name: 'SleepGreep',
  props: { mee: { type: Boolean, default: false } },
  render() {
    return h(
      'span',
      {
        class: ['lk-sleep-greep', this.mee ? 'lk-sleep-greep-mee' : ''],
        'aria-hidden': 'true',
        'data-testid': 'sleep-greep',
      },
      [h(Icoon, { naam: 'greep' })],
    )
  },
}

export function useSleepLijst({ haalIds, herschik, naSucces }) {
  const sleepId = ref(null)

  function pak(id) {
    sleepId.value = id
  }

  async function laatLos(doelId) {
    const bronId = sleepId.value
    sleepId.value = null
    if (bronId == null || bronId === doelId) return
    const ids = [...haalIds()]
    const van = ids.indexOf(bronId)
    const naar = ids.indexOf(doelId)
    // Cross-lijst-drop of onbekend id → no-op (slepen blijft binnen één lijst).
    if (van < 0 || naar < 0) return
    ids.splice(naar, 0, ...ids.splice(van, 1))
    await herschik(ids)
    // Zichtbare bevestiging bij loslaten — een lijst die stil blijft liggen laat de
    // beheerder gokken of het gelukt is.
    naSucces?.()
  }

  function annuleer() {
    sleepId.value = null
  }

  return { sleepId, pak, laatLos, annuleer }
}
