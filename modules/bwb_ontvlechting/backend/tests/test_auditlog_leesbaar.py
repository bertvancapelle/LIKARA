"""Tests — het auditlog vertelt wat er gebeurde (LI048 besluit 1 + 2).

Pure toetsen op de twee regels die bepalen WELKE gebeurtenis wordt getoond en MET WELKE naam.
Geen DB nodig: beide helpers werken op een auditrecord, en juist door ze hier los te toetsen
staat elke regel apart overeind — de integratiekant (hernoemen verandert de geschiedenis niet)
staat in test_auditlog_naam_resolutie.py.
"""
import types

from services.auditlog_service import (
    _is_betekenisloos,
    _kies_driver,
    _toon_naam,
    _vastgelegde_naam,
)


def _rec(entiteit_type="component", actie="create", wijziging=None):
    return types.SimpleNamespace(entiteit_type=entiteit_type, actie=actie, wijziging=wijziging)


# ── Besluit 2 — de betekenisloze regel is nooit de aanleiding ────────────────────────────
def test_supertype_rij_is_betekenisloos():
    # De `element`-rij draagt alleen het discriminator-veld: zij zegt dát er iets bestaat,
    # niet wát. 14.398 regels in het demolandschap begonnen hiermee.
    assert _is_betekenisloos(_rec("element", wijziging={"element_type": {"oud": None, "nieuw": "partij"}}))


def test_rij_met_inhoud_is_niet_betekenisloos():
    assert not _is_betekenisloos(_rec("partij", wijziging={"naam": {"oud": None, "nieuw": "X"}}))
    # Een `element`-rij die WÉL iets inhoudelijks draagt telt gewoon mee — het criterium is de
    # inhoud, niet de tabelnaam. Zo hoeft niemand een naam aan een lijst toe te voegen.
    assert not _is_betekenisloos(
        _rec("element", wijziging={"element_type": {"nieuw": "partij"}, "naam": {"nieuw": "X"}})
    )


def test_lege_wijziging_telt_niet_als_betekenisloos():
    # Niets weten is iets anders dan "alleen de discriminator dragen"; zo'n rij mag driver zijn.
    assert not _is_betekenisloos(_rec(wijziging=None))
    assert not _is_betekenisloos(_rec(wijziging={}))


def test_driver_slaat_de_supertype_rij_over():
    element = _rec("element", wijziging={"element_type": {"nieuw": "work_package"}})
    wp = _rec("work_package", wijziging={"naam": {"oud": None, "nieuw": "WP-Audit"}})
    # Chronologisch staat `element` vooraan — dáár ging het mis.
    assert _kies_driver([element, wp]) is wp


def test_driver_valt_terug_als_niets_betekenis_draagt():
    # Beter een magere regel dan geen regel: zegt geen enkel record iets, dan wint de eerste.
    element = _rec("element", wijziging={"element_type": {"nieuw": "partij"}})
    assert _kies_driver([element]) is element
    assert _kies_driver([]) is None


# ── Besluit 1 — de naam van TOEN wint ────────────────────────────────────────────────────
def test_aanmaak_gebruikt_de_vastgelegde_nieuwe_naam():
    assert _vastgelegde_naam(_rec(actie="create", wijziging={"naam": {"oud": None, "nieuw": "Zaaksysteem"}})) == "Zaaksysteem"


def test_verwijdering_gebruikt_de_oude_naam():
    # Bij een delete is `nieuw` leeg: de naam zoals hij WAS is het enige spoor dat overblijft.
    assert _vastgelegde_naam(_rec(actie="delete", wijziging={"naam": {"oud": "Cascade", "nieuw": None}})) == "Cascade"


def test_wijziging_van_de_naam_toont_de_nieuwe():
    # Een hernoeming is zelf een gebeurtenis; die regel gaat over de naam die het werd.
    assert _vastgelegde_naam(_rec(actie="update", wijziging={"naam": {"oud": "Oud", "nieuw": "Nieuw"}})) == "Nieuw"


