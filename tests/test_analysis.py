"""Small regression tests for the analysis results."""

import sys
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from main import (  # noqa: E402
    calculate_round_distribution,
    calculate_summary,
    check_group_allocation,
    compare_retention,
    load_and_check_data,
)


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_and_check_data()

    def test_dataset_shape_and_ids(self) -> None:
        self.assertEqual(len(self.data), 90_189)
        self.assertEqual(self.data["userid"].nunique(), 90_189)
        self.assertEqual(int(self.data.isna().sum().sum()), 0)
        self.assertEqual(int(self.data["userid"].duplicated().sum()), 0)
        self.assertEqual(set(self.data["version"]), {"gate_30", "gate_40"})
        self.assertGreaterEqual(int(self.data["sum_gamerounds"].min()), 0)

    def test_group_counts(self) -> None:
        summary = calculate_summary(self.data).set_index("version")
        self.assertEqual(int(summary.loc["gate_30", "players"]), 44_700)
        self.assertEqual(int(summary.loc["gate_40", "players"]), 45_489)

    def test_retention_results(self) -> None:
        d1 = compare_retention(self.data, "retention_1")
        d7 = compare_retention(self.data, "retention_7")
        self.assertAlmostEqual(d1["difference_percentage_points"], -0.5905, places=4)
        self.assertAlmostEqual(d1["p_value"], 0.0744, places=4)
        self.assertAlmostEqual(d7["difference_percentage_points"], -0.8201, places=4)
        self.assertAlmostEqual(d7["p_value"], 0.0016, places=4)
        self.assertAlmostEqual(d1["confidence_interval_low_pp"], -1.2393, places=4)
        self.assertAlmostEqual(d1["confidence_interval_high_pp"], 0.0582, places=4)
        self.assertAlmostEqual(d7["confidence_interval_low_pp"], -1.3282, places=4)
        self.assertAlmostEqual(d7["confidence_interval_high_pp"], -0.3121, places=4)

    def test_observed_split_differs_from_equal_split(self) -> None:
        allocation = check_group_allocation(self.data)
        self.assertTrue(allocation["differs_from_equal_split"])
        self.assertAlmostEqual(allocation["p_value"], 0.0086, places=4)

    def test_retention_success_counts(self) -> None:
        grouped = self.data.groupby("version")[["retention_1", "retention_7"]].sum()
        self.assertEqual(int(grouped.loc["gate_30", "retention_1"]), 20_034)
        self.assertEqual(int(grouped.loc["gate_40", "retention_1"]), 20_119)
        self.assertEqual(int(grouped.loc["gate_30", "retention_7"]), 8_502)
        self.assertEqual(int(grouped.loc["gate_40", "retention_7"]), 8_279)

    def test_empty_group_filter_returns_empty_distribution(self) -> None:
        distribution = calculate_round_distribution(self.data, [], 250)
        self.assertTrue(distribution.empty)

    def test_group_filter_changes_round_distribution(self) -> None:
        distribution = calculate_round_distribution(self.data, ["gate_40"], 250)
        self.assertEqual(set(distribution["version"]), {"gate_40"})
        self.assertTrue((distribution["group_total"] == 45_489).all())

    def test_visible_limit_changes_chart_window_not_denominator(self) -> None:
        narrow = calculate_round_distribution(
            self.data, ["gate_30", "gate_40"], 50
        )
        wide = calculate_round_distribution(
            self.data, ["gate_30", "gate_40"], 490
        )
        self.assertLessEqual(int(narrow["round_bin"].max()), 50)
        self.assertGreater(int(wide["round_bin"].max()), 50)
        narrow_totals = narrow.groupby("version")["group_total"].first().to_dict()
        wide_totals = wide.groupby("version")["group_total"].first().to_dict()
        self.assertEqual(narrow_totals, wide_totals)


if __name__ == "__main__":
    unittest.main()
