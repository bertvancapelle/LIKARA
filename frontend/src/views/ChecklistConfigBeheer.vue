<script setup>
/**
 * ChecklistConfigBeheer — platform-beheer van de checklist-antwoordconfiguratie
 * (ADR-019 fase 2E-c). Pure schil op de 2D-endpoints (`/platform/checklistconfig`):
 * de server handhaaft álle regels (geldig type, actieve optie, orphan-409,
 * afgeleide sets label-only). De UI biedt alleen affordances + nette foutweergave.
 *
 * Categorie-filter wordt afgeleid uit de code-prefix (de config-read kent geen
 * categorie_naam; het platform-account mag het tenant-`/checklistvragen` niet).
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
const laden = ref(false)
const fout = ref(null)
const actieFout = ref(null)
const categorieFilter = ref('')
const nieuweOptie = reactive({}) // code -> { optie_sleutel, label, volgorde }

function _categorieNr(code) {
  return Number.parseInt(String(code).split('.')[0], 10)
}

const categorieen = computed(() => {
  const set = new Set(vragen.value.map((v) => _categorieNr(v.code)))
  return [...set].sort((a, b) => a - b)
})

const zichtbareVragen = computed(() => {
  if (!categorieFilter.value) return vragen.value
  const nr = Number.parseInt(categorieFilter.value, 10)
  return vragen.value.filter((v) => _categorieNr(v.code) === nr)
})

function isAfgeleideSet(vraag) {
  return (vraag.opties || []).some((o) => o.afgeleid_bron)
}
function heeftOpties(vraag) {
  return vraag.antwoordtype === 'enkelvoudige_keuze' || vraag.antwoordtype === 'meerkeuze'
}

function _toonFout(e) {
  let detail
  if (e?.status === 409 || e?.code === 'CONFIGURATIE_CONFLICT') detail = e?.message || 'Niet toegestaan.'
  else if (e?.status === 422)
    detail = Array.isArray(e?.detail) ? e.detail[0]?.msg || 'Ongeldige invoer.' : 'Ongeldige invoer.'
  else if (e?.status === 404) detail = 'Item niet gevonden.'
  else detail = e?.message || 'Er ging iets mis.'
  actieFout.value = detail
  toast.add({ severity: e?.status === 409 ? 'warn' : 'error', summary: 'Configuratie', detail, life: 6000 })
}

function _vervangVraag(updated) {
  const i = vragen.value.findIndex((v) => v.code === updated.code)
  if (i >= 0) vragen.value[i] = updated
}
function _vervangOptie(vraag, optie) {
  const i = vraag.opties.findIndex((o) => o.id === optie.id)
  if (i >= 0) vraag.opties[i] = optie
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    vragen.value = await api.platformChecklistconfig.lijst()
  } catch (e) {
    fout.value = e?.message || 'Laden van de configuratie mislukt.'
  } finally {
    laden.value = false
  }
}

async function zetType(vraag, nieuwType) {
  if (nieuwType === vraag.antwoordtype) return
  actieFout.value = null
  try {
    const updated = await api.platformChecklistconfig.zetAntwoordtype(vraag.code, nieuwType)
    _vervangVraag(updated)
  } catch (e) {
    _toonFout(e)
    _vervangVraag({ ...vraag }) // forceer re-render → dropdown terug naar huidige type
  }
}

async function voegToe(vraag) {
  const buf = nieuweOptie[vraag.code]
  if (!buf?.optie_sleutel || !buf?.label) return
  actieFout.value = null
  try {
    const optie = await api.platformChecklistconfig.voegOptieToe(vraag.code, {
      optie_sleutel: buf.optie_sleutel,
      label: buf.label,
      volgorde: Number.parseInt(buf.volgorde, 10) || 0,
    })
    vraag.opties.push(optie)
    nieuweOptie[vraag.code] = { optie_sleutel: '', label: '', volgorde: 0 }
  } catch (e) {
    _toonFout(e)
  }
}

async function bewaarOptie(vraag, optie) {
  actieFout.value = null
  try {
    const updated = await api.platformChecklistconfig.wijzigOptie(optie.id, {
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
    const updated = await api.platformChecklistconfig.deactiveerOptie(optie.id)
    _vervangOptie(vraag, updated)
  } catch (e) {
    _toonFout(e)
  }
}

function buffer(code) {
  if (!nieuweOptie[code]) nieuweOptie[code] = { optie_sleutel: '', label: '', volgorde: 0 }
  return nieuweOptie[code]
}

laad()
</script>

<template>
  <section aria-labelledby="beheer-titel">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <h1 id="beheer-titel" class="text-[length:var(--cd-text-xl)] font-semibold">Checklistconfiguratie</h1>
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

    <ul class="flex flex-col gap-[var(--cd-space-md)]">
      <li
        v-for="vraag in zichtbareVragen"
        :key="vraag.code"
        :data-testid="`cfg-vraag-${vraag.code}`"
        class="card flex flex-col gap-[var(--cd-space-sm)]"
      >
        <div class="flex items-start gap-[var(--cd-space-md)]">
          <span class="font-mono font-semibold">{{ vraag.code }}</span>
          <span class="flex-1">{{ vraag.vraag }}</span>
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
              v-model="buffer(vraag.code).optie_sleutel"
              type="text"
              placeholder="sleutel"
              class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
            />
            <input
              :data-testid="`cfg-nieuw-label-${vraag.code}`"
              v-model="buffer(vraag.code).label"
              type="text"
              placeholder="label"
              class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
            />
            <input
              :data-testid="`cfg-nieuw-volgorde-${vraag.code}`"
              v-model="buffer(vraag.code).volgorde"
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
