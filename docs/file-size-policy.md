# Limite de tamanho dos arquivos (catraca)

Arquivos de texto **novos ou modificados** devem ter até **20.000 bytes UTF-8**, uma aproximação leve de 5.000 tokens (4 bytes por token). Não há tokenizador nem whitelist. Arquivos antigos não modificados ficam fora da verificação. Ao tocar um arquivo legado grande, reorganize-o até respeitar o limite.

**Objetivo:** tornar o conteúdo localizável pelo nome do arquivo e reduzir a quantidade de contexto necessária para humanos e agentes entenderem uma alteração. Separe unidades coesas por responsabilidade, assunto ou interface; escolha nomes descritivos, não nomes genéricos/numerados. Atualize imports, links, índices, referências e testes. Preserve comportamento e informação; nunca compacte/minifique somente para passar no check.

**Execução:** `python3 scripts/check_file_token_limit.py` ou `prek run file-token-limit --hook-stage pre-push --all-files`. CI executa o mesmo script comparando o HEAD da PR com sua base. São ignorados arquivos binários, lockfiles e artefatos gerados previstos no código. Esses filtros são técnicos, não exceções individuais.

Em caso de bloqueio, o próprio verificador informa o arquivo, a estimativa e os passos de reorganização.
