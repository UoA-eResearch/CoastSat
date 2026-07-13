from pathlib import Path

import pandas as pd


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path)


def main() -> None:
    csv_path = Path("data/seawall_distance.csv")
    df = load_csv(csv_path)

    print("Rows:", len(df))
    print("Columns:", list(df.columns))
    print("\nPreview:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
