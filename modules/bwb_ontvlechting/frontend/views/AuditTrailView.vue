<script setup>
/**
 * AuditTrailView — audit-spoor lezen (ADR-029 Fase 3a). Beheerder/auditor beantwoordt
 * "wie deed wat, wanneer, op welk onderdeel". Correlatie-gegroepeerde gebeurtenissen
 * (nieuwste eerst, keyset "Meer laden"); de driver-handeling vat de gebeurtenis samen,
 * afgeleide gevolgen worden als telling getoond (volledige diff-weergave is een follow-up).
 *
 * Filters v1 (AND): naam (vrije-tekst-fragment → backend resolveert naam→sub), periode (van/tot),
 * component (ZoekSelect), handeling. Backend handhaaft AUDITLOG.LEZEN; nav is affordance.
 * `--lk-`-tokens, geen `<style>`.
 */
import { reactive, ref } from 'vue'
import { Button, Column, DataTable, InputText } from '@/primevue'
import { api } from '@/api'
import { AUDIT_ACTIE, AUDIT_ENTITEIT, actorWeergave, diffWeergave, label } from '@modules/bwb_ontvlechting/frontend/labels'
import ZoekSelect from './ZoekSelect.vue'
import LijstKop from '@/components/LijstKop.vue'
import ZoektermMelding from '@/components/ZoektermMelding.vue'
import { schoonZoekterm } from '@/zoekterm'

const gebeurtenissen = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const filters = reactive({ actor_naam: '', component_id: '', actie: '', van: '', tot: '' })
// LI051 — opgeschoonde "wie"-term voor de melding (leeg = geen melding). Eén bron: schoonZoekterm.
const zoekMelding = ref('')
const uitgeklapt = ref({}) // LI019 — expandedRows-map { correlatie_id: true } (DataTable dataKey-vorm)

// LI019 — Onderdeel: entiteit-type + objectnaam (fallback: entiteit_id bij verwijderd/naamloos object).
function _onderdeel(d) {
  const type = label(AUDIT_ENTITEIT, d.entiteit_type)
  const naam = d.entiteit_naam || d.entiteit_id
  return naam ? `${type} — ${naam}` : type
}
// LI019 — diff-uitklap aan/uit (DataTable rendert de #expansion-rij voor keys in deze map).
function toggleRij(data) {
  const id = data.correlatie_id
  const next = { ...uitgeklapt.value }
  if (next[id]) delete next[id]
  else next[id] = true
  uitgeklapt.value = next
}
const _isOpen = (data) => !!uitgeklapt.value[data.correlatie_id]

const zoekComponenten = (params) => api.componenten.lijst({ ...params })

const _datum = (iso) =>
  iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : ''

// LI048 — de gebeurtenis DRAAGT zijn eigen samenvatting; de UI leidt hem niet opnieuw af.
// Voorheen stond hier `records[0]`, en dat was stelselmatig de betekenisloze supertype-rij:
// "Element — 9f1282d4… · Aangemaakt". De service kiest nu de eerste regel die iets zegt.
// De terugval op `records[0]` is er alleen voor oudere antwoorden zonder de nieuwe velden.
function _driver(g) {
  if (g?.entiteit_type) return g
  return (g?.records && g.records[0]) || {}
}
// Alleen betekenisdragende gevolgen tellen — een supertype-rij zegt slechts dát er iets bestaat,
// en dat weet je al uit de regel zelf. Zonder deze correctie droeg élke aanmaak "(+1 afgeleid)".
function _afgeleid(g) {
  const n = g?.aantal_afgeleid ?? Math.max(0, (g?.records?.length || 1) - 1)
  return n > 0 ? ` (+${n} afgeleid)` : ''
}

function _params(extra = {}) {
  const p = { limit: 25 }
  if (filters.actor_naam.trim()) p.actor_naam = filters.actor_naam.trim()
  if (filters.component_id) p.component_id = filters.component_id
  if (filters.actie) p.actie = filters.actie
  if (filters.van) p.van = new Date(filters.van).toISOString()
  if (filters.tot) p.tot = new Date(filters.tot).toISOString()
  return { ...p, ...extra }
}

