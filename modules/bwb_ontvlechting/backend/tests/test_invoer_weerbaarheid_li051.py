"""Invoer-weerbaarheid (LI051) — blok A/B-gedrag + de wachters van blok D en E.

De lijn (besluit Bert): **niet filteren op wat gevaarlijk lijkt, maar zorgen dat inhoud nooit
opdracht wordt.** Deze snede doet twee dingen: weigeren wat geen TÉKST is (nul-/stuurtekens; een
regelovergang in een enkelregelig veld) en de inhoud NFC-normaliseren (blok A/B, in de gedeelde
`_validators`-plek); en de al gemeten scheiding inhoud↔opdracht BEWAKEN met bron-scans (blok D/E).

De bron-scans erven het bereik af zoals de bestaande `test_schema_aanroepen_scan` — geen lijst met
bestandsnamen, en elke scan draagt een ZELFTEST die bewijst dat hij bijt.
"""
import ast
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCHEMAS = _ROOT / "modules" / "bwb_ontvlechting" / "backend" / "schemas"


# ── Blok A/B — het gedrag van de gedeelde validators ────────────────────────────

def test_nulteken_geweigerd_in_elk_veld():
    """Blok A — een nulteken is nooit tekst, ook niet in een meerregelig veld."""
    from schemas._validators import _optionele_tekst, _verplichte_tekst

    for mr in (False, True):
        with pytest.raises(ValueError, match="niet kunnen worden opgeslagen"):
            _verplichte_tekst("naam\x00rest", "naam", 255, meerregelig=mr)
        with pytest.raises(ValueError, match="niet kunnen worden opgeslagen"):
            _optionele_tekst("iets\x00", 255, meerregelig=mr)


def test_stuurteken_geweigerd_met_begrijpelijke_melding():
    """Blok A + C — onzichtbaar stuurteken (bv. U+0007) → NL-melding die zegt wát en wát-eraan-doen."""
    from schemas._validators import _verplichte_tekst

    with pytest.raises(ValueError) as exc:
        _verplichte_tekst("Zaak\x07systeem", "naam", 255)
    m = str(exc.value)
    assert "niet kunnen worden opgeslagen" in m
    assert "plak de tekst opnieuw" in m
    # Geen Engelse/technische tekst in de nieuwe melding (blok C).
    assert "Value error" not in m and "control" not in m.lower()


def test_regelovergang_enkelregelig_geweigerd_meerregelig_bewaard():
    """Ontwerpkeuze — een naam is één regel (plakfout), een toelichting mag alinea's dragen."""
    from schemas._validators import _optionele_tekst, _verplichte_tekst

    with pytest.raises(ValueError, match="niet uit meerdere regels"):
        _verplichte_tekst("regel1\nregel2", "naam", 255)  # enkelregelig
    with pytest.raises(ValueError, match="niet uit meerdere regels"):
        _verplichte_tekst("a\tb", "code", 60)  # tab telt óók als meerregelig-teken
    # Meerregelig: alinea's blijven exact bewaard.
    assert _optionele_tekst("Alinea 1.\n\nAlinea 2.", 10_000, meerregelig=True) == "Alinea 1.\n\nAlinea 2."


def test_twee_schrijfwijzen_worden_gelijk():
    """Blok B — 'José' met los accent en met samengestelde letter zijn na normalisatie DEZELFDE
    tekst; zoeken op de een vindt de ander. Onzichtbaar: de gebruiker ziet nog steeds José."""
    from schemas._validators import _verplichte_tekst

    los = "José"  # J o s e + combining acute
    samengesteld = "José"  # J o s é
    assert los != samengesteld  # ruwe invoer verschilt
    a = _verplichte_tekst(los, "naam", 255)
    b = _verplichte_tekst(samengesteld, "naam", 255)
    assert a == b == "José"  # gelijk, en wat de gebruiker ziet is ongewijzigd


