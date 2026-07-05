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
 * Uitklaprij (CD026): per vraag een toggle die `bevinding`/`actie`
 * (kolommen op Checklistscore) toont en — voor medewerker/beheerder — bewerkbaar
 * maakt met één expliciete "Opslaan"-knop. Die slaat de drie velden samen op via
 * werkBij(id, {bevinding, actie}) — **zonder `score`**, zodat de
 * score-afgeleide lifecycle/blokkade ongemoeid blijft (ADR-013/016). De drie
 * velden zijn pas bewerkbaar zodra de vraag gescoord is (er moet een
 * Checklistscore-rij zijn om op te PATCHen).
 */
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { PARTIJ_AARD, SCORE, SIGNAAL_LABEL, gebruikersgroepIdentiteit, label, scoreKleur } from '../labels'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

// ADR-037 — verantwoordelijke-picker: één gemengde lijst afdelingen + personen (aard_in).
const zoekVerantwoordelijken = (params) =>
  api.partijen.lijst({ ...params, aard_in: ['organisatie_eenheid', 'persoon'] })
// Gedempte aard-hint rechts in de lijst-regel ("afdeling"/"persoon").
const aardSuffix = (p) => (p?.aard ? label(PARTIJ_AARD, p.aard).toLowerCase() : '')
// ADR-037 — identiteit "afdeling — organisatie" / "persoon — afdeling — organisatie", zodat
// gelijknamige afdelingen van verschillende organisaties onderscheidbaar zijn. Sleutelt op
// afdeling-aanwezigheid (een afdeling-partij draagt zelf geen afdeling → 2-delig; een persoon draagt
// z'n afdeling → 3-delig) en hergebruikt de gebruikersgroep-string-helper (ADR-036a).
function verantwIdentiteit(naam, afdeling, organisatie) {
  if (!naam) return ''
  if (afdeling) return `${naam} — ${gebruikersgroepIdentiteit(afdeling, organisatie)}`
  return gebruikersgroepIdentiteit(naam, organisatie)
}

const props = defineProps({
  applicatieId: { type: String, required: true },
  // CD022: filtert de getoonde vragen op één checklist-categorie (categorie_nr).
  // null = alle vragen (zelfstandig gebruik / volledige lijst).
  categorieNr: { type: Number, default: null },
  // ADR-022 Fase E: scoping van de vragenset op componenttype (symmetrisch met de
  // engine). null = alle actieve vragen.
  componenttype: { type: String, default: null },
  // F-1-vervolg (blokkade-herkomst): wordt een vraag-code gezet, dan scrollt + markeert
  // de sectie die rij (read-only navigatie vanuit BlokkadeSectie). null = niets markeren.
  markeerCode: { type: String, default: null },
  // ADR-027 read-only-invariant: is de checklist van dit componenttype open voor invoer?
  // false ⇒ bestaande scores blijven leesbaar, maar invoer is gesloten (velden disabled).
  bewerkbaar: { type: Boolean, default: true },
})
const emit = defineEmits(['gewijzigd'])
const auth = useAuthStore()
const toast = useToast()

const magRol = computed(() => auth.hasRole('medewerker', 'beheerder'))
// Invoer mag alleen mét de rol ÉN wanneer het type checklist-dragend is (open voor bewerking).
const mag = computed(() => magRol.value && props.bewerkbaar)
// Toon de gesloten-melding alleen aan wie anders had mogen bewerken (geen ruis voor viewers).
const toonGeslotenMelding = computed(() => magRol.value && !props.bewerkbaar)

const vragen = ref([])
const scoreMap = reactive({}) // vraag_code -> { id, score, bevinding, actie }
const opties = ref({ score: [] })
const laden = ref(false)
const fout = ref(null)
const rijStatus = reactive({}) // vraag_code -> 'bezig' | 'opgeslagen' | 'fout'
const rijFout = reactive({}) // vraag_code -> melding

// Uitklaprij-state (CD026)
const uitgeklapt = reactive({}) // vraag_code -> bool
const bewerk = reactive({}) // vraag_code -> { bevinding, actie } (lokale buffer)
const veldStatus = reactive({}) // vraag_code -> 'bezig' | 'opgeslagen' | 'fout'
const veldFout = reactive({}) // vraag_code -> melding

const aantalVragen = computed(() => vragen.value.length)
const aantalGescoord = computed(() => Object.keys(scoreMap).length)

