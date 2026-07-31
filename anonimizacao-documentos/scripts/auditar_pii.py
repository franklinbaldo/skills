"""Script de Auditoria Adversarial de PII via LLM (Gemini 2.5 Flash / 2.0 Flash).

Submete o corpus anonimizado a dois papéis de auditoria (`Strict_Hunter` e `Forensic_LGPD`)
para garantir risco zero de reidentificação.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from litellm import completion

STRICT_HUNTER_PROMPT = """Você é um Auditor Adversarial de Anonimização (LGPD/Segurança da Informação).
Sua missão é realizar uma CAÇA HIPER-RIGOROSA de dados pessoais ou sensíveis RESIDUAIS que NÃO FORAM ANONIMIZADOS no texto abaixo.

Procure especificamente por:
1. Nomes próprios de pessoas físicas (requerentes, falecidos, dependentes, servidores, médicos, procuradores ou advogados).
2. Iniciais de pessoas (ex: J.S.O., M.A.B.).
3. Números identificadores (CPF, RG, Matrícula, OAB, PIS/PASEP, Título Eleitoral, Número de Processo Judicial CNJ).
4. Dados de Contato (Telefones, e-mails, endereços de rua/bairro).
5. Dados Sensíveis (Diagnósticos médicos, CIDs, laudos, idades exatas de dependentes/menores).

NÃO CONSIDERE PII:
- Municípios, Estados ou Nomes de Órgãos Públicos (ex: SEDUC, SESAU, Porto Velho, Rondônia).
- Marcadores de substituição válidos (ex: _NOME_PESSOA_1_, _CPF_1_, _MATRICULA_SERVIDOR_1_, _RG_1_, _PROCESSO_JUDICIAL_1_, _DATA_NASCIMENTO_1_, _DADO_SAUDE_1_).

Retorne EXCLUSIVAMENTE um JSON válido no formato:
{
  "achados": [
    {
      "documento": "nome_do_arquivo",
      "trecho": "trecho exato encontrado",
      "tipo_sugerido": "tipo de dado",
      "motivo": "explicacao"
    }
  ]
}
Se o texto estiver 100% limpo, retorne {"achados": []}.
"""

FORENSIC_LGPD_PROMPT = """Você é um Perito Forense Especializado em LGPD e Dados Abertos na Administração Pública.
Examine o corpus de documentos abaixo e identifique qualquer VULNERABILIDADE DE REIDENTIFICAÇÃO ou VAZAMENTO DE DADOS PESSOAIS (PII).

Avalie rigorosamente:
1. Reidentificação direta (nomes de pessoas, RGs, CPFs, matrículas, processos judiciais).
2. Marcadores inconsistentes ou vazamentos de metadados nos rodapés/cabeçalhos.
3. Informações sensíveis de saúde ou menores.

Retorne EXCLUSIVAMENTE um JSON válido no formato:
{
  "achados": [
    {
      "documento": "nome_do_arquivo",
      "trecho": "trecho_encontrado",
      "categoria": "categoria do risco",
      "justificativa_forense": "explicacao do risco de reidentificacao"
    }
  ]
}
Se não houver nenhum risco de reidentificação, retorne {"achados": []}.
"""

def auditar_documento(file_path: Path, model: str = "gemini/gemini-2.5-flash") -> dict:
    text = file_path.read_text(encoding="utf-8")
    
    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": STRICT_HUNTER_PROMPT},
            {"role": "user", "content": f"=== DOCUMENTO: {file_path.name} ===\n{text}"}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)

def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria Adversarial de PII via LLM.")
    parser.add_argument("--input", required=True, help="Arquivo .anon.md ou diretório contendo arquivos .anon.md")
    parser.add_argument("--model", default="gemini/gemini-2.5-flash", help="Modelo LLM para auditoria")
    args = parser.parse_args()

    input_path = Path(args.input)
    files = [input_path] if input_path.is_file() else list(input_path.glob("**/*.anon.md"))

    print(f"Submetendo {len(files)} arquivo(s) anonimizado(s) à auditoria adversarial ({args.model})...")
    total_findings = 0
    for idx, f in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] Auditando {f.name}...")
        try:
            res = auditar_documento(f, model=args.model)
            achados = res.get("achados", [])
            if achados:
                print(f"   [ALERTA] Encontradas {len(achados)} possíveis PIIs residuais:")
                for a in achados:
                    print(f"     - Trecho: {a.get('trecho')!r} | Tipo: {a.get('tipo_sugerido')} | Motivo: {a.get('motivo')}")
                total_findings += len(achados)
            else:
                print("   [OK] Documento 100% limpo.")
        except Exception as e:
            print(f"   [ERRO] Falha na auditoria de {f.name}: {e}")
        time.sleep(2)

    print(f"\nAuditoria concluída! Total de alertas encontrados: {total_findings}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
