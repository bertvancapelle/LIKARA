<script setup>
/**
 * OrganisatiegebruikSectie — "Wie gebruikt dit" op het componentdetail (ADR-046 stuk 2).
 *
 * Eén regel per ORGANISATIE (het grove feit, ADR-036 — niet per gebruikersgroep, niet
 * samengevouwen): organisatienaam + de bekende afdelingen, of rustig "afdeling onbekend"
 * (de normale stand na een eerste workshop — geen fout, geen gebrek). Toevoegen = een
 * organisatie kiezen zónder afdeling te hoeven verzinnen ("begin grof, verfijn waar het
 * telt"); verfijnen blijft via de gebruikersgroepen lopen — deze sectie verandert die
 * samenhang niet, ze maakt alleen de grove invoer mogelijk die ontbrak.
 *
 * Verwijderen = altijd bevestiging (BevestigVerwijderDialog, regel leesbaar); een feit
 * mét verfijnende gebruikersgroepen weigert de backend (409 GEBRUIK_HEEFT_VERFIJNING —
 * RESTRICT: veldwerk verdwijnt nooit stil) en dat tonen we als warn-melding ín de
 * dialoog. Dubbel toevoegen ⇒ 409 GEBRUIK_BESTAAT als vriendelijke melding (er is niets
 * kapot). Identiteitsregel (LI040): namen worden nooit afgekapt — de rij wrapt.
 * Rol-gating = affordance (toevoegen: medewerker/beheerder; verwijderen: beheerder —
 * het specifieke VERWIJDEREN-recht, LI037); de backend handhaaft.
 */
import { computed, ref, watch } from 'vue'
import { Button, Column, DataTable, useToast } from '@/primevue'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import { useRouter } from '@/composables/router'
import { api } from '@/api'
import { useAanstip } from '@/composables/useToonNieuweRij'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import MeldingBanner from '@/components/MeldingBanner.vue'
import RijActies from '@/components/RijActies.vue'
import IdentiteitLabel from './IdentiteitLabel.vue'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({
  componentId: { type: String, required: true },
  componentNaam: { type: String, default: '' },
})

const auth = useAuthStore()
const toast = useToast()
const router = useRouter()
const magToevoegen = computed(() => auth.hasRole('medewerker', 'beheerder'))
// Destructief gate't op het specifieke Verwijderen-recht (LI037): beheerder-only.
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

const rijen = ref([])
const laden = ref(false)
const fout = ref(null)
const { aangestiptId, aanstip } = useAanstip()

async function laad() {
  laden.value = true
  fout.value = null
  try {
    const uit = await api.organisatiegebruik.lijstVoorApplicatie({ applicatie_id: props.componentId })
    // `afdelingen_tekst` = het sorteerveld voor de Afdeling(en)-kolom (client-side
    // sorteerbaar: dit is een vaste, korte, ongepagineerde lijst — de toegestane
    // uitzondering op server-side sortering). Leeg = "afdeling onbekend".
    rijen.value = (uit ?? []).map((r) => ({ ...r, afdelingen_tekst: (r.afdelingen ?? []).join(' · ') }))
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van het gebruik is mislukt.'
  } finally {
    laden.value = false
  }
}
watch(() => props.componentId, () => laad(), { immediate: true })

// Rij-klasse: `lk-rij` (rij-acties verschijnen op de actieve rij — RijActies-contract)
// + de aanstip van een zojuist toegevoegde regel.
const rijKlasse = (data) =>
  ['lk-rij', String(aangestiptId.value) === String(data?.id) ? 'lk-aangestipt' : ''].filter(Boolean).join(' ')

// ── Toevoegen — organisatie kiezen, géén afdeling nodig ──────────────────────────
const nieuwOrgId = ref(null)
const bezig = ref(false)
const toevoegMelding = ref(null) // vriendelijke 409-melding — geen fout-toast
const pickerKey = ref(0) // remount na geslaagde toevoeging (label wissen, LI032-lijn)

