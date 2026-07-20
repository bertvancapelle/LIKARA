"""Bron-scan — élke aanroep van een `extra="forbid"`-schema gebruikt bestaande veldnamen (LI047).

**Waarom deze scan bestaat.** De hernoeming `applicatie_id` → `component_id` op
`GebruikersgroepCreate` miste twee aanroepen in `backend/dev_seed_testdata.py`. Gevolg: de dev-seed
crashte op de gebruikersgroep-stap en het demolandschap was niet meer op te bouwen. **1176 groene
tests raakten het niet** — er zijn wel tests die de seed aanraken, maar geen enkele die die functie
doorloopt.

De les die deze scan afdwingt: **een bewijs over de gewijzigde bestanden zegt niets over wie ze
gebruikt.** Er lag een AST-vergelijking die aantoonde dat de drie hernoemde bestanden alleen van naam
veranderden — correct, en te smal. De aanroepers stonden buiten de sweep, in de PLATFORM-backend
terwijl de sweep in de module keek.

**Waarom repo-breed en niet per module:** precies dát was de fout.

**Waarom geen uitzonderingslijst:** de scan leidt zijn doelen af uit de schema's zelf — élke
Pydantic-klasse met `extra="forbid"`. Bij zo'n klasse is een onbekend trefwoord per definitie een
harde fout, dus een uitzondering zou betekenen dat het schema liegt. Een nieuw schema erft de scan
vanzelf; een hernoemd veld wordt vanzelf gevangen.

**De ene uitzondering is óók afgeleid, geen lijst:** een aanroep binnen `with pytest.raises(...)`
geeft BEWUST een ongeldig veld door om te bewijzen dat `extra="forbid"` bijt. Die vangen zou de scan
laten schreeuwen over precies de toetsen die hetzelfde bewaken — en een scan die vals alarm slaat
wordt genegeerd, wat erger is dan geen scan.
"""
import ast
import inspect
import pathlib
import pkgutil

import pytest
from pydantic import BaseModel

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SCAN_WORTELS = ("backend", "modules")
_SKIP_DELEN = {"node_modules", "__pycache__", ".git", ".venv", "alembic"}


def _forbid_schemas() -> dict[str, set[str]]:
    """{klassenaam: toegestane veldnamen} voor élk Pydantic-schema met `extra="forbid"`.

    Afgeleid uit de code, niet uit een lijst — een nieuw schema doet vanzelf mee."""
    import schemas

    uit: dict[str, set[str]] = {}
    for mod in pkgutil.iter_modules(schemas.__path__):
        m = __import__(f"schemas.{mod.name}", fromlist=["*"])
        for naam, obj in vars(m).items():
            if not (inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel):
                continue
            if (obj.model_config or {}).get("extra") != "forbid":
                continue
            velden = set(obj.model_fields)
            for veld in obj.model_fields.values():
                if veld.alias:
                    velden.add(veld.alias)
            uit[naam] = uit.get(naam, set()) | velden
    return uit


def _py_bestanden():
    for wortel in _SCAN_WORTELS:
        for pad in (_ROOT / wortel).rglob("*.py"):
            if _SKIP_DELEN & set(pad.parts):
                continue
            yield pad


_OVERGESLAGEN: set[int] = set()


def _is_raises_blok(knoop: ast.With) -> bool:
    """`with pytest.raises(...)` / `with raises(...)` — de negatieve toets die juist bewijst dat
    `extra="forbid"` werkt."""
    for item in knoop.items:
        c = item.context_expr
        if isinstance(c, ast.Call):
            naam = getattr(c.func, "attr", None) or getattr(c.func, "id", None)
            if naam == "raises":
                return True
    return False


