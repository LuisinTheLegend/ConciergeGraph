"""
tests/test_rate_governor_priority.py — SDD-SURVIVAL-23

Suíte de testes TDD para o RateGovernor com Tráfego Prioritário.

Valida:
  1. Ordenação correta de prioridade na fila (HIGH < MEDIUM < LOW).
  2. Congelamento reativo de LOW ao atingir ≥ 85% de cota.
  3. Congelamento reativo de MEDIUM ao atingir ≥ 95% de cota.
  4. Bypass fast-path para HIGH sob tráfego verde (< 50%).
  5. Destravamento dinâmico (thaw) quando janela deslizante decai.
  6. Métricas de janela deslizante com expiração temporal.
"""

import threading
import time
import unittest

from core.rate_governor import PriorityRequest, RateGovernor


class TestPriorityRequestOrdering(unittest.TestCase):
    """Testa a ordenação lógica de PriorityRequest na fila de prioridade."""

    def test_should_prioritize_high_over_low_requests_in_queue(self):
        """Valida que requisições HIGH (prioridade 1) furam e executam antes de LOW (prioridade 3)."""
        # Pausa provisória na thread consumidora para preencher o backlog
        governor = RateGovernor(rpm_limit=10, tpm_limit=1000, check_window_seconds=10)
        # NÃO inicia a thread daemon — manipulamos a fila diretamente

        execution_order = []

        # Adiciona tarefas em ordem de prioridade invertida (LOW primeiro, HIGH depois)
        governor.request_queue.put(
            PriorityRequest(
                3, lambda: execution_order.append("LOW"), time.time(), "session_1"
            )
        )
        governor.request_queue.put(
            PriorityRequest(
                1, lambda: execution_order.append("HIGH"), time.time(), "session_1"
            )
        )
        governor.request_queue.put(
            PriorityRequest(
                2, lambda: execution_order.append("MEDIUM"), time.time(), "session_1"
            )
        )

        # Consome a fila manualmente na ordem que o PriorityQueue desempata
        req1 = governor.request_queue.get()
        req2 = governor.request_queue.get()
        req3 = governor.request_queue.get()

        req1.task_fn()
        req2.task_fn()
        req3.task_fn()

        self.assertEqual(execution_order, ["HIGH", "MEDIUM", "LOW"])

    def test_same_priority_should_be_fifo(self):
        """Em prioridade igual, a tarefa mais antiga (menor timestamp) sai primeiro."""
        governor = RateGovernor(rpm_limit=10, tpm_limit=1000, check_window_seconds=10)

        execution_order = []
        t_old = time.time() - 10
        t_new = time.time()

        governor.request_queue.put(
            PriorityRequest(
                2, lambda: execution_order.append("NEWER"), t_new, "session_1"
            )
        )
        governor.request_queue.put(
            PriorityRequest(
                2, lambda: execution_order.append("OLDER"), t_old, "session_1"
            )
        )

        req1 = governor.request_queue.get()
        req2 = governor.request_queue.get()

        req1.task_fn()
        req2.task_fn()

        self.assertEqual(execution_order, ["OLDER", "NEWER"])


