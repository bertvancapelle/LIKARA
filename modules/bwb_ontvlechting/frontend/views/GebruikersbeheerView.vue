<script setup>
/**
 * GebruikersbeheerView — beheerder maakt gebruikers aan vanuit LIKARA (ADR-029 Fase 4).
 *
 * Lijst van gekoppelde gebruikers (naam/email/aangemaakt) + aanmaak-dialog (persoon + Keycloak-
 * account + koppeling, server-side). Het server-gegenereerde tijdelijk wachtwoord wordt ÉÉNMALIG
 * getoond in een tweede dialog-staat met kopieerknop — nergens gepersisteerd (alleen component-
 * state tot de dialog sluit). Beheerder-only (affordance via hasRole; backend handhaaft via
 * GEBRUIKERSBEHEER). `--lk-`-tokens, geen `<style>`.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, DataTable, Column, Dialog, InputText, Tag, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { GEBRUIKER_ROL, label } from '@modules/bwb_ontvlechting/frontend/labels'
import ZoekSelect from './ZoekSelect.vue'
import AfdelingSelect from './AfdelingSelect.vue'

// ADR-029 Fase 2b — de vier toewijsbare tenant-rollen (rol-wijziging).
const ROL_OPTIES = ['viewer', 'medewerker', 'beheerder', 'auditor']

const auth = useAuthStore()
const toast = useToast()
const magBeheren = computed(() => auth.hasRole('beheerder'))

const gebruikers = ref([])
const laden = ref(false)
const fout = ref(null)

const dialogOpen = ref(false)
const bezig = ref(false)
// LI032 — een gebruiker hoort altijd bij een organisatie: eerst de organisatie kiezen (verplicht),
// die scoopt de afdeling. `organisatieId` blijft frontend-only (naar de backend gaat alleen
// `afdeling_id`; de organisatie wordt daaruit afgeleid — de gescoopte afdeling borgt de consistentie).
const form = reactive({ naam: '', email: '', organisatieId: '', afdelingId: '', functietitel: '', rol: 'medewerker' })
const fouten = reactive({})
const orgInitieel = ref('')
const afdKey = ref(0) // remount de afdeling-picker bij een org-wissel (reset de weergave)
// Tweede dialog-staat: na succes het eenmalige wachtwoord tonen (niet gepersisteerd).
const resultaat = ref(null) // { naam, wachtwoord } | null
const eersteVeld = ref(null)
let laatsteTrigger = null

// Organisatie-picker: alleen de eigen INTERNE organisatie(s) (ADR-038 scope=intern) — geen
// leveranciers/externe partijen. Een gebruiker is een inlog-account van de eigen organisatie.
const zoekInterneOrganisaties = (params) =>
  api.partijen.lijst({ ...params, aard: 'organisatie', scope: 'intern' })
const magAanmaakAfdeling = computed(() => auth.hasRole('beheerder'))

// Een andere organisatie kiezen → de al gekozen afdeling is niet meer geldig: resetten + remount.
function onOrgKies(id) {
  form.organisatieId = id || ''
  form.afdelingId = ''
  afdKey.value += 1
}

const _datum = (iso) =>
  iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : ''

async function laad() {
  laden.value = true
  fout.value = null
  try {
    // GET /gebruikers levert (Fase 2) een platte lijst — geen cursor; toon de set.
    gebruikers.value = await api.gebruikers.lijst({ limit: 100 })
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van gebruikers mislukt.'
  } finally {
    laden.value = false
  }
}

function openDialog(event) {
  laatsteTrigger = event?.currentTarget ?? document.activeElement
  Object.assign(form, { naam: '', email: '', organisatieId: '', afdelingId: '', functietitel: '', rol: 'medewerker' })
  orgInitieel.value = ''
  afdKey.value += 1
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
  // LI032 — organisatie verplicht (scoopt de afdeling); een gebruiker hoort altijd bij een organisatie.
  if (!form.organisatieId) fouten.organisatie = 'Kies een organisatie.'
  // Backend (ADR-029 Fase 2) vereist een afdeling (AFDELING_VERPLICHT) → hier ook verplicht.
  if (!form.afdelingId) fouten.afdeling = 'Kies een afdeling.'
  return Object.keys(fouten).length === 0
}

function _mapFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
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

// ── ADR-029 Fase 2b — beheer-paneel per bestaande gebruiker ─────────────────────────
const rolLabel = (r) => (r ? label(GEBRUIKER_ROL, r) : 'Onbekend')

const beheerOpen = ref(false)
const geselecteerd = ref(null) // de rij waarop beheerd wordt
const beheerRol = ref('')
const beheerNaam = ref('')
const beheerEmail = ref('')
// LI032 — organisatie/afdeling van een bestaande gebruiker wijzigen (voorgevuld op de huidige waarden).
const beheerOrganisatieId = ref('')
const beheerAfdelingId = ref('')
const beheerOrgInitieel = ref('')
const beheerAfdInitieel = ref('')
const beheerOrgKey = ref(0) // remount de organisatie-picker per geopende gebruiker (geen stale label)
const beheerAfdKey = ref(0) // remount de afdeling-picker bij een org-wissel
const beheerFouten = reactive({})
const resetWachtwoord = ref(null) // het eenmalige wachtwoord na een reset (niet gepersisteerd)
const bevestigUit = ref(false)    // inline bevestiging vóór uitschakelen
const beheerBezig = ref(false)
let beheerTrigger = null

// Eigen account: het account van de ingelogde beheerder zelf (de backend weigert hier
// uitschakelen/de-beheerrollen; de UI verbergt die affordances om de dode klik te voorkomen).
const isEigenAccount = computed(() => !!geselecteerd.value && geselecteerd.value.keycloak_sub === auth.user?.sub)
const isBeheerderRij = computed(() => geselecteerd.value?.rol === 'beheerder')

function openBeheer(rij, event) {
  beheerTrigger = event?.currentTarget ?? document.activeElement
  geselecteerd.value = rij
  beheerRol.value = rij.rol || ''
  beheerNaam.value = rij.naam || ''
  beheerEmail.value = rij.email || ''
  // LI032 — voorvullen op de huidige organisatie/afdeling (uit de verrijkte read).
  beheerOrganisatieId.value = rij.organisatie_id || ''
  beheerAfdelingId.value = rij.afdeling_id || ''
  beheerOrgInitieel.value = rij.organisatie_naam || ''
  beheerAfdInitieel.value = rij.afdeling || ''
  beheerOrgKey.value += 1 // verse organisatie-picker → toont deze gebruiker, geen stale label
  beheerAfdKey.value += 1
  Object.keys(beheerFouten).forEach((k) => delete beheerFouten[k])
  resetWachtwoord.value = null
  bevestigUit.value = false
  beheerOpen.value = true
}

// Een andere organisatie kiezen → de al gekozen afdeling is niet meer geldig: resetten + remount.
function onBeheerOrgKies(id) {
  beheerOrganisatieId.value = id || ''
  beheerAfdelingId.value = ''
  beheerAfdInitieel.value = ''
  beheerAfdKey.value += 1
}
function sluitBeheer() {
  beheerOpen.value = false
  if (beheerTrigger?.focus) setTimeout(() => beheerTrigger.focus(), 0)
}

const _GUARD = {
  LAATSTE_BEHEERDER: 'Dit is de laatste beheerder en kan niet worden uitgeschakeld of gewijzigd.',
  EIGEN_ACCOUNT: 'Je kunt je eigen account niet uitschakelen.',
  EIGEN_BEHEERROL: 'Je kunt jezelf niet de beheerrol ontnemen.',
}
function _mapBeheerFout(e, { veld = false } = {}) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
  if (veld && e?.status === 422 && Array.isArray(e.detail)) {
    let raak = false
    for (const d of e.detail) {
      const v = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (['naam', 'email'].includes(v)) { beheerFouten[v] = d.msg || 'Ongeldige waarde.'; raak = true }
    }
    if (raak) return
  }
  if (e?.code === 'EMAIL_AL_IN_GEBRUIK') { beheerFouten.email = 'Dit e-mailadres is al in gebruik.'; return }
  if (e?.code && _GUARD[e.code]) { toast.add({ severity: 'warn', summary: 'Niet toegestaan', detail: _GUARD[e.code], life: 6000 }); return }
  const detail =
    e?.status === 403 ? 'Je hebt geen rechten voor deze actie.'
    : e?.status === 404 ? 'Deze gebruiker bestaat niet (meer).'
    : e?.status === 503 ? 'Het account-systeem is even niet bereikbaar; probeer het later opnieuw.'
    : (e?.message || 'Er ging iets mis.')
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 6000 })
}

async function _herlaadEnSelecteer() {
  await laad()
  if (geselecteerd.value) {
    const ververst = gebruikers.value.find((g) => g.id === geselecteerd.value.id)
    if (ververst) geselecteerd.value = ververst
  }
}

async function doeWachtwoordReset() {
  beheerBezig.value = true
  try {
    const resp = await api.gebruikers.wachtwoordReset(geselecteerd.value.id)
    resetWachtwoord.value = resp.tijdelijk_wachtwoord // eenmalig getoond
  } catch (e) {
    _mapBeheerFout(e)
  } finally {
    beheerBezig.value = false
  }
}

async function kopieerReset() {
  try {
    await navigator.clipboard.writeText(resetWachtwoord.value)
    toast.add({ severity: 'success', summary: 'Gekopieerd', detail: 'Wachtwoord gekopieerd.', life: 2500 })
  } catch {
    toast.add({ severity: 'warn', summary: 'Kopiëren mislukt', detail: 'Selecteer en kopieer handmatig.', life: 4000 })
  }
}

async function doeRolWijzigen() {
  if (!beheerRol.value || beheerRol.value === geselecteerd.value.rol) return
  beheerBezig.value = true
  try {
    await api.gebruikers.wijzigRol(geselecteerd.value.id, beheerRol.value)
    toast.add({ severity: 'success', summary: 'Rol gewijzigd', life: 2500 })
    await _herlaadEnSelecteer()
  } catch (e) {
    _mapBeheerFout(e)
  } finally {
    beheerBezig.value = false
  }
}

async function doeStatus(actief) {
  if (!actief && !bevestigUit.value) { bevestigUit.value = true; return } // eerst bevestigen
  beheerBezig.value = true
  try {
    await api.gebruikers.wijzigStatus(geselecteerd.value.id, actief)
    bevestigUit.value = false
    toast.add({ severity: 'success', summary: actief ? 'Ingeschakeld' : 'Uitgeschakeld', life: 2500 })
    await _herlaadEnSelecteer()
  } catch (e) {
    _mapBeheerFout(e)
  } finally {
    beheerBezig.value = false
  }
}

async function doeCorrectie() {
  Object.keys(beheerFouten).forEach((k) => delete beheerFouten[k])
  if (!beheerNaam.value.trim()) beheerFouten.naam = 'Naam is verplicht.'
  if (!beheerEmail.value.trim()) beheerFouten.email = 'E-mail is verplicht.'
  else if (!_EMAIL.test(beheerEmail.value.trim())) beheerFouten.email = 'Geef een geldig e-mailadres op.'
  // LI032 — organisatie + afdeling verplicht (een gebruiker hoort altijd bij een organisatie).
  if (!beheerOrganisatieId.value) beheerFouten.organisatie = 'Kies een organisatie.'
  if (!beheerAfdelingId.value) beheerFouten.afdeling = 'Kies een afdeling.'
  if (Object.keys(beheerFouten).length) return
  beheerBezig.value = true
  try {
    // Alleen `afdeling_id` (+ naam/email) mee; de backend leidt de organisatie uit de afdeling af.
    await api.gebruikers.corrigeer(geselecteerd.value.id, {
      naam: beheerNaam.value.trim(), email: beheerEmail.value.trim(), afdeling_id: beheerAfdelingId.value || null,
    })
    toast.add({ severity: 'success', summary: 'Gegevens bijgewerkt', life: 2500 })
    await _herlaadEnSelecteer()
  } catch (e) {
    _mapBeheerFout(e, { veld: true })
  } finally {
    beheerBezig.value = false
  }
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="gebr-titel">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-md)]">
      <h1 id="gebr-titel">Gebruikersbeheer</h1>
      <Button
        v-if="magBeheren"
        label="Gebruiker toevoegen"
        data-testid="gebr-toevoegen"
        class="ml-auto"
        @click="openDialog"
      />
    </div>

    <p v-if="fout" role="alert" data-testid="gebr-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="gebr-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <DataTable :value="gebruikers" data-testid="gebruikers-tabel" class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]">
      <template #empty>
        <span data-testid="gebr-leeg" class="text-[var(--lk-color-text-muted)]">Nog geen gekoppelde gebruikers.</span>
      </template>
      <Column header="Naam"><template #body="{ data }">{{ data.naam }}</template></Column>
      <Column header="E-mail"><template #body="{ data }">{{ data.email || '—' }}</template></Column>
      <Column header="Rol">
        <template #body="{ data }">
          <span :data-testid="`gebr-rol-${data.id}`">{{ rolLabel(data.rol) }}</span>
        </template>
      </Column>
      <Column header="Status">
        <template #body="{ data }">
          <!-- enabled true → Actief, false → Uitgeschakeld, null/None → Onbekend (neutraal, geen fout). -->
          <Tag
            v-if="data.enabled === true"
            :data-testid="`gebr-status-${data.id}`"
            severity="success"
            value="Actief"
          />
          <Tag
            v-else-if="data.enabled === false"
            :data-testid="`gebr-status-${data.id}`"
            severity="danger"
            value="Uitgeschakeld"
          />
          <Tag v-else :data-testid="`gebr-status-${data.id}`" severity="secondary" value="Onbekend" />
        </template>
      </Column>
      <Column header="">
        <template #body="{ data }">
          <Button
            v-if="magBeheren"
            label="Beheren"
            severity="secondary"
            :data-testid="`gebr-beheren-${data.id}`"
            @click="openBeheer(data, $event)"
          />
        </template>
      </Column>
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
      <form v-if="!resultaat" class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="gebr-form" @submit.prevent="bevestig">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gebr-naam" class="font-semibold">Naam *</label>
          <InputText id="gebr-naam" ref="eersteVeld" v-model="form.naam" data-testid="gebr-naam" :aria-invalid="!!fouten.naam" aria-describedby="gebr-fout-naam" />
          <span v-if="fouten.naam" id="gebr-fout-naam" role="alert" data-testid="gebr-fout-naam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.naam }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gebr-email" class="font-semibold">E-mail *</label>
          <InputText id="gebr-email" v-model="form.email" type="email" data-testid="gebr-email" :aria-invalid="!!fouten.email" aria-describedby="gebr-fout-email" />
          <span v-if="fouten.email" id="gebr-fout-email" role="alert" data-testid="gebr-fout-email" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.email }}</span>
        </div>
        <!-- LI032 — eerst de organisatie (verplicht, alleen interne organisaties); die scoopt de afdeling. -->
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gebr-organisatie" class="font-semibold">Organisatie *</label>
          <ZoekSelect
            id="gebr-organisatie"
            testid="gebr-organisatie"
            :model-value="form.organisatieId"
            :zoek-functie="zoekInterneOrganisaties"
            :initieel-weergave="orgInitieel"
            :invalid="!!fouten.organisatie"
            aria-describedby="gebr-fout-organisatie"
            placeholder="Zoek een organisatie…"
            @update:model-value="onOrgKies"
          />
          <span v-if="fouten.organisatie" id="gebr-fout-organisatie" role="alert" data-testid="gebr-fout-organisatie" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.organisatie }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gebr-afdeling" class="font-semibold">Afdeling *</label>
          <!-- Uitgeschakeld tot er een organisatie is; daarna gescoped + ter-plekke-aanmaakbaar. -->
          <AfdelingSelect
            id="gebr-afdeling"
            testid="gebr-afdeling"
            :key="afdKey"
            v-model="form.afdelingId"
            :partij-id="form.organisatieId"
            :disabled="!form.organisatieId"
            :mag-aanmaken="magAanmaakAfdeling"
            :org-naam="orgInitieel"
            :placeholder="form.organisatieId ? 'Zoek een afdeling…' : 'Kies eerst een organisatie'"
          />
          <span v-if="!form.organisatieId" data-testid="gebr-afdeling-hint" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Kies eerst een organisatie.</span>
          <span v-if="fouten.afdeling" role="alert" data-testid="gebr-fout-afdeling" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.afdeling }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gebr-functietitel" class="font-semibold">Functietitel</label>
          <InputText id="gebr-functietitel" v-model="form.functietitel" data-testid="gebr-functietitel" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gebr-rol" class="font-semibold">Rol *</label>
          <select id="gebr-rol" v-model="form.rol" data-testid="gebr-rol" class="lk-veld">
            <option v-for="r in ['medewerker', 'viewer']" :key="r" :value="r">{{ label(GEBRUIKER_ROL, r) }}</option>
          </select>
        </div>
        <div class="flex justify-end gap-[var(--lk-space-md)]">
          <Button label="Annuleren" severity="secondary" data-testid="gebr-annuleer" @click="sluitDialog" />
          <Button label="Aanmaken" type="submit" :disabled="bezig" data-testid="gebr-opslaan" />
        </div>
      </form>

      <!-- Staat 2: eenmalig tijdelijk wachtwoord -->
      <div v-else class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="gebr-wachtwoord-staat">
        <p class="max-w-prose">
          Dit tijdelijke wachtwoord wordt <strong>eenmalig</strong> getoond. Geef het door aan
          <strong>{{ resultaat.naam }}</strong>; bij de eerste login moet het worden gewijzigd.
        </p>
        <div class="flex items-center gap-[var(--lk-space-sm)]">
          <code data-testid="gebr-wachtwoord" class="flex-1 rounded-[var(--lk-radius-input)] bg-[var(--lk-color-accent)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] font-mono select-all">{{ resultaat.wachtwoord }}</code>
          <Button label="Kopiëren" severity="secondary" data-testid="gebr-kopieer" @click="kopieer" />
        </div>
        <div class="flex justify-end">
          <Button label="Klaar" data-testid="gebr-klaar" @click="klaar" />
        </div>
      </div>
    </Dialog>

    <!-- ADR-029 Fase 2b — beheer-paneel: vier acties op een bestaande gebruiker. -->
    <Dialog
      v-model:visible="beheerOpen"
      modal
      :closable="false"
      :header="geselecteerd ? `Beheer — ${geselecteerd.naam}` : 'Beheer'"
      data-testid="gebr-beheer-dialog"
      @hide="sluitBeheer"
    >
      <div v-if="geselecteerd" class="flex flex-col gap-[var(--lk-space-lg)] min-w-[26rem]">
        <!-- 1. Wachtwoord opnieuw instellen -->
        <section class="flex flex-col gap-[var(--lk-space-sm)]" data-testid="gebr-beheer-wachtwoord">
          <h2>Wachtwoord opnieuw instellen</h2>
          <template v-if="!resetWachtwoord">
            <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)] max-w-prose">
              Genereert een nieuw eenmalig wachtwoord; de gebruiker wijzigt het verplicht bij de eerstvolgende login.
            </p>
            <Button label="Wachtwoord opnieuw instellen" severity="secondary" :disabled="beheerBezig" data-testid="gebr-wachtwoord-reset" class="self-start" @click="doeWachtwoordReset" />
          </template>
          <template v-else>
            <p class="text-[length:var(--lk-text-sm)] max-w-prose">
              Dit tijdelijke wachtwoord wordt <strong>eenmalig</strong> getoond. Geef het door; bij de eerste login moet het worden gewijzigd.
            </p>
            <div class="flex items-center gap-[var(--lk-space-sm)]">
              <code data-testid="gebr-reset-wachtwoord" class="flex-1 rounded-[var(--lk-radius-input)] bg-[var(--lk-color-accent)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] font-mono select-all">{{ resetWachtwoord }}</code>
              <Button label="Kopiëren" severity="secondary" data-testid="gebr-reset-kopieer" @click="kopieerReset" />
            </div>
          </template>
        </section>

        <!-- 2. Rol wijzigen -->
        <section class="flex flex-col gap-[var(--lk-space-sm)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]" data-testid="gebr-beheer-rol">
          <h2>Rol</h2>
          <template v-if="isEigenAccount && isBeheerderRij">
            <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="gebr-rol-eigen-note">Je kunt jezelf niet de beheerrol ontnemen.</p>
          </template>
          <template v-else>
            <div class="flex items-center gap-[var(--lk-space-sm)]">
              <label for="gebr-beheer-rol-select" class="sr-only">Rol</label>
              <select id="gebr-beheer-rol-select" v-model="beheerRol" data-testid="gebr-beheer-rol-select" class="lk-veld">
                <option v-for="r in ROL_OPTIES" :key="r" :value="r">{{ label(GEBRUIKER_ROL, r) }}</option>
              </select>
              <Button label="Rol wijzigen" severity="secondary" :disabled="beheerBezig || beheerRol === geselecteerd.rol" data-testid="gebr-rol-opslaan" @click="doeRolWijzigen" />
            </div>
          </template>
        </section>

        <!-- 3. Uit-/inschakelen -->
        <section v-if="!isEigenAccount" class="flex flex-col gap-[var(--lk-space-sm)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]" data-testid="gebr-beheer-status">
          <h2>Toegang</h2>
          <template v-if="geselecteerd.enabled === false">
            <Button label="Inschakelen" severity="secondary" :disabled="beheerBezig" data-testid="gebr-inschakelen" class="self-start" @click="doeStatus(true)" />
          </template>
          <template v-else>
            <p v-if="bevestigUit" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-danger)]" data-testid="gebr-uit-bevestig">Toegang wordt per direct ingetrokken. Doorgaan?</p>
            <div class="flex gap-[var(--lk-space-sm)]">
              <Button :label="bevestigUit ? 'Ja, uitschakelen' : 'Uitschakelen'" severity="danger" :disabled="beheerBezig" data-testid="gebr-uitschakelen" class="self-start" @click="doeStatus(false)" />
              <Button v-if="bevestigUit" label="Annuleren" severity="secondary" data-testid="gebr-uit-annuleer" @click="bevestigUit = false" />
            </div>
          </template>
        </section>
        <p v-else class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]" data-testid="gebr-status-eigen-note">Je kunt je eigen account niet uitschakelen.</p>

        <!-- 4. Gegevens corrigeren -->
        <section class="flex flex-col gap-[var(--lk-space-sm)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]" data-testid="gebr-beheer-gegevens">
          <h2>Gegevens</h2>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <label for="gebr-beheer-naam" class="font-semibold">Naam *</label>
            <InputText id="gebr-beheer-naam" v-model="beheerNaam" data-testid="gebr-beheer-naam" :aria-invalid="!!beheerFouten.naam" aria-describedby="gebr-beheer-fout-naam" />
            <span v-if="beheerFouten.naam" id="gebr-beheer-fout-naam" role="alert" data-testid="gebr-beheer-fout-naam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ beheerFouten.naam }}</span>
          </div>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <label for="gebr-beheer-email" class="font-semibold">E-mail *</label>
            <InputText id="gebr-beheer-email" v-model="beheerEmail" type="email" data-testid="gebr-beheer-email" :aria-invalid="!!beheerFouten.email" aria-describedby="gebr-beheer-fout-email" />
            <span v-if="beheerFouten.email" id="gebr-beheer-fout-email" role="alert" data-testid="gebr-beheer-fout-email" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ beheerFouten.email }}</span>
          </div>
          <!-- LI032 — organisatie + afdeling wijzigen (voorgevuld); zelfde opzet als aanmaken. -->
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <label for="gebr-beheer-organisatie" class="font-semibold">Organisatie *</label>
            <ZoekSelect
              id="gebr-beheer-organisatie"
              testid="gebr-beheer-organisatie"
              :key="beheerOrgKey"
              :model-value="beheerOrganisatieId"
              :zoek-functie="zoekInterneOrganisaties"
              :initieel-weergave="beheerOrgInitieel"
              :invalid="!!beheerFouten.organisatie"
              aria-describedby="gebr-beheer-fout-organisatie"
              placeholder="Zoek een organisatie…"
              @update:model-value="onBeheerOrgKies"
            />
            <span v-if="beheerFouten.organisatie" id="gebr-beheer-fout-organisatie" role="alert" data-testid="gebr-beheer-fout-organisatie" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ beheerFouten.organisatie }}</span>
          </div>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <label for="gebr-beheer-afdeling" class="font-semibold">Afdeling *</label>
            <AfdelingSelect
              id="gebr-beheer-afdeling"
              testid="gebr-beheer-afdeling"
              :key="beheerAfdKey"
              v-model="beheerAfdelingId"
              :partij-id="beheerOrganisatieId"
              :initieel-weergave="beheerAfdInitieel"
              :disabled="!beheerOrganisatieId"
              :mag-aanmaken="magAanmaakAfdeling"
              :org-naam="beheerOrgInitieel"
              :placeholder="beheerOrganisatieId ? 'Zoek een afdeling…' : 'Kies eerst een organisatie'"
            />
            <span v-if="!beheerOrganisatieId" data-testid="gebr-beheer-afdeling-hint" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Kies eerst een organisatie.</span>
            <span v-if="beheerFouten.afdeling" role="alert" data-testid="gebr-beheer-fout-afdeling" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ beheerFouten.afdeling }}</span>
          </div>
          <Button label="Gegevens opslaan" severity="secondary" :disabled="beheerBezig" data-testid="gebr-gegevens-opslaan" class="self-start" @click="doeCorrectie" />
        </section>

        <div class="flex justify-end border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]">
          <Button label="Sluiten" data-testid="gebr-beheer-sluit" @click="sluitBeheer" />
        </div>
      </div>
    </Dialog>
  </section>
</template>