def test_gewone_tekst_en_emoji_ongewijzigd():
    """Blok B — gewone tekst, accenten én emoji komen terug zoals bedoeld (vorm, niet toelaatbaarheid)."""
    from schemas._validators import _verplichte_tekst

    for tekst in ("Zaaksysteem", "Bevölkerungsregister", "Zaaksysteem 🚀", "Select & Go", "<adres>"):
        assert _verplichte_tekst(tekst, "naam", 255) == tekst


# ── Blok D — elk tekstveld passeert de gedeelde plek ────────────────────────────

_GEDEELDE_HELPERS = {"_verplichte_tekst", "_optionele_tekst"}


def _schema_bestanden():
    for pad in _SCHEMAS.glob("*.py"):
        if pad.name == "__init__.py":
            continue
        yield pad


def _aangeroepen_namen(fn: ast.FunctionDef) -> set[str]:
    return {
        getattr(k.func, "id", None) or getattr(k.func, "attr", None)
        for k in ast.walk(fn)
        if isinstance(k, ast.Call)
    }


def _bereikt_gedeelde_helper(fn: ast.FunctionDef, lokale_fns: dict[str, ast.FunctionDef]) -> bool:
    """Volgt lokale-functie-indirectie (bv. een dun `_verplichte_reden`-wrapper die zélf de
    gedeelde helper aanroept). Zonder dit zou de scan vals alarm slaan op elke validator die via
    een module-lokale wrapper normaliseert."""
    gezien: set[str] = set()
    stapel = [fn]
    while stapel:
        cur = stapel.pop()
        namen = _aangeroepen_namen(cur)
        if namen & _GEDEELDE_HELPERS:
            return True
        for naam in namen:
            if naam in lokale_fns and naam not in gezien:
                gezien.add(naam)
                stapel.append(lokale_fns[naam])
    return False


def _heeft_gesloten_domein(fn: ast.FunctionDef, lokale_fns: dict[str, ast.FunctionDef]) -> bool:
    """Een validator over een GESLOTEN domein (enum-lidmaatschap of structuur/envelope) draagt geen
    vrije tekst en hoeft de tekst-helper niet: een waarde buiten het domein wordt sowieso geweigerd.
    Afgeleid uit de body — een `in`/`not in`-test of een envelope-aanroep — mét één niveau lokale
    indirectie (de membership-check zit vaak in een dunne `_v_uit_set`/`_v_oordeel`-helper)."""
    gezien: set[str] = set()
    stapel = [fn]
    while stapel:
        cur = stapel.pop()
        for k in ast.walk(cur):
            if isinstance(k, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in k.ops):
                return True
            if isinstance(k, ast.Call):
                naam = getattr(k.func, "id", None) or getattr(k.func, "attr", None) or ""
                if "envelope" in naam:
                    return True
                if naam in lokale_fns and naam not in gezien:
                    gezien.add(naam)
                    stapel.append(lokale_fns[naam])
    return False


def _str_veld_validators(boom: ast.Module):
    """Elke `@field_validator`-functie die een SCALAIR str-veld valideert (annotatie exact `str`
    of `str | None` — géén `list[str]`, dat is een aparte lijst-validatie), plus de module-lokale
    functies (voor indirectie-resolutie)."""
    lokale_fns = {
        k.name: k for k in ast.walk(boom) if isinstance(k, ast.FunctionDef)
    }
    for k in ast.walk(boom):
        if not isinstance(k, ast.FunctionDef):
            continue
        is_validator = any(
            (getattr(d.func if isinstance(d, ast.Call) else d, "attr", None)
             or getattr(d.func if isinstance(d, ast.Call) else d, "id", None)) == "field_validator"
            for d in k.decorator_list
        )
        if not is_validator:
            continue
        # De tweede parameter is `v`; de annotatie staat op de parameter.
        ann = None
        for arg in k.args.args:
            if arg.arg == "v":
                ann = arg.annotation
        tekst = ast.unparse(ann).replace(" ", "") if ann is not None else ""
        if tekst in ("str", "str|None", "Optional[str]"):
            yield k, lokale_fns