// Picker-scope spiegelt de backend-regel: aard=organisatie (intern én extern — een
// burger-doelgroep is een externe organisatie en kan gebruiker zijn, ADR-038).
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })

async function voegToe() {
  if (!nieuwOrgId.value || bezig.value) return
  bezig.value = true
  toevoegMelding.value = null
  try {
    const nieuw = await api.organisatiegebruik.maak({
      organisatie_id: nieuwOrgId.value,
      applicatie_id: props.componentId,
    })
    toastSucces(toast, 'Toegevoegd')
    nieuwOrgId.value = null
    pickerKey.value += 1
    await laad()
    aanstip(nieuw?.id) // de nieuwe regel komt in beeld (scroll + highlight)
  } catch (e) {
    if (e?.status === 401) return
    if (e?.status === 409 || e?.code === 'GEBRUIK_BESTAAT') {
      toevoegMelding.value = e?.message || 'Deze organisatie staat al als gebruiker geregistreerd.'
    } else {
      toevoegMelding.value = e?.message || 'Toevoegen is mislukt.'
    }
  } finally {
    bezig.value = false
  }
}
// De melding hoort bij de geweigerde poging — weg zodra de invoer wijzigt.
watch(nieuwOrgId, () => { toevoegMelding.value = null })

// ── Verwijderen — altijd bevestiging; verfijning weigert (409), nooit stil ────────
const verwijderRij = ref(null)
const verwijderMelding = ref(null)
const verwijderBezig = ref(false)

function vraagVerwijderen(rij) {
  verwijderRij.value = rij
  verwijderMelding.value = null
}
const verwijderOmschrijving = computed(() => {
  const r = verwijderRij.value
  if (!r) return ''
  const comp = props.componentNaam || 'dit component'
  return `${r.organisatie_naam ?? 'deze organisatie'} als gebruiker van ${comp} verwijderen?`
})

async function bevestigVerwijderen() {
  const r = verwijderRij.value
  if (!r || verwijderBezig.value) return
  verwijderBezig.value = true
  verwijderMelding.value = null
  try {
    await api.organisatiegebruik.verwijder(r.id)
    toastSucces(toast, 'Verwijderd')
    verwijderRij.value = null
    await laad()
  } catch (e) {
    if (e?.status === 401) return
    // 409 GEBRUIK_HEEFT_VERFIJNING: veldwerk verdwijnt nooit stil — de melding legt uit
    // wat er eerst moet gebeuren; de dialoog blijft open.
    verwijderMelding.value = e?.message || 'Verwijderen is mislukt.'
  } finally {
    verwijderBezig.value = false
  }
}

function naarOrganisatie(rij) {
  router.push({ name: 'partij-detail', params: { id: rij.organisatie_id } })
}
</script>

