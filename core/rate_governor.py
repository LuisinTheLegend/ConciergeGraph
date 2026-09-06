"""
core/rate_governor.py — SDD-SURVIVAL-23

RateGovernor com Tráfego Prioritário (HTTP 429 Isolation & Queue Freezing).

Thread daemon de controle de taxa com fila de prioridade tripla:
  1 (HIGH)   — Decisões FSM síncronas do Hermes, chat direto com o usuário.
  2 (MEDIUM) — Ferramentas de subagentes, análises não-bloqueantes.
  3 (LOW)    — Consolidações do Janitor, cálculo de comunidades do GraphRAG.

Sob aproximação de estouro de cota (RPM/TPM), o governador congela
reativamente as filas inferiores:
  - LOW congelada se consumo ≥ 85%
  - MEDIUM congelada se consumo ≥ 95%
  - HIGH nunca é congelada

Bypass fast-path: chamadas HIGH com tráfego verde (< 50%) executam
inline em < 1ms sem enfileiramento.

Aging anti-starvation: tarefas LOW paradas por > 5 minutos (configurável)
recebem upgrade temporário para MEDIUM se uso médio cair abaixo de 75%.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)


class PriorityRequest:
    """
    Requisição encapsulada com prioridade, callback de resultado e metadados.

    Prioridades:
      1 = HIGH   (Hermes / Chat Direto)
      2 = MEDIUM (Subagentes)
      3 = LOW    (Janitor / GraphRAG background)
    """

    def __init__(
        self,
        priority: int,
        task_fn: Callable[[], Any],
        timestamp: float,
        session_id: str,
    ):
        self.priority = priority
        self.task_fn = task_fn
        self.timestamp = timestamp
        self.session_id = session_id
        # Canal de resultado síncrono bloqueante: (success: bool, result_or_exc)
        self.future_result: queue.Queue = queue.Queue(maxsize=1)

    def __lt__(self, other: "PriorityRequest") -> bool:
        """Compara por prioridade; em empate, a mais antiga executa primeiro (FIFO)."""
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority < other.priority


class RateGovernor(threading.Thread):
    """
    Thread daemon de governança de taxa com fila de prioridade tripla.

    Parâmetros:
      rpm_limit            — Requisições por minuto permitidas na janela.
      tpm_limit            — Tokens por minuto permitidos na janela.
      check_window_seconds — Tamanho da janela deslizante em segundos.
      aging_threshold_secs — Tempo (s) após o qual uma tarefa LOW sofre
                             upgrade temporário para MEDIUM (anti-starvation).
    """

    def __init__(
        self,
        rpm_limit: int = 60,
        tpm_limit: int = 40000,
        check_window_seconds: int = 60,
        aging_threshold_secs: float = 300.0,
    ):
        super().__init__(daemon=True)
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.window_seconds = check_window_seconds
        self.aging_threshold_secs = aging_threshold_secs

        # Fila de prioridade thread-safe
        self.request_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self.running = True

        # Histórico deslizante para cálculo de cotas: list of (timestamp, tokens_used)
        self.history: List[Tuple[float, int]] = []

        # Flags de congelamento ativo
        self.low_priority_frozen = False
        self.medium_priority_frozen = False

    # ── Registro de Consumo ───────────────────────────────────────

    def report_usage(self, tokens_used: int) -> None:
        """
        Registra uma chamada de API realizada com sucesso e seus tokens consumidos.

        Deve ser invocado pelo executor externo após cada chamada de LLM para
        que as métricas de janela deslizante reflitam o consumo real.
        """
        with self.lock:
            self.history.append((time.time(), tokens_used))
            self._recalculate_frozen_states()

    # ── Métricas de Janela Deslizante ─────────────────────────────

    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Calcula o uso corrente de RPM e TPM dentro da janela móvel.

        Retorna dicionário com:
          - current_rpm, current_tpm (contagens absolutas)
          - rpm_percentage, tpm_percentage (percentuais de ocupação)
          - low_priority_frozen, medium_priority_frozen (flags booleanas)
          - queue_backlog (tamanho da fila pendente)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Limpa registros antigos fora da janela deslizante
        self.history = [item for item in self.history if item[0] >= cutoff]

        current_requests = len(self.history)
        current_tokens = sum(item[1] for item in self.history)

        rpm_pct = (
            (current_requests / self.rpm_limit) * 100 if self.rpm_limit > 0 else 0
        )
        tpm_pct = (
            (current_tokens / self.tpm_limit) * 100 if self.tpm_limit > 0 else 0
        )

        return {
            "current_rpm": current_requests,
            "current_tpm": current_tokens,
            "rpm_percentage": round(rpm_pct, 2),
            "tpm_percentage": round(tpm_pct, 2),
            "low_priority_frozen": self.low_priority_frozen,
            "medium_priority_frozen": self.medium_priority_frozen,
            "queue_backlog": self.request_queue.qsize(),
        }

    # ── Recálculo Interno de Congelamento ─────────────────────────

    def _recalculate_frozen_states(self) -> None:
        """
        Determina o congelamento reativo das filas baseando-se no percentual
        máximo de ocupação entre RPM e TPM.

        Thresholds:
          - ≥ 85% → congela LOW
          - ≥ 95% → congela MEDIUM (LOW já congelada)
          - <  85% → libera ambas
        """
        metrics = self.get_current_metrics()
        max_pct = max(metrics["rpm_percentage"], metrics["tpm_percentage"])

        # Congelamento da fila LOW (Janitor) se ultrapassar 85%
        self.low_priority_frozen = max_pct >= 85.0

        # Congelamento da fila MEDIUM (Subagentes) se ultrapassar 95%
        self.medium_priority_frozen = max_pct >= 95.0

    # ── Submissão de Requisições ──────────────────────────────────

    def submit_request(
        self, priority: int, session_id: str, task_fn: Callable[[], Any]
    ) -> Any:
        """
        Envia uma tarefa para execução controlada no governador.
        Retorna o resultado de forma síncrona/bloqueante para quem chama.

        Bypass fast-path: requisições HIGH com tráfego verde (< 50%) executam
        inline sem passar pela fila daemon, eliminando qualquer lag perceptível.
        """
        # Fast-path: fura a fila instantaneamente se HIGH e tráfego verde
        with self.lock:
            metrics = self.get_current_metrics()
        max_pct = max(metrics["rpm_percentage"], metrics["tpm_percentage"])

        if priority == 1 and max_pct < 50.0:
            # Execução inline síncrona em < 1ms
            result = task_fn()
            return result

        # Enfileira para a thread consumidora daemon
        req = PriorityRequest(priority, task_fn, time.time(), session_id)
        self.request_queue.put(req)

        # Bloqueia aguardando a thread consumidora despachar o resultado
        success, result_or_exc = req.future_result.get()
        if success:
            return result_or_exc
        raise result_or_exc

    # ── Loop Consumidor Daemon ────────────────────────────────────

    def run(self) -> None:
        """
        Consumidor contínuo das filas respeitando o throttling dinâmico.

        Aplica aging anti-starvation: se uma tarefa LOW espera por mais de
        aging_threshold_secs, ela recebe upgrade temporário para MEDIUM
        (desde que o consumo esteja abaixo de 75%).
        """
        while self.running:
            if self.request_queue.empty():
                time.sleep(0.05)
                continue

            # Atualiza flags de congelamento antes de consumir
            with self.lock:
                self._recalculate_frozen_states()

            # Retira o item com maior prioridade (menor número)
            try:
                req = self.request_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # ── Aging anti-starvation ─────────────────────────────
            if req.priority == 3:
                age = time.time() - req.timestamp
                if age >= self.aging_threshold_secs:
                    with self.lock:
                        metrics = self.get_current_metrics()
                    max_pct = max(
                        metrics["rpm_percentage"], metrics["tpm_percentage"]
                    )
                    if max_pct < 75.0:
                        # Upgrade temporário: executa mesmo com LOW frozen
                        logger.info(
                            "[RATE-GOVERNOR] Aging upgrade: tarefa LOW da sessão '%s' "
                            "promovida após %.1fs na fila.",
                            req.session_id,
                            age,
                        )
                        # Cai direto para execução (bypass freeze check)
                    else:
                        # Ainda sob pressão: re-enfileira
                        self.request_queue.put(req)
                        time.sleep(0.5)
                        continue
                elif self.low_priority_frozen:
                    # Re-enfileira o item congelado e aguarda alívio de cotas
                    self.request_queue.put(req)
                    time.sleep(0.5)
                    continue

            # ── Congelamento MEDIUM ───────────────────────────────
            if req.priority == 2 and self.medium_priority_frozen:
                self.request_queue.put(req)
                time.sleep(0.5)
                continue

            # ── Execução segura ───────────────────────────────────
            try:
                result = req.task_fn()
                req.future_result.put((True, result))
            except Exception as e:
                req.future_result.put((False, e))
            finally:
                self.request_queue.task_done()
                # Pequeno espaçamento antirrefluxo de requisições de rede
                time.sleep(0.02)

    # ── Shutdown Graceful ─────────────────────────────────────────

    def shutdown(self) -> None:
        """Para o loop consumidor de forma segura."""
        self.running = False
