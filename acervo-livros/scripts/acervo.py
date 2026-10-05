#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "cyclopts>=3.0",
#     "defusedxml>=0.7",
# ]
# ///
"""acervo.py — busca livros em acervos legais, baixa e converte para Markdown por capítulo.

Fontes (só domínio público ou licença livre):
    gutenberg   Project Gutenberg, via catálogo OPDS oficial (confere "Public domain")
    wikisource  Wikisource em qualquer idioma (pt por padrão), via API MediaWiki
    archive     Internet Archive, só itens marcados como domínio público

Arquivos locais (livros que o usuário já tem) entram direto no `converter`.

Conversão:
    .epub .html .htm .xhtml .txt .docx   stdlib (sem dependência externa)
    .pdf                                 pdftotext (poppler) ou `uvx markitdown`
    .mobi .azw .azw3 .fb2 .odt .rtf      ebook-convert (Calibre) → EPUB → Markdown

Saída do converter: pasta com `NN-titulo.md` por capítulo, `livro.md` inteiro
e `meta.json` (fonte, licença, origem, capítulos).

Dependências: cyclopts (CLI) e defusedxml (XML de origem externa). HTTP e conversões nativas usam a stdlib.

Modos:
    buscar    <termo>            lista resultados das fontes
    baixar    <fonte> <id>       baixa o melhor formato disponível
    converter <arquivo>          converte um arquivo local
    obter     <fonte> <id>       baixar + converter
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from cyclopts import App, Parameter
from defusedxml import ElementTree

USER_AGENT = "acervo-livros/0.1 (+https://github.com/franklinbaldo/skills)"
TIMEOUT_S = 90
Fonte = Literal["gutenberg", "wikisource", "archive"]
FONTES: tuple[Fonte, ...] = ("gutenberg", "wikisource", "archive")
LICENCA = {
    "gutenberg": "Domínio público nos EUA (Project Gutenberg); confira a lei do seu país",
    "wikisource": "Domínio público ou licença livre (política do Wikisource)",
    "archive": "Marcado como domínio público no Internet Archive",
}
RE_GUTENBERG_INICIO = re.compile(r"^[\W_]*START OF (THE|THIS) PROJECT GUTENBERG.*$", re.MULTILINE | re.IGNORECASE)
RE_GUTENBERG_FIM = re.compile(r"^[\W_]*END OF (THE|THIS) PROJECT GUTENBERG", re.MULTILINE | re.IGNORECASE)
EXTENSOES_NATIVAS = {".epub", ".html", ".htm", ".xhtml", ".txt", ".docx"}
EXTENSOES_CALIBRE = {".mobi", ".azw", ".azw3", ".fb2", ".odt", ".rtf", ".lit", ".pdb"}


class ErroAcervoError(RuntimeError):
    """Falha de rede ou de ferramenta externa; vira mensagem e exit 1 em main()."""


# ── Modelos ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Resultado:
    """Um item encontrado numa fonte."""

    fonte: Fonte
    id: str
    titulo: str
    autor: str
    ano: str
    detalhe: str

    def linha(self) -> str:
        """Formata o resultado em uma linha legível."""
        ano = f" ({self.ano})" if self.ano else ""
        return f"[{self.fonte}] {self.id}\n    {self.titulo} — {self.autor}{ano}  {self.detalhe}".rstrip()


@dataclass(frozen=True)
class Capitulo:
    """Um capítulo convertido."""

    titulo: str
    texto: str

    def palavras(self) -> int:
        """Conta as palavras do capítulo."""
        return len(self.texto.split())


@dataclass
class Meta:
    """Procedência do texto convertido."""

    titulo: str
    origem: str
    fonte: str = "local"
    licenca: str = "arquivo do usuário"
    capitulos: list[dict[str, object]] = field(default_factory=list)


# ── HTTP ─────────────────────────────────────────────────────────────────────


def _abrir(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 - URLs montadas pelo script
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310
            return r.read()
    except (urllib.error.URLError, TimeoutError) as e:
        msg = f"falha ao acessar {url}: {e}"
        raise ErroAcervoError(msg) from e


def _json(url: str) -> dict:
    return json.loads(_abrir(url))


# ── Busca ────────────────────────────────────────────────────────────────────


ATOM = "{http://www.w3.org/2005/Atom}"
RE_ID_GUTENBERG = re.compile(r"/ebooks/(\d+)\.opds$")


def buscar_gutenberg(termo: str, idioma: str | None, limite: int) -> list[Resultado]:
    """Busca no catálogo OPDS oficial do Project Gutenberg."""
    consulta = f"{termo} l.{idioma}" if idioma else termo
    feed = ElementTree.fromstring(
        _abrir("https://www.gutenberg.org/ebooks/search.opds/?" + urllib.parse.urlencode({"query": consulta}))
    )
    resultados = []
    for entrada in feed.iter(f"{ATOM}entry"):
        if not (m := RE_ID_GUTENBERG.search(entrada.findtext(f"{ATOM}id", ""))):
            continue
        titulo = entrada.findtext(f"{ATOM}title", "?")
        autor = entrada.findtext(f"{ATOM}content", "") or ""
        autor = "" if "downloads" in autor else autor
        resultados.append(Resultado("gutenberg", m[1], titulo, autor.strip(), "", ""))
        if len(resultados) >= limite:
            break
    return resultados


def _api_wikisource(idioma: str) -> str:
    return f"https://{idioma}.wikisource.org/w/api.php"


def buscar_wikisource(termo: str, idioma: str | None, limite: int) -> list[Resultado]:
    """Busca páginas principais (namespace 0) no Wikisource."""
    lang = idioma or "pt"
    params = {"action": "query", "list": "search", "srsearch": termo, "srnamespace": "0",
              "srlimit": str(limite), "format": "json", "formatversion": "2"}  # fmt: skip
    dados = _json(_api_wikisource(lang) + "?" + urllib.parse.urlencode(params))
    resultados = []
    for item in dados.get("query", {}).get("search", []):
        trecho = html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")))[:80]
        detalhe = f"{item.get('wordcount', 0)} palavras · {trecho}"
        resultados.append(Resultado("wikisource", f"{lang}:{item['title']}", item["title"], "", "", detalhe))
    return resultados


def buscar_archive(termo: str, idioma: str | None, limite: int) -> list[Resultado]:
    """Busca no Internet Archive só textos marcados como domínio público."""
    q = (f"({termo}) AND mediatype:texts AND "
         '(licenseurl:*publicdomain* OR possible-copyright-status:"NOT_IN_COPYRIGHT")')  # fmt: skip
    if idioma:
        q += f" AND language:({idioma})"
    params = [("q", q), ("rows", str(limite)), ("output", "json")]
    params += [("fl[]", f) for f in ("identifier", "title", "creator", "date", "language")]
    dados = _json("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params))
    resultados = []
    for doc in dados.get("response", {}).get("docs", []):
        autor = doc.get("creator", "?")
        autor = "; ".join(autor) if isinstance(autor, list) else autor
        ano = str(doc.get("date", ""))[:4]
        resultados.append(Resultado("archive", doc["identifier"], str(doc.get("title", "?")), autor, ano, ""))
    return resultados


BUSCADORES = {"gutenberg": buscar_gutenberg, "wikisource": buscar_wikisource, "archive": buscar_archive}


# ── Download ─────────────────────────────────────────────────────────────────


def _slug(texto: str, limite: int = 60) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:limite] or "livro"


def baixar_gutenberg(ident: str, pasta: Path) -> Path:
    """Confere a licença no OPDS do livro; prefere EPUB, depois HTML, depois texto UTF-8."""
    numero = int(ident)
    feed = ElementTree.fromstring(_abrir(f"https://www.gutenberg.org/ebooks/{numero}.opds"))
    direitos = feed.findtext(f".//{ATOM}rights", "") or ""
    if "public domain" not in direitos.lower():
        msg = f"Gutenberg {numero}: direitos '{direitos or '?'}'; só baixo domínio público"
        raise ErroAcervoError(msg)
    titulo = feed.findtext(f".//{ATOM}entry/{ATOM}title", "") or f"gutenberg-{numero}"
    base = "https://www.gutenberg.org"
    candidatos = (
        (f"{base}/ebooks/{numero}.epub3.images", ".epub"),
        (f"{base}/ebooks/{numero}.epub.noimages", ".epub"),
        (f"{base}/ebooks/{numero}.html.images", ".html"),
        (f"{base}/cache/epub/{numero}/pg{numero}.txt", ".txt"),
    )
    for url, ext in candidatos:
        try:
            dados = _abrir(url)
        except ErroAcervoError:
            continue
        destino = pasta / f"{_slug(titulo)}{ext}"
        destino.write_bytes(dados)
        return destino
    msg = f"Gutenberg {numero}: nenhum formato EPUB/HTML/TXT"
    raise ErroAcervoError(msg)


def baixar_wikisource(ident: str, pasta: Path) -> Path:
    """Baixa a página e as subpáginas (capítulos) como um único HTML."""
    lang, _, titulo = ident.partition(":") if ":" in ident[:4] else ("pt", "", ident)
    api = _api_wikisource(lang)

    def parse(pagina: str) -> dict:
        params = {"action": "parse", "page": pagina, "prop": "text|links", "redirects": "1",
                  "format": "json", "formatversion": "2", "disableeditsection": "1"}  # fmt: skip
        dados = _json(api + "?" + urllib.parse.urlencode(params))
        if "error" in dados:
            msg = f"Wikisource {lang}:{pagina}: {dados['error'].get('info')}"
            raise ErroAcervoError(msg)
        return dados["parse"]

    principal = parse(titulo)
    nome = principal["title"]
    subpaginas = [lk["title"] for lk in principal.get("links", [])
                  if lk.get("exists") and lk["title"].startswith(nome + "/")]  # fmt: skip
    partes = [f"<h1>{html.escape(nome)}</h1>", principal["text"]]
    for sub in dict.fromkeys(subpaginas):
        partes += [f"<h1>{html.escape(sub.removeprefix(nome + '/'))}</h1>", parse(sub)["text"]]
    destino = pasta / f"{_slug(nome)}.html"
    destino.write_text("\n".join(partes), encoding="utf-8")
    return destino


def baixar_archive(ident: str, pasta: Path) -> Path:
    """Prefere EPUB aberto, depois texto OCR, depois PDF; recusa itens sem marca de domínio público."""
    meta = _json(f"https://archive.org/metadata/{urllib.parse.quote(ident)}")
    m = meta.get("metadata", {})
    livre = "publicdomain" in str(m.get("licenseurl", "")) or m.get("possible-copyright-status") == "NOT_IN_COPYRIGHT"
    if not livre:
        msg = f"archive {ident} não está marcado como domínio público; não baixo"
        raise ErroAcervoError(msg)
    nomes = [f["name"] for f in meta.get("files", [])]
    escolha = (
        next((n for n in nomes if n.endswith(".epub") and not n.endswith("_lcp.epub")), None)
        or next((n for n in nomes if n.endswith("_djvu.txt")), None)
        or next((n for n in nomes if n.endswith(".pdf")), None)
    )
    if escolha is None:
        msg = f"archive {ident}: sem EPUB, texto ou PDF"
        raise ErroAcervoError(msg)
    url = f"https://archive.org/download/{urllib.parse.quote(ident)}/{urllib.parse.quote(escolha)}"
    ext = ".txt" if escolha.endswith("_djvu.txt") else PurePosixPath(escolha).suffix
    destino = pasta / f"{_slug(str(m.get('title', ident)))}{ext}"
    destino.write_bytes(_abrir(url))
    return destino


BAIXADORES = {"gutenberg": baixar_gutenberg, "wikisource": baixar_wikisource, "archive": baixar_archive}


# ── HTML → Markdown ──────────────────────────────────────────────────────────

CLASSES_FORA = ("ws-noexport", "noprint", "mw-editsection", "reference", "navbox", "headertemplate",
                "metadata", "mw-references", "ws-header", "ws-summary")  # fmt: skip
ENFASE, FORTE = "\x01", "\x02"  # marcadores provisórios; ênfase vazia some antes de virar asterisco
TAGS_FORA = {"script", "style", "nav", "head", "sup", "table"}
TAGS_VAZIAS = {"br", "hr", "img", "meta", "link", "input", "wbr", "col", "area", "base", "source"}


class _HtmlParaMd(HTMLParser):
    """Converte HTML de livro em Markdown simples: títulos, parágrafos, ênfase."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.saida: list[str] = []
        self.pilha_fora: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in TAGS_VAZIAS:
            if tag == "br" and not self.pilha_fora:
                self.saida.append("  \n")
            return
        classes = dict(attrs).get("class") or ""
        if self.pilha_fora or tag in TAGS_FORA or any(c in classes for c in CLASSES_FORA):
            self.pilha_fora.append(tag)
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.saida.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in {"p", "div", "blockquote", "li", "section"}:
            self.saida.append("\n\n" + ("> " if tag == "blockquote" else "- " if tag == "li" else ""))
        elif tag in {"em", "i"}:
            self.saida.append(ENFASE)
        elif tag in {"strong", "b"}:
            self.saida.append(FORTE)

    def handle_endtag(self, tag: str) -> None:
        if self.pilha_fora:
            if self.pilha_fora[-1] == tag:
                self.pilha_fora.pop()
            return
        if tag in {"em", "i"}:
            self.saida.append(ENFASE)
        elif tag in {"strong", "b"}:
            self.saida.append(FORTE)
        elif re.fullmatch(r"h[1-6]|p|div|blockquote|li|section", tag):
            self.saida.append("\n\n")

    def handle_data(self, data: str) -> None:
        if not self.pilha_fora:
            self.saida.append(re.sub(r"\s+", " ", data))

    def markdown(self) -> str:
        texto = "".join(self.saida)
        texto = re.sub(rf"{ENFASE}\s*{ENFASE}|{FORTE}\s*{FORTE}", " ", texto)  # ênfase vazia
        texto = texto.replace(FORTE, "**").replace(ENFASE, "*")
        texto = re.sub(r"[ \t]+\n", "\n", texto)
        texto = re.sub(r"\n[ \t]+", "\n", texto)
        texto = re.sub(r"^(#{1,6}|>|-)\s+", r"\1 ", texto, flags=re.MULTILINE)
        return re.sub(r"\n{3,}", "\n\n", texto).strip()


