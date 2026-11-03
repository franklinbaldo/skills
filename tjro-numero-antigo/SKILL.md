---
name: tjro-numero-antigo
description: >-
  Converte o número antigo de processo do TJRO (FFF.AAAA.SSSSSS-D, anterior ao
  CNJ) para o formato de 14 dígitos do APPG e para o número CNJ, e procura o
  processo no DataJud, no DESARQ e no APPG. Use quando uma matrícula, certidão,
  ofício ou peça antiga citar processo do TJRO no formato antigo
  ("006.01.000138-2", "001.1993.006868-9", "00119950175057"), quando a busca
  pelo número der "inválido" ou "não localizado", ou antes de pedir
  desarquivamento. Não use para número já no padrão CNJ: para esse, use
  datajud.
compatibility: >-
  Requires Python 3 and uv (the script declares its dependencies inline, PEP
  723). The DataJud lookup needs outbound HTTPS to the public CNJ API. The APPG
  helper runs inside a browser tab through Claude in Chrome, and a human must
  solve the reCAPTCHA for every search.
---

# Número antigo de processo do TJRO

Antes da numeração única do CNJ (Res. 65/2008), o TJRO numerava os processos
de 1º grau como `FFF.AAAA.SSSSSS-D`:

| Parte    | O quê                                | Exemplo                   |
| -------- | ------------------------------------ | ------------------------- |
| `FFF`    | foro (comarca), 3 dígitos            | `006` = Presidente Médici |
| `AAAA`   | ano de entrada                       | `2001`                    |
| `SSSSSS` | sequencial no foro e no ano          | `000138`                  |
| `D`      | dígito verificador do sistema antigo | `2`                       |

Esse número ainda aparece em averbação de matrícula, mandado de penhora,
certidão e ofício antigo. Os sistemas de hoje o aceitam em formatos diferentes,
e com ele mal grafado a busca falha sem dizer por quê.

## Como as pessoas escrevem (e o que o script aceita)

- **Ano com 2 dígitos:** `006.01.000138-2`. Era comum em mandado e averbação.
  O script completa: até `30` vira `20xx`, acima vira `19xx`
  (`001.97.003786-5` → `001.1997.003786-5`).
- **Sequencial sem os zeros à esquerda:** `006.2005.1624-0` → `001624`.
- **Sem o dígito verificador:** `006.2001.000138`. O script gera os 10
  candidatos (`-0` a `-9`); com `--datajud`, testa todos de uma vez.
- **Sem pontuação:** `00620010001382` (14 dígitos) já é o formato do APPG.
- **Separadores trocados:** ponto, traço, barra ou espaço.
- **Sem o foro:** não dá para converter, porque o foro diz a comarca. Procure
  na própria matrícula ou certidão: "do Juízo desta comarca" indica a comarca
  do cartório.

Cuidado com a confusão mais frequente: o número que a matrícula traz pode ser
de **carta precatória** cumprida na comarca do imóvel, e não da ação
principal. Se o texto da averbação disser "carta precatória" ou "deprecado",
a ação principal tem outro número e corre em outra comarca.

## Regras de conversão

```text
APPG (14 dígitos):  FFF AAAA SSSSSS D                → 00620010001382
CNJ:                SSSSSSD-DV.AAAA.8.22.0FFF         → 0001382-90.2001.8.22.0006
                    └─ 7 dígitos: sequencial + dígito antigo
                    DV = 98 − (SSSSSSD·AAAA·822·0FFF·00 mod 97)
```

A regra do CNJ (sequencial junto com o dígito antigo e origem igual ao foro)
foi conferida em 03/11/2026 contra processos antigos reais no DataJud, entre
eles `001.1993.006868-9` → `0068689-57.1993.8.22.0001` e
`001.1995.017505-7` → `0175057-22.1995.8.22.0001`.

**Não confie no exemplo da ajuda do APPG.** A tela diz que `00119960056845`
corresponde a `0056845-15.1996.822.0011`, mas nem a origem (`0011` para o
foro `001`) nem o dígito (`15`; o cálculo dá `75` com essa origem) batem com
os processos reais.

**Erro comum:** montar o CNJ com o sequencial sem o dígito antigo
(`0000138-29.2001.8.22.0006`). Esse número parece válido, tem dígito
verificador certo, e não existe.

## Script

