import pandas as pd
import numpy as np
from analytics.features.builder import build_feature_dataset

def main():
    print("Building Dataset for Bahrain 2023 (Session 7953)...")
    df = build_feature_dataset(7953)
    
    print("\n--- TASK 3: MULTI-DRIVER SANITY CHECK (LAP 10) ---")
    lap10 = df[df['lap_number'] == 10].sort_values('position')
    
    # We want 5 drivers
    cols = ['driver_number', 'position', 'gap_to_leader', 'tyre_compound', 'tyre_age', 'stint_lap_number', 'cars_within_2s']
    print(lap10[cols].head(5).to_string(index=False))
    
    print("\n--- TASK 4: TYRE AGE VERIFICATION (Driver 1, Laps 10-15) ---")
    cols2 = ['lap_number', 'tyre_compound', 'tyre_age', 'stint_number', 'stint_lap_number', 'pit_in']
    d1 = df[df['driver_number'] == 1].sort_values('lap_number')
    print(d1[cols2][9:15].to_string(index=False))
    
    print("\n--- TASK 5: ROLLING WINDOW VERIFICATION (Driver 1, Laps 1-5) ---")
    cols3 = ['lap_number', 'lap_time', 'lap_time_valid', 'rolling_mean_pace_3', 'rolling_mean_pace_5']
    print(d1[cols3].head(5).to_string(index=False))
    
    print("\n--- TASK 6: FEATURE QUALITY REPORT ---")
    print(f"Total feature rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Number of valid lap-time rows: {df['lap_time_valid'].sum()}")
    print(f"Number of rows with valid gap data: {df['gap_valid'].sum()}")
    sc_vsc_rows = df['safety_car_active'].sum() + df['virtual_safety_car_active'].sum()
    print(f"Number of rows affected by SC/VSC context: {sc_vsc_rows}")
    aligned = df[df['weather_alignment_quality'] != 'POOR']
    print(f"Number of rows with weather alignment: {len(aligned)}")
    
    # Missing percentages
    missing = (df.isna().sum() / len(df)) * 100
    print("\nMissing Percentages:")
    for col, pct in missing.items():
        if pct > 0:
            print(f"  {col}: {pct:.1f}% missing")

if __name__ == "__main__":
    main()
