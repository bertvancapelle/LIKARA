<script setup>
/**
 * ChecklistConfigBeheer — TENANT-beheer van de checklist-vragenset + antwoord-
 * configuratie (ADR-022 W1/W2/W3/W4, LI050). Schil op de tenant-endpoints
 * (`/checklistconfig`, lk_app): de server handhaaft álle regels.
 *
 * Indeling (LI050): bovenaan kies je het COMPONENTTYPE; links staan de categorieën
 * van dat type (naam + aantal vragen, één geselecteerd); rechts uitsluitend de
 * vragen van de gekozen categorie. De kolom ís het filter — het losse
 * categoriefilter is vervallen. Nergens staat een vraagcode: de code is intern
 * (identiteit-anker voor de deeplink) en wordt bij aanmaken door het systeem
 * toegekend (W4).
 *
 * Rechten (W2): iedereen leest; alleen de beheerder ziet bewerk-affordances.
 */
import { computed, reactive, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useSleepLijst } from '@/composables/useSleepLijst'
import VeldUitleg from '@modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue'
import LijstKop from '@/components/LijstKop.vue'

const ANTWOORDTYPES = ['geen', 'enkelvoudige_keuze', 'meerkeuze', 'getal']
const TYPE_LABEL = {
  geen: 'Geen',
  enkelvoudige_keuze: 'Enkelvoudige keuze',
  meerkeuze: 'Meerkeuze',
  getal: 'Getal',
}

// ADR-022 W2 / LI050 — vraag- en categoriebeheer zijn beheerder-only; iedereen leest.
const auth = useAuthStore()
const magBeheren = computed(() => auth.hasRole('beheerder'))

const toast = useToast()
const vragen = ref([])
const componenttypeOpties = ref([]) // [{ optie_sleutel, label }]
const betekenisOpties = ref([]) // [{ optie_sleutel, label }] — ADR-023 Fase F (F-3)
const categorieen = ref([]) // [{ id, componenttype, naam, volgorde, aantal_vragen }]
const laden = ref(false)
const fout = ref(null)
const actieFout = ref(null)

// LI050 — de indeling: één componenttype tegelijk; de linkerkolom is het filter.
const typeKeuze = ref('')
const geselecteerdeCategorieId = ref(null)

const nieuweOptie = reactive({}) // vraag-id -> { optie_sleutel, label, volgorde }
// W4: geen code-invoer meer — het systeem kent de code toe.
const nieuweVraag = reactive({ vraag: '' })
const nieuweCategorie = reactive({ naam: '' })

// Categorieën van het gekozen type, in hun volgorde.
const typeCategorieen = computed(() =>
  categorieen.value
    .filter((c) => c.componenttype === typeKeuze.value)
    .sort((a, b) => a.volgorde - b.volgorde || a.naam.localeCompare(b.naam)),
)

const geopendeCategorie = computed(
  () => typeCategorieen.value.find((c) => c.id === geselecteerdeCategorieId.value) || null,
)

// Rechts: uitsluitend de vragen van de gekozen categorie (interne code = volgorde).
const zichtbareVragen = computed(() =>
  vragen.value
    .filter(
      (v) => v.componenttype === typeKeuze.value && v.categorie_id === geselecteerdeCategorieId.value,
    )
    // LI050 (W5): de beheerde sleep-volgorde, niet de code.
    .sort((a, b) => (a.volgorde ?? 0) - (b.volgorde ?? 0)),
)

// Uitstaande (gedeactiveerde) vragen per categorie — benoemd in de linkerkolom.
function aantalUit(catId) {
  return vragen.value.filter((v) => v.categorie_id === catId && !v.actief).length
}

// Typewissel → eerste categorie van dat type openen; categorielijst leeg → niets open.
watch([typeKeuze, typeCategorieen], () => {
  if (!typeCategorieen.value.some((c) => c.id === geselecteerdeCategorieId.value)) {
    geselecteerdeCategorieId.value = typeCategorieen.value[0]?.id ?? null
  }
})

function typeLabel(sleutel) {
  return componenttypeOpties.value.find((o) => o.optie_sleutel === sleutel)?.label || sleutel
}

function isAfgeleideSet(vraag) {
  return (vraag.opties || []).some((o) => o.afgeleid_bron)
}
function heeftOpties(vraag) {
  return vraag.antwoordtype === 'enkelvoudige_keuze' || vraag.antwoordtype === 'meerkeuze'
}

