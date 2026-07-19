# LIKARA Changelog V047

**Datum**: 2026-07-19
**Sessie**: LI046 — de kaart vertelt, het component verandert

## Wijzigingen

### Landschapskaart — één ingang naar het detailscherm (ADR-054)
- Gedeelde detail-ingang (`detailRoute`): vanaf de kaart naar een detailscherm gaat langs één deur, met de
  aanleiding in de URL; geen route zonder landing (`80d0038`/`4dd1387`/`466eb7b`).
- Veld-anker: `?veld=` landt gemarkeerd op het Overzicht (`4dd1387`).
- Terugkeer landt bij het bewaarde beeld; een volledig verdwenen selectie krijgt een eerlijke melding
  (`lk-leeg-verdwenen`) in plaats van een lege kaart (`9ee6fcb`).
- Startscherm: derde uitgang "Zelf beginnen" met de nadruk; beginscherm-binnenkomst als één eenmalige regel
  ná de beslisboom ("de bezoeker wint", `61665a4`/`3b7941f`).

### Landschapskaart — kijkinstellingen-kolom alléén bij een getekende kaart
- De `aside` draagt `v-if="heeftData"` (`nodes.length > 0`) — bewust níét `!beginschermOpen`; kijken ≠
  binnenkomen. Opgeslagen kijken + beheer (✎/×, `magViewsBeheren`) naar het startpaneel; Rol/BIV achter een
  inklap (`3a72b35`).

### Landschapskaart — relaties gescheiden op hoedanigheid
- Nieuw `kaartBanen.js`: `hoedanigheidVan()` (roltoewijzing→beheer, anders relatietype) + `baanVerdeling()`
  waaiert edges per knopenpaar met richting-gecorrigeerde `cpd` (`unbundled-bezier`), ná de
  instance-projectie (Lagen-veilig). Klik op een baan levert álle relaties tussen dat paar. Ring-agnostisch
  (`6651f1f`).

### Documentatie & borging
- ADR-054 vastgelegd; ADR-register aangevuld 049–054; statuscorrectie ADR-049/050/051 (kop + body)
  (`bf67e67`).
- Vier read-only checkpoints (open-punten per component, linkerkolom, hertekenen/overlappende lijnen,
  terugweg) (`f7929a9`/`bf67e67`).
- LI046-patronen verankerd in vier likara-skills (ux/frontend/werkprotocol/tests) (`aca7cb1`/`70f2cbb`).

## Tests
backend 1159 passed / 2 skipped · frontend 97 files / 1248 passed · vite build OK · css-build OK ·
alembic 1 head (`0073`), 0 branches · 0 kritieken (TST-V047).

## Migraties
Geen — LI046 was puur frontend + documentatie.
