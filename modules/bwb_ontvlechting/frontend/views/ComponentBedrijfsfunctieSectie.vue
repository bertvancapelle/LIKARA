<script setup>
/**
 * ComponentBedrijfsfunctieSectie — "Waarvoor gebruiken we het" vanaf het systeem bekeken
 * (ADR-043 gate 4, besluit G2/G9). De consultant koppelt dit systeem aan één of meer
 * bedrijfsfuncties, per koppeling GROF (geldt overal — het vertrekpunt) of FIJN (één plek).
 *
 * ⚠ INVARIANT (ADR-043 §Gate 4 / ADR-049 besluit 5): deze sectie LEEST de gedeelde leesregel via
 * `api.functievervullingen.componentKoppelingen` (server-side, fijn verdringt grof) — ze rekent de
 * grof/fijn-resolutie of de verdringing NOOIT zelf na. Grof telt af (`grof_geldt_op` van N) en een
 * verdrongen antwoord benoemt zichzelf; die waarden komen uit de leeslaag, niet uit dit scherm.
 *
 * Herbruikt de gedeelde bouwstenen (ZoekSelect, MeldingBanner, BevestigVerwijderDialog, toastSucces)
 * en spiegelt de grof/fijn-taal van de functieboom (BedrijfsfunctieLijst). Rechten: koppelen/oordeel/
 * verwijderen = medewerker+ (registratie-feit, ADR-050); de backend handhaaft.
 */
import { computed, ref, watch } from 'vue'
import { Button, useToast } from '@/primevue'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import MeldingBanner from '@/components/MeldingBanner.vue'
import ZoekSelect from './ZoekSelect.vue'
import VeldUitleg from './VeldUitleg.vue'
import { NORM_FEIT_LABEL } from '../labels'

const props = defineProps({
  componentId: { type: String, required: true },
  componentNaam: { type: String, default: '' },
})

const auth = useAuthStore()
const toast = useToast()
const magKoppelen = computed(() => auth.hasRole('medewerker', 'beheerder'))

const koppelingen = ref([])
const laden = ref(false)
const fout = ref(null)

const OORDEEL_LABEL = { naar_behoren: 'werkt naar behoren', noodoplossing: 'noodoplossing' }

async function laad() {
  laden.value = true
  fout.value = null
  try {
    koppelingen.value = await api.functievervullingen.componentKoppelingen(props.componentId)
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de bedrijfsfuncties is mislukt.'
  } finally {
    laden.value = false
  }
}

// Leesbare reikwijdte van een grove koppeling (UIT de leeslaag — nooit hier berekend).
function reikwijdte(k) {
  if (k.herkomst !== 'grof') return ''
  const delen = []
  if (k.grof_totaal_plekken && k.grof_totaal_plekken > 1)
    delen.push(`geldt op ${k.grof_geldt_op} van de ${k.grof_totaal_plekken} plekken`)
  if (k.verdrongen_op)
    delen.push(`op ${k.verdrongen_op} plek${k.verdrongen_op > 1 ? 'ken' : ''} verfijnd met een ander systeem`)
  return delen.join(' · ')
}

// ── Koppelen — toevoegregel (grof default; fijn kiest een plek van de functie) ────
const gekozenFunctie = ref(null) // { id, naam, ouder_ids }
const scope = ref('overal')      // 'overal' (grof) | 'hier' (fijn)
const plekId = ref(null)
const plekOpties = ref([])        // [{ ouder_id, ouder_naam }]
const oordeel = ref('')
const toelichting = ref('')
const koppelFout = ref(null)
const koppelMelding = ref(null)
const koppelBezig = ref(false)
const pickerKey = ref(0)

const heeftPlekken = computed(() => (gekozenFunctie.value?.ouder_ids?.length || 0) > 0)

