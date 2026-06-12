<script setup>
/**
 * ChecklistscoreSectie — inline scoringslijst over de 89 ChecklistVragen.
 *
 * Join client-side op CODE: ChecklistVraag.code ↔ Checklistscore (via
 * checklistvraag_id ↔ vraag.id, ADR-022 Fase A). Per vraag een ja/deels/nee/nvt-
 * keuze die direct opslaat: nog niet gescoord → maak({component_id, checklistvraag_id, score});
 * al gescoord → werkBij(scoreId, {score}). Per-rij inline feedback i.p.v. 89
 * toasts. Elke geslaagde score kan een blokkade laten ontstaan/oplossen en de
 * lifecycle herberekenen (backend) → de sectie emit 'gewijzigd' zodat de ouder
 * de lifecycle-indicator én de blokkadelijst herlaadt.
 *
 * Uitklaprij (CD026): per vraag een toggle die `bevinding`/`eigenaar`/`actie`
 * (kolommen op Checklistscore) toont en — voor medewerker/beheerder — bewerkbaar
 * maakt met één expliciete "Opslaan"-knop. Die slaat de drie velden samen op via
 * werkBij(id, {bevinding, eigenaar, actie}) — **zonder `score`**, zodat de
 * score-afgeleide lifecycle/blokkade ongemoeid blijft (ADR-013/016). De drie
 * velden zijn pas bewerkbaar zodra de vraag gescoord is (er moet een
 * Checklistscore-rij zijn om op te PATCHen).
 */
import { computed, reactive, ref } from 'vue'
import { useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { SCORE, label } from '../labels'

const props = defineProps({
  applicatieId: { type: String, required: true },
  // CD022: filtert de getoonde vragen op één checklist-categorie (categorie_nr).
  // null = alle vragen (zelfstandig gebruik / volledige lijst).
  categorieNr: { type: Number, default: null },
})
const emit = defineEmits(['gewijzigd'])
const auth = useAuthStore()
const toast = useToast()

const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const vragen = ref([])
const scoreMap = reactive({}) // vraag_code -> { id, score, bevinding, eigenaar, actie }
const opties = ref({ score: [] })
const laden = ref(false)
const fout = ref(null)
const rijStatus = reactive({}) // vraag_code -> 'bezig' | 'opgeslagen' | 'fout'
const rijFout = reactive({}) // vraag_code -> melding

// Uitklaprij-state (CD026)
const uitgeklapt = reactive({}) // vraag_code -> bool
const bewerk = reactive({}) // vraag_code -> { bevinding, eigenaar, actie } (lokale buffer)
const veldStatus = reactive({}) // vraag_code -> 'bezig' | 'opgeslagen' | 'fout'
const veldFout = reactive({}) // vraag_code -> melding

const aantalVragen = computed(() => vragen.value.length)
const aantalGescoord = computed(() => Object.keys(scoreMap).length)

// CD022: alleen de vragen van de actieve categorie tonen (null = alle), oplopend
// op code. De voortgang-tellers blijven bewust GLOBAAL (alle 89 vragen).
const zichtbareVragen = computed(() => {
  const lijst =
    props.categorieNr == null
      ? vragen.value
      : vragen.value.filter((v) => v.categorie_nr === props.categorieNr)
  return [...lijst].sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }))
})

// Afgeleide categorie-lijst (nr + naam, oplopend) voor de tab-labels in de ouder —
// single source uit de geladen vragen, geen seed-namen in de frontend dupliceren.
const categorieen = computed(() => {
  const perNr = new Map()
  for (const v of vragen.value) if (!perNr.has(v.categorie_nr)) perNr.set(v.categorie_nr, v.categorie_naam)
  return [...perNr.entries()].sort((a, b) => a[0] - b[0]).map(([nr, naam]) => ({ nr, naam }))
})

