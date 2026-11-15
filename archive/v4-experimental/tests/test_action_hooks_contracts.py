"""archive/v4-experimental/tests/test_action_hooks_contracts.py

Testes de contrato de ActionHooks extraidos de tests/test_interface_contracts.py
durante a quarentena 4.5d (Lote C).
"""
import inspect
from interface.action_hooks import ActionHooks


class TestInterfaceImports:
    def test_action_hooks_importable(self):
        from interface.action_hooks import ActionHooks as _AH  # noqa
        assert _AH is not None


class TestActionHooksSignature:
    def test_accepts_concierge_param(self):
        params = list(inspect.signature(ActionHooks.__init__).parameters.keys())
        assert "concierge" in params

    def test_accepts_revisor_param(self):
        params = list(inspect.signature(ActionHooks.__init__).parameters.keys())
        assert "revisor" in params

    def test_has_on_planning_method(self):
        assert hasattr(ActionHooks, "on_planning")

    def test_has_on_execution_method(self):
        assert hasattr(ActionHooks, "on_execution")

    def test_has_on_done_method(self):
        assert hasattr(ActionHooks, "on_done")
