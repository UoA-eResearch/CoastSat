"""Plot beach-scale waterline-to-seawall distance change through time.

Input CSV layout:
- One `dates` column.
- Many transect columns named like `nzd0133-0001`.
"""

from collections import defaultdict
import os
from pathlib import Path

import matplotlib
import pandas as pd


def _configure_matplotlib_backend() -> None:
    current_backend = matplotlib.get_backend().lower()
    if current_backend != "agg":
        return

    # Try an interactive backend only when a display is available.
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return

    for backend in ("QtAgg", "TkAgg"):
        try:
            matplotlib.use(backend, force=True)
            return
        except Exception:
            continue


_configure_matplotlib_backend()

import matplotlib.pyplot as plt


def _group_transects_by_beach(columns: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for col in columns:
        if col == "dates" or "-" not in col:
            continue
        beach_id = col.split("-", maxsplit=1)[0]
        grouped[beach_id].append(col)
    return dict(grouped)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    csv_path = script_dir / "data" / "seawall_distance.csv"
    output_path = script_dir / "beachsqueeze_plot.png"

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    df = pd.read_csv(csv_path)
    if "dates" not in df.columns:
        raise ValueError("CSV must contain a 'dates' column.")

    df["dates"] = pd.to_datetime(df["dates"], utc=True, errors="coerce")
    df = df.dropna(subset=["dates"]).sort_values("dates")

    transect_columns = [c for c in df.columns if c != "dates"]
    grouped = _group_transects_by_beach(transect_columns)
    if not grouped:
        raise ValueError("No transect columns like 'nzdXXXX-xxxx' were found.")

    color_map = plt.get_cmap("tab20", len(grouped))
    fig, ax = plt.subplots(figsize=(15, 8))

    for idx, beach_id in enumerate(sorted(grouped)):
        cols = sorted(grouped[beach_id])
        beach_data = df[cols].apply(pd.to_numeric, errors="coerce")

        # Delta beach width per transect: each transect starts at 0 at its first
        # valid observation, then shows widening (+) or narrowing (-) over time.
        beach_delta = beach_data.apply(lambda s: s - s.dropna().iloc[0] if s.notna().any() else s)

        color = color_map(idx)

        for col in cols:
            valid_transect = beach_delta[col].notna()
            ax.plot(
                df.loc[valid_transect, "dates"],
                beach_delta.loc[valid_transect, col],
                color=color,
                alpha=0.2,
                linewidth=1.0,
            )

        beach_mean = beach_delta.mean(axis=1, skipna=True)
        valid_mean = beach_mean.notna()
        ax.plot(
            df.loc[valid_mean, "dates"],
            beach_mean.loc[valid_mean],
            color=color,
            alpha=1.0,
            linewidth=2.2,
            label=f"{beach_id} (n={len(cols)})",
        )

    ax.axhline(0, color="black", linewidth=1.0, alpha=0.5)
    ax.set_title("Delta Beach Width Through Time by Beach")
    ax.set_xlabel("Date")
    ax.set_ylabel("Delta distance from initial observation (m)")
    ax.grid(True, alpha=0.25)
    ax.legend(title="Beach averages", bbox_to_anchor=(1.02, 1), loc="upper left")

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    if plt.get_backend().lower() == "agg":
        print("Interactive plot display is unavailable with backend 'Agg'; saved PNG instead.")
    else:
        plt.show()

    print(f"Loaded {len(df)} records from {csv_path}")
    print(f"Number of beaches: {len(grouped)}")
    print(f"Plotted {sum(len(v) for v in grouped.values())} transects across {len(grouped)} beaches")
    print(f"Saved figure: {output_path}")


if __name__ == "__main__":
    main()
