# Auditoria — `core/security_guard.py`

> **Item:** `core/security_guard.py` (SDD-SURVIVAL-24: Boundary Guard & Hazard Classifier)  
> **Fase:** 1 — Auditoria módulo a módulo  
> **Data:** 2026-09-20  
> **Status:** Concluído, aguardando aprovação  

---

## 1. Ferramentas Estáticas Executadas

| Ferramenta | Comando | Resultado |
|------------|---------|-----------|
| **ruff** | `python -m ruff core/security_guard.py` | Não instalado no ambiente Python |
| **bandit** | `python -m bandit core/security_guard.py` | Não instalado no ambiente Python |
| **mypy** | `python -m mypy core/security_guard.py --follow-imports=skip` | `Success: no issues found in 1 source file` |
| **unittest** | `python -m unittest tests/test_adaptive_gating.py` | 12 passed em 0.023s |
| **unittest** | `python -m unittest tests/test_agent_hsm_coupling.py` | 13 passed em 0.759s |

---

## 2. Tabela de Achados (Formato Oficial do Protocolo)

| # | arquivo | linha | severidade | mecanismo | reprodução | status |
|---|---------|-------|-----------|-----------|------------|--------|
| 1 | `core/security_guard.py` | 42–45, 94–95 | **CRÍTICA** | Regex de blacklist `\brm\s+-rf\s+/` é facilmente contornada por variações canônicas de comandos destrutivos: `rm -fr /` (flags invertidas), `rm -r -f /`, `rm --recursive --force /`, além de destruição do diretório corrente (`rm -rf .`, `rm -rf *`) e comandos destrutivos do Windows (`del /f /s /q C:\*`, `format C:`). Em modo `auto-approve`, qualquer comando não classificado como `CRITICAL` é executado automaticamente sem aprovação humana. | Script de reprodução testa 9 variações de evasão: todas retornam `SAFE`. Ver saída bruta abaixo. | **CONFIRMADO** |
| 2 | `core/security_guard.py` | 94 | **ALTA** | `classify_command(command)` não valida se `command` é `None` antes de executar `self.blacklisted_patterns.search(command)`. Lança `TypeError: expected string or bytes-like object, got 'NoneType'` não tratado, derrubando o fluxo do interceptador/servidor caso uma chamada venha com payload nulo. | Chamada direta `guard.classify_command(None)` lança `TypeError`. Ver saída abaixo. | **CONFIRMADO** |
| 3 | `core/security_guard.py` | 75–77 | **MÉDIA** | Concatenação ingênua de separador `self.project_root + os.sep`. Se `project_root` for a raiz de um disco ou volume (`C:\` no Windows ou `/` no Linux), `os.path.realpath` já termina com separador. A concatenação gera `C:\\\\` ou `//`. Como nenhum caminho de arquivo começa com barra dupla, `is_safe_path` retorna `False` para 100% dos arquivos válidos dentro do disco/raiz. | `SecurityGuard(project_root="C:\\").is_safe_path("C:\\test_folder\\file.txt")` retorna `False`. | **CONFIRMADO** |
| 4 | `core/security_guard.py` | 72–77 | **MÉDIA** | Resolução de caminhos relativos em `is_safe_path` via `os.path.realpath(target_path)` resolve contra o `os.getcwd()` do processo em vez de `self.project_root`. Se o `project_root` for um projeto externo registrado (diferente do CWD do servidor), qualquer caminho relativo legítimo (ex: `src/main.py`) é resolvido para o CWD do GrafoConcierge e incorretamente rejeitado como fora dos limites (`is_safe_path -> False`). | CWD em `C:\Nexus-Memory\GrafoConcierge`, `project_root` em `C:\ExternalProject\Workspace`: `is_safe_path("src/app.py")` retorna `False`. | **CONFIRMADO** |
| 5 | `core/security_guard.py` | 48–54, 98–99 | **BAIXA** | Verificação de `warning_terms` usa busca ingênua de substring sem limites de palavra (`any(term in command)`). O termo `"build"` causa falsos positivos automáticos para comandos inofensivos de desenvolvimento como `git log --grep="build"`, `cat build.py`, `git checkout build-fix` ou `ls -la build/`, disparando prompts interativos desnecessários no modo `ask`. | Comandos inofensivos de leitura e git com a palavra `build` são classificados como `WARNING`. | **CONFIRMADO** |

---

## 3. Detalhamento de Cada Achado

### Achado #1 — Evasão da Blacklist de Comandos Destrutivos (`CRITICAL`)

- **Mecanismo da Falha:**  
  A detecção de comandos críticos é baseada em uma única expressão regular estática:
  ```python
  self.blacklisted_patterns = re.compile(
      r"(\brm\s+-rf\s+/|\b(mkfs|dd\s+if|shutdown|reboot|systemctl|userdel|iptables)\b)",
      re.IGNORECASE,
  )
  ```
  A expressão exige literalmente a sequência de flags `-rf` e a barra raiz `/`. Qualquer variação de flags válida no shell GNU/POSIX ou comandos nativos de deleção massiva do Windows/Linux escapa da regex e cai no fallback `return "SAFE"`.
- **Impacto no Sistema:**  
  No modo `auto-approve` do [`GatingInterceptor`](file:///c:/Nexus-Memory/GrafoConcierge/core/gating_interceptor.py#L130), comandos classificados como `SAFE` ou `WARNING` são executados imediatamente sem confirmação humana. Um agente autônomo sob alucinação ou injeção de prompt que emita `rm -fr /`, `rm -rf .`, ou `del /f /s /q C:\*` tem seu comando executado sem bloqueio, causando destruição total dos arquivos do projeto ou do sistema operacional.
- **Correção Conceitual Sugerida (Fase 3):**  
  1. Tokenizar a linha de comando (ex: via `shlex.split`) e analisar o binário invocado e suas flags de forma semântica em vez de regex ingênua.
  2. Adicionar padrões para o Windows (`rmdir /s`, `del /s`, `format`, `diskpart`).
  3. Bloquear qualquer invocação recursiva de deleção (`-r`, `-R`, `--recursive`) quando o alvo for `/`, `/*`, `.`, `*` ou caminhos que resolvam fora ou na raiz do projeto.

---

### Achado #2 — `classify_command(None)` lança `TypeError` não tratado

- **Mecanismo da Falha:**  
  Diferente de `is_safe_path` (que faz `if not target_path: return True`), `classify_command` assume que o argumento é sempre uma string e invoca diretamente `self.blacklisted_patterns.search(command)`. Passar `None` faz o motor de regex do Python lançar `TypeError: expected string or bytes-like object, got 'NoneType'`.
- **Impacto no Sistema:**  
  Em pipelines onde argumentos de ferramentas são desserializados de JSON (onde chaves podem vir com valor `null` ou não preenchidas), a chamada quebra a thread de execução do agente ou dispara erro 500 no interceptador.
- **Correção Conceitual Sugerida (Fase 3):**  
  Adicionar salvaguarda no início do método:
  ```python
  if not command or not isinstance(command, str):
      return "SAFE"
  ```

---

### Achado #3 — Bug do Separador Duplo em Raiz de Disco / Filesystem Root

- **Mecanismo da Falha:**  
  O método `is_safe_path` constrói o prefixo de fronteira física através de:
  ```python
  return absolute_target.startswith(
      self.project_root + os.sep
  ) or absolute_target == self.project_root
  ```
  Quando `project_root` é uma raiz de partição (como `C:\` no Windows ou `/` no POSIX), `os.path.realpath(project_root)` preserva o separador final. A expressão `self.project_root + os.sep` resulta em `C:\\\\` ou `//`. Como caminhos absolutos como `C:\Projeto\arquivo.py` contêm apenas uma barra, a verificação `startswith` falha e o método retorna `False`.
- **Impacto no Sistema:**  
  Se um usuário configurar o GrafoConcierge para auditar ou minerar um disco/volume montado em raiz (`C:\` ou `/data`), nenhuma leitura ou escrita de arquivo é autorizada pelo `SecurityGuard`, tornando o sistema inoperante para esses projetos.
- **Correção Conceitual Sugerida (Fase 3):**  
  Normalizar o prefixo garantindo que haja exatamente um separador:
  ```python
  root = self.project_root.rstrip(os.sep) + os.sep
  return absolute_target.startswith(root) or absolute_target == self.project_root
  ```

---

### Achado #4 — Resolução de Caminhos Relativos Ancorada ao CWD em vez de `self.project_root`

- **Mecanismo da Falha:**  
  `os.path.realpath(target_path)` utiliza o diretório de trabalho atual do processo Python (`os.getcwd()`) para expandir caminhos que não comecem com barra ou letra de unidade. Se o `project_root` do `SecurityGuard` apontar para um diretório externo à pasta de execução do GrafoConcierge, passar `"src/main.py"` resulta no caminho `C:\Nexus-Memory\GrafoConcierge\src\main.py`, que não começa com `C:\ExternalProject\Workspace`.
- **Impacto no Sistema:**  
  Agentes que utilizam caminhos relativos ao projeto para operações de arquivo sofrem falso bloqueio de segurança (`GatingViolationException`) sempre que o projeto inspecionado estiver fora do CWD do servidor.
- **Correção Conceitual Sugerida (Fase 3):**  
  Ancorar caminhos relativos explicitamente ao `project_root`:
  ```python
  if not os.path.isabs(target_path):
      target_path = os.path.join(self.project_root, target_path)
  absolute_target = os.path.realpath(target_path)
  ```

---

### Achado #5 — Falsos Positivos em `warning_terms` por Substring Match Ingênuo

- **Mecanismo da Falha:**  
  A lista `warning_terms` contém `"build"`. O teste `any(term in command for term in self.warning_terms)` testa continência simples de substring dentro da linha de comando completa.
- **Impacto no Sistema:**  
  Qualquer comando ordinário que contenha a palavra "build" (ex: inspecionar commits via `git log --grep="build"`, ler scripts auxiliares `cat build.py`, alternar para branches `git checkout build-fix`) é indevidamente rotulado como `WARNING`. No modo `ask`, o fluxo do agente é interrompido e exige intervenção manual no console terminal.
- **Correção Conceitual Sugerida (Fase 3):**  
  Utilizar casamento por palavras inteiras com limites de expressão regular (`r"\bbuild\b"`) ou analisar especificamente o comando/subcomando executado.

---

## 4. Saída Bruta da Reprodução Executada

Script executado: `scratch/reproduce_security_guard_findings.py`

```text
======================================================================
REPRODUCAO DOS ACHADOS — core/security_guard.py
======================================================================

--- ACHADO 1 (CRITICA): Evasao da Blacklist de Comandos Destrutivos ---
[SAFE] Command: 'rm -fr /' (Flags invertidas (-fr))
[SAFE] Command: 'rm -r -f /' (Flags separadas (-r -f))
[SAFE] Command: 'rm -f -r /' (Flags separadas (-f -r))
[SAFE] Command: 'rm --recursive --force /' (Flags longas GNU rm)
[SAFE] Command: 'rm -rf .' (Destruicao do diretorio corrente)
[SAFE] Command: 'rm -rf *' (Destruicao de todo o conteudo corrente)
[SAFE] Command: 'del /f /s /q C:\*' (Comando nativo Windows de destruicao)
[SAFE] Command: 'format C: /fs:NTFS' (Formatacao de particao Windows)
[SAFE] Command: 'shred -u /dev/sda' (Comando Linux de destruicao de disco)

--- ACHADO 2 (ALTA): classify_command(None) lanca TypeError ---
SUCESSO NA REPRODUCAO: TypeError lancado ao passar None: expected string or bytes-like object, got 'NoneType'

--- ACHADO 3 (MEDIA): Bug do Separador Duplo em Raiz de Disco / Filesystem ---
project_root: 'C:\'
Prefix checked: 'C:\\'
target_path: 'C:\test_folder\file.txt'
is_safe_path result: False

--- ACHADO 4 (MEDIA): Caminho Relativo Ancorado ao CWD em vez de project_root ---
CWD do processo: 'C:\Nexus-Memory\GrafoConcierge'
project_root configurado: 'C:\ExternalProject\Workspace'
caminho relativo testado: 'src\app.py'
os.path.realpath resolveu para: 'C:\Nexus-Memory\GrafoConcierge\src\app.py'
is_safe_path('src\app.py') -> False

--- ACHADO 5 (BAIXA): Falsos Positivos em warning_terms ('build') ---
[WARNING] Command: 'git log --grep='build''
[WARNING] Command: 'cat build.py'
[WARNING] Command: 'git checkout build-fix'
[WARNING] Command: 'python -m build_tools.check'
[WARNING] Command: 'echo rebuilding index'
[WARNING] Command: 'ls -la build/'

======================================================================
TODOS OS 5 ACHADOS REPRODUZIDOS COM SUCESSO!
======================================================================
```

---

## 5. Arquivos de Teste Relacionados

- [`tests/test_adaptive_gating.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_adaptive_gating.py):
  - `TestSecurityGuardBounds`: testa caminhos relativos e absolutos simples com `project_root="."`. Não testa raízes de volume (`C:\`, `/`) nem divergência entre CWD e `project_root`.
  - `TestSecurityGuardCommandClassifier`: testa apenas os exemplos exatos contemplados pela regex (`rm -rf /`, `npm install`, `ls -la`). Não testa permutações de flags, comandos Windows, `None` ou termos contidos em argumentos de texto.
  - Resultado: 12 passed em 0.023s.
- [`tests/test_agent_hsm_coupling.py`](file:///c:/Nexus-Memory/GrafoConcierge/tests/test_agent_hsm_coupling.py):
  - Instancia `SecurityGuard` para validar integração com o HSM e GatingInterceptor no modo `plan-only`.
  - Resultado: 13 passed em 0.759s.