// De picker spiegelt de backend: koppelbaar zijn alleen niet-vervallen functies (vervallen ⇒ 422).
async function zoekFuncties(params = {}) {
  try {
    const res = await api.bedrijfsfuncties.lijst({ zoek: params.zoek || undefined, limit: 25 })
    return { items: (res.items || []).filter((f) => !f.vervallen), volgende_cursor: res.volgende_cursor }
  } catch {
    return { items: [], volgende_cursor: null }
  }
}
const functieWeergave = (f) => f?.naam ?? ''

async function kiesFunctie(item) {
  if (!item?.id) return
  gekozenFunctie.value = { id: item.id, naam: item.naam, ouder_ids: item.ouder_ids || [] }
  scope.value = 'overal'
  plekId.value = null
  plekOpties.value = []
  koppelFout.value = null
  // Plek-namen (bovenliggende functies) resolven voor de fijn-keuze — een leeslaag-verrijking.
  if (gekozenFunctie.value.ouder_ids.length) {
    plekOpties.value = await Promise.all(
      gekozenFunctie.value.ouder_ids.map(async (oid) => {
        try {
          const f = await api.bedrijfsfuncties.haal(oid)
          return { ouder_id: oid, ouder_naam: f.naam }
        } catch {
          return { ouder_id: oid, ouder_naam: '(bovenliggende functie)' }
        }
      }),
    )
  }
}

const koppelZin = computed(() => {
  const f = gekozenFunctie.value
  if (!f) return ''
  const wie = props.componentNaam || 'dit systeem'
  if (scope.value === 'hier' && plekId.value) {
    const p = plekOpties.value.find((x) => x.ouder_id === plekId.value)
    return `"${wie}" ondersteunt "${f.naam}" alleen op deze plek (onder "${p?.ouder_naam ?? '…'}"). Een grof antwoord op deze plek wordt hier vervangen.`
  }
  return `"${wie}" ondersteunt "${f.naam}" — op elke plek waar deze functie staat. Verfijn later per plek als het ergens anders gaat.`
})

function _reset() {
  gekozenFunctie.value = null
  scope.value = 'overal'
  plekId.value = null
  plekOpties.value = []
  oordeel.value = ''
  toelichting.value = ''
  pickerKey.value += 1
}

async function koppel() {
  koppelFout.value = null
  koppelMelding.value = null
  if (!gekozenFunctie.value) {
    koppelFout.value = 'Kies een bedrijfsfunctie.'
    return
  }
  if (scope.value === 'hier' && !plekId.value) {
    koppelFout.value = 'Kies de plek waar dit geldt.'
    return
  }
  koppelBezig.value = true
  try {
    await api.functievervullingen.maak({
      component_id: props.componentId,
      functie_id: gekozenFunctie.value.id,
      ouder_functie_id: scope.value === 'hier' ? plekId.value : null,
      oordeel: oordeel.value || null,
      toelichting: toelichting.value.trim() || null,
    })
    toastSucces(toast, 'Gekoppeld')
    _reset()
    await laad()
  } catch (e) {
    if (e?.status === 409) koppelMelding.value = 'Deze koppeling bestaat al op deze plek.'
    else if (e?.status === 422) koppelFout.value = e?.message || 'Deze koppeling kan hier niet.'
    else if (e?.status !== 401) koppelFout.value = 'Koppelen is mislukt. Probeer het opnieuw.'
  } finally {
    koppelBezig.value = false
  }
}

// ── Oordeel bijstellen op een bestaande koppeling (registratie-feit → medewerker) ──
async function zetOordeel(k, waarde) {
  try {
    await api.functievervullingen.zetOordeel(k.vervulling_id, waarde || null)
    await laad()
  } catch (e) {
    if (e?.status !== 401) fout.value = 'Het oordeel opslaan is mislukt.'
  }
}