// Client-side kolomsortering (geen API-wijziging): klik op een kolomkop togglet
// asc/desc. Default = code oplopend (= het pre-sorteer-gedrag). De markeer/scroll-
// naar-vraag blijft werken want die target de rij-id, niet de positie.
const sortKolom = ref('code') // 'code' | 'vraag' | 'score'
const sortRichting = ref('asc') // 'asc' | 'desc'

function sorteerOp(kolom) {
  if (sortKolom.value === kolom) {
    sortRichting.value = sortRichting.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKolom.value = kolom
    sortRichting.value = 'asc'
  }
}

function ariaSort(kolom) {
  if (sortKolom.value !== kolom) return 'none'
  return sortRichting.value === 'asc' ? 'ascending' : 'descending'
}

function _sortWaarde(v, kolom) {
  if (kolom === 'vraag') return v.vraag || ''
  if (kolom === 'score') return huidigeScore(v.code) || '' // ongescoord = '' (asc vooraan)
  return v.code
}

// CD022: alleen de vragen van de actieve categorie tonen (null = alle). De voortgang-
// tellers blijven bewust GLOBAAL (alle 89 vragen). Sortering client-side; stabiele
// tiebreak op code zodat gelijke waarden deterministisch blijven.
const zichtbareVragen = computed(() => {
  const lijst =
    props.categorieNr == null
      ? vragen.value
      : vragen.value.filter((v) => v.categorie_nr === props.categorieNr)
  const richting = sortRichting.value === 'asc' ? 1 : -1
  return [...lijst].sort((a, b) => {
    const wa = String(_sortWaarde(a, sortKolom.value))
    const wb = String(_sortWaarde(b, sortKolom.value))
    const cmp = wa.localeCompare(wb, undefined, { numeric: true })
    if (cmp !== 0) return cmp * richting
    return a.code.localeCompare(b.code, undefined, { numeric: true }) * richting
  })
})

