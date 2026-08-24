# 🧬 Active-SDD #15: Remoção da Dependência do NumPy no Thompson Sampling

## 🗺️ 1. Identificação e Propósito
* **ID da Especificação:** `SDD-SURVIVAL-15`
* **Módulo de Destino:** `core/probabilistic_retriever.py` (ou módulo de rankeamento e busca probabilística correspondente, como `core/search.py` ou `core/ranker.py`)
* **Arquivos de Dependências:** `requirements.txt` e `pyproject.toml`
* **Arquivo de Teste Relacionado:** `tests/test_probabilistic_retriever.py` (ou correspondente ao ranker)
* **Objetivo Principal:** Eliminar completamente a dependência de terceiros `numpy` (~30MB) do nosso ecossistema de memória local-first. Substituiremos o cálculo da distribuição Beta usado no **Thompson Sampling** por uma solução nativa utilizando a biblioteca padrão do Python (`random.betavariate()`). Isso enxuga drasticamente o tamanho do instalador e o consumo de disco do Grafo Concierge, mantendo a exata equivalência matemática e precisão estatística do ranqueamento.

---

## 🔍 2. Análise de Impacto de Segunda Ordem (Análise de Riscos)

A substituição de uma biblioteca matemática robusta por funções nativas requer atenção especial aos seguintes pontos:

*   **Risco de Incompatibilidade de Tipos (Arrays vs Listas):** O `numpy` lida nativamente com arrays de dados e operações vetorizadas de alta performance em C. Se o algoritmo de Thompson Sampling realizava amostragem paralela de um vetor inteiro de uma vez (como `np.random.beta(alpha_array, beta_array)`), tentar passar listas normais do Python para uma função escalar do `random` causará erros de tipo (`TypeError`).
    *   *Mitigação:* Como o Thompson Sampling no Grafo Concierge opera iterando sobre um conjunto limitado de documentos ou nós candidatos para calcular o score probabilístico individual de cada um, a amostragem escalar é ideal. Substituiremos chamadas vetorizadas por list comprehensions simples ou laços `for` que chamam `random.betavariate(alpha, beta)` para cada nó. Isso preserva a simplicidade e garante compatibilidade perfeita sem perdas de desempenho mensuráveis em listas de candidatos normais (< 1000 itens).
*   **Risco de Quebra na Geração de Sementes Aleatórias (Seeds):** Se o sistema de testes ou o orquestrador de busca dependia de `np.random.seed()` para gerar resultados determinísticos reproduzíveis em testes unitários, a remoção do NumPy quebrará o comportamento desses testes.
    *   *Mitigação:* Migrar qualquer configuração de semente aleatória nos arquivos de teste e de produção de `np.random.seed(seed)` para o equivalente da biblioteca padrão: `random.seed(seed)`.

---

## ⚙️ 3. Contrato de Funcionamento e Especificação

### 3.1. Equivalência Matemática do Thompson Sampling

O Thompson Sampling para ranqueamento probabilístico de itens baseado em utilidade histórica (cliques, uso em respostas, etc.) calcula para cada nó uma amostra da distribuição Beta:

\\[\theta \sim \text{Beta}(\alpha, \beta)\\]

Onde:
*   \\(\alpha\\) representa o número de sucessos (utilidade comprovada do nó).
*   \\(\beta\\) representa o número de falhas ou ociosidade.

#### Substituição de Código Conceitual:

**Antes (Usando NumPy):**
```python
import numpy as np

def calculate_thompson_score(alpha: float, beta: float) -> float:
    # Retorna uma amostra probabilística usando NumPy
    return np.random.beta(alpha, beta)
Depois (Solução Frugal Nativa):
import random

def calculate_thompson_score(alpha: float, beta: float) -> float:
    # Garante parâmetros estritamente válidos para a distribuição Beta (alpha > 0, beta > 0)
    safe_alpha = max(alpha, 1e-5)
    safe_beta = max(beta, 1e-5)
    return random.betavariate(safe_alpha, safe_beta)
3.2. Purga de Dependências
O desenvolvedor deverá remover qualquer linha correspondente ao pacote numpy dos arquivos de configuração de dependências do projeto:
requirements.txt: Remover a linha contendo numpy ou numpy>=...
pyproject.toml: Remover "numpy" da lista de dependências (dependencies ou install_requires).
🧪 4. Suíte de Testes TDD (tests/test_probabilistic_retriever.py)
Esta suíte garante que a geração de scores probabilísticos usando a biblioteca padrão gera distribuições estatisticamente equivalentes às anteriores, mantendo a lógica de negócio intacta:
import unittest
import random
from core.probabilistic_retriever import calculate_thompson_score  # Ajustar caminho físico real se necessário

class TestProbabilisticRetriever(unittest.TestCase):
    def setUp(self):
        # Define semente para garantir testes reproduzíveis
        random.seed(42)

    def test_thompson_score_equivalence_and_boundaries(self):
        """Valida que o cálculo do score com random.betavariate se comporta dentro dos limites normais"""
        # A distribuição Beta sempre gera valores no intervalo [1]
        for _ in range(100):
            score = calculate_thompson_score(2.0, 5.0)
            self.assertTrue(0.0 <= score <= 1.0)

    def test_thompson_score_utility_tendency(self):
        """Valida se itens com maior utilidade (alpha alto) tendem a pontuar mais alto estatisticamente"""
        high_utility_scores = [calculate_thompson_score(100.0, 10.0) for _ in range(500)]
        low_utility_scores = [calculate_thompson_score(10.0, 100.0) for _ in range(500)]
        
        avg_high = sum(high_utility_scores) / len(high_utility_scores)
        avg_low = sum(low_utility_scores) / len(low_utility_scores)
        
        # Itens de alta utilidade devem ter médias estatísticas muito superiores
        self.assertGreater(avg_high, avg_low)
        self.assertTrue(avg_high > 0.8)
        self.assertTrue(avg_low < 0.2)

    def test_robustness_near_zero_parameters(self):
        """Valida se o cálculo lida graciosamente com valores nulos ou negativos nos parâmetros alpha/beta"""
        # Parâmetros <= 0 causariam erro no random.betavariate nativo se não sanitizados
        try:
            score_zero = calculate_thompson_score(0.0, 0.0)
            score_neg = calculate_thompson_score(-1.0, -5.0)
            self.assertTrue(0.0 <= score_zero <= 1.0)
            self.assertTrue(0.0 <= score_neg <= 1.0)
        except ValueError as e:
            self.fail(f"O método calculate_thompson_score falhou ao lidar com parâmetros inválidos: {str(e)}")

---