def html_para_md(conteudo: str) -> str:
    """Converta uma página HTML em Markdown."""
    parser = _HtmlParaMd()
    parser.feed(conteudo)
    parser.close()
    return parser.markdown()


# ── Conversores por formato ──────────────────────────────────────────────────


def _secoes_substanciais(md: str, nivel: str, minimo: int = 300) -> int:
    """Quantas seções com pelo menos `minimo` palavras o corte neste nível produz."""
    pedacos = re.split(rf"^(?={re.escape(nivel)} )", md, flags=re.MULTILINE)
    return sum(1 for p in pedacos if p.startswith(nivel + " ") and len(p.split()) >= minimo)


def _sem_moldura_gutenberg(md: str) -> str:
    """Remove o cabeçalho e a licença que o Project Gutenberg põe em todo livro."""
    if inicio := RE_GUTENBERG_INICIO.search(md):
        md = md[inicio.end() :]
    if fim := RE_GUTENBERG_FIM.search(md):
        md = md[: fim.start()]
    return md.strip()


def _dividir_em_capitulos(md: str, titulo_padrao: str) -> list[Capitulo]:
    """Corta no nível de título mais alto que rende ao menos três seções de 300+ palavras."""
    nivel = next((h for h in ("#" * n for n in range(1, 7)) if _secoes_substanciais(md, h) >= 3), None)  # noqa: PLR2004
    if nivel is None:
        return [Capitulo(titulo_padrao, md)]
    pedacos = re.split(rf"^(?={re.escape(nivel)} )", md, flags=re.MULTILINE)
    capitulos = []
    for i, pedaco in enumerate(p.strip() for p in pedacos):
        if not pedaco:
            continue
        primeira = pedaco.splitlines()[0]
        titulo = primeira.lstrip("# ").strip() if primeira.startswith(nivel + " ") else "Abertura"
        if i == 0 and len(pedaco.split()) < 40 and capitulos == []:  # noqa: PLR2004 - folha de rosto curta
            continue
        capitulos.append(Capitulo(titulo or f"Parte {i}", pedaco))
    return capitulos or [Capitulo(titulo_padrao, md)]