// LI050 (W4): bevestigingen benoemen de vraag op zijn TEKST (afgekort), niet op een code.
function kort(tekst, max = 60) {
  const t = String(tekst || '')
  return t.length > max ? `${t.slice(0, max)}…` : t
}

function _toonFout(e) {
  let detail
  if (e?.status === 409 || e?.code === 'CONFIGURATIE_CONFLICT' || e?.code === 'CHECKLISTVRAAG_BESTAAT')
    detail = e?.message || 'Niet toegestaan.'
  else if (e?.status === 422)
    detail = Array.isArray(e?.detail) ? e.detail[0]?.msg || 'Ongeldige invoer.' : 'Ongeldige invoer.'
  else if (e?.status === 404) detail = 'Item niet gevonden.'
  else detail = e?.message || 'Er ging iets mis.'
  actieFout.value = detail
  toast.add({ severity: e?.status === 409 ? 'warn' : 'error', summary: 'Configuratie', detail, life: 6000 })
}

function _vervangVraag(updated) {
  const i = vragen.value.findIndex((v) => v.id === updated.id)
  if (i >= 0) vragen.value[i] = updated
}
function _vervangOptie(vraag, optie) {
  const i = vraag.opties.findIndex((o) => o.id === optie.id)
  if (i >= 0) vraag.opties[i] = optie
}

// "Raakt N componenten"-aankondiging vóór een tellende actie. Faalt de telling,
// dan blokkeren we de actie niet (best-effort melding).
async function _bevestigImpact(componenttype, aanhef) {
  try {
    const { aantal_componenten } = await api.checklistconfig.impact(componenttype)
    return window.confirm(`${aanhef}\n\nDit raakt ${aantal_componenten} componenten van type ${typeLabel(componenttype)}.`)
  } catch {
    return window.confirm(`${aanhef}\n\nDoorgaan?`)
  }
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    const [lijst, opties, betekenissen, cats] = await Promise.all([
      api.checklistconfig.lijst(),
      api.componenten.opties(),
      api.checklistconfig.betekenissen(),
      api.checklistconfig.categorieen(),
    ])
    vragen.value = lijst
    componenttypeOpties.value = opties?.componenttype || []
    betekenisOpties.value = betekenissen || []
    categorieen.value = cats || []
    // Verse binnenkomst: het eerste type mét categorieën (catalogus-volgorde), zodat het
    // scherm nooit leeg opent; de watch opent daarna de eerste categorie.
    if (!typeKeuze.value) {
      const met = componenttypeOpties.value.find((o) =>
        categorieen.value.some((c) => c.componenttype === o.optie_sleutel),
      )
      typeKeuze.value = met?.optie_sleutel || componenttypeOpties.value[0]?.optie_sleutel || ''
    }
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de configuratie mislukt.'
  } finally {
    laden.value = false
  }
}

async function _herlaadCategorieen() {
  try {
    categorieen.value = (await api.checklistconfig.categorieen()) || []
  } catch {
    /* best-effort — de volgende laad() herstelt */
  }
}

// ── Vragen (rechts, bij de geopende categorie) ─────────────────────────────────

async function maakVraag() {
  if (!nieuweVraag.vraag || !typeKeuze.value || !geselecteerdeCategorieId.value) return
  actieFout.value = null
  const akkoord = await _bevestigImpact(typeKeuze.value, 'Vraag toevoegen.')
  if (!akkoord) return
  try {
    const vraag = await api.checklistconfig.maakVraag({
      componenttype: typeKeuze.value,
      vraag: nieuweVraag.vraag,
      categorie_id: geselecteerdeCategorieId.value,
    })
    vragen.value.push(vraag)
    nieuweVraag.vraag = ''
    toast.add({ severity: 'success', summary: 'Toegevoegd', detail: 'Vraag toegevoegd.', life: 3000 })
    await _herlaadCategorieen() // de vraag-telling per categorie beweegt mee
  } catch (e) {
    _toonFout(e)
  }
}