def test_geen_naamveld_geeft_niets():
    # Dan valt de service terug op de huidige naam — behalve bij een delete. Deze helper zegt
    # alleen "ik weet het niet"; de keuze wat dan te doen ligt in de service.
    assert _vastgelegde_naam(_rec(actie="update", wijziging={"levensfase": {"oud": "a", "nieuw": "b"}})) is None
    assert _vastgelegde_naam(_rec(wijziging=None)) is None


def test_lege_of_witruimte_naam_telt_niet_als_naam():
    # Anders toont het scherm een lege plek waar een naam hoort — verwarrender dan een id.
    assert _vastgelegde_naam(_rec(actie="create", wijziging={"naam": {"nieuw": "   "}})) is None
    assert _vastgelegde_naam(_rec(actie="create", wijziging={"naam": {"nieuw": 42}})) is None


# ── Besluit 1, de service-tak — welke naam belandt er daadwerkelijk op de regel ───────────
# Deze vier toetsen bestaan omdat een opzettelijke breuk in de delete-tak eerst GROEN bleef:
# geen enkele toets oefende hem. De keuze staat nu in `_toon_naam`, en wordt hier los geoefend.
def _rec_id(entiteit_type="component", actie="create", wijziging=None, eid="11111111-1111-1111-1111-111111111111"):
    return types.SimpleNamespace(
        entiteit_type=entiteit_type, actie=actie, wijziging=wijziging, entiteit_id=eid,
    )


_HUIDIG = {("component", "11111111-1111-1111-1111-111111111111"): "Naam Van Nu"}


def test_vastgelegde_naam_gaat_voor_de_huidige():
    # De kern van besluit 1: hernoemen verandert de geschiedenis niet.
    rec = _rec_id(wijziging={"naam": {"oud": None, "nieuw": "Naam Van Toen"}})
    assert _toon_naam(rec, _HUIDIG) == "Naam Van Toen"


def test_zonder_vastgelegde_naam_valt_hij_terug_op_de_huidige():
    # De erkende TEKORTKOMING (geen ontwerp): bij een wijziging van een ánder veld staat er geen
    # naam in de rij, dus verandert die regel alsnog mee bij een hernoeming. Opvolgpunt.
    rec = _rec_id(actie="update", wijziging={"levensfase": {"oud": "a", "nieuw": "b"}})
    assert _toon_naam(rec, _HUIDIG) == "Naam Van Nu"


def test_verwijdering_gebruikt_NOOIT_de_huidige_naam():
    # Het object hoort niet meer te bestaan. Komt er tóch iets uit de resolutie, dan is dat een
    # ander object dat het id hergebruikt — misleidender dan geen naam.
    rec = _rec_id(actie="delete", wijziging={"reden": {"oud": "x", "nieuw": None}})
    assert _toon_naam(rec, _HUIDIG) is None


def test_verwijdering_toont_de_vastgelegde_oude_naam():
    rec = _rec_id(actie="delete", wijziging={"naam": {"oud": "Cascade", "nieuw": None}})
    assert _toon_naam(rec, _HUIDIG) == "Cascade"


# ── LI048 snede 3, besluit 3 — ELKE soort heeft een aanwijsbare naambron ─────────────────
# Dit is DE regel van deze snede, niet het geval. Twee soorten toonden een kale code; die twee
# los repareren lost het patroon niet op — de volgende soort komt er weer naamloos bij. Deze
# toets dwingt af dat er over élke geauditeerde soort een uitspraak bestaat.
def test_elke_geauditeerde_soort_staat_in_het_naambron_register():
    from app.core.audit import AUDIT_TENANT_ENTITEITEN
    from services.auditlog_service import NAAMBRON

    ontbreekt = sorted(AUDIT_TENANT_ENTITEITEN - set(NAAMBRON))
    assert not ontbreekt, (
        "Deze soorten worden geauditeerd maar hebben geen uitspraak over hun naam: "
        f"{ontbreekt}. Voeg ze toe aan NAAMBRON — óók als het antwoord 'geen naam' is; "
        "dat moet een besluit zijn met een reden, geen stilzwijgende terugval op een code."
    )


