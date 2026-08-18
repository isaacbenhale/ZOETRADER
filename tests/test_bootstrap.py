import unittest

from zoetrading.main import BootstrapState, RuntimeMode, build_state, render_state, resolve_mode


class BootstrapTests(unittest.TestCase):
    def test_default_state_is_monitoring_without_orders(self) -> None:
        state = build_state()

        self.assertEqual(
            state,
            BootstrapState(mode=RuntimeMode.MONITORING, orders_enabled=False),
        )

    def test_manual_mode_can_be_requested(self) -> None:
        state = build_state("manual")

        self.assertEqual(state.mode, RuntimeMode.MANUAL)
        self.assertFalse(state.orders_enabled)

    def test_auto_mode_is_blocked_during_bootstrap(self) -> None:
        with self.assertRaisesRegex(ValueError, "AUTO mode is not available"):
            resolve_mode("AUTO")

    def test_render_state_is_stable(self) -> None:
        output = render_state(BootstrapState(mode=RuntimeMode.MONITORING))

        self.assertEqual(
            output,
            "zoeTrading bootstrap OK\nmode=MONITORING\norders_enabled=false\nconfig_loaded=true",
        )


if __name__ == "__main__":
    unittest.main()
