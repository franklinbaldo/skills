# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest", "cyclopts>=3.0", "pydantic>=2.6"]
# ///
"""Troca do arquivo do acervo e WAL: escrita concorrente, falha no meio e checkpoint."""

from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import datajud_store as store  # noqa: E402
from datajud_dados_teste import (  # noqa: E402
    _V2,
    _legado,
    hit,
    registrar,
    tabelas,
)


def _v2_em_troca(banco):
    with closing(sqlite3.connect(banco)) as con, con:
        for sql in _V2:
            con.execute(sql)
        con.execute(f"PRAGMA user_version = {store.EM_TROCA}")


def test_escrita_durante_a_troca_espera_o_arquivo_novo(tmp_path, monkeypatch):
    """Antigo ja copiado e carimbado: quem chega nao grava nele, espera o novo."""
    import threading
    import time

    banco = tmp_path / "acervo.sqlite"
    _v2_em_troca(banco)
    novo = tmp_path / "novo.sqlite"
    store._abrir(novo, novo=True).close()

    def trocar():
        time.sleep(0.5)
        banco.replace(tmp_path / "backup.sqlite")
        novo.replace(banco)

    threading.Thread(target=trocar).start()
    registrar(banco, hit())
    assert tabelas(banco)["consultas"] == 1, "a escrita foi para o arquivo novo"
    with closing(sqlite3.connect(tmp_path / "backup.sqlite")) as con:
        assert con.execute("SELECT COUNT(*) FROM consultas").fetchone()[0] == 0, "nada no antigo"
    with pytest.raises(store._ArquivoTrocado):
        store._abrir(tmp_path / "backup.sqlite")


def test_troca_que_morreu_no_meio_e_refeita(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "ESPERA_TROCA", 0.3)
    banco = tmp_path / "acervo.sqlite"
    _v2_em_troca(banco)
    registrar(banco, hit())
    dados = store.estatisticas(banco=banco)
    assert dados.versao == store.VERSAO and dados["consultas"] == 1
    assert list(tmp_path.glob("acervo-antes-v3-*.sqlite")), "o antigo ficou como backup"


def test_dois_processos_convertendo_o_mesmo_banco(tmp_path):
    """So um converte; o outro espera e abre o novo. Nunca some o acervo."""
    import subprocess

    banco = tmp_path / "v1.sqlite"
    _legado(banco, [("2026-10-01T00:00:00.000000+00:00", hit())])
    scripts = Path(store.__file__).parent
    codigo = (f"import sys; sys.path.insert(0, {str(scripts)!r}); import datajud_store as s; "
              f"from pathlib import Path; print(s.migrar(banco=Path({str(banco)!r})).origem)")
    processos = [subprocess.Popen([sys.executable, "-c", codigo], stdout=subprocess.PIPE, text=True)
                 for _ in range(2)]
    origens = sorted(p.communicate(timeout=120)[0].strip() for p in processos)
    assert all(p.returncode == 0 for p in processos)
    assert origens == ["legado", "nada"], "um converteu, o outro achou pronto"
    assert banco.exists() and store.estatisticas(banco=banco).versao == store.VERSAO
    assert len(list(tmp_path.glob("v1-antes-v3-*.sqlite"))) == 1
    assert not list(tmp_path.glob("*em-construcao*")), "nenhum temporario sobra"


def test_troca_que_falha_deixa_o_antigo_no_lugar(tmp_path, monkeypatch):
    """O caminho principal nunca fica vazio: falhou a troca, o antigo segue intacto."""
    banco = tmp_path / "v1.sqlite"
    _legado(banco, [("2026-10-01T00:00:00.000000+00:00", hit())])

    def recusa(*_a, **_k):
        raise PermissionError("aberto")

    monkeypatch.setattr(store.os, "replace", recusa)
    monkeypatch.setattr(store.relogio, "monotonic", iter(range(0, 10_000, 100)).__next__)
    with pytest.raises(RuntimeError, match="aberto noutro processo"):
        store.migrar(banco=banco)
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 0, "versao restaurada"
        assert con.execute("SELECT COUNT(*) FROM observacoes_documento").fetchone()[0] == 1
    assert sorted(x.name for x in tmp_path.iterdir() if x.suffix == ".sqlite") == ["v1.sqlite"]

    monkeypatch.undo()
    assert store.migrar(banco=banco).origem == "legado", "a proxima abertura converte"


def test_carimbo_acompanha_a_ordem_das_gravacoes(tmp_path):
    """Gravacoes concorrentes: id maior nunca tem horario anterior."""
    import threading

    banco = tmp_path / "a.sqlite"
    linhas = [threading.Thread(target=registrar, args=(banco, hit())) for _ in range(8)]
    for linha in linhas:
        linha.start()
    for linha in linhas:
        linha.join()
    with closing(sqlite3.connect(banco)) as con:
        horarios = [h for (h,) in con.execute("SELECT observado_em FROM consultas ORDER BY id")]
    assert len(horarios) == 8 and horarios == sorted(horarios)


def test_checkpoint_incompleto_desiste_com_tudo_intacto(tmp_path, monkeypatch):
    """Leitor segurando o WAL: nada se apaga, nada se troca, a versao volta."""
    banco = tmp_path / "v1.sqlite"
    _legado(banco, [("2026-10-01T00:00:00.000000+00:00", hit())])
    monkeypatch.setattr(store, "_consolidar_wal", lambda *_a, **_k: False)
    with pytest.raises(RuntimeError, match="se repete na proxima abertura"):
        store.migrar(banco=banco)
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM observacoes_documento").fetchone()[0] == 1
    assert sorted(x.name for x in tmp_path.iterdir() if x.suffix == ".sqlite") == ["v1.sqlite"]
    monkeypatch.undo()
    assert store.migrar(banco=banco).origem == "legado"


def test_consolidar_wal_detecta_leitor_segurando(tmp_path):
    banco = tmp_path / "w.sqlite"
    escritor = sqlite3.connect(banco, isolation_level=None)
    escritor.execute("PRAGMA journal_mode = WAL")
    escritor.execute("CREATE TABLE t (x)")
    escritor.execute("INSERT INTO t VALUES (1)")
    leitor = sqlite3.connect(banco, isolation_level=None)
    leitor.execute("BEGIN")
    leitor.execute("SELECT * FROM t").fetchall()
    escritor.execute("INSERT INTO t VALUES (2)")
    escritor.execute("PRAGMA busy_timeout = 50")
    assert store._consolidar_wal(escritor, espera=0.3) is False, "o leitor segura frames"
    leitor.execute("COMMIT")
    leitor.close()
    assert store._consolidar_wal(escritor, espera=1) is True
    escritor.close()