def converter_epub(arquivo: Path) -> tuple[str, list[Capitulo]]:
    """Lê a ordem de leitura (spine) do OPF e divide por títulos; sem títulos úteis, cada documento é um capítulo."""
    ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container",
          "o": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}  # fmt: skip
    with zipfile.ZipFile(arquivo) as z:
        opf_path = ElementTree.fromstring(z.read("META-INF/container.xml")).find(".//c:rootfile", ns).get("full-path")
        opf = ElementTree.fromstring(z.read(opf_path))
        base = PurePosixPath(opf_path).parent
        titulo = (opf.findtext(".//dc:title", default="", namespaces=ns) or arquivo.stem).strip()
        itens = {i.get("id"): i.get("href") for i in opf.iterfind(".//o:manifest/o:item", ns)}
        capitulos = []
        for ref in opf.iterfind(".//o:spine/o:itemref", ns):
            href = itens.get(ref.get("idref"))
            if not href or ref.get("linear") == "no":
                continue
            caminho = str(base / urllib.parse.unquote(href)).lstrip("./")
            md = html_para_md(z.read(caminho).decode("utf-8", errors="replace"))
            if len(md.split()) < 15:  # noqa: PLR2004 - capa, sumário vazio, colofão
                continue
            cabecalho = re.match(r"#{1,6} (.+)", md)
            capitulos.append(Capitulo(cabecalho[1].strip() if cabecalho else f"Parte {len(capitulos) + 1}", md))
    por_titulo = _dividir_em_capitulos(_sem_moldura_gutenberg("\n\n".join(c.texto for c in capitulos)), titulo)
    return titulo, (por_titulo if len(por_titulo) > 1 else capitulos)