def test_het_register_verzint_geen_soorten():
    # Andersom: een sleutel die niet geauditeerd wordt is dode code die suggereert dat er iets
    # geregeld is. Beide richtingen moeten kloppen, anders zegt de toets hierboven niets.
    from app.core.audit import AUDIT_TENANT_ENTITEITEN
    from services.auditlog_service import NAAMBRON

    onbekend = sorted(set(NAAMBRON) - AUDIT_TENANT_ENTITEITEN)
    assert not onbekend, f"NAAMBRON noemt soorten die niet geauditeerd worden: {onbekend}"


def test_elke_geen_naam_uitspraak_draagt_een_leesbare_reden():
    # "Geen naam" mag, maar niet zonder verantwoording — anders is het alsnog een stille
    # terugval, alleen met een vinkje ervoor.
    from services.auditlog_service import NAAMBRON

    zonder_reden = [
        soort for soort, bron in NAAMBRON.items()
        if bron[0] == "geen" and (len(bron) < 2 or not isinstance(bron[1], str) or len(bron[1]) < 15)
    ]
    assert not zonder_reden, f"Deze 'geen naam'-uitspraken missen een leesbare reden: {zonder_reden}"


def test_register_kent_alleen_bekende_vormen():
    from services.auditlog_service import NAAMBRON

    for soort, bron in NAAMBRON.items():
        assert bron[0] in {"veld", "leen_veld", "leen_identiteit", "geen"}, (soort, bron)


# ── Besluit 1 — een checklistvraag heet naar zijn vraagtekst ─────────────────────────────
def test_checklistvraag_gebruikt_zijn_vraagtekst_als_naam():
    rec = _rec("checklistvraag", "create", {"vraag": {"oud": None, "nieuw": "Is de technische plaatsing vastgelegd?"}})
    assert _vastgelegde_naam(rec) == "Is de technische plaatsing vastgelegd?"


def test_lange_vraagtekst_wordt_afgekort_maar_blijft_herkenbaar():
    # Het begin draagt de herkenning; de volledige tekst hoort niet in een lijstregel.
    lang = "Op welke infrastructuur draait de applicatie (server, datacenter, cloudplatform) en wie beheert die?"
    naam = _toon_naam(_rec_id("checklistvraag", "create", {"vraag": {"nieuw": lang}}), {})
    assert naam.startswith("Op welke infrastructuur draait")
    assert naam.endswith("…") and len(naam) <= 80


def test_afkorten_gebeurt_op_EEN_plek_ook_bij_de_terugval():
    # Eerst kortte alleen de vastgelegde route af en de terugval niet — dan hangt de lengte af
    # van welke route toevallig een naam opleverde.
    lang = "X" * 200
    rec = _rec_id("checklistvraag", "update", {"actief": {"oud": True, "nieuw": False}})
    naam = _toon_naam(rec, {("checklistvraag", "11111111-1111-1111-1111-111111111111"): lang})
    assert len(naam) <= 80 and naam.endswith("…")


# ── Besluit 2 — een componentprofiel leent de naam van zijn component ────────────────────
def test_componentprofiel_leent_via_de_gedeelde_sleutel():
    # `component_profiel.id` is een FK naar `component.id` (1-op-1 uitbreiding), dus het id ís
    # de ingang. NB de opdracht ging uit van een `component_id` in de wijziging; die staat er
    # niet in (0 van 2.085 rijen) — gemeten, niet aangenomen.
    from services.auditlog_service import _geleend_component_id

    rec = _rec_id("component_profiel", "derive", {"lifecycle_status": {"oud": None, "nieuw": "concept"}})
    assert _geleend_component_id(rec) == "11111111-1111-1111-1111-111111111111"
    assert _toon_naam(rec, {("component", "11111111-1111-1111-1111-111111111111"): "Zaaksysteem"}) == "Zaaksysteem"


def test_checklistscore_leent_via_component_id_in_de_wijziging():
    from services.auditlog_service import _geleend_component_id

    rec = _rec_id("checklistscore", "create", {"component_id": {"oud": None, "nieuw": "abc-123"}})
    assert _geleend_component_id(rec) == "abc-123"
    assert _toon_naam(rec, {("component", "abc-123"): "Klantportaal"}) == "Klantportaal"