async function zetActief(vraag) {
  actieFout.value = null
  const aanhef = vraag.actief
    ? `Vraag "${kort(vraag.vraag)}" deactiveren.`
    : `Vraag "${kort(vraag.vraag)}" activeren.`
  const akkoord = await _bevestigImpact(vraag.componenttype, aanhef)
  if (!akkoord) return
  try {
    const updated = await api.checklistconfig.zetActief(vraag.id, !vraag.actief)
    _vervangVraag(updated)
  } catch (e) {
    _toonFout(e)
  }
}

async function zetType(vraag, nieuwType) {
  if (nieuwType === vraag.antwoordtype) return
  actieFout.value = null
  try {
    const updated = await api.checklistconfig.zetAntwoordtype(vraag.id, nieuwType)
    _vervangVraag(updated)
  } catch (e) {
    _toonFout(e)
    _vervangVraag({ ...vraag }) // forceer re-render → dropdown terug naar huidige type
  }
}

async function zetBetekenis(vraag, waarde) {
  const nieuw = waarde || null
  if (nieuw === (vraag.betekenis || null)) return
  actieFout.value = null
  try {
    const updated = await api.checklistconfig.zetBetekenis(vraag.id, nieuw)
    _vervangVraag(updated)
  } catch (e) {
    _toonFout(e)
    _vervangVraag({ ...vraag }) // forceer re-render → dropdown terug naar huidige waarde
  }
}

async function voegToe(vraag) {
  const buf = nieuweOptie[vraag.id]
  if (!buf?.optie_sleutel || !buf?.label) return
  actieFout.value = null
  try {
    const optie = await api.checklistconfig.voegOptieToe(vraag.id, {
      optie_sleutel: buf.optie_sleutel,
      label: buf.label,
      volgorde: Number.parseInt(buf.volgorde, 10) || 0,
    })
    vraag.opties.push(optie)
    nieuweOptie[vraag.id] = { optie_sleutel: '', label: '', volgorde: 0 }
  } catch (e) {
    _toonFout(e)
  }
}

async function bewaarOptie(vraag, optie) {
  actieFout.value = null
  try {
    const updated = await api.checklistconfig.wijzigOptie(optie.id, {
      label: optie.label,
      volgorde: Number.parseInt(optie.volgorde, 10) || 0,
    })
    _vervangOptie(vraag, updated)
    toast.add({ severity: 'success', summary: 'Opgeslagen', detail: `Optie ${updated.optie_sleutel}.`, life: 3000 })
  } catch (e) {
    _toonFout(e)
  }
}

async function deactiveer(vraag, optie) {
  actieFout.value = null
  try {
    const updated = await api.checklistconfig.deactiveerOptie(optie.id)
    _vervangOptie(vraag, updated)
  } catch (e) {
    _toonFout(e)
  }
}

function buffer(id) {
  if (!nieuweOptie[id]) nieuweOptie[id] = { optie_sleutel: '', label: '', volgorde: 0 }
  return nieuweOptie[id]
}

// ── Categorieën (links: toevoegen + volgorde; bij de geopende: hernoemen + verwijderen) ──

async function maakCategorie() {
  if (!nieuweCategorie.naam || !typeKeuze.value) return
  actieFout.value = null
  try {
    // LI050 (W5): geen volgorde-invoer — de categorie komt achteraan; daarna slepen.
    const cat = await api.checklistconfig.maakCategorie({
      componenttype: typeKeuze.value,
      naam: nieuweCategorie.naam,
    })
    nieuweCategorie.naam = ''
    toast.add({ severity: 'success', summary: 'Toegevoegd', detail: 'Categorie toegevoegd.', life: 3000 })
    await _herlaadCategorieen()
    geselecteerdeCategorieId.value = cat.id
  } catch (e) {
    _toonFout(e)
  }
}

// ── LI050 (W5): slepen — de ENIGE bediening voor volgorde (besluit Bert; geen
// getalveld, geen pijltjes). Beide lijsten hangen aan dezelfde gedeelde bouwsteen.

async function _herschikCategorieen(ids) {
  actieFout.value = null
  try {
    // Alleen de rijen wier plek wijzigt worden bewaard (1..n op de nieuwe posities).
    const huidige = new Map(typeCategorieen.value.map((c) => [c.id, c.volgorde]))
    for (const [i, id] of ids.entries()) {
      if (huidige.get(id) !== i + 1) await api.checklistconfig.wijzigCategorie(id, { volgorde: i + 1 })
    }
    await _herlaadCategorieen()
  } catch (e) {
    _toonFout(e)
  }
}

