# Protocolo de blocos para NotebookLM

Leia esta referência quando for preparar um bloco de perguntas para o usuário copiar no NotebookLM.

## Formato do payload

Cada bloco deve ser um payload limpo, separado do raciocínio da conversa:

1. cabeçalho curto de instruções dirigido ao NotebookLM;
2. perguntas numeradas;
3. nenhuma prosa dirigida ao usuário dentro do payload.

Modelo-base do cabeçalho:

> Responda às perguntas numeradas abaixo, uma a uma, exclusivamente com base nos documentos carregados neste notebook. Para cada resposta: (1) transcreva o trecho literal que a fundamenta; (2) identifique o documento de origem e informe a localização que consta no rodapé — ID para documentos do SEI e página/ID dos autos para documentos do PJe; (3) se as fontes não cobrirem o ponto, responda "as fontes não informam"; (4) se houver documentos divergentes, aponte todos. Não complete com conhecimento externo nem substitua extração documental por opinião jurídica.

Adapte o cabeçalho quando necessário:

- prazos: exigir datas/certidões literalmente;
- valores: exigir transcrição numérica exata;
- revisão de minuta: admitir correspondência parcial/implícita e indicar o grau;
- cronologias: pedir data + documento + ID/página para cada evento.

## Um bloco por rodada

Crie um bloco novo para cada rodada. Não edite o bloco anterior: o histórico da investigação importa porque cada rodada recalibra a seguinte.

O nome deve ser rastreável, por exemplo `bloco-1-<processo>.md`, `bloco-2-<processo>.md`.

## Separação de ferramentas

Não coloque no payload do NotebookLM perguntas que dependam de web, jurisprudência externa, legislação não juntada, DataJud ou outra fonte fora do notebook. Essas consultas pertencem a outro fluxo e devem ser apresentadas separadamente.

## Regra de autossuficiência

Cada pergunta deve fazer sentido para alguém que só tem os documentos carregados e nenhuma memória da conversa. Substitua dêixis como "este caso", "minha unidade", "nós" ou "aquela decisão" pelo nome concreto do órgão, parte, documento ou processo.
