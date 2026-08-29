# 🧠 Cognitive Memory, Bi-Temporal Facts & Reinforcement (v4.0.0)

> **Architectural Deep-Dive into Bi-Temporal Persistence, Scoped Core Memory, and Bayesian Thompson Sampling**

---

## 1. The Core Memory Challenge in AI Systems

Standard AI memory implementations suffer from three major design flaws:
1. **Destructive Overwriting**: When an architectural decision or user preference changes, naive systems overwrite or delete the old record, destroying historical context and debugging lineage.
2. **Context Window Contamination (Redundancy Bloat)**: Repeating similar facts leads to hundreds of near-identical memories polluting retrieval vectors.
3. **Static Scoring**: Systems rank old and new memories identically, unable to learn whether recalling a specific memory actually helped the agent solve the task.

Grafo Concierge solves these challenges through **Bi-Temporal Fact Invalidation**, **LLM-Driven Semantic Consolidation (`SemanticExtractor`)**, **Scoped Core Memory**, and **Bayesian Thompson Sampling**.

---

## 2. Bi-Temporal Fact Invalidation (`semantic_facts`)

### 2.1 The Two Dimensions of Time
Under Grafo Concierge's bi-temporal architecture, knowledge records track two explicit timestamps:
* **`t_valid`**: The moment in real-world time when the fact became true or active.
* **`t_invalid`**: The moment in real-world time when the fact was revoked, superseded, or proven obsolete. (Null for active facts).

```
   Fact #1: "Use ChromaDB as vector store" (t_valid: Jan 10, t_invalid: Mar 15)  [REVOKED]
   Fact #2: "Migrate from ChromaDB to Qdrant" (t_valid: Mar 15, t_invalid: NULL) [ACTIVE]
```

### 2.2 Relational Representation (SQLite)
```sql
CREATE TABLE semantic_facts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type     TEXT NOT NULL CHECK(scope_type IN ('user', 'session', 'agent', 'org')),
    scope_id       TEXT NOT NULL,
    fact_statement TEXT NOT NULL,
    t_valid        TEXT NOT NULL DEFAULT (datetime('now')),
    t_invalid      TEXT NULL,
    utility_alpha  REAL NOT NULL DEFAULT 1.0,
    utility_beta   REAL NOT NULL DEFAULT 1.0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 2.3 Active vs Historical Queries
* **Active Facts Only**:
  ```sql
  SELECT * FROM semantic_facts
  WHERE scope_type = ? AND scope_id = ? AND t_invalid IS NULL
  ORDER BY id ASC;
  ```
* **Full Temporal Audit Log**:
  ```sql
  SELECT * FROM semantic_facts
  WHERE scope_type = ? AND scope_id = ?
  ORDER BY t_valid ASC;
  ```

---

## 3. The `SemanticExtractor` Decision Pipeline

When a client or agent calls `concierge_store_fact`, the incoming statement passes through the `SemanticExtractor` pipeline (`core/memory_extractor.py`):

```
                        Incoming New Fact Statement
                                    │
                                    ▼
                 Fetch Active Facts for Scope (t_invalid IS NULL)
                                    │
                                    ▼
                      Prompt LLM (Decision Matrix Prompt)
                                    │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
            ┌───────┐            ┌────────┐           ┌────────┐
            │  ADD  │            │ UPDATE │           │ DELETE │
            └───────┘            └────────┘           └────────┘
                │                    │                    │
         Insert new row       1. Invalidate old       Invalidate
         with t_valid=now     (t_invalid=now)         target_id
                              2. Insert consolidated  (t_invalid=now)
                              statement (new ID)
                                    │
                                    ▼ (or NOOP: discard redundancy)
                        Consolidated Memory State
