# Guia de Migração — Grafo Concierge v3.8.0 (Absolute Solidity)

## Visão Geral

Este guia explica como migrar projetos existentes para o Grafo Concierge v3.8.0 (Concierge Core — Absolute Solidity), incluindo a migração de dados e os novos módulos.

---

## Cenários de Migração

### Cenário 1: Novo Projeto

Não há migração necessária — o projeto será registrado, ingerido e receberá um `.concierge_id` automaticamente.

```bash
# 1. Registre o projeto (gera UUID e .concierge_id)
grafo-concierge register /projetos/novo-projeto --wing "gestão/saas"

# 2. Ingira os arquivos (classificação automática)
grafo-concierge mine <UUID> --source /projetos/novo-projeto

# 3. Inicie a sessão (pré-carrega contexto)
grafo-concierge wake-up <UUID>
```

### Cenário 2: Projetos Existentes (sem Grafo Concierge)

Projetos que já existem no filesystem mas nunca foram registrados.

```bash
# Registre (gera .concierge_id na raiz)
grafo-concierge register /projetos/vortex-pro --wing "gestão/saas"

# Ingira os arquivos existentes
grafo-concierge mine <UUID> --source /projetos/vortex-pro

# O mine automaticamente:
# 1. Escaneia o diretório
# 2. Classifica cada arquivo (code, doc, config, conversation)
# 3. Aplica tags de metadados
# 4. Gera embeddings no backend vetorial
# 5. Cria nós no grafo SQLite
```

### Cenário 3: Projetos da v3.7 → v3.8.0

Se você já tem projetos registrados na v3.7:

```bash
# 1. Atualize o schema SQLite (adiciona 'privacy_level' na tabela projects)
grafo-concierge upgrade-db

# 2. Defina os níveis de privacidade dos seus projetos
grafo-concierge set-privacy vortex-pro "INTERNAL"

# 3. Re-ingira os arquivos com a versão v3.8.0 para aplicar Escudo de Sanitização XML
grafo-concierge mine <UUID> --source /projetos/vortex-pro
```

### Cenário 4: Importação em Lote (CSV/JSON)

```python
from core.middleware import GrafoConcierge
import csv

gc = GrafoConcierge(vector_backend="chroma")

with open('projetos.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        uuid = gc.register_project(
            project_path=row['path'],
            wing=row['wing']
        )
        # Ingestão automática
        gc.mine(uuid, row['path'])
        print(f"Registrado e ingerido: {row['path']} → UUID: {uuid}")
```

---

## Passo a Passo: Migração Completa

### 1. Inventário de Projetos Existentes

```bash
ls -la /projetos/
# vortex-pro/
# the-sovereign/
# insighthr/
# omnisched/
```

### 2. Inicialize o Grafo Concierge

```bash
# Inicialize com backend vetorial
grafo-concierge init --data-dir ~/.grafo-concierge --backend chroma
```

### 3. Registre os Projetos (Gera UUID + `.concierge_id`)

```bash
grafo-concierge register /projetos/vortex-pro --wing "gestão/saas"
grafo-concierge register /projetos/the-sovereign --wing "marketing/vendas"
grafo-concierge register /projetos/insighthr --wing "gestão/saas"
grafo-concierge register /projetos/omnisched --wing "gestão/saas"
```

### 4. Ingira os Arquivos (`concierge mine`)

> **Nota**: Todos os comandos CLI aceitam tanto o **UUID** quanto o **folder_name** do projeto. O sistema resolve automaticamente via `SELECT uuid FROM projects WHERE uuid = ? OR folder_name = ?`.

```bash
# Ingestão inteligente para cada projeto (usando folder_name por conveniência)
grafo-concierge mine vortex-pro --source /projetos/vortex-pro
grafo-concierge mine the-sovereign --source /projetos/the-sovereign
grafo-concierge mine insighthr --source /projetos/insighthr
grafo-concierge mine omnisched --source /projetos/omnisched

# Equivalente usando UUID:
# grafo-concierge mine e4b3c2a1-... --source /projetos/vortex-pro
```

### 5. Configure as Alas Híbridas

```bash
# Primary Wings já foram definidas no passo 3

# Adicione Reference Wings para projetos interdisciplinares
grafo-concierge add-ref-wing vortex-pro "finanças/quant"
grafo-concierge add-ref-wing insighthr "automação/rh"
```

### 6. Teste a Integração

```bash
# Wake-up (pré-carrega contexto)
grafo-concierge wake-up vortex-pro

# Resumo
grafo-concierge resume vortex-pro

# Busca Híbrida
grafo-concierge search "autenticação" --project vortex-pro

# Similares
grafo-concierge similar vortex-pro
```

### 7. Configure o MCP (opcional)

```bash
# Inicie o servidor MCP
grafo-concierge serve --transport stdio

# Ou configure no Claude Desktop / Cursor (veja api.md)
```

---

## O que o `.concierge_id` contém

```
e4b3c2a1-7f8d-4e9a-b2c3-d4e5f6a7b8c9
```