<template>
  <section aria-label="Wie gebruikt dit component" class="card">
    <div class="mb-[var(--lk-space-sm)]">
      <h2 class="mb-1">Wie gebruikt dit</h2>
      <p class="max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
        Eén regel per organisatie — de afdeling mag later volgen (verfijnen doe je via de
        gebruikersgroepen).
      </p>
    </div>

    <p v-if="laden" data-testid="gebruik-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>
    <p v-else-if="fout" role="alert" data-testid="gebruik-fout" class="text-[var(--lk-color-danger)]">{{ fout }}</p>

    <template v-else>
      <!-- Tabelvorm (LI040): draagt straks óók Stand en Tranche (ADR-046 stuk 3) zonder
           herbouw — die kolommen bestaan nu bewust nog niet (geen lege koppen).
           Client-side sorteerbaar: vaste, korte, ongepagineerde lijst. -->
      <DataTable
        :value="rijen"
        :row-class="rijKlasse"
        sort-field="organisatie_naam"
        :sort-order="1"
        data-testid="gebruik-tabel"
      >
        <Column field="organisatie_naam" header="Organisatie" sortable>
          <template #body="{ data }">
            <!-- Identiteitsregel (LI040): de naam krijgt de ruimte die hij nodig heeft —
                 nooit afkappen (geen truncate; de cel wrapt). -->
            <button
              type="button"
              class="text-left font-semibold text-[var(--lk-color-primary)] hover:underline"
              :data-testid="`gebruik-org-${data.id}`"
              @click="naarOrganisatie(data)"
            >
              {{ data.organisatie_naam ?? '—' }}
            </button>
          </template>
        </Column>
        <Column field="afdelingen_tekst" header="Afdeling(en)" sortable>
          <template #body="{ data }">
            <span
              v-if="data.afdelingen?.length"
              class="flex flex-wrap gap-x-[var(--lk-space-md)] text-[length:var(--lk-text-sm)]"
              :data-testid="`gebruik-afdelingen-${data.id}`"
            >
              <!-- LI040: elke afdeling met haar volledige identiteit (org gedempt) —
                   óók al is de organisatie de rij zelf; identiteit wordt nooit ingekort. -->
              <IdentiteitLabel
                v-for="afd in data.afdelingen"
                :key="afd"
                :naam="afd"
                :organisatie="data.organisatie_naam"
              />
            </span>
            <span
              v-else
              class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
              :data-testid="`gebruik-onbekend-${data.id}`"
            >
              afdeling onbekend
            </span>
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <RijActies v-if="magVerwijderen">
              <Button
                label="Verwijderen"
                severity="danger"
                :data-testid="`gebruik-verwijder-${data.id}`"
                @click="vraagVerwijderen(data)"
              />
            </RijActies>
          </template>
        </Column>
        <template #empty>
          <span data-testid="gebruik-leeg" class="text-[var(--lk-color-text-muted)]">
            Nog geen organisaties geregistreerd{{ magToevoegen ? ' — voeg er hieronder een toe.' : '.' }}
          </span>
        </template>
      </DataTable>

      <!-- Toevoegen: grof — alleen de organisatie; geen afdeling verplicht. -->
      <div v-if="magToevoegen" class="mt-[var(--lk-space-md)] flex flex-wrap items-end gap-[var(--lk-space-sm)]">
        <label class="flex w-full max-w-xl flex-col gap-[var(--lk-space-xs)]">
          <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">
            Organisatie toevoegen
          </span>
          <ZoekSelect
            :key="pickerKey"
            v-model="nieuwOrgId"
            :zoek-functie="zoekOrganisaties"
            :weergave="(p) => p.naam"
            placeholder="Zoek een organisatie…"
            testid="gebruik-org-picker"
          />
        </label>
        <Button
          label="Toevoegen"
          data-testid="gebruik-toevoegen"
          :disabled="!nieuwOrgId || bezig"
          @click="voegToe"
        />
        <MeldingBanner
          v-if="toevoegMelding"
          class="w-full"
          soort="warn"
          :tekst="toevoegMelding"
          testid="gebruik-melding"
        />
      </div>
    </template>

    <BevestigVerwijderDialog
      :visible="!!verwijderRij"
      kop="Gebruik verwijderen"
      :bezig="verwijderBezig"
      testid="gebruik-verwijder"
      @update:visible="(v) => { if (!v) verwijderRij = null }"
      @bevestig="bevestigVerwijderen"
    >
      <!-- Het slot vervangt de omschrijving-prop → beide hier renderen: de leesbare
           regel + (na een 409) de warn-melding die uitlegt waarom het niet stil kan. -->
      {{ verwijderOmschrijving }}
      <MeldingBanner
        v-if="verwijderMelding"
        class="mt-[var(--lk-space-sm)]"
        soort="warn"
        :tekst="verwijderMelding"
        testid="gebruik-verwijder-melding"
      />
    </BevestigVerwijderDialog>
  </section>
</template>
