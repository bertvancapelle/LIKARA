<script setup>
/**
 * SignaleringView — coherent Signalering-scherm (ADR-035).
 *
 * Twee tabs:
 *  - "Registratiegaten" — alle actieve signaaltypen, gegroepeerd per ernst (🔴 kritiek / 🟡 aandacht),
 *    read-only via `GET /signalering/registratiegaten`; per type een lijst met doorkliklink.
 *  - "Plaatsing" — de bestaande PlaatsingSignalenView, ongewijzigd ingebed.
 *
 * Read-only en informatief: signalering blokkeert niets en past niets aan.
 */
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api'
import { detailRoute } from '@/detailIngang'
import { humaniseer, label, NORM_FEIT_LABEL } from '@modules/bwb_ontvlechting/frontend/labels'
import PlaatsingSignalenView from '@/views/PlaatsingSignalenView.vue'
import WerkvoorraadPlekView from '@modules/bwb_ontvlechting/frontend/views/WerkvoorraadPlekView.vue'

// Config per ernst: signaaltype-sleutel → label + link-soort (+ toon lifecycle-badge).
const GROEPEN = {
  kritiek: [
    { key: 'component_zonder_eigenaar', label: 'Component zonder eigenaar', link: 'component', lc: true },
    { key: 'component_zonder_verantwoordelijke', label: 'Component zonder verantwoordelijke', link: 'component', lc: true },
    // ADR-028 slice 4 — BIV pas compleet als B, I én V staan.
    { key: 'biv_classificatie_onvolledig', label: 'BIV-classificatie onvolledig', link: 'component', lc: true },
  ],
  aandacht: [
    { key: 'component_zonder_gebruikersgroep', label: 'Component zonder gebruikersgroep', link: 'component' },
    { key: 'component_geisoleerd', label: 'Component zonder koppeling (geïsoleerd)', link: 'component' },
    { key: 'contract_zonder_component', label: 'Contract zonder gekoppeld component', link: 'contract' },
    { key: 'gebruikersgroep_zonder_organisatie', label: 'Gebruikersgroep zonder organisatie', link: null },
    // ADR-036 stap C — grof gebruiksfeit zonder afdeling eronder; link naar de applicatie.
    { key: 'gebruiksfeit_zonder_verfijning', label: 'Gebruik bekend, detaillering ontbreekt', link: 'applicatie' },
    { key: 'object_zonder_roltoewijzing', label: 'Object zonder roltoewijzing', link: 'object' },
  ],
}

const tab = ref('registratiegaten')
const data = ref({ kritiek: {}, aandacht: {} })
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)
// Slice 4a (besluit 1) — de verschoven lat: [{feit, aantal, componenten:[{id,naam}]}].
const verschovenLat = ref([])

const lcLabel = (s) => (s ? humaniseer(s) : '—')
const items = (ernst, key) => data.value?.[ernst]?.[key] || []
const totaal = computed(() => {
  let n = 0
  for (const ernst of ['kritiek', 'aandacht']) for (const g of GROEPEN[ernst]) n += items(ernst, g.key).length
  return n
})
function linkVoor(item, soort) {
  // LI046 — via de gedeelde ingang; een soort zonder detailscherm geeft null (geen link).
  if (soort === 'component') return detailRoute('component', item.id)
  // ADR-036 — het grof-feit-item draagt zijn eigen id (v-key) + de applicatie als linkdoel.
  if (soort === 'applicatie') return detailRoute('component', item.applicatie_id)
  if (soort === 'contract') return detailRoute('contract', item.id)
  if (soort === 'object') return detailRoute(item.entiteit_type, item.id)
  return null
}