**Regras:**
- UUID v4, imutável após criação
- Nunca deve ser editado manualmente
- Deve ser versionado no Git (não adicionar ao `.gitignore`)
- Se perdido: `grafo-concierge repair` regenera com novo UUID

---

## O que o `concierge mine` faz

| Etapa | Descrição |
|-------|-----------|
| 1. Scan | Escaneia o diretório recursivamente |
| 2. Delta Check | Verifica o Hash SHA256 do arquivo para evitar re-processamento |
| 3. Chunking & Tagging | Divide arquivos usando AST/Semantic Chunking (respeitando lógica) e aplica tags automáticas |
| 4. Embedding | Gera embeddings com payload `project_uuid` e `node_type` (v3.6) |
| 5. Indexação | Cria nós no grafo SQLite com arestas estruturais e semânticas |
| 6. Garbage Collection | Limpa arquivos deletados (seguro: ignora diretórios via `type='file'`) |
| 7. Agregação (Busca) | Garante que múltiplos chunks retornem apenas 1 nó (v3.4) |

**Classificação automática:**

| Extensão | Tipo | Tags detectadas |
|---------|------|----------------|
| `.py`, `.js`, `.ts`, `.go`, `.rs` | `code` | Linguagem, frameworks, imports |
| `.md`, `.txt`, `.rst` | `doc` | Tópicos, seções |
| `.json`, `.yaml`, `.toml`, `.env` | `config` | Chaves, valores |
| `.log`, `.chat` | `conversation` | Participantes, datas |

---

## O que o `concierge wake-up` faz

| Etapa | Dados carregados | Tokens |
|-------|-----------------|--------|
| 1. Bússola | Resumo do projeto ativo | 200-300 |
| 2. Reference Wings | Resumos das alas referenciadas | 50-150 |
| 3. Últimos commits | 3 commits mais recentes do `commit_log` | 50-100 |
| **Total** | **Contexto completo pré-carregado** | **300-500** |

---

## Mantendo Histórico

| Dado | Como Migrar | Observação |
|------|-------------|-----------|
| Nome do projeto | `folder_name` na tabela `projects` | Automático |
| Primary Wing | Definida no `register` | Obrigatório |
| Reference Wings | Via `add-ref-wing` | Opcional |
| Tecnologias | Detectadas pelo `mine` | Automático |
| Tags | Detectadas pelo `mine` | Automático |
| Embeddings | Gerados pelo `mine` | Automático |
| Histórico de commits | Construído a partir do primeiro `commit_memory` | Automático |
| Trajetórias Episódicas | Adicionado em falhas/correções no `commit_memory` | Novo (v3.6) |

---

## Rollback

```bash
# Ghost Mode (mantém histórico)
grafo-concierge delete vortex-pro --mode parcial

# Remoção total
grafo-concierge delete vortex-pro --mode total

# Reregistre
grafo-concierge register /projetos/vortex-pro --wing "gestão/saas"
grafo-concierge mine vortex-pro --source /projetos/vortex-pro
```

---

## Problemas Comuns

### Problema: "Projeto não encontrado"
```bash
grafo-concierge register /projetos/vortex-pro --wing "gestão/saas"
```

### Problema: "Ala incorreta"
```bash
grafo-concierge set-wing vortex-pro "gestão/saas"
```

### Problema: ".concierge_id ausente"
```bash
grafo-concierge repair /projetos/vortex-pro
```

### Problema: "Busca retorna vazia"
```bash
# Verifique se o mine foi executado
grafo-concierge mine vortex-pro --source /projetos/vortex-pro
```

### Problema: "Lentidão na ingestão (FTS5)"
```sql
-- Caso os triggers tornem o 'mine' lento em projetos gigantes,
-- desabilite-os e rode o rebuild manual:
INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');
```

---

## Checklist de Migração

- [ ] Inicializar Grafo Concierge (`init --backend chroma`)
- [ ] Registrar projetos (`register`) — gera `.concierge_id`
- [ ] Ingerir arquivos (`mine`) — classifica, tagueia, indexa
- [ ] Definir Primary Wings
- [ ] Configurar Reference Wings (se aplicável)
- [ ] Testar wake-up (pré-carga de sessão)
- [ ] Testar resumos (Bússola de Contexto)
- [ ] Testar Busca Híbrida (`search`)
- [ ] Configurar MCP (se usando Claude Desktop / Cursor)
- [ ] Integrar com Módulos Operacionais (hooks no Agente Executor)
- [ ] Verificar `.concierge_id` no Git

---

## Próximos Passos

Após migração:

1. Use `wake-up` no início de cada sessão
2. Use `mine` após alterações significativas
3. Use `search` para busca híbrida com Strict Scoping
4. Use `commit` para registrar resultados auditados
5. Monitore economia de tokens por fase

---

**Versão**: 3.8.0 (Absolute Solidity)
**Data**: 2026-05-03
**Autor**: LuisinTheLegend