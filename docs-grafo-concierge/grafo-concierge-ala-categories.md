# Ala Categories — Categorização de Projetos (v3.8.0 Absolute Solidity)

## Visão Geral

Cada projeto no Grafo Concierge é categorizado em uma **Ala (Wing)**. Isso garante:

1. **Isolamento de contexto** — Projetos de áreas diferentes não misturam contexto
2. **Strict Scoping** — Buscas híbridas são fisicamente restritas à Primary Wing por padrão
3. **Encontrabilidade** — Facilita identificar projetos similares
4. **Recomendação** — O grafo pode sugerir ideias de outras alas via Reference Wings

---

## Alas Pré-definidas

| Ala (Wing) | Descrição | Palavras-chave |
|-----------|-----------|---------------|
| **marketing/vendas** | Projetos de marketing, vendas e conversão | marketing, venda, copy, conversão, landing, promo |
| **finanças/quant** | Projetos financeiros e quantitativos | finanças, quant, trade, investimento, ações, crypto |
| **gestão/saas** | Projetos de gestão e SaaS | saas, dashboard, gestão, ERP, RH |
| **automação/rh** | Automação e recursos humanos | automação, excel, planilha, RH, workflow |
| **estatística** | Projetos estatísticos e análise de dados | estatística, análise, dados, média, probabilidade |
| **geral** | Projetos que não se encaixam em alas específicas | — |

---

## Sistema de Alas Híbridas

### Primary Wing (Ala Primária)

Todo projeto possui exatamente **uma** Primary Wing. Ela provê o isolamento central e é o alvo padrão do Strict Scoping na Busca Híbrida v4.

- Armazenada na coluna `primary_wing` da tabela `projects` do SQLite
- O Strict Scoping restringe buscas a esta ala por padrão
- Buscas por `find_similar_projects()` priorizam projetos da mesma Primary Wing
- Gavetas de dados brutos só são acessadas dentro da mesma ala

### Reference Wings (Alas de Referência)

Um projeto pode ter **zero ou mais** Reference Wings. Elas funcionam como **arestas de consulta semântica** — permitem à IA acessar **resumos e metadados** de outras alas sem misturar os arquivos brutos.

**Exemplo prático:**
- Projeto "Vortex Pro" tem Primary Wing = `gestão/saas`
- Mas consulta dados financeiros → Reference Wing = `finanças/quant`
- A IA pode ler o **resumo** de projetos de `finanças/quant` para sugestões
- A IA **não** carrega as gavetas brutas daquela ala (isolamento preservado)

> **Nota Crítica (v3.8.0) — Barreira de Contaminação:** Reference Wings estão sujeitas aos `privacy_levels` do projeto referenciado. O Revisor Crítico bloqueará cruzamento de dados de projetos marcados como `RESTRICTED` para dentro de projetos `PUBLIC`, evitando contaminação inter-dominial acidental.

**Armazenamento:** Tabela `reference_wings` do SQLite (FK para `projects.uuid`).

### Strict Scoping (Filtro Físico)

O Strict Scoping é um filtro **físico** (não lógico) que restringe os resultados da Busca Híbrida v4:

| Parâmetro | Escopo | Uso |
|----------|--------|-----|
| Padrão | Apenas Primary Wing | Operação normal |
| `include_references=True` | Primary + Reference Wings | Busca interdisciplinar |
| `all_wings=True` | Todas as alas | Exploração global |

```python
# Strict Scoping ativo (padrão)
results = gc.hybrid_search("autenticação JWT", project_id=uuid)
# → Busca APENAS na ala "gestão/saas"

# Incluindo Reference Wings
results = gc.hybrid_search("autenticação JWT", project_id=uuid, include_references=True)
# → Busca em "gestão/saas" + "finanças/quant"

# Global (todas as alas)
results = gc.hybrid_search("autenticação JWT", project_id=uuid, all_wings=True)
# → Busca em TODAS as alas
```

### Diferença entre Primary e Reference