// ── Verwijderen — gedeelde bevestiging (LI035) ───────────────────────────────────
const verwijderOpen = ref(false)
const teVerwijderen = ref(null)
const verwijderBezig = ref(false)
function omschrijving(k) {
  const wie = props.componentNaam || 'dit systeem'
  if (k.herkomst === 'fijn') {
    return `De koppeling van "${wie}" aan "${k.functie_naam}" (onder "${k.ouder_naam}") weghalen? Een antwoord dat overal geldt wordt hier weer leesbaar.`
  }
  return `De koppeling van "${wie}" aan "${k.functie_naam}" weghalen? Deze geldt overal — hij verdwijnt op elke plek waar deze functie staat.`
}
function vraagVerwijder(k) {
  teVerwijderen.value = k
  verwijderOpen.value = true
}
async function bevestigVerwijder() {
  verwijderBezig.value = true
  try {
    await api.functievervullingen.verwijder(teVerwijderen.value.vervulling_id)
    toastSucces(toast, 'Koppeling weggehaald')
    verwijderOpen.value = false
    await laad()
  } catch (e) {
    if (e?.status !== 401) fout.value = 'Weghalen van de koppeling is mislukt.'
    verwijderOpen.value = false
  } finally {
    verwijderBezig.value = false
  }
}

watch([gekozenFunctie, scope, plekId], () => {
  koppelMelding.value = null
})
watch(() => props.componentId, () => laad(), { immediate: true })
</script>

