# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.
O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [Unreleased]

### Quebras de Compatibilidade (Breaking Changes) — Desacoplamento de Domínio ([F4-030])

Em conformidade com o propósito central do **Grafo Concierge** (ser uma ferramenta de memória neutra quanto a domínio, confiável e honesta sobre o que sabe e o que não sabe), a Rodada 4.4 eliminou taxonomias fixas hardcoded e heurísticas de autocategorização que alteravam arbitrariamente a categorização definida pelo usuário.

Abaixo estão detalhadas as três quebras de compatibilidade introduzidas:

---

#### 1. Parâmetro `auto_categorize` removido de `GrafoConcierge.mine`

- **O que era:**  
  A assinatura do método `GrafoConcierge.mine` continha o parâmetro booleano opcional `auto_categorize: bool = True`:
  ```python
  def mine(self, file_path: str, wing: Optional[str] = None, auto_categorize: bool = True) -> Dict[str, Any]:
  ```
  Quando mantido como `True` (o padrão), qualquer mineração bem-sucedida invocava heurísticas de autocategorização que sobrescreviam silenciosamente a ala primária (`primary_wing`) do projeto no banco de dados.

- **O que virou:**  
  O parâmetro `auto_categorize` foi completamente removido da assinatura:
  ```python
  def mine(self, file_path: str, wing: Optional[str] = None) -> Dict[str, Any]:
  ```
  A mineração agora foca estritamente em analisar e indexar o código-fonte, preservando a ala atribuída pelo usuário no momento do cadastro ou configuração de estado.

- **Exemplo de código antes:**
  ```python
  from core.middleware import GrafoConcierge

  concierge = GrafoConcierge(config=config)
  # Chamada anterior especificando explicitamente auto_categorize
  resultado = concierge.mine("services/payment.py", wing="financeiro", auto_categorize=True)
  ```

- **Exemplo de código depois:**
  ```python
  from core.middleware import GrafoConcierge

  concierge = GrafoConcierge(config=config)
  # Chamada atual sem o parâmetro auto_categorize
  resultado = concierge.mine("services/payment.py", wing="financeiro")
  ```

- **Como migrar:**  
  Remova o argumento `auto_categorize` de todas as chamadas a `concierge.mine(...)` em seu código ou scripts de integração. Se invocado posicionalmente como 3º argumento, passe apenas `file_path` e `wing`. A ala primária do projeto agora é soberana e respeita exclusivamente a atribuição explícita realizada pelo usuário ou agente via `concierge_register` ou `concierge_set_state`.

- **Motivo:**  
  Desacoplamento de domínio e garantia da honestidade e neutralidade. O comportamento anterior violava o princípio de menor surpresa ao alterar metadados de projeto sem consentimento ou intenção explícita do usuário.

---

#### 2. Chave `auto_categorized_wing` removida do retorno de `GrafoConcierge.mine`

- **O que era:**  
  O dicionário retornado por `concierge.mine(...)` incluía a chave `"auto_categorized_wing": Optional[str]`, contendo a ala atribuída pela heurística de palavras-chave caso uma reclassificação tivesse ocorrido.

- **O que virou:**  
  A chave `"auto_categorized_wing"` foi eliminada do dicionário de retorno de `mine`. O payload retornado foca estritamente nas métricas e no status do processo de ingestão:
  ```python
  {
      "status": "success",
      "file_path": file_path,
      "nodes_created": count_nodes,
      "edges_created": count_edges,
      "ast_edges_created": count_ast,
      ...
  }
  ```

- **Exemplo de código antes:**
  ```python
  res = concierge.mine("models/customer.py")
  nova_ala = res.get("auto_categorized_wing")
  if nova_ala:
      print(f"Projeto reclassificado para: {nova_ala}")
  ```

- **Exemplo de código depois:**
  ```python
  res = concierge.mine("models/customer.py")
  # A chave auto_categorized_wing não existe mais
  print(f"Status: {res['status']}, Nós criados: {res['nodes_created']}")
  # Para verificar a ala do projeto, consulte concierge_status ou list_projects
  status = concierge.get_status(project_identifier)
  print(f"Ala atual do projeto: {status['primary_wing']}")
  ```

- **Como migrar:**  
  Remova acessos diretos à chave `res["auto_categorized_wing"]` ou `res.get("auto_categorized_wing")`. Se sua aplicação precisa verificar ou consultar a ala primária do projeto, consulte os métodos oficiais de inspeção de estado (`get_status`, `list_projects` ou ferramentas MCP equivalentes).

- **Motivo:**  
  Desacoplamento de domínio. Com o fim da autocategorização embutida na mineração, a presença dessa chave era enganosa e propagava acoplamento a heurísticas legadas.

---

#### 3. Campo `wing_keywords` removido de `ConciergeConfig`

- **O que era:**  
  A classe `ConciergeConfig` (`core/config.py`) possuía o campo `wing_keywords: Dict[str, List[str]]`, pré-populado com um mapa de palavras-chave arbitrário (ex: `"marketing/vendas"`, `"finanças/quant"`, `"gestão/saas"`, `"automação/rh"`, etc.).

- **O que virou:**  
  O campo `wing_keywords` foi completamente removido de `ConciergeConfig`. A classe de configuração não carrega mais nenhum dicionário de taxonomia pré-fixado.

- **Exemplo de código antes:**
  ```python
  from core.config import ConciergeConfig

  config = ConciergeConfig(
      db_path="concierge.db",
      wing_keywords={
          "custom_wing": ["token1", "token2"]
      }
  )
  ```

- **Exemplo de código depois:**
  ```python
  from core.config import ConciergeConfig

  config = ConciergeConfig(
      db_path="concierge.db"
  )
  ```

- **Como migrar:**  
  Remova o argumento `wing_keywords` de chamadas de instanciação de `ConciergeConfig` e quaisquer acessos a `config.wing_keywords`. Se a sua arquitetura necessita de classificação taxonômica personalizada, realize essa gestão na camada externa do agente ou passe a ala desejada diretamente via `concierge_register(..., wing="sua-ala")` ou `add_reference_wing`.

- **Motivo:**  
  Desacoplamento de domínio. A memória do Grafo Concierge deve ser agnóstica em relação ao domínio da aplicação. Taxonomias de negócios pertencem à camada de aplicação ou aos prompts dos agentes, nunca ao núcleo do motor de grafos.