```

### 3.1 The 4 Consolidation Actions

| Action | When it triggers | What happens in SQLite | What happens in Vector Store |
| :--- | :--- | :--- | :--- |
| **`ADD`** | Statement is brand new and unrelated to existing facts. | Inserts new row with `t_valid = now()`, `t_invalid = NULL`. | Generates and stores new embedding. |
| **`UPDATE`** | Statement refines, expands, or updates an existing fact. | 1. Sets `t_invalid = now()` on target fact ID.<br>2. Inserts new row with consolidated statement. | Updates vector document with new consolidated embedding. |
| **`DELETE`** | Statement explicitly contradicts or revokes an existing fact. | Sets `t_invalid = now()` on target fact ID. | Removes or marks vector document as obsolete. |
| **`NOOP`** | Statement is already fully covered or redundant. | **Zero changes** to SQLite. Zero bloat. | No vector generation (saves tokens and I/O). |

### 3.2 Robust Parser with Fallback Regex
Because fast/cheaper models (e.g. Gemini Flash, Claude Haiku) occasionally return markdown-wrapped JSON or malformed brackets, `SemanticExtractor` implements a 3-tier fallback parser:
1. `json.loads(text)` (Clean direct JSON)
2. Regex scan for `{...}` blocks
3. Outer delimiter substring slicing `text[first_brace:last_brace + 1]`
4. If all parsing fails, it safely falls back to a clean `ADD` without crashing the agent session.

---

## 4. Scoped Core Memory (`user_core_memory`)

While semantic facts represent granular, bi-temporal assertions, **Core Memory Blocks** provide structured key-value scratchpads for persistent agent state across conversations.

### 4.1 Scope Levels
1. **`user`**: Long-term user preferences, communication style, timezone, permissions.
2. **`session`**: Short-term goals and sprint objectives for the active session.
3. **`agent`**: Agent persona, system instructions, and specialized tool guidelines.
4. **`org`**: Enterprise-wide coding standards, repo conventions, and compliance rules.

### 4.2 Relational Schema
```sql
CREATE TABLE user_core_memory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_type    TEXT NOT NULL CHECK(scope_type IN ('user', 'session', 'agent', 'org')),
    scope_id      TEXT NOT NULL,
    block_label   TEXT NOT NULL,
    content       TEXT,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(scope_type, scope_id, block_label)
);
```

### 4.3 Atomic Upsert
Using SQLite's `ON CONFLICT` clause, `set_core_memory` guarantees atomic updates:
```sql
INSERT INTO user_core_memory (scope_type, scope_id, block_label, content, updated_at)
VALUES (?, ?, ?, ?, datetime('now'))
ON CONFLICT(scope_type, scope_id, block_label)
DO UPDATE SET content = excluded.content, updated_at = datetime('now');
```

---

## 5. Bayesian Thompson Sampling & Reinforcement (`probabilistic_retriever.py`)

To prevent the retrieval engine from getting stuck in local optima (repeatedly recalling the same high-similarity memory even when newer or alternative memories are more helpful), Grafo Concierge implements **Thompson Sampling (SA-CTS)**.

### 5.1 The Mathematical Model
Each semantic fact maintains two Bayesian utility counters:
* $\alpha$ (`utility_alpha`): Number of times recalling this fact led to a successful agent outcome (default: 1.0).
* $\beta$ (`utility_beta`): Number of times recalling this fact was irrelevant or failed (default: 1.0).

During retrieval with `enable_probabilistic=True`:
1. Candidate facts are retrieved via semantic vector similarity: $\text{Sim}(q, d)$.
2. A probabilistic multiplier is sampled from the Beta distribution:
   $$\text{Multiplier} \sim \text{Beta}(\alpha, \beta)$$
3. The final ranking score is:
   $$\text{Final Score} = \text{Sim}(q, d) \times \text{Multiplier}$$

```
                ┌────────────────────────────────────────────────────────┐
                │        Thompson Sampling Beta Multiplier (0.0 to 1.0)  │
                ├────────────────────────────────────────────────────────┤
                │ α=10, β=1 (High utility)  ──► Distribution peaks near 0.9 │
                │ α=1, β=1  (Unexplored)    ──► Uniform distribution [0,1]│
                │ α=1, β=10 (Low utility)   ──► Distribution peaks near 0.1 │
                └────────────────────────────────────────────────────────┘
```

### 5.2 Zero-NumPy Frugal Implementation (`random.betavariate`)
Under **Active-SDD #15**, Grafo Concierge completely eliminated the external `numpy` library (~30MB footprint) from its probabilistic ranking engine.

Instead, sampling executes via Python's standard library `random.betavariate()` with defensive input sanitization:

```python
@staticmethod
def sample_multiplier(alpha: float, beta: float) -> float:
    """Samples a probabilistic multiplier using Python's native Beta Distribution.

    Parameters are sanitized with max(val, 1e-5) to guarantee strictly
    positive values as required by random.betavariate (SDD-15).
    """
    safe_alpha = max(alpha, 1e-5)
    safe_beta = max(beta, 1e-5)
    return random.betavariate(safe_alpha, safe_beta)