async function laadGaten() {
  laden.value = true
  fout.value = null
  try {
    const r = await api.signalering.registratiegaten()
    data.value = { kritiek: r?.kritiek || {}, aandacht: r?.aandacht || {} }
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de registratiegaten mislukt.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
  try {
    verschovenLat.value = (await api.componentNormen.verschovenLat()) || []
  } catch {
    verschovenLat.value = []  // fail-safe: geen sectie (geen ruis)
  }
}
const _datum = (iso) => (iso ? new Date(iso).toLocaleDateString('nl-NL', { dateStyle: 'medium' }) : '')
onMounted(laadGaten)
</script>

<template>
  <section aria-labelledby="signalering-titel">
    <h1
      id="signalering-titel"
      class="mb-[var(--lk-space-sm)] text-[var(--lk-color-primary)]"
    >
      Signalering
    </h1>

    <div role="tablist" aria-label="Signalering" class="mb-[var(--lk-space-md)] flex gap-1 border-b border-[var(--lk-color-border)]">
      <button
        type="button" role="tab" data-testid="sig-tab-registratiegaten"
        :aria-selected="tab === 'registratiegaten'"
        :class="['h-10 rounded-t-[var(--lk-radius-btn)] px-[var(--lk-space-md)] text-[length:var(--lk-text-sm)]', tab === 'registratiegaten' ? 'bg-[var(--lk-color-primary)] font-semibold text-white' : 'hover:bg-[var(--lk-color-accent)]']"
        @click="tab = 'registratiegaten'"
      >Registratiegaten</button>
      <button
        type="button" role="tab" data-testid="sig-tab-plaatsing"
        :aria-selected="tab === 'plaatsing'"
        :class="['h-10 rounded-t-[var(--lk-radius-btn)] px-[var(--lk-space-md)] text-[length:var(--lk-text-sm)]', tab === 'plaatsing' ? 'bg-[var(--lk-color-primary)] font-semibold text-white' : 'hover:bg-[var(--lk-color-accent)]']"
        @click="tab = 'plaatsing'"
      >Plaatsing</button>
      <!-- ADR-051 gate 3 — de plek-werkvoorraad (nieuwe naam: "plaatsingsignaal" was bezet). -->
      <button
        type="button" role="tab" data-testid="sig-tab-werkvoorraad"
        :aria-selected="tab === 'werkvoorraad'"
        :class="['h-10 rounded-t-[var(--lk-radius-btn)] px-[var(--lk-space-md)] text-[length:var(--lk-text-sm)]', tab === 'werkvoorraad' ? 'bg-[var(--lk-color-primary)] font-semibold text-white' : 'hover:bg-[var(--lk-color-accent)]']"
        @click="tab = 'werkvoorraad'"
      >Werkvoorraad</button>
    </div>

    <!-- Tab 1 — Registratiegaten (gegroepeerd per ernst) -->
    <div v-show="tab === 'registratiegaten'" role="tabpanel" data-testid="sig-panel-registratiegaten">
      <p v-if="fout" role="alert" data-testid="sig-fout" class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">{{ fout }}</p>
      <p v-if="laden && !eersteGeladen" data-testid="sig-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

      <!-- Slice 4a (besluit 1) — VERSCHOVEN LAT: eigen neutrale sectie bovenaan, vóór de gewone
           gaten. Deze ontstonden niet doordat iemand iets naliet, maar doordat de organisatie haar
           lat verzette. Gedempt grijs + ↔, géén 🔴/🟡. Eén regel per verplicht gesteld feit. -->
      <section
        v-if="verschovenLat.length"
        data-testid="sig-verschoven-lat"
        class="mb-[var(--lk-space-lg)] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-md)] py-[var(--lk-space-md)]"
      >
        <h2 class="flex items-center gap-[var(--lk-space-xs)] text-[var(--lk-color-text-muted)]">
          <span aria-hidden="true">↔</span> De lat is verschoven
        </h2>
        <p class="mb-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          De organisatie heeft haar norm aangescherpt. Deze eerder klaar verklaarde componenten missen nu
          een verplicht gesteld feit — geen nalatigheid, maar werk dat erbij is gekomen.
        </p>
        <div
          v-for="rij in verschovenLat"
          :key="rij.feit"
          class="mb-[var(--lk-space-md)]"
          :data-testid="`sig-verschoven-${rij.feit}`"
        >
          <p class="mb-1 text-[length:var(--lk-text-sm)] font-semibold text-[var(--lk-color-text)]">
            {{ label(NORM_FEIT_LABEL, rij.feit) }} — {{ rij.aantal }} {{ rij.aantal === 1 ? 'component' : 'componenten' }}
          </p>
          <!-- Besluit 5 — wanneer/door wie de lat verschoof (uit het audit-spoor); alleen als bekend. -->
          <p
            v-if="rij.verschoven_door"
            :data-testid="`sig-verschoven-meta-${rij.feit}`"
            class="mb-1 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
          >
            verplicht gesteld door {{ rij.verschoven_door }}<template v-if="rij.verschoven_op"> · {{ _datum(rij.verschoven_op) }}</template>
          </p>
          <ul class="flex flex-col gap-0.5">
            <li
              v-for="c in rij.componenten"
              :key="c.id"
              :data-testid="`sig-verschoven-${rij.feit}-${c.id}`"
              class="text-[length:var(--lk-text-sm)]"
            >
              <router-link :to="detailRoute('component', c.id)" class="text-[var(--lk-color-primary)] hover:underline">{{ c.naam }}</router-link>
            </li>
          </ul>
        </div>
      </section>

      <p
        v-if="eersteGeladen && !laden && totaal === 0"
        data-testid="sig-leeg"
        class="rounded-[var(--lk-radius-card)] bg-[var(--lk-color-success)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-md)] text-[var(--lk-color-text)]"
      >Geen openstaande registratiegaten.</p>

      <template v-else-if="eersteGeladen && !laden">
        <section v-for="ernst in ['kritiek', 'aandacht']" :key="ernst" class="mb-[var(--lk-space-lg)]" :data-testid="`sig-ernst-${ernst}`">
          <h2 class="mb-[var(--lk-space-sm)]">
            {{ ernst === 'kritiek' ? '🔴 Kritiek' : '🟡 Aandacht' }}
          </h2>
          <template v-for="g in GROEPEN[ernst]" :key="g.key">
            <div v-if="items(ernst, g.key).length" class="mb-[var(--lk-space-md)]" :data-testid="`sig-groep-${g.key}`">
              <p class="mb-1 text-[length:var(--lk-text-sm)] font-semibold">{{ g.label }} ({{ items(ernst, g.key).length }})</p>
              <ul class="flex flex-col gap-0.5">
                <li v-for="c in items(ernst, g.key)" :key="c.id" :data-testid="`sig-${g.key}-${c.id}`" class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
                  <router-link v-if="linkVoor(c, g.link)" :to="linkVoor(c, g.link)" class="text-[var(--lk-color-primary)] hover:underline">{{ c.naam }}</router-link>
                  <span v-else>{{ c.naam }}</span>
                  <span v-if="c.entiteit_type" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">· {{ humaniseer(c.entiteit_type) }}</span>
                  <span v-if="g.lc" class="text-[var(--lk-color-text-muted)]">· {{ lcLabel(c.lifecycle_status) }}</span>
                </li>
              </ul>
            </div>
          </template>
          <p v-if="GROEPEN[ernst].every((g) => items(ernst, g.key).length === 0)" :data-testid="`sig-ernst-leeg-${ernst}`" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">Geen {{ ernst === 'kritiek' ? 'kritieke' : 'aandacht' }}-signalen.</p>
        </section>
      </template>
    </div>

    <!-- Tab 2 — Plaatsing (bestaande view, ongewijzigd ingebed) -->
    <div v-show="tab === 'plaatsing'" role="tabpanel" data-testid="sig-panel-plaatsing">
      <PlaatsingSignalenView />
    </div>

    <!-- Tab 3 — Werkvoorraad per plek (ADR-051 gate 3, venster 2) -->
    <div v-show="tab === 'werkvoorraad'" role="tabpanel" data-testid="sig-panel-werkvoorraad">
      <WerkvoorraadPlekView v-if="tab === 'werkvoorraad'" />
    </div>
  </section>
</template>
