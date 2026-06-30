"""Tests — gen_build backup-stap (CD013-A): iCloud-kopie, secrets uitgesloten."""
import sys
from pathlib import Path

_GEN = Path(__file__).resolve().parents[2] / "docs" / "_generators"
sys.path.insert(0, str(_GEN))

import gen_build  # noqa: E402


def test_kopieert_alleen_sql_niet_secrets(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    dump = backups / "likara_20260607_1200.sql"
    dump.write_text("DUMP")
    (backups / ".env").write_text("POSTGRES_PASSWORD=geheim")  # mag NOOIT mee

    icloud = tmp_path / "icloud" / "CompliData-backups"  # parent (icloud) bestaat
    icloud.parent.mkdir()

    assert gen_build.kopieer_naar_icloud(dump, icloud) is True
    assert (icloud / dump.name).read_text() == "DUMP"
    # alleen de .sql in de doelmap — geen .env / secrets
    assert [p.name for p in icloud.iterdir()] == [dump.name]


def test_ontbrekende_icloud_map_waarschuwt_zonder_fout(tmp_path):
    dump = tmp_path / "likara_x.sql"
    dump.write_text("D")
    afwezig = tmp_path / "niet_gemount" / "sub"  # parent bestaat niet → niet gemount
    assert gen_build.kopieer_naar_icloud(dump, afwezig) is False  # geen exception
    assert not afwezig.exists()  # geen pad geforceerd


def test_weigert_niet_sql_bestand(tmp_path):
    nep = tmp_path / "complidata.env"  # geen .sql
    nep.write_text("x")
    icloud = tmp_path / "ic"
    icloud.mkdir()
    assert gen_build.kopieer_naar_icloud(nep, icloud) is False
    assert list(icloud.iterdir()) == []


def test_geen_dump_geeft_false(tmp_path):
    assert gen_build.kopieer_naar_icloud(None, tmp_path) is False


def test_backup_stap_volgorde_dump_dan_icloud(monkeypatch, tmp_path):
    volgorde = []
    dump = tmp_path / "likara_y.sql"
    dump.write_text("D")

    def _fake_dump():
        volgorde.append("dump")
        return dump

    def _fake_icloud(d, *a, **k):
        volgorde.append("icloud")
        assert d == dump  # de zojuist gemaakte dump
        return True

    monkeypatch.setattr(gen_build, "maak_db_dump", _fake_dump)
    monkeypatch.setattr(gen_build, "kopieer_naar_icloud", _fake_icloud)
    gen_build.backup_stap()
    assert volgorde == ["dump", "icloud"]  # iCloud-kopie ná de lokale dump
