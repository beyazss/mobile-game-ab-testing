"""Mobile game A/B test analysis.

I use this script to compare two versions of the Cookie Cats experiment:
the progression gate at level 30 and the same gate at level 40.

Running the file creates summary tables and charts in the outputs folder.
"""

from math import erfc, sqrt
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PROJECT_DIR = Path(__file__).resolve().parent
DATA_PATH = PROJECT_DIR / "data" / "cookie_cats.csv"
OUTPUT_DIR = PROJECT_DIR / "outputs"
CONTROL_GROUP = "gate_30"
TEST_GROUP = "gate_40"


def load_and_check_data() -> pd.DataFrame:
    """Load the dataset and run the checks I need before starting the analysis."""
    data = pd.read_csv(DATA_PATH)
    required_columns = {
        "userid", "version", "sum_gamerounds", "retention_1", "retention_7"
    }

    missing_columns = required_columns.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")
    if data["userid"].duplicated().any():
        raise ValueError("The dataset contains duplicate user IDs.")
    if data[list(required_columns)].isna().any().any():
        raise ValueError("The dataset contains missing values.")

    expected_groups = {CONTROL_GROUP, TEST_GROUP}
    actual_groups = set(data["version"].unique())
    if actual_groups != expected_groups:
        raise ValueError(f"Unexpected experiment groups: {sorted(actual_groups)}")
    if (data["sum_gamerounds"] < 0).any():
        raise ValueError("The dataset contains negative round counts.")
    for column in ["retention_1", "retention_7"]:
        if not data[column].isin([True, False]).all():
            raise ValueError(f"{column} must contain only True/False values.")
    return data


def calculate_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate player count, gameplay and retention values for each group."""
    summary = (
        data.groupby("version", observed=True)
        .agg(
            players=("userid", "count"),
            average_rounds=("sum_gamerounds", "mean"),
            median_rounds=("sum_gamerounds", "median"),
            p90_rounds=("sum_gamerounds", lambda values: values.quantile(0.90)),
            d1_retention=("retention_1", "mean"),
            d7_retention=("retention_7", "mean"),
        )
        .reset_index()
    )
    summary["d1_retention_pct"] = summary["d1_retention"] * 100
    summary["d7_retention_pct"] = summary["d7_retention"] * 100
    return summary


def calculate_round_distribution(
    data: pd.DataFrame,
    groups: list[str],
    visible_limit: int,
    bin_width: int = 5,
) -> pd.DataFrame:
    """Prepare within-group round shares for the dashboard's visible window."""
    selected = data[data["version"].isin(groups)].copy()
    if selected.empty:
        return pd.DataFrame(
            columns=["version", "round_bin", "players", "group_total", "share"]
        )

    selected["round_bin"] = (
        selected["sum_gamerounds"] // bin_width * bin_width
    ).astype(int)
    distribution = (
        selected.groupby(["version", "round_bin"], observed=True)
        .size()
        .rename("players")
        .reset_index()
    )
    group_totals = selected.groupby("version", observed=True).size()
    distribution["group_total"] = distribution["version"].map(group_totals)
    distribution["share"] = distribution["players"] / distribution["group_total"]
    return distribution[distribution["round_bin"] <= visible_limit].copy()


def check_group_allocation(data: pd.DataFrame) -> dict:
    """Compare the observed group split with a hypothetical 50/50 split.

    The public dataset does not document the experiment's planned allocation.
    This diagnostic therefore signals a follow-up question; it is not proof of
    an implementation problem.
    """
    counts = data["version"].value_counts()
    total_players = len(data)
    expected_players = total_players / 2
    standard_error = sqrt(total_players * 0.5 * 0.5)
    z_score = (counts[TEST_GROUP] - expected_players) / standard_error
    p_value = erfc(abs(z_score) / sqrt(2))

    return {
        "gate_30_players": int(counts[CONTROL_GROUP]),
        "gate_40_players": int(counts[TEST_GROUP]),
        "gate_30_share": counts[CONTROL_GROUP] / total_players,
        "gate_40_share": counts[TEST_GROUP] / total_players,
        "share_difference_pp": (
            counts[TEST_GROUP] - counts[CONTROL_GROUP]
        ) / total_players * 100,
        "z_score": z_score,
        "p_value": p_value,
        "differs_from_equal_split": p_value < 0.05,
    }


def compare_retention(data: pd.DataFrame, metric: str) -> dict:
    """Compare one retention metric between the two experiment groups."""
    control_rate = data.loc[data["version"] == CONTROL_GROUP, metric].mean()
    test_rate = data.loc[data["version"] == TEST_GROUP, metric].mean()
    absolute_difference = test_rate - control_rate
    relative_difference = absolute_difference / control_rate

    control_n = (data["version"] == CONTROL_GROUP).sum()
    test_n = (data["version"] == TEST_GROUP).sum()
    control_successes = data.loc[
        data["version"] == CONTROL_GROUP, metric
    ].sum()
    test_successes = data.loc[data["version"] == TEST_GROUP, metric].sum()
    pooled_rate = (control_successes + test_successes) / (control_n + test_n)
    test_standard_error = sqrt(
        pooled_rate * (1 - pooled_rate) * (1 / control_n + 1 / test_n)
    )
    z_score = (test_rate - control_rate) / test_standard_error
    p_value = erfc(abs(z_score) / sqrt(2))

    standard_error = sqrt(
        control_rate * (1 - control_rate) / control_n
        + test_rate * (1 - test_rate) / test_n
    )
    ci_low = absolute_difference - 1.96 * standard_error
    ci_high = absolute_difference + 1.96 * standard_error

    return {
        "metric": metric,
        "gate_30_rate": control_rate,
        "gate_40_rate": test_rate,
        "difference_percentage_points": absolute_difference * 100,
        "relative_difference_pct": relative_difference * 100,
        "confidence_interval_low_pp": ci_low * 100,
        "confidence_interval_high_pp": ci_high * 100,
        "z_score": z_score,
        "p_value": p_value,
    }