| Aspecto | Primary Wing | Reference Wing |
|---------|-------------|----------------|
| Quantidade | Exatamente 1 | Zero ou mais |
| Isolamento | Total (dados brutos + grafo) | Parcial (só resumos e arestas) |
| Strict Scoping | Incluída por padrão | Só com `include_references=True` |
| Tabela SQLite | `projects.primary_wing` | `reference_wings` |
| Reranking | Candidatos diretos (Auditor de Evolução) | Candidatos secundários |

---

## Como a Categorização Funciona

### 1. Análise Automática

O sistema analisa o projeto e detecta palavras-chave:

```python
PROJECT_KEYWORDS = {
    "marketing/vendas": ["marketing", "venda", "copy", "CTA", "conversão", "landing"],
    "finanças/quant": ["finança", "quant", "trade", "ação", "crypto", "investimento"],
    "gestão/saas": ["saas", "dashboard", "gestão", "erp", "admin"],
    "automação/rh": ["automação", "excel", "planilha", "rh", "workflow"],
    "estatística": ["estatística", "análise", "dados", "média", "probabilidade"]
}
```

### 2. Override Manual

```bash
# Via CLI — Primary Wing
grafo-concierge set-wing e4b3c2a1-... "gestão/saas"

# Via CLI — Adicionar Reference Wing
grafo-concierge add-ref-wing e4b3c2a1-... "finanças/quant"

# Via API
from core.project_index import ProjectIndex

pi = ProjectIndex()
pi.set_wing_override("e4b3c2a1-...", "gestão/saas")
pi.add_reference_wing("e4b3c2a1-...", "finanças/quant")
```

---

## Criando Novas Alas

### Via Configuração

```json
// ~/.grafo-concierge/config.json
{
    "wings": {
        "devops/infra": {
            "description": "Projetos de infraestrutura e DevOps",
            "keywords": ["docker", "kubernetes", "ci/cd", "deploy", "infra"]
        }
    }
}
```

### Considerações

- Evite criar muitas Alas (máximo 10-12)
- Cada Ala deve ter palavras-chave distintivas
- Mantenha consistência na categorização

---

## Exemplos de Categorização

| Projeto | Primary Wing | Reference Wings | Justificativa |
|---------|-------------|-----------------|---------------|
| Zero Riscos | marketing/vendas | — | "marketing", "venda", "copy" |
| Robô de DayTrade | finanças/quant | estatística | "trade", "ação" + análise estatística |
| Mentor.IA | gestão/saas | automação/rh | "saas", "dashboard" + automação de fluxos |
| Módulo Executor | gestão/saas | — | Módulo Operacional (Skill) para execução |
| Excel Automation | automação/rh | — | "automação", "excel", "workflow" |
| Lotofácil | estatística | finanças/quant | "estatística", "análise" + contexto financeiro |
| GueberMansWear | gestão/saas | marketing/vendas | "e-commerce", "gestão" + marketing digital |

---

## Isolamento de Contexto com Busca Híbrida

A categorização alimenta o Strict Scoping da Busca Híbrida v4:

```python
from core.middleware import GrafoConcierge

gc = GrafoConcierge()

# Busca na Primary Wing apenas (Strict Scoping ativo — padrão)
similar = gc.find_similar_projects("e4b3c2a1-...", limit=5)
# Retorna apenas projetos da mesma Primary Wing

# Busca incluindo Reference Wings
similar = gc.find_similar_projects("e4b3c2a1-...", limit=5, include_references=True)
# Retorna projetos da Primary Wing + Reference Wings

# Busca em todas as Alas (explícito)
similar = gc.find_similar_projects("e4b3c2a1-...", limit=5, all_wings=True)
# Retorna projetos de todas as alas
```

---

## Boas Práticas

1. **Categorize manualmente** projetos importantes
2. **Mantenha palavras-chave precisas** para detecção automática
3. **Não crie muitas Alas** — limite a 8-10
4. **Revise categorizações** periodicamente
5. **Use Reference Wings** para projetos interdisciplinares em vez de trocar a Primary Wing
6. **Confie no Strict Scoping** — Reference Wings só expõem resumos, nunca dados brutos
7. **Aproveite o Reranking** — mesmo com Reference Wings ativas, o Auditor de Evolução filtra ruído

---

**Versão**: 3.8.0 (Absolute Solidity)
**Data**: 2026-05-03
**Autor**: LuisinTheLegend