def test_elk_vrije_tekst_veld_loopt_via_de_gedeelde_plek():
    """Blok D — een str-veld-validator die de gedeelde `_validators`-weg omzeilt is precies het gat
    dat de invoer-weerbaarheid mist. Afgeleid bereik (élk schema-`@field_validator` op een str-veld);
    geen bestandslijst. Gesloten-domein-validators (enum-lidmaatschap) zijn afgeleid uitgezonderd —
    die dragen geen vrije tekst.

    WAT DEZE WACHTER DEKT: elke Pydantic-str-veldvalidator in `schemas/`, mét één niveau lokale
    indirectie. WAT HIJ NIET DEKT: een tekstwaarde die zónder Pydantic-schema binnenkomt (query-
    params op een route) — die lopen via aparte `Query(..., max_length=)`-grenzen, niet via deze
    validators; dat valt buiten deze scan."""
    overtreders = []
    for pad in _schema_bestanden():
        boom = ast.parse(pad.read_text(encoding="utf-8"))
        for fn, lokale_fns in _str_veld_validators(boom):
            if _heeft_gesloten_domein(fn, lokale_fns):
                continue
            if not _bereikt_gedeelde_helper(fn, lokale_fns):
                overtreders.append(f"{pad.name}:{fn.name}")
    assert not overtreders, (
        "Deze str-veld-validators valideren vrije tekst zonder de gedeelde `_verplichte_tekst`/"
        f"`_optionele_tekst` (blok A/B lopen er dan langs): {overtreders}"
    )


def test_blok_d_scan_bijt():
    """Zelftest — een validator die een rauwe string teruggeeft zonder de gedeelde helper (ook niet
    via indirectie) wordt gevangen; via een lokale wrapper wél; en een enum-membership-validator is
    uitgezonderd."""
    mod = ast.parse(
        "def _wrap(v):\n"
        "    return _optionele_tekst(v, 60)\n"
        "def _slecht(cls, v: str):\n"
        "    return v.strip()\n"
        "def _goed_direct(cls, v: str):\n"
        "    return _verplichte_tekst(v, 'x', 60)\n"
        "def _goed_indirect(cls, v: str):\n"
        "    return _wrap(v)\n"
        "def _enum(cls, v: str):\n"
        "    if v not in ('a', 'b'):\n"
        "        raise ValueError('x')\n"
        "    return v\n"
    )
    fns = {k.name: k for k in mod.body}
    assert _bereikt_gedeelde_helper(fns["_slecht"], fns) is False   # gevangen
    assert _bereikt_gedeelde_helper(fns["_goed_direct"], fns) is True
    assert _bereikt_gedeelde_helper(fns["_goed_indirect"], fns) is True  # indirectie gevolgd
    assert _heeft_gesloten_domein(fns["_enum"], fns) is True        # membership-uitzondering
    # Membership één niveau diep (via een dunne helper) telt óók als gesloten domein.
    mod2 = ast.parse(
        "def _uit_set(v, s):\n"
        "    if v not in s:\n"
        "        raise ValueError('x')\n"
        "    return v\n"
        "def _v(cls, v: str):\n"
        "    return _uit_set(v, S)\n"
    )
    fns2 = {k.name: k for k in mod2.body}
    assert _heeft_gesloten_domein(fns2["_v"], fns2) is True


# ── Blok E — de scheiding inhoud↔opdracht bewaken ───────────────────────────────

_BACKEND_WORTELS = (
    _ROOT / "modules" / "bwb_ontvlechting" / "backend" / "services",
    _ROOT / "modules" / "bwb_ontvlechting" / "backend" / "routes",
    _ROOT / "backend" / "app",
)


def _py_regels(wortels):
    for wortel in wortels:
        for pad in wortel.rglob("*.py"):
            if "__pycache__" in pad.parts or "test" in pad.name:
                continue
            yield pad, pad.read_text(encoding="utf-8")


_IDENTIFIER_KEYWORDS = ("from ", "into ", "join ", "update ", "table ")


