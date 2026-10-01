# Contrato de produção: Gemini 3.8 Flash TTS

Verificado em 1º de outubro de 2026. Modelo-alvo: `gemini-3.8-flash-tts`. Este arquivo descreve recursos observados/documentados nessa data. Reconfira a documentação se o modelo, a interface ou o schema mudar; não suponha equivalência com Gemini 2.5/3.1, Live API ou Cloud Text-to-Speech.

## O que está confirmado

- Texto de entrada é transcrição literal; metadados de atuação ficam separados. Uma entrada de texto pode ter uma anotação `speech_metadata` com `style` e, em diálogo, `speaker`.
- Estilo é breve e local ao trecho. Ao mudar de intenção/prosódia, crie outro trecho. A mesma voz pode aparecer em vários trechos consecutivos.
- Eventos vocais e pausas podem aparecer inline: `<breath>`, `<sigh>`, `<gasp>`, `<laugh>`, `<sob>`, `<cough>`, `<short pause>`, `<long pause>`. Mantenha essas marcações em inglês. Elas não são rubricas arbitrárias nem SSML.
- Não há duração exata prometida para essas pausas. Pontuação e reticências também ajudam na cadência; ênfase por maiúsculas deve ser rara.
- O fluxo API documentado permite duas vozes predefinidas na mesma requisição. Para vozes customizadas, o guia orienta sintetizar cada turno separadamente.

