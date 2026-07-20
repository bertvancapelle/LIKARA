<script setup>
/**
 * NormBeheer — het norm-beheerscherm (ADR-052 slice 4b). De beheerder legt de lat: per hard feit of
 * het bekend moet zijn voordat een systeem migratieklaar heet. **Leesbaar voor iedereen** (de lat
 * bepaalt "compleet"); **bewerken alleen de beheerder** (de backend handhaaft COMPONENT_NORM.WIJZIGEN,
 * de knoppen zijn hier de affordance).
 *
 * Vóór opslaan leest de beheerder de IMPACT (besluit 3): geen blokkade, een voorspelling — rustig en
 * feitelijk, nadrukkelijk géén amber (dat draagt "bewuste afwijking"). Geen "terug naar default"-knop
 * (besluit 4). Broer van Checklistvragen (tenant-schil), geen platform-scherm.
 */
import { computed, ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { NORM_FEIT_LABEL, label } from '@modules/bwb_ontvlechting/frontend/labels'

const auth = useAuthStore()
const toast = useToast()
const magBeheren = computed(() => auth.hasRole('beheerder'))

const feiten = ref([]) // [{feit, verplicht, bewust_geen_mogelijk}]
const laden = ref(false)
const fout = ref(null)
const bezig = ref(false)

async function laad() {
  laden.value = true
  fout.value = null
  try {
    feiten.value = await api.componentNormen.definitie()
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de norm mislukt.'
  } finally {
    laden.value = false
  }
}

// ── Impact-voorspelling + bevestiging (besluit 3) ────────────────────────────
const dialogOpen = ref(false)
const pending = ref(null) // {feit, label, verplicht_doel}
const impact = ref(null)

async function beginToggle(rij) {
  const doel = !rij.verplicht
  pending.value = { feit: rij.feit, label: label(NORM_FEIT_LABEL, rij.feit), verplicht_doel: doel }
  impact.value = null
  dialogOpen.value = true
  try {
    impact.value = await api.componentNormen.impact(rij.feit, doel)
  } catch {
    impact.value = null // impact niet leesbaar → geen cijfers, opslaan mag nog
  }
}

async function bevestig() {
  if (!pending.value) return
  bezig.value = true
  try {
    await api.componentNormen.zetVerplicht(pending.value.feit, pending.value.verplicht_doel)
    toastSucces(
      toast,
      pending.value.verplicht_doel
        ? `${pending.value.label} verplicht gesteld`
        : `${pending.value.label} niet meer verplicht`,
    )
    dialogOpen.value = false
    await laad()
  } catch (e) {
    if (e?.status === 403) {
      toast.add({ severity: 'error', summary: 'Geen rechten', detail: 'Alleen de beheerder kan de norm wijzigen.', life: 4000 })
    } else if (e?.status !== 401) {
      toast.add({ severity: 'error', summary: 'Opslaan mislukt.', life: 3000 })
    }
  } finally {
    bezig.value = false
  }
}

laad()
</script>

<template>
  <section aria-labelledby="norm-titel">
    <h1 id="norm-titel" class="mb-[var(--lk-space-sm)]">
      Migratienorm
    </h1>
    <p class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
      De lat voor "migratieklaar": welke feiten moeten bekend zijn voordat een component klaar verklaard
      mag worden. Een verplicht feit dat nog niet is vastgesteld verschijnt als openstaand werk — het
      blokkeert niets.
    </p>
    <p
      v-if="!magBeheren"
      data-testid="norm-readonly-hint"
      class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
    >
      Je kunt de lat inzien; alleen de beheerder kan hem verzetten.
    </p>

    <p v-if="fout" role="alert" data-testid="norm-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="norm-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <section class="card" data-testid="norm-tabel">
      <table class="w-full text-[length:var(--lk-text-sm)]">
        <thead>
          <tr class="text-left text-[var(--lk-color-text-muted)]">
            <th class="py-[var(--lk-space-xs)]">Feit</th>
            <th>Antwoord</th>
            <th>Op de lat</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="rij in feiten"
            :key="rij.feit"
            :data-testid="`norm-rij-${rij.feit}`"
            class="border-t border-[var(--lk-color-border)]"
          >
            <td class="py-[var(--lk-space-xs)] font-medium text-[var(--lk-color-text)]">{{ label(NORM_FEIT_LABEL, rij.feit) }}</td>
            <td>
              <Tag
                :data-testid="`norm-soort-${rij.feit}`"
                :value="rij.bewust_geen_mogelijk ? '“bewust geen” mogelijk' : 'eigen veld'"
                :severity="rij.bewust_geen_mogelijk ? 'info' : 'secondary'"
              />
            </td>
            <td>
              <Tag v-if="rij.verplicht" :data-testid="`norm-verplicht-${rij.feit}`" value="Verplicht" severity="success" />
              <span v-else :data-testid="`norm-nietverplicht-${rij.feit}`" class="text-[var(--lk-color-text-muted)]">Niet verplicht</span>
            </td>
            <td class="text-right">
              <Button
                v-if="magBeheren"
                :label="rij.verplicht ? 'Uitzetten' : 'Aanzetten'"
                severity="secondary"
                :data-testid="`norm-toggle-${rij.feit}`"
                @click="beginToggle(rij)"
              />
            </td>
          </tr>
          <tr v-if="!laden && !feiten.length">
            <td colspan="4" data-testid="norm-leeg" class="py-[var(--lk-space-sm)] text-[var(--lk-color-text-muted)]">Geen feiten.</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Impact vóór opslaan (besluit 3): rustig, feitelijk, GEEN amber. -->
    <Dialog
      v-model:visible="dialogOpen"
      modal
      :closable="false"
      :header="pending?.verplicht_doel ? `${pending?.label} verplicht stellen?` : `${pending?.label} niet meer verplicht?`"
      data-testid="norm-impact-dialog"
    >
      <div class="min-w-[24rem] max-w-prose" data-testid="norm-impact">
        <p v-if="impact === null" class="text-[var(--lk-color-text-muted)]">Impact niet beschikbaar — je kunt toch opslaan.</p>
        <p v-else-if="pending?.verplicht_doel">
          Dit raakt <strong>{{ impact.componenten_geraakt }}</strong> componenten die er nu niet aan voldoen<template v-if="impact.klaarverklaringen_geraakt">
          — waarvan <strong>{{ impact.klaarverklaringen_geraakt }}</strong> eerder klaar {{ impact.klaarverklaringen_geraakt === 1 ? 'is' : 'zijn' }} verklaard</template>.
        </p>
        <p v-else>
          <strong>{{ impact.componenten_geraakt }}</strong> openstaande {{ impact.componenten_geraakt === 1 ? 'signaal vervalt' : 'signalen vervallen' }}<template v-if="impact.componenten_nu_compleet">,
          en <strong>{{ impact.componenten_nu_compleet }}</strong> {{ impact.componenten_nu_compleet === 1 ? 'component voldoet' : 'componenten voldoen' }} daardoor alsnog volledig</template>.
        </p>
        <p class="mt-[var(--lk-space-sm)] text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
          Geen blokkade — je mag dit doen. Dit is alleen wat het aanricht.
        </p>
      </div>
      <div class="flex justify-end gap-[var(--lk-space-md)] mt-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="norm-annuleer" @click="dialogOpen = false" />
        <Button
          :label="pending?.verplicht_doel ? 'Verplicht stellen' : 'Niet meer verplicht'"
          :disabled="bezig"
          data-testid="norm-opslaan"
          @click="bevestig"
        />
      </div>
    </Dialog>
  </section>
</template>