async function _herschikVragen(ids) {
  actieFout.value = null
  try {
    const huidige = new Map(zichtbareVragen.value.map((v) => [v.id, v.volgorde]))
    for (const [i, id] of ids.entries()) {
      if (huidige.get(id) !== i + 1) {
        const updated = await api.checklistconfig.werkVraagBij(id, { volgorde: i + 1 })
        _vervangVraag(updated)
      }
    }
  } catch (e) {
    _toonFout(e)
  }
}

const catSleep = useSleepLijst({
  haalIds: () => typeCategorieen.value.map((c) => c.id),
  herschik: _herschikCategorieen,
  naSucces: () => toast.add({ severity: 'success', summary: 'Volgorde', detail: 'Volgorde bewaard.', life: 3000 }),
})

const vraagSleep = useSleepLijst({
  haalIds: () => zichtbareVragen.value.map((v) => v.id),
  herschik: _herschikVragen,
  naSucces: () => toast.add({ severity: 'success', summary: 'Volgorde', detail: 'Volgorde bewaard.', life: 3000 }),
})

// Hernoem-buffer voor de geopende categorie (pas opslaan schrijft).
const hernoemNaam = ref('')
watch(geopendeCategorie, (cat) => {
  hernoemNaam.value = cat?.naam ?? ''
})

async function hernoemCategorie() {
  const cat = geopendeCategorie.value
  if (!cat || !hernoemNaam.value || hernoemNaam.value === cat.naam) return
  actieFout.value = null
  try {
    await api.checklistconfig.wijzigCategorie(cat.id, { naam: hernoemNaam.value })
    toast.add({ severity: 'success', summary: 'Opgeslagen', detail: `Categorie ${hernoemNaam.value}.`, life: 3000 })
    // Hernoemen raakt de categorie-naam op élke vraag-read → beide herladen.
    await laad()
  } catch (e) {
    _toonFout(e)
  }
}

async function verwijderCategorie() {
  const cat = geopendeCategorie.value
  if (!cat) return
  actieFout.value = null
  if (!window.confirm(`Categorie "${cat.naam}" verwijderen?`)) return
  try {
    await api.checklistconfig.verwijderCategorie(cat.id)
    toast.add({ severity: 'success', summary: 'Verwijderd', detail: `Categorie ${cat.naam}.`, life: 3000 })
    geselecteerdeCategorieId.value = null
    await _herlaadCategorieen()
  } catch (e) {
    // 409 CATEGORIE_HEEFT_VRAGEN → de weigering mét telling verschijnt als warn-melding.
    _toonFout(e)
  }
}

laad()
</script>