function _toastFout(e) {
  const per = { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

// Sla de volledige score-rij op in de lokale map (de respons/lijst draagt óók
// bevinding/eigenaar/actie — single source, voorkomt verlies van die velden bij
// een score-wijziging).
function _zetScore(code, r) {
  scoreMap[code] = {
    id: r.id,
    score: r.score,
    bevinding: r.bevinding ?? '',
    eigenaar: r.eigenaar ?? '',
    actie: r.actie ?? '',
    antwoord_waarde: r.antwoord_waarde ?? null,
  }
}

// ADR-022 Fase A: scores dragen `checklistvraag_id` (UUID), niet meer `vraag_code`.
// De sectie blijft per CODE redeneren (display/join), dus we mappen id → code via
// de geladen vragenlijst (single source).
function _codeVoorVraagId(id) {
  return vragen.value.find((q) => q.id === id)?.code
}

function _vulScoreMap(scores) {
  for (const k of Object.keys(scoreMap)) delete scoreMap[k]
  for (const s of scores) {
    const code = _codeVoorVraagId(s.checklistvraag_id)
    if (code) _zetScore(code, s)
  }
}

async function _laadScores() {
  // Vereist dat `vragen` al geladen is (id → code-resolutie); zie `laad()`.
  const p = await api.checklistscores.lijst({ applicatieId: props.applicatieId, limit: 100 })
  _vulScoreMap(p.items)
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    // Vragen + scores parallel ophalen; scoreMap pas vullen NÁ het zetten van
    // `vragen` (id → code-join vereist de vragenlijst).
    const [vragenResp, scoresPagina] = await Promise.all([
      api.checklistvragen.lijst(),
      api.checklistscores.lijst({ applicatieId: props.applicatieId, limit: 100 }),
      (async () => {
        if (!opties.value.score.length) opties.value = await api.checklistscores.opties()
      })(),
    ])
    vragen.value = vragenResp
    _vulScoreMap(scoresPagina.items)
  } catch (e) {
    fout.value = e?.message || 'Laden van de checklist mislukt.'
  } finally {
    laden.value = false
  }
}

function huidigeScore(code) {
  return scoreMap[code]?.score ?? ''
}

function isGescoord(code) {
  return !!scoreMap[code]?.id
}

// ── ADR-019: gestructureerd antwoordveld (CD029) ─────────────────────────────

function vraagVan(code) {
  return vragen.value.find((q) => q.code === code)
}

function antwoordType(code) {
  return vraagVan(code)?.antwoordtype ?? 'geen'
}

// Alleen ACTIEVE opties zijn kiesbaar; gedeactiveerde komen wél mee in vraag.opties
// (label-resolutie van een eerder gekozen, inmiddels inactieve sleutel).
function actieveOpties(code) {
  return (vraagVan(code)?.opties ?? []).filter((o) => o.actief)
}

function toggleOptie(code, sleutel) {
  const arr = bewerk[code].antwoord_opties
  const i = arr.indexOf(sleutel)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(sleutel)
}

// Bouw de antwoord_waarde-envelope uit de lokale buffer naar het type; leeg → null.
function _antwoordEnvelope(code) {
  const b = bewerk[code]
  const t = antwoordType(code)
  if (t === 'enkelvoudige_keuze') return b.antwoord_optie ? { optie: b.antwoord_optie } : null
  if (t === 'meerkeuze') return b.antwoord_opties.length ? { opties: [...b.antwoord_opties] } : null
  if (t === 'getal') {
    const n = Number.parseInt(b.antwoord_getal, 10)
    return Number.isInteger(n) && n >= 1 ? { getal: n } : null
  }
  return null
}

async function onScoreChange(code, nieuweScore) {
  if (!nieuweScore) return
  rijStatus[code] = 'bezig'
  delete rijFout[code]
  try {
    const bestaand = scoreMap[code]
    if (bestaand) {
      const r = await api.checklistscores.werkBij(bestaand.id, { score: nieuweScore })
      _zetScore(code, r)
    } else {
      try {
        const r = await api.checklistscores.maak({
          component_id: props.applicatieId,
          checklistvraag_id: vraagVan(code)?.id,
          score: nieuweScore,
        })
        _zetScore(code, r)
      } catch (e) {
        if (e?.status === 409) {
          // race: score bestaat al → ophalen en bijwerken
          await _laadScores()
          const id = scoreMap[code]?.id
          const r = await api.checklistscores.werkBij(id, { score: nieuweScore })
          _zetScore(code, r)
        } else {
          throw e
        }
      }
    }
    rijStatus[code] = 'opgeslagen'
    emit('gewijzigd')
  } catch (e) {
    rijStatus[code] = 'fout'
    if (e?.status === 422 && Array.isArray(e.detail)) {
      rijFout[code] = e.detail[0]?.msg || 'Ongeldige waarde.'
    } else {
      _toastFout(e)
    }
  }
}

// ── Uitklaprij: bevinding/eigenaar/actie (CD026) ─────────────────────────────

function toggleDetail(code) {
  const open = !uitgeklapt[code]
  if (open) {
    const s = scoreMap[code]
    const aw = s?.antwoord_waarde || {}
    // Verse buffer uit de huidige waarden — bewerken muteert scoreMap niet.
    bewerk[code] = {
      bevinding: s?.bevinding ?? '',
      eigenaar: s?.eigenaar ?? '',
      actie: s?.actie ?? '',
      antwoord_optie: aw.optie ?? '',
      antwoord_opties: Array.isArray(aw.opties) ? [...aw.opties] : [],
      antwoord_getal: aw.getal ?? '',
    }
    delete veldFout[code]
    delete veldStatus[code]
  }
  uitgeklapt[code] = open
}

async function opslaanVelden(code) {
  const s = scoreMap[code]
  if (!mag.value || !s?.id) return // alleen-lezen of nog niet gescoord → niets te PATCHen
  veldStatus[code] = 'bezig'
  delete veldFout[code]
  try {
    const b = bewerk[code]
    // BEWUST géén `score` → backend laat lifecycle/blokkade ongemoeid (ADR-013/016).
    const payload = { bevinding: b.bevinding, eigenaar: b.eigenaar, actie: b.actie }
    // Alleen waar geconfigureerd: het gestructureerde antwoord (envelope of null).
    if (antwoordType(code) !== 'geen') payload.antwoord_waarde = _antwoordEnvelope(code)
    const r = await api.checklistscores.werkBij(s.id, payload)
    _zetScore(code, r)
    veldStatus[code] = 'opgeslagen'
  } catch (e) {
    veldStatus[code] = 'fout'
    if (e?.status === 422 && Array.isArray(e.detail)) {
      veldFout[code] = e.detail[0]?.msg || 'Ongeldige waarde.'
    } else {
      _toastFout(e)
    }
  }
}

defineExpose({ aantalVragen, aantalGescoord, categorieen, herlaad: () => laad() })

laad()
</script>

<template>
  <section class="card" aria-labelledby="sectie-checklist">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-sm)]">
      <h2 id="sectie-checklist" class="text-[length:var(--cd-text-lg)] font-semibold">Checklist</h2>
      <span data-testid="cs-voortgang" class="ml-auto text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]">
        {{ aantalGescoord }}/{{ aantalVragen }} gescoord
      </span>
    </div>

    <p v-if="fout" role="alert" data-testid="cs-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>

    <table>
      <thead>
        <tr><th>Code</th><th>Vraag</th><th>Afgehandeld</th><th></th><th><span class="sr-only">Details</span></th></tr>
      </thead>
      <tbody>
        <template v-for="v in zichtbareVragen" :key="v.code">
          <tr :data-testid="`cs-rij-${v.code}`">
            <td>{{ v.code }}</td>
            <td>{{ v.vraag }}</td>
            <td>
              <select
                :id="`cs-score-${v.code}`"
                :value="huidigeScore(v.code)"
                :disabled="!mag"
                :aria-label="`Afgehandeld voor vraag ${v.code}`"
                :aria-invalid="!!rijFout[v.code]"
                :data-testid="`cs-score-${v.code}`"
                class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60"
                @change="onScoreChange(v.code, $event.target.value)"
              >
                <option value="" disabled>— niet gescoord —</option>
                <option v-for="s in opties.score" :key="s" :value="s">{{ label(SCORE, s) }}</option>
              </select>
            </td>
            <td>
              <span v-if="rijStatus[v.code] === 'bezig'" :data-testid="`cs-status-${v.code}`" class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-xs)]">bezig…</span>
              <span v-else-if="rijStatus[v.code] === 'opgeslagen'" :data-testid="`cs-status-${v.code}`" class="text-[var(--cd-color-success)] text-[length:var(--cd-text-xs)]">opgeslagen</span>
              <span v-else-if="rijFout[v.code]" role="alert" :data-testid="`cs-fout-${v.code}`" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-xs)]">{{ rijFout[v.code] }}</span>
            </td>
            <td>
              <button
                type="button"
                :data-testid="`cs-toggle-${v.code}`"
                :aria-expanded="!!uitgeklapt[v.code]"
                :aria-controls="`cs-detail-${v.code}`"
                :aria-label="`Details vraag ${v.code}`"
                class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
                @click="toggleDetail(v.code)"
              >
                {{ uitgeklapt[v.code] ? '▾' : '▸' }}
              </button>
            </td>
          </tr>

          <tr v-if="uitgeklapt[v.code]" :id="`cs-detail-${v.code}`" :data-testid="`cs-detail-${v.code}`">
            <td colspan="5">
              <p
                v-if="!isGescoord(v.code)"
                :data-testid="`cs-detail-hint-${v.code}`"
                class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]"
              >
                Scoor eerst deze vraag om bevinding, eigenaar en actie vast te leggen.
              </p>
              <div v-else class="flex flex-col gap-[var(--cd-space-sm)]">
                <!-- ADR-019: gestructureerd antwoordveld, alleen waar geconfigureerd -->
                <div v-if="antwoordType(v.code) !== 'geen'" class="flex flex-col gap-[var(--cd-space-xs)]">
                  <label :for="`cs-antwoord-${v.code}`" class="text-[length:var(--cd-text-sm)] font-medium">Antwoord</label>

                  <select
                    v-if="antwoordType(v.code) === 'enkelvoudige_keuze'"
                    :id="`cs-antwoord-${v.code}`"
                    :data-testid="`cs-antwoord-${v.code}`"
                    v-model="bewerk[v.code].antwoord_optie"
                    :disabled="!mag"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60"
                  >
                    <option value="">— geen —</option>
                    <option v-for="o in actieveOpties(v.code)" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
                  </select>

                  <div
                    v-else-if="antwoordType(v.code) === 'meerkeuze'"
                    :data-testid="`cs-antwoord-${v.code}`"
                    class="flex flex-col gap-[var(--cd-space-xs)]"
                  >
                    <label v-for="o in actieveOpties(v.code)" :key="o.optie_sleutel" class="flex items-center gap-[var(--cd-space-xs)]">
                      <input
                        type="checkbox"
                        :data-testid="`cs-antwoord-${v.code}-${o.optie_sleutel}`"
                        :value="o.optie_sleutel"
                        :checked="bewerk[v.code].antwoord_opties.includes(o.optie_sleutel)"
                        :disabled="!mag"
                        @change="toggleOptie(v.code, o.optie_sleutel)"
                      />
                      <span>{{ o.label }}</span>
                    </label>
                  </div>

                  <input
                    v-else-if="antwoordType(v.code) === 'getal'"
                    type="number"
                    min="1"
                    :id="`cs-antwoord-${v.code}`"
                    :data-testid="`cs-antwoord-${v.code}`"
                    v-model="bewerk[v.code].antwoord_getal"
                    :disabled="!mag"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60 w-32"
                  />
                </div>

                <div class="flex flex-col gap-[var(--cd-space-xs)]">
                  <label :for="`cs-bevinding-${v.code}`" class="text-[length:var(--cd-text-sm)] font-medium">Bevinding</label>
                  <textarea
                    :id="`cs-bevinding-${v.code}`"
                    :data-testid="`cs-bevinding-${v.code}`"
                    v-model="bewerk[v.code].bevinding"
                    :disabled="!mag"
                    rows="2"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60"
                  ></textarea>
                </div>
                <div class="flex flex-col gap-[var(--cd-space-xs)]">
                  <label :for="`cs-eigenaar-${v.code}`" class="text-[length:var(--cd-text-sm)] font-medium">Eigenaar</label>
                  <input
                    :id="`cs-eigenaar-${v.code}`"
                    :data-testid="`cs-eigenaar-${v.code}`"
                    v-model="bewerk[v.code].eigenaar"
                    :disabled="!mag"
                    type="text"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60"
                  />
                </div>
                <div class="flex flex-col gap-[var(--cd-space-xs)]">
                  <label :for="`cs-actie-${v.code}`" class="text-[length:var(--cd-text-sm)] font-medium">Actie</label>
                  <textarea
                    :id="`cs-actie-${v.code}`"
                    :data-testid="`cs-actie-${v.code}`"
                    v-model="bewerk[v.code].actie"
                    :disabled="!mag"
                    rows="2"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60"
                  ></textarea>
                </div>
                <div v-if="mag" class="flex items-center gap-[var(--cd-space-sm)]">
                  <button
                    type="button"
                    :data-testid="`cs-velden-opslaan-${v.code}`"
                    class="rounded-[var(--cd-radius-input)] bg-[var(--cd-color-accent)] text-white px-[var(--cd-space-md)] py-[var(--cd-space-xs)]"
                    @click="opslaanVelden(v.code)"
                  >
                    Opslaan
                  </button>
                  <span v-if="veldStatus[v.code] === 'bezig'" :data-testid="`cs-velden-status-${v.code}`" class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-xs)]">bezig…</span>
                  <span v-else-if="veldStatus[v.code] === 'opgeslagen'" :data-testid="`cs-velden-status-${v.code}`" class="text-[var(--cd-color-success)] text-[length:var(--cd-text-xs)]">opgeslagen</span>
                  <span v-else-if="veldFout[v.code]" role="alert" :data-testid="`cs-velden-fout-${v.code}`" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-xs)]">{{ veldFout[v.code] }}</span>
                </div>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </section>
</template>
