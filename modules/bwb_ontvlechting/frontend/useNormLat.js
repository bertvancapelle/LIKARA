/**
 * useNormLat — ADR-052 slice 4c (besluiten 19/21). Eén leesbron voor "staat dit feit op de lat?".
 *
 * Leest de norm-definitie (`GET /component-normen` → [{feit, verplicht, …}]) — dezelfde bron die
 * slice 4a/4b lezen; géén tweede telling. Het scherm laadt bij mount en `provide`t `verplichtPerFeit`;
 * `VeldUitleg` injecteert die en beslist zélf (op `norm-feit`) of de aanduiding verschijnt — zo draagt
 * elk feit precies ÉÉN aanduiding (besluit 21). De aanduiding hangt aan de NORM, niet aan of het feit
 * is ingevuld (een regel, geen status), en beweegt mee zodra de beheerder de lat verzet (volgende load).
 */
import { ref } from 'vue'
import { api } from '@/api'

export function useNormLat() {
  const verplichtPerFeit = ref({})

  async function laad() {
    try {
      const defs = await api.componentNormen.definitie()
      verplichtPerFeit.value = Object.fromEntries((defs || []).map((d) => [d.feit, !!d.verplicht]))
    } catch {
      verplichtPerFeit.value = {} // norm niet leesbaar → geen aanduiding (fail-safe, geen ruis)
    }
  }

  return { verplichtPerFeit, laad }
}
