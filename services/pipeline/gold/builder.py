import pandas as pd


def build_gold_tables(silver_parquet: str, output_dir: str):
    print(f"Building Gold tables from {silver_parquet}...")
    df = pd.read_parquet(silver_parquet)
    # Output dimensional tables
    df.to_parquet(f"{output_dir}/dim_observations.parquet")
    print(f"Gold tables written to {output_dir}")
