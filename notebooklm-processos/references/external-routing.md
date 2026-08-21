# Roteamento para fontes externas

Leia esta referência quando uma pergunta relevante não puder ser respondida apenas pelos documentos carregados no NotebookLM.

## Regra de fronteira

NotebookLM é para conteúdo dos autos/documentos carregados. Não use o notebook como mecanismo de pesquisa jurídica externa.

Redirecione para outras fontes quando a questão depender de:

- texto ou interpretação de norma não juntada;
- jurisprudência, precedentes, doutrina ou estado da arte;
- movimentação processual posterior à exportação do PDF;
- metadados correntes de processo;
- documento administrativo citado, mas não presente no material carregado.

## Ferramentas típicas

- `datajud`: metadados e linha de movimentação pública por número CNJ; não substitui o teor do ato;
- `juris-tjro`: jurisprudência do TJRO;
- web/fontes oficiais: legislação, STF/STJ e demais pesquisas externas;
- PJe/SEI via usuário: teor de ato/documento que não está nas fontes disponíveis.

## PDF como snapshot

O PDF dos autos é um retrato da data de exportação. Se a data estiver incerta, antiga ou a conclusão depender da fase atual, confira a movimentação corrente antes de fechar o trabalho. Se houver ato novo relevante, o teor precisa entrar por fonte adequada.

## Pesquisa ampla vs consulta pontual

Para uma ou duas verificações pontuais, execute a pesquisa diretamente quando a ferramenta estiver disponível. Para investigação ampla ou exploratória, entregue queries específicas, variadas e executáveis, incluindo ao menos uma voltada a encontrar evidência contrária à tese.

Todo retorno externo precisa trazer âncoras verificáveis — número do processo/precedente, órgão, data, situação e fonte oficial quando aplicável — antes de ser integrado ao raciocínio.
