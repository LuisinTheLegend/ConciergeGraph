"""
tests/test_rate_governor_priority.py — SDD-SURVIVAL-23

TDD Test Suite for RateGovernor with Priority Traffic Management.

Validates:
  1. Priority queue ordering (HIGH < MEDIUM < LOW).
  2. Reactive freezing of LOW queue upon reaching >= 85% quota usage.
  3. Reactive freezing of MEDIUM queue upon reaching >= 95% quota usage.
  4. Fast-path inline bypass for HIGH priority under green traffic (< 50%).
  5. Dynamic thawing when sliding window usage decays.
  6. Sliding window metrics calculation with temporal expiration.
"""

import threading
import time
import unittest

from core.rate_governor import PriorityRequest, RateGovernor


class TestPriorityRequestOrdering(unittest.TestCase):
    """Tests the logical ordering of PriorityRequest items within the priority queue."""

    def test_should_prioritize_high_over_low_requests_in_queue(self):
        """Validates that HIGH requests (priority 1) jump ahead and execute before LOW (priority 3)."""
        # Instantiate governor without starting background daemon to inspect queue directly
        governor = RateGovernor(rpm_limit=10, tpm_limit=1000, check_window_seconds=10)

        execution_order = []

        # Add tasks in inverted priority order (LOW first, then HIGH and MEDIUM)
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

        # Dequeue requests manually in PriorityQueue order
        req1 = governor.request_queue.get()
        req2 = governor.request_queue.get()
        req3 = governor.request_queue.get()

        req1.task_fn()
        req2.task_fn()
        req3.task_fn()

        self.assertEqual(execution_order, ["HIGH", "MEDIUM", "LOW"])

    def test_same_priority_should_be_fifo(self):
        """Under equal priority, older requests (lower timestamp) must be processed first (FIFO)."""
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
    """Tests reactive queue freezing and thawing under quota pressure."""

    def setUp(self):
        # Low limits for deterministic saturation: 10 RPM, 1000 TPM, 10s window
        self.governor = RateGovernor(
            rpm_limit=10, tpm_limit=1000, check_window_seconds=10
        )
        self.governor.start()

    def tearDown(self):
        self.governor.running = False
        self.governor.join(timeout=1.0)

    def test_should_freeze_low_priority_requests_upon_approaching_budget_limits(self):
        """Ensures that LOW priority tasks (priority 3) freeze when consumption reaches >= 85%."""
        # Report usage of 900 tokens (90% of 1000 TPM limit)
        self.governor.report_usage(900)

        metrics = self.governor.get_current_metrics()
        self.assertTrue(self.governor.low_priority_frozen)
        self.assertFalse(self.governor.medium_priority_frozen)
        self.assertGreaterEqual(metrics["tpm_percentage"], 85.0)

        # LOW priority task should remain held in queue without executing
        low_executed = threading.Event()

        def low_task():
            low_executed.set()
            return "ok"

        req = PriorityRequest(3, low_task, time.time(), "session_1")
        self.governor.request_queue.put(req)

        # Confirm the daemon thread did NOT consume the frozen task
        time.sleep(0.4)
        self.assertFalse(low_executed.is_set())

        # Simulate quota relief by clearing usage history (temporal decay)
        with self.governor.lock:
            self.governor.history.clear()
            self.governor._recalculate_frozen_states()

        # Task should now unfreeze and execute via the daemon thread
        time.sleep(1.0)
        self.assertTrue(
            low_executed.is_set() or self.governor.request_queue.empty(),
            "LOW priority task should have been released after quota relief.",
        )

    def test_should_freeze_medium_priority_at_95_percent(self):
        """Ensures that MEDIUM priority tasks freeze when consumption reaches >= 95%."""
        # 960 tokens = 96% of 1000 TPM limit
        self.governor.report_usage(960)

        self.assertTrue(self.governor.low_priority_frozen)
        self.assertTrue(self.governor.medium_priority_frozen)

    def test_should_not_freeze_any_queue_under_green_traffic(self):
        """No queues are frozen under green traffic (< 50%)."""
        self.governor.report_usage(100)  # 10% of limit

        self.assertFalse(self.governor.low_priority_frozen)
        self.assertFalse(self.governor.medium_priority_frozen)


class TestRateGovernorFastPath(unittest.TestCase):
    """Tests the fast-path bypass for HIGH priority requests under green traffic."""

    def setUp(self):
        self.governor = RateGovernor(
            rpm_limit=100, tpm_limit=10000, check_window_seconds=60
        )
        self.governor.start()

    def tearDown(self):
        self.governor.running = False
        self.governor.join(timeout=1.0)

    def test_high_priority_should_bypass_queue_under_green_traffic(self):
        """HIGH priority requests with usage < 50% must execute inline without queue overhead."""
        # Green traffic: zero reported consumption
        result = self.governor.submit_request(
            priority=1,
            session_id="primary_session",
            task_fn=lambda: "fast_result",
        )

        self.assertEqual(result, "fast_result")
        # Nothing should have queued
        self.assertEqual(self.governor.request_queue.qsize(), 0)


class TestRateGovernorSlidingWindowMetrics(unittest.TestCase):
    """Tests sliding window metrics calculation with temporal expiration."""

    def test_metrics_should_expire_outside_window(self):
        """Usage entries outside the sliding window must expire automatically."""
        governor = RateGovernor(
            rpm_limit=10, tpm_limit=1000, check_window_seconds=2
        )

        # Inject an expired usage entry (3 seconds in the past)
        with governor.lock:
            governor.history.append((time.time() - 3, 500))

        metrics = governor.get_current_metrics()

        # Expired entry should not count towards current metrics
        self.assertEqual(metrics["current_rpm"], 0)
        self.assertEqual(metrics["current_tpm"], 0)
        self.assertEqual(metrics["rpm_percentage"], 0)
        self.assertEqual(metrics["tpm_percentage"], 0)

    def test_metrics_should_count_entries_within_window(self):
        """Usage entries within the sliding window must be aggregated correctly."""
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