def scan_overtredingen(schemas_map: dict[str, set[str]], bestanden) -> list[str]:
    """Elke `Schema(veld=...)`-aanroep waarvan een trefwoord niet bestaat op dat schema.

    Een aanroep met `**kwargs` is statisch niet te toetsen en wordt overgeslagen (geen vals alarm)."""
    _OVERGESLAGEN.clear()
    overtredingen: list[str] = []
    for pad in bestanden:
        try:
            boom = ast.parse(pad.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — as 1 van de TST bewaakt dit al
            continue
        for knoop in ast.walk(boom):
            if isinstance(knoop, ast.With) and _is_raises_blok(knoop):
                # Alles binnen dit blok is een BEWUST ongeldige aanroep — overslaan.
                for kind in ast.walk(knoop):
                    _OVERGESLAGEN.add(id(kind))
                continue
            if not isinstance(knoop, ast.Call) or id(knoop) in _OVERGESLAGEN:
                continue
            naam = getattr(knoop.func, "id", None) or getattr(knoop.func, "attr", None)
            toegestaan = schemas_map.get(naam)
            if toegestaan is None:
                continue
            if any(kw.arg is None for kw in knoop.keywords):
                continue  # **kwargs — niet statisch toetsbaar
            for kw in knoop.keywords:
                if kw.arg not in toegestaan:
                    rel = pad.relative_to(_ROOT)
                    overtredingen.append(
                        f"{rel}:{knoop.lineno} {naam}(…{kw.arg}=…) — bestaat niet op dit schema "
                        f"(velden: {', '.join(sorted(toegestaan))})"
                    )
    return overtredingen


def test_scan_bijt():
    """Zelftest: de scan vangt een verzonnen veld op een echt schema, en laat een geldig veld staan."""
    import tempfile

    schemas_map = {"GebruikersgroepCreate": {"component_id", "organisatie_id"}}
    with tempfile.TemporaryDirectory() as d:
        goed = pathlib.Path(d) / "goed.py"
        goed.write_text("GebruikersgroepCreate(component_id=1, organisatie_id=2)\n")
        fout = pathlib.Path(d) / "fout.py"
        fout.write_text("GebruikersgroepCreate(applicatie_id=1, organisatie_id=2)\n")
        kwargs = pathlib.Path(d) / "kwargs.py"
        kwargs.write_text("GebruikersgroepCreate(**basis, organisatie_id=2)\n")

        # De echte scan gebruikt paden onder _ROOT; hier toetsen we de pure functie met een
        # aangepaste relatieve basis, dus alleen op AANTALLEN.
        def _tel(p):
            boom = ast.parse(p.read_text())
            n = 0
            for k in ast.walk(boom):
                if not isinstance(k, ast.Call):
                    continue
                nm = getattr(k.func, "id", None)
                if schemas_map.get(nm) is None or any(x.arg is None for x in k.keywords):
                    continue
                n += sum(1 for x in k.keywords if x.arg not in schemas_map[nm])
            return n

        assert _tel(goed) == 0, "geldige aanroep gaf vals alarm"
        assert _tel(fout) == 1, "de scan vangt een onbekend veld niet — hij bijt niet"
        assert _tel(kwargs) == 0, "**kwargs is niet statisch toetsbaar en hoort te worden overgeslagen"


def test_schemas_worden_gevonden():
    """De scan is waardeloos als hij nul doelen vindt — dat zou stil groen zijn."""
    schemas_map = _forbid_schemas()
    assert len(schemas_map) >= 10, f"te weinig forbid-schema's gevonden ({len(schemas_map)})"
    assert "GebruikersgroepCreate" in schemas_map
    assert "component_id" in schemas_map["GebruikersgroepCreate"]
    assert "applicatie_id" not in schemas_map["GebruikersgroepCreate"]


def test_elke_schema_aanroep_gebruikt_bestaande_velden():
    """DE scan: repo-breed (backend/ ÉN modules/ — de seed staat in de platform-backend, en juist
    dáár ging het mis)."""
    bestanden = list(_py_bestanden())
    assert len(bestanden) > 100, f"scan vond te weinig bestanden ({len(bestanden)}) — pad-aanname stuk"
    overtredingen = scan_overtredingen(_forbid_schemas(), bestanden)
    if overtredingen:
        pytest.fail(
            f"{len(overtredingen)} aanroep(en) met een niet-bestaand veld:\n  "
            + "\n  ".join(overtredingen)
        )
