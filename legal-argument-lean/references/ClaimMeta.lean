/-
  ============================================================
  CLAIM METADATA — proveniência e status de claims da Camada 5
  ============================================================

  Stability: experimental

  Módulo standalone (sem imports). Define dois tipos para
  anotar axiomas da Camada 5 (fatos do caso) com metadados
  de rastreabilidade.

  As anotações não afetam derivabilidade. Seu valor está na
  auditoria: `#print axioms` não distingue axioma sólido de
  axioma pendente — este módulo torna a diferença explícita no
  arquivo Lean.

  Uso obrigatório em novos casos do pipeline complexo. No workflow
  direto, importar quando o caso envolver:
  - Claims com fonte incerta ou inferida
  - Workflow de inferência regressiva (acórdão → documentos
    anteriores)
  - Necessidade de registrar o que ainda precisa ser verificado
    antes de protocolar a peça
-/

namespace ClaimMeta

/-- Proveniência de um axioma da Camada 5.

  - `endogena`: o tribunal chegou à conclusão por raciocínio
    próprio; o axioma é extraído do próprio acórdão/decisão.
  - `fonte_declarada s`: o tribunal ou documento cita
    explicitamente a origem `s`.
  - `fonte_inferida`: o documento pressupõe algo que
    provavelmente veio de documento anterior, mas não cita.
    Gera pergunta ao formalizante (ver workflow regressivo).
  - `confirmada_pelo_procurador`: origem inicialmente inferida
    e depois confirmada por quem tem os autos.
  - `pendente`: o formalizante ainda não determinou. Estado
    neutro — não implica que o conhecimento seja irrecuperável.
    Não trava o pipeline; registra incerteza honestamente.
-/
inductive Proveniencia
  | endogena
  | fonte_declarada : String → Proveniencia
  | fonte_inferida
  | confirmada_pelo_procurador
  | pendente

/-- Status de necessidade de um claim num documento.

  - `necessaria`: sem esta claim o efeito processual do ato
    não ocorreria — é load-bearing para o documento de origem.
  - `contingente`: presente no documento mas não necessária
    para o efeito produzido. "Dito de passagem." Claims
    contingentes de documentos anteriores propagam-se
    inadvertidamente em documentos posteriores — identificar
    essa propagação é argumento processual.
  - `pendente`: o formalizante não tem como determinar a partir
    do material disponível. Estado neutro; não trava o pipeline.
-/
inductive StatusClaim
  | necessaria
  | contingente
  | pendente

/-- Localização auditável da claim no material do caso. Strings são
    intencionais: sistemas judiciais variam entre página, folha, ID,
    evento, item e timestamp. -/
structure Localizador where
  documento : String
  localizacao : String
  autorOuOrgao : String
  deriving Repr

/-- Associa um axioma da Camada 5 à sua proveniência.
    Obrigatório em novos casos do pipeline complexo; não afeta
    derivabilidade.

    Exemplo de uso em um arquivo de peça:
    ```lean
    axiom mb_eh_especialista : EspecialistaEmEducacao servidora_mb cargo
    axiom prov_mb_eh_especialista :
        TemProveniencia mb_eh_especialista
          (Proveniencia.fonte_declarada "Decreto 7.999/1997, posse 23.03.1998")
    ``` -/
axiom TemProveniencia : ∀ {P : Prop}, P → Proveniencia → Prop

/-- Associa um axioma da Camada 5 ao seu status de necessidade.
    Obrigatório em novos casos do pipeline complexo; não afeta
    derivabilidade.

    Axiomas com `StatusClaim.pendente` têm ônus argumentativo
    adicional na Fase 3 (análise subjetiva). -/
axiom TemStatus : ∀ {P : Prop}, P → StatusClaim → Prop

/-- Associa um axioma da Camada 5 ao documento e ao ponto exato
    de onde foi extraído. -/
axiom TemLocalizador : ∀ {P : Prop}, P → Localizador → Prop

/- Metadados próprios de premissas STEEL_n. -/

/-- Natureza da reconstrução caridosa do passo ausente. -/
inductive TipoReconstrucao
  | textual
  | reconstrutiva
  | puramenteCaridosa

/-- Grau de apoio material encontrado para a premissa reconstruída. -/
inductive StatusSuporte
  | semSuporte
  | plausivel
  | ancoradaNosAutos

/-- Ficha auditável de uma premissa STEEL_n.

    - `atribuivelA`: ator cuja posição precisaria aceitar a premissa.
    - `baseTextual`: trecho/localizador que pode sustentá-la; usar
      "nenhuma identificada" quando inexistente.
    - `tipo`: textual, reconstrutiva ou puramente caridosa.
    - `status`: força do apoio material efetivamente encontrado.
    - `condicaoFalsificacao`: observação que derrotaria a premissa.
-/
structure SteelMeta where
  atribuivelA : String
  baseTextual : String
  tipo : TipoReconstrucao
  status : StatusSuporte
  condicaoFalsificacao : String
  deriving Repr

/-- Associa uma premissa STEEL_n à sua ficha epistemológica.
    Obrigatório para novos steelmans. Não torna a premissa mais
    verdadeira nem altera derivabilidade. -/
axiom TemSteelMeta : ∀ {P : Prop}, P → SteelMeta → Prop

end ClaimMeta