// Afgeleide categorie-lijst (nr + naam, oplopend) voor de tab-labels in de ouder —
// single source uit de geladen vragen, geen seed-namen in de frontend dupliceren.
const categorieen = computed(() => {
  const perNr = new Map()
  for (const v of vragen.value) if (!perNr.has(v.categorie_nr)) perNr.set(v.categorie_nr, v.categorie_naam)
  return [...perNr.entries()].sort((a, b) => a[0] - b[0]).map(([nr, naam]) => ({ nr, naam }))
})

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  const per = { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

// Sla de volledige score-rij op in de lokale map (de respons/lijst draagt óók
// bevinding/actie — single source, voorkomt verlies van die velden bij een
// score-wijziging). ADR-037: het vrije-tekstveld `eigenaar` verviel (verantwoordelijke = Pass 2).
function _zetScore(code, r) {
  scoreMap[code] = {
    id: r.id,
    score: r.score,
    bevinding: r.bevinding ?? '',
    actie: r.actie ?? '',
    antwoord_waarde: r.antwoord_waarde ?? null,
    // ADR-037: verantwoordelijke (id) + afgeleide leesvelden uit de read.
    verantwoordelijke_id: r.verantwoordelijke_id ?? null,
    verantwoordelijke_naam: r.verantwoordelijke_naam ?? '',
    verantwoordelijke_afdeling: r.verantwoordelijke_afdeling ?? '',
    verantwoordelijke_organisatie: r.verantwoordelijke_organisatie ?? '',
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
  const p = await api.checklistscores.lijst({ component_id: props.applicatieId, limit: 100 })
  _vulScoreMap(p.items)
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    // Vragen + scores parallel ophalen; scoreMap pas vullen NÁ het zetten van
    // `vragen` (id → code-join vereist de vragenlijst).
    const [vragenResp, scoresPagina] = await Promise.all([
      api.checklistvragen.lijst(props.componenttype),
      api.checklistscores.lijst({ component_id: props.applicatieId, limit: 100 }),
      (async () => {
        if (!opties.value.score.length) opties.value = await api.checklistscores.opties()
      })(),
    ])
    vragen.value = vragenResp
    _vulScoreMap(scoresPagina.items)
    // Deep-link-markering: de rij `cs-rij-<code>` bestaat pas ná dit punt → nu (her)toepassen.
    if (props.markeerCode) _pasMarkeringToe(props.markeerCode)
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de checklist mislukt.'
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

// ── Uitklaprij: bevinding/actie (CD026) ─────────────────────────────

function toggleDetail(code) {
  const open = !uitgeklapt[code]
  if (open) {
    const s = scoreMap[code]
    const aw = s?.antwoord_waarde || {}
    // Verse buffer uit de huidige waarden — bewerken muteert scoreMap niet.
    bewerk[code] = {
      bevinding: s?.bevinding ?? '',
      actie: s?.actie ?? '',
      // ADR-037: verantwoordelijke-id (bewerkbaar) + de VOLLEDIGE identiteit als voorvul-weergave
      // (gelijk aan de lijst), zodat het veld bij bewerken "persoon — afdeling — organisatie" toont.
      verantwoordelijke_id: s?.verantwoordelijke_id ?? null,
      verantwoordelijke_weergave: verantwIdentiteit(
        s?.verantwoordelijke_naam, s?.verantwoordelijke_afdeling, s?.verantwoordelijke_organisatie,
      ),
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
    // ADR-037: verantwoordelijke_id (afdeling/persoon of null = leeg) gaat mee; score niet.
    const payload = { bevinding: b.bevinding, actie: b.actie, verantwoordelijke_id: b.verantwoordelijke_id ?? null }
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

// Herkomst-markering (blokkade-doorklik): scroll naar + highlight de aangewezen rij.
// `scrollIntoView` defensief (niet alle test-DOM's implementeren het).
const gemarkeerd = ref(null)
let _markeerTimer = null
async function _pasMarkeringToe(code) {
  if (!code) return
  await nextTick()
  const el = document.getElementById(`cs-rij-${code}`)
  el?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  gemarkeerd.value = code
  if (_markeerTimer) clearTimeout(_markeerTimer)
  _markeerTimer = setTimeout(() => {
    if (gemarkeerd.value === code) gemarkeerd.value = null
  }, 2500)
}
// In-page doorklik (BlokkadeSectie `naar-vraag`): markeerCode wijzigt terwijl de rijen al
// bestaan. Deep-link (route-query, ADR-024-vervolg): markeerCode staat al gezet vóór de
// vragen geladen zijn — daarom hertoepassen ná `laad()` (zie daar). Eén markeerpad.
watch(() => props.markeerCode, (code) => _pasMarkeringToe(code), { immediate: true })

defineExpose({ aantalVragen, aantalGescoord, categorieen, herlaad: () => laad() })

laad()
</script>

<template>
  <section class="card" aria-labelledby="sectie-checklist">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-checklist" class="text-[length:var(--lk-text-lg)] font-semibold">Checklist</h2>
      <span data-testid="cs-voortgang" class="ml-auto text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">
        {{ aantalGescoord }}/{{ aantalVragen }} gescoord
      </span>
    </div>

    <p v-if="fout" role="alert" data-testid="cs-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <p
      v-if="toonGeslotenMelding"
      role="status"
      data-testid="cs-gesloten"
      class="mb-[var(--lk-space-sm)] flex items-center gap-[var(--lk-space-xs)] rounded-[var(--lk-radius-input)] bg-[color-mix(in_srgb,var(--lk-color-warn)_12%,transparent)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-warn)]"
    >
      <span aria-hidden="true">🔒</span>
      De checklist voor dit componenttype is gesloten voor bewerking. Bestaande antwoorden blijven leesbaar.
    </p>

    <table>
      <thead>
        <tr>
          <th :aria-sort="ariaSort('code')">
            <button type="button" data-testid="cs-sort-code" class="font-semibold inline-flex items-center gap-1 hover:underline" @click="sorteerOp('code')">
              Code <span aria-hidden="true">{{ sortKolom === 'code' ? (sortRichting === 'asc' ? '▲' : '▼') : '↕' }}</span>
            </button>
          </th>
          <th :aria-sort="ariaSort('vraag')">
            <button type="button" data-testid="cs-sort-vraag" class="font-semibold inline-flex items-center gap-1 hover:underline" @click="sorteerOp('vraag')">
              Vraag <span aria-hidden="true">{{ sortKolom === 'vraag' ? (sortRichting === 'asc' ? '▲' : '▼') : '↕' }}</span>
            </button>
          </th>
          <th :aria-sort="ariaSort('score')">
            <span class="inline-flex items-center gap-1">
              <button type="button" data-testid="cs-sort-score" class="font-semibold inline-flex items-center gap-1 hover:underline" @click="sorteerOp('score')">
                Afgehandeld <span aria-hidden="true">{{ sortKolom === 'score' ? (sortRichting === 'asc' ? '▲' : '▼') : '↕' }}</span>
              </button>
              <VeldUitleg veld="score" opties="score" />
            </span>
          </th>
          <th></th>
          <th><span class="sr-only">Details</span></th>
        </tr>
      </thead>
      <tbody>
        <template v-for="v in zichtbareVragen" :key="v.code">
          <tr
            :id="`cs-rij-${v.code}`"
            :data-testid="`cs-rij-${v.code}`"
            :class="gemarkeerd === v.code ? 'bg-[var(--lk-color-accent)]' : ''"
          >
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
                :class="['rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white disabled:opacity-60 font-semibold', scoreKleur(huidigeScore(v.code))]"
                @change="onScoreChange(v.code, $event.target.value)"
              >
                <option value="" disabled>— niet gescoord —</option>
                <option v-for="s in opties.score" :key="s" :value="s">{{ label(SCORE, s) }}</option>
              </select>
            </td>
            <td>
              <span v-if="rijStatus[v.code] === 'bezig'" :data-testid="`cs-status-${v.code}`" class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-xs)]">bezig…</span>
              <span v-else-if="rijStatus[v.code] === 'opgeslagen'" :data-testid="`cs-status-${v.code}`" class="text-[var(--lk-color-success)] text-[length:var(--lk-text-xs)]">opgeslagen</span>
              <span v-else-if="rijFout[v.code]" role="alert" :data-testid="`cs-fout-${v.code}`" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-xs)]">{{ rijFout[v.code] }}</span>
            </td>
            <td>
              <button
                type="button"
                :data-testid="`cs-toggle-${v.code}`"
                :aria-expanded="!!uitgeklapt[v.code]"
                :aria-controls="`cs-detail-${v.code}`"
                :aria-label="`Details vraag ${v.code}`"
                class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
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
                class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]"
              >
                Scoor eerst deze vraag om bevinding en actie vast te leggen.
              </p>
              <div v-else class="flex flex-col gap-[var(--lk-space-sm)]">
                <!-- ADR-019: gestructureerd antwoordveld, alleen waar geconfigureerd -->
                <div v-if="antwoordType(v.code) !== 'geen'" class="flex flex-col gap-[var(--lk-space-xs)]">
                  <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
                    <label :for="`cs-antwoord-${v.code}`" class="text-[length:var(--lk-text-sm)] font-medium">Antwoord</label>
                    <VeldUitleg :veld="'checklist_antwoord'" :testid="`uitleg-antwoord-${v.code}`" />
                  </span>

                  <select
                    v-if="antwoordType(v.code) === 'enkelvoudige_keuze'"
                    :id="`cs-antwoord-${v.code}`"
                    :data-testid="`cs-antwoord-${v.code}`"
                    v-model="bewerk[v.code].antwoord_optie"
                    :disabled="!mag"
                    class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white disabled:opacity-60"
                  >
                    <option value="">— geen —</option>
                    <option v-for="o in actieveOpties(v.code)" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
                  </select>

                  <div
                    v-else-if="antwoordType(v.code) === 'meerkeuze'"
                    :data-testid="`cs-antwoord-${v.code}`"
                    class="flex flex-col gap-[var(--lk-space-xs)]"
                  >
                    <label v-for="o in actieveOpties(v.code)" :key="o.optie_sleutel" class="flex items-center gap-[var(--lk-space-xs)]">
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
                    class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white disabled:opacity-60 w-32"
                  />
                </div>

                <div class="flex flex-col gap-[var(--lk-space-xs)]">
                  <label :for="`cs-bevinding-${v.code}`" class="text-[length:var(--lk-text-sm)] font-medium">Bevinding</label>
                  <textarea
                    :id="`cs-bevinding-${v.code}`"
                    :data-testid="`cs-bevinding-${v.code}`"
                    v-model="bewerk[v.code].bevinding"
                    :disabled="!mag"
                    rows="2"
                    class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white disabled:opacity-60"
                  ></textarea>
                </div>
                <!-- ADR-037: verantwoordelijke-picker (afdeling of persoon; leeg mag). -->
                <div class="flex flex-col gap-[var(--lk-space-xs)]">
                  <div class="flex items-center gap-[var(--lk-space-xs)]">
                    <label :for="`cs-verantw-${v.code}`" class="text-[length:var(--lk-text-sm)] font-medium">Verantwoordelijke</label>
                    <VeldUitleg :veld="'verantwoordelijke'" :testid="`uitleg-verantw-${v.code}`" />
                  </div>
                  <ZoekSelect
                    :id="`cs-verantw-${v.code}`"
                    :testid="`cs-verantw-${v.code}`"
                    :model-value="bewerk[v.code].verantwoordelijke_id"
                    :zoek-functie="zoekVerantwoordelijken"
                    :initieel-weergave="bewerk[v.code].verantwoordelijke_weergave"
                    :weergave="(p) => verantwIdentiteit(p.naam, p.afdeling_naam, p.organisatie_naam)"
                    :disabled="!mag"
                    placeholder="Zoek een afdeling of persoon (optioneel)…"
                    @update:model-value="(id) => (bewerk[v.code].verantwoordelijke_id = id)"
                  >
                    <template #optie="{ item }">
                      <span class="flex items-center justify-between gap-[var(--lk-space-sm)]">
                        <span class="truncate">{{ verantwIdentiteit(item.naam, item.afdeling_naam, item.organisatie_naam) }}</span>
                        <span class="shrink-0 text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-xs)]">{{ aardSuffix(item) }}</span>
                      </span>
                    </template>
                  </ZoekSelect>
                  <div class="flex items-center gap-[var(--lk-space-md)] text-[length:var(--lk-text-xs)]">
                    <!-- Afgeleide identiteit "afdeling — organisatie" / "persoon — afdeling — organisatie"
                         (uit de read; verschijnt ná opslaan). Ontdubbelt gelijknamige afdelingen. -->
                    <span v-if="scoreMap[v.code]?.verantwoordelijke_naam" :data-testid="`cs-verantw-identiteit-${v.code}`" class="text-[var(--lk-color-text-muted)]">
                      {{ verantwIdentiteit(scoreMap[v.code].verantwoordelijke_naam, scoreMap[v.code].verantwoordelijke_afdeling, scoreMap[v.code].verantwoordelijke_organisatie) }}
                    </span>
                    <button
                      v-if="mag && bewerk[v.code].verantwoordelijke_id"
                      type="button"
                      :data-testid="`cs-verantw-wissen-${v.code}`"
                      class="text-[var(--lk-color-primary)] hover:underline"
                      @click="bewerk[v.code].verantwoordelijke_id = null"
                    >
                      Wissen
                    </button>
                    <!-- Aandacht-signaal in de checklist-context: gescoord maar geen verantwoordelijke. -->
                    <span
                      v-if="scoreMap[v.code] && !scoreMap[v.code].verantwoordelijke_id"
                      :data-testid="`cs-verantw-signaal-${v.code}`"
                      class="text-[var(--lk-color-warning)]"
                    >
                      🟡 {{ SIGNAAL_LABEL.antwoord_zonder_verantwoordelijke }}
                    </span>
                  </div>
                </div>
                <div class="flex flex-col gap-[var(--lk-space-xs)]">
                  <label :for="`cs-actie-${v.code}`" class="text-[length:var(--lk-text-sm)] font-medium">Actie</label>
                  <textarea
                    :id="`cs-actie-${v.code}`"
                    :data-testid="`cs-actie-${v.code}`"
                    v-model="bewerk[v.code].actie"
                    :disabled="!mag"
                    rows="2"
                    class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white disabled:opacity-60"
                  ></textarea>
                </div>
                <div v-if="mag" class="flex items-center gap-[var(--lk-space-sm)]">
                  <button
                    type="button"
                    :data-testid="`cs-velden-opslaan-${v.code}`"
                    class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white font-semibold px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                    @click="opslaanVelden(v.code)"
                  >
                    Opslaan
                  </button>
                  <span v-if="veldStatus[v.code] === 'bezig'" :data-testid="`cs-velden-status-${v.code}`" class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-xs)]">bezig…</span>
                  <span v-else-if="veldStatus[v.code] === 'opgeslagen'" :data-testid="`cs-velden-status-${v.code}`" class="text-[var(--lk-color-success)] text-[length:var(--lk-text-xs)]">opgeslagen</span>
                  <span v-else-if="veldFout[v.code]" role="alert" :data-testid="`cs-velden-fout-${v.code}`" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-xs)]">{{ veldFout[v.code] }}</span>
                </div>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </section>
</template>