<template>
  <section aria-labelledby="beheer-titel">
    <!-- LI050: de typekeuze bepaalt WELKE vragenlijst je inricht en hoort dus in de kop
         (zelfde plek als filters elders). Het losse categoriefilter is vervallen — de
         linkerkolom ís het filter. -->
    <LijstKop titel="Checklistvragen" titel-id="beheer-titel">
      <template #filter>
        <label class="flex items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
          Componenttype
          <select v-model="typeKeuze" data-testid="cfg-type-keuze" class="lk-veld">
            <option v-for="o in componenttypeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">
              {{ o.label }}
            </option>
          </select>
        </label>
      </template>
    </LijstKop>

    <!-- W2 — wie niet mag bewerken ziet geen knoppen, wél waarom (NormBeheer-patroon). -->
    <p
      v-if="!magBeheren"
      data-testid="cfg-alleen-lezen-hint"
      class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
    >
      De vragenlijst wordt bepaald door de beheerder van uw organisatie.
    </p>

    <p v-if="fout" role="alert" data-testid="cfg-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="actieFout" role="alert" data-testid="cfg-actie-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ actieFout }}</p>
    <p v-if="laden" data-testid="cfg-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <div class="flex gap-[var(--lk-space-md)] items-start">
      <!-- ── Linkerkolom: de categorieën van het gekozen type ─────────────────── -->
      <aside
        data-testid="cfg-categorie-kolom"
        aria-label="Categorieën"
        class="card w-72 shrink-0 flex flex-col gap-[var(--lk-space-xs)]"
      >
        <h2 class="font-semibold text-[length:var(--lk-text-sm)]">Categorieën</h2>
        <ul class="flex flex-col gap-[2px]">
          <!-- LI050 (W5): volgorde verzet je door te SLEPEN — de enige bediening
               (besluit Bert; het getalveld is bewust vervallen). Gedeelde bouwsteen. -->
          <li
            v-for="cat in typeCategorieen"
            :key="cat.id"
            :draggable="magBeheren ? 'true' : undefined"
            :data-testid="`cfg-cat-rij-${cat.id}`"
            :class="['flex items-center gap-[var(--lk-space-xs)]', catSleep.sleepId.value === cat.id ? 'opacity-50' : '', magBeheren ? 'cursor-grab' : '']"
            @dragstart="magBeheren && catSleep.pak(cat.id)"
            @dragover.prevent
            @drop.prevent="magBeheren && catSleep.laatLos(cat.id)"
          >
            <button
              type="button"
              :data-testid="`cfg-cat-${cat.id}`"
              :aria-current="cat.id === geselecteerdeCategorieId ? 'true' : undefined"
              :class="[
                'flex-1 text-left rounded-[var(--lk-radius-input)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]',
                cat.id === geselecteerdeCategorieId
                  ? 'bg-[var(--lk-color-accent)] font-semibold'
                  : 'hover:bg-[var(--lk-color-primary-50)]',
              ]"
              @click="geselecteerdeCategorieId = cat.id"
            >
              {{ cat.naam }}
              <span class="block text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
                {{ cat.aantal_vragen }} {{ cat.aantal_vragen === 1 ? 'vraag' : 'vragen' }}<template v-if="aantalUit(cat.id)"> · {{ aantalUit(cat.id) }} uitgezet</template>
              </span>
            </button>
          </li>
        </ul>

        <!-- Toevoegen hoort bij de lijst (beheerder). -->
        <form
          v-if="magBeheren"
          data-testid="cfg-nieuwe-categorie"
          class="flex flex-col gap-[var(--lk-space-xs)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)] mt-[var(--lk-space-xs)]"
          @submit.prevent="maakCategorie"
        >
          <label class="flex flex-col gap-[2px] text-[length:var(--lk-text-xs)]">
            Nieuwe categorie
            <input
              v-model="nieuweCategorie.naam"
              data-testid="cfg-nieuwe-categorie-naam"
              type="text"
              placeholder="naam"
              class="lk-veld"
            />
          </label>
          <div class="flex items-end gap-[var(--lk-space-xs)]">
            <!-- LI050 (W5): geen volgorde-invoer — de categorie komt achteraan; daarna slepen. -->
            <button
              type="submit"
              data-testid="cfg-nieuwe-categorie-knop"
              class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5]"
            >
              Toevoegen
            </button>
          </div>
        </form>
      </aside>

      <!-- ── Rechterkolom: de geopende categorie + haar vragen ────────────────── -->
      <div class="flex-1 min-w-0 flex flex-col gap-[var(--lk-space-md)]">
        <div v-if="geopendeCategorie" class="card flex flex-col gap-[var(--lk-space-sm)]">
          <!-- Hernoemen + verwijderen horen bij de geopende categorie (beheerder). -->
          <div class="flex items-center gap-[var(--lk-space-sm)]">
            <template v-if="magBeheren">
              <input
                v-model="hernoemNaam"
                data-testid="cfg-cat-open-naam"
                type="text"
                class="lk-veld flex-1 min-w-0 font-semibold"
                :aria-label="`Naam van categorie ${geopendeCategorie.naam}`"
              />
              <button
                type="button"
                data-testid="cfg-cat-opslaan"
                class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                @click="hernoemCategorie"
              >
                Opslaan
              </button>
              <button
                type="button"
                data-testid="cfg-cat-verwijderen"
                class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-danger)] text-white px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]"
                @click="verwijderCategorie"
              >
                Verwijderen
              </button>
            </template>
            <h2 v-else data-testid="cfg-cat-open-titel" class="font-semibold">{{ geopendeCategorie.naam }}</h2>
          </div>

          <!-- Lege categorie: geen leegte maar een regel mét de route (likara-ux §4). -->
          <p
            v-if="!zichtbareVragen.length"
            data-testid="cfg-leeg"
            class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
          >
            Er staan nog geen vragen in deze categorie.
            <template v-if="magBeheren"> Voeg hieronder de eerste vraag toe.</template>
            <template v-else> De beheerder van uw organisatie kan er een toevoegen.</template>
          </p>

          <ul class="flex flex-col gap-[var(--lk-space-md)]">
            <li
              v-for="vraag in zichtbareVragen"
              :key="vraag.id"
              :data-testid="`cfg-vraag-${vraag.code}`"
              :draggable="magBeheren ? 'true' : undefined"
              :class="['flex flex-col gap-[var(--lk-space-sm)] border-b border-[var(--lk-color-border)] pb-[var(--lk-space-sm)]', vraag.actief ? '' : 'opacity-60', vraagSleep.sleepId.value === vraag.id ? 'opacity-50' : '', magBeheren ? 'cursor-grab' : '']"
              @dragstart="magBeheren && vraagSleep.pak(vraag.id)"
              @dragover.prevent
              @drop.prevent="magBeheren && vraagSleep.laatLos(vraag.id)"
            >
              <div class="flex items-start gap-[var(--lk-space-md)]">
                <!-- LI050 (W4): geen vraagcode meer op het scherm — de tekst ís de vraag. -->
                <span class="flex-1">{{ vraag.vraag }}</span>
                <span
                  :data-testid="`cfg-vraag-status-${vraag.code}`"
                  :class="['text-[length:var(--lk-text-xs)]', vraag.actief ? 'text-[var(--lk-color-success)]' : 'text-[var(--lk-color-danger)]']"
                >{{ vraag.actief ? 'actief' : 'uitgezet' }}</span>
                <button
                  v-if="magBeheren"
                  type="button"
                  :data-testid="`cfg-vraag-actief-${vraag.code}`"
                  class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                  @click="zetActief(vraag)"
                >
                  {{ vraag.actief ? 'Deactiveren' : 'Activeren' }}
                </button>
                <label class="flex items-center gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
                  Antwoordtype
                  <select
                    v-if="magBeheren"
                    :data-testid="`cfg-type-${vraag.code}`"
                    :value="vraag.antwoordtype"
                    class="lk-veld"
                    @change="zetType(vraag, $event.target.value)"
                  >
                    <option v-for="t in ANTWOORDTYPES" :key="t" :value="t">{{ TYPE_LABEL[t] }}</option>
                  </select>
                  <span v-else :data-testid="`cfg-type-tekst-${vraag.code}`">{{ TYPE_LABEL[vraag.antwoordtype] }}</span>
                </label>
                <VeldUitleg veld="antwoordtype" opties="antwoordtype" :testid="`uitleg-antwoordtype-${vraag.code}`" />
                <label class="flex items-center gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
                  Betekenis
                  <select
                    v-if="magBeheren"
                    :data-testid="`cfg-betekenis-${vraag.code}`"
                    :value="vraag.betekenis || ''"
                    class="lk-veld"
                    @change="zetBetekenis(vraag, $event.target.value)"
                  >
                    <option value="">— geen —</option>
                    <option v-for="b in betekenisOpties" :key="b.optie_sleutel" :value="b.optie_sleutel">{{ b.label }}</option>
                  </select>
                  <span v-else :data-testid="`cfg-betekenis-tekst-${vraag.code}`">{{ betekenisOpties.find((b) => b.optie_sleutel === vraag.betekenis)?.label || '— geen —' }}</span>
                </label>
                <VeldUitleg veld="betekenis" :testid="`uitleg-betekenis-${vraag.code}`" />
              </div>
              <p v-if="magBeheren && vraag.antwoordtype !== 'geen'" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
                Een reeds geconfigureerde vraag kan niet van antwoordtype wisselen (de server weigert dat).
              </p>

              <!-- Opties-editor (alleen keuze-types) -->
              <div v-if="heeftOpties(vraag)" class="flex flex-col gap-[var(--lk-space-xs)]">
                <div
                  v-if="isAfgeleideSet(vraag)"
                  :data-testid="`cfg-afgeleid-${vraag.code}`"
                  class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
                >
                  Afgeleide optieset — structuur is vast; alleen labels zijn aanpasbaar.
                </div>

                <table>
                  <thead>
                    <tr><th>Sleutel</th><th>Label</th><th>Volgorde</th><th>Status</th><th></th></tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="optie in vraag.opties"
                      :key="optie.id"
                      :data-testid="`cfg-optie-${vraag.code}-${optie.optie_sleutel}`"
                      :class="optie.actief ? '' : 'opacity-50'"
                    >
                      <td class="font-mono">{{ optie.optie_sleutel }}</td>
                      <td>
                        <input
                          v-if="magBeheren"
                          :data-testid="`cfg-optie-label-${optie.id}`"
                          v-model="optie.label"
                          type="text"
                          class="lk-veld"
                        />
                        <span v-else>{{ optie.label }}</span>
                      </td>
                      <td>
                        <input
                          v-if="magBeheren"
                          :data-testid="`cfg-optie-volgorde-${optie.id}`"
                          v-model="optie.volgorde"
                          type="number"
                          :disabled="!!optie.afgeleid_bron"
                          class="lk-veld w-20"
                        />
                        <span v-else>{{ optie.volgorde }}</span>
                      </td>
                      <td>
                        <span v-if="optie.afgeleid_bron" :data-testid="`cfg-bron-${optie.id}`" class="text-[length:var(--lk-text-xs)]">afgeleid · {{ optie.afgeleid_bron }}</span>
                        <span v-else-if="!optie.actief" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-danger)]">gedeactiveerd</span>
                        <span v-else class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-success)]">actief</span>
                      </td>
                      <td class="flex gap-[var(--lk-space-xs)]">
                        <button
                          v-if="magBeheren"
                          type="button"
                          :data-testid="`cfg-optie-opslaan-${optie.id}`"
                          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                          @click="bewaarOptie(vraag, optie)"
                        >
                          Opslaan
                        </button>
                        <button
                          v-if="magBeheren && !optie.afgeleid_bron && optie.actief"
                          type="button"
                          :data-testid="`cfg-optie-deactiveren-${optie.id}`"
                          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                          @click="deactiveer(vraag, optie)"
                        >
                          Deactiveren
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <!-- Optie toevoegen (niet bij afgeleide sets; beheerder-only) -->
                <form
                  v-if="magBeheren && !isAfgeleideSet(vraag)"
                  :data-testid="`cfg-toevoegen-${vraag.code}`"
                  class="flex items-end gap-[var(--lk-space-sm)] mt-[var(--lk-space-xs)]"
                  @submit.prevent="voegToe(vraag)"
                >
                  <input
                    :data-testid="`cfg-nieuw-sleutel-${vraag.code}`"
                    v-model="buffer(vraag.id).optie_sleutel"
                    type="text"
                    placeholder="sleutel"
                    class="lk-veld"
                  />
                  <input
                    :data-testid="`cfg-nieuw-label-${vraag.code}`"
                    v-model="buffer(vraag.id).label"
                    type="text"
                    placeholder="label"
                    class="lk-veld"
                  />
                  <input
                    :data-testid="`cfg-nieuw-volgorde-${vraag.code}`"
                    v-model="buffer(vraag.id).volgorde"
                    type="number"
                    class="lk-veld w-20"
                  />
                  <button
                    type="submit"
                    :data-testid="`cfg-toevoegen-knop-${vraag.code}`"
                    class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5]"
                  >
                    Optie toevoegen
                  </button>
                </form>
              </div>
            </li>
          </ul>

          <!-- Vraag toevoegen bij de geopende categorie (W4: zonder code — het systeem kent hem toe). -->
          <form
            v-if="magBeheren"
            data-testid="cfg-nieuwe-vraag"
            class="flex items-end gap-[var(--lk-space-sm)]"
            @submit.prevent="maakVraag"
          >
            <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] flex-1 min-w-[16rem]">
              Nieuwe vraag in {{ geopendeCategorie.naam }}
              <input
                v-model="nieuweVraag.vraag"
                data-testid="cfg-nieuwe-vraag-tekst"
                type="text"
                class="lk-veld"
              />
            </label>
            <button
              type="submit"
              data-testid="cfg-nieuwe-vraag-knop"
              class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5]"
            >
              Vraag toevoegen
            </button>
          </form>
        </div>

        <p
          v-else-if="!laden"
          data-testid="cfg-geen-categorie"
          class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
        >
          Dit componenttype heeft nog geen categorieën.
          <template v-if="magBeheren"> Voeg er links een toe.</template>
        </p>
      </div>
    </div>
  </section>
</template>
