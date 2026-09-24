"""
Execution script to process all FIRMS datasets in data/raw/
using the FIRMS + Temporal Intelligence Pipeline.
"""

import glob
import os
import pandas as pd
from data_processing.pipeline import FIRMSTemporalPipeline


def main():
    pipeline = FIRMSTemporalPipeline(output_dir="data/processed")
    raw_files = sorted(glob.glob("data/raw/*.csv"))

    print(f"Found {len(raw_files)} raw FIRMS files to process:")
    for f in raw_files:
        print(f"  - {f}")

    results = {}

    # Process each individual file
    for filepath in raw_files:
        fname = os.path.basename(filepath)
        prefix = os.path.splitext(fname)[0]
        df_raw = pd.read_csv(filepath)
        raw_count = len(df_raw)

        print(f"\nProcessing {fname} ({raw_count} raw rows)...")
        res = pipeline.process_observations(
            observations_source=filepath,
            save_outputs=True,
            output_prefix=prefix,
        )

        filtered_count = res["summary"]["observations_within_monitoring_area"]
        event_count = res["summary"]["total_clustered_events"]
        persist = res["summary"]["persistence_distribution"]

        results[fname] = {
            "raw_rows": raw_count,
            "filtered_rows": filtered_count,
            "events": event_count,
            "persistence": persist,
        }
        print(f"  -> Raw: {raw_count}, Filtered (50km): {filtered_count}, Events: {event_count}")
        print(f"  -> Persistence: {persist}")

    # Process consolidated/combined dataset across all files
    print("\nProcessing consolidated dataset across all raw files...")
    raw_dfs = [pd.read_csv(f) for f in raw_files]
    df_combined = pd.concat(raw_dfs, ignore_index=True)
    combined_raw_count = len(df_combined)

    res_combined = pipeline.process_observations(
        observations_source=df_combined,
        save_outputs=True,
        output_prefix="giaspura_fire_events",
    )

    combined_filtered = res_combined["summary"]["observations_within_monitoring_area"]
    combined_events = res_combined["summary"]["total_clustered_events"]
    combined_persist = res_combined["summary"]["persistence_distribution"]

    results["combined"] = {
        "raw_rows": combined_raw_count,
        "filtered_rows": combined_filtered,
        "events": combined_events,
        "persistence": combined_persist,
    }

    print(f"  -> Combined Raw: {combined_raw_count}, Filtered (50km): {combined_filtered}, Events: {combined_events}")
    print(f"  -> Persistence: {combined_persist}")

    print("\nDone!")
    return results


if __name__ == "__main__":
    main()
