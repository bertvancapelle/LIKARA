<script setup>
/**
 * ChecklistConfigBeheer — TENANT-beheer van de checklist-vragenset + antwoord-
 * configuratie (ADR-022 W1). Schil op de tenant-endpoints (`/checklistconfig`,
 * cd_app): de server handhaaft álle regels (geldig type, actieve optie, orphan-409,
 * CHECKLISTVRAAG_BESTAAT-409, afgeleide sets label-only). De UI biedt affordances:
 * vragen aanmaken/(de)activeren, antwoordtypes + opties beheren, en een
 * "raakt N componenten"-aankondiging vóór tellende acties.
 *
 * Vragen worden geadresseerd op hun `id`. Categorie/type komen rechtstreeks uit de
 * respons (`categorie_nr`/`categorie_naam`/`componenttype`).
 */
import { computed, reactive, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { api } from '@/api'

const ANTWOORDTYPES = ['geen', 'enkelvoudige_keuze', 'meerkeuze', 'getal']
const TYPE_LABEL = {
  geen: 'Geen',
  enkelvoudige_keuze: 'Enkelvoudige keuze',
  meerkeuze: 'Meerkeuze',
  getal: 'Getal',
}

const toast = useToast()
const vragen = ref([])
const componenttypeOpties = ref([]) // [{ optie_sleutel, label }]
const laden = ref(false)
const fout = ref(null)
const actieFout = ref(null)
const categorieFilter = ref('')
const nieuweOptie = reactive({}) // id -> { optie_sleutel, label, volgorde }

// Nieuwe-vraag-formulier (W1).
const nieuweVraag = reactive({
  componenttype: '',
  code: '',
  vraag: '',
  categorie_nr: null,
  categorie_naam: '',
})

const categorieen = computed(() => {
  const set = new Set(vragen.value.map((v) => v.categorie_nr))
  return [...set].sort((a, b) => a - b)
})

const zichtbareVragen = computed(() => {
  if (!categorieFilter.value) return vragen.value
  const nr = Number.parseInt(categorieFilter.value, 10)
  return vragen.value.filter((v) => v.categorie_nr === nr)
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
    const [lijst, opties] = await Promise.all([
      api.checklistconfig.lijst(),
      api.componenten.opties(),
    ])
    vragen.value = lijst
    componenttypeOpties.value = opties?.componenttype || []
  } catch (e) {
    fout.value = e?.message || 'Laden van de configuratie mislukt.'
  } finally {
    laden.value = false
  }
}

async function maakVraag() {
  if (!nieuweVraag.componenttype || !nieuweVraag.code || !nieuweVraag.vraag || !nieuweVraag.categorie_naam) return
  actieFout.value = null
  const akkoord = await _bevestigImpact(
    nieuweVraag.componenttype,
    `Vraag "${nieuweVraag.code}" toevoegen.`,
  )
  if (!akkoord) return
  try {
    const vraag = await api.checklistconfig.maakVraag({
      componenttype: nieuweVraag.componenttype,
      code: nieuweVraag.code,
      vraag: nieuweVraag.vraag,
      categorie_nr: Number.parseInt(nieuweVraag.categorie_nr, 10) || 0,
      categorie_naam: nieuweVraag.categorie_naam,
    })
    vragen.value.push(vraag)
    Object.assign(nieuweVraag, {
      componenttype: '', code: '', vraag: '', categorie_nr: null, categorie_naam: '',
    })
    toast.add({ severity: 'success', summary: 'Toegevoegd', detail: `Vraag ${vraag.code}.`, life: 3000 })
  } catch (e) {
    _toonFout(e)
  }
}

async function zetActief(vraag) {
  actieFout.value = null
  const aanhef = vraag.actief ? `Vraag "${vraag.code}" deactiveren.` : `Vraag "${vraag.code}" activeren.`
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

laad()
</script>

<template>
  <section aria-labelledby="beheer-titel">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <h1 id="beheer-titel" class="text-[length:var(--cd-text-xl)] font-semibold">Checklistvragen</h1>
      <label class="ml-auto flex items-center gap-[var(--cd-space-sm)] text-[length:var(--cd-text-sm)]">
        Categorie
        <select
          v-model="categorieFilter"
          data-testid="cfg-categorie-filter"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        >
          <option value="">Alle</option>
          <option v-for="nr in categorieen" :key="nr" :value="String(nr)">Categorie {{ nr }}</option>
        </select>
      </label>
    </div>

    <p v-if="fout" role="alert" data-testid="cfg-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>
    <p v-if="actieFout" role="alert" data-testid="cfg-actie-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ actieFout }}</p>
    <p v-if="laden" data-testid="cfg-laden" class="text-[var(--cd-color-text-muted)]">Laden…</p>

    <!-- Vraag toevoegen (ADR-022 W1) — tenant-CRUD. Toont 409 CHECKLISTVRAAG_BESTAAT
         netjes via de actieFout-melding; tellende actie → impact-aankondiging. -->
    <form
      data-testid="cfg-nieuwe-vraag"
      class="card flex flex-wrap items-end gap-[var(--cd-space-sm)] mb-[var(--cd-space-md)]"
      @submit.prevent="maakVraag"
    >
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        Type
        <select
          v-model="nieuweVraag.componenttype"
          data-testid="cfg-nieuwe-vraag-type"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        >
          <option value="" disabled>— maak een keuze —</option>
          <option v-for="o in componenttypeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
      </label>
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        Code
        <input
          v-model="nieuweVraag.code"
          data-testid="cfg-nieuwe-vraag-code"
          type="text"
          placeholder="bv. 1.4"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        />
      </label>
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)] flex-1 min-w-[12rem]">
        Vraag
        <input
          v-model="nieuweVraag.vraag"
          data-testid="cfg-nieuwe-vraag-tekst"
          type="text"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        />
      </label>
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        Categorie-nr
        <input
          v-model="nieuweVraag.categorie_nr"
          data-testid="cfg-nieuwe-vraag-catnr"
          type="number"
          class="w-24 rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        />
      </label>
      <label class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
        Categorie-naam
        <input
          v-model="nieuweVraag.categorie_naam"
          data-testid="cfg-nieuwe-vraag-catnaam"
          type="text"
          class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
        />
      </label>
      <button
        type="submit"
        data-testid="cfg-nieuwe-vraag-knop"
        class="rounded-[var(--cd-radius-input)] bg-[var(--cd-color-accent)] text-white px-[var(--cd-space-md)] py-[var(--cd-space-xs)]"
      >
        Vraag toevoegen
      </button>
    </form>

    <ul class="flex flex-col gap-[var(--cd-space-md)]">
      <li
        v-for="vraag in zichtbareVragen"
        :key="vraag.code"
        :data-testid="`cfg-vraag-${vraag.code}`"
        :class="['card flex flex-col gap-[var(--cd-space-sm)]', vraag.actief ? '' : 'opacity-60']"
      >
        <div class="flex items-start gap-[var(--cd-space-md)]">
          <span class="font-mono font-semibold">{{ vraag.code }}</span>
          <span
            :data-testid="`cfg-vraag-type-${vraag.code}`"
            class="text-[length:var(--cd-text-xs)] rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-xs)] py-[2px]"
          >{{ typeLabel(vraag.componenttype) }}</span>
          <span class="flex-1">{{ vraag.vraag }}</span>
          <span
            :data-testid="`cfg-vraag-status-${vraag.code}`"
            :class="['text-[length:var(--cd-text-xs)]', vraag.actief ? 'text-[var(--cd-color-success)]' : 'text-[var(--cd-color-danger)]']"
          >{{ vraag.actief ? 'actief' : 'gedeactiveerd' }}</span>
          <button
            type="button"
            :data-testid="`cfg-vraag-actief-${vraag.code}`"
            class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
            @click="zetActief(vraag)"
          >
            {{ vraag.actief ? 'Deactiveren' : 'Activeren' }}
          </button>
          <label class="flex items-center gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
            Antwoordtype
            <select
              :data-testid="`cfg-type-${vraag.code}`"
              :value="vraag.antwoordtype"
              class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
              @change="zetType(vraag, $event.target.value)"
            >
              <option v-for="t in ANTWOORDTYPES" :key="t" :value="t">{{ TYPE_LABEL[t] }}</option>
            </select>
          </label>
        </div>
        <p v-if="vraag.antwoordtype !== 'geen'" class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">
          Een reeds geconfigureerde vraag kan niet van antwoordtype wisselen (de server weigert dat).
        </p>

        <!-- Opties-editor (alleen keuze-types) -->
        <div v-if="heeftOpties(vraag)" class="flex flex-col gap-[var(--cd-space-xs)]">
          <div
            v-if="isAfgeleideSet(vraag)"
            :data-testid="`cfg-afgeleid-${vraag.code}`"
            class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]"
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
                    :data-testid="`cfg-optie-label-${optie.id}`"
                    v-model="optie.label"
                    type="text"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
                  />
                </td>
                <td>
                  <input
                    :data-testid="`cfg-optie-volgorde-${optie.id}`"
                    v-model="optie.volgorde"
                    type="number"
                    :disabled="!!optie.afgeleid_bron"
                    class="w-20 rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white disabled:opacity-60"
                  />
                </td>
                <td>
                  <span v-if="optie.afgeleid_bron" :data-testid="`cfg-bron-${optie.id}`" class="text-[length:var(--cd-text-xs)]">afgeleid · {{ optie.afgeleid_bron }}</span>
                  <span v-else-if="!optie.actief" class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-danger)]">gedeactiveerd</span>
                  <span v-else class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-success)]">actief</span>
                </td>
                <td class="flex gap-[var(--cd-space-xs)]">
                  <button
                    type="button"
                    :data-testid="`cfg-optie-opslaan-${optie.id}`"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
                    @click="bewaarOptie(vraag, optie)"
                  >
                    Opslaan
                  </button>
                  <button
                    v-if="!optie.afgeleid_bron && optie.actief"
                    type="button"
                    :data-testid="`cfg-optie-deactiveren-${optie.id}`"
                    class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
                    @click="deactiveer(vraag, optie)"
                  >
                    Deactiveren
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Optie toevoegen (niet bij afgeleide sets) -->
          <form
            v-if="!isAfgeleideSet(vraag)"
            :data-testid="`cfg-toevoegen-${vraag.code}`"
            class="flex items-end gap-[var(--cd-space-sm)] mt-[var(--cd-space-xs)]"
            @submit.prevent="voegToe(vraag)"
          >
            <input
              :data-testid="`cfg-nieuw-sleutel-${vraag.code}`"
              v-model="buffer(vraag.id).optie_sleutel"
              type="text"
              placeholder="sleutel"
              class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
            />
            <input
              :data-testid="`cfg-nieuw-label-${vraag.code}`"
              v-model="buffer(vraag.id).label"
              type="text"
              placeholder="label"
              class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
            />
            <input
              :data-testid="`cfg-nieuw-volgorde-${vraag.code}`"
              v-model="buffer(vraag.id).volgorde"
              type="number"
              class="w-20 rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
            />
            <button
              type="submit"
              :data-testid="`cfg-toevoegen-knop-${vraag.code}`"
              class="rounded-[var(--cd-radius-input)] bg-[var(--cd-color-accent)] text-white px-[var(--cd-space-md)] py-[var(--cd-space-xs)]"
            >
              Optie toevoegen
            </button>
          </form>
        </div>
      </li>
    </ul>
  </section>
</template>
