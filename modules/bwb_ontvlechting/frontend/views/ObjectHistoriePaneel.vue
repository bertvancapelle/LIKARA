<script setup>
/**
 * ObjectHistoriePaneel — 'i'-knop + dialog met de geschiedenis van één object (ADR-029).
 *
 * Toont per gebeurtenis wie (naam, e-mail-fallback) · wanneer · handeling, en — anders dan de
 * centrale auditview — de **detail-diff per record** ("veld: oud → nieuw"). Voor iedereen die het
 * scherm ziet (geen rol-gating op de knop); de backend handhaaft de objecttoegang. `--lk-`-tokens.
 */
import { ref } from 'vue'
import { Button, Dialog } from '@/primevue'
import { api } from '@/api'
import { AUDIT_ACTIE, AUDIT_ENTITEIT, VELD_LABELS, humaniseer, label } from '@modules/bwb_ontvlechting/frontend/labels'
import Icoon from '@/components/Icoon.vue'

const props = defineProps({
  entiteitType: { type: String, required: true },
  entiteitId: { type: [String, Number], required: true },
})

const open = ref(false)
const laden = ref(false)
const fout = ref(null)
const gebeurtenissen = ref([])
const cursor = ref(null)
let geladenVoor = null

const _datum = (iso) =>
  iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : ''

const _wie = (g) => g.actor_naam || g.actor_email || '—'
const _veldLabel = (naam) => VELD_LABELS[naam] ?? humaniseer(naam)

function _diffRegels(record) {
  // wijziging = { veld: { oud, nieuw } } → leesbare regels; lege diff → geen regels.
  return Object.entries(record.wijziging || {}).map(([veld, w]) => ({
    veld: _veldLabel(veld),
    oud: w?.oud ?? '—',
    nieuw: w?.nieuw ?? '—',
  }))
}

async function laad({ meer = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const pagina = await api.objecthistorie.lijst({
      entiteitType: props.entiteitType, entiteitId: props.entiteitId, limit: 50,
      ...(meer && cursor.value ? { after: cursor.value } : {}),
    })
    const items = pagina.items || []
    gebeurtenissen.value = meer ? [...gebeurtenissen.value, ...items] : items
    cursor.value = pagina.volgende_cursor || null
    geladenVoor = props.entiteitId
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de geschiedenis mislukt.'
  } finally {
    laden.value = false
  }
}

function toon() {
  open.value = true
  if (geladenVoor !== props.entiteitId) {
    cursor.value = null
    laad()
  }
}
</script>

<template>
  <span>
    <!-- LI048 — WEGWIJZER, dus een teken: deze knop brengt je ergens heen en verandert niets.
         Klik je er per ongeluk op, dan sluit je het venster weer. De handelingen in dezelfde rij
         (Bewerken, Heropenen, Verwijderen) blijven bewust een WOORD — zie de grens in Icoon.vue.

         Hier stond een verwijzing naar een informatie-icoontje uit een iconenpakket dat geen
         afhankelijkheid van dit project is. Die klasse bestond nergens, dus er rendeerde al
         maanden niets zonder dat iets het meldde. Niet ingevuld maar vervangen — deze knop hoort
         een klokje te dragen, geen "i". De bron-scan in check-css-build.mjs vangt zo'n dode
         verwijzing voortaan bij elke build.

         `title` levert de tooltip, `aria-label` de uitgesproken naam. Beide nodig: een tooltip
         verschijnt pas bij hangen (en op een tablet nooit), en een schermlezer leest `title`
         niet betrouwbaar voor. -->
    <Button
      severity="secondary"
      title="Geschiedenis"
      aria-label="Geschiedenis"
      data-testid="oh-knop"
      @click="toon"
    >
      <Icoon naam="geschiedenis" />
    </Button>
    <Dialog
      v-model:visible="open"
      modal
      :header="`Geschiedenis`"
      data-testid="oh-dialog"
      class="min-w-[28rem]"
    >
      <!-- Statusregels: volledige laad-/lege-status alleen als er nog niets staat; bij naladen
           blijft de lijst zichtbaar en toont de "Meer laden"-knop de bezig-staat. -->
      <p v-if="laden && !gebeurtenissen.length" data-testid="oh-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>
      <p v-else-if="fout && !gebeurtenissen.length" role="alert" data-testid="oh-fout" class="text-[var(--lk-color-danger)]">{{ fout }}</p>
      <p v-else-if="!laden && !gebeurtenissen.length" data-testid="oh-leeg" class="text-[var(--lk-color-text-muted)]">Nog geen geschiedenis voor dit object.</p>

      <template v-else>
        <p v-if="fout" role="alert" data-testid="oh-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
        <ol class="flex flex-col gap-[var(--lk-space-md)]">
          <li v-for="g in gebeurtenissen" :key="g.correlatie_id" data-testid="oh-gebeurtenis" class="border-b border-[var(--lk-color-border)] pb-[var(--lk-space-sm)]">
            <p class="text-[length:var(--lk-text-sm)]">
              <strong data-testid="oh-wie">{{ _wie(g) }}</strong> · {{ _datum(g.tijdstip) }}
            </p>
            <ul class="mt-[var(--lk-space-xs)] flex flex-col gap-[var(--lk-space-xs)]">
              <li v-for="r in g.records" :key="r.id" class="text-[length:var(--lk-text-sm)]">
                <span class="font-semibold">{{ label(AUDIT_ENTITEIT, r.entiteit_type) }} — {{ label(AUDIT_ACTIE, r.actie) }}</span>
                <ul v-if="_diffRegels(r).length" class="ml-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
                  <li v-for="d in _diffRegels(r)" :key="d.veld" data-testid="oh-diff">{{ d.veld }}: {{ d.oud }} → {{ d.nieuw }}</li>
                </ul>
              </li>
            </ul>
          </li>
        </ol>

        <div v-if="cursor" class="mt-[var(--lk-space-md)] flex justify-center">
          <Button :label="laden ? 'Laden…' : 'Meer laden'" severity="secondary" :disabled="laden" data-testid="oh-meer" @click="laad({ meer: true })" />
        </div>
      </template>
    </Dialog>
  </span>
</template>