```bash
uv run scripts/numero_antigo.py 006.01.000138-2 006.2005.1624
uv run scripts/numero_antigo.py --datajud 006.01.000138-2 001.97.003786-5
uv run scripts/numero_antigo.py --datajud --todas-origens 00620010001382
uv run scripts/numero_antigo.py --datajud --json < numeros.txt
```

`--datajud` manda todos os candidatos numa única consulta `terms` à API
pública do DataJud (TJRO), em lotes de até 1.000, com nova tentativa em HTTP
429\. `--todas-origens` acrescenta as origens 0001 a 0099, para processo que
mudou de vara ou de comarca.

## Onde procurar, nesta ordem

1. **DataJud** (`--datajud`): rápido e em lote, mas **muitos processos físicos
   antigos não estão lá**, sobretudo os baixados antes da migração. "Não
   encontrado" não quer dizer que o processo não existe.
2. **DESARQ** (arquivo central do TJRO, skill `desarq-tjro`):
   `processo/numero/{n}` aceita o CNJ de 20 dígitos ou os 14 dígitos do APPG.
   Cobre só o que está no arquivo central; processo guardado na comarca, ou já
   eliminado, dá 404.
3. **APPG** (https://www.tjro.jus.br/appg/pages/index.xhtml), na Pesquisa
   Avançada: comarca + "Número Processo Antigo" com os **14 dígitos sem
   pontuação**. Com ponto ou traço, a tela responde "O Número do Processo
   informado é inválido". Se der "não foi localizado", tente "Nome da Parte"
   na mesma comarca, com "Apenas Processos Baixados" marcado.

### APPG pelo navegador

Cada busca do APPG exige um reCAPTCHA **resolvido pela pessoa**. Não tente
resolver, contornar ou automatizar o CAPTCHA. O `scripts/appg.js` só tira o
trabalho manual em volta dele: rodado na aba do APPG pelo Claude in Chrome
(`javascript_tool`), preenche a Pesquisa Avançada e, **se** o CAPTCHA já
estiver resolvido, clica em Consultar e devolve o resultado. Sem CAPTCHA,
devolve `{estado: "aguardando_captcha"}` com o formulário pronto. O desafio
vence em 2 minutos: preencha primeiro e peça à pessoa para marcar a caixa só
depois.

```js
await appg({comarca: "Presidente Médici", tipo: "Número Processo Antigo", parametro: "00620010001382"})
await appg({comarca: "Presidente Médici", tipo: "Nome da Parte", parametro: "NORSEGEL", baixados: true})
```

Detalhes da tela: trocar o tipo de parâmetro reconstrói o formulário e volta
a comarca para Porto Velho. O script escolhe o tipo antes da comarca. A caixa
"Apenas Processos Baixados" é um checkbox do PrimeFaces: o `<input>` fica
escondido, e o script clica na caixa visível.

## Foros do TJRO

Códigos do seletor de comarca do APPG (03/11/2026), que são o `FFF` do número
antigo:

| FFF | Comarca             | FFF | Comarca                   |
| --- | ------------------- | --- | ------------------------- |
| 001 | Porto Velho         | 013 | Cerejeiras                |
| 002 | Ariquemes           | 014 | Vilhena                   |
| 003 | Jaru                | 015 | Guajará-Mirim             |
| 004 | Ouro Preto do Oeste | 016 | Costa Marques             |
| 005 | Ji-Paraná           | 017 | Alta Floresta             |
| 006 | Presidente Médici   | 018 | Santa Luzia do Oeste      |
| 007 | Cacoal              | 019 | Machadinho do Oeste       |
| 008 | Espigão do Oeste    | 020 | Nova Brasilândia do Oeste |
| 009 | Pimenta Bueno       | 021 | Buritis                   |
| 010 | Rolim de Moura      | 022 | São Miguel do Guaporé     |
| 011 | Alvorada do Oeste   | 023 | São Francisco do Guaporé  |
| 012 | Colorado do Oeste   |     |                           |

## Quando nada acha o processo

Não encontrado no DataJud, 404 no DESARQ e "não localizado" no APPG costuma
querer dizer que os autos físicos foram eliminados ou ficaram no arquivo da
comarca. O caminho é pedir à vara de origem (ou à gestão documental do TJRO) o
desarquivamento ou, se eliminados, a data da eliminação e uma **certidão
narrativa** do que consta no sistema.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