Fonte: [guia oficial de geração de fala](https://ai.google.dev/gemini-api/docs/speech-generation).

O modelo aceita texto e retorna áudio. A página do modelo publica 8.192 tokens de entrada e 16.384 de saída e inclui português entre os idiomas suportados. Esses números não são caracteres, palavras nem minutos; verifique os limites vigentes para planejar material extenso. Não derive uma duração garantida por chamada. Fonte: [ficha oficial do modelo](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts).

## Preparação para AI Studio (fluxo principal)

Interface observada diretamente em [Generate speech](https://aistudio.google.com/generate-speech?model=gemini-3.8-flash-tts), na data acima:

- O editor tem blocos de fala, com seletor de falante/voz, controle `Style` e campo `Speech block text`.
- `Style` oferece `Custom style` com o campo `Describe the voice style`; há também presets como `Whisper`, `Friendly` e `Narration`.
- `Add speech block` cria o próximo trecho. `+ Expression` insere expressões/pausas suportadas.
- As configurações de voz abrem um catálogo. A lista pode diferir dos nomes exemplificados na API; selecione o que a interface realmente apresentar.

Entregue **um conjunto por bloco**, nesta ordem:

1. **Falante:** quem selecionar no controle, fora da transcrição.
2. **Style / Custom style:** uma instrução curta de interpretação.
3. **Speech block text:** somente o texto a falar, em bloco copiável separado.

Exemplo de instrução de uso: “No bloco 1, selecione Helena; cole a direção em Custom style e apenas a fala em Speech block text. Depois use Add speech block.” Não diga para colar tudo no campo de texto. Cabeçalhos como “Bloco 1”, nomes e direções não pertencem à fala.

Se não puder observar a interface atual, use esse mapeamento como referência datada. Se o usuário relatar campos diferentes, peça uma captura ou os nomes dos controles; mantenha transcrição e direção separadas enquanto isso. Não crie um prompt monolítico como falsa solução de compatibilidade.

## Persona contínua e interpretação momentânea

Escolha primeiro uma voz de catálogo que combine com o papel. Timbre, textura, faixa etária percebida e sotaque contínuo pertencem à escolha da voz ou ao recurso opcional Voice Design. `Style` descreve o comportamento da voz neste trecho: contida, hesitante, urgente, bem-humorada, ritmo mais lento etc.

Se o usuário quiser Voice Design, prepare apenas uma descrição curta e consistente, por exemplo: “Voz adulta, médio-grave, textura ligeiramente áspera, português brasileiro com sotaque do interior de Minas discreto. Dicção íntima, sem impostação de locutor.” Isso é um briefing criativo, não uma garantia de resultado. Não misture nele todas as emoções da história.

O [guia oficial de Voice Design](https://ai.google.dev/gemini-api/docs/voice-design) descreve a criação de uma voz a partir de uma descrição e o uso do identificador retornado. Não invente esse ID. A interface observada exige uma chave de API paga para prosseguir em Voice Design. Esse recurso é opcional; não o torne requisito para adaptar o texto. Não vincule chaves, gere vozes ou use replicação de voz apenas porque a skill foi invocada.

## API: representação opcional

Use este formato somente se o usuário pedir API/JSON. A representação corresponde à Interactions API, não ao schema legado `generateContent`. A API e a UI não precisam expor exatamente os mesmos recursos.

Exemplo original mínimo de duas vozes predefinidas:

```json
{
  "model": "gemini-3.8-flash-tts",
  "input": [
    {
      "type": "user_input",
      "content": [
        {
          "type": "text",
          "text": "Você fechou a janela?",
          "annotations": [
            {
              "type": "speech_metadata",
              "speaker": "Helena",
              "style": "hesitant, quiet, slightly suspended ending"
            }
          ]
        },
        {
          "type": "text",
          "text": "Fechei. <short pause> Eu espero você.",
          "annotations": [
            {
              "type": "speech_metadata",
              "speaker": "Bia",
              "style": "gentle, patient, unhurried"
            }
          ]
        }
      ]
    }
  ],
  "response_format": { "type": "audio" },
  "generation_config": {
    "speech_config": {
      "speakers": [
        { "speaker": "Helena", "voice": "Kore" },
        { "speaker": "Bia", "voice": "Puck" }
      ]
    }
  }
}
```

Os nomes `Helena` e `Bia` devem corresponder exatamente entre anotação e configuração. `Kore` e `Puck` são exemplos reais de vozes; não uma recomendação comprovada para estes personagens em português. O JSON é um modelo de estrutura, não um áudio testado. `style` pode descrever a intenção em linguagem natural; inglês curto é uma opção, não obrigação de traduzir a fala.

Para uma voz só, a forma de `speech_config` muda: use `[{"voice":"Kore"}]`; a anotação pode omitir `speaker`. Preserve a sequência de itens de texto se precisar variar `style`. Não adicione um narrador como terceiro speaker a um payload de duas vozes.

Endpoint documentado: `POST https://generativelanguage.googleapis.com/v1beta/interactions`. Autenticação e execução ficam fora desta skill. Fonte do contrato: [Interactions API](https://ai.google.dev/api/interactions-api).

## Recursos avançados, compatibilidade e escuta

O guia oficial documenta `|reação|` para backchannel/sobreposição do outro falante. Não use por padrão: reserve a pedidos de sobreposição natural, mantenha a fala principal inteligível e planeje uma audição curta. Não trate isso como suporte a coro ou elenco ilimitado.

Não há base nesta skill para prometer suporte a `<break time="2s">`, `<phoneme>`, SSML completo, sons de porta, música ou espacialização. Não tente corrigir direção mal posicionada inventando outra tag. Sons ambientais e trilha, se desejados, são indicações para edição externa.

Checklist antes de copiar:

- modelo correto e superfície identificada;
- falantes configurados e nomes coerentes;
- atuação em Style/metadados, transcrição em texto;
- tags válidas, necessárias e sem rubricas disfarçadas;
- limites e cortes de partes conferidos;
- nenhuma afirmação de audição sem áudio de fato ouvido.

Para ensaiar, escolha um trecho representativo. Avalie pronúncia, clareza dos falantes, transição de intenção, pausas e vazamento de instruções. Corrija uma causa por vez. Se não houver áudio disponível, informe “roteiro revisado; interpretação sonora ainda não testada”.