async function laad({ meer = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    // LI051 — schoon de "wie"-zoekterm op (onzichtbare tekens weg, NFC); toon de opgeschoonde
    // term en meld wat er is weggehaald. Dezelfde regel als de achterkant (`schoonZoekterm`).
    const { schoon, ietsWeggehaald } = schoonZoekterm(filters.actor_naam)
    if (schoon !== filters.actor_naam) filters.actor_naam = schoon
    zoekMelding.value = ietsWeggehaald && schoon ? schoon : ''
    const pagina = await api.auditlog.lijst(_params(meer && cursor.value ? { after: cursor.value } : {}))
    const items = pagina.items || []
    gebeurtenissen.value = meer ? [...gebeurtenissen.value, ...items] : items
    cursor.value = pagina.volgende_cursor || null
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van het auditspoor mislukt.'
  } finally {
    laden.value = false
  }
}

function pasToe() {
  cursor.value = null // filterwijziging → terug naar de eerste pagina
  laad()
}

function wis() {
  Object.assign(filters, { actor_naam: '', component_id: '', actie: '', van: '', tot: '' })
  pasToe()
}

laad()
</script>

<template>
  <section aria-labelledby="audit-titel">
    <!-- LI048 snede 2 — de gedeelde kop. Auditlog is géén andere soort scherm: de consultant
         komt hier om iets terug te vinden, dezelfde beweging als op Componenten. Staat de
         besturing hier ergens anders, dan moet hij juist op het scherm waar hij uitzoekt wát er
         gebeurd is, opnieuw leren hoe het werkt. Twee van de vier onderdelen ontbreken (geen
         filtervenster, geen aanmaakactie) — en dat is precies waar regel 3 voor is.

         ÉÉN functioneel verschil blijft: de Zoeken-knop is EXPLICIET. Op een auditlog kunnen
         heel veel regels staan; elke toetsaanslag een zoekopdracht laten afvuren is daar geen
         dienst. Het veld luistert dus alleen naar Enter (`@keyup.enter`), nooit naar `@input`.
         Dat verschil zit in het gedrag, niet in de vorm — de knop staat naast het veld, niet in
         het actie-slot: hij maakt niets aan, hij voert de zoekopdracht uit. -->
    <LijstKop titel="Auditlog" titel-id="audit-titel">
      <template #zoek>
        <div class="flex items-center gap-[var(--lk-space-sm)]">
          <label for="filter-naam" class="sr-only">Wie</label>
          <input
            id="filter-naam"
            v-model="filters.actor_naam"
            type="search"
            maxlength="255"
            data-testid="filter-naam"
            placeholder="Zoek op wie…"
            class="lk-veld w-full"
            @keyup.enter="pasToe"
          />
          <Button label="Zoeken" data-testid="audit-toepassen" class="shrink-0" @click="pasToe" />
        </div>
      </template>
    </LijstKop>

    <!-- LI051 — melding bij onzichtbare tekens in de "wie"-zoekterm: direct onder het zoekveld
         (geen aantal hier). Alleen zichtbaar als er werkelijk iets is weggehaald. -->
    <ZoektermMelding v-if="zoekMelding" :term="zoekMelding" class="mb-[var(--lk-space-md)]" />

    <!-- Filterbalk — blijft onder de kop staan; deze vier verfijnen de zoekopdracht. -->
    <div class="flex flex-wrap items-end gap-[var(--lk-space-md)] mb-[var(--lk-space-md)]">
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="filter-van" class="text-[length:var(--lk-text-sm)] font-semibold">Van</label>
        <input id="filter-van" v-model="filters.van" type="date" data-testid="filter-van" class="lk-veld" @change="pasToe" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="filter-tot" class="text-[length:var(--lk-text-sm)] font-semibold">Tot</label>
        <input id="filter-tot" v-model="filters.tot" type="date" data-testid="filter-tot" class="lk-veld" @change="pasToe" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)] min-w-[14rem]">
        <!-- LI048 — heette "Onderdeel", en dat beloofde meer dan het veld waarmaakt: hier zijn
             alléén componenten kiesbaar, terwijl de KOLOM Onderdeel ook checklistvragen,
             werkpakketten en partijen toont. Wie op een checklistvraag zocht, kwam er nooit —
             zonder dat iets dat aangaf. Het filter heet nu naar wat het doet; de kolom houdt
             zijn naam, want die toont wél alles. Dat verschil is nu eerlijk.
             Het filter dekt álles wat met dit component gebeurde, inclusief zijn koppelingen
             (zie `_record_filters` in auditlog_service). Wordt het veld ooit breder dan
             componenten, dan verandert deze naam mee — zie OPVOLGPUNTEN (na-MVP). -->
        <label for="filter-component" class="text-[length:var(--lk-text-sm)] font-semibold">Component</label>
        <ZoekSelect v-model="filters.component_id" :zoek-functie="zoekComponenten" placeholder="Kies een component…" testid="filter-component" @update:modelValue="pasToe" />
      </div>
      <div class="flex flex-col gap-[var(--lk-space-xs)]">
        <label for="filter-actie" class="text-[length:var(--lk-text-sm)] font-semibold">Handeling</label>
        <select id="filter-actie" v-model="filters.actie" data-testid="filter-actie" class="lk-veld" @change="pasToe">
          <option value="">Alle</option>
          <option v-for="a in ['create', 'update', 'delete', 'derive']" :key="a" :value="a">{{ label(AUDIT_ACTIE, a) }}</option>
        </select>
      </div>
      <Button label="Wissen" severity="secondary" data-testid="audit-wissen" @click="wis" />
    </div>

    <p v-if="fout" role="alert" data-testid="audit-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <DataTable
      :value="gebeurtenissen"
      data-testid="audit-tabel"
      v-model:expandedRows="uitgeklapt"
      dataKey="correlatie_id"
      class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]"
    >
      <template #empty>
        <span data-testid="audit-leeg" class="text-[var(--lk-color-text-muted)]">{{ laden ? 'Laden…' : 'Geen gebeurtenissen gevonden.' }}</span>
      </template>
      <Column header="" style="width: 3rem">
        <template #body="{ data }">
          <button
            type="button"
            :data-testid="`audit-toggle-${data.correlatie_id}`"
            :aria-expanded="_isOpen(data)"
            aria-label="Toon wijziging-details"
            class="px-1 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)]"
            @click="toggleRij(data)"
          >{{ _isOpen(data) ? '▾' : '▸' }}</button>
        </template>
      </Column>
      <Column header="Wie"><template #body="{ data }"><span data-testid="audit-wie">{{ actorWeergave(data) }}</span></template></Column>
      <Column header="Wanneer"><template #body="{ data }">{{ _datum(data.tijdstip) }}</template></Column>
      <Column header="Onderdeel"><template #body="{ data }"><span data-testid="audit-onderdeel">{{ _onderdeel(_driver(data)) }}</span></template></Column>
      <Column header="Handeling"><template #body="{ data }">{{ label(AUDIT_ACTIE, _driver(data).actie) }}{{ _afgeleid(data) }}</template></Column>
      <template #expansion="{ data }">
        <div data-testid="audit-diff" class="px-[var(--lk-space-lg)] py-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
          <div v-for="r in data.records" :key="r.id" class="mb-[var(--lk-space-sm)]">
            <p class="font-semibold">{{ _onderdeel(r) }} · {{ label(AUDIT_ACTIE, r.actie) }}</p>
            <template v-if="diffWeergave(r).regels.length">
              <p v-if="diffWeergave(r).intro" class="text-[var(--lk-color-text-muted)]">{{ diffWeergave(r).intro }}</p>
              <ul class="ml-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
                <!-- LI048 — een korte waarde leest het best als één regel (`van → naar`); een
                     lange niet. Bij een beschrijving van twintig woorden met vier verschil aan
                     het eind moet je in één doorlopende regel eerst zoeken waar de ene ophoudt.
                     Onder elkaar, op dezelfde beginpositie, loopt het oog beide langs tot ze
                     uiteenlopen. De regel past zichzelf toe: past het niet, dan gestapeld. -->
                <li v-for="(regel, i) in diffWeergave(r).regels" :key="i" data-testid="audit-diff-regel">
                  <template v-if="regel.gestapeld">
                    <span class="font-medium">{{ regel.veld }}</span>
                    <span class="mt-[var(--lk-space-xs)] grid grid-cols-[auto_1fr] gap-x-[var(--lk-space-sm)]" data-testid="audit-diff-gestapeld">
                      <span class="text-[var(--lk-color-text-muted)]">Was:</span><span>{{ regel.was }}</span>
                      <span class="text-[var(--lk-color-text-muted)]">Nu:</span><span>{{ regel.nu }}</span>
                    </span>
                  </template>
                  <template v-else>{{ regel.tekst }}</template>
                </li>
              </ul>
            </template>
            <p v-else class="ml-[var(--lk-space-md)] italic text-[var(--lk-color-text-muted)]">Geen velddetails vastgelegd.</p>
          </div>
        </div>
      </template>
    </DataTable>

    <div v-if="cursor" class="mt-[var(--lk-space-md)] flex justify-center">
      <Button label="Meer laden" severity="secondary" :disabled="laden" data-testid="audit-meer" @click="laad({ meer: true })" />
    </div>
  </section>
</template>