class TestRateGovernorFreezing(unittest.TestCase):
    """Testa o congelamento e descongelamento reativo de filas sob pressão de cotas."""

    def setUp(self):
        # Limites baixos para fácil saturação: 10 RPM, 1000 TPM, janela 10s
        self.governor = RateGovernor(
            rpm_limit=10, tpm_limit=1000, check_window_seconds=10
        )
        self.governor.start()

    def tearDown(self):
        self.governor.running = False
        # Dá tempo para a thread daemon morrer
        self.governor.join(timeout=1.0)

    def test_should_freeze_low_priority_requests_upon_approaching_budget_limits(self):
        """Garante que tarefas LOW (prioridade 3) fiquem congeladas se o consumo ultrapassar 85%."""
        # Reporta um uso massivo de 900 tokens (90% do limite de 1000 TPM)
        self.governor.report_usage(900)

        metrics = self.governor.get_current_metrics()
        self.assertTrue(self.governor.low_priority_frozen)
        self.assertFalse(self.governor.medium_priority_frozen)
        self.assertGreaterEqual(metrics["tpm_percentage"], 85.0)

        # Tarefa LOW deve ficar retida na fila sem ser executada
        low_executed = threading.Event()

        def low_task():
            low_executed.set()
            return "ok"

        req = PriorityRequest(3, low_task, time.time(), "session_1")
        self.governor.request_queue.put(req)

        # Espera para confirmar que a thread NÃO consumiu a tarefa bloqueada
        time.sleep(0.4)
        self.assertFalse(low_executed.is_set())

        # Simula alívio de cotas limpando o histórico (decaimento temporal)
        with self.governor.lock:
            self.governor.history.clear()
            self.governor._recalculate_frozen_states()

        # Agora a tarefa deve ser desbloqueada e consumida pela thread daemon
        time.sleep(1.0)
        self.assertTrue(
            low_executed.is_set() or self.governor.request_queue.empty(),
            "Tarefa LOW deveria ter sido liberada após alívio de cotas.",
        )

    def test_should_freeze_medium_priority_at_95_percent(self):
        """Garante que MEDIUM congela ao atingir ≥ 95% da cota."""
        # 960 tokens = 96% do limite de 1000
        self.governor.report_usage(960)

        self.assertTrue(self.governor.low_priority_frozen)
        self.assertTrue(self.governor.medium_priority_frozen)

    def test_should_not_freeze_any_queue_under_green_traffic(self):
        """Nenhuma fila é congelada sob tráfego verde (< 50%)."""
        self.governor.report_usage(100)  # 10% do limite

        self.assertFalse(self.governor.low_priority_frozen)
        self.assertFalse(self.governor.medium_priority_frozen)


class TestRateGovernorFastPath(unittest.TestCase):
    """Testa o bypass fast-path para chamadas HIGH sob tráfego verde."""

    def setUp(self):
        self.governor = RateGovernor(
            rpm_limit=100, tpm_limit=10000, check_window_seconds=60
        )
        self.governor.start()

    def tearDown(self):
        self.governor.running = False
        self.governor.join(timeout=1.0)

    def test_high_priority_should_bypass_queue_under_green_traffic(self):
        """Chamadas HIGH com tráfego < 50% devem executar inline sem enfileiramento."""
        # Tráfego verde: nenhum uso reportado
        result = self.governor.submit_request(
            priority=1,
            session_id="hermes_main",
            task_fn=lambda: "fast_result",
        )

        self.assertEqual(result, "fast_result")
        # Nada deve ter passado pela fila
        self.assertEqual(self.governor.request_queue.qsize(), 0)


class TestRateGovernorSlidingWindowMetrics(unittest.TestCase):
    """Testa as métricas de janela deslizante com expiração temporal."""

    def test_metrics_should_expire_outside_window(self):
        """Registros fora da janela deslizante devem ser limpos automaticamente."""
        governor = RateGovernor(
            rpm_limit=10, tpm_limit=1000, check_window_seconds=2
        )

        # Injeta um registro artificial "antigo" (3 segundos no passado)
        with governor.lock:
            governor.history.append((time.time() - 3, 500))

        metrics = governor.get_current_metrics()

        # O registro antigo deve ter sido expirado pela janela deslizante
        self.assertEqual(metrics["current_rpm"], 0)
        self.assertEqual(metrics["current_tpm"], 0)
        self.assertEqual(metrics["rpm_percentage"], 0)
        self.assertEqual(metrics["tpm_percentage"], 0)

    def test_metrics_should_count_entries_within_window(self):
        """Registros dentro da janela devem ser contados corretamente."""
        governor = RateGovernor(
            rpm_limit=10, tpm_limit=1000, check_window_seconds=60
        )

        governor.report_usage(200)
        governor.report_usage(300)

        metrics = governor.get_current_metrics()

        self.assertEqual(metrics["current_rpm"], 2)
        self.assertEqual(metrics["current_tpm"], 500)
        self.assertEqual(metrics["rpm_percentage"], 20.0)
        self.assertEqual(metrics["tpm_percentage"], 50.0)


if __name__ == "__main__":
    unittest.main()
