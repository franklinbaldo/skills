# Desenho de perguntas grounded

Leia esta referência quando precisar aprofundar a técnica de formulação de perguntas para o NotebookLM.

## Princípios

- **Uma pergunta = um fato ou relação verificável.** Evite perguntas amplas como "o que dizem as manifestações?".
- **Peça a fonte e a localização.** Exija documento, trecho literal e ID/página do rodapé.
- **Pergunte pelo que falta.** Datas, protocolos, valores, teor exato, existência de documentos, sequência temporal e divergências documentais são bons alvos.
- **Evite opinião jurídica.** O NotebookLM extrai o que os documentos dizem; a análise jurídica fica fora dele.
- **Varie as frentes dentro do bloco.** Não concentre todas as perguntas numa única hipótese ou documento.
- **Sem dêixis.** Use nomes concretos de órgãos, partes, documentos e processos.
- **Inclua ao menos uma pergunta falsificadora.** Se já existe uma tese em construção, pergunte pelo fato ou documento que mais poderia enfraquecê-la.
- **Abra a primeira rodada com inventário quando necessário.** Rol de peças, IDs/páginas e último ato ajudam a calibrar fase, completude e lacunas.
- **Use cronologia consolidada quando a tese for temporal.** Peça atos em ordem, com data, origem e localização.

## Falsificação

A pergunta falsificadora não busca "mais munição". Ela procura o dado que mudaria a conclusão.

Exemplos de direção:

- se a tese é que uma salvaguarda impede X, pergunte se há nos autos aplicação, falha ou contorno da salvaguarda;
- se a tese é ausência de lesão, procure ato preparatório, efeito indireto ou aplicação concreta;
- se um argumento adverso parece fraco por depender de Y, procure fundamento autônomo Z;
- se um vício parece afastado por um fundamento, procure outra base independente para o mesmo vício.

Uma resposta que enfraquece a tese é um resultado valioso. Se várias rodadas apenas confirmam o enquadramento inicial, endureça as perguntas.

## Primeiro bloco quando a própria tarefa é incerta

Antes do mérito, pergunte pelo ato de encaminhamento e pelo encargo atribuído ao órgão concreto:

- qual ato encaminhou o processo ao órgão e o que pediu;
- se há prazo e a quem foi atribuído;
- se o órgão deve manifestar-se, apenas tomar ciência ou atuar em recorte específico;
- se outro órgão/unidade já conduz o feito.

Defina a tarefa antes de produzir a peça errada com grande convicção.
