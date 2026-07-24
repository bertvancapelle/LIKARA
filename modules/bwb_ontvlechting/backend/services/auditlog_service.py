"""Service-laag — audit-spoor lezen (ADR-006 Fase E).

Read-only. Levert **correlatie-gegroepeerde gebeurtenissen**: per `correlatie_id` één
gebeurtenis met de driver + al haar afgeleide gevolgen (lifecycle/blokkade), gebonden
via dat correlatie-id. Tenant-scoped (RLS + expliciete `tenant_id`-filter, dubbele
bescherming). Keyset-paginering over de gebeurtenissen (anker = vroegste tijdstip per
groep, aflopend = nieuwste eerst); filterbaar op actor / entiteit-type / component /
periode.

De groepering haalt voor elke gepaginate `correlatie_id` de **volledige** groep op —
ook records die zelf niet aan het filter voldoen (de afgeleide gevolgen horen erbij).
"""
import base64
import uuid
from datetime import datetime

from sqlalchemy import Text, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import AuditLog
from services import actor_resolutie, entiteit_resolutie
from services import zoektekst

_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _encode_cursor(anker: datetime, correlatie_id) -> str:
    rauw = f"{anker.isoformat()}|{correlatie_id}"
    return base64.urlsafe_b64encode(rauw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """`(anker_tijdstip, correlatie_id)`; `ValueError` bij een misvormde cursor."""
    if not cursor:
        raise ValueError("lege cursor")
    try:
        rauw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        anker_str, corr_str = rauw.rsplit("|", 1)
        return datetime.fromisoformat(anker_str), uuid.UUID(corr_str)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError("ongeldige cursor") from exc


# ── LI048 besluit 2 — WELKE regel is de aanleiding? ───────────────────────────────────────
# Bij het aanmaken van een element-subtype ontstaan twee auditrijen: eerst de supertype-rij
# (tabel `element`), die alléén het discriminator-veld draagt, en dan de subtype-rij die zegt
# wát het is en hoe het heet. De weergave nam stelselmatig de eerste — vandaar
# "Element — 9f1282d4… · Aangemaakt (+1 afgeleid)": een regel die de consultant niets vertelt.
#
# Het criterium is INHOUDELIJK, niet op tabelnaam: een record is betekenisloos als zijn hele
# `wijziging` niets anders bevat dan de discriminator. Zo vangt het ook een toekomstig subtype
# zonder dat iemand een naam aan een lijst toevoegt — en een `element`-rij die wél iets
# inhoudelijks draagt, blijft gewoon meetellen.
_DISCRIMINATOR_VELDEN = frozenset({"element_type"})


def _is_betekenisloos(rec) -> bool:
    velden = set((rec.wijziging or {}).keys())
    return bool(velden) and velden <= _DISCRIMINATOR_VELDEN


def _kies_driver(records: list):
    """De regel die de gebeurtenis benoemt: de eerste die iets inhoudelijks zegt.

    Zegt géén enkel record iets (alles betekenisloos), dan valt hij terug op het eerste —
    beter een magere regel dan geen regel."""
    for rec in records:
        if not _is_betekenisloos(rec):
            return rec
    return records[0] if records else None


# ── LI048 besluit 1 — de naam van TOEN wint ───────────────────────────────────────────────
# Een auditlog beantwoordt de vraag wat er tóén gebeurde. Haal je de naam op bij het object van
# nu, dan verandert de geschiedenis mee zodra iemand hernoemt, en klopt het log niet meer met
# wat er destijds op het scherm stond. Bij een verwijdering is het scherper: het object bestaat
# niet meer, en juist die regel is het enige spoor dat overblijft.
#
# Volgorde: de VASTGELEGDE naam uit de wijziging (bij delete de `oud`-waarde, anders `nieuw`),
# daarna pas de huidige naam uit de resolutie — behalve bij een verwijdering, waar de huidige
# naam NOOIT mag worden gebruikt: als daar iets uit komt, is het een ander object dat het id
# hergebruikt of een halfverwijderde rij, en dat is misleidender dan geen naam.
#
# TEKORTKOMING (geen ontwerp): bij een `update` van een ánder veld staat er geen naam in de rij,
# dus daar blijft de huidige naam de enige bron — en verandert die regel dus alsnog mee bij een
# hernoeming. Vastgelegd als opvolgpunt; oplossen vraagt een naam-snapshot bij élke mutatie.
def _vastgelegde_naam(rec) -> str | None:
    # Wélk veld de naam draagt verschilt per soort (LI048 snede 3): een checklistvraag heet
    # naar zijn vraagtekst, een contract naar zijn contractnaam. Het register is de ene bron;
    # `naam` blijft de terugval voor een soort die er (nog) niet in staat.
    bron = NAAMBRON.get(rec.entiteit_type)
    veld = bron[1] if bron and bron[0] == "veld" else ("naam" if bron is None else None)
    if not veld:
        return None
    w = (rec.wijziging or {}).get(veld)
    if not isinstance(w, dict):
        return None
    waarde = w.get("oud") if rec.actie == "delete" else w.get("nieuw")
    if waarde is None:                      # bij delete valt `oud` soms leeg → probeer `nieuw`
        waarde = w.get("nieuw") if rec.actie == "delete" else None
    return waarde if isinstance(waarde, str) and waarde.strip() else None


# ── LI048 snede 3, besluit 3 — ELKE soort heeft een naam met een AANWIJSBARE bron ────────
# Twee soorten toonden een kale code (`Checklistvraag — e123f280…`, `Componentprofiel —
# d7f127c0…`). Die twee los repareren lost het geval op maar niet het patroon: de volgende
# soort komt er weer naamloos bij. Vandaar dit register, dat voor élke geauditeerde soort
# uitspreekt wáár zijn naam vandaan komt — inclusief de soorten waarvoor het antwoord "geen"
# is. Dat laatste is een BESLUIT, geen stilzwijgende terugval, en een toets bewaakt dat de
# lijst compleet blijft (zie test_auditlog_leesbaar.py).
#
# Vier vormen:
#   ("veld", <veldnaam>)        — het ding draagt zelf een naam, in dit veld van de wijziging
#   ("leen_veld", <idveld>)     — geen eigen naam; leen die van het component waarnaar dit
#                                 id-veld in de wijziging verwijst
#   ("leen_identiteit",)        — geen eigen naam; het ding IS een component (gedeelde PK,
#                                 1-op-1 uitbreiding) → leen de naam van dat component
#   ("geen", <reden>)           — bewust naamloos; de reden staat erbij en is leesbaar
_GEEN_NAAM = "geen"
NAAMBRON: dict[str, tuple] = {
    # ── Draagt zelf een naam ────────────────────────────────────────────────────────────
    "component": ("veld", "naam"),
    "partij": ("veld", "naam"),
    "relatie": ("veld", "naam"),
    "bedrijfsfunctie": ("veld", "naam"),
    "plateau": ("veld", "naam"),
    "work_package": ("veld", "naam"),
    "deliverable": ("veld", "naam"),
    "gap": ("veld", "naam"),
    "proces": ("veld", "naam"),
    "referentiemodel": ("veld", "naam"),
    "impact_view": ("veld", "naam"),
    "contract": ("veld", "contractnaam"),
    # LI048 besluit 1 — een checklistvraag herken je aan zijn VRAAGTEKST, niet aan zijn code.
    # De tekst wordt afgekort getoond; het begin is genoeg om hem te herkennen.
    "checklistvraag": ("veld", "vraag"),
    # LI050 (ADR-022 W3) — de categorie draagt zelf haar naam.
    "checklist_categorie": ("veld", "naam"),
    "checklistvraag_optie": ("veld", "tekst"),
    "datatype": ("veld", "omschrijving"),
    # ── Leent de naam van het component waar het bij hoort ──────────────────────────────
    # Deze dingen zijn geen zelfstandig onderwerp maar een uitspraak OVER een component;
    # de consultant wil weten over wélk component het ging.
    "checklistscore": ("leen_veld", "component_id"),
    "functievervulling": ("leen_veld", "component_id"),
    "procesvervulling": ("leen_veld", "component_id"),
    "component_klaarverklaring": ("leen_veld", "component_id"),
    "component_bevinding": ("leen_veld", "component_id"),
    "blokkade": ("leen_veld", "component_id"),
    "impact_view_component": ("leen_veld", "component_id"),
    # LI048 besluit 2 — een componentprofiel is geen ding op zichzelf maar de uitkomst die
    # LIKARA per component bijhoudt. Het deelt zijn PRIMAIRE SLEUTEL met het component
    # (`component_profiel.id` is een FK naar `component.id`), dus het id ís de ingang.
    # NB de opdracht ging uit van een `component_id` in de wijziging; die staat er NIET in
    # (0 van 2.085 rijen). De gedeelde sleutel is de werkende route — zie het gate-rapport.
    "component_profiel": ("leen_identiteit",),
    # ── Bewust geen naam, met de reden erbij ────────────────────────────────────────────
    "element": (_GEEN_NAAM, "supertype-rij; wordt nooit de aanleiding van een gebeurtenis"),
    "component_norm": (_GEEN_NAAM, "gaat over de tenant-norm als geheel, niet over één ding"),
    "organisatiegebruik": (_GEEN_NAAM, "koppelfeit organisatie↔applicatie; geen van beide is DE naam"),
    "gebruiker_persoon": (_GEEN_NAAM, "koppelfeit login↔persoon; de persoon staat al in de kolom Wie"),
    "roltoewijzing": (_GEEN_NAAM, "koppelfeit partij↔rol↔object; geen enkelvoudige naam"),
    # Gemeten, niet aangenomen: `gebruikersgroep` heeft GEEN naamkolom (id, aantal_gebruikers,
    # gebruik_id, afdeling_id). Het is een aantalsfeit onder een organisatiegebruik; een naam
    # zou twee stappen ver geleend moeten worden (groep → gebruiksfeit → applicatie).
    "gebruikersgroep": (_GEEN_NAAM, "aantalsfeit onder een gebruiksfeit; heeft zelf geen naam"),
    "contract_dekking": (_GEEN_NAAM, "dekkingsvlag op een contract; geen eigen naam"),
    "contract_kostenmodel": (_GEEN_NAAM, "kostenmodelvlag op een contract; geen eigen naam"),
    "contract_band_dekking": (_GEEN_NAAM, "per-band dekkingsvlag; geen eigen naam"),
}

# Een lange vraagtekst hoort herkenbaar te zijn, niet volledig. Het begin draagt de herkenning.
_NAAM_MAX = 80


def _kort_af(waarde: str | None) -> str | None:
    if not waarde:
        return None
    waarde = waarde.strip()
    return waarde if len(waarde) <= _NAAM_MAX else waarde[: _NAAM_MAX - 1].rstrip() + "…"


def _geleend_component_id(rec) -> str | None:
    """Het component waarvan deze regel zijn naam leent — of None."""
    bron = NAAMBRON.get(rec.entiteit_type)
    if not bron:
        return None
    if bron[0] == "leen_identiteit":
        return str(rec.entiteit_id)
    if bron[0] == "leen_veld":
        w = (rec.wijziging or {}).get(bron[1])
        if isinstance(w, dict):
            waarde = w.get("nieuw") if w.get("nieuw") is not None else w.get("oud")
            return str(waarde) if waarde else None
    return None


# ── LI048 — WAT HOORT ER IN DE GESCHIEDENIS VAN EEN DING? ────────────────────────────────
# Sta je op een partij, dan hoort daarin te staan dat iemand haar een rol gaf of afnam. Dat
# gebeurde alleen als het toevallig in dezelfde handeling zat: 154 van de 229 roltoewijzingen
# waren onvindbaar — niet hier, en nergens anders. De geschiedenis zag er compleet uit en was
# het niet; hetzelfde patroon als de koppelingen die het component-filter miste.
#
# In de code stond bovendien uitgelegd dat dit WÉL gebeurde ("verschijnt in de historie van de
# ouder", routes/objecthistorie.py). Dat is nu waargemaakt in plaats van bijgesteld.
#
# Twee vormen, net als bij NAAMBRON:
#   [(sub_type, veld), ...]  — deze sub-entiteiten horen erbij; `veld` in hun `wijziging`
#                              verwijst naar de ouder
#   ("geen", <reden>)        — bewust geen sub-entiteiten, met een leesbare reden
#
# `component` staat hier NIET in: dat type heeft zijn eigen, rijkere modus (component_id-filter
# plus koppelingen) en die blijft ongemoeid — één waarheid, twee ingangen.
_GEEN_SUB = "geen"
SUB_ENTITEITEN: dict[str, object] = {
    # Een partij is een leverancier, organisatie of persoon. Wat er met haar gebeurt, gebeurt
    # vaak in een koppelfeit: welke rol had deze leverancier, en sinds wanneer niet meer.
    "partij": [
        ("roltoewijzing", "partij_id"),          # rol op een component/contract
        ("gebruiker_persoon", "persoon_id"),     # koppeling login ↔ persoon
        ("organisatiegebruik", "organisatie_id"),  # organisatie gebruikt applicatie
    ],
    # Gemeten (niet aangenomen): de sub-typen van contract staan wél in AUDIT_TENANT_ENTITEITEN
    # maar hebben 0 auditregels — er is niets om op te halen. Verschijnt er ooit een regel, dan
    # valt deze uitspraak op via de toets die het register in beide richtingen afdwingt.
    "contract": (_GEEN_SUB, "de dekking-/kostenmodel-subtypen leveren geen auditregels op"),
    # Het lidmaatschap van deze vier loopt via `relatie` (ADR-023 Fase E), niet via een id-veld
    # in een sub-entiteit. Gemeten: 0 relatieregels met een van deze vier als uiteinde, dus er
    # valt vandaag niets op te halen. Komt dat er, dan is dit hetzelfde geval als de koppelingen
    # bij component — en dan hoort het hier, niet in een losse uitzondering.
    "plateau": (_GEEN_SUB, "lidmaatschap loopt via koppelingen, die vandaag geen regels opleveren"),
    "work_package": (_GEEN_SUB, "lidmaatschap loopt via koppelingen, die vandaag geen regels opleveren"),
    "deliverable": (_GEEN_SUB, "lidmaatschap loopt via koppelingen, die vandaag geen regels opleveren"),
    "gap": (_GEEN_SUB, "lidmaatschap loopt via koppelingen, die vandaag geen regels opleveren"),
    # ADR-056 besluit 17 — de geschiedenis van een vraag draagt óók haar antwoordopties
    # (toegevoegd/uitgezet; de create-/delete-diff draagt `checklistvraag_id`). De
    # ANTWOORDEN (checklistscore) staan er bewust NIET in: die horen bij de geschiedenis
    # van het component, en honderden score-regels zouden de formulering-geschiedenis —
    # waarvoor deze ingang bestaat — verdrinken.
    "checklistvraag": [("checklistvraag_optie", "checklistvraag_id")],
}


def _sub_clausules(entiteit_type: str, eid: str):
    """De OR-takken voor de sub-entiteiten van dit type — leeg als het er bewust geen heeft."""
    bron = SUB_ENTITEITEN.get(entiteit_type)
    if not isinstance(bron, list):
        return []
    takken = []
    for sub_type, veld in bron:
        takken.append(
            and_(
                AuditLog.entiteit_type == sub_type,
                or_(
                    AuditLog.wijziging[veld]["nieuw"].astext == eid,
                    AuditLog.wijziging[veld]["oud"].astext == eid,
                ),
            )
        )
    return takken


def _toon_naam(rec, ent_map: dict) -> str | None:
    """De naam die bij deze auditregel hoort — besluit 1 in één plek.

    Stond dit inline in de leslus, dan was de delete-tak niet los te toetsen: een opzettelijke
    breuk erin bleef groen omdat geen enkele toets hem oefende. Dat is precies de valse zekerheid
    uit likara-ux §P8a, en de reden dat deze keuze een eigen functie is."""
    # Afkorten gebeurt op ÉÉN plek, aan het eind — anders hangt de lengte af van wélke route
    # toevallig een naam opleverde (de vastgelegde tekst werd wél ingekort, de terugval niet).
    return _kort_af(_ruwe_naam(rec, ent_map))


def _ruwe_naam(rec, ent_map: dict) -> str | None:
    vastgelegd = _vastgelegde_naam(rec)
    if vastgelegd:
        return vastgelegd
    # LI048 snede 3 — GELEENDE naam: dit ding is geen zelfstandig onderwerp maar een uitspraak
    # over een component. Ook hier geldt besluit 1 niet: het geleende component bestaat nog wél
    # (anders was deze regel meegecascadeerd), dus de huidige naam is hier de juiste — en de
    # enige die er is. Bij een verwijdering van het koppelfeit blijft het component bestaan.
    geleend = _geleend_component_id(rec)
    if geleend:
        return ent_map.get(("component", geleend))
    if rec.actie == "delete":
        # NOOIT de huidige naam: het object hoort niet meer te bestaan. Komt er tóch iets uit de
        # resolutie, dan is dat een ander object dat het id hergebruikt of een halfverwijderde
        # rij — misleidender dan geen naam.
        return None
    return ent_map.get((rec.entiteit_type, str(rec.entiteit_id)))


def _record_filters(tid: uuid.UUID, *, actor, entiteit_type, entiteit_id, component_id, van, tot,
                    actie, subs, wie_fragment=None, gekoppeld=None):
    """Record-niveau filterclausules (een groep kwalificeert als ≥1 record matcht)."""
    clauses = [AuditLog.tenant_id == tid]
    if actor:
        clauses.append(AuditLog.actor_sub == actor)
    if subs is not None:
        # LI048 — het "wie"-filter volgt DEZELFDE regel als de kolom Wie, die `naam or e-mail`
        # toont: treffer op de naam van de gekoppelde persoon, OF — alléén voor rijen zónder
        # koppeling, want die tonen het e-mailadres — treffer op `actor_email`.
        #
        # Zonder die tweede tak was iedereen zonder gekoppelde persoon onvindbaar, en dat was in
        # het demolandschap iedereen: het scherm toonde "test:bert@test" en gaf op "bert" nul
        # regels, zonder fout. De consultant concludeert dan dat er niets gebeurd is.
        #
        # De `notin_`-voorwaarde is geen detail: zonder die beperking zou een gebruiker MET naam
        # gevonden worden op zijn e-mailadres — dus op iets wat op dit scherm nergens staat.
        wie = [AuditLog.actor_sub.in_(subs)]
        if wie_fragment:
            # LI051 — de gedeelde zoek-bron: accent-ongevoelig, met de jokertekst-escape op één plek.
            email_treffer = zoektekst.zoek_clause(AuditLog.actor_email, wie_fragment)
            if gekoppeld:
                email_treffer = and_(email_treffer, AuditLog.actor_sub.notin_(gekoppeld))
            wie.append(email_treffer)
        clauses.append(or_(*wie))
    if actie:
        clauses.append(AuditLog.actie == actie)
    if entiteit_type and entiteit_id is not None:
        # ADR-029 objecthistorie — de geschiedenis van ÉÉN object. LI048: niet alleen de regels
        # over het object zelf, maar ook die van zijn sub-entiteiten (zie SUB_ENTITEITEN). Deze
        # twee voorwaarden horen als één OR bij elkaar; zou het object-deel een losse AND blijven,
        # dan sluit het de sub-takken juist uit.
        eid = str(entiteit_id)
        eigen = and_(
            AuditLog.entiteit_type == entiteit_type,
            cast(AuditLog.entiteit_id, Text) == eid,
        )
        takken = [eigen, *_sub_clausules(entiteit_type, eid)]
        clauses.append(or_(*takken) if len(takken) > 1 else eigen)
    elif entiteit_type:
        clauses.append(AuditLog.entiteit_type == entiteit_type)
    elif entiteit_id is not None:
        clauses.append(cast(AuditLog.entiteit_id, Text) == str(entiteit_id))
    if van is not None:
        clauses.append(AuditLog.tijdstip >= van)
    if tot is not None:
        clauses.append(AuditLog.tijdstip <= tot)
    if component_id is not None:
        cid = str(component_id)
        # Wat de consultant hier vraagt is niet "welke regels hangen aan dit component" maar
        # **wat is er met dit ding gebeurd**. Drie manieren waarop een auditregel daarover gaat:
        #
        #  1. de entiteit ÍS het component — geldt ook voor de rijen die hun primaire sleutel met
        #     het component delen (`element`, `component_profiel`);
        #  2. het component staat als `component_id` in de diff (checklistscore, blokkade,
        #     functievervulling, klaarverklaring, bevinding, procesvervulling);
        #  3. LI048 — het component is BRON of DOEL van een koppeling.
        #
        # Die derde ontbrak, en dat was een fout, geen afbakening: een `relatie` draagt nooit een
        # `component_id` (0 van 9.291 regels), dus "iemand haalde de koppeling naar DigiD weg" was
        # onvindbaar via dit filter — terwijl dát vaak juist is waar de consultant naar zoekt als
        # er iets niet meer werkt. Het scherm toonde een compleet ogende lijst die het niet was;
        # dezelfde onwaarheid als een zoekveld dat iets anders doorzoekt dan het toont (§P8b).
        clauses.append(
            or_(
                cast(AuditLog.entiteit_id, Text) == cid,
                AuditLog.wijziging["component_id"]["nieuw"].astext == cid,
                AuditLog.wijziging["component_id"]["oud"].astext == cid,
                AuditLog.wijziging["bron_id"]["nieuw"].astext == cid,
                AuditLog.wijziging["bron_id"]["oud"].astext == cid,
                AuditLog.wijziging["doel_id"]["nieuw"].astext == cid,
                AuditLog.wijziging["doel_id"]["oud"].astext == cid,
            )
        )
    return clauses


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    actor: str | None = None,
    actor_naam: str | None = None,
    entiteit_type: str | None = None,
    entiteit_id: uuid.UUID | None = None,
    component_id: uuid.UUID | None = None,
    van: datetime | None = None,
    tot: datetime | None = None,
    actie: str | None = None,
) -> tuple[list[dict], str | None]:
    """Correlatie-gegroepeerde gebeurtenissen, nieuwste eerst. Cursor-mismatch/-corruptie
    ⇒ `ValueError` (route ⇒ 400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    # ADR-029 Fase 3a — naam-filter: resolveer het naam-fragment vóór de query naar sub's.
    # Een fragment dat geen gekoppelde persoon matcht ⇒ lege set ⇒ lege auditlijst (geen fout).
    subs = None
    wie_fragment = None
    gekoppeld = None
    if actor_naam and actor_naam.strip():
        wie_fragment = actor_naam.strip()
        subs = await actor_resolutie.subs_voor_naam(session, tid, wie_fragment)
        gekoppeld = await actor_resolutie.gekoppelde_subs(session, tid)
        # GEEN vroege `return [], None` meer bij een lege sub-set: een fragment dat geen
        # persoonsnaam matcht kan nog steeds een e-mailadres matchen — precies het geval dat
        # hier stuk was. Vindt geen van beide iets, dan levert de query zelf netjes leeg op.

    filters = _record_filters(
        tid, actor=actor, entiteit_type=entiteit_type, entiteit_id=entiteit_id,
        component_id=component_id, van=van, tot=tot, actie=actie, subs=subs,
        wie_fragment=wie_fragment, gekoppeld=gekoppeld,
    )

    # (1) Pagineer de groepen: per correlatie_id het anker (vroegste tijdstip = driver),
    # geordend nieuwste-eerst met correlatie_id als stabiele tiebreaker.
    anker = func.min(AuditLog.tijdstip).label("anker")
    groep_q = (
        select(AuditLog.correlatie_id, anker)
        .where(and_(*filters))
        .group_by(AuditLog.correlatie_id)
    )
    if after:
        cur_anker, cur_corr = _decode_cursor(after)
        groep_q = groep_q.having(
            or_(
                anker < cur_anker,
                and_(anker == cur_anker, AuditLog.correlatie_id < cur_corr),
            )
        )
    groep_q = groep_q.order_by(anker.desc(), AuditLog.correlatie_id.desc()).limit(limit + 1)
    groep_rijen = list((await session.execute(groep_q)).all())

    heeft_meer = len(groep_rijen) > limit
    pagina = groep_rijen[:limit]
    if not pagina:
        return [], None

    corr_ids = [r.correlatie_id for r in pagina]

    # (2) Haal de VOLLEDIGE groepen op (incl. afgeleide records die niet aan het filter
    # voldoen), chronologisch per groep (driver eerst).
    recs = list(
        (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.tenant_id == tid, AuditLog.correlatie_id.in_(corr_ids))
                .order_by(AuditLog.correlatie_id, AuditLog.tijdstip.asc(), AuditLog.id.asc())
            )
        )
        .scalars()
        .all()
    )
    per_corr: dict = {}
    for rec in recs:
        per_corr.setdefault(rec.correlatie_id, []).append(rec)

    # ADR-029 Fase 3a — naam-verrijking: ÉÉN batch-resolutie voor álle subs op de pagina
    # (N+1-vrij). Transient `actor_naam` (sub → persoon.naam, anders e-mail-fallback, nooit leeg).
    naam_map = await actor_resolutie.resolveer_namen(session, tid, {rec.actor_sub for rec in recs})
    for rec in recs:
        rec.actor_naam = naam_map.get(rec.actor_sub) or rec.actor_email

    # LI019 — objectnaam-verrijking: ÉÉN batch-resolutie van (entiteit_type, entiteit_id) → naam
    # (N+1-vrij). Transient `entiteit_naam`; None bij verwijderde/naamloze objecten → UI valt terug op id.
    # LI048 snede 3 — de GELEENDE component-ids gaan in DEZELFDE batch. Zou dat een aparte
    # ronde worden, dan is de N+1-vrijheid weg die deze functie expliciet borgt (er staat een
    # toets op dat er één resolutie per lijst-aanroep is).
    te_resolveren = {(rec.entiteit_type, rec.entiteit_id) for rec in recs}
    for rec in recs:
        geleend = _geleend_component_id(rec)
        if geleend:
            te_resolveren.add(("component", geleend))
    ent_map = await entiteit_resolutie.resolveer_namen(session, tid, te_resolveren)
    for rec in recs:
        # LI048 besluit 1 — de vastgelegde naam gaat vóór de huidige. Bij een verwijdering is de
        # huidige naam geen terugval maar een risico: het object hoort niet meer te bestaan.
        rec.entiteit_naam = _toon_naam(rec, ent_map)

    gebeurtenissen: list[dict] = []
    for r in pagina:
        records = per_corr.get(r.correlatie_id, [])
        # LI048 besluit 2 — de driver is de eerste BETEKENISDRAGENDE regel, niet simpelweg de
        # chronologisch eerste. De UI leest deze keuze; hij wordt niet aan beide kanten opnieuw
        # afgeleid, want dan kunnen ze uiteenlopen.
        driver = _kies_driver(records)
        # De telling "(+N afgeleid)" gaat over wat de consultant zou kunnen missen. Een
        # betekenisloze supertype-rij hoort daar niet in: die zegt alleen dát er iets bestaat,
        # en dat weet je al uit de driver. Zonder deze correctie zou elke aanmaak "(+1 afgeleid)"
        # tonen voor een regel die niets toevoegt.
        betekenisvol = [rec for rec in records if not _is_betekenisloos(rec)]
        gebeurtenissen.append({
            "correlatie_id": r.correlatie_id,
            "tijdstip": r.anker,
            "actor_sub": driver.actor_sub if driver else None,
            "actor_email": driver.actor_email if driver else None,
            "actor_naam": (driver.actor_naam if driver else None),
            # De samenvatting van de gebeurtenis — ÉÉN waarheid, door de backend bepaald.
            "entiteit_type": driver.entiteit_type if driver else None,
            "entiteit_naam": driver.entiteit_naam if driver else None,
            "entiteit_id": driver.entiteit_id if driver else None,
            "actie": driver.actie if driver else None,
            "aantal_afgeleid": max(0, len(betekenisvol) - 1),
            "records": records,
        })

    volgende = (
        _encode_cursor(pagina[-1].anker, pagina[-1].correlatie_id) if heeft_meer else None
    )
    return gebeurtenissen, volgende