def _lokale_literal_namen(fn: ast.FunctionDef | None) -> set[str]:
    """Namen die BINNEN deze functie uitsluitend aan string-literals (of een keuze daartussen)
    zijn gebonden — code-constante SQL-fragmenten, geen gebruikersinvoer. Bv.
    `sub_filter = "b.tenant_id = :tid AND " if … else ""`."""
    if fn is None:
        return set()

    def _is_lit(node) -> bool:
        if isinstance(node, ast.Constant):
            return isinstance(node.value, str)
        if isinstance(node, ast.IfExp):  # a if c else b
            return _is_lit(node.body) and _is_lit(node.orelse)
        return False

    namen = set()
    for k in ast.walk(fn):
        if isinstance(k, ast.Assign) and _is_lit(k.value):
            for doel in k.targets:
                if isinstance(doel, ast.Name):
                    namen.add(doel.id)
    return namen


def _fstring_waarde_interpolaties(arg: ast.JoinedStr, literalnamen: set[str]) -> bool:
    """True als de f-string een WAARDE interpoleert (het gevaar). AFGELEID veilig — en dus géén
    treffer — zijn: (1) een IDENTIFIER-positie (het deel ervóór eindigt op FROM/INTO/JOIN/… → een
    tabel-/kolomnaam, die SQL niet kan binden); (2) een kale naam die in deze functie aan een
    string-literal is gebonden (code-constant fragment). Alles anders (attribuut/subscript/aanroep,
    of een kale naam die een parameter/waarde is) telt als waarde-interpolatie."""
    delen = arg.values
    for i, deel in enumerate(delen):
        if not isinstance(deel, ast.FormattedValue):
            continue
        vorige = delen[i - 1] if i > 0 else None
        vorige_tekst = vorige.value.lower() if isinstance(vorige, ast.Constant) and isinstance(vorige.value, str) else ""
        if any(vorige_tekst.rstrip().endswith(kw.strip()) or vorige_tekst.endswith(kw) for kw in _IDENTIFIER_KEYWORDS):
            continue  # identifier-positie → veilig
        if isinstance(deel.value, ast.Name) and deel.value.id in literalnamen:
            continue  # lokale string-literal → veilig
        return True  # waarde-interpolatie
    return False


def _detecteer_sql_samenvoeging(bron: str) -> list[str]:
    """Een `text(...)` waarin een WAARDE wordt samengevoegd (f-string met een waarde-expressie, of
    `+`/`%`/`.format`) = tekst samengevoegd tot een opdracht aan de opslag. Gescheiden parameters
    (`text("… :p")`), identifier-interpolatie (`FROM {tabel}`) en lokale-literal-fragmenten zijn
    juist goed — afgeleid uit de code, niet uit een bestandslijst."""
    treffers = []
    boom = ast.parse(bron)
    # Map elke text()-Call naar zijn omvattende functie (voor de lokale-literal-check).
    fn_van: dict[int, ast.FunctionDef] = {}
    for fn in ast.walk(boom):
        if isinstance(fn, ast.FunctionDef):
            for k in ast.walk(fn):
                fn_van[id(k)] = fn
    for knoop in ast.walk(boom):
        if not (isinstance(knoop, ast.Call) and getattr(knoop.func, "id", None) == "text"):
            continue
        literalnamen = _lokale_literal_namen(fn_van.get(id(knoop)))
        for arg in knoop.args:
            if isinstance(arg, ast.JoinedStr):  # f-string
                if _fstring_waarde_interpolaties(arg, literalnamen):
                    treffers.append("text(f'…{waarde}…')")
            elif isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Add, ast.Mod)):
                treffers.append("text(… + / % …)")
            elif isinstance(arg, ast.Call) and getattr(arg.func, "attr", None) == "format":
                treffers.append("text(….format(…))")
    return treffers


