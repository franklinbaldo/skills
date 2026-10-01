# Exemplo original — A chave

Texto-fonte e adaptação criados para esta skill. Ficção, não transcrição de um acontecimento real. O exemplo mostra passadas diferentes; os blocos da etapa 5 são o material destinado à síntese.

## Texto-fonte

No dia em que deixou a velha casa, Helena entregou a chave à irmã, Bia. Bia deveria passá-la ao comprador às cinco. Antes de sair, Helena voltou e fechou a janela da cozinha. Depois perguntou à irmã se a janela estava fechada. Bia confirmou. Helena perguntou outra vez. Bia percebeu que a irmã adiava a despedida e devolveu a chave por um instante. Helena tocou o metal, sorriu e a entregou de volta. As duas saíram juntas.

## Passada 1 — Brief e plano

Pedido de exemplo: “Adapte este texto para uma cena íntima de duas vozes no AI Studio. Preserve os acontecimentos e evite melodrama.”

Escolhas: adaptação dramática fiel, português brasileiro, duas vozes, sem narrador. As falas serão criadas a partir dos acontecimentos narrados. Não haverá trilha nem efeito obrigatório. O tempo resultará da interpretação, sem alvo cronometrado.

Invariantes: venda da casa; entrega ao comprador às cinco; janela de fato fechada; repetição como adiamento; breve devolução da chave; despedida conjunta.

Mapa de beats:

1. Uma providência prática tenta encerrar a saída.
2. A pergunta sobre a janela adia a despedida.
3. A repetição faz Bia reconhecer o que Helena precisa.
4. A chave volta por um instante; Helena consegue devolvê-la e sair.

Critério para avançar: a virada será um gesto de Bia, não um discurso explicando o apego de Helena.

## Passada 2 — Rascunho funcional, ainda sem TTS

Os nomes abaixo são rótulos editoriais; este rascunho não deve ser colado no campo de fala.

Helena: O comprador vem às cinco?
Bia: Sim. Eu entrego a chave.
Helena: Fechei a janela, mas queria verificar de novo.
Bia: A janela está fechada.
Helena: Tem certeza?
Bia: Você não está pronta para ir embora. Pegue a chave por mais um instante.
Helena: Obrigada. Agora estou pronta. Pode levar.
Bia: Vamos juntas.

O percurso está completo. O diálogo, porém, explica demais o sentimento e resolve a despedida de modo excessivamente arrumado.

## Passada 3 — Revisão dramatúrgica

Mudanças observáveis:

- “Você não está pronta” vira uma oferta concreta: segurar a chave. Bia compreende sem diagnosticar a irmã.
- Helena pergunta novamente sobre o que acabou de fazer. A repetição passa a executar o adiamento.
- “Agora estou pronta” dá lugar a “Pronto. Pode levar.” A decisão está numa ação pequena.
- A saída fecha com pergunta e resposta, preservando a companhia sem uma moral final.

Versão revisada, ainda sem tags:

Helena: Bia... o comprador vem às cinco?
Bia: Às cinco. Deixa a chave comigo.
Helena: A janela da cozinha... ficou fechada?
Bia: Você fechou. Eu vi.
Helena: Ficou mesmo?
Bia: Ficou. Toma. Segura mais um pouquinho.
Helena: Eu só... Pronto. Pode levar.
Bia: Vamos?
Helena: Vamos.

A relação de irmãs orienta a intimidade da cena. Não foi acrescentada uma explicação artificial do parentesco. A venda, a janela e a chave continuam sustentando a ação.

## Passada 4 — Direção

Mapa editorial do elenco: Speaker 1 = Helena; Speaker 2 = Bia. Se a UI permitir renomear, use os nomes; se não, mantenha esse mapa fora da transcrição.

- Helena: reserva emocional, frases que procuram continuar, pouco volume; firmeza apenas na decisão final.
- Bia: objetividade afetuosa, respostas diretas; depois oferece tempo, sem pena ou tom terapêutico.