```

**Benefits**:
* **Zero Overhead**: Identical statistical properties without loading massive C-extensions in RAM.
* **Resilient**: Safely handles zero or negative utility edge cases without crashing (`ValueError`).
* **Deterministic Testing**: Fully reproducible via `random.seed(seed)`.

### 5.3 The Agent Feedback Loop (`concierge_feedback`)
Agents or IDE hooks close the learning loop by submitting feedback after completing tasks:
* `concierge_feedback(fact_id=21, was_useful=True)`:
  $$\alpha \leftarrow \alpha + 1.0$$
* `concierge_feedback(fact_id=21, was_useful=False)`:
  $$\beta \leftarrow \beta + 1.0$$

Over time, the memory graph automatically optimizes its retrieval distribution to the specific workflows of the development team.

---

## 6. Durable FSM Checkpoints & Cognitive Time-Travel (`core/checkpointer.py`)

Under **Active-SDD #20**, Grafo Concierge extends state persistence into durable SQLite WAL tables, enabling resilient session recovery and non-destructive rollbacks across agent execution phases.

### 6.1 Relational Schema (`storage/relational_db.py`)
```sql
CREATE TABLE IF NOT EXISTS fsm_checkpoints (
    session_id    TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    state_blob    TEXT NOT NULL,      -- Recursively sanitized JSON snapshot
    created_at    REAL NOT NULL,      -- Epoch timestamp (time.time())
    dirty_files   TEXT DEFAULT '[]',  -- JSON list of files touched in step
    PRIMARY KEY (session_id, checkpoint_id)
);
CREATE INDEX IF NOT EXISTS idx_fsm_checkpoints_session_created
    ON fsm_checkpoints(session_id, created_at ASC);
```

### 6.2 Resilient JSON Sanitization (`_sanitize_for_json`)
Autonomous AI agents frequently maintain active locks, generator states, file descriptors, or custom objects inside their state dictionaries. Passing these directly to `json.dumps()` triggers `TypeError: Object is not JSON serializable`.

The `AgnosticCheckpointer` runs recursive sanitization:
* Primitives (`str`, `int`, `float`, `bool`, `None`): Preserved as-is.
* Containers (`dict`, `list`, `tuple`, `set`): Recursively traversed and normalized.
* Non-Serializable Objects (`threading.Lock`, `Coroutine`, custom instances): Converted to deterministic string representations (e.g. `"<Lock object at 0x...>"`), allowing 100% of state snapshots to save cleanly without crashing the agent.

### 6.3 Time-Travel Rollback Workflow
When an agent or developer triggers a rollback (`POST /api/checkpoints/time-travel`):
1. **Target Snapshot Retrieval**: Fetches `target_checkpoint_id` from `fsm_checkpoints` for the given `session_id`.
2. **Future State Invalidation**: Automatically executes an atomic deletion of all future checkpoints recorded after the target step:
   ```sql
   DELETE FROM fsm_checkpoints WHERE session_id = ? AND created_at > ?;
   ```
3. **Dirty File Synchronization**: Parses the `dirty_files` array stored in the snapshot and executes `UPDATE files SET is_dirty = 1 WHERE path IN (...)`, instructing the file watcher and background Janitor to immediately re-synchronize local graph state.

---

## 7. Hierarchical Global Memory Adapter (`core/global_memory_adapter.py`)

Under **Active-SDD #22**, the `GlobalMemoryAdapter` eliminates the quadratic token bloat caused by linear raw chat histories while preserving conversational naturalness.

### 7.1 Hybrid Sliding Window Architecture

```
                    Incoming Chat History (N messages)
                                    │
          ┌─────────────────────────┴─────────────────────────┐
          ▼ Messages 1 to N-3                                 ▼ Last 3 Messages
┌───────────────────────────────────────┐           ┌───────────────────────────────────┐
│ Old Conversation History              │           │ Short-Term Memory (STM)           │
│ Podada (Discarded from raw prompt)    │           │ Preserved intact to maintain      │
│ Substituída por LTM estruturado       │           │ pronouns & conversational context │
└───────────────────────────────────────┘           └───────────────────────────────────┘
                    │                                                 │
                    ▼                                                 ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ System Injection Prompt:                                                              │
│ - Anchor instructions                                                                 │
│ - === SUBSTRATO DE MEMÓRIA DE LONGO PRAZO === (From Local GraphRAG / Nozomio Router) │
│ - === HISTÓRICO CONVERSACIONAL DE CURTO PRAZO === (Formatted last 3 messages)        │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Context Compilation Pipeline
* **Short-Term Memory (STM)**: Takes `chat_history[-3:]` to preserve the user's immediate question, the assistant's previous answer, and pronoun references ("fix it", "run this again").
* **Long-Term Memory (LTM)**: Inserts the structured technical substrate retrieved by the `NozomioRouter`:
  ```text
  === SUBSTRATO DE MEMÓRIA DE LONGO PRAZO (Sourced from: LOCAL_GRAPHRAG) ===
  Contexto Recuperado:
  [Local GraphRAG Content] Módulo core/database.py possui in-degree alto.
  
  === HISTÓRICO CONVERSACIONAL DE CURTO PRAZO ===
  Desenvolvedor: Mensagem recente 4
  Agente: Resposta recente 5
  Desenvolvedor: Pergunta atual 6
  ```
* **Impact**: Slashes prompt token consumption by 70–90% across long pair-programming sessions while anchoring the model to the sovereign SQLite graph memory.

