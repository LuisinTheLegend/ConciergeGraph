# Registro de Observações Fora de Escopo

> **Base Normativa:** Regra 4 do [`AUDIT_PROTOCOL.md`](file:///c:/Nexus-Memory/GrafoConcierge/AUDIT_PROTOCOL.md).  
> **Objetivo:** Registrar ocorrências notadas durante as execuções e validações que estão fora do escopo estrito da auditoria de produção, preservando o backlog sem investigar nem alterar código de testes ou de terceiros prematuramente.  
> **Classificação:** Todas as entradas abaixo são rotuladas formalmente como **Observações**, e **NÃO** como achados de auditoria do produto.

---

## 1. Observações em Código e Infraestrutura de Teste

### Observação 1: Falta de `import importlib.util` em `tests/test_vector_reconciler.py`
- **Arquivo & Linhas:** [`tests/test_vector_reconciler.py:17, 27, 31, 37, 41`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_vector_reconciler.py#L17)
- **O que foi observado:** O arquivo executa `import importlib` na linha 17, mas referencia o submódulo `importlib.util` diretamente nas linhas 27, 31, 37 e 41 (`importlib.util.spec_from_file_location`, `importlib.util.module_from_spec`). Em Python, `import importlib` não vincula automaticamente o submódulo `util` ao namespace `importlib`. Trata-se de um bug latente no arquivo de teste, mascarado sempre que outro módulo importado previamente no mesmo processo já carregou `importlib.util`.
- **Por que NÃO foi tratado nesta auditoria:** A auditoria em curso tem escopo restrito às vulnerabilidades, defeitos arquiteturais e contratos de código de produção e catálogo do backlog (Regras 4 e 8). Edições em suítes de teste de terceiros ou arquivos de teste pré-existentes estão fora do escopo estrito da Fase 3 e foram contornadas no ambiente de auditoria através de pré-carregamento explícito de `importlib.util` no script de reprodução [`scratch/reproduce_all_targets.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_all_targets.py).

### Observação 2: Acoplamento de Imports no Topo de `tests/test_interface_contracts.py` Bloqueia Importação Isolada
- **Arquivo & Linhas:** [`tests/test_interface_contracts.py:15, 19`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_interface_contracts.py#L15)
- **O que foi observado:** O arquivo importa `pytest` (linha 15) e `interface.mcp_server.GrafoConciergeServer` (linha 19) no nível de módulo (top-level). Por sua vez, `interface/mcp_server.py` requer a biblioteca externa `mcp` (`FastMCP`). Isso impede que utilitários de inspeção ou revisores externos importem diretamente classes utilitárias isoladas definidas no mesmo arquivo — como `_MockVectorStore` (linhas 40–65) — sem que todo o ambiente de produção e dependências externas do projeto estejam previamente instalados e funcionais.
- **Por que NÃO foi tratado nesta auditoria:** Trata-se de uma característica de design e empacotamento da suíte de testes legada. Modificar a estrutura de imports do arquivo de teste violaria o escopo estrito das Regras 4 e 8 (não editar código de teste ou produção pré-existente). A questão foi remediada no script de auditoria [`scratch/reproduce_all_targets.py`](file:///c:/Nexus-Memory/GrafoConcierge/scratch/reproduce_all_targets.py) através de stubs via `unittest.mock` e fallback autônomo via AST parsing.