<template>
  <section class="card" aria-labelledby="comp-bf-titel" data-testid="component-bedrijfsfunctie-sectie">
    <!-- C1 (LI045) — de consultant-vriendelijke kop blijft; de feitnaam uit de werkvoorraad komt
         eronder als ondertitel, zodat hij deze plek herkent. De norm-"i" hoort bij de KÓP en staat
         daarom in de kop-rij (items-center op de h2), niet in het ondertitel-blok — zo schuift hij niet
         mee met de ondertitel. Het woord komt uit NORM_FEIT_LABEL: exact wat de werkvoorraad toont. -->
    <div class="mb-[var(--lk-space-sm)]">
      <div class="flex items-center gap-[var(--lk-space-xs)]">
        <h2 id="comp-bf-titel" class="text-[length:var(--lk-text-lg)] font-semibold">
          Waarvoor gebruiken we het
        </h2>
        <VeldUitleg veld="bedrijfsfunctie" testid="uitleg-bedrijfsfunctie-comp" norm-feit="bedrijfsfunctie" />
      </div>
      <p data-testid="cbf-ondertitel" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
        {{ NORM_FEIT_LABEL.bedrijfsfunctie }}
      </p>
    </div>

    <p v-if="fout" role="alert" data-testid="cbf-fout" class="mb-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden && !koppelingen.length" data-testid="cbf-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <ul v-if="koppelingen.length" class="mb-[var(--lk-space-md)] divide-y divide-[var(--lk-color-border)]" data-testid="cbf-regels">
      <li
        v-for="k in koppelingen"
        :key="k.vervulling_id"
        class="flex flex-wrap items-baseline gap-[var(--lk-space-sm)] py-[var(--lk-space-sm)]"
        :data-testid="`cbf-regel-${k.vervulling_id}`"
      >
        <span class="min-w-0">
          <em class="not-italic font-medium">{{ k.functie_naam }}</em>
          <span v-if="k.herkomst === 'fijn'" class="text-[var(--lk-color-text-muted)]"> — alleen onder {{ k.ouder_naam }}</span>
          <span v-else class="text-[var(--lk-color-text-muted)]"> — geldt overal</span>
          <span v-if="reikwijdte(k)" class="block text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" :data-testid="`cbf-reikwijdte-${k.vervulling_id}`">{{ reikwijdte(k) }}</span>
        </span>
        <div class="ml-auto flex shrink-0 items-center gap-[var(--lk-space-xs)]">
          <!-- Oordeel: naar behoren / noodoplossing / nog niet beoordeeld (optioneel; ADR-051). -->
          <label class="sr-only" :for="`cbf-oordeel-${k.vervulling_id}`">Oordeel</label>
          <select
            v-if="magKoppelen"
            :id="`cbf-oordeel-${k.vervulling_id}`"
            :value="k.oordeel || ''"
            class="lk-veld"
            :data-testid="`cbf-oordeel-${k.vervulling_id}`"
            @change="(e) => zetOordeel(k, e.target.value)"
          >
            <option value="">nog niet beoordeeld</option>
            <option value="naar_behoren">werkt naar behoren</option>
            <option value="noodoplossing">noodoplossing</option>
          </select>
          <span v-else class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
            {{ k.oordeel ? OORDEEL_LABEL[k.oordeel] : 'nog niet beoordeeld' }}
          </span>
          <Button v-if="magKoppelen" label="Verwijderen" severity="danger" :data-testid="`cbf-verwijder-${k.vervulling_id}`" @click="vraagVerwijder(k)" />
        </div>
      </li>
    </ul>
    <p v-else-if="!laden && !fout" data-testid="cbf-leeg" class="mb-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
      Nog niet vastgelegd waarvoor dit systeem wordt gebruikt.
      <template v-if="magKoppelen"> Koppel het hieronder aan een bedrijfsfunctie.</template>
    </p>

    <!-- Toevoegregel — direct opslaan; grof is het vertrekpunt (G9). -->
    <form v-if="magKoppelen" class="flex flex-col gap-[var(--lk-space-sm)]" data-testid="cbf-toevoegregel" @submit.prevent="koppel">
      <MeldingBanner v-if="koppelMelding" soort="warn" :tekst="koppelMelding" testid="cbf-melding" />
      <div class="flex flex-wrap items-end gap-[var(--lk-space-md)]">
        <label class="flex min-w-[16rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Bedrijfsfunctie</span>
          <ZoekSelect
            :key="pickerKey"
            :zoek-functie="zoekFuncties"
            :weergave="functieWeergave"
            placeholder="Zoek een bedrijfsfunctie…"
            testid="cbf-functie"
            @keuze="kiesFunctie"
          />
        </label>
        <fieldset class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]" :disabled="!gekozenFunctie">
          <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Waar</span>
          <div class="flex items-center gap-[var(--lk-space-md)]">
            <label class="flex items-center gap-[var(--lk-space-xs)]">
              <input v-model="scope" type="radio" value="overal" data-testid="cbf-scope-overal" /> Geldt overal
            </label>
            <label class="flex items-center gap-[var(--lk-space-xs)]" :class="{ 'opacity-50': !heeftPlekken }">
              <input v-model="scope" type="radio" value="hier" data-testid="cbf-scope-hier" :disabled="!heeftPlekken" /> Eén plek
            </label>
          </div>
        </fieldset>
        <label v-if="scope === 'hier'" class="flex min-w-[12rem] flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Plek</span>
          <select v-model="plekId" class="lk-veld" data-testid="cbf-plek">
            <option :value="null">— kies een plek —</option>
            <option v-for="p in plekOpties" :key="p.ouder_id" :value="p.ouder_id">onder {{ p.ouder_naam }}</option>
          </select>
        </label>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Oordeel (optioneel)</span>
          <select v-model="oordeel" class="lk-veld" data-testid="cbf-oordeel">
            <option value="">nog niet beoordeeld</option>
            <option value="naar_behoren">werkt naar behoren</option>
            <option value="noodoplossing">noodoplossing</option>
          </select>
        </label>
        <label class="flex min-w-[12rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Toelichting (optioneel)</span>
          <input v-model="toelichting" type="text" maxlength="500" class="lk-veld" data-testid="cbf-toelichting" />
        </label>
        <Button type="submit" label="Koppelen" data-testid="cbf-koppel" :disabled="koppelBezig || !gekozenFunctie" />
      </div>
      <p v-if="koppelZin" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="cbf-koppelzin">{{ koppelZin }}</p>
      <span v-if="koppelFout" role="alert" data-testid="cbf-koppel-fout" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-danger)]">{{ koppelFout }}</span>
    </form>

    <BevestigVerwijderDialog
      v-model:visible="verwijderOpen"
      kop="Koppeling verwijderen"
      :omschrijving="teVerwijderen ? omschrijving(teVerwijderen) : ''"
      :bezig="verwijderBezig"
      testid="cbf-verwijder"
      @bevestig="bevestigVerwijder"
    />
  </section>
</template>
