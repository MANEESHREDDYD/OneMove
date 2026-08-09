import pandas as pd


def process_bronze_layer(raw_events_path: str, output_parquet: str):
    print(f"Extracting raw JSON from {raw_events_path}...")
    # Simulated pipeline
    df = pd.DataFrame([{"id": "ev1", "type": "OBSERVATION", "raw_payload": "{}"}])
    df.to_parquet(output_parquet)
    print(f"Bronze parquet written to {output_parquet}")