Selecione duas vozes de catálogo com contraste discreto e teste se soam naturais em português. Não é necessário criar vozes. A direção por bloco muda a atuação; o timbre de cada personagem permanece.

Há duas pausas marcadas: Bia dá tempo para a oferta chegar, e Helena passa da dificuldade à decisão. Não é necessário inserir choro, suspiro, riso ou uma expressão em cada fala.

## Passada 5 — Campos prontos para AI Studio

Selecione o modelo Gemini 3.8 Flash TTS. Em cada bloco, selecione o falante e coloque a direção em Style → Custom style. Copie somente o conteúdo do bloco de texto para Speech block text. Crie o seguinte com Add speech block. Os títulos, nomes e direções abaixo não são transcrição.

### Bloco 1

Falante: Helena / Speaker 1

Style / Custom style:

```text
Contida; pergunta como quem prolonga uma conversa. Entrada hesitante, sem choro.
```

Speech block text:

```text
Bia... o comprador vem às cinco?
```

### Bloco 2

Falante: Bia / Speaker 2

Style / Custom style:

```text
Prática e afetuosa. Resposta simples, cadência cotidiana.
```

Speech block text:

```text
Às cinco. Deixa a chave comigo.
```

### Bloco 3

Falante: Helena / Speaker 1

Style / Custom style:

```text
Hesitante, procurando uma última providência. Final da pergunta ligeiramente suspenso.
```

Speech block text:

```text
A janela da cozinha... ficou fechada?
```

### Bloco 4

Falante: Bia / Speaker 2

Style / Custom style:

```text
Tranquila e direta. Confirma sem corrigir com dureza.
```

Speech block text:

```text
Você fechou. Eu vi.
```

### Bloco 5

Falante: Helena / Speaker 1

Style / Custom style:

```text
Mais baixa e breve; a insistência quase lhe escapa.
```

Speech block text:

```text
Ficou mesmo?
```

### Bloco 6

Falante: Bia / Speaker 2

Style / Custom style:

```text
Suave e paciente. A oferta vem com espaço, sem pena nem solenidade.
```

Speech block text:

```text
Ficou. <short pause> Toma. Segura mais um pouquinho.
```

### Bloco 7

Falante: Helena / Speaker 1

Style / Custom style:

```text
Começa sem encontrar palavras; depois da pausa, fica discretamente mais firme, com um sorriso leve no final.
```

Speech block text:

```text
Eu só... <short pause> Pronto. Pode levar.
```

### Bloco 8

Falante: Bia / Speaker 2

Style / Custom style:

```text
Convite sereno, sem apressar a resposta.
```

Speech block text:

```text
Vamos?
```

### Bloco 9

Falante: Helena / Speaker 1

Style / Custom style:

```text
Simples e decidida, ainda íntima. Final baixo e assentado.
```

Speech block text:

```text
Vamos.
```

## Passada 6 — Conferência e próxima revisão

- A chave volta por um instante pela oferta “Toma” e é devolvida por “Pode levar”. A ação precisa continuar clara na escuta.
- A única emoção que muda dentro de uma fala curta está vinculada à pausa de Helena. Se a mudança ficar imprecisa no áudio, divida o bloco 7 em dois, mantendo a mesma voz.
- Não há terceiro speaker, nomes de personagem como rótulos dentro do texto nem sons não vocais solicitados ao TTS. “Bia” no bloco 1 é um vocativo intencional, parte da fala.
- Não foram gerados nem ouvidos áudios deste exemplo. O roteiro foi revisado, mas a interpretação sonora ainda precisa de teste.

Ensaio sugerido, caso o usuário decida gerar: blocos 5–9. Verificar se a gentileza de Bia soa cotidiana, se a hesitação de Helena não vira choro excessivo e se os dois “Vamos” têm intenções diferentes. Corrigir a direção localizada; não acrescentar mais tags automaticamente.
