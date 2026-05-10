/-
  ============================================================
  CLAIM METADATA — proveniência e status de claims da Camada 5
  ============================================================

  Módulo standalone (sem imports). Define dois tipos para
  anotar axiomas da Camada 5 (fatos do caso) com metadados
  de rastreabilidade.

  Uso é OPCIONAL: as anotações não afetam derivabilidade.
  Seu valor está na auditoria: `#print axioms` não distingue
  axioma sólido de axioma pendente — este módulo torna a
  diferença explícita no arquivo Lean.

  Importar quando o caso envolver:
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

/-- Associa um axioma da Camada 5 à sua proveniência.
    Uso opcional; não afeta derivabilidade.

    Exemplo de uso em um arquivo de peça:
    ```lean
    axiom mb_eh_especialista : EspecialistaEmEducacao servidora_mb cargo
    axiom prov_mb_eh_especialista :
        TemProveniencia mb_eh_especialista
          (Proveniencia.fonte_declarada "Decreto 7.999/1997, posse 23.03.1998")
    ``` -/
axiom TemProveniencia : ∀ {P : Prop}, P → Proveniencia → Prop

/-- Associa um axioma da Camada 5 ao seu status de necessidade.
    Uso opcional; não afeta derivabilidade.

    Axiomas com `StatusClaim.pendente` têm ônus argumentativo
    adicional na Fase 3 (análise subjetiva). -/
axiom TemStatus : ∀ {P : Prop}, P → StatusClaim → Prop

end ClaimMeta
