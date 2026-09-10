"""
core/rate_governor.py — SDD-SURVIVAL-23

RateGovernor with Priority Traffic (HTTP 429 Isolation & Queue Freezing).

Daemon worker thread regulating rate limits with a three-tier priority queue:
  1 (HIGH)   — Synchronous FSM decisions from Primary Agent, direct chat with user.
  2 (MEDIUM) — Subagent tools, non-blocking analysis routines.
  3 (LOW)    — Janitor background cleanups, GraphRAG community detection.

When quota thresholds (RPM/TPM) approach exhaustion, the governor reactively
freezes lower-priority queues:
  - LOW frozen if usage >= 85%
  - MEDIUM frozen if usage >= 95%
  - HIGH is never frozen

Fast-path bypass: HIGH requests under green traffic (< 50%) execute
inline in < 1ms without queueing overhead.

Anti-starvation aging: LOW tasks queued for longer than aging_threshold_secs (configurable)
receive temporary promotion to MEDIUM if overall consumption drops below 75%.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)


class PriorityRequest:
    """
    Encapsulated request with priority, result callback channel, and metadata.

    Priorities:
      1 = HIGH   (Primary Agent / Direct User Chat)
      2 = MEDIUM (Subagents / Auxiliary Tasks)
      3 = LOW    (Janitor / Background GraphRAG)
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
        # Synchronous blocking result channel: (success: bool, result_or_exc)
        self.future_result: queue.Queue = queue.Queue(maxsize=1)

    def __lt__(self, other: "PriorityRequest") -> bool:
        """Compares by priority; upon tie, earlier timestamp executes first (FIFO)."""
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority < other.priority


class RateGovernor(threading.Thread):
    """
    Daemon rate governance thread with a three-tier priority queue.

    Parameters:
      rpm_limit            — Permitted requests per minute within moving window.
      tpm_limit            — Permitted tokens per minute within moving window.
      check_window_seconds — Moving window duration in seconds.
      aging_threshold_secs — Time in seconds after which a LOW task receives
                             temporary promotion to MEDIUM (anti-starvation).
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

        # Thread-safe priority queue
        self.request_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self.running = True

        # Sliding window history: list of (timestamp, tokens_used)
        self.history: List[Tuple[float, int]] = []

        # Active freezing flags
        self.low_priority_frozen = False
        self.medium_priority_frozen = False

    # ── Usage Reporting ────────────────────────────────────────────

    def report_usage(self, tokens_used: int) -> None:
        """
        Records a completed API invocation and its consumed tokens.

        Must be invoked by external callers after every LLM request
        so that moving window metrics accurately reflect real consumption.
        """
        with self.lock:
            self.history.append((time.time(), tokens_used))
            self._recalculate_frozen_states()

    # ── Sliding Window Metrics ─────────────────────────────────────

    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Calculates current RPM and TPM utilization within moving window.

        Returns dict with:
          - current_rpm, current_tpm (absolute counts)
          - rpm_percentage, tpm_percentage (utilization percentages)
          - low_priority_frozen, medium_priority_frozen (boolean flags)
          - queue_backlog (pending queue size)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Evict records outside sliding window
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

    # ── Internal Freezing Recomputation ────────────────────────────

    def _recalculate_frozen_states(self) -> None:
        """
        Determines reactive queue freezing based on maximum percentage
        utilization between RPM and TPM.

        Thresholds:
          - >= 85% -> freeze LOW
          - >= 95% -> freeze MEDIUM (LOW already frozen)
          - <  85% -> unfreeze both
        """
        metrics = self.get_current_metrics()
        max_pct = max(metrics["rpm_percentage"], metrics["tpm_percentage"])

        # Freeze LOW queue (Janitor) if exceeding 85%
        self.low_priority_frozen = max_pct >= 85.0

        # Freeze MEDIUM queue (Subagents) if exceeding 95%
        self.medium_priority_frozen = max_pct >= 95.0

    # ── Request Submission ─────────────────────────────────────────

    def submit_request(
        self, priority: int, session_id: str, task_fn: Callable[[], Any]
    ) -> Any:
        """
        Submits a task for governed execution.
        Returns the result synchronously / blocking to the caller.

        Fast-path bypass: HIGH requests under green traffic (< 50%) execute
        inline without entering the daemon queue, eliminating observable latency.
        """
        # Fast-path: bypass queue instantly if HIGH and green traffic
        with self.lock:
            metrics = self.get_current_metrics()
        max_pct = max(metrics["rpm_percentage"], metrics["tpm_percentage"])

        if priority == 1 and max_pct < 50.0:
            # Inline synchronous execution in < 1ms
            result = task_fn()
            return result

        # Enqueue for daemon consumer thread
        req = PriorityRequest(priority, task_fn, time.time(), session_id)
        self.request_queue.put(req)

        # Block waiting for consumer thread to dispatch result
        success, result_or_exc = req.future_result.get()
        if success:
            return result_or_exc
        raise result_or_exc

    # ── Daemon Consumer Loop ───────────────────────────────────────

    def run(self) -> None:
        """
        Continuous consumer loop processing requests respecting dynamic throttling.

        Applies anti-starvation aging: if a LOW task waits for more than
        aging_threshold_secs, it receives temporary promotion to MEDIUM
        (provided overall usage is below 75%).
        """
        while self.running:
            if self.request_queue.empty():
                time.sleep(0.05)
                continue

            # Update freezing flags before consuming
            with self.lock:
                self._recalculate_frozen_states()

            # Retrieve highest priority item (lowest integer)
            try:
                req = self.request_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # ── Anti-starvation Aging ──────────────────────────────
            if req.priority == 3:
                age = time.time() - req.timestamp
                if age >= self.aging_threshold_secs:
                    with self.lock:
                        metrics = self.get_current_metrics()
                    max_pct = max(
                        metrics["rpm_percentage"], metrics["tpm_percentage"]
                    )
                    if max_pct < 75.0:
                        # Temporary promotion: execute even if LOW is frozen
                        logger.info(
                            "[RATE-GOVERNOR] Aging upgrade: LOW task from session '%s' "
                            "promoted after %.1fs in queue.",
                            req.session_id,
                            age,
                        )
                        # Fall through directly to execution (bypass freeze check)
                    else:
                        # Still under load: re-enqueue
                        self.request_queue.put(req)
                        time.sleep(0.5)
                        continue
                elif self.low_priority_frozen:
                    # Re-enqueue frozen item and wait for quota relief
                    self.request_queue.put(req)
                    time.sleep(0.5)
                    continue

            # ── MEDIUM Queue Freezing ──────────────────────────────
            if req.priority == 2 and self.medium_priority_frozen:
                self.request_queue.put(req)
                time.sleep(0.5)
                continue

            # ── Safe Execution ─────────────────────────────────────
            try:
                result = req.task_fn()
                req.future_result.put((True, result))
            except Exception as e:
                req.future_result.put((False, e))
            finally:
                self.request_queue.task_done()
                # Subtle spacing to avoid socket connection bursts
                time.sleep(0.02)

    # ── Graceful Shutdown ──────────────────────────────────────────

    def shutdown(self) -> None:
        """Safely terminates consumer worker loop."""
        self.running = False