def save_group_chart(summary: pd.DataFrame) -> None:
    """Show whether both groups contain similar player counts."""
    plt.figure(figsize=(8, 5))
    chart = sns.barplot(
        data=summary, x="version", y="players", hue="version",
        palette=["#37cdbd", "#7560eb"], legend=False,
    )
    chart.set(
        title="Players in Each Experiment Group",
        xlabel="Experiment group",
        ylabel="Number of players",
    )
    for container in chart.containers:
        chart.bar_label(container, fmt="{:,.0f}", padding=4)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_group_sizes.png", dpi=180)
    plt.close()


def save_rounds_chart(data: pd.DataFrame) -> None:
    """Compare rounds while keeping a few extreme values from hiding the pattern."""
    display_limit = data["sum_gamerounds"].quantile(0.99)
    chart_data = data[data["sum_gamerounds"] <= display_limit].copy()

    plt.figure(figsize=(9, 5))
    chart = sns.histplot(
        data=chart_data, x="sum_gamerounds", hue="version", bins=45,
        stat="density", common_norm=False, element="step",
        palette=["#37cdbd", "#7560eb"], alpha=0.35,
    )
    chart.set(
        title="Game Rounds by Experiment Group (up to the 99th percentile)",
        xlabel="Rounds played in the first 14 days",
        ylabel="Density",
    )
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_round_distribution.png", dpi=180)
    plt.close()


def save_retention_chart(summary: pd.DataFrame) -> None:
    """Create one chart for the D1 and D7 retention comparison."""
    chart_data = summary.melt(
        id_vars="version",
        value_vars=["d1_retention_pct", "d7_retention_pct"],
        var_name="metric",
        value_name="retention_pct",
    )
    chart_data["metric"] = chart_data["metric"].map({
        "d1_retention_pct": "D1 retention",
        "d7_retention_pct": "D7 retention",
    })

    plt.figure(figsize=(9, 5))
    chart = sns.barplot(
        data=chart_data, x="metric", y="retention_pct", hue="version",
        palette=["#37cdbd", "#7560eb"],
    )
    chart.set(
        title="D1 and D7 Retention by Experiment Group",
        xlabel="",
        ylabel="Retention (%)",
        ylim=(0, 50),
    )
    for container in chart.containers:
        chart.bar_label(container, fmt="%.2f%%", padding=4)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_retention_comparison.png", dpi=180)
    plt.close()


def print_result(result: dict) -> None:
    """Print one result in a format that is easy to explain."""
    print(f"\n{result['metric']}")
    print(f"Gate 30: {result['gate_30_rate']:.2%}")
    print(f"Gate 40: {result['gate_40_rate']:.2%}")
    print(f"Difference: {result['difference_percentage_points']:.2f} percentage points")
    print(f"Relative difference: {result['relative_difference_pct']:.2f}%")
    print(
        "95% confidence interval: "
        f"[{result['confidence_interval_low_pp']:.2f}, "
        f"{result['confidence_interval_high_pp']:.2f}] percentage points"
    )
    print(f"p-value: {result['p_value']:.4f}")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid")

    data = load_and_check_data()
    summary = calculate_summary(data)
    d1_result = compare_retention(data, "retention_1")
    d7_result = compare_retention(data, "retention_7")
    allocation = check_group_allocation(data)

    pd.DataFrame([d1_result, d7_result]).to_csv(
        OUTPUT_DIR / "retention_test_results.csv", index=False
    )
    summary.to_csv(OUTPUT_DIR / "group_summary.csv", index=False)
    pd.DataFrame([allocation]).to_csv(
        OUTPUT_DIR / "allocation_check.csv", index=False
    )
    save_group_chart(summary)
    save_rounds_chart(data)
    save_retention_chart(summary)

    print("Data checks completed.")
    print(f"Rows: {len(data):,}")
    print(f"Unique players: {data['userid'].nunique():,}")
    print("Missing values: 0")
    print("Duplicate user IDs: 0")
    print(
        "Experiment split: "
        f"{allocation['gate_30_share']:.2%} Gate 30 / "
        f"{allocation['gate_40_share']:.2%} Gate 40"
    )
    print(f"Observed-vs-50/50 diagnostic p-value: {allocation['p_value']:.4f}")
    if allocation["differs_from_equal_split"]:
        print(
            "Allocation note: the public data does not document the planned split. "
            "If it was 50/50, review assignment and tracking before treating the "
            "experiment as production-ready."
        )
    print_result(d1_result)
    print_result(d7_result)

    print("\nMy conclusion")
    if d7_result["p_value"] < 0.05 and d7_result["difference_percentage_points"] < 0:
        print(
            "Moving the gate from level 30 to level 40 did not improve retention. "
            "The D7 result shows a statistically significant decline. I would not "
            "roll out Gate 40. I would first confirm the planned allocation and "
            "validate assignment and tracking; if those checks are clean, I would "
            "retain Gate 30 and investigate the D7 decline."
        )
    else:
        print(
            "The available evidence is not strong enough to recommend changing "
            "the current gate position."
        )
    print(f"\nTables and charts were saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
