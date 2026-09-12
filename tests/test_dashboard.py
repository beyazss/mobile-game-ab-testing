"""Interaction checks for the Streamlit dashboard."""

import logging
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_DIR = Path(__file__).resolve().parents[1]
logging.getLogger(
    "streamlit.runtime.scriptrunner_utils.script_run_context"
).disabled = True


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = AppTest.from_file(
            str(PROJECT_DIR / "dashboard.py"), default_timeout=20
        ).run()
        self.assertFalse(self.app.exception)

    def test_default_controls_and_tabs(self) -> None:
        self.assertEqual(
            [tab.label for tab in self.app.tabs],
            [
                "Experiment overview",
                "Player behavior",
                "Statistical evidence",
                "Dataset",
            ],
        )
        self.assertEqual(self.app.multiselect[0].value, ["gate_30", "gate_40"])
        self.assertEqual(self.app.slider[0].value, 250)

    def test_group_and_round_filters_update_exploration_views(self) -> None:
        self.app.multiselect[0].set_value(["gate_40"])
        self.app.slider[0].set_value(50)
        self.app.run()
        self.assertFalse(self.app.exception)
        messages = [item.value for item in self.app.info]
        self.assertTrue(any("gate_40" in text and "0–50" in text for text in messages))
        self.assertTrue(any("45,489 players selected" in text for text in messages))

    def test_empty_group_selection_is_handled(self) -> None:
        self.app.multiselect[0].set_value([])
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.warning), 2)


if __name__ == "__main__":
    unittest.main()