def test_geleende_naam_werkt_ook_bij_een_verwijderd_koppelfeit():
    # Bij een delete van het koppelfeit bestaat het COMPONENT nog (anders was deze rij
    # meegecascadeerd), dus hier is de huidige naam juist wél de goede — en de enige die er is.
    rec = _rec_id("checklistscore", "delete", {"component_id": {"oud": "abc-123", "nieuw": None}})
    assert _toon_naam(rec, {("component", "abc-123"): "Klantportaal"}) == "Klantportaal"


def test_soort_zonder_naambron_levert_geen_code_op():
    # Een bewust naamloze soort geeft None — de UI toont dan het id, maar dat is een BESLUIT
    # met een opgeschreven reden, geen ongemerkt gat.
    rec = _rec_id("roltoewijzing", "create", {"rol": {"oud": None, "nieuw": "beheerder"}})
    assert _toon_naam(rec, {}) is None


# ── LI048 — het component-filter: wat is er met DIT ding gebeurd? ────────────────────────
# De dekking was hier dun: één toets die alleen bewees dat er íets terugkwam. Het gedrag dat
# afgeleide regels meekomen was er al, maar was nergens vastgelegd — het kon dus ongemerkt
# verdwijnen. En koppelingen kwamen NIET mee, wat niemand had gemeld.
def _filter_clausules(cid):
    """De filterclausules zoals de lijst ze bouwt, als leesbare SQL-tekst."""
    import uuid as _uuid

    from services.auditlog_service import _record_filters

    clauses = _record_filters(
        _uuid.UUID("11111111-1111-1111-1111-111111111111"),
        actor=None, entiteit_type=None, entiteit_id=None, component_id=cid,
        van=None, tot=None, actie=None, subs=None,
    )
    return " ".join(str(c.compile(compile_kwargs={"literal_binds": True})) for c in clauses)


def test_componentfilter_pakt_de_koppelingen_van_het_component():
    # HET HERSTEL: een `relatie` draagt nooit een `component_id` (0 van 9.291 regels), dus
    # "iemand haalde de koppeling naar DigiD weg" was onvindbaar via dit filter — terwijl dát
    # vaak precies is waar de consultant naar zoekt als er iets niet meer werkt.
    sql = _filter_clausules("abc-123")
    assert "bron_id" in sql, "koppelingen waarin het component BRON is moeten meekomen"
    assert "doel_id" in sql, "koppelingen waarin het component DOEL is moeten meekomen"


def test_componentfilter_pakt_de_afgeleide_regels():
    # Deze dekking ontbrak volledig terwijl het gedrag er al was. Profiel en element delen hun
    # primaire sleutel met het component (entiteit_id-tak); score/functievervulling/blokkade
    # dragen het component_id in hun diff.
    sql = _filter_clausules("abc-123")
    assert "entiteit_id" in sql, "rijen die de PK met het component delen (profiel, element)"
    assert "component_id" in sql, "rijen die het component in hun diff dragen (score, blokkade)"


def test_componentfilter_kijkt_naar_oud_EN_nieuw():
    # Een verwijderde koppeling draagt zijn ids in `oud`, niet in `nieuw`. Alleen naar `nieuw`
    # kijken zou juist de ONTkoppelingen missen — precies waar de consultant naar zoekt als er
    # iets niet meer werkt. Per veld beide takken los toetsen; een losse "oud" ergens in de
    # SQL bewijst niets (de eerste versie van deze toets deed dat, en oefende zijn geval dus niet).
    sql = _filter_clausules("abc-123")
    for veld in ("component_id", "bron_id", "doel_id"):
        for tak in ("nieuw", "oud"):
            assert f"audit_log.wijziging['{veld}']) ->> '{tak}'" in sql, f"{veld}.{tak} ontbreekt"


def test_zonder_componentfilter_geen_component_clausule():
    # De filters zijn AND-gecombineerd; een niet-gezet filter mag niets beperken.
    sql = _filter_clausules(None)
    assert "bron_id" not in sql and "component_id" not in sql