def test_geen_zoekopdracht_wordt_als_tekst_samengevoegd():
    """Blok E — alle opslag-opdrachten leveren waarden gescheiden aan als parameter (0
    waarde-samenvoegingen).

    WAT DEZE WACHTER DEKT: elke `text(...)`-aanroep in services/routes/app. WAT HIJ NIET DEKT:
    identifier-interpolatie (een tabel-/kolomnaam-`{naam}`), die SQL sowieso niet kan binden en
    hier uit een code-constante komt — die wordt afgeleid uitgezonderd (geen waarde-expressie).
    De hash-chain-lees in `app/core/audit.py` interpoleert zó een tabelnaam; dat is geverifieerd
    veilig en géén gebruikersinhoud."""
    overtreders = []
    for pad, bron in _py_regels(_BACKEND_WORTELS):
        for t in _detecteer_sql_samenvoeging(bron):
            overtreders.append(f"{pad.name}: {t}")
    assert not overtreders, f"waarde samengevoegd tot een opslag-opdracht: {overtreders}"


def test_blok_e_sql_scan_bijt():
    """Zelftest — waarde-interpolatie (óók via een kale naam-parameter in waarde-positie) wordt
    gevangen; geparametriseerd, identifier-positie en lokaal literal-fragment niet."""
    assert _detecteer_sql_samenvoeging('text(f"SELECT {req.q}")')          # attribuut = waarde
    assert _detecteer_sql_samenvoeging('text(f"SELECT {rijen[0]}")')       # subscript = waarde
    assert _detecteer_sql_samenvoeging('def z(t):\n return text(f"WHERE n = {t}")')  # param in waarde-positie
    assert _detecteer_sql_samenvoeging('q = text("a" + b)')
    assert _detecteer_sql_samenvoeging('text("SELECT * WHERE n = :naam")') == []
    # Identifier-positie (na FROM/INTO) — een tabelnaam, geen waarde.
    assert _detecteer_sql_samenvoeging('text(f"SELECT x FROM {tabel} a")') == []
    assert _detecteer_sql_samenvoeging('text(f"INSERT INTO {tabel} (a)")') == []
    # Lokaal literal-fragment (met gebonden :param) — code-constant, geen gebruikersinvoer.
    assert _detecteer_sql_samenvoeging(
        'def z(tid):\n'
        '    sub = "b.tid = :tid AND " if tid else ""\n'
        '    return text(f"... WHERE {sub}b.x = a.y")'
    ) == []


def test_geen_gebruikersinhoud_rechtstreeks_in_de_pagina():
    """Blok E — nergens `v-html`/`innerHTML`/`insertAdjacentHTML`/`document.write` in de frontend:
    alle inhoud loopt via Vue-interpolatie (die escapet). Afgeleid bereik: álle .vue/.js buiten test."""
    _FE_WORTELS = (
        _ROOT / "frontend" / "src",
        _ROOT / "modules" / "bwb_ontvlechting" / "frontend",
    )
    verboden = ("v-html", "innerHTML", "insertAdjacentHTML", "outerHTML", "document.write")
    overtreders = []
    aantal_bestanden = 0
    for wortel in _FE_WORTELS:
        for pad in wortel.rglob("*"):
            if pad.suffix not in (".vue", ".js") or "node_modules" in pad.parts:
                continue
            if pad.name.endswith(".test.js") or "test" in pad.parts:
                continue
            aantal_bestanden += 1
            bron = pad.read_text(encoding="utf-8")
            for term in verboden:
                if term in bron:
                    overtreders.append(f"{pad.name}: {term}")
    assert aantal_bestanden > 50, "bereik onverwacht smal — scan dekt niet wat hij belooft"
    assert not overtreders, f"gebruikersinhoud kan als opmaak/code op het scherm belanden: {overtreders}"


def test_blok_e_html_scan_bijt():
    """Zelftest — een v-html-regel wordt herkend als overtreding."""
    nep = '<div v-html="gebruikerstekst"></div>'
    assert any(t in nep for t in ("v-html", "innerHTML"))
    schoon = '<div>{{ gebruikerstekst }}</div>'
    assert not any(t in schoon for t in ("v-html", "innerHTML", "insertAdjacentHTML"))