def converter_html(arquivo: Path) -> tuple[str, list[Capitulo]]:
    """HTML único (Gutenberg, Wikisource) dividido pelos títulos."""
    md = _sem_moldura_gutenberg(html_para_md(arquivo.read_text(encoding="utf-8", errors="replace")))
    titulo = (re.search(r"^# (.+)$", md, flags=re.MULTILINE) or [None, arquivo.stem])[1]
    return titulo, _dividir_em_capitulos(md, titulo)


RE_TITULO_TXT = re.compile(r"^(CAP[IÍ]TULO|CHAPTER|LIVRO|PARTE|BOOK|PART)\b.*$|^[IVXLC]+\.?$", re.MULTILINE)


def converter_txt(arquivo: Path) -> tuple[str, list[Capitulo]]:
    """Texto puro: tira o cabeçalho do Gutenberg e marca CAPÍTULO/CHAPTER como título."""
    texto = arquivo.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    texto = _sem_moldura_gutenberg(texto)
    md = RE_TITULO_TXT.sub(lambda m: f"## {m[0].strip()}", texto)
    md = re.sub(r"(?<!\n)\n(?!\n|## )", " ", md)  # desfaz quebra de linha dura dentro do parágrafo
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return arquivo.stem, _dividir_em_capitulos(md, arquivo.stem)


