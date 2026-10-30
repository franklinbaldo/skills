# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic>=2.6",
# ]
# ///
"""Consulta de processos por número: um (`processo`) ou muitos (`lote`), com cópia crua."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import datajud_api as api
import datajud_store as store
from datajud_api import FalhaHTTPTransitoria
from datajud_cnj import NumeroCNJ, cnj, familia_do_cnj, so_digitos, tribunal_do_cnj
from datajud_formatos import assuntos_str, classe_str, fmt_data_ajuiz, fmt_data_iso, grau_label, orgao_str
from datajud_modelos import RequisicaoBusca
from datajud_saidas import (
    ConsultaLote,
    DocumentoProcesso,
    FalhaIndice,
    FalhaLote,
    PresencaForaDaOrigem,
    ProcessoConsultado,
    Registro,
    ResumoLote,
    SaidaProcesso,
    _imprimir,
)
from pydantic import TypeAdapter, ValidationError


def consultar(entrada: ConsultaLote) -> dict[str, ProcessoConsultado]:
    """Procura cada numero em todos os indices da sua familia (ou so na origem).

    Uma consulta `terms` por indice para ate LOTE numeros, em paralelo. Devolve
    um `ProcessoConsultado` por numero (chave: os 20 digitos). Indice que falha
    fica em `falhas`, e o processo nao deve ser tratado como ausente nele.
    """
    alvo: dict[str, ProcessoConsultado] = {}
    for n in entrada.numeros:
        indices = [tribunal_do_cnj(n)] if entrada.so_origem else familia_do_cnj(n)
        alvo[so_digitos(n)] = ProcessoConsultado(
            processo=n, origem=tribunal_do_cnj(n), consultados=[i for i in indices if i])
    por_indice: dict[str, list[str]] = {}
    for d, item in alvo.items():
        for i in item.consultados:
            por_indice.setdefault(i, []).append(d)
    tarefas = [(i, ds[k:k + LOTE]) for i, ds in por_indice.items() for k in range(0, len(ds), LOTE)]

    def rodar(tarefa):
        i, ds = tarefa

        def consultar_parte(numeros, subdividir=True):
            try:
                d = api.search(RequisicaoBusca(
                    size=len(numeros) * 10,
                    query={"terms": {"numeroProcesso": numeros}},
                ).bruto(), tribunal=i)
                hits = d.get("hits", {}).get("hits", [])
                total = d.get("hits", {}).get("total", {}).get("value", 0)
                if total > len(hits):
                    raise RuntimeError(f"resposta truncada em {i}: {len(hits)} de {total}")
                return [Registro.model_validate(h) for h in hits], []
            except (RuntimeError, ValidationError) as e:
                # Uma falha em 100 numeros nao deve invalidar os 100:
                # tente partes menores, mas sem recursao ilimitada.
                if subdividir and len(numeros) > 25 and isinstance(e, FalhaHTTPTransitoria):
                    registros, falhas = [], []
                    for k in range(0, len(numeros), 25):
                        encontrados, erros = consultar_parte(numeros[k:k + 25], False)
                        registros.extend(encontrados)
                        falhas.extend(erros)
                    return registros, falhas
                return [], [(n, str(e)[:200]) for n in numeros]

        return consultar_parte(ds)

    with ThreadPoolExecutor(entrada.trabalhadores) as pool:
        futuros = {pool.submit(rodar, t): t for t in tarefas}
        for futuro in as_completed(futuros):
            i, ds = futuros[futuro]
            try:
                registros, falhas = futuro.result()
                for registro in registros:
                    if registro.numero in alvo:
                        alvo[registro.numero].registros.append(registro)
                for num, erro in falhas:
                    alvo[num].falhas.append(FalhaIndice(indice=i, erro=erro))
            except (RuntimeError, ValidationError) as e:
                for num in ds:
                    alvo[num].falhas.append(FalhaIndice(indice=i, erro=str(e)[:200]))
    for item in alvo.values():
        item.registros.sort(key=lambda r: (r.tribunal, r.grau or ""))
    return alvo


def consultar_um(numero: str, *, tribunal: str | None = None,
                 so_origem: bool = False) -> ProcessoConsultado:
    """Um processo: so no indice pedido, ou na familia do numero (o padrao)."""
    if not tribunal:
        return consultar(ConsultaLote(numeros=[numero], so_origem=so_origem))[so_digitos(numero)]
    d = api.search(RequisicaoBusca(size=50, query={"match": {"numeroProcesso": so_digitos(numero)}},
                               sort=[{"grau.keyword": "asc"}]).bruto(), tribunal=tribunal)
    registros = [Registro.model_validate(h) for h in d.get("hits", {}).get("hits", [])]
    for r in registros:
        r.indice_bruto = r.indice_bruto or f"api_publica_{tribunal}"
    return ProcessoConsultado(processo=numero, origem=tribunal_do_cnj(numero),
                              consultados=[tribunal], registros=registros)


def cmd_processo(numero: str, tribunal: str | None, movimentos: bool, as_json: bool,
                 so_origem: bool = False):
    nr = so_digitos(numero)
    item = consultar_um(numero, tribunal=tribunal, so_origem=so_origem)
    onde = ", ".join(i.upper() for i in item.consultados) or "nenhum indice (numero sem tribunal deduzivel)"
    for f in item.falhas:
        print(f"Aviso: {f.indice.upper()} nao respondeu ({f.erro}).", file=sys.stderr)
    if not item.encontrado:
        if item.falhas or not item.consultados:
            print(f"Consulta incompleta de {cnj(nr)} ({onde}): ausencia nao confirmada.",
                  file=sys.stderr)
        else:
            print(f"Nenhum processo {cnj(nr)} encontrado em {onde}.", file=sys.stderr)
        return 1

    if as_json:
        documentos = []
        for r in item.registros:
            src = r.fonte
            documentos.append(DocumentoProcesso.model_validate({
                "tribunal": r.tribunal,
                "grau": src.get("grau"),
                "classe": src.get("classe"),
                "assuntos": src.get("assuntos"),
                "orgaoJulgador": src.get("orgaoJulgador"),
                "dataAjuizamento": src.get("dataAjuizamento"),
                "ultimaAtualizacao": src.get("dataHoraUltimaAtualizacao"),
                "movimentos": src.get("movimentos") if movimentos else None,
            }))
        _imprimir(SaidaProcesso(processo=item.processo, consultados=item.consultados,
                                falhas=item.falhas, documentos=documentos))
        return 0

    print(f"Processo {item.processo} — {len(item.registros)} registro(s) em "
          f"{', '.join(t.upper() for t in item.tribunais)} (consultados: {onde})")
    print("=" * 92)
    for r in item.registros:
        src = r.fonte
        print(f"\n### {r.tribunal.upper()} · {grau_label(src.get('grau'))} — {classe_str(src)}")
        print(f"    assuntos: {assuntos_str(src)}")
        print(f"    orgao:    {orgao_str(src)}")
        print(f"    sistema:  {(src.get('sistema') or {}).get('nome','—')} | "
              f"formato: {(src.get('formato') or {}).get('nome','—')} | "
              f"sigilo: {src.get('nivelSigilo','—')}")
        print(f"    ajuizado: {fmt_data_ajuiz(src.get('dataAjuizamento'))} | "
              f"atualizado: {fmt_data_iso(src.get('dataHoraUltimaAtualizacao'))}")
        movs = src.get("movimentos") or []
        if movimentos and movs:
            movs_ord = sorted(movs, key=lambda m: m.get("dataHora", ""))
            print(f"    --- {len(movs_ord)} movimento(s) ---")
            for m in movs_ord:
                compl = ""
                ct = m.get("complementosTabelados") or []
                if ct:
                    vals = "; ".join(f"{c.get('descricao','')}={c.get('nome','')}"
                                     for c in ct if c.get("nome"))
                    if vals:
                        compl = f"  [{vals}]"
                print(f"      {fmt_data_iso(m.get('dataHora'))}  "
                      f"({m.get('codigo')}) {m.get('nome')}{compl}")
        elif movs:
            print(f"    movimentos: {len(movs)} (use --movimentos para listar)")
    return 0


# ----------------------------------------------------------------------------
# Modo: buscar
# ----------------------------------------------------------------------------


LOTE = 100


def _arquivo_lote(saida: Path, numero: str) -> Path:
    return saida / (tribunal_do_cnj(numero) or "sem-tribunal") / f"{so_digitos(numero)}.json"


def ler_processo(saida: Path, numero: str) -> ProcessoConsultado | None:
    """Le o legado de JSON individual, se houver (SQLite e a fonte primaria)."""
    arquivo = _arquivo_lote(saida, numero)
    if not arquivo.exists():
        return None
    try:
        return ProcessoConsultado.model_validate_json(arquivo.read_text(encoding="utf-8"))
    except ValidationError:
        return None  # formato antigo ou corrompido: consulta de novo


def _ja_baixado(saida: Path, numero: str, so_origem: bool) -> bool:
    """Em disco e consultado em todos os indices pedidos agora."""
    gravado = ler_processo(saida, numero)
    pedidos = [tribunal_do_cnj(numero)] if so_origem else familia_do_cnj(numero)
    return gravado is not None and set(pedidos) <= set(gravado.consultados)


_CNJ = TypeAdapter(NumeroCNJ)


def cmd_lote(arquivo: Path, saida: Path | None, trabalhadores: int,
             so_origem: bool, as_json: bool):
    """SQLite e o padrao: cada execucao observa novamente a fonte.

    --saida preserva a exportacao JSON antiga, com a semantica antiga de pular
    JSONs ja completos. Em ambos os casos, cada chamada real a api.search() registra
    todas as respostas no SQLite append-only.
    """
    numeros, invalidos = [], []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        try:
            numeros.append(_CNJ.validate_python(linha.strip()))
        except ValidationError:
            invalidos.append(linha.strip())
    numeros = list(dict.fromkeys(numeros))
    sem_tribunal = [n for n in numeros if tribunal_do_cnj(n) is None]
    pendentes = [
        n for n in numeros
        if tribunal_do_cnj(n) and (
            saida is None or not _ja_baixado(saida, n, so_origem)
        )
    ]
    print(f"{len(numeros)} processos; {len(pendentes)} a consultar"
          f"{' (so na origem)' if so_origem else ' (familia: origem + outros + superiores)'}",
          file=sys.stderr)
    resultado = consultar(ConsultaLote(
        numeros=pendentes, so_origem=so_origem, trabalhadores=trabalhadores
    ))
    destino_descr = str(saida or store.caminho_banco())
    resumo = ResumoLote(
        processos=len(numeros), em_disco=0, encontrados=0,
        sem_tribunal=sem_tribunal, invalidos=invalidos, saida=destino_descr,
    )
    validos = {}
    for item in resultado.values():
        if item.falhas:
            resumo.falhas.append(FalhaLote(
                processo=item.processo, indices=[f.indice for f in item.falhas]
            ))
            continue
        validos[so_digitos(item.processo)] = item
        if saida is not None:
            # Compatibilidade: exporta JSON apenas quando solicitado; cada
            # observacao vinda da rede ja foi armazenada no banco imutavel.
            destino = _arquivo_lote(saida, item.processo)
            destino.parent.mkdir(parents=True, exist_ok=True)
            temporario = destino.with_suffix(".json.tmp")
            temporario.write_text(item.para_disco(), encoding="utf-8")
            temporario.replace(destino)
    for n in numeros:
        if tribunal_do_cnj(n) is None:
            continue
        gravado = (ler_processo(saida, n) if saida is not None
                   else validos.get(so_digitos(n)))
        if gravado is None:
            continue
        resumo.em_disco += 1
        resumo.encontrados += gravado.encontrado
        outros = [t for t in gravado.tribunais if t != gravado.origem]
        if outros:
            resumo.tambem_em_outro_tribunal.append(
                PresencaForaDaOrigem(processo=gravado.processo, tambem_em=outros)
            )
    if as_json:
        print(resumo.model_dump_json(indent=2))
    else:
        print(f"{resumo.processos} processos; {resumo.em_disco} observados e "
              f"{resumo.encontrados} encontrados no DataJud, em {destino_descr}")
        if resumo.tambem_em_outro_tribunal:
            print(f"  {len(resumo.tambem_em_outro_tribunal)} tambem em outro tribunal")
        if resumo.sem_tribunal:
            print(f"  {len(resumo.sem_tribunal)} sem indice deduzivel")
        if resumo.invalidos:
            print(f"  {len(resumo.invalidos)} linhas invalidas")
        if resumo.falhas:
            print(f"  {len(resumo.falhas)} processos com indice sem resposta — "
                  "nao interpretados como ausentes")
    return 1 if resumo.falhas else 0


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
