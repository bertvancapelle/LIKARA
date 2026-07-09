<script setup>
/**
 * PartijProcessenSectie — "Processen" op de organisatie-pagina (ADR-042 slice 5).
 *
 * AFGELEID beeld, eerlijk gepresenteerd: welke processen steunen op de componenten van
 * deze organisatie (eigendom + geregistreerd gebruik samengenomen; de backend dedupet
 * per proces). Regels "Vergunningverlening — via 3 componenten": de procesnaam is de
 * doorklik, de uitklap toont de brug-componenten (klikbaar). Géén bewerk-acties — hier
 * wordt niets geregistreerd (dat zegt de (i)-uitleg ook). Lege staat rustig.
 */
import { ref, watch } from 'vue'
import { api } from '@/api'
import MeldingBanner from '@/components/MeldingBanner.vue'
import VeldUitleg from './VeldUitleg.vue'

const props = defineProps({ partijId: { type: String, required: true } })

const processen = ref([])
const laden = ref(false)
const fout = ref(null)
const uitgeklapt = ref(new Set()) // proces_id's waarvan de brug-componenten open staan

async function laad() {
  laden.value = true
  fout.value = null
  uitgeklapt.value = new Set()
  try {
    processen.value = await api.partijen.processen(props.partijId)
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de processen van deze organisatie is mislukt.'
  } finally {
    laden.value = false
  }
}

function wissel(procesId) {
  const s = new Set(uitgeklapt.value)
  if (s.has(procesId)) s.delete(procesId)
  else s.add(procesId)
  uitgeklapt.value = s
}

watch(() => props.partijId, () => laad(), { immediate: true })
</script>

<template>
  <section class="card" aria-labelledby="partij-processen-titel" data-testid="partij-processen-sectie">
    <div class="flex items-center gap-[var(--lk-space-xs)] mb-[var(--lk-space-sm)]">
      <h2 id="partij-processen-titel" class="text-[length:var(--lk-text-lg)] font-semibold">Processen</h2>
      <VeldUitleg veld="organisatie_processen" testid="uitleg-organisatie-processen" />
    </div>

    <MeldingBanner v-if="fout" soort="danger" :tekst="fout" testid="pps-fout" />
    <p v-else-if="laden && !processen.length" data-testid="pps-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <ul v-else-if="processen.length" class="divide-y divide-[var(--lk-color-border)]" data-testid="pps-regels">
      <li v-for="p in processen" :key="p.proces_id" class="py-[var(--lk-space-sm)]" :data-testid="`pps-regel-${p.proces_id}`">
        <div class="flex items-baseline gap-[var(--lk-space-sm)]">
          <span class="min-w-0">
            <router-link
              :to="{ name: 'proces-detail', params: { id: p.proces_id } }"
              data-testid="pps-proces-link"
              class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >{{ p.proces_naam }}</router-link>
            <span v-if="p.proces_ouder_naam" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"> — {{ p.proces_ouder_naam }}</span>
          </span>
          <button
            type="button"
            :data-testid="`pps-wissel-${p.proces_id}`"
            :aria-expanded="uitgeklapt.has(p.proces_id)"
            class="ml-auto shrink-0 text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            @click="wissel(p.proces_id)"
          >via {{ p.component_aantal }} component(en) {{ uitgeklapt.has(p.proces_id) ? '▾' : '▸' }}</button>
        </div>
        <!-- Uitklap: de brug-componenten (klikbaar) — het "waarom" van de regel. -->
        <ul v-if="uitgeklapt.has(p.proces_id)" class="mt-[var(--lk-space-xs)] pl-[var(--lk-space-md)]" :data-testid="`pps-componenten-${p.proces_id}`">
          <li v-for="c in p.componenten" :key="c.component_id" class="py-[2px] text-[length:var(--lk-text-sm)]">
            <router-link
              :to="{ name: 'component-detail', params: { id: c.component_id } }"
              data-testid="pps-component-link"
              class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >{{ c.component_naam }}</router-link>
            <span v-if="c.componenttype_label" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"> ({{ c.componenttype_label }})</span>
          </li>
        </ul>
      </li>
    </ul>

    <p v-else-if="!laden && !fout" data-testid="pps-leeg" class="text-[var(--lk-color-text-muted)]">
      Nog geen processen via componenten van deze organisatie.
    </p>
  </section>
</template>