def converter_docx(arquivo: Path) -> tuple[str, list[Capitulo]]:
    """DOCX via XML: estilos Heading/Título viram títulos."""
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(arquivo) as z:
        doc = ElementTree.fromstring(z.read("word/document.xml"))
    linhas = []
    for p in doc.iter(f"{w}p"):
        texto = "".join(t.text or "" for t in p.iter(f"{w}t")).strip()
        if not texto:
            continue
        estilo = p.find(f"{w}pPr/{w}pStyle")
        nome = (estilo.get(f"{w}val") if estilo is not None else "") or ""
        nivel = re.search(r"(?:heading|ttulo|titulo|title)\s*(\d)?", nome, flags=re.IGNORECASE)
        prefixo = "#" * min(int(nivel[1] or 1), 3) + " " if nivel else ""
        linhas.append(prefixo + texto)
    md = "\n\n".join(linhas)
    return arquivo.stem, _dividir_em_capitulos(md, arquivo.stem)


def converter_pdf(arquivo: Path) -> tuple[str, list[Capitulo]]:
    """Extraia o PDF com pdftotext se houver; senão markitdown via uvx. PDF escaneado sem texto pede OCR."""
    if shutil.which("pdftotext"):
        proc = subprocess.run(["pdftotext", "-enc", "UTF-8", str(arquivo), "-"],  # noqa: S607
                              capture_output=True, text=True, check=False)  # fmt: skip
        texto = proc.stdout
    elif shutil.which("uvx"):
        proc = subprocess.run(["uvx", "--from", "markitdown[pdf]", "markitdown", str(arquivo)],  # noqa: S607
                              capture_output=True, text=True, check=False)  # fmt: skip
        texto = proc.stdout
    else:
        msg = "PDF exige pdftotext (poppler-utils) ou uv (para markitdown)"
        raise ErroAcervoError(msg)
    if len(texto.split()) < 50:  # noqa: PLR2004
        msg = "o PDF não tem camada de texto; rode OCR antes (ocrmypdf ou a skill paddleocr)"
        raise ErroAcervoError(msg)
    with tempfile.TemporaryDirectory() as tmp:
        txt = Path(tmp) / f"{arquivo.stem}.txt"
        txt.write_text(texto.replace("\f", "\n\n"), encoding="utf-8")
        return converter_txt(txt)


