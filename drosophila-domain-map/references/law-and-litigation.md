# Direito / processo -> Drosophila

O direito é particularmente adequado a uma tradução por **loops sucessivos de expectativa,
feedback e correção**, não por um único reward terminal.

A correspondência útil não é "ganhar a causa = açúcar". É representar cada fase como um
evento que atualiza crença, valor esperado, estratégia e disposição para continuar agindo.

## Estrutura geral

Um processo jurídico pode ser lido como uma sequência:

```text
expectativa inicial
  -> consulta / triagem
  -> aceitação ou rejeição pelo advogado
  -> formulação da tese
  -> resposta da outra parte
  -> decisões interlocutórias
  -> produção de prova
  -> sentença
  -> recurso
  -> resposta do tribunal
  -> execução / resultado real
```

Cada estágio pode produzir:

- confirmação parcial;
- surpresa positiva;
- surpresa negativa;
- redução ou aumento de confiança;
- mudança de política;
- abandono;
- persistência;
- escalada;
- atualização sobre a confiabilidade de outro agente.

Isso se aproxima mais de **reinforcement learning hierárquico e social** do que de um reward
terminal único.

## Mapa inicial

| Conceito jurídico/processual | Correspondência plausível em Drosophila | Força | Tradução experimental |
|---|---|---|---|
| expectativa da parte sobre o caso | valor esperado / predisposição inicial condicionada por estado e memória | operational_analogy | inicializar uma crença/drive antes do primeiro feedback |
| consulta ao advogado | primeiro agente social/avaliador que fornece feedback informativo | operational_analogy | outro agente transforma evidência em sinal de confiança/rejeição |
| advogado aceita a tese | reinforcement intermediário / confirmação de expectativa | operational_analogy | reward parcial, menor que o resultado terminal |
| advogado rejeita a tese | aversive prediction error / correção de expectativa | operational_analogy | penalidade informativa que deve alterar política futura |
| petição inicial | ação escolhida após integração de expectativa + aconselhamento | operational_analogy | saída/ação que altera o ambiente e provoca nova observação |
| contestação | feedback adversarial de outro agente com informação estratégica | functional/operational | nova observação capaz de revelar erro da política anterior |
| réplica | atualização de política após observação adversarial | operational_analogy | segunda ação condicionada ao novo estado |
| decisão interlocutória | reward/punishment parcial com efeito sobre trajetória futura | operational_analogy | shaping signal legítimo se refletir mudança real de valor futuro |
| produção de prova | aquisição ativa de informação com custo | operational_analogy | probe pago que reduz incerteza e pode mudar valor esperado |
| sentença | grande atualização de valor, mas ainda não necessariamente terminal | operational_analogy | reward forte com possibilidade de continuação |
| recurso | escolha de persistir/escalar após resultado negativo | operational_analogy | política dependente do valor esperado residual e custo |
| precedente/jurisprudência | memória coletiva / experiência indireta usada para atualizar política | operational_analogy | informação prévia sobre contingências semelhantes |
| trânsito em julgado | estado terminal jurídico da controvérsia | operational_analogy | fechar episódio apenas quando o sistema realmente não admite continuação |
| execução | realização material do reward esperado | operational_analogy | separar reconhecimento formal de recompensa efetivamente entregue |
| sucumbência/custos | penalidade econômica associada à política escolhida | functional/operational | custo explícito que deve entrar no valor líquido |
| acordo | política alternativa que troca upside por redução de risco/tempo | operational_analogy | escolha entre recompensa certa menor e distribuição futura incerta |
| litigância repetitiva | aprendizado em episódios recorrentes | operational_analogy | atualizar política usando histórico de múltiplos casos |
| reputação do advogado/juízo | confiança aprendida em outra fonte de feedback | operational_analogy | meta-learning sobre confiabilidade de agentes |

## Exemplo: cadeia de feedback da parte

Considere uma parte que chega com a expectativa (E_0).

1. **Consulta ao advogado**
   - advogado concorda: atualização positiva (E_1 > E_0);
   - advogado discorda: atualização negativa (E_1 < E_0).

2. **Petição / contestação**
   - a parte contrária revela fato ou argumento forte: surpresa negativa;
   - a tese resiste: confirmação parcial.

3. **Decisão interlocutória / prova**
   - cada evento fornece evidência adicional sobre o valor esperado do caso;
   - alguns eventos são informativos sem serem reward final.

4. **Sentença**
   - grande atualização, mas não necessariamente terminal;
   - possibilidade de recurso mantém valor futuro acessível.

5. **Trânsito / execução**
   - o reward jurídico e o reward material podem divergir;
   - vitória formal sem satisfação material deve ser modelada como reward incompleto.

A tradução para uma drosófila não deve injetar cada fase como um mesmo escalar. Uma forma
mais biologicamente plausível é classificar os eventos:

- confirmação apetitiva;
- surpresa aversiva;
- alívio por evitar uma perda esperada;
- custo energético/temporal;
- informação nova sem valência imediata;
- mudança de confiança em um agente social.

## Multi-agent loop

O processo também contém vários agentes aprendendo simultaneamente:

- parte;
- advogado;
- contraparte;
- advogado adversário;
- juiz;
- tribunal;
- eventualmente MP, perito, testemunhas e órgãos administrativos.

Cada agente observa apenas uma parte do estado, possui objetivos distintos e produz sinais
que alteram a política dos demais.

Isso torna o processo jurídico um bom candidato para analogias com:

- partially observable multi-agent learning;
- repeated games;
- hierarchical reinforcement learning;
- active information acquisition;
- reputation / reliability learning;
- delayed and sparse rewards;
- nested feedback loops.

## Regra importante

Não mapear "decisão judicial desfavorável" automaticamente para dor/punição biológica.

Primeiro perguntar: **qual função computacional esse evento exerce para o agente?**

Ele pode ser:

- punição;
- informação;
- surpresa;
- atualização de probabilidade;
- custo;
- sinal social;
- mudança de oportunidade futura.

A transdução biológica deve seguir essa função, não o nome jurídico do evento.

## Experimentos derivados

Uma task jurídica biologicamente endereçada poderia modelar um agente que decide, em etapas,
se deve:

- consultar;
- coletar mais evidência;
- formular uma tese;
- negociar;
- persistir;
- recorrer;
- abandonar.

O reward terminal pode representar resultado líquido, mas os sinais intermediários devem ser
separados em valência, informação, custo e confiabilidade social. O teste interessante é se o
MaleCNS consegue aprender uma política robusta sob esses loops melhor ou com menos dados/compute
que controles pareados.
