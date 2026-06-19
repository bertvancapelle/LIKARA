<script setup>
/**
 * GebruikersbeheerView — beheerder maakt gebruikers aan vanuit KILARA (ADR-029 Fase 4).
 *
 * Lijst van gekoppelde gebruikers (naam/email/aangemaakt) + aanmaak-dialog (persoon + Keycloak-
 * account + koppeling, server-side). Het server-gegenereerde tijdelijk wachtwoord wordt ÉÉNMALIG
 * getoond in een tweede dialog-staat met kopieerknop — nergens gepersisteerd (alleen component-
 * state tot de dialog sluit). Beheerder-only (affordance via hasRole; backend handhaaft via
 * GEBRUIKERSBEHEER). `--cd-`-tokens, geen `<style>`.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, DataTable, Column, Dialog, InputText, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { GEBRUIKER_ROL, label } from '@modules/bwb_ontvlechting/frontend/labels'
import ZoekSelect from './ZoekSelect.vue'

const auth = useAuthStore()
const toast = useToast()
const magBeheren = computed(() => auth.hasRole('beheerder'))

const gebruikers = ref([])
const laden = ref(false)
const fout = ref(null)

const dialogOpen = ref(false)
const bezig = ref(false)
const form = reactive({ naam: '', email: '', afdelingId: '', functietitel: '', rol: 'medewerker' })
const fouten = reactive({})
// Tweede dialog-staat: na succes het eenmalige wachtwoord tonen (niet gepersisteerd).
const resultaat = ref(null) // { naam, wachtwoord } | null
const eersteVeld = ref(null)
let laatsteTrigger = null

// Afdeling-keuze: server-side zoeken op aard=organisatie_eenheid (hergebruik partijen-lijst).
const zoekAfdelingen = (params) => api.partijen.lijst({ ...params, aard: 'organisatie_eenheid' })

const _datum = (iso) =>
  iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : ''

async function laad() {
  laden.value = true
  fout.value = null
  try {
    // GET /gebruikers levert (Fase 2) een platte lijst — geen cursor; toon de set.
    gebruikers.value = await api.gebruikers.lijst({ limit: 100 })
  } catch (e) {
    fout.value = e?.message || 'Laden van gebruikers mislukt.'
  } finally {
    laden.value = false
  }
}

function openDialog(event) {
  laatsteTrigger = event?.currentTarget ?? document.activeElement
  Object.assign(form, { naam: '', email: '', afdelingId: '', functietitel: '', rol: 'medewerker' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
  resultaat.value = null
  dialogOpen.value = true
}

function sluitDialog() {
  dialogOpen.value = false
  if (laatsteTrigger?.focus) setTimeout(() => laatsteTrigger.focus(), 0)
}

const _EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

function _valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.naam.trim()) fouten.naam = 'Naam is verplicht.'
  if (!form.email.trim()) fouten.email = 'E-mail is verplicht.'
  else if (!_EMAIL.test(form.email.trim())) fouten.email = 'Geef een geldig e-mailadres op.'
  // Backend (ADR-029 Fase 2) vereist een afdeling (AFDELING_VERPLICHT) → hier ook verplicht.
  if (!form.afdelingId) fouten.afdeling = 'Kies een afdeling.'
  return Object.keys(fouten).length === 0
}

function _mapFout(e) {
  // Native 422 (Pydantic) → veldfouten op loc.
  if (e?.status === 422 && Array.isArray(e.detail)) {
    for (const d of e.detail) {
      const veld = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (veld && veld in fouten === false && ['naam', 'email', 'functietitel'].includes(veld)) {
        fouten[veld] = d.msg || 'Ongeldige waarde.'
      }
    }
    if (Object.keys(fouten).length) return
  }
  // Envelope-fouten met code.
  if (e?.code === 'EMAIL_AL_IN_GEBRUIK') { fouten.email = e.message || 'Dit e-mailadres is al in gebruik.'; return }
  if (e?.code === 'AFDELING_VERPLICHT' || e?.code === 'ONGELDIGE_AFDELING') {
    fouten.afdeling = e.message || 'Ongeldige of ontbrekende afdeling.'; return
  }
  const detail =
    e?.status === 403 ? 'Je hebt geen rechten voor deze actie.'
    : e?.status === 503 ? 'Gebruiker kon niet worden aangemaakt in het identiteitssysteem; probeer opnieuw.'
    : e?.status === 409 ? (e?.message || 'Conflict.')
    : (e?.message || 'Er ging iets mis.')
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 6000 })
}

async function bevestig() {
  if (!_valideer()) return
  bezig.value = true
  try {
    const data = {
      naam: form.naam.trim(),
      email: form.email.trim(),
      afdeling_id: form.afdelingId || null,
      functietitel: form.functietitel.trim() || null,
      rol: form.rol,
    }
    const resp = await api.gebruikers.maak(data)
    resultaat.value = { naam: resp.gebruiker?.naam || data.naam, wachtwoord: resp.tijdelijk_wachtwoord }
  } catch (e) {
    _mapFout(e)
  } finally {
    bezig.value = false
  }
}

async function kopieer() {
  try {
    await navigator.clipboard.writeText(resultaat.value.wachtwoord)
    toast.add({ severity: 'success', summary: 'Gekopieerd', detail: 'Wachtwoord gekopieerd.', life: 2500 })
  } catch {
    toast.add({ severity: 'warn', summary: 'Kopiëren mislukt', detail: 'Selecteer en kopieer handmatig.', life: 4000 })
  }
}

async function klaar() {
  sluitDialog()
  resultaat.value = null
  await laad()
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="gebr-titel">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
      <h1 id="gebr-titel" class="text-[length:var(--cd-text-xl)] font-semibold">Gebruikersbeheer</h1>
      <Button
        v-if="magBeheren"
        label="Gebruiker toevoegen"
        size="small"
        data-testid="gebr-toevoegen"
        class="ml-auto"
        @click="openDialog"
      />
    </div>

    <p v-if="fout" role="alert" data-testid="gebr-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="gebr-laden" class="text-[var(--cd-color-text-muted)]">Laden…</p>

    <DataTable :value="gebruikers" data-testid="gebruikers-tabel" class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]">
      <template #empty>
        <span data-testid="gebr-leeg" class="text-[var(--cd-color-text-muted)]">Nog geen gekoppelde gebruikers.</span>
      </template>
      <Column header="Naam"><template #body="{ data }">{{ data.naam }}</template></Column>
      <Column header="E-mail"><template #body="{ data }">{{ data.email || '—' }}</template></Column>
      <Column header="Aangemaakt op"><template #body="{ data }">{{ _datum(data.aangemaakt_op) }}</template></Column>
    </DataTable>

    <!-- Aanmaak-dialog: twee staten (formulier → eenmalig wachtwoord). -->
    <Dialog
      v-model:visible="dialogOpen"
      modal
      :closable="false"
      :header="resultaat ? 'Gebruiker aangemaakt' : 'Gebruiker toevoegen'"
      data-testid="gebr-dialog"
      @show="eersteVeld?.$el?.focus?.() ?? eersteVeld?.focus?.()"
      @hide="sluitDialog"
    >
      <!-- Staat 1: formulier -->
      <form v-if="!resultaat" class="flex flex-col gap-[var(--cd-space-md)] min-w-[24rem]" data-testid="gebr-form" @submit.prevent="bevestig">
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gebr-naam" class="font-semibold">Naam *</label>
          <InputText id="gebr-naam" ref="eersteVeld" v-model="form.naam" data-testid="gebr-naam" :aria-invalid="!!fouten.naam" aria-describedby="gebr-fout-naam" />
          <span v-if="fouten.naam" id="gebr-fout-naam" role="alert" data-testid="gebr-fout-naam" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.naam }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gebr-email" class="font-semibold">E-mail *</label>
          <InputText id="gebr-email" v-model="form.email" type="email" data-testid="gebr-email" :aria-invalid="!!fouten.email" aria-describedby="gebr-fout-email" />
          <span v-if="fouten.email" id="gebr-fout-email" role="alert" data-testid="gebr-fout-email" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.email }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gebr-afdeling" class="font-semibold">Afdeling *</label>
          <ZoekSelect
            v-model="form.afdelingId"
            :zoek-functie="zoekAfdelingen"
            placeholder="Zoek een afdeling…"
            testid="gebr-afdeling"
          />
          <span v-if="fouten.afdeling" role="alert" data-testid="gebr-fout-afdeling" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.afdeling }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gebr-functietitel" class="font-semibold">Functietitel</label>
          <InputText id="gebr-functietitel" v-model="form.functietitel" data-testid="gebr-functietitel" />
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="gebr-rol" class="font-semibold">Rol *</label>
          <select id="gebr-rol" v-model="form.rol" data-testid="gebr-rol" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
            <option v-for="r in ['medewerker', 'viewer']" :key="r" :value="r">{{ label(GEBRUIKER_ROL, r) }}</option>
          </select>
        </div>
        <div class="flex justify-end gap-[var(--cd-space-md)]">
          <Button label="Annuleren" severity="secondary" data-testid="gebr-annuleer" @click="sluitDialog" />
          <Button label="Aanmaken" type="submit" :disabled="bezig" data-testid="gebr-opslaan" />
        </div>
      </form>

      <!-- Staat 2: eenmalig tijdelijk wachtwoord -->
      <div v-else class="flex flex-col gap-[var(--cd-space-md)] min-w-[24rem]" data-testid="gebr-wachtwoord-staat">
        <p class="max-w-prose">
          Dit tijdelijke wachtwoord wordt <strong>eenmalig</strong> getoond. Geef het door aan
          <strong>{{ resultaat.naam }}</strong>; bij de eerste login moet het worden gewijzigd.
        </p>
        <div class="flex items-center gap-[var(--cd-space-sm)]">
          <code data-testid="gebr-wachtwoord" class="flex-1 rounded-[var(--cd-radius-input)] bg-[var(--cd-color-accent)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] font-mono select-all">{{ resultaat.wachtwoord }}</code>
          <Button label="Kopiëren" severity="secondary" data-testid="gebr-kopieer" @click="kopieer" />
        </div>
        <div class="flex justify-end">
          <Button label="Klaar" data-testid="gebr-klaar" @click="klaar" />
        </div>
      </div>
    </Dialog>
  </section>
</template>