def converter_calibre(arquivo: Path) -> tuple[str, list[Capitulo]]:
    """MOBI/AZW3/FB2/ODT/RTF: Calibre converte para EPUB e seguimos pelo spine."""
    if not shutil.which("ebook-convert"):
        msg = f"{arquivo.suffix} exige o Calibre (ebook-convert) instalado"
        raise ErroAcervoError(msg)
    with tempfile.TemporaryDirectory() as tmp:
        epub = Path(tmp) / f"{arquivo.stem}.epub"
        proc = subprocess.run(["ebook-convert", str(arquivo), str(epub)],  # noqa: S607
                              capture_output=True, text=True, check=False)  # fmt: skip
        if proc.returncode != 0:
            msg = f"ebook-convert falhou: {proc.stderr[-300:]}"
            raise ErroAcervoError(msg)
        return converter_epub(epub)


def converter_arquivo(arquivo: Path) -> tuple[str, list[Capitulo]]:
    """Escolhe o conversor pela extensão."""
    ext = arquivo.suffix.lower()
    if ext == ".epub":
        return converter_epub(arquivo)
    if ext in {".html", ".htm", ".xhtml"}:
        return converter_html(arquivo)
    if ext == ".txt":
        return converter_txt(arquivo)
    if ext == ".docx":
        return converter_docx(arquivo)
    if ext == ".pdf":
        return converter_pdf(arquivo)
    if ext in EXTENSOES_CALIBRE:
        return converter_calibre(arquivo)
    msg = f"formato não suportado: {ext}"
    raise ErroAcervoError(msg)


def gravar(titulo: str, capitulos: list[Capitulo], saida: Path, meta: Meta) -> Path:
    """Grava capítulos, livro.md e meta.json."""
    saida.mkdir(parents=True, exist_ok=True)
    for antigo in saida.glob("[0-9][0-9]-*.md"):
        antigo.unlink()
    meta.titulo = titulo
    meta.capitulos = []
    for i, cap in enumerate(capitulos, 1):
        nome = f"{i:02d}-{_slug(cap.titulo, 50)}.md"
        (saida / nome).write_text(cap.texto + "\n", encoding="utf-8")
        meta.capitulos.append({"arquivo": nome, "titulo": cap.titulo, "palavras": cap.palavras()})
    livro = f"# {titulo}\n\n" + "\n\n".join(c.texto for c in capitulos) + "\n"
    (saida / "livro.md").write_text(livro, encoding="utf-8")
    (saida / "meta.json").write_text(json.dumps(asdict(meta), ensure_ascii=False, indent=2), encoding="utf-8")
    return saida


# ── CLI ──────────────────────────────────────────────────────────────────────

app = App(
    name="acervo",
    help="Busca livros em acervos legais (Gutenberg, Wikisource, Internet Archive) e converte para Markdown.",
    help_format="plaintext",
)


@app.command
def buscar(
    termo: str,
    *,
    fonte: Annotated[Literal["todas", "gutenberg", "wikisource", "archive"], Parameter(alias="-f")] = "todas",
    idioma: Annotated[str | None, Parameter(alias="-i")] = None,
    limite: Annotated[int, Parameter(alias="-n")] = 8,
    json_: Annotated[bool, Parameter(name="--json", negative="")] = False,
) -> int:
    """Liste livros que casam com o termo (título ou autor).

    Parameters
    ----------
    termo
        Título, autor ou ambos: "machado espelho", "poe tell-tale heart".
    fonte
        Uma fonte só, ou todas (padrão).
    idioma
        Código de idioma: pt, en, es... No Wikisource escolhe o subdomínio (padrão pt).
    limite
        Resultados por fonte.
    json_
        Emite JSON em vez da lista legível.

    """
    fontes = FONTES if fonte == "todas" else (fonte,)
    resultados: list[Resultado] = []
    falhas: list[str] = []
    for f in fontes:
        try:
            resultados += BUSCADORES[f](termo, idioma, limite)
        except ErroAcervoError as e:
            falhas.append(f"{f}: {e}")
    if json_:
        print(json.dumps({"resultados": [asdict(r) for r in resultados], "falhas": falhas}, ensure_ascii=False))
    else:
        for r in resultados:
            print(r.linha())
        for falha in falhas:
            print(f"! {falha}", file=sys.stderr)
        if not resultados:
            print("nenhum resultado")
    return 0 if resultados or not falhas else 1


@app.command
def baixar(fonte: Fonte, ident: str, *, pasta: Path = Path()) -> int:
    """Baixe o melhor formato disponível de um item.

    Parameters
    ----------
    fonte
        gutenberg, wikisource ou archive.
    ident
        O id mostrado pelo `buscar`: número no Gutenberg, "pt:Título" no Wikisource, identifier no archive.
    pasta
        Onde salvar o arquivo.

    """
    pasta.mkdir(parents=True, exist_ok=True)
    print(BAIXADORES[fonte](ident, pasta))
    return 0


@app.command
def converter(arquivo: Path, *, saida: Path | None = None) -> int:
    """Converta um arquivo local para Markdown por capítulo.

    Parameters
    ----------
    arquivo
        EPUB, HTML, TXT, DOCX, PDF (com texto) ou MOBI/AZW3/FB2/ODT/RTF (com Calibre).
    saida
        Pasta de saída. Padrão: pasta com o nome do arquivo, ao lado dele.

    """
    if not arquivo.is_file():
        print(f"arquivo não encontrado: {arquivo}", file=sys.stderr)
        return 1
    titulo, capitulos = converter_arquivo(arquivo)
    pasta = gravar(titulo, capitulos, saida or arquivo.with_suffix(""), Meta(titulo, str(arquivo)))
    _resumo(pasta, capitulos)
    return 0


@app.command
def obter(fonte: Fonte, ident: str, *, saida: Path | None = None) -> int:
    """Baixe e converta: o caminho curto de busca até o Markdown.

    Parameters
    ----------
    fonte
        gutenberg, wikisource ou archive.
    ident
        O id mostrado pelo `buscar`.
    saida
        Pasta de saída. Padrão: ./<titulo>/

    """
    with tempfile.TemporaryDirectory() as tmp:
        arquivo = BAIXADORES[fonte](ident, Path(tmp))
        titulo, capitulos = converter_arquivo(arquivo)
        pasta = saida or Path(_slug(titulo))
        meta = Meta(titulo, f"{fonte}:{ident}", fonte=fonte, licenca=LICENCA[fonte])
        gravar(titulo, capitulos, pasta, meta)
    _resumo(pasta, capitulos)
    return 0


def _resumo(pasta: Path, capitulos: list[Capitulo]) -> None:
    total = sum(c.palavras() for c in capitulos)
    print(f"{pasta}/ — {len(capitulos)} capítulo(s), {total} palavras (~{total / 135:.0f} min lidos em voz alta)")
    for i, c in enumerate(capitulos[:12], 1):
        print(f"  {i:02d}. {c.titulo[:60]} ({c.palavras()} palavras)")
    if len(capitulos) > 12:  # noqa: PLR2004
        print(f"  … mais {len(capitulos) - 12}")


def main(tokens: list[str] | None = None) -> int:
    """Ponto de entrada; erros de rede/ferramenta viram mensagem e exit 1."""
    try:
        return app(tokens) or 0
    except ErroAcervoError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
